"""
server/app/services/code_validator.py

Deterministic pre-processor for Gemini-generated Manim code.
Runs BEFORE the render attempt and BEFORE the Gemini retry loop.

Two-phase approach:
  Phase 1 — Auto-fix: patterns we can correct safely without LLM help
  Phase 2 — Violation report: things that need LLM rewrite, returned as
             a structured list so manim_engine can include them in the
             fix prompt for maximum precision

Usage (in manim_engine.py):
    from app.services.code_validator import preprocess_code
    fixed_code, violations = preprocess_code(code_string)
    # If violations is non-empty, pass them to _ask_gemini_to_fix()
    # before attempting the render.
"""

import re
from dataclasses import dataclass, field


# ─────────────────────────────────────────────────────────────────────────────
@dataclass
class Violation:
    rule: str          # short rule name e.g. "LATEX_IN_TEXT"
    line: int          # 1-based line number
    snippet: str       # the offending code snippet (first 80 chars)
    description: str   # human-readable description for Gemini prompt


@dataclass
class ValidationResult:
    fixed_code: str
    violations: list[Violation] = field(default_factory=list)
    auto_fixes: list[str] = field(default_factory=list)   # human-readable fix log

    @property
    def has_violations(self) -> bool:
        return len(self.violations) > 0

    def violation_summary(self) -> str:
        """Return a compact summary for inclusion in the Gemini fix prompt."""
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
# Phase 1 helpers — auto-fixers that are safe to apply unconditionally
# ─────────────────────────────────────────────────────────────────────────────

def _fix_latex_escape_in_text(code: str, fixes: list[str]) -> str:
    """
    Auto-fix: Text('...\\(\\lambda\\)...') → Text('...(lambda)...')
    When someone puts LaTeX \\( \\) inside a Python Text() call, strip it out
    and replace with plain text fallback so it at least doesn't crash.
    This is a last-resort fix — the Violation report will also flag it so
    Gemini can do a proper VGroup(Text, MathTex) split.
    """
    # Match \\( ... \\) inside string literals that appear to be in Text() calls
    # This regex finds the pattern and removes the \\( \\) wrappers
    pattern = re.compile(r'\\\\?\(\\\\?([a-zA-Z]+)\\\\?\)')
    def replacer(m):
        name = m.group(1)
        fixes.append(f"AUTO-FIX: Removed LaTeX \\({name}\\) from Text() call")
        return f"({name})"
    return pattern.sub(replacer, code)


def _fix_text_in_mathtex(code: str, fixes: list[str]) -> str:
    r"""
    Auto-fix: \text{...} → \mathrm{...} inside MathTex/Tex strings.
    But only if the content is purely ASCII (no Thai) — if Thai is inside,
    leave it for the violation report.
    """
    # Find \text{<ascii-only content>} inside r-strings or regular strings
    pattern = re.compile(r'\\\\text\{([^}]*)\}')
    def replacer(m):
        content = m.group(1)
        # Only auto-fix if content is ASCII (no Thai chars)
        if all(ord(c) < 128 for c in content):
            fixes.append(f"AUTO-FIX: \\text{{{content}}} → \\mathrm{{{content}}}")
            return f'\\\\mathrm{{{content}}}'
        return m.group(0)  # leave Thai-in-text for violation report
    return pattern.sub(replacer, code)


