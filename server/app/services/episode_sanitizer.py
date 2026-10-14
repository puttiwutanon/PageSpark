"""
server/app/services/episode_sanitizer.py

Deterministic clean-up of Gemini's structured episode JSON BEFORE it is
validated against EpisodeData and handed to scene_compiler.compile_scene().

Why this exists
---------------
The template pipeline removed most failure modes, but three remain because
they happen at the JSON-decoding layer, where neither the schema nor the
compiler can see them:

1. JSON control-character corruption.  When Gemini writes a LaTeX command
   with ONE backslash inside a JSON string ("\\frac", "\\theta", "\\beta",
   "\\nu", "\\rho", "\\times" ...), JSON decodes the backslash+letter pair as
   a control character (\\f, \\t, \\b, \\n, \\r).  The string then contains a
   form-feed / tab / backspace / newline instead of the LaTeX command, and
   LaTeX fails to compile ("\\x0crac{1}{2}").  repr() in the compiler
   faithfully embeds the corrupted string, so the compiler cannot help.

2. Over-escaped backslashes ("\\\\frac" decoded to "\\\\frac" -> a LaTeX line
   break followed by the word "frac").

3. diagram_code_lines is still free-form Python.  It must sit at exactly
   8-space indentation inside construct(), must not re-import / re-define
   the boilerplate, and must not contain stray control characters.

Everything here is pure string work (no Manim needed) so it is cheap and
easy to test.
"""
from __future__ import annotations

import logging
import re
from typing import Any

logger = logging.getLogger(__name__)

IND_WIDTH = 8

_THAI_RUN = re.compile(r"[\u0E00-\u0E7F][\u0E00-\u0E7F\s]*")
_ANY_THAI = re.compile(r"[\u0E00-\u0E7F]")
_EMPTY_TEXT_CMD = re.compile(r"\\(?:text|mathrm|textbf|mbox)\s*\{\s*\}")

# Characters JSON turns a "\x" into when Gemini forgot to double the backslash.
_ALWAYS_CORRUPT = {
    "\x07": "\\a",
    "\x08": "\\b",   # \beta, \bar, \binom, \boldsymbol
    "\x0b": "\\v",   # \vec, \varphi, \vartheta
    "\x0c": "\\f",   # \frac, \forall
}
# These three are also legitimate whitespace, so only treat them as corrupted
# when they are glued to a following letter (\theta -> TAB + "heta").
_AMBIGUOUS = {"\t": "\\t", "\n": "\\n", "\r": "\\r"}

# Lines Gemini must NOT emit inside diagram_code_lines (the boilerplate header
# already provides them).  Re-importing with `import *` inside construct() is a
# SyntaxError, and redefining the zone variables silently shifts the layout.
_FORBIDDEN_LINE = re.compile(
    r"^\s*(?:"
    r"from\s+manim\s+import\s+\*"
    r"|import\s+numpy(?:\s+as\s+np)?"
    r"|config\.\w+\s*="
    r"|self\.camera\.background_color\s*="
    r"|(?:frame_height|frame_width|top_zone_height|middle_zone_height"
    r"|bottom_zone_height|top_zone_top|top_zone_bottom|top_zone_center_y"
    r"|middle_zone_top|middle_zone_bottom|middle_zone_center_y"
    r"|bottom_zone_top|bottom_zone_bottom|bottom_zone_center_y"
    r"|top_center|middle_center|bottom_center)\s*="
    r")"
)
_SCENE_SHELL_LINE = re.compile(r"^\s*(?:class\s+PhysicsScene\b|def\s+construct\s*\()")


# ─────────────────────────────────────────────────────────────────────────────
# LaTeX / label repair
# ─────────────────────────────────────────────────────────────────────────────
def repair_control_chars(s: str) -> str:
    """Turn JSON-decoded control characters back into the LaTeX backslash
    commands they were meant to be."""
    for ch, esc in _ALWAYS_CORRUPT.items():
        s = s.replace(ch, esc)
    for ch, esc in _AMBIGUOUS.items():
        # glued to a letter => it was "\theta", "\nu", "\rho" ...
        s = re.sub(re.escape(ch) + r"(?=[A-Za-z])", lambda _m, e=esc: e, s)
        # otherwise it is real whitespace
        s = s.replace(ch, " ")
    return s


def _braces_balanced(latex: str) -> bool:
    stripped = re.sub(r"\\[{}]", "", latex)  # \{ and \} are literal braces
    depth = 0
    for c in stripped:
        if c == "{":
            depth += 1
        elif c == "}":
            depth -= 1
            if depth < 0:
                return False
    return depth == 0


