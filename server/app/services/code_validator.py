"""
server/app/services/code_validator.py

Deterministic pre-processor for Gemini-generated Manim code.
Runs BEFORE the render attempt and BEFORE the Gemini retry loop.

PHILOSOPHY: Fix as much as possible deterministically so Gemini retries
are only needed for structural rewrites, not trivial pattern fixes.

Two-phase approach:
  Phase 1 — Auto-fix: patterns we can correct safely without LLM help
  Phase 2 — Violation report: things that need LLM rewrite

NOTE ON APPROACH: most fixers below are still regex/text based rather than
fully AST/token based. That is a known limitation (a global text
substitution can in principle touch a comment or an unrelated string) and
the long-term recommendation is to migrate the highest-risk fixers to
AST/tokenize-based rewrites and to split this module into
models.py / syntax.py / autofix.py / detectors.py / validator.py. This
revision tightens the highest-risk spots (NumPy import insertion,
indentation-safety of generated blocks, comment/string-safety of the
`.replace()`-based renames, scope-aware undefined-variable detection,
explicit syntax-error detection, and a font-size threshold conflict)
without rewriting every fixer, so it stays a drop-in replacement for the
existing call sites.
"""

import re
import ast
import io
import tokenize
import builtins as _builtins_module
from dataclasses import dataclass, field


# ─────────────────────────────────────────────────────────────────────────────
# Shared constants — single source of truth for font-size clamping so the
# auto-fixer and the detector can never disagree with each other again.
# ─────────────────────────────────────────────────────────────────────────────
MAX_TEXT_FONT_SIZE = 28
MAX_MATHTEX_FONT_SIZE = 20


def _safe_identifier_replace(code: str, old: str, new: str) -> tuple[str, int]:
    """
    Replace bare-word occurrences of `old` with `new`, skipping any
    occurrence that falls inside a comment or a string literal.

    This is the token-aware alternative to `code.replace(old, new)` for
    renames like `ShowCreation(` -> `Create(`: a plain `.replace()` will
    happily rewrite text inside a `# comment` or inside an unrelated
    string such as "Use ShowCreation(...)", silently corrupting content
    that was never meant to be touched. Tokenizing lets us only rewrite
    NAME tokens that are actual Python identifiers in code.

    Falls back to a plain string replace if the source doesn't tokenize
    (e.g. it's already broken); an auto-fixer should never be the thing
    that turns fixable code into a hard failure.

    Returns (new_code, num_replacements).
    """
    old_name = old.rstrip("(")
    try:
        tokens = list(tokenize.generate_tokens(io.StringIO(code).readline))
    except (tokenize.TokenizeError, IndentationError, SyntaxError):
        count = code.count(old)
        return code.replace(old, new), count

    count = 0
    out_tokens = []
    for tok in tokens:
        if tok.type == tokenize.NAME and tok.string == old_name:
            count += 1
            out_tokens.append(tok._replace(string=new.rstrip("(")))
        else:
            out_tokens.append(tok)

    if count == 0:
        return code, 0

    try:
        new_code = tokenize.untokenize(out_tokens)
    except Exception:
        # untokenize can be finicky about exact whitespace round-tripping;
        # if it fails, don't risk corrupting the file — fall back to the
        # plain (less safe, but at least predictable) string replace.
        return code.replace(old, new), code.count(old)

    return new_code, count


# ─────────────────────────────────────────────────────────────────────────────
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
        lines = ["RULE VIOLATIONS FOUND — แก้ทุกข้อต่อไปนี้:"]
        for i, v in enumerate(self.violations, 1):
            lines.append(
                f"{i}. [{v.rule}] บรรทัด {v.line}: {v.description}\n"
                f"   โค้ดที่ผิด: {v.snippet}"
            )
        return "\n".join(lines)


# ─────────────────────────────────────────────────────────────────────────────
# Phase 1 helpers — expanded auto-fixers
# ─────────────────────────────────────────────────────────────────────────────

def _fix_bottom_zone_bottom(code: str, fixes: list[str]) -> str:
    pattern = re.compile(
        r'bottom_center\s*=\s*np\.array\(\[0,\s*bottom_zone_bottom\s*,\s*0\]\)'
    )
    if pattern.search(code):
        fixes.append("AUTO-FIX: bottom_center used bottom_zone_bottom → bottom_zone_center_y")
        code = pattern.sub('bottom_center = np.array([0, bottom_zone_center_y, 0])', code)
    return code


def _fix_include_numbers_in_axis_config(code: str, fixes: list[str]) -> str:
    lines = code.splitlines()
    in_axis_config = False
    result_lines = []
    for line in lines:
        if re.search(r'\baxis_config\s*=\s*\{', line) and not re.search(r'[xy]_axis_config', line):
            in_axis_config = True
        if in_axis_config:
            if '}' in line:
                in_axis_config = False
            if re.search(r"'include_numbers'\s*:", line):
                fixes.append(f"AUTO-FIX: Removed 'include_numbers' from axis_config: {line.strip()}")
                continue
        result_lines.append(line)
    return '\n'.join(result_lines)


def _fix_text_in_mathtex(code: str, fixes: list[str]) -> str:
    pattern = re.compile(r'\\\\text\{([^}]*)\}')
    def replacer(m):
        content = m.group(1)
        if all(ord(c) < 128 for c in content):
            fixes.append(f"AUTO-FIX: \\text{{{content}}} → \\mathrm{{{content}}}")
            return f'\\\\mathrm{{{content}}}'
        return m.group(0)
    return pattern.sub(replacer, code)


def _fix_single_backslash_lambda(code: str, fixes: list[str]) -> str:
    dangerous_sequences = {
        r'\lambda': r'\\lambda', r'\Lambda': r'\\Lambda',
        r'\frac': r'\\frac', r'\phi': r'\\phi', r'\Phi': r'\\Phi',
        r'\Delta': r'\\Delta', r'\delta': r'\\delta',
        r'\theta': r'\\theta', r'\Theta': r'\\Theta',
        r'\pi': r'\\pi', r'\Pi': r'\\Pi',
        r'\mathrm': r'\\mathrm', r'\mathbf': r'\\mathbf',
        r'\cdot': r'\\cdot', r'\times': r'\\times',
        r'\sqrt': r'\\sqrt', r'\approx': r'\\approx',
        r'\circ': r'\\circ', r'\alpha': r'\\alpha',
        r'\beta': r'\\beta', r'\gamma': r'\\gamma', r'\Gamma': r'\\Gamma',
        r'\sigma': r'\\sigma', r'\omega': r'\\omega', r'\Omega': r'\\Omega',
        r'\mu': r'\\mu', r'\nu': r'\\nu',
        r'\vec': r'\\vec', r'\hat': r'\\hat',
        r'\pm': r'\\pm', r'\leq': r'\\leq', r'\geq': r'\\geq', r'\neq': r'\\neq',
        r'\,': r'\\,', r'\;': r'\\;', r'\!': r'\\!',
    }
    pattern = re.compile(r"(MathTex|Tex)\s*\(\s*(f)?'([^']*)'")
    def replacer(m):
        call, f_prefix, content = m.group(1), m.group(2) or '', m.group(3)
        original = content
        for bad, good in dangerous_sequences.items():
            if bad in content:
                content = content.replace(bad, good)
        if content != original:
            fixes.append(f"AUTO-FIX: Fixed backslash escapes in {call}({f_prefix}'{original[:40]}...')")
        return f"{call}({f_prefix}'{content}'"
    return pattern.sub(replacer, code)


def _fix_long_mathtex(code: str, fixes: list[str]) -> str:
    """
    Split MathTex with > 40 chars into a VGroup of multiple MathTex lines.
    Splits at '=', '\approx', or after a comma, whichever comes first.
    Preserves exact Python indentation of the replaced line.
    """
    pattern = re.compile(
        r'^(\s*)(\w+)\s*=\s*MathTex\s*\(\s*r\'(.*?)\'\s*(?:,\s*[^)]*)?\)',
        re.MULTILINE
    )
    def replacer(m):
        indent, var, content = m.group(1), m.group(2), m.group(3)
        if len(content) <= 40:
            return m.group(0)
        # Try to split at first '=' or '\approx' that is not inside braces
        depth = 0
        split_idx = None
        for i, ch in enumerate(content):
            if ch == '{':
                depth += 1
            elif ch == '}':
                depth -= 1
            if depth == 0 and ch == '=':
                split_idx = i
                break
        if split_idx is None:
            # fallback: split at last comma
            split_idx = content.rfind(',')
            if split_idx == -1:
                return m.group(0)  # no safe split
        first = content[:split_idx+1].strip()
        second = content[split_idx+1:].strip()
        if not first or not second:
            return m.group(0)
        fixes.append(f"AUTO-FIX: Split long MathTex '{content[:40]}...' into two lines")
        return (
            f"{indent}{var} = VGroup(\n"
            f"{indent}    MathTex(r'{first}', font_size=26),\n"
            f"{indent}    MathTex(r'{second}', font_size=26),\n"
            f"{indent}).arrange(DOWN, aligned_edge=LEFT, buff=0.15)\n"
            f"{indent}{var}.scale_to_fit_width(frame_width * 0.88)"
        )
    return pattern.sub(replacer, code)