def _fix_single_backslash_lambda(code: str, fixes: list[str]) -> str:
    r"""
    Auto-fix: common single-backslash LaTeX commands that aren't in raw strings
    and will cause SyntaxWarning (e.g. '\lambda' → '\\lambda').
    Only applies to non-raw strings (doesn't start with r').
    """
    # LaTeX commands that are also valid Python escape sequences causing SyntaxWarning
    # \l, \f, \t, \n, \b, \a, \v, \, etc.
    dangerous_sequences = {
        r'\lambda': r'\\lambda',
        r'\frac': r'\\frac',
        r'\phi': r'\\phi',
        r'\Delta': r'\\Delta',
        r'\theta': r'\\theta',
        r'\pi': r'\\pi',
        r'\mathrm': r'\\mathrm',
        r'\cdot': r'\\cdot',
        r'\times': r'\\times',
        r'\sqrt': r'\\sqrt',
        r'\approx': r'\\approx',
    }
    # Find MathTex/Tex calls with non-raw strings containing single backslash
    # Pattern: MathTex('...\lambda...')  — note single backslash, no r prefix
    pattern = re.compile(r"(MathTex|Tex)\s*\(\s*'([^']*)'")
    def replacer(m):
        call = m.group(1)
        content = m.group(2)
        original = content
        for bad, good in dangerous_sequences.items():
            # bad has a real backslash; good has double backslash
            if bad in content:
                content = content.replace(bad, good)
        if content != original:
            fixes.append(f"AUTO-FIX: Added missing backslash escapes in {call}('{original[:40]}...')")
        return f"{call}('{content}'"
    return pattern.sub(replacer, code)


def _fix_bottom_zone_bottom(code: str, fixes: list[str]) -> str:
    """
    Auto-fix: bottom_center = np.array([0, bottom_zone_bottom, 0])
           → bottom_center = np.array([0, bottom_zone_center_y, 0])
    This is the #1 most common layout bug — safe to auto-fix unconditionally.
    """
    pattern = re.compile(
        r'bottom_center\s*=\s*np\.array\(\[0,\s*bottom_zone_bottom\s*,\s*0\]\)'
    )
    if pattern.search(code):
        fixes.append(
            "AUTO-FIX: bottom_center np.array used bottom_zone_bottom → bottom_zone_center_y"
        )
        code = pattern.sub(
            'bottom_center = np.array([0, bottom_zone_center_y, 0])',
            code
        )
    return code


def _fix_include_numbers_in_axis_config(code: str, fixes: list[str]) -> str:
    """
    Auto-fix: Remove 'include_numbers': True/False from axis_config dict.
    (It should only be in x_axis_config / y_axis_config.)

    This targets the pattern:
        axis_config={
            ...
            'include_numbers': True,
            ...
        }
    and removes just that key-value pair.
    """
    # Match 'include_numbers': True or False inside axis_config={...}
    # We'll use a simple line-by-line approach for safety
    lines = code.splitlines()
    in_axis_config = False
    result_lines = []
    for line in lines:
        # Detect entering axis_config (but not x_axis_config or y_axis_config)
        if re.search(r'\baxis_config\s*=\s*\{', line) and \
           not re.search(r'[xy]_axis_config', line):
            in_axis_config = True
        if in_axis_config:
            if '}' in line:
                in_axis_config = False
            if re.search(r"'include_numbers'\s*:", line):
                fixes.append(
                    f"AUTO-FIX: Removed 'include_numbers' from axis_config: {line.strip()}"
                )
                continue  # skip this line
        result_lines.append(line)
    return '\n'.join(result_lines)


# ─────────────────────────────────────────────────────────────────────────────
# Phase 2 helpers — violation detectors (things we can't safely auto-fix)
# ─────────────────────────────────────────────────────────────────────────────

def _detect_latex_in_text(lines: list[str]) -> list[Violation]:
    """Detect LaTeX syntax \\( \\) or \\[ \\] inside Text() calls."""
    violations = []
    # Pattern: Text('...  \\( or \\[  ...')
    pattern = re.compile(r'Text\s*\(.*?(\\\\[\(\[\\]|\\\\lambda|\\\\phi|\\\\Delta|\\\\frac)')
    for i, line in enumerate(lines, 1):
        if 'Text(' in line and re.search(r'\\\\[\(\[a-zA-Z]', line):
            m = pattern.search(line)
            if m:
                violations.append(Violation(
                    rule="LATEX_IN_TEXT",
                    line=i,
                    snippet=line.strip()[:80],
                    description=(
                        "พบ LaTeX syntax ใน Text() เช่น \\\\(\\\\lambda\\\\) — "
                        "ต้องแยกเป็น VGroup(Text('...'), MathTex(r'(\\lambda)')) แทน"
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
    r"""Detect Thai characters inside \mathrm{...}."""
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
                        "\\mathrm{} รองรับเฉพาะ ASCII เท่านั้น ต้องแยกออกเป็น Text()"
                    )
                ))
    return violations


