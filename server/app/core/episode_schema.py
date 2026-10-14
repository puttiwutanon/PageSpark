"""
server/app/core/episode_schema.py

Structured episode schema for the template-based generation pipeline.

Replaces the old "Gemini writes the entire manim_code_lines as freeform
Python" approach for everything EXCEPT the middle-zone diagram. Title,
problem description, and equation steps are now DATA (this schema), turned
into Python by app/services/scene_compiler.py — a hand-written, tested
compiler that can never produce the font-size/aligned_edge/VGroup-comprehension
class of bugs, because Gemini never writes that Python at all.

The middle-zone diagram (diagram_code_lines) is still freeform Manim code —
diagrams are structurally different per problem type (a force junction vs.
a projectile parabola vs. a wave plot), so templating them all is a much
bigger project than this first step. diagram_code_lines still goes through
app.services.code_validator.preprocess_code() before being spliced into the
compiled scene, same as before.

Passed directly as `response_schema=` to the Gemini call (mirroring how
QuizResponseSchema already works in main.py's /api/generate-quiz), so the
shape is enforced by Gemini's controlled generation instead of hoped for —
smart_json_sanitize()/the multi-strategy JSON parser in main.py can stay as
a defensive fallback but should rarely be needed for this endpoint anymore.
"""
from __future__ import annotations

from typing import Literal, Optional

from pydantic import BaseModel, Field


class VideoPlan(BaseModel):
    estimated_duration_seconds: int
    visual_cues: str
    audio_cues: str


class ScriptBlock(BaseModel):
    hook: str
    main_body: str
    example_or_trick: str
    call_to_action: str


class VoiceoverSegment(BaseModel):
    segment_id: str
    phase: Literal["hook_problem", "diagram_explain", "step_solve", "cta"]
    thai_text: str
    start_time_seconds: float
    end_time_seconds: float
    start_frame: int
    end_frame: int
    synced_visual_action: str


class EquationLine(BaseModel):
    """One line of an equation step. `latex` is PLAIN LaTeX content only —
    no leading/trailing $, no MathTex(...) wrapper, no r-prefix concerns:
    the compiler embeds it via Python's own repr(), which is guaranteed to
    round-trip any backslash content correctly with zero manual escaping.
    `label`, if given, is short Thai text shown above the equation (e.g.
    'จาก (2):') — always laid out as its own line, never side-by-side, so
    this can never trigger the old .arrange(RIGHT)-with-long-Thai overflow
    bug; the compiler enforces that layout choice, Gemini doesn't pick it.
    """
    label: Optional[str] = None
    latex: str


class EquationStep(BaseModel):
    title: str  # short Thai step heading, e.g. "1. พิจารณาแนวแกน Y (สมดุล):"
    lines: list[EquationLine] = Field(min_length=1)
    duration_seconds: float = 2.5  # compiler clamps to a sane [1.5, 6.0] range


class EpisodeData(BaseModel):
    episode_number: int
    title: str            # top-zone heading, e.g. "โจทย์ข้อ 15: หาอัตราส่วน T1 : T2"
    problem_desc: str      # top-zone problem statement line
    core_vocabulary: list[str] = Field(default_factory=list)
    video_plan: VideoPlan
    script: ScriptBlock
    voiceover_script: list[VoiceoverSegment] = Field(default_factory=list)

    # The only field Gemini still writes as freeform Manim source. Assumed
    # already indented to match construct()'s body (8 spaces), same
    # convention as the old manim_code_lines list. Still validated via
    # code_validator.preprocess_code() as its own isolated fragment.
    diagram_code_lines: list[str] = Field(default_factory=list)

    steps: list[EquationStep] = Field(default_factory=list)


class LessonResponse(BaseModel):
    is_physics: bool
    message: str
    source_problem_summary: Optional[str] = None
    content_type: Literal["concept", "problem", "mixed"]
    total_episodes: int
    episodes: list[EpisodeData]