def _fix_over_escaped_latex(code: str, fixes: list[str]) -> str:
    """
    Collapse over-escaped LaTeX commands inside MathTex(r'...')/Tex(r'...') calls.

    ROOT CAUSE: MathTex(r'...') is a raw string. Raw strings do NOT collapse
    '\\\\' down to '\\' the way a normal Python string does -- every backslash
    character written in the source survives unchanged into the runtime string.
    So if the source line contains r'...\\frac...' (two literal backslash
    characters), LaTeX receives '\\frac' verbatim. LaTeX reads two backslashes
    as a line-break control symbol ('\\') followed by ordinary text, so the
    rest of the command ('frac{...}') prints as literal garbled text instead
    of being interpreted as a command. This is the cause of text like
    "mathrm{m/s}" appearing verbatim in rendered videos instead of rendering
    as a fraction/unit.

    This auto-fixer finds MathTex(r'...')/Tex(r'...') calls and collapses any
    run of 2+ backslashes immediately before a known LaTeX command name (or
    spacing command like \\, \\; \\!) down to exactly one backslash. It runs
    regardless of what the LLM was told to do, so it catches the bug even if
    the generation prompt is ever wrong again.
    """
    known_commands = [
        'frac', 'sqrt', 'lambda', 'Lambda', 'phi', 'Phi', 'theta', 'Theta',
        'Delta', 'delta', 'pi', 'Pi', 'mathrm', 'mathbf', 'cdot', 'times',
        'approx', 'circ', 'alpha', 'beta', 'gamma', 'Gamma', 'sigma', 'Sigma',
        'omega', 'Omega', 'mu', 'nu', 'epsilon', 'rho', 'tau', 'chi', 'psi',
        'eta', 'xi', 'zeta', 'vec', 'hat', 'pm', 'leq', 'geq', 'neq',
        'Rightarrow', 'rightarrow', 'Leftarrow', 'leftarrow', 'quad', 'qquad',
        'left', 'right', 'infty', 'sum', 'int', 'partial', 'equiv', 'propto',
    ]
    cmd_alt = '|'.join(known_commands)
    # Matches a run of 2+ literal backslash characters immediately followed by
    # a known command name (word boundary) OR by one of the spacing commands.
    double_bs_pattern = re.compile(rf'\\{{2,}}(?=(?:{cmd_alt})\b|[,;!])')

    pattern = re.compile(r"((?:MathTex|Tex)\s*\(\s*r')([^']*)(')")

    def replacer(m):
        prefix, content, suffix = m.group(1), m.group(2), m.group(3)
        new_content = double_bs_pattern.sub(r'\\', content)
        if new_content != content:
            fixes.append(
                "AUTO-FIX: Collapsed over-escaped LaTeX backslash(es) in "
                f"{prefix.strip()}'{content[:50]}...' -> '{new_content[:50]}...'"
            )
        return prefix + new_content + suffix

    return pattern.sub(replacer, code)


def _fix_vgroup_list_comprehension(code: str, fixes: list[str]) -> str:
    """
    Auto-fix VGroup(*[Text(line, ...) for line in ['a', 'b', 'c']]) →
    VGroup(Text('a', ...), Text('b', ...), Text('c', ...))
    """
    pattern = re.compile(
        r'VGroup\s*\(\s*\*\s*\[\s*'
        r'(\w+)\s*\(([\w_]+)\s*,\s*([^]]+?)\)'
        r'\s*for\s+(\w+)\s+in\s+\[([^\]]+)\]'
        r'\s*\]\s*\)',
        re.DOTALL
    )
    
    def replacer(m):
        ctor = m.group(1)
        kwargs_str = m.group(3).strip()
        items_str = m.group(5)

        items = re.findall(r"'([^']*)'|\"([^\"]*)\"", items_str)
        strings = [a or b for a, b in items]

        if not strings:
            return m.group(0)

        # Preserve the indentation of the line the match starts on, instead
        # of hard-coding 12/8-space indents. Hard-coded indentation produces
        # invalid Python whenever this expression sits inside a method,
        # conditional, or another nested block with different indentation.
        line_start = code.rfind('\n', 0, m.start()) + 1
        indent = re.match(r'[ \t]*', code[line_start:m.start()]).group(0)
        inner_indent = indent + '    '

        parts = [f"{ctor}('{s}', {kwargs_str})" for s in strings]
        result = (
            'VGroup(\n'
            + ',\n'.join(f'{inner_indent}{p}' for p in parts)
            + f'\n{indent})'
        )
        fixes.append(
            f"AUTO-FIX: Expanded VGroup(*[{ctor}(var, ...) for var in [...]]) "
            f"→ VGroup({ctor}(...), ...) with {len(strings)} items (indentation preserved)"
        )
        return result
    
    new_code = pattern.sub(replacer, code)
    
    var_list_pattern = re.compile(
        r'(\w+)\s*=\s*\[\s*\n?((?:\s*\'[^\']*\',?\s*\n?)+)\s*\]',
        re.DOTALL
    )
    
    comprehension_pattern = re.compile(
        r'VGroup\s*\(\s*\*\s*\[\s*\n?\s*'
        r'(\w+)\s*\(\s*(\w+)\s*,\s*([^]]+?)\)\s*\n?\s*'
        r'for\s+(\w+)\s+in\s+(\w+)\s*'
        r'\]\s*\)',
        re.DOTALL
    )
    
    list_vars = {}
    for vm in var_list_pattern.finditer(new_code):
        var_name = vm.group(1)
        items_block = vm.group(2)
        strings = re.findall(r"'([^']*)'", items_block)
        if strings:
            list_vars[var_name] = strings
    
    def comprehension_replacer(m):
        ctor = m.group(1)
        kwargs_str = m.group(3).strip()
        list_name = m.group(5)

        if list_name not in list_vars:
            return m.group(0)

        strings = list_vars[list_name]

        line_start = new_code.rfind('\n', 0, m.start()) + 1
        indent = re.match(r'[ \t]*', new_code[line_start:m.start()]).group(0)
        inner_indent = indent + '    '

        parts = [f"{ctor}('{s}', {kwargs_str})" for s in strings]
        result = (
            'VGroup(\n'
            + ',\n'.join(f'{inner_indent}{p}' for p in parts)
            + f'\n{indent})'
        )
        fixes.append(
            f"AUTO-FIX: Resolved VGroup(*[{ctor}(line, ...) for line in {list_name}]) "
            f"→ VGroup({ctor}(...), ...) with {len(strings)} items (indentation preserved)"
        )
        return result
    
    new_code = comprehension_pattern.sub(comprehension_replacer, new_code)
    return new_code


def _fix_latex_in_text_calls(code: str, fixes: list[str]) -> str:
    """
    Auto-fix Text('...\\lambda...') patterns by replacing with unicode.
    """
    latex_to_unicode = {
        r'\\lambda': 'λ',
        r'\\Lambda': 'Λ',
        r'\\phi': 'φ',
        r'\\Phi': 'Φ',
        r'\\theta': 'θ',
        r'\\Theta': 'Θ',
        r'\\alpha': 'α',
        r'\\beta': 'β',
        r'\\gamma': 'γ',
        r'\\Gamma': 'Γ',
        r'\\delta': 'δ',
        r'\\Delta': 'Δ',
        r'\\pi': 'π',
        r'\\Pi': 'Π',
        r'\\sigma': 'σ',
        r'\\omega': 'ω',
        r'\\Omega': 'Ω',
        r'\\mu': 'μ',
        r'\\nu': 'ν',
        r'\\epsilon': 'ε',
        r'\\rho': 'ρ',
        r'\\tau': 'τ',
        r'\\chi': 'χ',
        r'\\psi': 'ψ',
        r'\\eta': 'η',
        r'\\xi': 'ξ',
        r'\\zeta': 'ζ',
        r'\\vec': '',
        r'\\hat': '',
        r'\\frac': '/',
        r'\\cdot': '·',
        r'\\times': '×',
        r'\\pm': '±',
        r'\\leq': '≤',
        r'\\geq': '≥',
        r'\\neq': '≠',
        r'\\approx': '≈',
        r'\\sqrt': '√',
        r'\\circ': '°',
        r'\\infty': '∞',
        r'\\mathrm': '',
        r'\\mathbf': '',
    }
    
    lines = code.splitlines()
    result_lines = []
    
    for line in lines:
        if 'Text(' in line and '\\\\' in line:
            text_pattern = re.compile(r"(Text\s*\(\s*')((?:[^'\\]|\\.)*)(')")
            
            def text_replacer(m):
                prefix = m.group(1)
                content = m.group(2)
                suffix = m.group(3)
                
                original_content = content
                modified = False
                
                for latex, uni in latex_to_unicode.items():
                    if latex + '{' in content:
                        brace_pat = re.compile(re.escape(latex) + r'\{([^}]*)\}')
                        content = brace_pat.sub(r'\1', content)
                        modified = True
                    elif latex in content:
                        content = content.replace(latex, uni)
                        modified = True
                
                content = re.sub(r'\{([^}]*)\}', r'\1', content)
                
                if modified:
                    fixes.append(
                        f"AUTO-FIX: Replaced LaTeX symbols with unicode in Text('{original_content[:40]}...')"
                    )
                
                return prefix + content + suffix
            
            line = text_pattern.sub(text_replacer, line)
        
        result_lines.append(line)
    
    return '\n'.join(result_lines)


