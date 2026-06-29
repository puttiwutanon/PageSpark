import subprocess
import os
import re
import ast
import json
import logging
import time

from google import genai
from google.genai import types
from dotenv import load_dotenv
from app.services.code_validator import preprocess_code
from pydantic import BaseModel

load_dotenv()
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

MAX_RETRIES = 2


def smart_json_sanitize(raw: str) -> str:
    """
    Robust JSON sanitizer for Gemini responses that contain Manim/Python code.

    Problem: Gemini embeds Python code in JSON strings. LaTeX backslash sequences
    like \\frac, \\lambda create invalid JSON escapes:
      - \\f: JSON treats this as form feed (valid!) then "rac{..." is orphaned
      - \\l: JSON treats this as invalid escape → JSONDecodeError
      - \\t: JSON treats this as tab (valid!) then "heta" is orphaned

    Strategy:
      1. Protect already-doubled backslashes (\\\\ → placeholder)
      2. Protect valid \\uXXXX unicode escapes (\\u0e02 etc.)
      3. Double all remaining single backslashes
      4. Restore protected sequences

    This handles BOTH cases:
      - Gemini outputs single \\ (wrong): \frac → \\frac ✓
      - Gemini outputs double \\\\ (correct): \\frac → \\frac (unchanged) ✓
    """
    DB_PLACEHOLDER = '\x00__DB__\x00'   # for already-doubled backslashes
    UNI_PLACEHOLDER = '\x00__UNI__\x00'  # for \\uXXXX sequences

    # Step 1: protect already-doubled backslashes (\\\\ in raw string = \\ in JSON)
    raw = raw.replace('\\\\', DB_PLACEHOLDER)

    # Step 2: protect valid \\uXXXX unicode escapes (which are now \\u after step 1)
    # After step 1, any \\uXXXX that was originally \uXXXX is now just \uXXXX
    # We need to protect those
    raw = re.sub(
        r'\\u[0-9a-fA-F]{4}',
        lambda m: UNI_PLACEHOLDER + m.group(0)[2:],  # store the 4 hex chars
        raw
    )

    # Step 3: double all remaining single backslashes
    raw = raw.replace('\\', '\\\\')

    # Step 4: restore
    raw = raw.replace(DB_PLACEHOLDER, '\\\\')
    raw = raw.replace(UNI_PLACEHOLDER, '\\u')

    return raw


FIX_PROMPT_TEMPLATE = """
คุณเป็น Manim developer ระดับ senior ที่แก้บั๊กได้เก่งมาก

โค้ด Manim ด้านล่างนี้รันแล้วเกิด Error:

=== ERROR ===
{error_message}
=============

{violation_block}

=== โค้ดเดิมที่มีบั๊ก ===
{original_code}
========================

══ กฎเหล็ก — ดูตัวอย่างก่อน/หลังแล้วแก้ตามนี้เสมอ ══

❌ WRONG — VGroup(*[...]) list comprehension:
    lines = ['A', 'B', 'C']
    VGroup(*[Text(line, font='TH Sarabun New', font_size=26) for line in lines])
✅ CORRECT:
    VGroup(
        Text('A', font='TH Sarabun New', font_size=26, color=GRAY_A),
        Text('B', font='TH Sarabun New', font_size=26, color=GRAY_A),
        Text('C', font='TH Sarabun New', font_size=26, color=GRAY_A),
    ).arrange(DOWN, aligned_edge=LEFT, buff=0.1)

❌ WRONG — LaTeX ใน Text():
    Text('หาความยาวคลื่น (\\lambda)', ...)
✅ CORRECT — ใช้ unicode:
    Text('หาความยาวคลื่น (λ)', font='TH Sarabun New', font_size=26, color=GOLD_B)

❌ WRONG — Thai ใน MathTex() หรือ \\text{{Thai}}:
    MathTex(r'\\text{{ระยะห่างบัพ}} = \\frac{{\\lambda}}{{2}}', ...)
    MathTex(r'\\mathrm{{วินาที}}', ...)
✅ CORRECT — แยก Thai ออกเป็น VGroup(Text, MathTex):
    VGroup(
        Text('ระยะห่างบัพ', font='TH Sarabun New', font_size=26, color=WHITE),
        MathTex(r'= \\frac{{\\lambda}}{{2}}', font_size=26, color=WHITE),
    ).arrange(RIGHT, buff=0.1)

❌ WRONG — .move_to(scalar):
    group.move_to(bottom_zone_center_y)
✅ CORRECT:
    group.move_to(bottom_center)   # or np.array([0, bottom_zone_center_y, 0])

❌ WRONG — .arrange(RIGHT) กับ Text ไทยยาว:
    VGroup(Text('ก. เวลาที่วัตถุตกถึงพื้น:', ...), MathTex(...)).arrange(RIGHT)
✅ CORRECT:
    VGroup(Text('ก. เวลาที่วัตถุตกถึงพื้น:', ...), MathTex(...)).arrange(DOWN, aligned_edge=LEFT)

กฎอื่น:
- import numpy as np บรรทัดแรก
- ShowCreation → Create, TexMobject → MathTex, get_graph → plot
- ห้าม font= ใน MathTex()/Tex()
- ห้าม include_numbers ใน axis_config
- ทุก VGroup: scale_to_fit_width(frame_width*0.88) แล้ว move_to(zone_center)
- MathTex ใช้ r-string: MathTex(r'\\frac{{1}}{{2}}', ...)

ส่งคืนเฉพาะ JSON เท่านั้น ห้ามมีข้อความอื่น:
{{"manim_code_lines": ["import numpy as np", "from manim import *", ...]}}
"""


