"""
server/app/services/scene_compiler.py

Turns a validated EpisodeData (see app.core.episode_schema) into a complete,
working Manim scene file, as a list of source lines (same return shape the
old pipeline used for manim_code_lines, so manim_engine.py's downstream
_write_scene_file/_run_manim/etc. don't need to change).

DESIGN RULE: every Thai/LaTeX string from Gemini is embedded via Python's
own repr(), never by hand-building an r'...' literal. repr() is guaranteed
to produce Python source that, when parsed, reconstructs the EXACT original
string — arbitrary backslashes, quotes, Thai text, all of it — with zero
manual escaping logic on our part. This is what eliminates the whole class
of "Gemini forgot the r-prefix" / "backslash got doubled wrong" bugs for
everything that goes through this compiler: there's no escaping to get
wrong, because we never hand-write the escaping at all.

IMPORTANT: do NOT run code_validator.preprocess_code() over this compiler's
OUTPUT. Its string-content fixer assumes a *raw*-string convention (r'...')
and will actively corrupt correctly-repr()-escaped non-raw content — for
example it would collapse a legitimately-doubled backslash that repr()
produced for a non-raw string down to one, breaking it. Only ever validate
the diagram_code_lines FRAGMENT before compiling (see manim_engine.py) —
never the compiler's own text, which is trusted by construction.
"""
from __future__ import annotations

from app.core.episode_schema import EpisodeData, EquationStep

IND = "        "  # 8 spaces — matches construct()'s body indentation

_MIN_STEP_DURATION = 1.5
_MAX_STEP_DURATION = 6.0

BOILERPLATE_HEADER = [
    "import numpy as np",
    "from manim import *",
    "",
    "config.pixel_width = 1080",
    "config.pixel_height = 1920",
    "config.frame_height = 16.0",
    "config.frame_width = 9.0",
    "config.frame_rate = 60",
    "",
    "class PhysicsScene(Scene):",
    "    def construct(self):",
    "        self.camera.background_color = '#1C1C2E'",
    "        frame_height = config.frame_height",
    "        frame_width = config.frame_width",
    "        top_zone_height = frame_height * 0.20",
    "        middle_zone_height = frame_height * 0.45",
    "        bottom_zone_height = frame_height * 0.35",
    "        top_zone_top = frame_height / 2",
    "        top_zone_bottom = top_zone_top - top_zone_height",
    "        top_zone_center_y = (top_zone_top + top_zone_bottom) / 2",
    "        middle_zone_top = top_zone_bottom",
    "        middle_zone_bottom = middle_zone_top - middle_zone_height",
    "        middle_zone_center_y = (middle_zone_top + middle_zone_bottom) / 2",
    "        bottom_zone_top = middle_zone_bottom",
    "        bottom_zone_bottom = bottom_zone_top - bottom_zone_height",
    "        bottom_zone_center_y = (bottom_zone_top + bottom_zone_bottom) / 2",
    "        top_center = np.array([0, top_zone_center_y, 0])",
    "        middle_center = np.array([0, middle_zone_center_y, 0])",
    "        bottom_center = np.array([0, bottom_zone_center_y, 0])",
]


def _kwargs_str(**kwargs) -> str:
    return ", ".join(f"{k}={v}" for k, v in kwargs.items())


def _text_call(content: str, **kwargs) -> str:
    """Text(<repr'd content>, font='TH Sarabun New', ...)"""
    kw = _kwargs_str(font="'TH Sarabun New'", **kwargs)
    return f"Text({content!r}, {kw})"


def _mathtex_call(latex: str, **kwargs) -> str:
    """MathTex(<repr'd latex>, ...). No r-prefix — repr() makes it
    unnecessary; see module docstring."""
    kw = _kwargs_str(**kwargs)
    return f"MathTex({latex!r}, {kw})" if kw else f"MathTex({latex!r})"


def _clamp_duration(seconds: float) -> float:
    return max(_MIN_STEP_DURATION, min(_MAX_STEP_DURATION, seconds))