def _fix_thai_in_mathrm(code: str, fixes: list[str]) -> str:
    """Auto-fix \\mathrm{ภาษาไทย} by removing Thai chars."""
    thai_range = re.compile(r'[\u0E00-\u0E7F]')
    mathrm_with_thai = re.compile(r'\\\\?mathrm\{([^}]*[\u0E00-\u0E7F][^}]*)\}')
    
    def replacer(m):
        content = m.group(1)
        ascii_content = ''.join(c for c in content if ord(c) < 128)
        if ascii_content.strip():
            fixes.append(f"AUTO-FIX: \\mathrm{{{content[:20]}}} - removed Thai chars, kept ASCII")
            return f'\\\\mathrm{{{ascii_content}}}'
        else:
            fixes.append(f"AUTO-FIX: \\mathrm{{{content[:20]}}} - all Thai, removed \\mathrm wrapper")
            return content
    
    return mathrm_with_thai.sub(replacer, code)


def _fix_step_title_latex(code: str, fixes: list[str]) -> str:
    """Fix LaTeX symbols in Text() step titles."""
    double_bs_symbols = {
        r'(\\\\lambda)': 'λ',
        r'(\\\\phi)': 'φ',
        r'(\\\\phi_': 'φ_',
        r'(\\\\theta)': 'θ',
        r'(\\\\alpha)': 'α',
        r'(\\\\beta)': 'β',
        r'(\\\\gamma)': 'γ',
        r'(\\\\delta)': 'δ',
        r'(\\\\Delta)': 'Δ',
        r'(\\\\pi)': 'π',
        r'(\\\\omega)': 'ω',
        r'(\\\\mu)': 'μ',
        r'(\\\\sigma)': 'σ',
        r'(\\\\nu)': 'ν',
    }
    
    lines = code.splitlines()
    result_lines = []
    
    for line in lines:
        if 'Text(' in line:
            for pattern, replacement in double_bs_symbols.items():
                if '\\\\' in line and pattern.replace('(', '').replace(')', '') in line:
                    def make_replacer(rep):
                        def replacer(m):
                            inner = m.group(0)
                            pat = pattern.replace('(', r'\(').replace(')', r'\)')
                            new_inner = re.sub(pat, rep, inner)
                            if new_inner != inner:
                                fixes.append(f"AUTO-FIX: Replaced {pattern} with {rep} in Text()")
                            return new_inner
                        return replacer
                    
                    text_pattern = re.compile(r"Text\s*\('[^']*'")
                    line = text_pattern.sub(make_replacer(replacement), line)
        
        result_lines.append(line)
    
    return '\n'.join(result_lines)


def _fix_latex_escape_in_text(code: str, fixes: list[str]) -> str:
    """Remove LaTeX \\( \\) from Text() calls as last resort."""
    pattern = re.compile(r'\\\\?\(\\\\?([a-zA-Z]+)\\\\?\)')
    def replacer(m):
        name = m.group(1)
        fixes.append(f"AUTO-FIX: Removed LaTeX \\({name}\\) from Text() call")
        return f'({name})'
    return pattern.sub(replacer, code)


def _fix_move_to_scalar(code: str, fixes: list[str]) -> str:
    """Auto-fix .move_to(scalar_var) → .move_to(np.array([0, scalar_var, 0]))."""
    zone_vars = [
        'bottom_zone_center_y', 'middle_zone_center_y', 'top_zone_center_y',
        'bottom_zone_bottom', 'bottom_zone_top',
        'middle_zone_bottom', 'middle_zone_top',
        'top_zone_bottom', 'top_zone_top',
    ]
    
    for var in zone_vars:
        pattern = re.compile(rf'\.move_to\(\s*{re.escape(var)}\s*\)')
        if pattern.search(code):
            fixes.append(f"AUTO-FIX: .move_to({var}) → .move_to(np.array([0, {var}, 0]))")
            code = pattern.sub(f'.move_to(np.array([0, {var}, 0]))', code)
    
    return code


def _fix_axes_too_large(code: str, fixes: list[str]) -> str:
    """Clamp x_length/y_length on Axes(...) calls to safe limits (5.4 / 4.3)."""
    def x_replacer(m):
        val = float(m.group(1))
        if val > 5.4:
            fixes.append(f"AUTO-FIX: x_length={val} > 5.4 → clamped to 5.4")
            return "x_length=5.4"
        return m.group(0)

    def y_replacer(m):
        val = float(m.group(1))
        if val > 4.3:
            fixes.append(f"AUTO-FIX: y_length={val} > 4.3 → clamped to 4.3")
            return "y_length=4.3"
        return m.group(0)

    code = re.sub(r'x_length\s*=\s*([0-9.]+)', x_replacer, code)
    code = re.sub(r'y_length\s*=\s*([0-9.]+)', y_replacer, code)
    return code


def _fix_font_size_too_large(code: str, fixes: list[str]) -> str:
    """
    Clamp font_size on Text() to MAX_TEXT_FONT_SIZE, and MathTex() to
    MAX_MATHTEX_FONT_SIZE (perfect size for mobile vertical video).

    Uses the module-level MAX_TEXT_FONT_SIZE / MAX_MATHTEX_FONT_SIZE
    constants so this fixer and `_detect_font_size_violations` below can
    never contradict each other again (previously the fixer clamped
    MathTex to 20 while a detector separately flagged anything over 28,
    and a second, unused detector flagged anything over 30).
    """

    # 1. Clamp MathTex (Matches the highlighted text size in your Q17 example)
    def math_replacer(m):
        size = int(m.group(2))
        if size > MAX_MATHTEX_FONT_SIZE:
            fixes.append(f"AUTO-FIX: MathTex font_size={size} > {MAX_MATHTEX_FONT_SIZE} → clamped to {MAX_MATHTEX_FONT_SIZE}")
            return f"{m.group(1)}{MAX_MATHTEX_FONT_SIZE}"
        return m.group(0)
    code = re.sub(r'(MathTex\s*\([^)]*?font_size\s*=\s*)([0-9]+)', math_replacer, code)

    # 2. Clamp Text (Keeps Top Zone & Step titles readable)
    def text_replacer(m):
        size = int(m.group(2))
        if size > MAX_TEXT_FONT_SIZE:
            fixes.append(f"AUTO-FIX: Text font_size={size} > {MAX_TEXT_FONT_SIZE} → clamped to {MAX_TEXT_FONT_SIZE}")
            return f"{m.group(1)}{MAX_TEXT_FONT_SIZE}"
        return m.group(0)
    code = re.sub(r'(Text\s*\([^)]*?font_size\s*=\s*)([0-9]+)', text_replacer, code)

    return code


def _fix_missing_numpy_import(code: str, fixes: list[str]) -> str:
    """
    Add `import numpy as np` if missing, at a syntactically valid insertion
    point rather than blindly prepending it.

    Blindly prepending 'import numpy as np\\n' can place the import before
    a shebang, an encoding declaration, a module docstring, or a
    `from __future__ import ...` line. The last case is a hard SyntaxError,
    since future imports must appear at the very start of the module (only
    a docstring/comments/blank lines may precede them). This version is
    AST-aware: it parses the module, finds the module docstring (if any)
    and any leading `__future__` imports, and inserts the numpy import
    immediately after them, preserving a leading shebang/encoding line too.
    """
    try:
        tree = ast.parse(code)
    except SyntaxError:
        # Can't safely determine an insertion point without a parse.
        # Fall back to the old prepend behavior rather than doing nothing —
        # the syntax-error detector below will flag the file either way,
        # and the retry loop needs *some* code back.
        if 'import numpy as np' not in '\n'.join(code.splitlines()[:10]):
            fixes.append("AUTO-FIX: Added 'import numpy as np' at top of file (unparsable source, best-effort placement)")
            return 'import numpy as np\n' + code
        return code

    already_imported = any(
        isinstance(node, ast.Import)
        and any(alias.name == "numpy" and alias.asname == "np" for alias in node.names)
        for node in tree.body
    )
    if already_imported:
        return code

    lines = code.splitlines(keepends=True)
    if not lines:
        fixes.append("AUTO-FIX: Added 'import numpy as np' at top of file")
        return 'import numpy as np\n'

    insert_at = 0

    # Keep a shebang and an encoding declaration at the very top.
    if lines[0].startswith('#!'):
        insert_at = 1
    if insert_at < len(lines) and 'coding' in lines[insert_at] and lines[insert_at].lstrip().startswith('#'):
        insert_at += 1

    # Skip any leading blank/comment lines before the docstring.
    while insert_at < len(lines):
        stripped = lines[insert_at].strip()
        if not stripped or stripped.startswith('#'):
            insert_at += 1
        else:
            break

    # If the module starts with a docstring, insert after it.
    if (
        tree.body
        and isinstance(tree.body[0], ast.Expr)
        and isinstance(getattr(tree.body[0], "value", None), ast.Constant)
        and isinstance(tree.body[0].value.value, str)
    ):
        doc_end = tree.body[0].end_lineno
        if doc_end is not None:
            insert_at = max(insert_at, doc_end)

    # Keep any `from __future__ import ...` lines ahead of the new import —
    # they are required to be the first statements in the module.
    while insert_at < len(lines) and lines[insert_at].strip().startswith('from __future__ import'):
        insert_at += 1

    lines.insert(insert_at, 'import numpy as np\n')
    fixes.append("AUTO-FIX: Added 'import numpy as np' (inserted after docstring/__future__ imports, not blindly prepended)")
    return ''.join(lines)


