"""
server/app/services/code_validator.py

Deterministic pre-processor for Gemini-generated Manim code.
Runs BEFORE the render attempt and BEFORE the Gemini retry loop.

v2 (AST/tokenizer-based rewrite): see py's module docstring for the
core design rationale. Summary of what changed from the regex-based v1 and
why (each maps to a specific item from friend feedback on the old file):

  - Phase 1a (py): deprecated-API renames now use Python's
    own tokenizer, so a comment or a Text() string that happens to mention
    "ShowCreation(" is never corrupted (old: plain str.replace() touched
    everything, comments and strings included).
  - Phase 1b (py): numpy-import insertion, .move_to() scalar
    wrapping, aligned_edge=CENTER, font=, font_size/axes clamping, and
    axis_config include_numbers removal are now AST-based — e.g. the numpy
    import fixer now respects module docstrings and `from __future__`
    imports instead of blindly prepending (old version could produce an
    actual SyntaxError by inserting before a future import).
  - Phase 1c (py): MathTex/Tex/Text string CONTENT fixes
    (backslash over-escaping, missing r-prefix, Thai-in-mathrm, LaTeX-in-
    Text, quote normalization) now edit the exact raw source span of each
    string argument located via the AST, rather than matching a regex
    against the whole file. This is what makes it possible to correctly
    fix a non-raw string with a dangerous escape sequence at all (working
    on the AST's decoded .value would already be corrupted by the time we
    see it), and it naturally handles multi-line and double-quoted strings
    that the old per-line regexes missed.
  - Phase 1d (py): VGroup(*[comprehension]) expansion
    and long-MathTex splitting now compute indentation from the actual
    AST node position instead of a hardcoded guess — the old version could
    produce invalid (or just wrong) indentation if the pattern appeared at
    an unexpected nesting depth.
  - Undefined-variable detection (py): properly scope-aware using
    real nested-function resolution, instead of one flat file-wide dict.
    This fixes a real cross-function false-negative bug AND correctly
    avoids flagging legitimate closures (the projectile-motion
    `def trajectory(t): ...` pattern from prompts.py rule 5B-2 reads
    outer-scope variables, which is normal Python and must not be flagged).
  - New: explicit syntax-error detection (py), run first and
    short-circuiting the rest of the pipeline — a malformed file now gets
    reported as an explicit, actionable SYNTAX_ERROR violation instead of
    silently skipping downstream checks.
  - Font-size detectors consolidated: the old file had two detectors with
    different, contradictory thresholds (>28 and >30) and a comment noting
    one might be unused. Now one detector matching the fixer's own limits.

A critical bug specific to this rewrite (documented in py): Python's
`ast` module reports column offsets in UTF-8 BYTES, not characters. Since
virtually every string in this codebase contains Thai text, naively treating
col_offset as a Python string index silently misaligns every edit on a line
with Thai text before the target node. Source handles the conversion
correctly — every fixer above goes through it.
"""

from __future__ import annotations
import ast
import io
import tokenize as _tokenize
import builtins as _builtins_module
import re
from dataclasses import dataclass, field


# ============================================================================
# CORE
# ============================================================================

import ast
import io
import tokenize as _tokenize


def _byte_col_to_char_col(line: str, byte_col: int) -> int:
    """
    ast.AST.col_offset / end_col_offset are documented as UTF-8 BYTE offsets
    into the source line, not character offsets (see the `ast` docs: "the
    UTF-8 byte offset of the first token"). Since virtually every string in
    this codebase contains Thai text (3 bytes/char in UTF-8), naively using
    col_offset as a Python string index silently misaligns every node that
    comes after Thai text on the same line — this converts correctly.
    """
    return len(line.encode("utf-8")[:byte_col].decode("utf-8", errors="ignore"))


class Source:
    """
    Precomputed position-lookup context for one piece of source code. Build
    ONE of these per call to a fixer (via `Source(code)`), then use
    .span(node) / .text(node) instead of bare line-offset math — this is
    what correctly handles the UTF-8 byte-vs-char column issue above.
    """

    __slots__ = ("code", "_lines", "_char_offsets")

    def __init__(self, code: str):
        self.code = code
        # Lines WITHOUT line endings — ast col_offset never includes the
        # newline character, so this is what byte-column conversion needs.
        self._lines = code.splitlines() + ["", ""]  # padded for EOF edge positions
        offsets = [0]
        for line in code.splitlines(keepends=True):
            offsets.append(offsets[-1] + len(line))
        self._char_offsets = offsets

    def offset(self, lineno: int, byte_col: int) -> int:
        line = self._lines[lineno - 1] if 0 <= lineno - 1 < len(self._lines) else ""
        char_col = _byte_col_to_char_col(line, byte_col)
        base = self._char_offsets[lineno - 1] if 0 <= lineno - 1 < len(self._char_offsets) else len(self.code)
        return base + char_col

    def span(self, node: ast.AST) -> tuple[int, int]:
        start = self.offset(node.lineno, node.col_offset)
        end = self.offset(node.end_lineno, node.end_col_offset)
        return start, end

    def text(self, node: ast.AST) -> str:
        start, end = self.span(node)
        return self.code[start:end]


def apply_edits(code: str, edits: list[tuple[int, int, str]]) -> str:
    """edits: list of (start_offset, end_offset, replacement). Later-position
    edits are applied first so earlier offsets stay valid."""
    if not edits:
        return code
    # Reject overlapping edits defensively (keep the first one seen at a
    # given start, drop any edit whose span overlaps an already-kept one) —
    # this can legitimately happen if two independent fixers both decide to
    # touch the same node; better to skip one than corrupt the source.
    deduped: list[tuple[int, int, str]] = []
    for e in sorted(edits, key=lambda e: e[0]):
        if deduped and e[0] < deduped[-1][1]:
            continue  # overlaps previous edit — skip, keep the earlier one
        deduped.append(e)
    result = code
    for start, end, repl in sorted(deduped, key=lambda e: e[0], reverse=True):
        result = result[:start] + repl + result[end:]
    return result


def safe_parse(code: str) -> ast.Module | None:
    """Returns None instead of raising on any SyntaxError/ValueError, so
    AST-based fixers can be skipped cleanly on malformed code instead of
    crashing the whole pipeline."""
    try:
        return ast.parse(code)
    except (SyntaxError, ValueError):
        return None


def replace_bare_names(
    code: str,
    name_map: dict[str, str],
    *,
    require_call: bool = False,
    require_attribute: bool = False,
    fixes: list[str] | None = None,
    fix_label: str = "AUTO-FIX",
) -> str:
    """
    Token-level find/replace of NAME tokens. Skips anything inside a STRING
    or COMMENT token automatically (tokenize separates those out), so this
    never corrupts a comment or a Text()/Manim string literal that happens
    to mention the same identifier — unlike a plain str.replace() or a
    regex over the raw source.

    require_call: only replace when the NAME is immediately followed by '('
        (i.e. it's being called — used for ShowCreation(, TexMobject(, ...).
    require_attribute: only replace when the NAME is immediately preceded
        by '.' (i.e. it's an attribute access — used for .get_graph()).

    Falls back to returning the code unchanged if tokenizing fails (e.g. the
    code has a real syntax error); downstream syntax-error detection handles
    that case instead.
    """
    if fixes is None:
        fixes = []
    try:
        tokens = list(_tokenize.generate_tokens(io.StringIO(code).readline))
    except (_tokenize.TokenizeError, IndentationError, SyntaxError, ValueError):
        return code

    lines = code.splitlines(keepends=True)
    # tokenize can report positions on a virtual line one past the last real
    # line (e.g. ENDMARKER after a file with no trailing newline) — pad so
    # row lookups never go out of range.
    lines = lines + ["", ""]

    def text_between(start: tuple[int, int], end: tuple[int, int]) -> str:
        if start[0] == end[0]:
            return lines[start[0] - 1][start[1]:end[1]]
        parts = [lines[start[0] - 1][start[1]:]]
        for row in range(start[0] + 1, end[0]):
            parts.append(lines[row - 1])
        parts.append(lines[end[0] - 1][:end[1]])
        return "".join(parts)

    out: list[str] = []
    last_end = (1, 0)
    n = len(tokens)

    for i, tok in enumerate(tokens):
        tok_type, tok_string, start, end, _line = tok
        out.append(text_between(last_end, start))

        matched = tok_type == _tokenize.NAME and tok_string in name_map
        if matched and require_call:
            nxt = tokens[i + 1] if i + 1 < n else None
            matched = bool(nxt and nxt.type == _tokenize.OP and nxt.string == "(")
        if matched and require_attribute:
            prev = tokens[i - 1] if i > 0 else None
            matched = bool(prev and prev.type == _tokenize.OP and prev.string == ".")

        if matched:
            replacement = name_map[tok_string]
            if replacement != tok_string:
                fixes.append(f"{fix_label}: {tok_string} \u2192 {replacement}")
            out.append(replacement)
        else:
            out.append(tok_string)
        last_end = end

    # Trailing text after the final token (rare, e.g. trailing whitespace
    # with no final NEWLINE) — tokens always end with ENDMARKER whose start
    # covers this, so this is normally a no-op.
    return "".join(out)


def split_string_prefix_and_quote(raw: str) -> tuple[str, str, str, str]:
    """
    raw is the exact source text of a string literal, e.g. "r'\\theta'" or
    'f"hello"' or "'''multi\\nline'''". Returns (prefix, quote, content,
    quote) where content is the text strictly between the quote characters,
    unmodified. Raises ValueError if raw doesn't look like a string literal.
    """
    i = 0
    while i < len(raw) and raw[i].isalpha():
        i += 1
    prefix = raw[:i]
    rest = raw[i:]
    for q in ("'''", '"""', "'", '"'):
        if rest.startswith(q) and rest.endswith(q) and len(rest) >= 2 * len(q):
            content = rest[len(q):-len(q)]
            return prefix, q, content, q
    raise ValueError(f"not a recognizable string literal: {raw!r}")


