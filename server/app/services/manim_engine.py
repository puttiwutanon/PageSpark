"""
server/app/services/manim_engine.py

Manim rendering engine with automatic Gemini-powered retry loop.
When a render fails, the engine sends the error back to Gemini with the
original code so it can fix and regenerate — up to MAX_RETRIES attempts.
"""

import subprocess
import os
import re
import ast
import json
import logging
import tempfile

from google import genai
from google.genai import types
from dotenv import load_dotenv

load_dotenv()
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

MAX_RETRIES = 3  # maximum fix attempts after the first render failure


# ──────────────────────────────────────────────────────────────────────────────
# Prompt sent to Gemini when a render fails
# ──────────────────────────────────────────────────────────────────────────────
FIX_PROMPT_TEMPLATE = """
คุณเป็น Manim developer ระดับ senior ที่แก้บั๊กได้เก่งมาก

โค้ด Manim ด้านล่างนี้รันแล้วเกิด Error ต่อไปนี้:

=== ERROR ===
{error_message}
=============

=== โค้ดเดิมที่มีบั๊ก ===
{original_code}
========================

กรุณาแก้ไขโค้ดให้ถูกต้องและรันผ่านโดยไม่มี Error ใดๆ โดยปฏิบัติตามกฎเหล็กต่อไปนี้:

กฎเหล็กที่ต้องตรวจสอบทุกครั้ง:
1. ห้ามใส่ภาษาไทยใน MathTex() หรือ Tex() หรือ \\mathrm{{}} เด็ดขาด
2. ห้ามใส่ LaTeX syntax เช่น \\( \\lambda \\) ใน Text() เด็ดขาด
3. ห้ามใช้ \\text{{}} ใน MathTex() — ใช้ \\mathrm{{}} เท่านั้น (แต่ห้ามใส่ Thai ใน \\mathrm)
4. bottom_center ต้องใช้ bottom_zone_center_y ไม่ใช่ bottom_zone_bottom
5. ทุก .move_to() ต้องใช้ numpy array [x, y, z] ไม่ใช่ scalar
6. BraceBetweenPoints ต้องใช้จุดที่อยู่ในแนวนอนเดียวกัน ห้ามวาดทแยงมุม
7. ห้ามใช้ \\text{{}} ใน MathTex ทุกกรณี
8. ห้ามมี include_numbers ใน axis_config (ใส่แค่ใน x_axis_config / y_axis_config)
9. font_size: สมการ/หัวข้อ = 26-28, label แกน = 16-18, tick = 14-16
10. axes x_length ≤ frame_width * 0.65, y_length ≤ middle_zone_height * 0.65
11. ทุก VGroup ต้องผ่าน scale_to_fit_width(frame_width * 0.88) และ
    scale_to_fit_height(zone_height * 0.88) ก่อน move_to() เสมอ
12. ห้ามใช้ axes.get_graph() — ใช้ axes.plot() หรือ ParametricFunction
13. ห้ามใช้ ShowCreation() — ใช้ Create()
14. import numpy as np ต้องอยู่บรรทัดแรก

ส่งคืนเฉพาะ JSON ที่มีฟิลด์ "manim_code_lines" เป็น array ของ string เท่านั้น
ห้ามมีข้อความอื่นนอกจาก JSON เด็ดขาด ตัวอย่างรูปแบบ:
{{"manim_code_lines": ["import numpy as np", "from manim import *", ...]}}
"""


