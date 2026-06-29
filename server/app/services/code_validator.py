"""
server/app/services/code_validator.py

Deterministic pre-processor for Gemini-generated Manim code.
Runs BEFORE the render attempt and BEFORE the Gemini retry loop.

PHILOSOPHY: Fix as much as possible deterministically so Gemini retries
are only needed for structural rewrites, not trivial pattern fixes.

Two-phase approach:
  Phase 1 — Auto-fix: patterns we can correct safely without LLM help
  Phase 2 — Violation report: things that need LLM rewrite

NEW in v2: Massively expanded Phase 1 to auto-fix the most common
violation patterns that Gemini keeps generating:
  - VGroup(*[...list comprehension...]) → expanded VGroup(Text(...), Text(...))
  - Text('...\\lambda...') → VGroup(Text('...'), MathTex(r'\\lambda'))
  - step_title VGroup with .arrange(RIGHT) on long Thai + symbol → .arrange(DOWN)
  - Trailing backslash issues in MathTex strings
  - Thai in \\mathrm{} → extracted to Text()
"""

import re
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


# ── NEW: Fix VGroup(*[Text(...) for line in [...]]) ─────────────────────────
def _fix_vgroup_list_comprehension(code: str, fixes: list[str]) -> str:
    """
    Auto-fix VGroup(*[Text(line, ...) for line in ['a', 'b', 'c']]) →
    VGroup(Text('a', ...), Text('b', ...), Text('c', ...))
    
    This handles the most common pattern Gemini generates.
    """
    # Pattern: VGroup(*[Text(var, ...kwargs...) for var in ['str1', 'str2', ...]])
    pattern = re.compile(
        r'VGroup\s*\(\s*\*\s*\[\s*'           # VGroup(*[
        r'(\w+)\s*\(([\w_]+)\s*,\s*([^]]+?)\)'  # Text(var, ...kwargs...)
        r'\s*for\s+(\w+)\s+in\s+\[([^\]]+)\]'  # for var in [...]
        r'\s*\]\s*\)',                           # ])
        re.DOTALL
    )
    
    def replacer(m):
        ctor = m.group(1)          # e.g. "Text"
        # m.group(2) is var name in comprehension (unused since we inline)
        kwargs_str = m.group(3).strip()  # e.g. font='TH Sarabun New', font_size=26
        # m.group(4) is the loop variable name
        items_str = m.group(5)     # e.g. 'line1', 'line2', 'line3'
        
        # Extract string literals from the list
        items = re.findall(r"'([^']*)'|\"([^\"]*)\"", items_str)
        strings = [a or b for a, b in items]
        
        if not strings:
            return m.group(0)  # Can't parse, leave as-is
        
        # Build expanded VGroup
        parts = [f"{ctor}('{s}', {kwargs_str})" for s in strings]
        result = 'VGroup(\n' + ',\n'.join(f'            {p}' for p in parts) + '\n        )'
        fixes.append(
            f"AUTO-FIX: Expanded VGroup(*[{ctor}(var, ...) for var in [...]]) "
            f"→ VGroup({ctor}(...), ...) with {len(strings)} items"
        )
        return result
    
    new_code = pattern.sub(replacer, code)
    
    # Also handle: variable = [...]; VGroup(*[Text(line, ...) for line in variable])
    # This is harder to detect, do a simpler pass for the common case
    # where problem_lines or similar variable is defined then used
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
    
    # Find all list variable definitions
    list_vars = {}
    for vm in var_list_pattern.finditer(new_code):
        var_name = vm.group(1)
        items_block = vm.group(2)
        strings = re.findall(r"'([^']*)'", items_block)
        if strings:
            list_vars[var_name] = strings
    
    # Now replace VGroup(*[Text(line, ...) for line in list_var])
    def comprehension_replacer(m):
        ctor = m.group(1)
        # m.group(2) is loop var name
        kwargs_str = m.group(3).strip()
        # m.group(4) is loop var
        list_name = m.group(5)
        
        if list_name not in list_vars:
            return m.group(0)  # Can't resolve, leave
        
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