def find_calls(tree: ast.AST, names: set[str]) -> list[ast.Call]:
    """All ast.Call nodes anywhere in tree whose function is a bare Name
    (not an attribute access) in `names`, e.g. MathTex(...), Text(...)."""
    return [
        node for node in ast.walk(tree)
        if isinstance(node, ast.Call)
        and isinstance(node.func, ast.Name)
        and node.func.id in names
    ]


def get_keyword(call: ast.Call, name: str) -> ast.keyword | None:
    for kw in call.keywords:
        if kw.arg == name:
            return kw
    return None


# ============================================================================
# SCOPE
# ============================================================================

import ast
import builtins as _builtins_module
import re


_KNOWN_GLOBALS = {
    "self", "cls", "config", "np",
    "smooth", "linear", "there_and_back", "there_and_back_with_pause",
    "running_start", "not_quite_there", "wiggle", "squish_rate_func",
    "lingering", "exponential_decay", "double_smooth", "rush_into",
    "rush_from", "slow_into", "always_redraw", "always_shift",
    "always_rotate", "always_scale", "turn_animation_into_updater",
    "interpolate", "rate_functions",
}
_NAME_PATTERN = re.compile(r"^[a-z_][a-z0-9_]*$")
_COMP_TYPES = (ast.ListComp, ast.SetComp, ast.DictComp, ast.GeneratorExp)


class _Scope:
    __slots__ = ("names", "kind", "parent")

    def __init__(self, kind: str, parent: "_Scope | None" = None):
        self.names: dict[str, int] = {}
        self.kind = kind  # 'module' | 'function' | 'comprehension' | 'class'
        self.parent = parent

    def define(self, name: str, lineno: int) -> None:
        if name not in self.names or lineno < self.names[name]:
            self.names[name] = lineno

    def resolve(self) -> "_Scope | None":
        """Find the nearest ancestor (including self) with this name bound,
        skipping class scopes when walking outward (real Python behavior:
        a function nested in a class body doesn't see the class's own
        attributes as bare names)."""
        return None  # replaced per-call below; see resolve_name()

    def resolve_name(self, name: str) -> "_Scope | None":
        scope = self
        first = True
        while scope is not None:
            if (first or scope.kind != "class") and name in scope.names:
                return scope
            scope = scope.parent
            first = False
        return None


class _BindingCollector(ast.NodeVisitor):
    """Populates scope.names with every name bound DIRECTLY in this scope's
    statements — does not descend into nested function/lambda/comprehension
    bodies (those get their own child _Scope, collected separately when the
    checker recurses into them)."""

    def __init__(self, scope: _Scope):
        self.scope = scope

    def _targets(self, target: ast.AST, lineno: int) -> None:
        for n in ast.walk(target):
            if isinstance(n, ast.Name):
                self.scope.define(n.id, lineno)

    def visit_FunctionDef(self, node):
        self.scope.define(node.name, node.lineno)  # name bound in enclosing scope

    visit_AsyncFunctionDef = visit_FunctionDef

    def visit_ClassDef(self, node):
        self.scope.define(node.name, node.lineno)

    def visit_Lambda(self, node):
        pass  # lambda body is its own scope; nothing leaks out

    def visit_Import(self, node):
        for alias in node.names:
            self.scope.define(alias.asname or alias.name.split(".")[0], node.lineno)

    def visit_ImportFrom(self, node):
        for alias in node.names:
            if alias.name != "*":
                self.scope.define(alias.asname or alias.name, node.lineno)

    def visit_Assign(self, node):
        for t in node.targets:
            self._targets(t, node.lineno)
        self.generic_visit(node)

    def visit_AugAssign(self, node):
        self._targets(node.target, node.lineno)
        self.generic_visit(node)

    def visit_AnnAssign(self, node):
        if node.target is not None:
            self._targets(node.target, node.lineno)
        self.generic_visit(node)

    def visit_For(self, node):
        self._targets(node.target, node.lineno)
        self.generic_visit(node)

    visit_AsyncFor = visit_For

    def visit_With(self, node):
        for item in node.items:
            if item.optional_vars is not None:
                self._targets(item.optional_vars, node.lineno)
        self.generic_visit(node)

    visit_AsyncWith = visit_With

    def visit_NamedExpr(self, node):  # walrus operator `x := ...`
        if isinstance(node.target, ast.Name):
            self.scope.define(node.target.id, node.lineno)
        self.generic_visit(node)

    def _skip_comprehension(self, node):
        pass  # own scope, collected separately

    visit_ListComp = _skip_comprehension
    visit_SetComp = _skip_comprehension
    visit_DictComp = _skip_comprehension
    visit_GeneratorExp = _skip_comprehension


def _collect(stmts_or_node, scope: _Scope) -> None:
    collector = _BindingCollector(scope)
    if isinstance(stmts_or_node, list):
        for s in stmts_or_node:
            collector.visit(s)
    else:
        collector.visit(stmts_or_node)


def find_undefined_variables(code: str) -> list[tuple[int, str, str]]:
    """
    Returns a list of (lineno, name, description) for every name that's
    either never bound anywhere visible from where it's used, or used
    before its first assignment within the SAME immediate scope (ordering
    is only checked within one scope — a nested function using a name the
    enclosing scope defines later-in-the-function-but-before-the-call is a
    normal, valid Python closure and is never flagged).
    """
    tree = safe_parse(code)
    if tree is None:
        return []

    src = Source(code)
    whitelist = set(dir(_builtins_module)) | _KNOWN_GLOBALS
    violations: list[tuple[int, str, str]] = []
    reported: set[str] = set()

    module_scope = _Scope("module")
    _collect(tree.body, module_scope)

    def check_scope(body, scope: _Scope) -> None:
        """Check every Load-context Name directly in `body` (a list of
        statements or a single expression), recursing into nested scopes
        with fresh _Scope objects as they're encountered."""

        class _Checker(ast.NodeVisitor):
            def visit_Name(self, node: ast.Name):
                if not isinstance(node.ctx, ast.Load):
                    return
                name = node.id
                if name in whitelist or not _NAME_PATTERN.match(name):
                    return
                owner = scope.resolve_name(name)
                if owner is None:
                    if name not in reported:
                        violations.append((
                            node.lineno, name,
                            f"\u0e15\u0e31\u0e27\u0e41\u0e1b\u0e23 '{name}' "
                            "\u0e16\u0e39\u0e01\u0e43\u0e0a\u0e49\u0e07\u0e32\u0e19\u0e41\u0e15\u0e48\u0e44\u0e21\u0e48\u0e40\u0e04\u0e22\u0e16\u0e39\u0e01\u0e01\u0e33\u0e2b\u0e19\u0e14\u0e04\u0e48\u0e32\u0e17\u0e35\u0e48\u0e44\u0e2b\u0e19\u0e40\u0e25\u0e22\u0e43\u0e19\u0e42\u0e04\u0e49\u0e14 "
                            "(\u0e2d\u0e32\u0e08\u0e16\u0e39\u0e01\u0e25\u0e1a\u0e17\u0e34\u0e49\u0e07\u0e42\u0e14\u0e22\u0e44\u0e21\u0e48\u0e44\u0e14\u0e49\u0e15\u0e31\u0e49\u0e07\u0e43\u0e08\u0e23\u0e30\u0e2b\u0e27\u0e48\u0e32\u0e07\u0e01\u0e32\u0e23\u0e41\u0e01\u0e49\u0e1a\u0e31\u0e01\u0e2d\u0e31\u0e15\u0e42\u0e19\u0e21\u0e31\u0e15\u0e34) "
                            "\u0e08\u0e30\u0e17\u0e33\u0e43\u0e2b\u0e49\u0e40\u0e01\u0e34\u0e14 NameError \u0e15\u0e2d\u0e19\u0e40\u0e23\u0e19\u0e40\u0e14\u0e2d\u0e23\u0e4c",
                        ))
                        reported.add(name)
                elif owner is scope and scope.kind != "module_ordering_exempt":
                    first_def = scope.names[name]
                    if first_def > node.lineno and name not in reported:
                        violations.append((
                            node.lineno, name,
                            f"\u0e15\u0e31\u0e27\u0e41\u0e1b\u0e23 '{name}' \u0e16\u0e39\u0e01\u0e43\u0e0a\u0e49\u0e07\u0e32\u0e19\u0e17\u0e35\u0e48\u0e1a\u0e23\u0e23\u0e17\u0e31\u0e14 "
                            f"{node.lineno} \u0e01\u0e48\u0e2d\u0e19\u0e17\u0e35\u0e48\u0e08\u0e30\u0e16\u0e39\u0e01\u0e01\u0e33\u0e2b\u0e19\u0e14\u0e04\u0e48\u0e32\u0e04\u0e23\u0e31\u0e49\u0e07\u0e41\u0e23\u0e01\u0e17\u0e35\u0e48\u0e1a\u0e23\u0e23\u0e17\u0e31\u0e14 "
                            f"{first_def} \u2014 \u0e08\u0e30\u0e17\u0e33\u0e43\u0e2b\u0e49\u0e40\u0e01\u0e34\u0e14 NameError \u0e15\u0e2d\u0e19\u0e40\u0e23\u0e19\u0e40\u0e14\u0e2d\u0e23\u0e4c",
                        ))
                        reported.add(name)

            def _enter_function(self, node):
                child = _Scope("function", parent=scope)
                args = node.args
                for a in list(args.posonlyargs) + list(args.args) + list(args.kwonlyargs):
                    child.define(a.arg, node.lineno)
                if args.vararg:
                    child.define(args.vararg.arg, node.lineno)
                if args.kwarg:
                    child.define(args.kwarg.arg, node.lineno)
                _collect(node.body, child)
                check_scope(node.body, child)
                # defaults & decorators execute in the ENCLOSING scope
                for d in list(args.defaults) + [d for d in args.kw_defaults if d is not None]:
                    self.visit(d)
                for d in node.decorator_list:
                    self.visit(d)

            def visit_FunctionDef(self, node):
                self._enter_function(node)

            visit_AsyncFunctionDef = visit_FunctionDef

            def visit_Lambda(self, node):
                child = _Scope("function", parent=scope)
                args = node.args
                for a in list(args.posonlyargs) + list(args.args) + list(args.kwonlyargs):
                    child.define(a.arg, node.lineno)
                if args.vararg:
                    child.define(args.vararg.arg, node.lineno)
                if args.kwarg:
                    child.define(args.kwarg.arg, node.lineno)
                check_scope([node.body], child)
                for d in list(args.defaults) + [d for d in args.kw_defaults if d is not None]:
                    self.visit(d)

            def visit_ClassDef(self, node):
                child = _Scope("class", parent=scope)
                _collect(node.body, child)
                check_scope(node.body, child)
                for base in node.bases:
                    self.visit(base)
                for kw in node.keywords:
                    self.visit(kw)
                for d in node.decorator_list:
                    self.visit(d)

            def _comp(self, node):
                # Simplification: treat the whole comprehension (elt/key/
                # value + all generators' iters + ifs) as living in the
                # comprehension's own child scope. Real Python resolves the
                # OUTERMOST iterable in the enclosing scope instead, but
                # that distinction essentially never matters for generated
                # Manim code (comprehensions over already-defined lists),
                # and erring toward "treat as one scope" only risks a rare
                # missed false-positive, never a wrong NameError report.
                child = _Scope("comprehension", parent=scope)
                for gen in node.generators:
                    for n in ast.walk(gen.target):
                        if isinstance(n, ast.Name):
                            child.define(n.id, node.lineno)
                parts = [node.elt] if hasattr(node, "elt") else [node.key, node.value]
                for gen in node.generators:
                    parts.append(gen.iter)
                    parts.extend(gen.ifs)
                check_scope(parts, child)

            visit_ListComp = _comp
            visit_SetComp = _comp
            visit_DictComp = _comp
            visit_GeneratorExp = _comp

        checker = _Checker()
        if isinstance(body, list):
            for item in body:
                checker.visit(item)
        else:
            checker.visit(body)

    check_scope(tree.body, module_scope)
    return violations