def _build_top_zone(title: str, problem_desc: str) -> list[str]:
    lines = [f"{IND}title = {_text_call(title, font_size=28, color='GOLD_B')}"]
    if problem_desc.strip():
        lines += [
            f"{IND}problem_desc = {_text_call(problem_desc, font_size=24, color='GRAY_A')}",
            f"{IND}top_group = VGroup(title, problem_desc).arrange(DOWN, aligned_edge=LEFT, buff=0.1)",
        ]
    else:
        lines.append(f"{IND}top_group = VGroup(title)")
    lines += [
        f"{IND}top_group.scale_to_fit_width(frame_width * 0.88)",
        f"{IND}if top_group.height > top_zone_height * 0.88:",
        f"{IND}    top_group.scale_to_fit_height(top_zone_height * 0.88)",
        f"{IND}top_group.move_to(top_center)",
        f"{IND}self.play(FadeIn(top_group, shift=UP*0.15))",
        f"{IND}self.wait(1.0)",
        "",
    ]
    return lines


def _build_step_group(step: EquationStep, var_name: str) -> list[str]:
    """One VGroup(...) holding a step's title + equation lines, laid out
    top-to-bottom always (never side-by-side) — this is the deterministic
    layout choice the compiler enforces instead of leaving it to Gemini,
    which is what makes the old .arrange(RIGHT)-with-long-Thai overflow bug
    structurally impossible here."""
    lines = [f"{IND}{var_name}_title = {_text_call(step.title, font_size=26, color='GOLD_B')}"]
    member_names = [f"{var_name}_title"]

    for i, eq_line in enumerate(step.lines):
        eq_var = f"{var_name}_eq{i}"
        if eq_line.label:
            label_var = f"{eq_var}_label"
            lines.append(f"{IND}{label_var} = {_text_call(eq_line.label, font_size=20, color='GRAY_A')}")
            lines.append(f"{IND}{eq_var}_math = {_mathtex_call(eq_line.latex, font_size=20, color='WHITE')}")
            lines.append(
                f"{IND}{eq_var} = VGroup({label_var}, {eq_var}_math)"
                f".arrange(DOWN, aligned_edge=LEFT, buff=0.05)"
            )
        else:
            lines.append(f"{IND}{eq_var} = {_mathtex_call(eq_line.latex, font_size=20, color='WHITE')}")
        member_names.append(eq_var)

    members = ", ".join(member_names)
    lines.append(f"{IND}{var_name} = VGroup({members}).arrange(DOWN, aligned_edge=LEFT, buff=0.15)")
    lines.append(f"{IND}{var_name}.scale_to_fit_width(frame_width * 0.88)")
    lines.append(f"{IND}if {var_name}.height > bottom_zone_height * 0.88:")
    lines.append(f"{IND}    {var_name}.scale_to_fit_height(bottom_zone_height * 0.88)")
    lines.append(f"{IND}{var_name}.move_to(bottom_center)")
    return lines


def _build_bottom_zone_steps(steps: list[EquationStep]) -> list[str]:
    """Deterministic fade-out-previous / fade-in-current choreography,
    looped over however many steps there are — 1 step and 8 steps both
    work correctly, unlike a template with a fixed number of named blanks."""
    if not steps:
        return []

    lines: list[str] = []
    prev_var: str | None = None

    for i, step in enumerate(steps):
        var_name = f"step{i + 1}_group"
        lines.append(f"{IND}# Step {i + 1}")
        lines.extend(_build_step_group(step, var_name))

        if prev_var is not None:
            lines.append(f"{IND}self.play(FadeOut({prev_var}, shift=DOWN*0.15))")
        lines.append(f"{IND}self.play(FadeIn({var_name}, shift=UP*0.15))")
        lines.append(f"{IND}self.wait({_clamp_duration(step.duration_seconds)})")
        lines.append("")

        prev_var = var_name

    return lines


def compile_scene(episode: EpisodeData, validated_diagram_lines: list[str]) -> list[str]:
    """
    Assemble the final scene source. `validated_diagram_lines` must already
    have gone through code_validator.preprocess_code() as its own fragment
    (see manim_engine.py) — this function does not validate it again.
    """
    lines: list[str] = list(BOILERPLATE_HEADER)
    lines.append("")
    lines.append(f"{IND}# --- Top zone (compiler-generated) ---")
    lines.extend(_build_top_zone(episode.title, episode.problem_desc))

    lines.append(f"{IND}# --- Middle zone: diagram (Gemini-generated, validated) ---")
    lines.extend(validated_diagram_lines)
    lines.append("")

    lines.append(f"{IND}# --- Bottom zone: equation steps (compiler-generated) ---")
    lines.extend(_build_bottom_zone_steps(episode.steps))

    return lines