def _detect_overlapping_labels(lines: list[str]) -> list[Violation]:
    """
    Detect high-risk annotation placement patterns:
    - Labels with .next_to(axes, UR/UL/DR/DL, buff=...) that are placed
      relative to the whole axes object (not a specific point on it),
      which almost always causes overlap in the narrow 9:16 frame.
    - Multiple labels using the same direction from the same reference point.
    """
    violations = []
    # Track labels placed next_to the same reference in the same direction
    placement_map: dict[str, list[int]] = {}  # "ref_direction" → [line numbers]

    next_to_pattern = re.compile(
        r'\.next_to\(\s*(\w+)\s*,\s*(UR|UL|DR|DL|UP|DOWN|LEFT|RIGHT)\s*'
    )
    for i, line in enumerate(lines, 1):
        for m in next_to_pattern.finditer(line):
            ref = m.group(1)
            direction = m.group(2)
            key = f"{ref}_{direction}"
            if key not in placement_map:
                placement_map[key] = []
            placement_map[key].append(i)

    for key, line_nums in placement_map.items():
        if len(line_nums) >= 3:  # 3 or more labels in same direction from same ref
            ref, direction = key.rsplit('_', 1)
            violations.append(Violation(
                rule="OVERLAPPING_LABELS",
                line=line_nums[0],
                snippet=f"บรรทัด {line_nums}: .next_to({ref}, {direction}, ...)",
                description=(
                    f"มี {len(line_nums)} labels ที่ถูก .next_to({ref}, {direction}) "
                    f"ในทิศเดียวกัน (บรรทัด {line_nums}) — จะทับซ้อนกัน "
                    "ต้องกระจายทิศทาง หรือวางด้วย .next_to(จุดบนกราฟจริง, direction)"
                )
            ))
    return violations


def _detect_axes_too_large(lines: list[str]) -> list[Violation]:
    """
    Detect x_length or y_length values hardcoded larger than the allowed limits.
    Allowed: x_length ≤ frame_width * 0.65 = 9.0 * 0.65 = 5.85
             y_length ≤ middle_zone_height * 0.65 = 7.2 * 0.65 = 4.68
    """
    violations = []
    for i, line in enumerate(lines, 1):
        # Check for x_length = <number>
        m = re.search(r'x_length\s*=\s*([0-9.]+)', line)
        if m:
            try:
                val = float(m.group(1))
                if val > 5.9:
                    violations.append(Violation(
                        rule="AXES_TOO_LARGE",
                        line=i,
                        snippet=line.strip()[:80],
                        description=(
                            f"x_length={val} เกินขีดจำกัด 5.85 (frame_width*0.65) "
                            "จะทำให้ Y-axis labels หลุดขอบซ้าย — ต้องใช้ frame_width * 0.60"
                        )
                    ))
            except ValueError:
                pass
        m = re.search(r'y_length\s*=\s*([0-9.]+)', line)
        if m:
            try:
                val = float(m.group(1))
                if val > 4.8:
                    violations.append(Violation(
                        rule="AXES_TOO_LARGE",
                        line=i,
                        snippet=line.strip()[:80],
                        description=(
                            f"y_length={val} เกินขีดจำกัด 4.68 (middle_zone_height*0.65) "
                            "จะทำให้ X-axis label หลุดขอบล่าง — ต้องใช้ middle_zone_height * 0.65"
                        )
                    ))
            except ValueError:
                pass
    return violations