# ============================================================================
# TOKEN FIXERS
# ============================================================================

# Deprecated/forbidden Manim API names → their replacements. All of these
# are call-site renames (the old name is always followed by '(' in valid
# usage), so require_call=True is safe and mirrors the intent of each
# original single-purpose fixer.
_CALL_RENAMES: dict[str, str] = {
    "ShowCreation": "Create",
    "TexMobject": "MathTex",
    "TextMobject": "Text",
    "Indicate": "FadeIn",
    "Flash": "GrowFromCenter",
    "ApplyWave": "FadeIn",
}

# Attribute-access call-site rename: axes.get_graph(...) -> axes.plot(...)
_ATTRIBUTE_CALL_RENAMES: dict[str, str] = {
    "get_graph": "plot",
}


def fix_deprecated_call_names(code: str, fixes: list[str]) -> str:
    return replace_bare_names(
        code, _CALL_RENAMES, require_call=True, fixes=fixes,
        fix_label="AUTO-FIX: deprecated API",
    )


def fix_deprecated_attribute_names(code: str, fixes: list[str]) -> str:
    return replace_bare_names(
        code, _ATTRIBUTE_CALL_RENAMES, require_call=True, require_attribute=True,
        fixes=fixes, fix_label="AUTO-FIX: deprecated API",
    )


TOKEN_LEVEL_FIXERS = [
    fix_deprecated_call_names,
    fix_deprecated_attribute_names,
]


# ============================================================================
# AST FIXERS
# ============================================================================

import ast



def fix_missing_numpy_import(code: str, fixes: list[str]) -> str:
    """
    AST-aware insertion of 'import numpy as np', placed after any shebang,
    encoding declaration, module docstring, and __future__ imports — never
    just blindly prepended, which could otherwise land before a
    `from __future__ import annotations` line and cause a SyntaxError
    (future imports must be the first statement in the file).
    """
    tree = safe_parse(code)
    if tree is None:
        return code

    for node in tree.body:
        if isinstance(node, ast.Import) and any(
            alias.name == "numpy" and alias.asname == "np" for alias in node.names
        ):
            return code  # already imported correctly

    src = Source(code)
    insert_at_offset = 0
    body = tree.body

    idx = 0
    # module docstring
    if (
        body
        and isinstance(body[0], ast.Expr)
        and isinstance(body[0].value, ast.Constant)
        and isinstance(body[0].value.value, str)
    ):
        idx = 1
    # __future__ imports (must stay first, so keep them ahead of our import)
    while idx < len(body) and (
        isinstance(body[idx], ast.ImportFrom) and body[idx].module == "__future__"
    ):
        idx += 1

    if idx < len(body):
        insert_at_offset = src.offset(body[idx].lineno, 0)
    else:
        insert_at_offset = len(code)

    fixes.append("AUTO-FIX: Added 'import numpy as np'")
    insertion = "import numpy as np\n"
    return code[:insert_at_offset] + insertion + code[insert_at_offset:]


_ZONE_SCALAR_VARS = {
    "bottom_zone_center_y", "middle_zone_center_y", "top_zone_center_y",
    "bottom_zone_bottom", "bottom_zone_top",
    "middle_zone_bottom", "middle_zone_top",
    "top_zone_bottom", "top_zone_top",
}


def fix_move_to_scalar(code: str, fixes: list[str]) -> str:
    """.move_to(some_zone_scalar_var) -> .move_to(np.array([0, var, 0]))"""
    tree = safe_parse(code)
    if tree is None:
        return code
    src = Source(code)
    edits: list[tuple[int, int, str]] = []

    for node in ast.walk(tree):
        if not (
            isinstance(node, ast.Call)
            and isinstance(node.func, ast.Attribute)
            and node.func.attr == "move_to"
            and len(node.args) == 1
        ):
            continue
        arg = node.args[0]
        if isinstance(arg, ast.Name) and arg.id in _ZONE_SCALAR_VARS:
            start, end = src.span(arg)
            edits.append((start, end, f"np.array([0, {arg.id}, 0])"))
            fixes.append(
                f"AUTO-FIX: .move_to({arg.id}) \u2192 "
                f".move_to(np.array([0, {arg.id}, 0]))"
            )
    return apply_edits(code, edits)


def fix_aligned_edge_center(code: str, fixes: list[str]) -> str:
    """aligned_edge=CENTER doesn't exist in Manim -> aligned_edge=LEFT."""
    tree = safe_parse(code)
    if tree is None:
        return code
    src = Source(code)
    edits: list[tuple[int, int, str]] = []

    for node in ast.walk(tree):
        if isinstance(node, ast.keyword) and node.arg == "aligned_edge":
            if isinstance(node.value, ast.Name) and node.value.id == "CENTER":
                start, end = src.span(node.value)
                edits.append((start, end, "LEFT"))
                fixes.append(
                    "AUTO-FIX: aligned_edge=CENTER \u2192 aligned_edge=LEFT "
                    "(CENTER doesn't exist in Manim)"
                )
    return apply_edits(code, edits)


def fix_font_in_mathtex(code: str, fixes: list[str]) -> str:
    """Remove font= kwarg from MathTex()/Tex() calls (not a supported param)."""
    tree = safe_parse(code)
    if tree is None:
        return code
    src = Source(code)
    edits: list[tuple[int, int, str]] = []

    for call in find_calls(tree, {"MathTex", "Tex"}):
        kw = get_keyword(call, "font")
        if kw is None:
            continue
        # Remove "font=<value>" plus one adjacent comma (prefer the comma
        # that precedes it, matching how the original arg list reads).
        kw_start, kw_end = src.span(kw)
        # kw.value doesn't include "font=" itself in its span, so walk back
        # to find the '=' and the arg name by re-deriving the start from
        # the keyword node's own position (ast.keyword has its own lineno
        # in modern Python — use it directly).
        start = src.offset(kw.lineno, kw.col_offset)
        end = kw_end
        before = code[:start]
        after = code[end:]
        # Consume a leading ", " before this kwarg if present, else a
        # trailing ", " after it.
        stripped_before = before.rstrip()
        if stripped_before.endswith(","):
            start -= (len(before) - len(stripped_before)) + 1
        else:
            stripped_after = after.lstrip()
            consumed = len(after) - len(stripped_after)
            if stripped_after.startswith(","):
                end += consumed + 1
        edits.append((start, end, ""))
        fixes.append("AUTO-FIX: Removed font= parameter from MathTex/Tex (not supported)")
    return apply_edits(code, edits)


MAX_TEXT_FONT_SIZE = 28
MAX_MATHTEX_FONT_SIZE = 20
MAX_AXES_X_LENGTH = 5.4
MAX_AXES_Y_LENGTH = 4.3


def _clamp_numeric_keyword(
    code: str, tree: ast.Module, src: "Source", *, call_names, kw_name, max_value, label,
) -> tuple[str, list[str]]:
    edits: list[tuple[int, int, str]] = []
    fixes: list[str] = []
    for call in find_calls(tree, call_names):
        kw = get_keyword(call, kw_name)
        if kw is None or not isinstance(kw.value, ast.Constant):
            continue
        val = kw.value.value
        if not isinstance(val, (int, float)) or isinstance(val, bool):
            continue
        if val > max_value:
            start, end = src.span(kw.value)
            clamped = int(max_value) if float(max_value).is_integer() else max_value
            edits.append((start, end, repr(clamped)))
            fixes.append(f"AUTO-FIX: {label} {kw_name}={val} > {max_value} \u2192 clamped to {clamped}")
    return apply_edits(code, edits), fixes


