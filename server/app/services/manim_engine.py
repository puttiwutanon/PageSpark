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
from app.storage.cloudinary_storage import upload_episode_video
from pydantic import BaseModel

load_dotenv()

# Enhanced logging configuration
logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

MAX_RETRIES = 2  # Keep at 2 to avoid API exhaustion


def _quality_check(self, code_lines: list[str]) -> tuple[bool, list[str]]:
    """
    Run a quick quality check on the generated code.
    Returns (is_acceptable, issues_list)
    This runs BEFORE any API calls to save quota.
    """
    issues = []
    
    # Check for common issues
    code_str = "\n".join(code_lines)
    
    # Check for correct scaling
    if 'scale_to_fit_width' not in code_str:
        issues.append("Missing scale_to_fit_width")
    
    # Check for correct font sizes
    import re
    font_sizes = re.findall(r'font_size\s*=\s*(\d+)', code_str)
    for size in font_sizes:
        if int(size) > 28:
            issues.append(f"font_size={size} exceeds 28")
    
    # Check for math errors
    if '\\\\equiv' in code_str:
        issues.append("Using \\equiv instead of =")
    
    if 'sqrt{200^2 + 200^2}' in code_str and '200\\\\sqrt{2}' not in code_str:
        issues.append("Incorrect sqrt(200²+200²) calculation")
    
    # Check for Thai in MathTex
    thai_pattern = re.compile(r'MathTex\([^)]*[\u0E00-\u0E7F]')
    if thai_pattern.search(code_str):
        issues.append("Thai characters found in MathTex()")
    
    # Check for LaTeX in Text
    latex_pattern = re.compile(r'Text\([^)]*\\\\(?:frac|sqrt|lambda|phi|theta)')
    if latex_pattern.search(code_str):
        issues.append("LaTeX commands found in Text()")
    
    # Check for VGroup without scaling in bottom zone
    if 'bottom_center' in code_str:
        vgroup_pattern = re.compile(r'(\w+)\s*=\s*VGroup\(')
        vgroups = vgroup_pattern.findall(code_str)
        for vg in vgroups:
            if f'{vg}.scale_to_fit_width' not in code_str and f'{vg}.scale_to_fit_height' not in code_str:
                if 'axes' not in vg.lower():  # Axes don't need scaling
                    issues.append(f"VGroup '{vg}' missing scaling")
    
    # Check if bottom zone has enough content (at least 2 steps)
    step_count = len(re.findall(r'step\d+_title', code_str))
    if step_count < 2:
        issues.append(f"Only {step_count} step(s) found - should have at least 2")
    
    return len(issues) == 0, issues


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