def repair_latex(latex: str) -> str:
    s = repair_control_chars(latex)
    # "\\\\frac" (2+ backslashes glued to a command name) -> "\frac"
    s = re.sub(r"\\{2,}(?=[A-Za-z])", lambda _m: "\\", s)
    s = s.strip()
    # Gemini sometimes wraps the formula in $...$ or $$...$$
    if s.startswith("$$") and s.endswith("$$") and len(s) > 4:
        s = s[2:-2].strip()
    elif s.startswith("$") and s.endswith("$") and len(s) > 2:
        s = s[1:-1].strip()
    return s


def sanitize_equation_line(label: str | None, latex: str) -> tuple[str | None, str | None]:
    """Return (label, latex) cleaned, or (label, None) if the line is unusable
    and should be dropped (empty after cleaning, or unbalanced braces)."""
    latex = repair_latex(latex or "")
    if label:
        label = repair_control_chars(label).strip() or None

    # Thai inside LaTeX can never render; move it to the label instead.
    if _ANY_THAI.search(latex):
        thai = " ".join(m.group(0).strip() for m in _THAI_RUN.finditer(latex))
        latex = _THAI_RUN.sub("", latex)
        latex = _EMPTY_TEXT_CMD.sub("", latex).strip()
        if thai and not label:
            label = thai
        logger.info("  🧹 moved Thai text out of a latex field into its label")

    if not latex.strip():
        return label, None
    if not _braces_balanced(latex):
        logger.warning(f"  🧹 dropping equation line with unbalanced braces: {latex[:60]!r}")
        return label, None
    return label, latex


# ─────────────────────────────────────────────────────────────────────────────
# diagram_code_lines repair
# ─────────────────────────────────────────────────────────────────────────────
def normalize_diagram_lines(lines: list[Any]) -> list[str]:
    """Make a diagram fragment safe to splice into construct():
       - str-only, no embedded newlines, control characters repaired
       - forbidden boilerplate (imports / config / zone redefinitions) removed
       - minimum indentation forced to exactly 8 spaces
    """
    cleaned: list[str] = []
    for raw in lines or []:
        if not isinstance(raw, str):
            continue
        for piece in raw.replace("\r\n", "\n").replace("\r", "\n").split("\n"):
            # expand leading tabs (indentation), repair any other control char
            lead = len(piece) - len(piece.lstrip("\t "))
            head = piece[:lead].replace("\t", "    ")
            body = piece[lead:]
            for ch, esc in _ALWAYS_CORRUPT.items():
                body = body.replace(ch, esc)
            body = body.replace("\t", "\\t")
            cleaned.append((head + body).rstrip())

    kept: list[str] = []
    for line in cleaned:
        if _FORBIDDEN_LINE.match(line) or _SCENE_SHELL_LINE.match(line):
            logger.info(f"  🧹 removed boilerplate line from diagram: {line.strip()[:70]}")
            continue
        kept.append(line)

    non_empty = [l for l in kept if l.strip()]
    if not non_empty:
        return []

    min_indent = min(len(l) - len(l.lstrip(" ")) for l in non_empty)
    shift = IND_WIDTH - min_indent
    if shift == 0:
        return kept
    out: list[str] = []
    for l in kept:
        if not l.strip():
            out.append("")
        elif shift > 0:
            out.append(" " * shift + l)
        else:
            out.append(l[-shift:])
    return out


# ─────────────────────────────────────────────────────────────────────────────
# Whole-episode entry point
# ─────────────────────────────────────────────────────────────────────────────
def sanitize_episode_dict(ep: dict) -> dict:
    """Return a cleaned COPY of one episode dict (the original, which the audio
    engine and the API response still use, is left untouched)."""
    out = dict(ep)

    out["title"] = repair_control_chars(str(out.get("title") or "")).strip() or "โจทย์"
    out["problem_desc"] = repair_control_chars(str(out.get("problem_desc") or "")).strip()
    out["diagram_code_lines"] = normalize_diagram_lines(out.get("diagram_code_lines") or [])

    steps_out = []
    for step in out.get("steps") or []:
        if not isinstance(step, dict):
            continue
        lines_out = []
        for ln in step.get("lines") or []:
            if not isinstance(ln, dict):
                continue
            label, latex = sanitize_equation_line(ln.get("label"), ln.get("latex") or "")
            if latex is None:
                continue
            lines_out.append({"label": label, "latex": latex})
        if not lines_out:
            continue
        new_step = dict(step)
        new_step["title"] = repair_control_chars(str(step.get("title") or "")).strip() or "ขั้นตอน"
        new_step["lines"] = lines_out
        steps_out.append(new_step)
    out["steps"] = steps_out
    return out