COUNT_PROMPT = """
    อ่านเนื้อหาที่ผู้ใช้ส่งมาและนับจำนวนโจทย์ฟิสิกส์ที่แยกจากกันได้ทั้งหมด
    (แต่ละโจทย์ที่มีสถานการณ์หรือตัวเลขต่างกัน นับเป็น 1 โจทย์)
    ส่งคืน JSON เท่านั้น: {"question_count": <number>, "question_titles": ["...", "..."]}
    """


class Manim_Engine:
    def __init__(self, output_dir: str = "renders"):
        self.output_dir = output_dir
        os.makedirs(output_dir, exist_ok=True)
        self.gemini_client = genai.Client()

    def _validate_code(self, code_string: str) -> tuple[bool, str]:
        forbidden = {
            "eval", "exec", "compile", "__import__",
            "os", "sys", "shutil", "subprocess", "open",
            "socket", "requests", "urllib", "pathlib",
        }
        try:
            tree = ast.parse(code_string)
        except SyntaxError as exc:
            bad_line = ""
            if exc.lineno:
                code_lines = code_string.splitlines()
                if exc.lineno - 1 < len(code_lines):
                    bad_line = code_lines[exc.lineno - 1]
            return False, f"SyntaxError: {exc} | offending line: {bad_line.strip()}"
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                for alias in node.names:
                    if alias.name.split(".")[0] in forbidden:
                        return False, f"Forbidden import: {alias.name}"
            if isinstance(node, ast.ImportFrom):
                if (node.module or "").split(".")[0] in forbidden:
                    return False, f"Forbidden import-from: {node.module}"
            if isinstance(node, ast.Name) and node.id in forbidden:
                return False, f"Forbidden name: {node.id}"
            if isinstance(node, ast.Call):
                if isinstance(node.func, ast.Name) and node.func.id == "__import__":
                    return False, "Forbidden: __import__"
        return True, "ok"

    def _write_scene_file(self, episode_data: dict, filename: str) -> tuple[str, str]:
        filepath = os.path.join(self.output_dir, filename)
        code = "\n".join(episode_data["manim_code_lines"])
        with open(filepath, "w", encoding="utf-8") as fh:
            fh.write(code)
        return filepath, code

    def _run_manim(self, filepath: str) -> tuple[bool, str]:
        cmd = ["manim", "-ql", filepath, "PhysicsScene", "--media_dir", self.output_dir]
        try:
            result = subprocess.run(cmd, capture_output=True, text=True, check=True, timeout=300)
            output = result.stdout
            if "Played 0 animations" in output:
                return False, "Render produced 0 animations — empty construct() body.\n" + output
            return True, output
        except subprocess.CalledProcessError as exc:
            return False, exc.stderr or exc.stdout
        except subprocess.TimeoutExpired:
            return False, "Render timed out after 300 seconds."

    def _ask_gemini_to_fix(
        self,
        original_code: str,
        error_message: str,
        violation_summary: str | None = None,
    ) -> list[str] | None:
        violation_block = ""
        if violation_summary:
            violation_block = (
                f"=== RULE VIOLATIONS (แก้ทุกข้อนี้ก่อน) ===\n"
                f"{violation_summary}\n"
                f"======================="
            )
        prompt = FIX_PROMPT_TEMPLATE.format(
            error_message=error_message[:3000],
            original_code=original_code[:8000],
            violation_block=violation_block,
        )

        for backoff in range(3):
            try:
                response = self.gemini_client.models.generate_content(
                    model="gemini-2.5-flash",
                    contents=prompt,
                    config=types.GenerateContentConfig(
                        temperature=0.1,
                        response_mime_type="application/json",
                    ),
                )
                raw = response.text.strip()
                # Strip markdown fences if present
                raw = re.sub(r"^```(?:json|python)?\s*", "", raw)
                raw = re.sub(r"\s*```$", "", raw)

                # Apply smart sanitizer BEFORE json.loads
                raw = smart_json_sanitize(raw)

                try:
                    parsed = json.loads(raw)
                except json.JSONDecodeError as e:
                    logger.error(f"Gemini fix JSON parse failed after sanitize: {e}")
                    logger.error(f"Sanitized raw (first 300): {raw[:300]}")
                    return None

                lines = parsed.get("manim_code_lines")
                if isinstance(lines, list) and lines:
                    return lines
                logger.warning("Gemini fix response had no manim_code_lines field.")
                return None

            except Exception as exc:
                err_str = str(exc)
                if any(x in err_str for x in [
                    "429", "503", "RESOURCE_EXHAUSTED", "UNAVAILABLE", "quota", "overloaded",
                ]):
                    wait = 2 ** (backoff + 1)
                    logger.warning(
                        f"Gemini transient error ({err_str[:60]}). "
                        f"Waiting {wait}s (backoff {backoff + 1}/3)..."
                    )
                    time.sleep(wait)
                    continue
                if any(x in err_str for x in ["403", "PERMISSION_DENIED", "denied"]):
                    logger.error(
                        "Gemini API quota exhausted (403). "
                        "Wait until midnight Pacific or add billing.\n"
                        f"Error: {exc}"
                    )
                    return None
                logger.error(f"Gemini fix failed (non-retryable): {exc}")
                return None

        logger.error("Gemini: exhausted all backoff retries.")
        return None

    def enforce_episode_count(
        self,
        lesson_json: dict,
        expected_count: int,
        question_titles: list[str] | None = None,
    ) -> dict:
        episodes = lesson_json.get("episodes", [])
        actual = len(episodes)
        if actual >= expected_count:
            return lesson_json
        logger.warning(
            f"enforce_episode_count: expected {expected_count}, got {actual}. "
            f"Stubbing {expected_count - actual} episode(s)."
        )
        for i in range(actual + 1, expected_count + 1):
            title = (question_titles[i - 1]
                     if question_titles and len(question_titles) >= i
                     else f"โจทย์ข้อ {i}")
            episodes.append({
                "episode_number": i,
                "title": title,
                "core_vocabulary": [],
                "video_plan": {"estimated_duration_seconds": 60},
                "script": {"hook": "", "main_body": "", "example_or_trick": "", "call_to_action": ""},
                "voiceover_script": [],
                "manim_code_lines": [
                    "import numpy as np",
                    "from manim import *",
                    "config.pixel_width = 1080",
                    "config.pixel_height = 1920",
                    "config.frame_height = 16.0",
                    "config.frame_width = 9.0",
                    "config.frame_rate = 60",
                    "class PhysicsScene(Scene):",
                    "    def construct(self):",
                    "        self.camera.background_color = '#1C1C2E'",
                    f"        title = Text('{title}', font='TH Sarabun New', font_size=28, color=WHITE)",
                    "        title.move_to(ORIGIN)",
                    "        self.play(FadeIn(title))",
                    "        self.wait(3)",
                ]
            })
        lesson_json["episodes"] = episodes
        lesson_json["total_episodes"] = expected_count
        return lesson_json

    def render_episode(self, episode_data: dict) -> dict:
        ep_num = episode_data.get("episode_number", 0)
        filename = f"scene_ep_{ep_num}.py"
        current_data = dict(episode_data)
        render_output = "No render attempted yet."

        for attempt in range(1, MAX_RETRIES + 2):
            logger.info(f"Episode {ep_num} — render attempt {attempt}/{MAX_RETRIES + 1}")

            # ── Step 0: Deterministic pre-processor ─────────────────────────
            raw_code = "\n".join(current_data["manim_code_lines"])
            val = preprocess_code(raw_code)

            if val.auto_fixes:
                logger.info(f"  Auto-fixes ({len(val.auto_fixes)}):")
                for fix in val.auto_fixes:
                    logger.info(f"    • {fix}")

            if val.has_violations:
                logger.warning(
                    f"Ep {ep_num} attempt {attempt}: "
                    f"{len(val.violations)} violations after auto-fix:"
                )
                for v in val.violations:
                    logger.warning(f"    [{v.rule}] line {v.line}: {v.snippet[:60]}")

                if attempt > MAX_RETRIES:
                    return {
                        "status": "error",
                        "message": (
                            f"Violations not resolved after {MAX_RETRIES} retries:\n"
                            + val.violation_summary()
                        ),
                        "attempts": attempt,
                    }

                fixed_lines = self._ask_gemini_to_fix(
                    original_code=val.fixed_code,
                    error_message="Pre-render validation failed — see violations.",
                    violation_summary=val.violation_summary(),
                )
                if fixed_lines is None:
                    # Gemini unavailable — try rendering with auto-fixed code anyway
                    # (better than failing immediately on a rate limit)
                    logger.warning(
                        f"Ep {ep_num}: Gemini unavailable (rate limit?). "
                        "Attempting render with auto-fixed code."
                    )
                    current_data["manim_code_lines"] = val.fixed_code.splitlines()
                    # Fall through to render
                else:
                    current_data["manim_code_lines"] = fixed_lines
                    continue  # re-validate

            else:
                current_data["manim_code_lines"] = val.fixed_code.splitlines()

            # ── Step 1: Security check ───────────────────────────────────────
            filepath, code_string = self._write_scene_file(current_data, filename)
            is_safe, safety_msg = self._validate_code(code_string)
            if not is_safe:
                if os.path.exists(filepath):
                    os.remove(filepath)
                if attempt > MAX_RETRIES:
                    return {"status": "error",
                            "message": f"Security validation failed: {safety_msg}",
                            "attempts": attempt}
                fixed_lines = self._ask_gemini_to_fix(
                    original_code=code_string,
                    error_message=f"Security validation failed: {safety_msg}",
                )
                if fixed_lines is None:
                    return {"status": "error",
                            "message": f"Security fail + Gemini unavailable: {safety_msg}",
                            "attempts": attempt}
                current_data["manim_code_lines"] = fixed_lines
                continue

            # ── Step 2: Render ───────────────────────────────────────────────
            success, render_output = self._run_manim(filepath)
            if success:
                logger.info(f"Episode {ep_num} rendered OK on attempt {attempt}.")
                return {
                    "status": "success",
                    "filepath": filepath,
                    "output": render_output,
                    "attempts": attempt,
                }

            logger.warning(
                f"Episode {ep_num} attempt {attempt} render failed:\n"
                + render_output[:400]
            )
            if attempt > MAX_RETRIES:
                break

            fixed_lines = self._ask_gemini_to_fix(
                original_code=code_string,
                error_message=render_output,
            )
            if fixed_lines is None:
                logger.warning(f"Ep {ep_num}: Gemini unavailable on render error. Stopping.")
                break
            current_data["manim_code_lines"] = fixed_lines

        return {
            "status": "error",
            "message": render_output,
            "attempts": min(attempt, MAX_RETRIES + 1),
        }

    def render_all_episodes(self, lesson_json: dict) -> list[dict]:
        results = []
        for episode in lesson_json.get("episodes", []):
            result = self.render_episode(episode)
            result["episode_number"] = episode.get("episode_number")
            results.append(result)
        return results

    def count_questions_first(self, page_content: str) -> int:
        try:
            response = self.gemini_client.models.generate_content(
                model="gemini-2.5-flash",
                contents=COUNT_PROMPT + "\n\nเนื้อหา:\n" + page_content,
                config=types.GenerateContentConfig(temperature=0.1),
            )
            raw = response.text.strip()
            raw = re.sub(r"^```(?:json)?\s*", "", raw)
            raw = re.sub(r"\s*```$", "", raw)
            data = json.loads(raw)
            count = data.get("question_count", 1)
            logger.info(f"Pre-scan: {count} question(s): {data.get('question_titles', [])}")
            return count
        except Exception as e:
            logger.warning(f"Question count pre-scan failed: {e} — defaulting to 1")
            return 1