def _fix_showcreation(code: str, fixes: list[str]) -> str:
    """Auto-fix ShowCreation → Create. Token-aware: won't touch comments/strings."""
    new_code, count = _safe_identifier_replace(code, 'ShowCreation(', 'Create(')
    if count:
        fixes.append(f"AUTO-FIX: ShowCreation() → Create() ({count} occurrence(s))")
    return new_code


def _fix_get_graph(code: str, fixes: list[str]) -> str:
    """Auto-fix axes.get_graph() → axes.plot(). Token-aware: won't touch comments/strings."""
    new_code, count = _safe_identifier_replace(code, 'get_graph(', 'plot(')
    if count:
        fixes.append(f"AUTO-FIX: .get_graph() → .plot() ({count} occurrence(s))")
    return new_code


def _fix_double_quote_in_strings(code: str, fixes: list[str]) -> str:
    """Fix Text("...") using double quotes → Text('...')."""
    pattern = re.compile(r'((?:Text|MathTex|Tex)\s*\()"([^"]*)"')
    
    def replacer(m):
        if "'" in m.group(2):
            return m.group(0)
        fixes.append(f"AUTO-FIX: Double-quoted string in {m.group(1)} → single quotes")
        return f"{m.group(1)}'{m.group(2)}'"
    
    return pattern.sub(replacer, code)


def _fix_arrange_right_long_thai(code: str, fixes: list[str]) -> str:
    """Auto-fix .arrange(RIGHT) with long Thai Text to .arrange(DOWN)."""
    thai_long = re.compile(r'[\u0E00-\u0E7F]{15,}')
    
    lines = code.splitlines()
    result_lines = list(lines)
    
    i = 0
    while i < len(lines):
        line = lines[i]
        
        if '.arrange(RIGHT' in line or '.arrange( RIGHT' in line:
            has_long_thai = False
            for back in range(i, max(i - 20, 0), -1):
                if thai_long.search(lines[back]) and 'Text(' in lines[back]:
                    has_long_thai = True
                    break
                if 'VGroup(' in lines[back]:
                    break
            
            if has_long_thai:
                new_line = re.sub(
                    r'\.arrange\s*\(\s*RIGHT\s*(?:,\s*buff\s*=\s*[\d.]+)?\s*\)',
                    '.arrange(DOWN, aligned_edge=LEFT, buff=0.15)',
                    line
                )
                if new_line != line:
                    result_lines[i] = new_line
                    fixes.append(
                        f"AUTO-FIX: Line {i+1}: .arrange(RIGHT) with long Thai Text → "
                        f".arrange(DOWN, aligned_edge=LEFT) to prevent overflow"
                    )
        i += 1
    
    return '\n'.join(result_lines)


def _fix_tex_mobject(code: str, fixes: list[str]) -> str:
    """Auto-fix deprecated TexMobject/TextMobject → MathTex/Text. Token-aware."""
    code, count = _safe_identifier_replace(code, 'TexMobject(', 'MathTex(')
    if count:
        fixes.append(f"AUTO-FIX: TexMobject() → MathTex() ({count} occurrence(s))")
    code, count = _safe_identifier_replace(code, 'TextMobject(', 'Text(')
    if count:
        fixes.append(f"AUTO-FIX: TextMobject() → Text() ({count} occurrence(s))")
    return code


def _fix_indicate_flash(code: str, fixes: list[str]) -> str:
    """Remove forbidden animations that crash Manim. Token-aware: won't touch comments/strings."""
    replacements = [
        ('Indicate(', 'FadeIn('),
        ('Flash(', 'GrowFromCenter('),
        ('ApplyWave(', 'FadeIn('),
    ]
    for old, new in replacements:
        code, count = _safe_identifier_replace(code, old, new)
        if count:
            fixes.append(f"AUTO-FIX: {old} → {new} (forbidden animation, {count} occurrence(s))")
    return code


def _fix_font_in_mathtex(code: str, fixes: list[str]) -> str:
    """Remove font= parameter from MathTex/Tex calls."""
    pattern = re.compile(r"((?:MathTex|Tex)\s*\([^)]*),\s*font\s*=\s*'[^']*'([^)]*\))")
    if pattern.search(code):
        fixes.append("AUTO-FIX: Removed font= parameter from MathTex/Tex (not supported)")
        code = pattern.sub(r'\1\2', code)
    return code


def _fix_mathrm_curly_braces(code: str, fixes: list[str]) -> str:
    """Fix \\mathrm{} with no content."""
    if r'\\mathrm{}' in code:
        fixes.append("AUTO-FIX: Removed empty \\mathrm{}")
        code = code.replace(r'\\mathrm{}', '')
    return code


def _fix_enforce_zone_clamping(code: str, fixes: list[str]) -> str:
    """
    Deterministically guarantee scale_to_fit_width/height before every
    .move_to(top_center / middle_center / bottom_center), regardless of
    whether Gemini remembered to add clamping itself.
    """
    zone_configs = {
        'top_center': ('frame_width * 0.88', 'top_zone_height * 0.88'),
        'middle_center': ('frame_width * 0.88', 'middle_zone_height * 0.82'),
        'bottom_center': ('frame_width * 0.88', 'bottom_zone_height * 0.88'),
    }
    lines = code.splitlines()
    out = []
    move_to_pattern = re.compile(r'^(\s*)(\w+)\.move_to\((top_center|middle_center|bottom_center)\)\s*$')

    for line in lines:
        m = move_to_pattern.match(line)
        if m:
            indent, var, zone = m.groups()
            w_expr, h_expr = zone_configs[zone]

            # Scan back through everything already emitted to find THIS
            # variable's assignment line, then only look for an existing
            # scale_to_fit_width call between that assignment and here.
            # This fixes two bugs from the fixed 6-line-window version:
            #   (a) false negative: a legitimate double-clamp block (scale
            #       width, scale height, min-width check, min-height check)
            #       can run 6-8+ lines and fall outside a fixed window,
            #       causing a redundant (harmless but wasteful) re-clamp.
            #   (b) false positive: checking `f'{var}.scale_to_fit_width'
            #       not in recent` as a plain substring means var='group'
            #       incorrectly matches inside 'sub_group.scale_to_fit_width',
            #       causing 'group' to be silently skipped and left
            #       unclamped — the exact overflow bug this fixer exists
            #       to prevent.
            assign_pattern = re.compile(rf'(?<![\w.]){re.escape(var)}\s*=')
            scan_start = 0
            for idx in range(len(out) - 1, -1, -1):
                if assign_pattern.search(out[idx]):
                    scan_start = idx
                    break

            already_scaled_pattern = re.compile(
                rf'(?<![\w.]){re.escape(var)}\.scale_to_fit_width\s*\('
            )
            recent = "\n".join(out[scan_start:])
            already_scaled = bool(already_scaled_pattern.search(recent))

            if not already_scaled:
                out.append(f"{indent}if {var}.width > {w_expr}:")
                out.append(f"{indent}    {var}.scale_to_fit_width({w_expr})")
                out.append(f"{indent}if {var}.height > {h_expr}:")
                out.append(f"{indent}    {var}.scale_to_fit_height({h_expr})")
                fixes.append(f"AUTO-FIX: Force-clamped '{var}' before .move_to({zone})")
        out.append(line)
    return '\n'.join(out)



# ─────────────────────────────────────────────────────────────────────────────
# Phase 2 helpers — violation detectors (things we CAN'T safely auto-fix)
# ─────────────────────────────────────────────────────────────────────────────

def _detect_latex_in_text(lines: list[str]) -> list[Violation]:
    """Detect remaining LaTeX syntax in Text() after auto-fixes."""
    violations = []
    latex_in_text = re.compile(
        r'Text\s*\([^)]*(?:'
        r'\\\\(?:frac|sqrt|sum|int|prod|lim|partial)'
        r'|\\\\[\(\[\\]'
        r')[^)]*\)'
    )
    for i, line in enumerate(lines, 1):
        if 'Text(' in line and latex_in_text.search(line):
            violations.append(Violation(
                rule="LATEX_IN_TEXT",
                line=i,
                snippet=line.strip()[:80],
                description=(
                    "พบ LaTeX syntax ซับซ้อน (\\frac, \\sqrt ฯลฯ) ใน Text() — "
                    "ต้องแยกเป็น VGroup(Text('...'), MathTex(r'...')) แทน"
                )
            ))
    return violations