def fix_font_size_too_large(code: str, fixes: list[str]) -> str:
    """Clamp MathTex()/Tex() font_size to 20, Text() font_size to 28 — the
    same hard cap in every zone (see prompts.py rule 10 / table 5F)."""
    tree = safe_parse(code)
    if tree is None:
        return code
    src = Source(code)
    code, math_fixes = _clamp_numeric_keyword(
        code, tree, src, call_names={"MathTex", "Tex"},
        kw_name="font_size", max_value=MAX_MATHTEX_FONT_SIZE, label="MathTex/Tex font_size",
    )
    fixes.extend(math_fixes)
    tree = safe_parse(code)  # re-parse: positions shifted after edits above
    if tree is None:
        return code
    src = Source(code)
    code, text_fixes = _clamp_numeric_keyword(
        code, tree, src, call_names={"Text"},
        kw_name="font_size", max_value=MAX_TEXT_FONT_SIZE, label="Text font_size",
    )
    fixes.extend(text_fixes)
    return code


def fix_axes_too_large(code: str, fixes: list[str]) -> str:
    """Clamp x_length/y_length keyword args (on any call, matching the
    original's non-call-specific behavior) to the same limits enforced
    everywhere else in this pipeline and in prompts.py rule 9."""
    tree = safe_parse(code)
    if tree is None:
        return code
    src = Source(code)

    edits: list[tuple[int, int, str]] = []
    for node in ast.walk(tree):
        if not isinstance(node, ast.keyword):
            continue
        if node.arg not in ("x_length", "y_length"):
            continue
        if not isinstance(node.value, ast.Constant):
            continue
        val = node.value.value
        if not isinstance(val, (int, float)) or isinstance(val, bool):
            continue
        limit = MAX_AXES_X_LENGTH if node.arg == "x_length" else MAX_AXES_Y_LENGTH
        if val > limit:
            start, end = src.span(node.value)
            edits.append((start, end, repr(limit)))
            fixes.append(f"AUTO-FIX: {node.arg}={val} > {limit} \u2192 clamped to {limit}")
    return apply_edits(code, edits)


def fix_include_numbers_in_axis_config(code: str, fixes: list[str]) -> str:
    """
    Remove 'include_numbers' from an axis_config={...} dict (but NOT from
    x_axis_config/y_axis_config, where it's legitimate) — uses the AST
    dict's actual key/value nodes instead of line-based INDENT-sensitive
    scanning, so it's correct regardless of how the dict is formatted.
    """
    tree = safe_parse(code)
    if tree is None:
        return code
    src = Source(code)
    edits: list[tuple[int, int, str]] = []

    for node in ast.walk(tree):
        if not (isinstance(node, ast.keyword) and node.arg == "axis_config"):
            continue
        if not isinstance(node.value, ast.Dict):
            continue
        d = node.value
        for key, value in zip(d.keys, d.values):
            if (
                isinstance(key, ast.Constant)
                and key.value == "include_numbers"
            ):
                pair_start, _ = src.span(key)
                _, pair_end = src.span(value)
                # Consume a trailing ", " (or leading ", " if this was the
                # last item) so we don't leave a dangling comma behind.
                after = code[pair_end:]
                before = code[:pair_start]
                stripped_after = after.lstrip()
                consumed_after = len(after) - len(stripped_after)
                if stripped_after.startswith(","):
                    pair_end += consumed_after + 1
                    # also eat one following space so we don't leave "{  'x'"
                    if pair_end < len(code) and code[pair_end] == " ":
                        pair_end += 1
                else:
                    stripped_before = before.rstrip()
                    if stripped_before.endswith(","):
                        pair_start -= (len(before) - len(stripped_before)) + 1
                edits.append((pair_start, pair_end, ""))
                fixes.append(
                    "AUTO-FIX: Removed 'include_numbers' from axis_config "
                    "(not x_axis_config/y_axis_config, which keep it)"
                )
    return apply_edits(code, edits)


def fix_bottom_zone_bottom_typo(code: str, fixes: list[str]) -> str:
    """
    bottom_center = np.array([0, bottom_zone_bottom, 0])
      -> bottom_center = np.array([0, bottom_zone_center_y, 0])

    Deliberately narrow (matches the original regex's exact scope, not a
    blanket rename): `bottom_zone_bottom` is ALSO a distinct, LEGITIMATELY
    correct boilerplate variable elsewhere (the bottom edge Y-coordinate,
    as opposed to bottom_zone_center_y, the center Y-coordinate) — a
    blanket rename of every occurrence would corrupt that unrelated,
    correct usage. This only touches the second element of the literal
    [0, ..., 0] list passed to np.array(...) when assigned to bottom_center.
    """
    tree = safe_parse(code)
    if tree is None:
        return code
    src = Source(code)
    edits: list[tuple[int, int, str]] = []

    for node in ast.walk(tree):
        if not (
            isinstance(node, ast.Assign)
            and len(node.targets) == 1
            and isinstance(node.targets[0], ast.Name)
            and node.targets[0].id == "bottom_center"
            and isinstance(node.value, ast.Call)
            and isinstance(node.value.func, ast.Attribute)
            and node.value.func.attr == "array"
            and node.value.args
            and isinstance(node.value.args[0], ast.List)
        ):
            continue
        elts = node.value.args[0].elts
        if len(elts) == 3 and isinstance(elts[1], ast.Name) and elts[1].id == "bottom_zone_bottom":
            start, end = src.span(elts[1])
            edits.append((start, end, "bottom_zone_center_y"))
            fixes.append(
                "AUTO-FIX: bottom_center used bottom_zone_bottom \u2192 bottom_zone_center_y"
            )
    return apply_edits(code, edits)


PHASE_1B_FIXERS = [
    fix_missing_numpy_import,
    fix_bottom_zone_bottom_typo,
    fix_move_to_scalar,
    fix_aligned_edge_center,
    fix_font_in_mathtex,
    fix_font_size_too_large,
    fix_axes_too_large,
    fix_include_numbers_in_axis_config,
]


# ============================================================================
# STRING FIXERS
# ============================================================================

import ast
import re


# ─────────────────────────────────────────────────────────────────────────
# LaTeX command table — shared across several fixers below
# ─────────────────────────────────────────────────────────────────────────
_KNOWN_LATEX_COMMANDS = [
    "frac", "sqrt", "lambda", "Lambda", "phi", "Phi", "theta", "Theta",
    "Delta", "delta", "pi", "Pi", "mathrm", "mathbf", "cdot", "times",
    "approx", "circ", "alpha", "beta", "gamma", "Gamma", "sigma", "Sigma",
    "omega", "Omega", "mu", "nu", "epsilon", "rho", "tau", "chi", "psi",
    "eta", "xi", "zeta", "vec", "hat", "pm", "leq", "geq", "neq",
    "Rightarrow", "rightarrow", "Leftarrow", "leftarrow", "quad", "qquad",
    "left", "right", "infty", "sum", "int", "partial", "equiv", "propto",
]

_LATEX_TO_UNICODE = {
    "lambda": "\u03bb", "Lambda": "\u039b", "phi": "\u03c6", "Phi": "\u03a6",
    "theta": "\u03b8", "Theta": "\u0398", "alpha": "\u03b1", "beta": "\u03b2",
    "gamma": "\u03b3", "Gamma": "\u0393", "delta": "\u03b4", "Delta": "\u0394",
    "pi": "\u03c0", "Pi": "\u03a0", "sigma": "\u03c3", "omega": "\u03c9",
    "Omega": "\u03a9", "mu": "\u03bc", "nu": "\u03bd", "epsilon": "\u03b5",
    "rho": "\u03c1", "tau": "\u03c4", "chi": "\u03c7", "psi": "\u03c8",
    "eta": "\u03b7", "xi": "\u03be", "zeta": "\u03b6",
    "vec": "", "hat": "", "frac": "/", "cdot": "\u00b7", "times": "\u00d7",
    "pm": "\u00b1", "leq": "\u2264", "geq": "\u2265", "neq": "\u2260",
    "approx": "\u2248", "sqrt": "\u221a", "circ": "\u00b0", "infty": "\u221e",
    "mathrm": "", "mathbf": "",
}

_THAI_RANGE = re.compile(r"[\u0E00-\u0E7F]")

# A run of 2+ literal backslashes immediately before a known LaTeX command
# (or a spacing command \, \; \!) inside a raw string collapses to exactly
# one backslash — this is the root cause of the "mathrm{m/s}" garbled-text
# bug: a raw string keeps every backslash literally, so r'...\\\\frac...'
# (2 real backslash chars) reaches LaTeX as "\\" (newline) + "frac{...}"
# printed as plain text instead of being interpreted as \frac.
_cmd_alt = "|".join(_KNOWN_LATEX_COMMANDS)
_OVER_ESCAPED_PATTERN = re.compile(rf"\\{{2,}}(?=(?:{_cmd_alt})\b|[,;!])")