class Manim_Engine:
    def __init__(self, output_dir: str = "renders"):
        self.output_dir = output_dir
        os.makedirs(output_dir, exist_ok=True)
        self.gemini_client = genai.Client()

    # ─────────────────────────────────────────────────────────────────────────
    # Security validation
    # ─────────────────────────────────────────────────────────────────────────
    def _validate_code(self, code_string: str) -> tuple[bool, str]:
        """Block dangerous imports/calls before shelling out to manim."""
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
                    root = alias.name.split(".")[0]
                    if root in forbidden:
                        return False, f"Forbidden import: {alias.name}"

            if isinstance(node, ast.ImportFrom):
                root = (node.module or "").split(".")[0]
                if root in forbidden:
                    return False, f"Forbidden import-from: {node.module}"

            if isinstance(node, ast.Name) and node.id in forbidden:
                return False, f"Forbidden name: {node.id}"

            if isinstance(node, ast.Call):
                func = node.func
                if isinstance(func, ast.Name) and func.id == "__import__":
                    return False, "Forbidden: __import__"

        return True, "ok"

    # ─────────────────────────────────────────────────────────────────────────
    # File helpers
    # ─────────────────────────────────────────────────────────────────────────
    def _write_scene_file(self, episode_data: dict, filename: str) -> tuple[str, str]:
        filepath = os.path.join(self.output_dir, filename)
        code = "\n".join(episode_data["manim_code_lines"])
        with open(filepath, "w", encoding="utf-8") as fh:
            fh.write(code)
        return filepath, code

    def _write_code_string(self, code_string: str, filename: str) -> str:
        filepath = os.path.join(self.output_dir, filename)
        with open(filepath, "w", encoding="utf-8") as fh:
            fh.write(code_string)
        return filepath

    # ─────────────────────────────────────────────────────────────────────────
    # Manim CLI runner
    # ─────────────────────────────────────────────────────────────────────────
    def _run_manim(self, filepath: str) -> tuple[bool, str]:
        cmd = ["manim", "-ql", filepath, "PhysicsScene", "--media_dir", self.output_dir]
        try:
            result = subprocess.run(cmd, capture_output=True, text=True, check=True, timeout=300)
            output = result.stdout
            if "Played 0 animations" in output:
                return False, "Render produced 0 animations — likely a stripped/empty construct() body, no video was generated.\n" + output
            return True, output
        except subprocess.CalledProcessError as exc:
            return False, exc.stderr or exc.stdout
        except subprocess.TimeoutExpired:
            return False, "Render timed out after 300 seconds."

    # ─────────────────────────────────────────────────────────────────────────
    # Gemini fix loop
    # ─────────────────────────────────────────────────────────────────────────
    def _ask_gemini_to_fix(self, original_code: str, error_message: str) -> list[str] | None:
        """
        Sends the broken code + error to Gemini and asks for a fixed version.
        Returns a new manim_code_lines list, or None on failure.
        """
        prompt = FIX_PROMPT_TEMPLATE.format(
            error_message=error_message[:4000],   # cap to avoid token blowout
            original_code=original_code[:8000],
        )
        try:
            response = self.gemini_client.models.generate_content(
                model="gemini-2.5-flash",
                contents=prompt,
                config=types.GenerateContentConfig(
                    temperature=0.2,   # low temp → precise fixes
                ),
            )
            raw = response.text.strip()

            # Strip markdown fences if present
            raw = re.sub(r"^```(?:json)?\s*", "", raw)
            raw = re.sub(r"\s*```$", "", raw)

            parsed = json.loads(raw)
            lines = parsed.get("manim_code_lines")
            if isinstance(lines, list) and lines:
                return lines
            logger.warning("Gemini fix response had no manim_code_lines.")
            return None
        except Exception as exc:
            logger.error(f"Gemini fix request failed: {exc}")
            return None

    # ─────────────────────────────────────────────────────────────────────────
    # Public API
    # ─────────────────────────────────────────────────────────────────────────
    def render_episode(self, episode_data: dict) -> dict:
        """
        Render one episode with automatic Gemini-powered retry on failure.

        Flow:
          1. Validate + write code → attempt render
          2. On failure → ask Gemini to fix → re-validate → attempt render
          3. Repeat up to MAX_RETRIES times
          4. Return success dict (with output path) or error dict

        Returns:
            {
                "status": "success" | "error",
                "filepath": str,          # only on success
                "output": str,            # manim stdout on success
                "message": str,           # error description on failure
                "attempts": int,          # total render attempts made
            }
        """
        ep_num = episode_data.get("episode_number", 0)
        filename = f"scene_ep_{ep_num}.py"
        current_data = dict(episode_data)   # mutable copy

        for attempt in range(1, MAX_RETRIES + 2):   # attempt 1 = first try; 2..N+1 = retries
            logger.info(f"Episode {ep_num} — render attempt {attempt}/{MAX_RETRIES + 1}")

            # ── Security check ──────────────────────────────────────────────
            filepath, code_string = self._write_scene_file(current_data, filename)
            is_safe, safety_msg = self._validate_code(code_string)
            if not is_safe:
                logger.warning(f"Ep {ep_num} attempt {attempt}: Security validation failed: {safety_msg}")
                if os.path.exists(filepath):
                    os.remove(filepath)

                if attempt > MAX_RETRIES:
                    return {
                        "status": "error",
                        "message": f"Security validation failed: {safety_msg}",
                        "attempts": attempt,
                    }

                logger.info(f"Episode {ep_num}: Asking Gemini to fix validation error (retry {attempt}/{MAX_RETRIES})…")
                fixed_lines = self._ask_gemini_to_fix(code_string, f"Security validation failed: {safety_msg}")

                if fixed_lines is None:
                    logger.error(f"Episode {ep_num}: Gemini could not produce a fix for validation error. Stopping.")
                    return {
                        "status": "error",
                        "message": f"Security validation failed: {safety_msg}",
                        "attempts": attempt,
                    }

                current_data = dict(episode_data)
                current_data["manim_code_lines"] = fixed_lines
                logger.info(f"Episode {ep_num}: Gemini fix received ({len(fixed_lines)} lines). Retrying…")
                continue  # skip render this loop, re-validate the fixed code next iteration

            # ── Render ──────────────────────────────────────────────────────
            success, render_output = self._run_manim(filepath)

            if success:
                logger.info(f"Episode {ep_num} rendered successfully on attempt {attempt}.")
                return {
                    "status": "success",
                    "filepath": filepath,
                    "output": render_output,
                    "attempts": attempt,
                }

            # ── Failed — log and maybe retry ────────────────────────────────
            logger.warning(f"Episode {ep_num} attempt {attempt} failed:\n{render_output[:500]}")

            if attempt > MAX_RETRIES:
                # Exhausted all retries
                break

            logger.info(f"Episode {ep_num}: Asking Gemini to fix error (retry {attempt}/{MAX_RETRIES})…")
            fixed_lines = self._ask_gemini_to_fix(code_string, render_output)

            if fixed_lines is None:
                logger.error(f"Episode {ep_num}: Gemini could not produce a fix. Stopping.")
                break

            # Replace code lines with Gemini's fixed version and loop again
            current_data = dict(episode_data)
            current_data["manim_code_lines"] = fixed_lines
            logger.info(f"Episode {ep_num}: Gemini fix received ({len(fixed_lines)} lines). Retrying…")

        return {
            "status": "error",
            "message": render_output,
            "attempts": min(attempt, MAX_RETRIES + 1),
        }

    def render_all_episodes(self, lesson_json: dict) -> list[dict]:
        """Render every episode in a lesson JSON response and return results list."""
        results = []
        for episode in lesson_json.get("episodes", []):
            result = self.render_episode(episode)
            result["episode_number"] = episode.get("episode_number")
            results.append(result)
        return results