LINE_FIX_PROMPT_TEMPLATE = """
คุณเป็น Manim developer ที่แก้บั๊กแบบ surgical — แก้เฉพาะบรรทัดที่ระบุเท่านั้น

ด้านล่างคือ "violations" ที่พบ พร้อมหมายเลขบรรทัดและบริบทรอบๆ (3 บรรทัดก่อน/หลัง)
แต่ละ violation มี context_id กำกับไว้ — ใช้ context_id นั้นตอบกลับ

{violation_blocks}

══ กฎเหล็ก — ดูตัวอย่างก่อน/หลังแล้วแก้ตามนี้เสมอ ══

❌ WRONG — VGroup(*[...]) list comprehension:
    VGroup(*[Text(line, font='TH Sarabun New', font_size=26) for line in lines])
✅ CORRECT:
    VGroup(
        Text('A', font='TH Sarabun New', font_size=26, color=GRAY_A),
        Text('B', font='TH Sarabun New', font_size=26, color=GRAY_A),
    ).arrange(DOWN, aligned_edge=LEFT, buff=0.1)

❌ WRONG — LaTeX ใน Text(): Text('หาความยาวคลื่น (\\lambda)', ...)
✅ CORRECT — ใช้ unicode: Text('หาความยาวคลื่น (λ)', ...)

❌ WRONG — Thai ใน MathTex(): MathTex(r'\\mathrm{{วินาที}}', ...)
✅ CORRECT — แยก Thai ออกเป็น Text() แล้วรวมด้วย VGroup

❌ WRONG — .move_to(scalar): group.move_to(bottom_zone_center_y)
✅ CORRECT: group.move_to(np.array([0, bottom_zone_center_y, 0]))

❌ WRONG — .arrange(RIGHT) กับ Text ไทยยาว (15+ ตัวอักษร)
✅ CORRECT — .arrange(DOWN, aligned_edge=LEFT)

สำหรับแต่ละ context_id ด้านบน ส่งคืนเฉพาะบรรทัดที่แก้ไขแล้ว (อาจมีจำนวนบรรทัด
มากกว่าหรือน้อยกว่าเดิมได้ถ้าจำเป็น เช่นแยก 1 บรรทัดเป็นหลายบรรทัด) เป็น list ของ string

ส่งคืนเฉพาะ JSON เท่านั้น ห้ามมีข้อความอื่น ห้ามใส่หมายเลขบรรทัดในสตริง:
{{"fixes": {{"<context_id>": ["บรรทัดที่แก้ 1", "บรรทัดที่แก้ 2"]}}}}
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
        logger.info(f"🚀 Manim_Engine initialized with output_dir: {output_dir}")

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
        logger.debug(f"📝 Wrote scene file: {filepath} ({len(code)} chars)")
        return filepath, code

    def _resolve_rendered_mp4_path(self, scene_filepath: str) -> str:
        """
        manim renders to 1920p60 quality.
        """
        stem = os.path.splitext(os.path.basename(scene_filepath))[0]
        
        # Only 1920p60
        path = os.path.join(self.output_dir, "videos", stem, "1920p60", "PhysicsScene.mp4")
        
        # If not found, try to find any PhysicsScene.mp4
        if not os.path.exists(path):
            import glob
            pattern = os.path.join(self.output_dir, "videos", "**", "PhysicsScene.mp4")
            matches = glob.glob(pattern, recursive=True)
            if matches:
                matches.sort(key=os.path.getmtime, reverse=True)
                path = matches[0]
                logger.info(f"✅ Found video at: {path}")
            else:
                logger.warning(f"⚠️ No video found at expected path: {path}")
        
        return path

    def _run_manim(self, filepath: str) -> tuple[bool, str]:
        cmd = ["manim", "-ql", filepath, "PhysicsScene", "--media_dir", self.output_dir]
        logger.info(f"🎬 Running manim command: {' '.join(cmd)}")
        
        try:
            result = subprocess.run(cmd, capture_output=True, text=True, check=True, timeout=300)
            output = result.stdout
            
            # Log first few lines of output for debugging
            output_lines = output.splitlines()
            logger.info(f"📺 Manim output preview (first 10 lines):")
            for line in output_lines[:10]:
                logger.info(f"  {line}")
            
            if "Played 0 animations" in output:
                logger.warning("⚠️ Render produced 0 animations — empty construct() body.")
                return False, "Render produced 0 animations — empty construct() body.\n" + output
            
            logger.info("✅ Manim render completed successfully!")
            return True, output
            
        except subprocess.CalledProcessError as exc:
            error_output = exc.stderr or exc.stdout or ""
            logger.error(f"❌ Manim render failed with error code {exc.returncode}")
            logger.error(f"Error output: {error_output[:500]}")
            return False, error_output
        except subprocess.TimeoutExpired:
            logger.error("❌ Manim render timed out after 300 seconds.")
            return False, "Render timed out after 300 seconds."

    def _ask_gemini_to_fix(
        self,
        original_code: str,
        error_message: str,
        violation_summary: str | None = None,
    ) -> list[str] | None:
        logger.info("🔄 Asking Gemini for code fix...")
        
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
                    model="gemini-3.5-flash",
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
                    logger.info(f"✅ Gemini provided fix with {len(lines)} lines")
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

    def _ask_gemini_to_fix_lines(
        self,
        code: str,
        violations: list,
        context_radius: int = 3,
    ) -> str | None:
        """
        Targeted fix: send Gemini ONLY the violating lines (plus a few lines
        of context each) instead of the whole file, and splice the returned
        replacement lines back into `code` locally.

        Used for validator violations (which already carry an exact line
        number per code_validator.Violation) — NOT for raw render/stderr
        errors, where the root cause is often several lines away from where
        the traceback points and full-file context is genuinely needed.

        Returns the full patched code string, or None if Gemini fix failed
        (caller should fall back to the full-file _ask_gemini_to_fix or
        render with auto-fixed code as-is).
        """
        logger.info(f"🔧 Asking Gemini for targeted line fix ({len(violations)} violations)")
        
        lines = code.splitlines()

        # Build one context block per violation, each tagged with a stable
        # context_id so we know exactly which lines to replace after Gemini
        # responds — no fuzzy matching needed.
        blocks = []
        replace_ranges: dict[str, tuple[int, int]] = {}  # context_id -> (start_idx, end_idx) inclusive, 0-based

        for i, v in enumerate(violations):
            ctx_id = f"v{i}_{v.rule}"
            line_idx = v.line - 1  # Violation.line is 1-based
            start = max(0, line_idx - context_radius)
            end = min(len(lines) - 1, line_idx + context_radius)

            numbered = "\n".join(
                f"{n + 1}: {lines[n]}" for n in range(start, end + 1)
            )
            blocks.append(
                f"--- context_id: {ctx_id} ---\n"
                f"[{v.rule}] {v.description}\n"
                f"บรรทัดที่ต้องแก้คือบรรทัด {v.line} (อยู่ในช่วงด้านล่าง):\n"
                f"{numbered}\n"
            )
            replace_ranges[ctx_id] = (start, end)

        prompt = LINE_FIX_PROMPT_TEMPLATE.format(
            violation_blocks="\n".join(blocks)
        )

        for backoff in range(3):
            try:
                response = self.gemini_client.models.generate_content(
                    model="gemini-3.5-flash",
                    contents=prompt,
                    config=types.GenerateContentConfig(
                        temperature=0.1,
                        response_mime_type="application/json",
                    ),
                )
                raw = response.text.strip()
                raw = re.sub(r"^```(?:json|python)?\s*", "", raw)
                raw = re.sub(r"\s*```$", "", raw)
                raw = smart_json_sanitize(raw)

                try:
                    parsed = json.loads(raw)
                except json.JSONDecodeError as e:
                    logger.error(f"Gemini line-fix JSON parse failed: {e}")
                    logger.error(f"Sanitized raw (first 300): {raw[:300]}")
                    return None

                fixes = parsed.get("fixes")
                if not isinstance(fixes, dict) or not fixes:
                    logger.warning("Gemini line-fix response had no usable 'fixes' field.")
                    return None

                # Splice replacements back in, working from the BOTTOM up so
                # earlier replace_ranges indices stay valid as line counts shift.
                ordered = sorted(
                    replace_ranges.items(),
                    key=lambda kv: kv[1][0],
                    reverse=True,
                )
                patched_lines = list(lines)
                applied = 0
                for ctx_id, (start, end) in ordered:
                    replacement = fixes.get(ctx_id)
                    if not isinstance(replacement, list) or not replacement:
                        logger.warning(f"No fix returned for {ctx_id} — leaving original lines.")
                        continue
                    patched_lines[start:end + 1] = replacement
                    applied += 1

                if applied == 0:
                    logger.warning("Gemini line-fix returned no applicable fixes.")
                    return None

                logger.info(f"✅ Line-fix: applied {applied}/{len(violations)} targeted patches.")
                return "\n".join(patched_lines)

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
                    logger.error(f"Gemini API quota exhausted (403): {exc}")
                    return None
                logger.error(f"Gemini line-fix failed (non-retryable): {exc}")
                return None

        logger.error("Gemini line-fix: exhausted all backoff retries.")
        return None

    def enforce_episode_count(
        self,
        lesson_json: dict,
        expected_count: int,
        question_titles: list[str] | None = None,
    ) -> dict:
        episodes = lesson_json.get("episodes", [])
        actual = len(episodes)
        
        logger.info(f"📊 Episode count check: expected={expected_count}, actual={actual}")
        
        if actual >= expected_count:
            logger.info(f"✅ Episode count OK ({actual} >= {expected_count})")
            return lesson_json
            
        logger.warning(
            f"⚠️ Episode count mismatch: expected {expected_count}, got {actual}. "
            f"Stubbing {expected_count - actual} episode(s)."
        )
        
        for i in range(actual + 1, expected_count + 1):
            title = (question_titles[i - 1]
                     if question_titles and len(question_titles) >= i
                     else f"โจทย์ข้อ {i}")
            logger.info(f"📝 Creating stub episode {i}: '{title}'")
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
        logger.info(f"✅ Episode count enforced: now {len(episodes)} episodes")
        return lesson_json

    def render_episode(self, episode_data: dict, *, uid: str | None = None, lesson_id: str | None = None) -> dict:
        ep_num = episode_data.get("episode_number", 0)
        logger.info(f"🔄 ===== STARTING RENDER for episode {ep_num} =====")
        logger.info(f"   uid={uid}, lesson_id={lesson_id}")
        logger.info(f"   title={episode_data.get('title', 'Untitled')}")
        
        filename = f"scene_ep_{ep_num}.py"
        current_data = dict(episode_data)
        render_output = "No render attempted yet."

        for attempt in range(1, MAX_RETRIES + 2):
            logger.info(f"📹 Episode {ep_num} — render attempt {attempt}/{MAX_RETRIES + 1}")

            # ── Step 0: Deterministic pre-processor ─────────────────────────
            raw_code = "\n".join(current_data["manim_code_lines"])
            val = preprocess_code(raw_code)

            if val.auto_fixes:
                logger.info(f"  🔧 Auto-fixes ({len(val.auto_fixes)}):")
                for fix in val.auto_fixes:
                    logger.info(f"    • {fix}")

            if val.has_violations:
                logger.warning(
                    f"  ⚠️ Ep {ep_num} attempt {attempt}: "
                    f"{len(val.violations)} violations after auto-fix:"
                )
                for v in val.violations:
                    logger.warning(f"    [{v.rule}] line {v.line}: {v.snippet[:60]}")

                if attempt > MAX_RETRIES:
                    logger.error(f"❌ Episode {ep_num}: Violations not resolved after {MAX_RETRIES} retries")
                    return {
                        "status": "error",
                        "message": (
                            f"Violations not resolved after {MAX_RETRIES} retries:\n"
                            + val.violation_summary()
                        ),
                        "attempts": attempt,
                    }

                fixed_code = self._ask_gemini_to_fix_lines(
                    code=val.fixed_code,
                    violations=val.violations,
                )
                if fixed_code is not None:
                    current_data["manim_code_lines"] = fixed_code.splitlines()
                    continue  # re-validate

                # Targeted line-fix failed/unavailable — fall back to the
                # full-file fixer once before giving up on this attempt.
                logger.warning(
                    f"  ⚠️ Ep {ep_num}: targeted line-fix failed, "
                    "falling back to full-file fix."
                )
                fixed_lines = self._ask_gemini_to_fix(
                    original_code=val.fixed_code,
                    error_message="Pre-render validation failed — see violations.",
                    violation_summary=val.violation_summary(),
                )
                if fixed_lines is None:
                    # Gemini unavailable — try rendering with auto-fixed code anyway
                    # (better than failing immediately on a rate limit)
                    logger.warning(
                        f"  ⚠️ Ep {ep_num}: Gemini unavailable (rate limit?). "
                        "Attempting render with auto-fixed code."
                    )
                    current_data["manim_code_lines"] = val.fixed_code.splitlines()
                    # Fall through to render
                else:
                    current_data["manim_code_lines"] = fixed_lines
                    continue  # re-validate

            else:
                current_data["manim_code_lines"] = val.fixed_code.splitlines()

            # ── STEP 2.5: Quality Check (BEFORE rendering to save time) ────
            is_quality_ok, quality_issues = _quality_check(self, current_data["manim_code_lines"])
            
            if not is_quality_ok:
                logger.warning(f"  ⚠️ Ep {ep_num} quality check failed: {len(quality_issues)} issues")
                for issue in quality_issues:
                    logger.warning(f"    • {issue}")
                
                if attempt > MAX_RETRIES:
                    logger.error(f"❌ Episode {ep_num}: Quality issues not resolved after {MAX_RETRIES} retries")
                    return {
                        "status": "error",
                        "message": f"Quality check failed after {MAX_RETRIES} retries:\n" + "\n".join(quality_issues),
                        "attempts": attempt,
                    }
                
                # Try to fix quality issues with Gemini (line fix first)
                logger.info(f"  🔧 Attempting to fix quality issues for episode {ep_num}...")
                
                # Convert quality issues to Violation objects for the line fixer
                quality_violations = []
                for i, issue in enumerate(quality_issues):
                    # Find the line number where this issue occurs
                    line_num = 1
                    for line_idx, line in enumerate(current_data["manim_code_lines"]):
                        if 'scale_to_fit_width' in line and 'Missing scale_to_fit_width' in issue:
                            line_num = line_idx + 1
                            break
                        elif 'font_size=' in issue:
                            if 'font_size' in line:
                                line_num = line_idx + 1
                                break
                        elif 'MathTex' in line and 'Thai' in issue:
                            line_num = line_idx + 1
                            break
                    else:
                        line_num = len(current_data["manim_code_lines"])
                    
                    # Create a Violation-like object
                    class QualityViolation:
                        def __init__(self, line, rule, description):
                            self.line = line
                            self.rule = rule
                            self.description = description
                            self.snippet = current_data["manim_code_lines"][line-1] if line <= len(current_data["manim_code_lines"]) else ""
                    
                    quality_violations.append(QualityViolation(line_num, f"QUALITY_{i}", issue))
                
                # Try line fix first (cheaper API call)
                fixed_code = self._ask_gemini_to_fix_lines(
                    code="\n".join(current_data["manim_code_lines"]),
                    violations=quality_violations,
                )
                
                if fixed_code is not None:
                    current_data["manim_code_lines"] = fixed_code.splitlines()
                    logger.info(f"  ✅ Quality issues sent to Gemini for line fix")
                    continue  # re-validate and re-check quality
                else:
                    # If line fix fails, try full fix
                    logger.warning(f"  ⚠️ Line fix failed, trying full-file fix for quality issues")
                    fixed_lines = self._ask_gemini_to_fix(
                        original_code="\n".join(current_data["manim_code_lines"]),
                        error_message=f"Quality check failed:\n" + "\n".join(quality_issues),
                    )
                    if fixed_lines is not None:
                        current_data["manim_code_lines"] = fixed_lines
                        logger.info(f"  ✅ Quality issues sent to Gemini for full fix")
                        continue
                    else:
                        logger.warning(f"  ⚠️ Gemini unavailable for quality fix, attempting render anyway")
                        # Fall through to render

            # ── Step 1: Security check ───────────────────────────────────────
            filepath, code_string = self._write_scene_file(current_data, filename)
            is_safe, safety_msg = self._validate_code(code_string)
            if not is_safe:
                logger.error(f"🔒 Security validation failed: {safety_msg}")
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
                logger.info(f"✅ Episode {ep_num} rendered OK on attempt {attempt}.")
                mp4_path = self._resolve_rendered_mp4_path(filepath)

                upload_doc = None
                if uid and os.path.exists(mp4_path):
                    logger.info(f"📤 Uploading video to Firebase for episode {ep_num}...")
                    upload_doc = upload_episode_video(
                        mp4_path,
                        uid=uid,
                        episode_number=ep_num,
                        lesson_id=lesson_id,
                        question_title=episode_data.get("question_title"),
                    )
                    if upload_doc is None:
                        logger.warning(
                            f"⚠️ Episode {ep_num}: render succeeded but Firestore/"
                            "Storage upload was skipped or failed (non-fatal — "
                            f"video still exists locally at {mp4_path})"
                        )
                    else:
                        logger.info(f"✅ Episode {ep_num} uploaded successfully!")
                        logger.info(f"   Video URL: {upload_doc.get('video_url')}")
                        logger.info(f"   Document ID: {upload_doc.get('doc_id')}")
                elif uid and not os.path.exists(mp4_path):
                    logger.warning(
                        f"⚠️ Episode {ep_num}: render reported success but expected "
                        f"mp4 not found at {mp4_path} — skipping upload."
                    )
                elif not uid:
                    logger.info(f"ℹ️ No uid provided, skipping Firebase upload for episode {ep_num}")

                logger.info(f"✅ Episode {ep_num} complete!")
                return {
                    "status": "success",
                    "filepath": filepath,
                    "video_path": mp4_path,
                    "video_url": upload_doc["video_url"] if upload_doc else None,
                    "output": render_output,
                    "attempts": attempt,
                }

            logger.warning(
                f"❌ Episode {ep_num} attempt {attempt} render failed:\n"
                + render_output[:400]
            )
            if attempt > MAX_RETRIES:
                break

            fixed_lines = self._ask_gemini_to_fix(
                original_code=code_string,
                error_message=render_output,
            )
            if fixed_lines is None:
                logger.warning(f"⚠️ Ep {ep_num}: Gemini unavailable on render error. Stopping.")
                break
            current_data["manim_code_lines"] = fixed_lines

        logger.error(f"❌ Episode {ep_num} failed after {min(attempt, MAX_RETRIES + 1)} attempts")
        return {
            "status": "error",
            "message": render_output,
            "attempts": min(attempt, MAX_RETRIES + 1),
        }

    def render_all_episodes(self, lesson_json: dict, *, uid: str | None = None, lesson_id: str | None = None) -> list[dict]:
        episodes = lesson_json.get("episodes", [])
        total = len(episodes)
        
        logger.info(f"🎬 ===== RENDERING ALL {total} EPISODES =====")
        logger.info(f"   uid={uid}, lesson_id={lesson_id}")
        
        results = []
        for i, episode in enumerate(episodes, 1):
            logger.info(f"📹 Processing episode {i}/{total}")
            result = self.render_episode(episode, uid=uid, lesson_id=lesson_id)
            result["episode_number"] = episode.get("episode_number")
            results.append(result)
            
            # Log summary after each episode
            status = result.get("status", "unknown")
            logger.info(f"📊 Episode {i} status: {status}")
            if status == "success":
                logger.info(f"   Video URL: {result.get('video_url', 'N/A')}")
            else:
                logger.warning(f"   Error: {result.get('message', 'Unknown error')[:100]}")
        
        # Summary of all episodes
        success_count = sum(1 for r in results if r.get("status") == "success")
        logger.info(f"🏁 ===== RENDER COMPLETE: {success_count}/{total} episodes successful =====")
        
        return results

    def count_questions_first(self, page_content: str) -> int:
        try:
            response = self.gemini_client.models.generate_content(
                model="gemini-3.5-flash",
                contents=COUNT_PROMPT + "\n\nเนื้อหา:\n" + page_content,
                config=types.GenerateContentConfig(temperature=0.1),
            )
            raw = response.text.strip()
            raw = re.sub(r"^```(?:json)?\s*", "", raw)
            raw = re.sub(r"\s*```$", "", raw)
            data = json.loads(raw)
            count = data.get("question_count", 1)
            logger.info(f"📊 Pre-scan: {count} question(s): {data.get('question_titles', [])}")
            return count
        except Exception as e:
            logger.warning(f"⚠️ Question count pre-scan failed: {e} — defaulting to 1")
            return 1