"""
server/app/services/manim_engine.py
"""

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

load_dotenv()
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# ── Keep this at 1 on free tier (20 RPD). Raise to 2-3 after adding billing.
MAX_RETRIES = 1


FIX_PROMPT_TEMPLATE = """
คุณเป็น Manim developer ระดับ senior ที่แก้บั๊กได้เก่งมาก

โค้ด Manim ด้านล่างนี้รันแล้วเกิด Error ต่อไปนี้:

=== ERROR ===
{error_message}
=============

{violation_block}

=== โค้ดเดิมที่มีบั๊ก ===
{original_code}
========================

กรุณาแก้ไขโค้ดให้ถูกต้องและรันผ่านโดยไม่มี Error ใดๆ โดยปฏิบัติตามกฎเหล็กต่อไปนี้:

1. ห้ามใส่ภาษาไทยใน MathTex() หรือ Tex() หรือ \\mathrm{{}} เด็ดขาด
2. ห้ามใส่ LaTeX syntax เช่น \\( \\lambda \\) ใน Text() เด็ดขาด
3. ห้ามใช้ \\text{{}} ใน MathTex() — ใช้ \\mathrm{{}} เท่านั้น (แต่ห้ามใส่ Thai ใน \\mathrm)
4. bottom_center ต้องใช้ bottom_zone_center_y ไม่ใช่ bottom_zone_bottom
5. ทุก .move_to() ต้องใช้ numpy array [x, y, z] ไม่ใช่ scalar
6. BraceBetweenPoints ต้องใช้จุดที่อยู่ในแนวนอนเดียวกัน ห้ามวาดทแยงมุม
7. ห้ามมี include_numbers ใน axis_config (ใส่แค่ใน x_axis_config / y_axis_config)
8. font_size: สมการ/หัวข้อ = 26-28, label แกน = 16-18, tick = 14-16
9. axes x_length ≤ frame_width * 0.65, y_length ≤ middle_zone_height * 0.65
10. ทุก VGroup ต้องผ่าน scale_to_fit_width(frame_width * 0.88) และ
    scale_to_fit_height(zone_height * 0.88) ก่อน move_to() เสมอ
11. ห้ามใช้ axes.get_graph() — ใช้ axes.plot() หรือ ParametricFunction
12. ห้ามใช้ ShowCreation() — ใช้ Create()
13. import numpy as np ต้องอยู่บรรทัดแรก
14. ห้ามใช้ VGroup(*[Text(...) for line in [...]]) — เขียน Text() แยกบรรทัดใน VGroup()
15. ถ้า Error คือ "Render timed out" ให้ลด ParametricFunction sampling หรือลด MathTex จำนวน
    ห้ามลบ self.play()/self.wait() จนวิดีโอสั้นกว่า 30 วินาที

ส่งคืนเฉพาะ JSON ที่มีฟิลด์ "manim_code_lines" เป็น array ของ string เท่านั้น
ห้ามมีข้อความอื่นนอกจาก JSON เด็ดขาด:
{{"manim_code_lines": ["import numpy as np", "from manim import *", ...]}}
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
            bad_line = code_string.splitlines()[exc.lineno - 1] if exc.lineno else ""
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
            error_message=error_message[:4000],
            original_code=original_code[:8000],
            violation_block=violation_block,
        )

        # Exponential backoff for rate-limit errors (2s → 4s → 8s)
        for backoff in range(3):
            try:
                response = self.gemini_client.models.generate_content(
                    model="gemini-2.5-flash",
                    contents=prompt,
                    config=types.GenerateContentConfig(temperature=0.2),
                )
                raw = response.text.strip()
                raw = re.sub(r"^```(?:json)?\s*", "", raw)
                raw = re.sub(r"\s*```$", "", raw)
                parsed = json.loads(raw)
                lines = parsed.get("manim_code_lines")
                if isinstance(lines, list) and lines:
                    return lines
                logger.warning("Gemini fix response had no manim_code_lines.")
                return None

            except Exception as exc:
                err_str = str(exc)

                # ── Rate limit (429) — wait and retry ──────────────────────
                if any(x in err_str for x in ["429", "RESOURCE_EXHAUSTED", "quota"]):
                    wait = 2 ** (backoff + 1)   # 2, 4, 8 seconds
                    logger.warning(
                        f"Gemini rate limit hit. Waiting {wait}s "
                        f"(backoff {backoff + 1}/3)..."
                    )
                    time.sleep(wait)
                    continue

                # ── Daily quota / permission denied (403) — stop immediately ─
                if any(x in err_str for x in ["403", "PERMISSION_DENIED", "denied"]):
                    logger.error(
                        "Gemini API access denied (403 / PERMISSION_DENIED).\n"
                        "Your daily free-tier quota is likely exhausted (20 RPD).\n"
                        "Fix options:\n"
                        "  1. Wait until quota resets (midnight Pacific time)\n"
                        "  2. Create a new API key in a DIFFERENT Google Cloud project\n"
                        "     at aistudio.google.com (not just a new key in the same project)\n"
                        "  3. Add billing to your current project at aistudio.google.com/billing\n"
                        f"Original error: {exc}"
                    )
                    return None  # Don't retry — quota is gone for today

                # ── Any other error ─────────────────────────────────────────
                logger.error(f"Gemini fix request failed: {exc}")
                return None

        logger.error("Gemini: exhausted all backoff retries on rate limit.")
        return None

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

            for fix in val.auto_fixes:
                logger.info(f"  PRE-FIX: {fix}")

            if val.has_violations:
                logger.warning(
                    f"Ep {ep_num} attempt {attempt}: "
                    f"{len(val.violations)} rule violations — sending to Gemini."
                )
                if attempt > MAX_RETRIES:
                    return {
                        "status": "error",
                        "message": f"Violations not resolved:\n{val.violation_summary()}",
                        "attempts": attempt,
                    }
                fixed_lines = self._ask_gemini_to_fix(
                    original_code=val.fixed_code,
                    error_message="Pre-render validation failed — see violations.",
                    violation_summary=val.violation_summary(),
                )
                if fixed_lines is None:
                    return {
                        "status": "error",
                        "message": "Gemini unavailable (quota/403). "
                                   "Check aistudio.google.com/rate-limit.",
                        "attempts": attempt,
                    }
                current_data = dict(episode_data)
                current_data["manim_code_lines"] = fixed_lines
                continue  # re-validate fixed code

            # Use auto-fixed code (no violations)
            current_data["manim_code_lines"] = val.fixed_code.splitlines()

            # ── Step 1: Security check ───────────────────────────────────────
            filepath, code_string = self._write_scene_file(current_data, filename)
            is_safe, safety_msg = self._validate_code(code_string)
            if not is_safe:
                if os.path.exists(filepath):
                    os.remove(filepath)
                if attempt > MAX_RETRIES:
                    return {
                        "status": "error",
                        "message": f"Security validation failed: {safety_msg}",
                        "attempts": attempt,
                    }
                fixed_lines = self._ask_gemini_to_fix(
                    original_code=code_string,
                    error_message=f"Security validation failed: {safety_msg}",
                )
                if fixed_lines is None:
                    return {
                        "status": "error",
                        "message": "Gemini unavailable. " + safety_msg,
                        "attempts": attempt,
                    }
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

            logger.warning(f"Episode {ep_num} attempt {attempt} failed: {render_output[:300]}")
            if attempt > MAX_RETRIES:
                break

            fixed_lines = self._ask_gemini_to_fix(
                original_code=code_string,
                error_message=render_output,
            )
            if fixed_lines is None:
                return {
                    "status": "error",
                    "message": "Gemini unavailable (quota/403). Render also failed: "
                               + render_output[:200],
                    "attempts": attempt,
                }
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