def _fix_mathtex_content(content: str, is_raw: bool, fixes: list[str]) -> str:
    """
    Apply the MathTex/Tex-specific content fixes to the RAW string content
    (the exact source text between the quotes, before Python ever decodes
    it — see the module docstring for why that matters).

    Because we work on raw source text, a single backslash character here
    means exactly one backslash character in the source regardless of
    whether the string is raw-prefixed or not — the string hasn't been
    Python-decoded yet. So the over-escape collapse (2+ backslashes before
    a known LaTeX command -> 1) applies identically either way. The only
    thing that differs between raw and non-raw strings is what happens
    AFTER this function returns: a non-raw string needs an 'r' prefix
    added at the call site (handled by the caller) so that Python's own
    parser doesn't later eat a sequence like '\\theta' as TAB+'heta' when
    the generated file is actually executed. We deliberately do NOT modify
    the backslash count differently based on is_raw — doing so double-
    counted the fix (this was caught by the test suite): the correct
    single fix is "collapse over-escaping in the raw text" + "ensure an r
    prefix is present if any backslash remains", never both an r-prefix
    AND a backslash-doubling for the same content.
    """
    original = content
    new_content = _OVER_ESCAPED_PATTERN.sub("\\\\", content)

    # \text{...} inside MathTex isn't valid LaTeX in Manim's renderer —
    # \mathrm{...} is, for ASCII-only content.
    def _text_to_mathrm(m: re.Match) -> str:
        inner = m.group(1)
        if all(ord(c) < 128 for c in inner):
            return f"\\mathrm{{{inner}}}"
        return m.group(0)
    new_content = re.sub(r"\\text\{([^}]*)\}", _text_to_mathrm, new_content)

    # Thai characters inside \mathrm{...} — LaTeX can't render Thai at all.
    def _strip_thai_from_mathrm(m: re.Match) -> str:
        inner = m.group(1)
        if not _THAI_RANGE.search(inner):
            return m.group(0)
        ascii_only = "".join(c for c in inner if ord(c) < 128)
        return f"\\mathrm{{{ascii_only}}}" if ascii_only.strip() else ""
    new_content = re.sub(r"\\mathrm\{([^}]*)\}", _strip_thai_from_mathrm, new_content)

    # Empty \mathrm{}
    new_content = new_content.replace("\\mathrm{}", "")

    if new_content != original:
        fixes.append(
            f"AUTO-FIX: Fixed LaTeX content in MathTex/Tex: "
            f"{original[:40]!r} \u2192 {new_content[:40]!r}"
        )
    return new_content


def _fix_text_content(content: str, fixes: list[str]) -> str:
    """Apply Text()-specific content fixes: strip LaTeX symbols (replace
    with unicode or drop), since Text() cannot render LaTeX at all."""
    original = content
    new_content = content

    # \command{...} -> just the inner content (e.g. \mathrm{m/s} -> m/s)
    def _brace_cmd(m: re.Match) -> str:
        cmd, inner = m.group(1), m.group(2)
        return inner
    new_content = re.sub(
        r"\\(" + "|".join(re.escape(c) for c in _KNOWN_LATEX_COMMANDS) + r")\{([^}]*)\}",
        _brace_cmd, new_content,
    )

    # bare \command (no braces) -> unicode symbol or drop
    for cmd, uni in sorted(_LATEX_TO_UNICODE.items(), key=lambda kv: -len(kv[0])):
        new_content = new_content.replace(f"\\{cmd}", uni)

    # \( \) \[ \] leftovers
    new_content = re.sub(r"\\[()\[\]]", "", new_content)

    if new_content != original:
        fixes.append(
            f"AUTO-FIX: Replaced LaTeX symbols with unicode in Text(): "
            f"{original[:40]!r} \u2192 {new_content[:40]!r}"
        )
    return new_content


def fix_string_contents(code: str, fixes: list[str]) -> str:
    """
    Walk every MathTex()/Tex()/Text() call, find its first positional
    argument IF it's a literal string (skip anything dynamic — an f-string,
    a variable, a .format() call — exactly matching feedback item 7's
    recommendation to ignore dynamically generated text), and rewrite its
    raw source content in place.
    """
    tree = safe_parse(code)
    if tree is None:
        return code
    src = Source(code)
    edits: list[tuple[int, int, str]] = []

    for call in find_calls(tree, {"MathTex", "Tex", "Text"}):
        if not call.args:
            continue
        arg = call.args[0]
        if not (isinstance(arg, ast.Constant) and isinstance(arg.value, str)):
            continue  # dynamic content (f-string, variable, etc.) — skip

        raw = src.text(arg)
        try:
            prefix, quote, content, _ = split_string_prefix_and_quote(raw)
        except ValueError:
            continue

        is_mathtex = call.func.id in ("MathTex", "Tex")
        is_raw = "r" in prefix.lower()

        if is_mathtex:
            new_content = _fix_mathtex_content(content, is_raw, fixes)
            # If the (possibly now-fixed) content contains a backslash and
            # the string isn't already raw, add the r-prefix so Python's
            # own parser won't later decode e.g. '\theta' into a literal
            # TAB character + 'heta' when the generated file is executed.
            if not is_raw and "\\" in new_content:
                new_prefix = prefix + "r"
                fixes.append(
                    "AUTO-FIX: Added missing r-prefix to MathTex/Tex string "
                    "containing a backslash (prevents Python from silently "
                    "eating LaTeX escapes like \\theta as control characters)"
                )
            else:
                new_prefix = prefix
        else:
            new_content = _fix_text_content(content, fixes)
            new_prefix = prefix

        # Normalize double-quoted -> single-quoted only when content has no
        # unescaped single quote (matches original behavior/intent).
        new_quote = quote
        if quote == '"' and "'" not in new_content:
            new_quote = "'"
            fixes.append(f"AUTO-FIX: Double-quoted string in {call.func.id}() \u2192 single quotes")

        if new_content != content or new_prefix != prefix or new_quote != quote:
            start, end = src.span(arg)
            edits.append((start, end, f"{new_prefix}{new_quote}{new_content}{new_quote}"))

    return apply_edits(code, edits)


# ============================================================================
# STRUCTURAL FIXERS
# ============================================================================

import ast
import re


_THAI_LONG = re.compile(r"[\u0E00-\u0E7F]{15,}")


def _indent_of(src: Source, node: ast.AST) -> str:
    """
    Leading whitespace of the STATEMENT this node's line belongs to — i.e.
    the actual code indentation, not the column the node itself happens to
    start at. For a bare expression statement (`VGroup(...)` on its own
    line) those are the same thing; for `var = VGroup(...)`, the call
    starts partway through the line (after "var = "), so we walk back from
    the node's start to the true start of that physical line and count
    leading spaces there instead of at the node's own column.
    """
    start_offset, _ = src.span(node)
    line_start = src.code.rfind("\n", 0, start_offset) + 1
    line_end = src.code.find("\n", line_start)
    if line_end == -1:
        line_end = len(src.code)
    line_text = src.code[line_start:line_end]
    stripped = line_text.lstrip(" ")
    return " " * (len(line_text) - len(stripped))


def fix_vgroup_list_comprehension(code: str, fixes: list[str]) -> str:
    """
    VGroup(*[Text(line, ...) for line in [...]]) or
    VGroup(*[Text(line, ...) for line in some_list_var])
    -> VGroup(Text('a', ...), Text('b', ...), ...)

    Handles both the inline-list-literal form and the named-variable form
    (matching the original fixer's two supported patterns), but computes
    indentation from the actual call site instead of assuming a fixed
    nesting depth.
    """
    tree = safe_parse(code)
    if tree is None:
        return code
    src = Source(code)
    edits: list[tuple[int, int, str]] = []

    # Collect module-level "name = ['a', 'b', ...]" string-list assignments,
    # for the named-variable form.
    list_vars: dict[str, list[str]] = {}
    for node in ast.walk(tree):
        if (
            isinstance(node, ast.Assign)
            and len(node.targets) == 1
            and isinstance(node.targets[0], ast.Name)
            and isinstance(node.value, ast.List)
        ):
            strs = []
            ok = True
            for elt in node.value.elts:
                if isinstance(elt, ast.Constant) and isinstance(elt.value, str):
                    strs.append(elt.value)
                else:
                    ok = False
                    break
            if ok and strs:
                list_vars[node.targets[0].id] = strs

    for call in ast.walk(tree):
        if not (isinstance(call, ast.Call) and isinstance(call.func, ast.Name)
                and call.func.id == "VGroup"):
            continue
        if len(call.args) != 1 or not isinstance(call.args[0], ast.Starred):
            continue
        starred = call.args[0]
        if not isinstance(starred.value, ast.ListComp):
            continue
        comp = starred.value
        if len(comp.generators) != 1:
            continue
        gen = comp.generators[0]
        # elt must itself be a Call like Text(loop_var, kw=..., ...)
        if not (
            isinstance(comp.elt, ast.Call)
            and isinstance(comp.elt.func, ast.Name)
            and comp.elt.args
            and isinstance(comp.elt.args[0], ast.Name)
            and isinstance(gen.target, ast.Name)
            and comp.elt.args[0].id == gen.target.id
        ):
            continue

        ctor = comp.elt.func.id
        # Reconstruct the "rest of the args" (everything after the loop
        # variable) exactly as written, using its own raw source span.
        if len(comp.elt.args) > 1 or comp.elt.keywords:
            first_extra = comp.elt.args[1] if len(comp.elt.args) > 1 else comp.elt.keywords[0]
            rest_start, _ = src.span(first_extra)
            _, call_end = src.span(comp.elt)
            # trim the trailing ')'
            rest_text = code[rest_start:call_end].rstrip()
            if rest_text.endswith(")"):
                rest_text = rest_text[:-1].rstrip()
        else:
            rest_text = ""

        strings: list[str] | None = None
        if isinstance(gen.iter, ast.List):
            strs = []
            ok = True
            for elt in gen.iter.elts:
                if isinstance(elt, ast.Constant) and isinstance(elt.value, str):
                    strs.append(elt.value)
                else:
                    ok = False
                    break
            if ok and strs:
                strings = strs
        elif isinstance(gen.iter, ast.Name) and gen.iter.id in list_vars:
            strings = list_vars[gen.iter.id]

        if not strings:
            continue

        indent = _indent_of(src, call)
        inner_indent = indent + "    "
        rest_suffix = f", {rest_text}" if rest_text else ""
        parts = [f"{ctor}('{item}'{rest_suffix})" for item in strings]
        replacement = (
            "VGroup(\n"
            + ",\n".join(f"{inner_indent}{p}" for p in parts)
            + f"\n{indent})"
        )
        start, end = src.span(call)
        edits.append((start, end, replacement))
        fixes.append(
            f"AUTO-FIX: Expanded VGroup(*[{ctor}(var, ...) for var in ...]) "
            f"\u2192 VGroup({ctor}(...), ...) with {len(strings)} items "
            f"(indentation matched to actual call site)"
        )

    return apply_edits(code, edits)