def _detect_thai_in_mathtex(lines: list[str]) -> list[Violation]:
    """Detect Thai characters inside MathTex() or Tex() calls."""
    violations = []
    thai_range = re.compile(r'[\u0E00-\u0E7F]')
    mathtex_pattern = re.compile(r'(MathTex|Tex)\s*\(')
    for i, line in enumerate(lines, 1):
        if mathtex_pattern.search(line) and thai_range.search(line):
            code_part = line.split('#')[0]
            if mathtex_pattern.search(code_part) and thai_range.search(code_part):
                violations.append(Violation(
                    rule="THAI_IN_MATHTEX",
                    line=i,
                    snippet=line.strip()[:80],
                    description=(
                        "พบตัวอักษรภาษาไทยใน MathTex()/Tex() — "
                        "ต้องแยกข้อความไทยออกเป็น Text() แล้วใช้ VGroup จัดวาง"
                    )
                ))
    return violations


def _detect_thai_in_mathrm(lines: list[str]) -> list[Violation]:
    """Detect Thai characters inside \\mathrm{...} after auto-fix."""
    violations = []
    thai_range = re.compile(r'[\u0E00-\u0E7F]')
    mathrm_pattern = re.compile(r'\\\\?mathrm\{([^}]*)\}')
    for i, line in enumerate(lines, 1):
        for m in mathrm_pattern.finditer(line):
            if thai_range.search(m.group(1)):
                violations.append(Violation(
                    rule="THAI_IN_MATHRM",
                    line=i,
                    snippet=line.strip()[:80],
                    description=(
                        f"พบภาษาไทยใน \\mathrm{{{m.group(1)[:20]}}} — "
                        "ต้องแยกออกเป็น Text()"
                    )
                ))
    return violations


def _detect_overlapping_labels(lines: list[str]) -> list[Violation]:
    violations = []
    placement_map: dict[str, list[int]] = {}
    next_to_pattern = re.compile(
        r'\.next_to\(\s*(\w+)\s*,\s*(UR|UL|DR|DL|UP|DOWN|LEFT|RIGHT)\s*'
    )
    for i, line in enumerate(lines, 1):
        for m in next_to_pattern.finditer(line):
            ref, direction = m.group(1), m.group(2)
            key = f"{ref}_{direction}"
            placement_map.setdefault(key, []).append(i)
    for key, line_nums in placement_map.items():
        if len(line_nums) >= 3:
            ref, direction = key.rsplit('_', 1)
            violations.append(Violation(
                rule="OVERLAPPING_LABELS",
                line=line_nums[0],
                snippet=f"บรรทัด {line_nums}: .next_to({ref}, {direction}, ...)",
                description=(
                    f"มี {len(line_nums)} labels ที่ .next_to({ref}, {direction}) "
                    f"ทิศเดียวกัน — จะทับซ้อนกัน ต้องกระจายทิศทาง"
                )
            ))
    return violations


def _detect_axes_too_large(lines: list[str]) -> list[Violation]:
    violations = []
    for i, line in enumerate(lines, 1):
        m = re.search(r'x_length\s*=\s*([0-9.]+)', line)
        if m:
            try:
                val = float(m.group(1))
                if val > 5.4:
                    violations.append(Violation(
                        rule="AXES_TOO_LARGE",
                        line=i,
                        snippet=line.strip()[:80],
                        description=f"x_length={val} เกิน 5.4 — ควรใช้ frame_width * 0.60 (หรือ 5.4)"
                    ))
            except ValueError:
                pass
        m = re.search(r'y_length\s*=\s*([0-9.]+)', line)
        if m:
            try:
                val = float(m.group(1))
                if val > 4.3:
                    violations.append(Violation(
                        rule="AXES_TOO_LARGE",
                        line=i,
                        snippet=line.strip()[:80],
                        description=f"y_length={val} เกิน 4.3 — ควรใช้ middle_zone_height * 0.65 (หรือ 4.3)"
                    ))
            except ValueError:
                pass
    return violations


def _detect_missing_numpy_import(lines: list[str]) -> list[Violation]:
    first_lines = '\n'.join(lines[:10])
    if 'import numpy as np' not in first_lines:
        return [Violation(
            rule="MISSING_NUMPY",
            line=1,
            snippet=lines[0].strip() if lines else '',
            description="ไม่มี 'import numpy as np' — จะเกิด NameError: name 'np' is not defined"
        )]
    return []


def _detect_move_to_scalar(lines: list[str]) -> list[Violation]:
    violations = []
    scalar_pattern = re.compile(
        r'\.move_to\(\s*(?!np\.array|ORIGIN|UP|DOWN|LEFT|RIGHT|UR|UL|DR|DL)'
        r'([a-z_]+(?:_y|_bottom|_top|_center_y))\s*\)'
    )
    for i, line in enumerate(lines, 1):
        m = scalar_pattern.search(line)
        if m:
            varname = m.group(1)
            violations.append(Violation(
                rule="MOVE_TO_SCALAR",
                line=i,
                snippet=line.strip()[:80],
                description=f".move_to({varname}) ส่ง scalar → ต้องเป็น np.array([0, {varname}, 0])"
            ))
    return violations


def _detect_final_answer_arrange_right(lines: list[str]) -> list[Violation]:
    """Detect .arrange(RIGHT) with long Thai Text as direct member."""
    violations = []
    thai_long = re.compile(r'[\u0E00-\u0E7F]{15,}')
    arrange_right_pat = re.compile(r'\.arrange\(\s*RIGHT')

    for i, line in enumerate(lines, 1):
        if not arrange_right_pat.search(line):
            continue

        vgroup_block_lines = []
        if 'VGroup(' in line:
            vgroup_block_lines = [line]
        else:
            depth = 0
            found_open = False
            for back in range(i - 1, max(i - 12, 0), -1):
                back_line = lines[back]
                depth += back_line.count(')') - back_line.count('(')
                vgroup_block_lines.insert(0, back_line)
                if 'VGroup(' in back_line and depth >= 0:
                    found_open = True
                    break
            if not found_open:
                continue

        vgroup_text = '\n'.join(vgroup_block_lines)
        vgroup_args_pat = re.compile(r'VGroup\s*\(([^)]+)\)', re.DOTALL)
        args_match = vgroup_args_pat.search(vgroup_text)
        if not args_match:
            continue

        arg_names = re.findall(r'\b([a-zA-Z_]\w*)\b', args_match.group(1))
        found_long_thai_text = False

        for arg_name in arg_names:
            for back in range(i - 1, max(i - 22, 0), -1):
                def_line = lines[back]
                if not re.match(rf'\s*{re.escape(arg_name)}\s*=', def_line):
                    continue
                if 'Text(' not in def_line or 'MathTex(' in def_line:
                    break
                if thai_long.search(def_line):
                    found_long_thai_text = True
                    break
                break

            if found_long_thai_text:
                break

        if found_long_thai_text:
            violations.append(Violation(
                rule="ANSWER_ARRANGE_RIGHT_OVERFLOW",
                line=i,
                snippet=line.strip()[:80],
                description=(
                    "พบ .arrange(RIGHT) ที่มี Text ไทยยาว (15+ ตัว) — "
                    "ต้องเปลี่ยนเป็น .arrange(DOWN, aligned_edge=LEFT)"
                )
            ))
    return violations


def _detect_vgroup_list_comprehension(lines: list[str]) -> list[Violation]:
    """Detect any remaining VGroup(*[...]) patterns after auto-fix."""
    violations = []
    pattern = re.compile(r'VGroup\s*\(\s*\*\s*\[')
    for i, line in enumerate(lines, 1):
        if pattern.search(line):
            violations.append(Violation(
                rule="VGROUP_LIST_COMPREHENSION",
                line=i,
                snippet=line.strip()[:80],
                description=(
                    "พบ VGroup(*[...]) — เสี่ยงวงเล็บไม่สมดุล "
                    "ต้องเขียน Text() แยกบรรทัดเป็น argument ตรงๆ ของ VGroup()"
                )
            ))
    return violations


def _detect_unbalanced_latex_braces(lines: list[str]) -> list[Violation]:
    violations = []
    pattern = re.compile(r'(?:MathTex|Tex)\s*\(\s*r[\'"]([^\'"]*)[\'"]')
    for i, line in enumerate(lines, 1):
        for m in pattern.finditer(line):
            latex_content = m.group(1)
            opens = latex_content.count('{')
            closes = latex_content.count('}')
            if opens != closes:
                violations.append(Violation(
                    rule="UNBALANCED_LATEX_BRACES",
                    line=i,
                    snippet=line.strip()[:80],
                    description=(
                        f"วงเล็บปีกกา LaTeX ไม่สมดุล: {opens} เปิด แต่ {closes} ปิด — "
                        "ตรวจนับและแก้ให้สมดุล"
                    )
                ))
    return violations


