"""
server/app/services/code_validator.py

Deterministic pre-processor for Gemini-generated Manim code.
Runs BEFORE the render attempt and BEFORE the Gemini retry loop.

PHILOSOPHY: Fix as much as possible deterministically so Gemini retries
are only needed for structural rewrites, not trivial pattern fixes.

Two-phase approach:
  Phase 1 — Auto-fix: patterns we can correct safely without LLM help
  Phase 2 — Violation report: things that need LLM rewrite
"""

import re
import ast
import builtins as _builtins_module
from dataclasses import dataclass, field


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
        
        parts = [f"{ctor}('{s}', {kwargs_str})" for s in strings]
        result = 'VGroup(\n' + ',\n'.join(f'            {p}' for p in parts) + '\n        )'
        fixes.append(
            f"AUTO-FIX: Expanded VGroup(*[{ctor}(var, ...) for var in [...]]) "
            f"→ VGroup({ctor}(...), ...) with {len(strings)} items"
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
        parts = [f"{ctor}('{s}', {kwargs_str})" for s in strings]
        result = 'VGroup(\n' + ',\n'.join(f'            {p}' for p in parts) + '\n        )'
        fixes.append(
            f"AUTO-FIX: Resolved VGroup(*[{ctor}(line, ...) for line in {list_name}]) "
            f"→ VGroup({ctor}(...), ...) with {len(strings)} items"
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
    """Clamp x_length/y_length on Axes(...) calls to safe limits."""
    def x_replacer(m):
        val = float(m.group(1))
        if val > 5.85:
            fixes.append(f"AUTO-FIX: x_length={val} > 5.85 → clamped to 5.85")
            return "x_length=5.85"
        return m.group(0)

    def y_replacer(m):
        val = float(m.group(1))
        if val > 4.68:
            fixes.append(f"AUTO-FIX: y_length={val} > 4.68 → clamped to 4.68")
            return "y_length=4.68"
        return m.group(0)

    code = re.sub(r'x_length\s*=\s*([0-9.]+)', x_replacer, code)
    code = re.sub(r'y_length\s*=\s*([0-9.]+)', y_replacer, code)
    return code


def _fix_font_size_too_large(code: str, fixes: list[str]) -> str:
    """Clamp font_size on Text()/MathTex() calls to 28."""
    pattern = re.compile(
        r'((?:Text|MathTex)\s*\([^)]*?font_size\s*=\s*)([0-9]+)'
    )

    def replacer(m):
        size = int(m.group(2))
        if size > 28:
            fixes.append(f"AUTO-FIX: font_size={size} > 28 → clamped to 28")
            return f"{m.group(1)}28"
        return m.group(0)

    return pattern.sub(replacer, code)


def _fix_missing_numpy_import(code: str, fixes: list[str]) -> str:
    """Add import numpy as np if missing."""
    lines = code.splitlines()
    first_block = '\n'.join(lines[:10])
    if 'import numpy as np' not in first_block:
        fixes.append("AUTO-FIX: Added 'import numpy as np' at top of file")
        return 'import numpy as np\n' + code
    return code


def _fix_showcreation(code: str, fixes: list[str]) -> str:
    """Auto-fix ShowCreation → Create."""
    if 'ShowCreation(' in code:
        fixes.append("AUTO-FIX: ShowCreation() → Create()")
        code = code.replace('ShowCreation(', 'Create(')
    return code


def _fix_get_graph(code: str, fixes: list[str]) -> str:
    """Auto-fix axes.get_graph() → axes.plot()."""
    pattern = re.compile(r'\.get_graph\s*\(')
    if pattern.search(code):
        fixes.append("AUTO-FIX: .get_graph() → .plot()")
        code = pattern.sub('.plot(', code)
    return code


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
    """Auto-fix deprecated TexMobject/TextMobject → MathTex/Text."""
    if 'TexMobject(' in code:
        fixes.append("AUTO-FIX: TexMobject() → MathTex()")
        code = code.replace('TexMobject(', 'MathTex(')
    if 'TextMobject(' in code:
        fixes.append("AUTO-FIX: TextMobject() → Text()")
        code = code.replace('TextMobject(', 'Text(')
    return code


def _fix_indicate_flash(code: str, fixes: list[str]) -> str:
    """Remove forbidden animations that crash Manim."""
    replacements = [
        ('Indicate(', 'FadeIn('),
        ('Flash(', 'GrowFromCenter('),
        ('ApplyWave(', 'FadeIn('),
    ]
    for old, new in replacements:
        if old in code:
            fixes.append(f"AUTO-FIX: {old} → {new} (forbidden animation)")
            code = code.replace(old, new)
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
                if val > 5.9:
                    violations.append(Violation(
                        rule="AXES_TOO_LARGE",
                        line=i,
                        snippet=line.strip()[:80],
                        description=f"x_length={val} เกิน 5.85 — ใช้ frame_width * 0.60"
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
                        description=f"y_length={val} เกิน 4.68 — ใช้ middle_zone_height * 0.65"
                    ))
            except ValueError:
                pass
    return violations


def _detect_font_size_too_large(lines: list[str]) -> list[Violation]:
    violations = []
    for i, line in enumerate(lines, 1):
        m = re.search(r'font_size\s*=\s*([0-9]+)', line)
        if m:
            try:
                size = int(m.group(1))
                is_equation = 'MathTex(' in line or 'Text(' in line
                if is_equation and size > 30:
                    violations.append(Violation(
                        rule="FONT_TOO_LARGE",
                        line=i,
                        snippet=line.strip()[:80],
                        description=f"font_size={size} เกิน 28 — ใช้ 26-28"
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


def _detect_undefined_variables(code: str) -> list[Violation]:
    """
    Catch NameError-causing bugs *before* Manim render: variables that are
    used (e.g. inside a VGroup(...) call) but never assigned anywhere in the
    script, or used before their first assignment.

    This exists mainly as a safety net for auto-fix/line-patch bugs that can
    silently drop a variable's definition line (e.g. a targeted Gemini patch
    that only echoes back the line it was asked to fix, dropping a sibling
    definition that happened to sit in the same context window). Catching it
    here means the pipeline gets another retry instead of a hard render crash.

    Deliberately conservative to avoid false positives:
      - Only checks bare lowercase/snake_case identifiers (regex
        ^[a-z_][a-z0-9_]*$). Manim/numpy library symbols are virtually always
        PascalCase (Text, VGroup, MathTex, Circle) or ALL_CAPS (UP, BLUE_D,
        ORIGIN), so this naturally excludes them without needing a full
        manim symbol table.
      - Whitelists Python builtins, any imported names, and a short list of
        known lowercase manim/numpy globals (self, config, np, and common
        rate functions) that are legitimately used without local assignment.
      - Only reports each offending name once, and only for the *first*
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

    assigned_at: dict[str, int] = {}
    imported: set[str] = set()

    def _record(name: str, lineno: int) -> None:
        if name not in assigned_at or lineno < assigned_at[name]:
            assigned_at[name] = lineno

    class DefCollector(ast.NodeVisitor):
        def visit_Import(self, node):
            for alias in node.names:
                imported.add(alias.asname or alias.name.split(".")[0])
            self.generic_visit(node)

        def visit_ImportFrom(self, node):
            for alias in node.names:
                if alias.name != "*":
                    imported.add(alias.asname or alias.name)
            self.generic_visit(node)

        def _record_targets(self, target, lineno):
            for n in ast.walk(target):
                if isinstance(n, ast.Name):
                    _record(n.id, lineno)

        def visit_Assign(self, node):
            for target in node.targets:
                self._record_targets(target, node.lineno)
            self.generic_visit(node)

        def visit_AugAssign(self, node):
            self._record_targets(node.target, node.lineno)
            self.generic_visit(node)

        def visit_AnnAssign(self, node):
            self._record_targets(node.target, node.lineno)
            self.generic_visit(node)

        def visit_For(self, node):
            self._record_targets(node.target, node.lineno)
            self.generic_visit(node)

        def visit_With(self, node):
            for item in node.items:
                if item.optional_vars:
                    self._record_targets(item.optional_vars, node.lineno)
            self.generic_visit(node)

        def visit_FunctionDef(self, node):
            _record(node.name, node.lineno)
            for arg in node.args.args:
                _record(arg.arg, node.lineno)
            self.generic_visit(node)

        def visit_Lambda(self, node):
            for arg in node.args.args:
                _record(arg.arg, node.lineno)
            self.generic_visit(node)

        def _comp(self, node):
            for gen in node.generators:
                self._record_targets(gen.target, node.lineno)
            self.generic_visit(node)

        visit_ListComp = _comp
        visit_SetComp = _comp
        visit_DictComp = _comp
        visit_GeneratorExp = _comp

    DefCollector().visit(tree)

    whitelist = set(dir(_builtins_module)) | imported | known_globals
    name_pattern = re.compile(r"^[a-z_][a-z0-9_]*$")
    reported: set[str] = set()

    class UseCollector(ast.NodeVisitor):
        def visit_Name(self, node):
            if isinstance(node.ctx, ast.Load):
                name = node.id
                if name not in whitelist and name_pattern.match(name) and name not in reported:
                    first_def = assigned_at.get(name)
                    if first_def is None:
                        violations.append(Violation(
                            rule="UNDEFINED_VARIABLE",
                            line=node.lineno,
                            snippet=name,
                            description=(
                                f"ตัวแปร '{name}' ถูกใช้งานแต่ไม่เคยถูกกำหนดค่าที่ไหนเลยในโค้ด "
                                "(อาจถูกลบทิ้งโดยไม่ได้ตั้งใจระหว่างการแก้บั๊กอัตโนมัติ) "
                                "จะทำให้เกิด NameError ตอนเรนเดอร์"
                            ),
                        ))
                        reported.add(name)
                    elif first_def > node.lineno:
                        violations.append(Violation(
                            rule="UNDEFINED_VARIABLE",
                            line=node.lineno,
                            snippet=name,
                            description=(
                                f"ตัวแปร '{name}' ถูกใช้งานที่บรรทัด {node.lineno} "
                                f"ก่อนที่จะถูกกำหนดค่าครั้งแรกที่บรรทัด {first_def} — "
                                "จะทำให้เกิด NameError ตอนเรนเดอร์"
                            ),
                        ))
                        reported.add(name)
            self.generic_visit(node)

    UseCollector().visit(tree)
    return violations


def _detect_missing_scaling(lines: list[str]) -> list[Violation]:
    """
    Detect VGroups in bottom/middle zone without scaling.

    NOTE: this used to decide "is this VGroup in the bottom/middle zone?" by
    checking whether the literal words "bottom" or "middle" appeared in the
    text of the VGroup's *assignment* line -- which only happens to be true
    if the variable itself is named with "bottom"/"middle" in it. Variables
    like `step1_group` or `prob_desc` never match, and variables like
    `bottom_zone_height` (a float, not a VGroup) can spuriously match other
    unrelated lines. This version instead checks whether the SAME variable
    is later moved to `bottom_center`/`middle_center` -- which is the actual
    definition of "being in that zone" -- and only then requires a scaling
    call on that variable.
    """
    violations = []

    vgroup_assign_pattern = re.compile(r'(\w+)\s*=\s*VGroup\(')
    zone_targets = ('bottom_center', 'middle_center')

    for i, line in enumerate(lines):
        m = vgroup_assign_pattern.search(line)
        if not m:
            continue
        var_name = m.group(1)
        if 'axes' in var_name.lower():
            continue  # Axes groups don't need scaling

        window = lines[max(0, i - 10):min(i + 15, len(lines))]
        window_text = "\n".join(window)

        in_zone = any(f'{var_name}.move_to({target})' in window_text for target in zone_targets)
        if not in_zone:
            continue  # not a bottom/middle-zone VGroup -- rule doesn't apply

        has_scaling = (
            f'{var_name}.scale_to_fit_width' in window_text
            or f'{var_name}.scale_to_fit_height' in window_text
        )
        if not has_scaling:
            violations.append(Violation(
                rule="MISSING_SCALING",
                line=i + 1,
                snippet=f"{var_name} = VGroup(...)",
                description=(
                    f"พบ VGroup {var_name} ในโซนล่าง/กลางแต่ไม่มี .scale_to_fit_width() — "
                    "อาจทำให้ข้อความล้นจอ ต้องเพิ่ม scaling"
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
            if size > 28:
                violations.append(Violation(
                    rule="FONT_SIZE_TOO_LARGE",
                    line=i,
                    snippet=line.strip()[:80],
                    description=f"font_size={size} ใน Text() — ต้อง ≤ 28"
                ))
        
        math_match = re.search(r'MathTex\([^)]*font_size\s*=\s*(\d+)', line)
        if math_match:
            size = int(math_match.group(1))
            if size > 28:
                violations.append(Violation(
                    rule="FONT_SIZE_TOO_LARGE",
                    line=i,
                    snippet=line.strip()[:80],
                    description=f"font_size={size} ใน MathTex() — ต้อง ≤ 28"
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
            if 'step_title' in line or 'eq' in line and 'MathTex' in line:
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

    # ── Phase 2: Detect remaining violations ─────────────────────────────────
    lines = code.splitlines()
    violations: list[Violation] = []
    
    # Existing validations
    violations.extend(_detect_missing_numpy_import(lines))
    violations.extend(_detect_thai_in_mathtex(lines))
    violations.extend(_detect_thai_in_mathrm(lines))
    violations.extend(_detect_latex_in_text(lines))
    violations.extend(_detect_move_to_scalar(lines))
    violations.extend(_detect_axes_too_large(lines))
    violations.extend(_detect_font_size_too_large(lines))
    violations.extend(_detect_overlapping_labels(lines))
    violations.extend(_detect_final_answer_arrange_right(lines))
    violations.extend(_detect_vgroup_list_comprehension(lines))
    violations.extend(_detect_unbalanced_latex_braces(lines))
    
    # New validations
    violations.extend(_detect_math_errors(lines))
    violations.extend(_detect_missing_scaling(lines))
    violations.extend(_detect_font_size_violations(lines))
    violations.extend(_detect_bottom_zone_empty(lines))
    violations.extend(_detect_undefined_variables(code))

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