def fix_long_mathtex(code: str, fixes: list[str]) -> str:
    """
    var = MathTex(r'... > 40 chars ...', font_size=20)
    -> var = VGroup(MathTex(...), MathTex(...)).arrange(DOWN, ...)

    Splits at the first top-level '=' in the LaTeX, else the last comma.
    Indentation is computed from the Assign statement's own column, not a
    hardcoded guess.
    """
    tree = safe_parse(code)
    if tree is None:
        return code
    src = Source(code)
    edits: list[tuple[int, int, str]] = []

    for node in ast.walk(tree):
        if not (
            isinstance(node, ast.Assign)
            and len(node.targets) == 1
            and isinstance(node.targets[0], ast.Name)
            and isinstance(node.value, ast.Call)
            and isinstance(node.value.func, ast.Name)
            and node.value.func.id == "MathTex"
            and node.value.args
            and isinstance(node.value.args[0], ast.Constant)
            and isinstance(node.value.args[0].value, str)
        ):
            continue

        var = node.targets[0].id
        raw = src.text(node.value.args[0])
        try:
            prefix, quote, content, _ = split_string_prefix_and_quote(raw)
        except ValueError:
            continue
        if len(content) <= 40:
            continue

        depth = 0
        split_idx = None
        for i, ch in enumerate(content):
            if ch == "{":
                depth += 1
            elif ch == "}":
                depth -= 1
            elif depth == 0 and ch == "=":
                split_idx = i
                break
        if split_idx is None:
            split_idx = content.rfind(",")
            if split_idx == -1:
                continue
        first = content[:split_idx + 1].strip()
        second = content[split_idx + 1:].strip()
        if not first or not second:
            continue

        indent = _indent_of(src, node)
        inner_indent = indent + "    "
        replacement = (
            f"{var} = VGroup(\n"
            f"{inner_indent}MathTex({prefix}{quote}{first}{quote}, font_size=20),\n"
            f"{inner_indent}MathTex({prefix}{quote}{second}{quote}, font_size=20),\n"
            f"{indent}).arrange(DOWN, aligned_edge=LEFT, buff=0.15)\n"
            f"{indent}{var}.scale_to_fit_width(frame_width * 0.88)"
        )
        start, end = src.span(node)
        edits.append((start, end, replacement))
        fixes.append(
            f"AUTO-FIX: Split long MathTex ({len(content)} chars) into two "
            f"lines via VGroup (indentation matched to actual assignment)"
        )

    return apply_edits(code, edits)


def fix_arrange_right_long_thai(code: str, fixes: list[str]) -> str:
    """
    VGroup(Text('long thai label...'), MathTex(...)).arrange(RIGHT, ...)
    -> ...arrange(DOWN, aligned_edge=LEFT, buff=0.15)

    Unlike the original (which scanned up to 20 PHYSICAL LINES backward
    looking for a Text() call, a fragile heuristic that breaks on unusual
    formatting), this walks the actual VGroup(...) call's own arguments via
    the AST, so it works regardless of line layout.
    """
    tree = safe_parse(code)
    if tree is None:
        return code
    src = Source(code)
    edits: list[tuple[int, int, str]] = []

    for node in ast.walk(tree):
        if not (
            isinstance(node, ast.Call)
            and isinstance(node.func, ast.Attribute)
            and node.func.attr == "arrange"
            and node.args
            and isinstance(node.args[0], ast.Name)
            and node.args[0].id == "RIGHT"
        ):
            continue
        target = node.func.value
        if not (
            isinstance(target, ast.Call)
            and isinstance(target.func, ast.Name)
            and target.func.id == "VGroup"
        ):
            continue

        has_long_thai = False
        for element in target.args:
            if (
                isinstance(element, ast.Call)
                and isinstance(element.func, ast.Name)
                and element.func.id == "Text"
                and element.args
                and isinstance(element.args[0], ast.Constant)
                and isinstance(element.args[0].value, str)
                and _THAI_LONG.search(element.args[0].value)
            ):
                has_long_thai = True
                break
        if not has_long_thai:
            continue

        # Replace the argument list of .arrange(...) with the DOWN form,
        # preserving nothing else about the call (matches original intent).
        start, end = src.span(node)
        call_head_end = src.span(node.func)[1]  # end of ".arrange"
        replacement = code[start:call_head_end] + "(DOWN, aligned_edge=LEFT, buff=0.15)"
        edits.append((start, end, replacement))
        fixes.append(
            "AUTO-FIX: .arrange(RIGHT) with long Thai Text (found via AST, "
            "not line-scanning) \u2192 .arrange(DOWN, aligned_edge=LEFT) to prevent overflow"
        )

    return apply_edits(code, edits)


PHASE_1D_FIXERS = [
    fix_vgroup_list_comprehension,
    fix_long_mathtex,
    fix_arrange_right_long_thai,
]


# ============================================================================
# DETECTORS
# ============================================================================

import ast
import re
from dataclasses import dataclass, field


_THAI_RANGE = re.compile(r"[\u0E00-\u0E7F]")
_THAI_LONG = re.compile(r"[\u0E00-\u0E7F]{15,}")


@dataclass
class Violation:
    rule: str
    line: int
    snippet: str
    description: str


@dataclass
class ValidationResult:
    fixed_code: str
    violations: list[Violation] = field(default_factory=list)
    auto_fixes: list[str] = field(default_factory=list)

    @property
    def has_violations(self) -> bool:
        return len(self.violations) > 0

    def violation_summary(self) -> str:
        if not self.violations:
            return "No violations found."
        lines = ["RULE VIOLATIONS FOUND \u2014 \u0e41\u0e01\u0e49\u0e17\u0e38\u0e01\u0e02\u0e49\u0e2d\u0e15\u0e48\u0e2d\u0e44\u0e1b\u0e19\u0e35\u0e49:"]
        for i, v in enumerate(self.violations, 1):
            lines.append(
                f"{i}. [{v.rule}] \u0e1a\u0e23\u0e23\u0e17\u0e31\u0e14 {v.line}: {v.description}\n"
                f"   \u0e42\u0e04\u0e49\u0e14\u0e17\u0e35\u0e48\u0e1c\u0e34\u0e14: {v.snippet}"
            )
        return "\n".join(lines)


def detect_syntax_error(code: str) -> list[Violation]:
    try:
        ast.parse(code)
    except SyntaxError as exc:
        line = exc.lineno or 1
        return [Violation(
            rule="SYNTAX_ERROR",
            line=line,
            snippet=(exc.text or "").strip()[:120],
            description=f"{exc.msg} at line {line}",
        )]
    return []


def detect_undefined_variables(code: str) -> list[Violation]:
    return [
        Violation(rule="UNDEFINED_VARIABLE", line=lineno, snippet=name, description=desc)
        for lineno, name, desc in find_undefined_variables(code)
    ]


def _string_call_scan(code: str, tree: ast.Module, call_names: set[str]) -> list[tuple[ast.Call, str]]:
    """(call, RAW source content) for every matching call whose first arg is
    a plain string literal — skips dynamic content automatically. Uses the
    raw source slice (via Source), NOT ast.Constant.value: for a
    non-raw string containing a backslash sequence Python recognizes as an
    escape (e.g. Text('x \\frac{1}{2}') — \\f is a real escape, form-feed),
    `.value` would already be silently corrupted by the time we see it,
    which is exactly the kind of bug these detectors exist to catch. This
    mirrors the same reasoning as py."""
    src = Source(code)
    out = []
    for call in find_calls(tree, call_names):
        if not (call.args and isinstance(call.args[0], ast.Constant) and isinstance(call.args[0].value, str)):
            continue
        raw = src.text(call.args[0])
        try:
            _, _, content, _ = split_string_prefix_and_quote(raw)
        except ValueError:
            continue
        out.append((call, content))
    return out


def detect_thai_in_mathtex(code: str) -> list[Violation]:
    tree = safe_parse(code)
    if tree is None:
        return []
    violations = []
    for call, content in _string_call_scan(code, tree, {"MathTex", "Tex"}):
        if _THAI_RANGE.search(content):
            violations.append(Violation(
                rule="THAI_IN_MATHTEX",
                line=call.lineno,
                snippet=content[:80],
                description=(
                    "\u0e1e\u0e1a\u0e15\u0e31\u0e27\u0e2d\u0e31\u0e01\u0e29\u0e23\u0e20\u0e32\u0e29\u0e32\u0e44\u0e17\u0e22\u0e43\u0e19 MathTex()/Tex() \u2014 "
                    "\u0e15\u0e49\u0e2d\u0e07\u0e41\u0e22\u0e01\u0e02\u0e49\u0e2d\u0e04\u0e27\u0e32\u0e21\u0e44\u0e17\u0e22\u0e2d\u0e2d\u0e01\u0e40\u0e1b\u0e47\u0e19 Text() \u0e41\u0e25\u0e49\u0e27\u0e43\u0e0a\u0e49 VGroup \u0e08\u0e31\u0e14\u0e27\u0e32\u0e07"
                ),
            ))
    return violations