def _detect_math_errors(lines: list[str]) -> list[Violation]:
    """
    Detect common mathematical errors in equations.

    NOTE: the old MATH_BACKSLASH_MISSING checks that lived here have been
    REMOVED. They checked `r'\\frac' in content and r'\\\\frac' not in
    content`, which is backwards: a CORRECTLY single-escaped raw string
    (content == '\\frac{1}{2}', exactly one backslash) always satisfies
    this condition too, because the single-backslash substring '\\frac' is
    trivially found inside itself. So this rule flagged correct code as
    broken and told Gemini (via its own description text, which said
    '\\\\frac' i.e. double-backslash) to add a SECOND backslash -- which is
    exactly what produces the garbled "mathrm{m/s}"-style text bug. The
    real fix for over-escaping is the deterministic `_fix_over_escaped_latex`
    auto-fixer (Phase 1), which runs before this detector and needs no LLM
    call at all.
    """
    violations = []

    for i, line in enumerate(lines, 1):
        # Check for \equiv used incorrectly
        if r'\equiv' in line and 'MathTex' in line:
            violations.append(Violation(
                rule="MATH_EQUIV_INCORRECT",
                line=i,
                snippet=line.strip()[:80],
                description=(
                    "พบ \\equiv ในสมการ — ควรใช้ = แทน \\equiv "
                    "(\\equiv ใช้สำหรับเอกลักษณ์/นิยามเท่านั้น)"
                )
            ))

        # Check for wrong final velocity calculation. Look at a forward
        # window of lines (not just this one) since the correct final
        # answer is often written on a LATER MathTex/variable, e.g.:
        #   eq4 = MathTex(r'v = \sqrt{200^2 + 200^2}', ...)
        #   eq5 = MathTex(r'v = 200\sqrt{2}\,\mathrm{m/s}', ...)
        # Checking only `line` for '200\sqrt{2}' incorrectly flags eq4 even
        # though eq5 (a few lines later) already has the correct answer.
        if 'sqrt{200^2 + 200^2}' in line and '200^2' in line and 'MathTex' in line:
            window = "\n".join(lines[i - 1:min(i + 5, len(lines))])
            if '200\\sqrt{2}' not in window and '200\\\\sqrt{2}' not in window:
                violations.append(Violation(
                    rule="MATH_SQRT_WRONG",
                    line=i,
                    snippet=line.strip()[:80],
                    description=(
                        "พบ sqrt(200² + 200²) แต่ไม่พบคำตอบ 200√2 ในสมการถัดไป — "
                        "ต้องเป็น sqrt(200² + 200²) = 200√2"
                    )
                ))

    return violations


class _Scope:
    """One lexical scope: module, function/lambda, class, or comprehension."""
    __slots__ = ("kind", "parent", "assigned_at")

    def __init__(self, kind: str, parent: "_Scope | None"):
        self.kind = kind
        self.parent = parent
        self.assigned_at: dict[str, int] = {}


def _detect_undefined_variables(code: str) -> list[Violation]:
    """
    Catch NameError-causing bugs *before* Manim render: variables that are
    used (e.g. inside a VGroup(...) call) but never assigned anywhere that
    could actually reach that use, or used before their first assignment
    in the *same* scope.

    This exists mainly as a safety net for auto-fix/line-patch bugs that can
    silently drop a variable's definition line (e.g. a targeted Gemini patch
    that only echoes back the line it was asked to fix, dropping a sibling
    definition that happened to sit in the same context window). Catching it
    here means the pipeline gets another retry instead of a hard render crash.

    SCOPE-AWARE (previous version was not): assignments are tracked
    per-scope with proper Python lexical scoping (module / function /
    comprehension scopes; class bodies are NOT an enclosing scope for
    nested methods, matching real Python semantics). This fixes two
    opposite bugs the flat, single-dict version had:
      - false negative: `value = 1` inside one function made `value` look
        "defined" for an unrelated `print(value)` inside a completely
        different function.
      - false positive risk: a name assigned only inside some other
        function could mask a genuinely undefined name of the same
        spelling used at module level, or vice versa.
    Name resolution follows LEGB (skipping class scopes when climbing up,
    since a method cannot see its class body's names as an enclosing
    scope). A name resolved in the *same* scope where it's used is still
    checked for "used before its first assignment on an earlier line"
    (this matters most for the typical single straight-line
    `construct(self)` method these scripts are generated as). A name that
    only resolves in an *enclosing* scope is never flagged for ordering,
    since a nested function's body runs after the enclosing scope has
    already executed up to that point — flagging that would produce false
    positives on ordinary, valid closures.

    Deliberately conservative to avoid false positives:
      - Only checks bare lowercase/snake_case identifiers (regex
        ^[a-z_][a-z0-9_]*$). Manim/numpy library symbols are virtually always
        PascalCase (Text, VGroup, MathTex, Circle) or ALL_CAPS (UP, BLUE_D,
        ORIGIN), so this naturally excludes them without needing a full
        manim symbol table.
      - Whitelists Python builtins, any imported names, and a short list of
        known lowercase manim/numpy globals (self, config, np, and common
        rate functions) that are legitimately used without local assignment.
      - `x += 1` now correctly counts as reading `x` (on the same line, at
        the point evaluation happens) in addition to writing it — the
        previous version only recorded it as a write, so `x += 1` with no
        prior `x = ...` anywhere was silently treated as fine.
      - Only reports each offending name once file-wide, for the first
        genuinely undefined/used-too-early occurrence.
    """
    violations: list[Violation] = []

    try:
        tree = ast.parse(code)
    except SyntaxError:
        return violations  # syntax errors are already caught elsewhere

    known_globals = {
        "self", "cls", "config", "np",
        # common lowercase manim rate-functions / helpers pulled in via
        # `from manim import *` that are never locally assigned
        "smooth", "linear", "there_and_back", "there_and_back_with_pause",
        "running_start", "not_quite_there", "wiggle", "squish_rate_func",
        "lingering", "exponential_decay", "double_smooth", "rush_into",
        "rush_from", "slow_into", "always_redraw", "always_shift",
        "always_rotate", "always_scale", "turn_animation_into_updater",
        "interpolate", "rate_functions",
    }

    imported: set[str] = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for alias in node.names:
                imported.add(alias.asname or alias.name.split(".")[0])
        elif isinstance(node, ast.ImportFrom):
            for alias in node.names:
                if alias.name != "*":
                    imported.add(alias.asname or alias.name)

    whitelist = set(dir(_builtins_module)) | imported | known_globals
    name_pattern = re.compile(r"^[a-z_][a-z0-9_]*$")

    module_scope = _Scope("module", None)
    scope_of: dict[int, _Scope] = {}  # id(node) -> Scope, for scope-owning nodes

    def record(scope: _Scope, name: str, lineno: int) -> None:
        if name not in scope.assigned_at or lineno < scope.assigned_at[name]:
            scope.assigned_at[name] = lineno

    def record_targets(scope: _Scope, target: ast.AST, lineno: int) -> None:
        for n in ast.walk(target):
            if isinstance(n, ast.Name):
                record(scope, n.id, lineno)

    def all_params(args: ast.arguments):
        return list(args.posonlyargs) + list(args.args) + list(args.kwonlyargs)

    # ── Pass 1: build the scope tree and collect every assignment per scope
    def build(node: ast.AST, scope: _Scope) -> None:
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            record(scope, node.name, node.lineno)
            new_scope = _Scope("function", scope)
            scope_of[id(node)] = new_scope
            args = node.args
            for a in all_params(args):
                record(new_scope, a.arg, node.lineno)
            if args.vararg:
                record(new_scope, args.vararg.arg, node.lineno)
            if args.kwarg:
                record(new_scope, args.kwarg.arg, node.lineno)
            for deco in node.decorator_list:
                build(deco, scope)
            for d in list(args.defaults) + [d for d in args.kw_defaults if d is not None]:
                build(d, scope)
            for stmt in node.body:
                build(stmt, new_scope)
            return

        if isinstance(node, ast.Lambda):
            new_scope = _Scope("function", scope)
            scope_of[id(node)] = new_scope
            args = node.args
            for a in all_params(args):
                record(new_scope, a.arg, getattr(node, "lineno", 0))
            if args.vararg:
                record(new_scope, args.vararg.arg, getattr(node, "lineno", 0))
            if args.kwarg:
                record(new_scope, args.kwarg.arg, getattr(node, "lineno", 0))
            build(node.body, new_scope)
            return

        if isinstance(node, ast.ClassDef):
            record(scope, node.name, node.lineno)
            new_scope = _Scope("class", scope)
            scope_of[id(node)] = new_scope
            for deco in node.decorator_list:
                build(deco, scope)
            for base in node.bases:
                build(base, scope)
            for stmt in node.body:
                build(stmt, new_scope)
            return

        if isinstance(node, (ast.ListComp, ast.SetComp, ast.DictComp, ast.GeneratorExp)):
            new_scope = _Scope("comprehension", scope)
            scope_of[id(node)] = new_scope
            for gen in node.generators:
                record_targets(new_scope, gen.target, getattr(node, "lineno", 0))
                for cond in gen.ifs:
                    build(cond, new_scope)
            if isinstance(node, ast.DictComp):
                build(node.key, new_scope)
                build(node.value, new_scope)
            else:
                build(node.elt, new_scope)
            return

        if isinstance(node, ast.Assign):
            for t in node.targets:
                record_targets(scope, t, node.lineno)
        elif isinstance(node, ast.AugAssign):
            record_targets(scope, node.target, node.lineno)
        elif isinstance(node, ast.AnnAssign) and node.target is not None:
            record_targets(scope, node.target, node.lineno)
        elif isinstance(node, ast.For):
            record_targets(scope, node.target, node.lineno)
        elif isinstance(node, ast.With):
            for item in node.items:
                if item.optional_vars:
                    record_targets(scope, item.optional_vars, node.lineno)

        for child in ast.iter_child_nodes(node):
            build(child, scope)

    build(tree, module_scope)

    # ── Pass 2: collect every Name *use* (Load), tagged with the scope it
    # occurs in, including the implicit read inside `x += 1`.
    uses: list[tuple[str, int, _Scope]] = []

    def collect_uses(node: ast.AST, scope: _Scope) -> None:
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            new_scope = scope_of[id(node)]
            for deco in node.decorator_list:
                collect_uses(deco, scope)
            args = node.args
            for d in list(args.defaults) + [d for d in args.kw_defaults if d is not None]:
                collect_uses(d, scope)
            for stmt in node.body:
                collect_uses(stmt, new_scope)
            return

        if isinstance(node, ast.Lambda):
            collect_uses(node.body, scope_of[id(node)])
            return

        if isinstance(node, ast.ClassDef):
            new_scope = scope_of[id(node)]
            for deco in node.decorator_list:
                collect_uses(deco, scope)
            for base in node.bases:
                collect_uses(base, scope)
            for stmt in node.body:
                collect_uses(stmt, new_scope)
            return

        if isinstance(node, (ast.ListComp, ast.SetComp, ast.DictComp, ast.GeneratorExp)):
            new_scope = scope_of[id(node)]
            for gen in node.generators:
                collect_uses(gen.iter, scope)
                for cond in gen.ifs:
                    collect_uses(cond, new_scope)
            if isinstance(node, ast.DictComp):
                collect_uses(node.key, new_scope)
                collect_uses(node.value, new_scope)
            else:
                collect_uses(node.elt, new_scope)
            return

        if isinstance(node, ast.AugAssign):
            # `x += 1` reads x before it (re)writes it — the previous
            # version missed this and treated it as pure assignment.
            for n in ast.walk(node.target):
                if isinstance(n, ast.Name):
                    uses.append((n.id, node.lineno, scope))
            collect_uses(node.value, scope)
            return

        if isinstance(node, ast.Name):
            if isinstance(node.ctx, ast.Load):
                uses.append((node.id, node.lineno, scope))
            return

        for child in ast.iter_child_nodes(node):
            collect_uses(child, scope)

    collect_uses(tree, module_scope)

    # ── Resolve each use against the scope chain (LEGB, skipping class
    # scopes when climbing, matching real Python closure rules).
    def resolve(scope: _Scope, name: str):
        if name in scope.assigned_at:
            return scope, scope.assigned_at[name]
        s = scope.parent
        while s is not None:
            if s.kind != "class" and name in s.assigned_at:
                return s, s.assigned_at[name]
            s = s.parent
        return None, None

    reported: set[str] = set()
    for name, lineno, scope in uses:
        if name in whitelist or not name_pattern.match(name) or name in reported:
            continue
        defining_scope, first_def = resolve(scope, name)
        if defining_scope is None:
            violations.append(Violation(
                rule="UNDEFINED_VARIABLE",
                line=lineno,
                snippet=name,
                description=(
                    f"ตัวแปร '{name}' ถูกใช้งานแต่ไม่เคยถูกกำหนดค่าที่ไหนเลยในโค้ด "
                    "(อาจถูกลบทิ้งโดยไม่ได้ตั้งใจระหว่างการแก้บั๊กอัตโนมัติ) "
                    "จะทำให้เกิด NameError ตอนเรนเดอร์"
                ),
            ))
            reported.add(name)
        elif defining_scope is scope and first_def > lineno:
            violations.append(Violation(
                rule="UNDEFINED_VARIABLE",
                line=lineno,
                snippet=name,
                description=(
                    f"ตัวแปร '{name}' ถูกใช้งานที่บรรทัด {lineno} "
                    f"ก่อนที่จะถูกกำหนดค่าครั้งแรกที่บรรทัด {first_def} — "
                    "จะทำให้เกิด NameError ตอนเรนเดอร์"
                ),
            ))
            reported.add(name)
        # else: resolved cleanly in this scope before use, or resolved in
        # an enclosing scope (a valid closure reference) — not flagged.

    return violations