# ── NEW: Fix LaTeX symbols in Text() calls ───────────────────────────────────
def _fix_latex_in_text_calls(code: str, fixes: list[str]) -> str:
    """
    Auto-fix Text('...\\lambda...') patterns.
    
    Strategy:
    - If the Text contains a LaTeX symbol like \\lambda, \\phi, etc. embedded
      in an otherwise Thai string, we replace the LaTeX symbol with its
      Thai/readable equivalent or split into VGroup.
    
    For step titles like: Text('หาความยาวคลื่น (\\lambda)', ...)
    → Split into VGroup:
      VGroup(
        Text('หาความยาวคลื่น (', ...),
        MathTex(r'\\lambda', ...),
        Text(')', ...),
      ).arrange(RIGHT, buff=0.05)
    
    Simpler approach: replace \\lambda etc. with unicode or readable text
    inside Text() since the symbol will just be decorative context in a title.
    """
    # Map LaTeX symbols to Unicode/readable equivalents for use in Text()
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
        r'\\vec': '',      # remove \vec from text context
        r'\\hat': '',      # remove \hat from text context
        r'\\frac': '/',    # frac becomes /
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
        r'\\mathrm': '',   # \mathrm{x} → just leave x (handled below)
        r'\\mathbf': '',
    }
    
    lines = code.splitlines()
    result_lines = []
    
    for line in lines:
        # Only process lines with Text( that also have backslash sequences
        if 'Text(' in line and '\\\\' in line:
            # Find all Text('...') calls on this line
            # Pattern: Text('content', rest_of_args)
            text_pattern = re.compile(r"(Text\s*\(\s*')((?:[^'\\]|\\.)*)(')")
            
            def text_replacer(m):
                prefix = m.group(1)   # Text('
                content = m.group(2)  # the string content
                suffix = m.group(3)   # closing '
                
                original_content = content
                modified = False
                
                # Replace LaTeX symbols with unicode in the content
                for latex, uni in latex_to_unicode.items():
                    # Match \\symbol or \\symbol{...}
                    if latex + '{' in content:
                        # Handle \mathrm{x}, \mathbf{x} etc - just keep the content
                        brace_pat = re.compile(re.escape(latex) + r'\{([^}]*)\}')
                        content = brace_pat.sub(r'\1', content)
                        modified = True
                    elif latex in content:
                        content = content.replace(latex, uni)
                        modified = True
                
                # Clean up leftover braces from removed commands
                content = re.sub(r'\{([^}]*)\}', r'\1', content)
                
                if modified:
                    fixes.append(
                        f"AUTO-FIX: Replaced LaTeX symbols with unicode in Text('{original_content[:40]}...')"
                    )
                
                return prefix + content + suffix
            
            line = text_pattern.sub(text_replacer, line)
        
        result_lines.append(line)
    
    return '\n'.join(result_lines)


# ── NEW: Fix Thai in \mathrm{} ────────────────────────────────────────────────
def _fix_thai_in_mathrm(code: str, fixes: list[str]) -> str:
    """
    Auto-fix \\mathrm{ภาษาไทย} → just remove the \\mathrm{} wrapper
    since Thai can't be in mathrm anyway. The content remains as bare text
    which will cause issues, but at least it won't crash LaTeX immediately.
    
    For cases like: MathTex(r'\\mathrm{ก.\,} t = 5')
    We can't easily split these deterministically, so we flag them but also
    try to do a best-effort fix by stripping the Thai from mathrm.
    """
    thai_range = re.compile(r'[\u0E00-\u0E7F]')
    mathrm_with_thai = re.compile(r'\\\\?mathrm\{([^}]*[\u0E00-\u0E7F][^}]*)\}')
    
    def replacer(m):
        content = m.group(1)
        # Strip Thai characters, keep ASCII
        ascii_content = ''.join(c for c in content if ord(c) < 128)
        if ascii_content.strip():
            fixes.append(f"AUTO-FIX: \\mathrm{{{content[:20]}}} - removed Thai chars, kept ASCII")
            return f'\\\\mathrm{{{ascii_content}}}'
        else:
            fixes.append(f"AUTO-FIX: \\mathrm{{{content[:20]}}} - all Thai, removed \\mathrm wrapper")
            return content
    
    return mathrm_with_thai.sub(replacer, code)