def detect_thai_in_mathrm(code: str) -> list[Violation]:
    tree = safe_parse(code)
    if tree is None:
        return []
    violations = []
    mathrm_pattern = re.compile(r"\\mathrm\{([^}]*)\}")
    for call, content in _string_call_scan(code, tree, {"MathTex", "Tex"}):
        for m in mathrm_pattern.finditer(content):
            if _THAI_RANGE.search(m.group(1)):
                violations.append(Violation(
                    rule="THAI_IN_MATHRM",
                    line=call.lineno,
                    snippet=content[:80],
                    description=f"\u0e1e\u0e1a\u0e20\u0e32\u0e29\u0e32\u0e44\u0e17\u0e22\u0e43\u0e19 \\mathrm{{{m.group(1)[:20]}}} \u2014 \u0e15\u0e49\u0e2d\u0e07\u0e41\u0e22\u0e01\u0e2d\u0e2d\u0e01\u0e40\u0e1b\u0e47\u0e19 Text()",
                ))
    return violations


def detect_latex_in_text(code: str) -> list[Violation]:
    tree = safe_parse(code)
    if tree is None:
        return []
    violations = []
    complex_latex = re.compile(r"\\(frac|sqrt|sum|int|prod|lim|partial)\b|\\[(\[]")
    for call, content in _string_call_scan(code, tree, {"Text"}):
        if complex_latex.search(content):
            violations.append(Violation(
                rule="LATEX_IN_TEXT",
                line=call.lineno,
                snippet=content[:80],
                description=(
                    "\u0e1e\u0e1a LaTeX syntax \u0e0b\u0e31\u0e1a\u0e0b\u0e49\u0e2d\u0e19 (\\frac, \\sqrt \u0e2f\u0e25\u0e2f) \u0e43\u0e19 Text() \u2014 "
                    "\u0e15\u0e49\u0e2d\u0e07\u0e41\u0e22\u0e01\u0e40\u0e1b\u0e47\u0e19 VGroup(Text('...'), MathTex(r'...')) \u0e41\u0e17\u0e19"
                ),
            ))
    return violations


def detect_move_to_scalar(code: str) -> list[Violation]:
    """Safety net for fix_move_to_scalar — should rarely fire since the
    fixer runs first, but catches any zone-scalar-var name not in that
    fixer's known list."""
    tree = safe_parse(code)
    if tree is None:
        return []
    violations = []
    zone_suffixes = ("_y", "_bottom", "_top", "_center_y")
    for node in ast.walk(tree):
        if (
            isinstance(node, ast.Call)
            and isinstance(node.func, ast.Attribute)
            and node.func.attr == "move_to"
            and len(node.args) == 1
            and isinstance(node.args[0], ast.Name)
        ):
            name = node.args[0].id
            if name in ("ORIGIN", "UP", "DOWN", "LEFT", "RIGHT", "UR", "UL", "DR", "DL"):
                continue
            if any(name.endswith(suf) for suf in zone_suffixes):
                violations.append(Violation(
                    rule="MOVE_TO_SCALAR",
                    line=node.lineno,
                    snippet=f".move_to({name})",
                    description=f".move_to({name}) \u0e2a\u0e48\u0e07 scalar \u2192 \u0e15\u0e49\u0e2d\u0e07\u0e40\u0e1b\u0e47\u0e19 np.array([0, {name}, 0])",
                ))
    return violations


def detect_axes_too_large(code: str) -> list[Violation]:
    tree = safe_parse(code)
    if tree is None:
        return []
    violations = []
    for node in ast.walk(tree):
        if not isinstance(node, ast.keyword) or node.arg not in ("x_length", "y_length"):
            continue
        if not (isinstance(node.value, ast.Constant) and isinstance(node.value.value, (int, float))
                and not isinstance(node.value.value, bool)):
            continue
        limit = MAX_AXES_X_LENGTH if node.arg == "x_length" else MAX_AXES_Y_LENGTH
        val = node.value.value
        if val > limit:
            violations.append(Violation(
                rule="AXES_TOO_LARGE",
                line=node.value.lineno,
                snippet=f"{node.arg}={val}",
                description=f"{node.arg}={val} \u0e40\u0e01\u0e34\u0e19 {limit}",
            ))
    return violations


def detect_font_size_violations(code: str) -> list[Violation]:
    """Consolidated: was two contradictory detectors in the original
    (one flagging >30, one flagging >28, with a comment noting one was
    possibly unused) — now a single check matching the fixer's own limits
    exactly (MathTex/Tex > 20, Text > 28)."""
    tree = safe_parse(code)
    if tree is None:
        return []
    violations = []
    for call_names, limit, label in (
        ({"MathTex", "Tex"}, MAX_MATHTEX_FONT_SIZE, "MathTex()/Tex()"),
        ({"Text"}, MAX_TEXT_FONT_SIZE, "Text()"),
    ):
        for call in find_calls(tree, call_names):
            kw = get_keyword(call, "font_size")
            if kw is None or not isinstance(kw.value, ast.Constant):
                continue
            val = kw.value.value
            if isinstance(val, (int, float)) and not isinstance(val, bool) and val > limit:
                violations.append(Violation(
                    rule="FONT_SIZE_TOO_LARGE",
                    line=kw.value.lineno,
                    snippet=f"font_size={val}",
                    description=f"font_size={val} \u0e43\u0e19 {label} \u2014 \u0e15\u0e49\u0e2d\u0e07 \u2264 {limit}",
                ))
    return violations


def detect_overlapping_labels(code: str) -> list[Violation]:
    tree = safe_parse(code)
    if tree is None:
        return []
    placement: dict[tuple[str, str], list[int]] = {}
    for node in ast.walk(tree):
        if not (
            isinstance(node, ast.Call)
            and isinstance(node.func, ast.Attribute)
            and node.func.attr == "next_to"
            and len(node.args) >= 2
            and isinstance(node.args[0], ast.Name)
            and isinstance(node.args[1], ast.Name)
        ):
            continue
        ref, direction = node.args[0].id, node.args[1].id
        if direction not in ("UR", "UL", "DR", "DL", "UP", "DOWN", "LEFT", "RIGHT"):
            continue
        placement.setdefault((ref, direction), []).append(node.lineno)

    violations = []
    for (ref, direction), lines in placement.items():
        if len(lines) >= 3:
            violations.append(Violation(
                rule="OVERLAPPING_LABELS",
                line=lines[0],
                snippet=f"\u0e1a\u0e23\u0e23\u0e17\u0e31\u0e14 {lines}: .next_to({ref}, {direction}, ...)",
                description=(
                    f"\u0e21\u0e35 {len(lines)} labels \u0e17\u0e35\u0e48 .next_to({ref}, {direction}) "
                    f"\u0e17\u0e34\u0e28\u0e40\u0e14\u0e35\u0e22\u0e27\u0e01\u0e31\u0e19 \u2014 \u0e08\u0e30\u0e17\u0e31\u0e1a\u0e0b\u0e49\u0e2d\u0e19\u0e01\u0e31\u0e19 \u0e15\u0e49\u0e2d\u0e07\u0e01\u0e23\u0e30\u0e08\u0e32\u0e22\u0e17\u0e34\u0e28\u0e17\u0e32\u0e07"
                ),
            ))
    return violations


def detect_vgroup_list_comprehension(code: str) -> list[Violation]:
    """Safety net — should rarely fire since the fixer handles this
    structurally, but flags any VGroup(*[...]) shape the fixer's pattern
    match didn't recognize (e.g. more exotic comprehension forms)."""
    tree = safe_parse(code)
    if tree is None:
        return []
    violations = []
    for node in ast.walk(tree):
        if (
            isinstance(node, ast.Call)
            and isinstance(node.func, ast.Name)
            and node.func.id == "VGroup"
            and len(node.args) == 1
            and isinstance(node.args[0], ast.Starred)
            and isinstance(node.args[0].value, ast.ListComp)
        ):
            violations.append(Violation(
                rule="VGROUP_LIST_COMPREHENSION",
                line=node.lineno,
                snippet="VGroup(*[...])",
                description="\u0e1e\u0e1a VGroup(*[...]) \u0e17\u0e35\u0e48\u0e2b\u0e25\u0e07\u0e40\u0e2b\u0e25\u0e37\u0e2d\u0e2b\u0e25\u0e31\u0e07 auto-fix \u2014 \u0e15\u0e49\u0e2d\u0e07\u0e40\u0e02\u0e35\u0e22\u0e19 Text() \u0e41\u0e22\u0e01\u0e40\u0e1b\u0e47\u0e19 argument \u0e15\u0e23\u0e07\u0e46 \u0e02\u0e2d\u0e07 VGroup()",
            ))
    return violations


def detect_unbalanced_latex_braces(code: str) -> list[Violation]:
    tree = safe_parse(code)
    if tree is None:
        return []
    violations = []
    for call, content in _string_call_scan(code, tree, {"MathTex", "Tex"}):
        opens, closes = content.count("{"), content.count("}")
        if opens != closes:
            violations.append(Violation(
                rule="UNBALANCED_LATEX_BRACES",
                line=call.lineno,
                snippet=content[:80],
                description=f"\u0e27\u0e07\u0e40\u0e25\u0e47\u0e1a\u0e1b\u0e35\u0e01\u0e01\u0e32 LaTeX \u0e44\u0e21\u0e48\u0e2a\u0e21\u0e14\u0e38\u0e25: {opens} \u0e40\u0e1b\u0e34\u0e14 \u0e41\u0e15\u0e48 {closes} \u0e1b\u0e34\u0e14",
            ))
    return violations


def detect_math_errors(code: str) -> list[Violation]:
    tree = safe_parse(code)
    if tree is None:
        return []
    violations = []
    for call, content in _string_call_scan(code, tree, {"MathTex"}):
        if "\\equiv" in content:
            violations.append(Violation(
                rule="MATH_EQUIV_INCORRECT",
                line=call.lineno,
                snippet=content[:80],
                description="\u0e1e\u0e1a \\equiv \u0e43\u0e19\u0e2a\u0e21\u0e01\u0e32\u0e23 \u2014 \u0e04\u0e27\u0e23\u0e43\u0e0a\u0e49 = \u0e41\u0e17\u0e19 \\equiv",
            ))
    return violations