def _detect_missing_scaling(lines: list[str]) -> list[Violation]:
    """
    Detect VGroups in bottom/middle zone without scaling.
    Scans forward from the assignment line to ensure scaling happens before move_to.
    """
    violations = []
    vgroup_assign_pattern = re.compile(r'^(\w+)\s*=\s*VGroup\(')
    
    for i, line in enumerate(lines):
        m = vgroup_assign_pattern.search(line)
        if not m:
            continue
        var_name = m.group(1)
        if 'axes' in var_name.lower():
            continue  # Axes groups are handled separately, don't double-flag

        # Scan forward up to 25 lines
        found_scale = False
        found_move_to_zone = False
        scan_end = min(i + 25, len(lines))

        for j in range(i + 1, scan_end):
            cur_line = lines[j]
            
            # Check if this variable gets scaled in this line
            if re.search(rf'\b{re.escape(var_name)}\.scale_to_fit_(width|height)\s*\(', cur_line):
                found_scale = True
                break  # Found scaling, this group is safe, no violation.

            # Check if this variable gets moved to bottom/middle center
            if re.search(rf'\b{re.escape(var_name)}\.move_to\s*\(\s*(?:bottom_center|middle_center)\s*\)', cur_line):
                found_move_to_zone = True
                # If we find a move_to, but haven't found a scaling yet, we have a violation.
                break 

        if found_move_to_zone and not found_scale:
            violations.append(Violation(
                rule="MISSING_SCALING",
                line=i + 1,
                snippet=line.strip()[:80],
                description=(
                    f"พบ VGroup '{var_name}' เคลื่อนไปกลาง/ล่าง (move_to) "
                    f"แต่ไม่พบการ .scale_to_fit_width() ก่อนหน้านั้น — "
                    "อาจทำให้เนื้อหาล้นจอ แก้โดยเพิ่ม scaling"
                )
            ))
    return violations


def _detect_text_overflow(lines: list[str]) -> list[Violation]:
    """
    Heuristic detector: estimates text width based on char count and font_size.
    Flags if estimated width exceeds frame_width * 0.88 (~7.9 pixels).
    """
    violations = []
    text_pattern = re.compile(r'Text\s*\(\s*[\'"]([^\'"]*)[\'"]\s*,\s*font_size\s*=\s*(\d+)')
    
    for i, line in enumerate(lines):
        for m in text_pattern.finditer(line):
            text_content = m.group(1)
            font_size = int(m.group(2))
            # Rough pixel estimate for TH Sarabun New (approx 0.55x pixel width per char)
            estimated_width = len(text_content) * font_size * 0.55
            
            if estimated_width > 7.9:  # frame_width * 0.88
                # We don't check for scaling here because scaling happens on VGroups.
                # This detector just warns the LLM to split the string or use a VGroup.
                violations.append(Violation(
                    rule="TEXT_OVERFLOW",
                    line=i + 1,
                    snippet=line.strip()[:80],
                    description=(
                        f"Text '{text_content[:20]}...' (len={len(text_content)}, font_size={font_size}) "
                        f"คาดว่าจะยาวเกินกรอบจอ (~{estimated_width:.0f}px > 7.9) — "
                        "ให้แบ่งเป็นหลายบรรทัดใน VGroup หรือห่อด้วย .scale_to_fit_width()"
                    )
                ))
    return violations


def _detect_font_size_violations(lines: list[str]) -> list[Violation]:
    """
    Detect font_size > 28 in Text()/MathTex().
    """
    violations = []
    
    for i, line in enumerate(lines, 1):
        text_match = re.search(r'Text\([^)]*font_size\s*=\s*(\d+)', line)
        if text_match:
            size = int(text_match.group(1))
            if size > MAX_TEXT_FONT_SIZE:
                violations.append(Violation(
                    rule="FONT_SIZE_TOO_LARGE",
                    line=i,
                    snippet=line.strip()[:80],
                    description=f"font_size={size} ใน Text() — ต้อง ≤ {MAX_TEXT_FONT_SIZE}"
                ))

        math_match = re.search(r'MathTex\([^)]*font_size\s*=\s*(\d+)', line)
        if math_match:
            size = int(math_match.group(1))
            if size > MAX_MATHTEX_FONT_SIZE:
                violations.append(Violation(
                    rule="FONT_SIZE_TOO_LARGE",
                    line=i,
                    snippet=line.strip()[:80],
                    description=f"font_size={size} ใน MathTex() — ต้อง ≤ {MAX_MATHTEX_FONT_SIZE}"
                ))
    
    return violations