def _detect_font_size_too_large(lines: list[str]) -> list[Violation]:
    """
    Detect font_size values that violate the hard limits:
    - Equations/titles: max 28
    - Graph labels: max 18 (only if inside get_x/y_axis_label or annotation)
    """
    violations = []
    for i, line in enumerate(lines, 1):
        m = re.search(r'font_size\s*=\s*([0-9]+)', line)
        if m:
            try:
                size = int(m.group(1))
                # Check if this is an equation/title context (MathTex or step Text)
                is_equation = 'MathTex(' in line or ('Text(' in line and 'font_size' in line)
                if is_equation and size > 30:
                    violations.append(Violation(
                        rule="FONT_TOO_LARGE",
                        line=i,
                        snippet=line.strip()[:80],
                        description=(
                            f"font_size={size} เกิน 28 (ขีดจำกัดสำหรับสมการ/หัวข้อ) "
                            "จะทำให้เนื้อหาล้นโซน — ต้องใช้ font_size=26-28"
                        )
                    ))
            except ValueError:
                pass
    return violations


def _detect_missing_numpy_import(lines: list[str]) -> list[Violation]:
    """Detect if import numpy as np is missing from first few lines."""
    first_lines = '\n'.join(lines[:5])
    if 'import numpy as np' not in first_lines:
        return [Violation(
            rule="MISSING_NUMPY",
            line=1,
            snippet=lines[0].strip() if lines else '',
            description=(
                "ไม่มี 'import numpy as np' ใน 5 บรรทัดแรก — "
                "จะทำให้เกิด NameError: name 'np' is not defined"
            )
        )]
    return []


def _detect_move_to_scalar(lines: list[str]) -> list[Violation]:
    """
    Detect .move_to() calls with scalar values (not np.array).
    e.g. .move_to(middle_zone_center_y) where the value is a plain float.
    """
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
                description=(
                    f".move_to({varname}) ส่ง scalar float ให้ Manim — "
                    f"ต้องเป็น np.array([0, {varname}, 0]) แทน"
                )
            ))
    return violations


# ─────────────────────────────────────────────────────────────────────────────
# Main public function
# ─────────────────────────────────────────────────────────────────────────────

def preprocess_code(code_string: str) -> ValidationResult:
    """
    Run all auto-fixes and violation checks on Gemini-generated Manim code.

    Returns a ValidationResult with:
      - fixed_code: the code after all safe auto-fixes have been applied
      - violations: list of Violation objects for things needing LLM rewrite
      - auto_fixes: list of human-readable descriptions of changes made

    Intended usage in manim_engine.py:

        result = preprocess_code(code_string)

        # Log all auto-fixes applied
        for fix in result.auto_fixes:
            logger.info(f"  {fix}")

        # If violations remain, include them in the Gemini fix prompt
        if result.has_violations:
            logger.warning(f"{len(result.violations)} violations found — sending to Gemini")
            # Use result.violation_summary() in the fix prompt
            return result.fixed_code, result.violation_summary()

        return result.fixed_code, None
    """
    auto_fixes: list[str] = []

    # ── Phase 1: Auto-fix ────────────────────────────────────────────────────
    code = code_string
    code = _fix_bottom_zone_bottom(code, auto_fixes)
    code = _fix_include_numbers_in_axis_config(code, auto_fixes)
    code = _fix_text_in_mathtex(code, auto_fixes)
    code = _fix_single_backslash_lambda(code, auto_fixes)
    code = _fix_latex_escape_in_text(code, auto_fixes)

    # ── Phase 2: Detect remaining violations ─────────────────────────────────
    lines = code.splitlines()
    violations: list[Violation] = []
    violations.extend(_detect_missing_numpy_import(lines))
    violations.extend(_detect_thai_in_mathtex(lines))
    violations.extend(_detect_thai_in_mathrm(lines))
    violations.extend(_detect_latex_in_text(lines))
    violations.extend(_detect_move_to_scalar(lines))
    violations.extend(_detect_axes_too_large(lines))
    violations.extend(_detect_font_size_too_large(lines))
    violations.extend(_detect_overlapping_labels(lines))

    return ValidationResult(
        fixed_code=code,
        violations=violations,
        auto_fixes=auto_fixes,
    )