def detect_missing_scaling(code: str) -> list[Violation]:
    tree = safe_parse(code)
    if tree is None:
        return []
    violations = []
    for node in ast.walk(tree):
        if not (
            isinstance(node, ast.Assign)
            and len(node.targets) == 1
            and isinstance(node.targets[0], ast.Name)
            and isinstance(node.value, ast.Call)
            and isinstance(node.value.func, ast.Name)
            and node.value.func.id == "VGroup"
        ):
            continue
        var_name = node.targets[0].id
        if "axes" in var_name.lower():
            continue
        found_scale = False
        found_move_to_zone = False
        for later in ast.walk(tree):
            if not (
                isinstance(later, ast.Call)
                and isinstance(later.func, ast.Attribute)
                and isinstance(later.func.value, ast.Name)
                and later.func.value.id == var_name
            ):
                continue
            if later.lineno < node.lineno:
                continue
            if later.func.attr in ("scale_to_fit_width", "scale_to_fit_height"):
                found_scale = True
                break
            if later.func.attr == "move_to" and later.args and isinstance(later.args[0], ast.Name) \
                    and later.args[0].id in ("bottom_center", "middle_center"):
                found_move_to_zone = True
        if found_move_to_zone and not found_scale:
            violations.append(Violation(
                rule="MISSING_SCALING",
                line=node.lineno,
                snippet=f"{var_name} = VGroup(...)",
                description=(
                    f"\u0e1e\u0e1a VGroup '{var_name}' \u0e40\u0e04\u0e25\u0e37\u0e48\u0e2d\u0e19\u0e44\u0e1b\u0e01\u0e25\u0e32\u0e07/\u0e25\u0e48\u0e32\u0e07 (move_to) "
                    "\u0e41\u0e15\u0e48\u0e44\u0e21\u0e48\u0e1e\u0e1a\u0e01\u0e32\u0e23 .scale_to_fit_width() \u0e01\u0e48\u0e2d\u0e19\u0e2b\u0e19\u0e49\u0e32\u0e19\u0e31\u0e49\u0e19 \u2014 "
                    "\u0e2d\u0e32\u0e08\u0e17\u0e33\u0e43\u0e2b\u0e49\u0e40\u0e19\u0e37\u0e49\u0e2d\u0e2b\u0e32\u0e25\u0e49\u0e19\u0e08\u0e2d "
                    "\u0e41\u0e01\u0e49\u0e42\u0e14\u0e22\u0e40\u0e1e\u0e34\u0e48\u0e21 scaling"
                ),
            ))
    return violations


def detect_text_overflow(code: str) -> list[Violation]:
    """Improved estimate (feedback item 7): differentiate Thai vs Latin
    character width instead of a flat len()*0.55 estimate, and measure
    each line of a multi-line string separately rather than the whole
    string at once."""
    tree = safe_parse(code)
    if tree is None:
        return []
    max_width = 9.0 * 0.88  # frame_width * 0.88, matches prompts.py clamp target
    violations = []
    for call, content in _string_call_scan(code, tree, {"Text"}):
        kw = get_keyword(call, "font_size")
        if kw is None or not isinstance(kw.value, ast.Constant):
            continue
        font_size = kw.value.value
        if not isinstance(font_size, (int, float)) or isinstance(font_size, bool):
            continue
        for line in (content.splitlines() or [content]):
            thai_chars = sum(1 for c in line if "\u0E00" <= c <= "\u0E7F")
            latin_chars = len(line) - thai_chars
            estimated_width = font_size * (thai_chars * 0.048 + latin_chars * 0.055)
            if estimated_width > max_width:
                violations.append(Violation(
                    rule="TEXT_OVERFLOW",
                    line=call.lineno,
                    snippet=line[:60],
                    description=(
                        f"Text '{line[:20]}...' (font_size={font_size}) "
                        f"\u0e04\u0e32\u0e14\u0e27\u0e48\u0e32\u0e08\u0e30\u0e22\u0e32\u0e27\u0e40\u0e01\u0e34\u0e19\u0e01\u0e23\u0e2d\u0e1a\u0e08\u0e2d "
                        f"(~{estimated_width:.1f} > {max_width:.1f}) \u2014 "
                        "\u0e43\u0e2b\u0e49\u0e41\u0e1a\u0e48\u0e07\u0e40\u0e1b\u0e47\u0e19\u0e2b\u0e25\u0e32\u0e22\u0e1a\u0e23\u0e23\u0e17\u0e31\u0e14\u0e43\u0e19 VGroup "
                        "\u0e2b\u0e23\u0e37\u0e2d\u0e2b\u0e48\u0e2d\u0e14\u0e49\u0e27\u0e22 .scale_to_fit_width()"
                    ),
                ))
    return violations


def detect_bottom_zone_empty(code: str) -> list[Violation]:
    """AST-based: any VGroup(...).move_to(bottom_center) call anywhere in
    the file means the bottom zone has content. Only flags when the file
    has substantial Text/MathTex/VGroup content overall but genuinely none
    of it ever reaches the bottom zone."""
    tree = safe_parse(code)
    if tree is None:
        return []
    for node in ast.walk(tree):
        if (
            isinstance(node, ast.Call)
            and isinstance(node.func, ast.Attribute)
            and node.func.attr == "move_to"
            and node.args
            and isinstance(node.args[0], ast.Name)
            and node.args[0].id == "bottom_center"
        ):
            return []  # bottom zone has content somewhere — fine

    has_content = any(
        isinstance(n, ast.Call) and isinstance(n.func, ast.Name)
        and n.func.id in ("Text", "MathTex", "VGroup")
        for n in ast.walk(tree)
    )
    if not has_content:
        return []
    return [Violation(
        rule="BOTTOM_ZONE_EMPTY",
        line=1,
        snippet="construct()",
        description="\u0e44\u0e21\u0e48\u0e1e\u0e1a\u0e40\u0e19\u0e37\u0e49\u0e2d\u0e2b\u0e32\u0e43\u0e19\u0e42\u0e0b\u0e19\u0e25\u0e48\u0e32\u0e07 \u2014 \u0e15\u0e23\u0e27\u0e08\u0e2a\u0e2d\u0e1a\u0e27\u0e48\u0e32\u0e21\u0e35 VGroup(...).move_to(bottom_center) \u0e2b\u0e23\u0e37\u0e2d\u0e44\u0e21\u0e48",
    )]


ALL_DETECTORS = [
    detect_undefined_variables,
    detect_thai_in_mathtex,
    detect_thai_in_mathrm,
    detect_latex_in_text,
    detect_move_to_scalar,
    detect_axes_too_large,
    detect_font_size_violations,
    detect_overlapping_labels,
    detect_vgroup_list_comprehension,
    detect_unbalanced_latex_braces,
    detect_math_errors,
    detect_missing_scaling,
    detect_text_overflow,
    detect_bottom_zone_empty,
]


# ============================================================================
# ORCHESTRATION
# ============================================================================

def preprocess_code(code_string: str) -> ValidationResult:
    """
    Run all auto-fixes and violation checks on Gemini-generated Manim code.

    Order:
      1. Phase 1a — token-level fixes (syntax-error tolerant; these run even
         if the code doesn't parse, since tokenizing is more lenient than
         full grammar validation).
      2. Phase 1b/1c/1d — AST-based fixes. Each individually calls
         safe_parse() and no-ops on unparseable code, so a syntax
         error anywhere doesn't crash the pipeline — it just means these
         phases can't do anything until Phase 2 reports the syntax error
         back to Gemini for a rewrite.
      3. Phase 2 — detect remaining violations, starting with an explicit
         syntax-error check. If the code doesn't parse at all, we report
         ONLY that (matching the old behavior of short-circuiting further
         AST-dependent checks, but now as an explicit, actionable
         violation instead of a silent skip).
    """
    auto_fixes: list[str] = []
    code = code_string

    # ── Phase 1a: token-level (syntax-tolerant) ─────────────────────────
    for fixer in TOKEN_LEVEL_FIXERS:
        code = fixer(code, auto_fixes)

    # ── Phase 1b: AST-based structural/keyword fixes ────────────────────
    for fixer in PHASE_1B_FIXERS:
        code = fixer(code, auto_fixes)

    # ── Phase 1c: string CONTENT fixes (MathTex/Tex/Text) ───────────────
    code = fix_string_contents(code, auto_fixes)

    # ── Phase 1d: structural rewrites needing correct indentation ───────
    for fixer in PHASE_1D_FIXERS:
        code = fixer(code, auto_fixes)

    # ── Phase 2: detect remaining violations ────────────────────────────
    syntax_violations = detect_syntax_error(code)
    if syntax_violations:
        # Same short-circuit the original had (its undefined-variable
        # detector silently caught SyntaxError and returned early) — now
        # explicit and reported as its own actionable violation instead of
        # just silently skipping the rest.
        return ValidationResult(fixed_code=code, violations=syntax_violations, auto_fixes=auto_fixes)

    violations: list[Violation] = []
    for detector in ALL_DETECTORS:
        violations.extend(detector(code))

    return ValidationResult(fixed_code=code, violations=violations, auto_fixes=auto_fixes)


def validate_episode_count(lesson_json: dict, expected_min: int | None = None) -> tuple[bool, str]:
    declared = lesson_json.get("total_episodes", 0)
    actual = len(lesson_json.get("episodes", []))
    if declared != actual:
        return False, f"total_episodes={declared} but episodes array has {actual} items."
    if expected_min and actual < expected_min:
        return False, f"Only {actual} episode(s) generated but expected at least {expected_min}."
    return True, "ok"