# In code_validator.py, replace the _detect_bottom_zone_empty function with:

def _detect_bottom_zone_empty(lines: list[str]) -> list[Violation]:
    """
    Detect if bottom zone has no content.
    Only flag if there are truly NO steps at all in the bottom zone.
    """
    violations = []
    
    # Check for bottom zone content by looking for VGroups moved to bottom_center
    vgroup_assign_pattern = re.compile(r'(\w+)\s*=\s*VGroup\(')
    
    for i, line in enumerate(lines):
        m = vgroup_assign_pattern.search(line)
        if not m:
            continue
        var_name = m.group(1)
        
        # Skip axes-related VGroups
        if 'axes' in var_name.lower() or 'vis' in var_name.lower() or 'viz' in var_name.lower():
            continue
            
        # Check if this VGroup is moved to bottom_center
        window = lines[max(0, i):min(i + 35, len(lines))]
        window_text = "\n".join(window)
        
        if f'{var_name}.move_to(bottom_center)' in window_text:
            # Found bottom zone content - this episode is fine
            return []
    
    # If we get here, no bottom zone VGroup found
    # But double-check: maybe the code uses direct placement without VGroup?
    has_equations = False
    for i, line in enumerate(lines):
        if 'bottom_center' in line:
            # Look backward for MathTex that might be in bottom zone
            for back in range(max(0, i - 25), i):
                if 'MathTex' in lines[back] and 'bottom' not in lines[back].lower():
                    has_equations = True
                    break
            if has_equations:
                break
    
    if not has_equations:
        # One more check: any step_title or equation content?
        for line in lines[:80]:
            # Parenthesized: previously `'step_title' in line or 'eq' in
            # line and 'MathTex' in line` relied on Python's `and`/`or`
            # precedence, which parses as `A or (B and C)` — that already
            # happens to be the intended grouping, but leaving it implicit
            # makes the condition easy to misread and easy to break with a
            # future edit. Made explicit here with no behavior change.
            if 'step_title' in line or ('eq' in line and 'MathTex' in line):
                return []  # Found equations, it's fine
    
    # Only flag if there's truly no content
    has_content = False
    for line in lines[:50]:
        if 'Text(' in line or 'MathTex' in line or 'VGroup' in line:
            has_content = True
            break
    
    if has_content:
        violations.append(Violation(
            rule="BOTTOM_ZONE_EMPTY",
            line=1,
            snippet="construct() method",
            description="ไม่พบเนื้อหาในโซนล่าง — ตรวจสอบว่ามี VGroup(...).move_to(bottom_center) หรือไม่"
        ))
    
    return violations


def _fix_aligned_edge_center(code: str, fixes: list[str]) -> str:
    """Fix aligned_edge=CENTER which doesn't exist in Manim."""
    pattern = re.compile(r'aligned_edge\s*=\s*CENTER')
    if pattern.search(code):
        fixes.append("AUTO-FIX: aligned_edge=CENTER → aligned_edge=LEFT (CENTER doesn't exist in Manim)")
        code = pattern.sub('aligned_edge=LEFT', code)
    return code


def _detect_syntax_error(code: str) -> list[Violation]:
    """
    Explicit syntax-error check, run immediately after Phase 1 auto-fixes.

    Previously a SyntaxError after auto-fixing was silently swallowed:
    `_detect_undefined_variables` (and other AST-based checks) would hit
    `except SyntaxError: return []` and simply report zero violations,
    which reads as "this code is fine" even when it can't be parsed at
    all — a false negative that would only surface later as a hard render
    crash. This is especially important because some of the fixers above
    are themselves capable of introducing a syntax error (e.g. an
    indentation-sensitive rewrite landing in the wrong context). Surfacing
    it here as an explicit, ranked-first violation means it gets a
    Gemini retry with an exact line/message instead of a silent pass-through.
    """
    try:
        ast.parse(code)
    except SyntaxError as exc:
        line = exc.lineno or 1
        return [Violation(
            rule="SYNTAX_ERROR",
            line=line,
            snippet=(exc.text or "").strip()[:120],
            description=f"Python syntax error: {exc.msg} (บรรทัด {line}) — โค้ดนี้ parse ไม่ผ่านเลย ต้องแก้ก่อนอย่างอื่นทั้งหมด",
        )]
    return []


# ─────────────────────────────────────────────────────────────────────────────
# Main public function
# ─────────────────────────────────────────────────────────────────────────────

def preprocess_code(code_string: str) -> ValidationResult:
    """
    Run all auto-fixes and violation checks on Gemini-generated Manim code.
    
    Phase 1 order matters: some fixes depend on previous fixes.
    """
    auto_fixes: list[str] = []
    code = code_string

    # ── Phase 1: Auto-fix (order matters) ───────────────────────────────────
    
    # 1. Structural fixes first
    code = _fix_missing_numpy_import(code, auto_fixes)
    code = _fix_showcreation(code, auto_fixes)
    code = _fix_get_graph(code, auto_fixes)
    code = _fix_tex_mobject(code, auto_fixes)
    code = _fix_indicate_flash(code, auto_fixes)
    code = _fix_font_in_mathtex(code, auto_fixes)
    code = _fix_aligned_edge_center(code, auto_fixes)
    code = _fix_enforce_zone_clamping(code, auto_fixes) 
    
    # 2. Variable/value fixes
    code = _fix_bottom_zone_bottom(code, auto_fixes)
    code = _fix_move_to_scalar(code, auto_fixes)
    code = _fix_include_numbers_in_axis_config(code, auto_fixes)
    code = _fix_axes_too_large(code, auto_fixes)
    code = _fix_font_size_too_large(code, auto_fixes)
    
    # 3. String content fixes (order: most specific first)
    # Must run BEFORE other MathTex/Text content fixers so they operate on
    # normalized (single-backslash) LaTeX rather than over-escaped garbage.
    code = _fix_over_escaped_latex(code, auto_fixes)
    code = _fix_vgroup_list_comprehension(code, auto_fixes)
    code = _fix_latex_in_text_calls(code, auto_fixes)
    code = _fix_step_title_latex(code, auto_fixes)
    code = _fix_thai_in_mathrm(code, auto_fixes)
    code = _fix_arrange_right_long_thai(code, auto_fixes)
    code = _fix_text_in_mathtex(code, auto_fixes)
    code = _fix_single_backslash_lambda(code, auto_fixes)
    code = _fix_latex_escape_in_text(code, auto_fixes)
    code = _fix_mathrm_curly_braces(code, auto_fixes)
    code = _fix_double_quote_in_strings(code, auto_fixes)
    code = _fix_long_mathtex(code, auto_fixes)

    # ── Phase 2: Detect remaining violations ─────────────────────────────────
    violations: list[Violation] = []

    # Syntax-error check runs FIRST and short-circuits everything else: if
    # the code doesn't parse, every other detector's output is unreliable
    # (several of them fall back to "no violations" on a SyntaxError, which
    # would otherwise look like a clean bill of health). Some auto-fixers
    # above are themselves capable of introducing a syntax error, so this
    # check runs on the post-auto-fix code, not the original input.
    syntax_violations = _detect_syntax_error(code)
    if syntax_violations:
        return ValidationResult(
            fixed_code=code,
            violations=syntax_violations,
            auto_fixes=auto_fixes,
        )

    lines = code.splitlines()

    # Existing validations
    violations.extend(_detect_missing_numpy_import(lines))
    violations.extend(_detect_thai_in_mathtex(lines))
    violations.extend(_detect_thai_in_mathrm(lines))
    violations.extend(_detect_latex_in_text(lines))
    violations.extend(_detect_move_to_scalar(lines))
    violations.extend(_detect_axes_too_large(lines))    # ← UPDATED THRESHOLDS
    violations.extend(_detect_overlapping_labels(lines))
    violations.extend(_detect_final_answer_arrange_right(lines))
    violations.extend(_detect_vgroup_list_comprehension(lines))
    violations.extend(_detect_unbalanced_latex_braces(lines))
    
    # New validations
    violations.extend(_detect_math_errors(lines))
    violations.extend(_detect_missing_scaling(lines))   # ← UPDATED SCAN LOGIC
    violations.extend(_detect_font_size_violations(lines))
    violations.extend(_detect_bottom_zone_empty(lines))
    violations.extend(_detect_undefined_variables(code))
    
    # ← NEWLY ADDED
    violations.extend(_detect_text_overflow(lines)) 

    return ValidationResult(
        fixed_code=code,
        violations=violations,
        auto_fixes=auto_fixes,
    )


def validate_episode_count(lesson_json: dict, expected_min: int = None) -> tuple[bool, str]:
    declared = lesson_json.get("total_episodes", 0)
    actual = len(lesson_json.get("episodes", []))
    if declared != actual:
        return False, (
            f"total_episodes={declared} but episodes array has {actual} items."
        )
    if expected_min and actual < expected_min:
        return False, (
            f"Only {actual} episode(s) generated but expected at least {expected_min}."
        )
    return True, "ok"