# ── NEW: Fix step_title VGroup with LaTeX in Text ───────────────────────────
def _fix_step_title_latex(code: str, fixes: list[str]) -> str:
    """
    Fix the very common Gemini pattern:
    
    step1_title = VGroup(
        Text('ขั้นตอนที่ 1:', ...),
        Text('หาความยาวคลื่น (\\lambda)', ...),   ← LaTeX in Text!
    ).arrange(RIGHT, buff=0.15)
    
    → Replace the Text with LaTeX symbol with a version using unicode
    (already handled by _fix_latex_in_text_calls, but this targets
    the specific VGroup step_title pattern for better messaging)
    """
    # This is now handled by _fix_latex_in_text_calls above
    # But add a specific fixer for the double-backslash pattern in step titles
    # Pattern: Text('...สัญลักษณ์... (\\\\symbol)', ...)
    
    # Double-backslash variants in Text strings (these are the most common)
    double_bs_symbols = {
        r'(\\\\lambda)': 'λ',
        r'(\\\\phi)': 'φ',
        r'(\\\\phi_': 'φ_',  # don't fully replace subscripts
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
                    # Find Text('...') strings and do replacement inside them
                    def make_replacer(rep):
                        def replacer(m):
                            # m is from Text('...') match
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
    """
    Auto-fix .move_to(scalar_var) → .move_to(np.array([0, scalar_var, 0]))
    for common zone center variable names.
    """
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


def _fix_missing_numpy_import(code: str, fixes: list[str]) -> str:
    """Add import numpy as np if missing from first 5 lines."""
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
    """Auto-fix axes.get_graph() → axes.plot() (simple cases only)."""
    pattern = re.compile(r'\.get_graph\s*\(')
    if pattern.search(code):
        fixes.append("AUTO-FIX: .get_graph() → .plot()")
        code = pattern.sub('.plot(', code)
    return code


def _fix_double_quote_in_strings(code: str, fixes: list[str]) -> str:
    """
    Fix Text("...") using double quotes → Text('...')
    Only in Text() and MathTex() calls, not in general code.
    This handles the case where Gemini uses double quotes inside Python code.
    """
    # This is risky to do broadly - only fix obvious cases
    # Pattern: Text("content") → Text('content')
    # But only when there are no single quotes inside the content
    pattern = re.compile(r'((?:Text|MathTex|Tex)\s*\()"([^"]*)"')
    
    def replacer(m):
        if "'" in m.group(2):
            return m.group(0)  # Has single quotes inside, skip
        fixes.append(f"AUTO-FIX: Double-quoted string in {m.group(1)} → single quotes")
        return f"{m.group(1)}'{m.group(2)}'"
    
    return pattern.sub(replacer, code)


def _fix_arrange_right_long_thai(code: str, fixes: list[str]) -> str:
    """
    Auto-fix .arrange(RIGHT) on VGroups that contain long Thai Text objects.
    Change to .arrange(DOWN, aligned_edge=LEFT) to prevent overflow.
    
    This handles patterns like:
      step1_title = VGroup(
          Text('ขั้นตอนที่ 1: หาความยาวคลื่น...', ...),  # long Thai
          MathTex(r'\\lambda', ...)
      ).arrange(RIGHT, buff=0.15)   ← THIS causes overflow
    """
    thai_long = re.compile(r'[\u0E00-\u0E7F]{15,}')
    
    # Look for VGroup blocks ending with .arrange(RIGHT, ...)
    # This is a multi-line pattern
    lines = code.splitlines()
    result_lines = list(lines)  # copy
    
    i = 0
    while i < len(lines):
        line = lines[i]
        
        # Check if this line has .arrange(RIGHT
        if '.arrange(RIGHT' in line or '.arrange( RIGHT' in line:
            # Scan backward to find the VGroup opening and check for long Thai
            has_long_thai = False
            for back in range(i, max(i - 20, 0), -1):
                if thai_long.search(lines[back]) and 'Text(' in lines[back]:
                    has_long_thai = True
                    break
                if 'VGroup(' in lines[back]:
                    break
            
            if has_long_thai:
                # Replace .arrange(RIGHT, buff=...) with .arrange(DOWN, aligned_edge=LEFT, buff=0.15)
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
    """Remove font= parameter from MathTex/Tex calls (not supported)."""
    pattern = re.compile(r"((?:MathTex|Tex)\s*\([^)]*),\s*font\s*=\s*'[^']*'([^)]*\))")
    if pattern.search(code):
        fixes.append("AUTO-FIX: Removed font= parameter from MathTex/Tex (not supported)")
        code = pattern.sub(r'\1\2', code)
    return code


def _fix_mathrm_curly_braces(code: str, fixes: list[str]) -> str:
    """
    Fix \\mathrm{} with no content or broken braces inside MathTex strings.
    """
    # Fix \\mathrm{} → nothing
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
    # After auto-fix, only flag if there are actual LaTeX sequences remaining
    latex_in_text = re.compile(
        r'Text\s*\([^)]*(?:'
        r'\\\\(?:frac|sqrt|sum|int|prod|lim|partial)'  # Complex LaTeX that can't be unicode-ified
        r'|\\\\[\(\[\\]'             # \\( \\[ \\\ delimiters
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
            # Skip lines where Thai is in a comment
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


def _detect_latex_in_text_calls(lines: list[str]) -> list[Violation]:
    """Detect remaining LaTeX escapes in Text() after all auto-fixes."""
    violations = []
    # Only flag complex LaTeX that truly can't be rendered in Text()
    pattern = re.compile(
        r'Text\s*\([^)]*\\(?:frac|sqrt|sum|int|partial|binom)[^)]*\)'
    )
    for i, line in enumerate(lines, 1):
        if 'Text(' in line and pattern.search(line):
            violations.append(Violation(
                rule="LATEX_ESCAPE_IN_TEXT",
                line=i,
                snippet=line.strip()[:80],
                description=(
                    "พบ LaTeX complex (\\frac, \\sqrt ฯลฯ) ใน Text() — "
                    "ต้องแยกเป็น MathTex() แล้วรวมด้วย VGroup"
                )
            ))
    return violations


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
    
    # 2. Variable/value fixes
    code = _fix_bottom_zone_bottom(code, auto_fixes)
    code = _fix_move_to_scalar(code, auto_fixes)
    code = _fix_include_numbers_in_axis_config(code, auto_fixes)
    
    # 3. String content fixes (order: most specific first)
    code = _fix_vgroup_list_comprehension(code, auto_fixes)  # ← KEY NEW FIX
    code = _fix_latex_in_text_calls(code, auto_fixes)         # ← KEY NEW FIX
    code = _fix_step_title_latex(code, auto_fixes)            # ← KEY NEW FIX
    code = _fix_thai_in_mathrm(code, auto_fixes)              # ← KEY NEW FIX
    code = _fix_arrange_right_long_thai(code, auto_fixes)     # ← KEY NEW FIX
    code = _fix_text_in_mathtex(code, auto_fixes)
    code = _fix_single_backslash_lambda(code, auto_fixes)
    code = _fix_latex_escape_in_text(code, auto_fixes)
    code = _fix_mathrm_curly_braces(code, auto_fixes)
    code = _fix_double_quote_in_strings(code, auto_fixes)

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
    violations.extend(_detect_final_answer_arrange_right(lines))
    violations.extend(_detect_vgroup_list_comprehension(lines))
    violations.extend(_detect_unbalanced_latex_braces(lines))
    violations.extend(_detect_latex_in_text_calls(lines))

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