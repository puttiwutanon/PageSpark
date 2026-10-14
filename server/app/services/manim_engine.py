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
from app.core.episode_schema import EpisodeData
from app.services.scene_compiler import compile_scene, BOILERPLATE_HEADER, IND
from app.services.episode_sanitizer import sanitize_episode_dict, normalize_diagram_lines
from app.services.audio_engine import AudioEngine
from app.services.video_engine import VideoEngine
from app.storage.cloudinary_storage import upload_episode_video

load_dotenv()

# Enhanced logging configuration
logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

MAX_RETRIES = 1

# The diagram fragment is validated INSIDE the boilerplate header (so the
# validator sees frame_width / middle_center / np defined, exactly like the old
# full-scene pipeline did) and delimited by markers so it can be cut back out.
_FRAG_START = IND + "# <<<DIAGRAM_START>>>"
_FRAG_END = IND + "# <<<DIAGRAM_END>>>"


def _wrap_fragment(fragment: list[str]) -> str:
    body = fragment if any(l.strip() for l in fragment) else [IND + "pass"]
    return "\n".join(BOILERPLATE_HEADER + [_FRAG_START] + body + [_FRAG_END])


def _fragment_bounds(lines: list[str]) -> tuple[int | None, int | None]:
    s = next((i for i, l in enumerate(lines) if "<<<DIAGRAM_START>>>" in l), None)
    e = next((i for i, l in enumerate(lines) if "<<<DIAGRAM_END>>>" in l), None)
    return s, e


def _extract_fragment(code: str) -> list[str] | None:
    """Cut the diagram fragment back out of a wrapped scene. If a Gemini
    full-rewrite dropped the markers, fall back to everything after the zone
    boilerplate (the last boilerplate line is `bottom_center = ...`)."""
    lines = code.splitlines()
    s, e = _fragment_bounds(lines)
    if s is None:
        idx = [i for i, l in enumerate(lines) if l.strip().startswith("bottom_center = np.array")]
        if not idx:
            return None
        s = idx[-1]
    if e is None or e <= s:
        e = len(lines)
    frag = lines[s + 1:e]
    return [l for l in frag if "<<<DIAGRAM_" not in l]


def _quality_check(self, code_lines: list[str]) -> tuple[bool, list[str]]:
    """Run a quick quality check on the generated code."""
    issues = []
    code_str = "\n".join(code_lines)

    thai_in_mathtex = re.compile(
        r'MathTex\s*\([^)]*[\u0E00-\u0E7F]'
    )
    if thai_in_mathtex.search(code_str):
        issues.append("Thai characters found in MathTex()")

    latex_in_text = re.compile(
        r'Text\s*\([^)]*\\(?:frac|sqrt|sum|int|prod|lim|partial)'
    )
    if latex_in_text.search(code_str):
        issues.append("Complex LaTeX commands (\\frac, \\sqrt etc.) found in Text()")

    return len(issues) == 0, issues


def smart_json_sanitize(raw: str) -> str:
    """
    Robust JSON sanitizer for Gemini responses that contain Manim/Python code.
    
    Handles:
    1. Invalid backslash escapes in JSON strings
    2. Unescaped quotes inside strings
    3. Trailing commas
    4. Missing quotes around keys
    """
    import re
    
    # First, try to extract just the JSON part if there's extra text
    # Look for { ... } pattern
    json_match = re.search(r'\{[^{}]*"episodes"[\s\S]*\}', raw)
    if json_match:
        raw = json_match.group(0)
    
    # Step 1: Protect already-doubled backslashes
    DB_PLACEHOLDER = '\x00__DB__\x00'
    UNI_PLACEHOLDER = '\x00__UNI__\x00'
    
    raw = raw.replace('\\\\', DB_PLACEHOLDER)
    
    # Step 2: Protect valid \\uXXXX unicode escapes
    raw = re.sub(
        r'\\u[0-9a-fA-F]{4}',
        lambda m: UNI_PLACEHOLDER + m.group(0)[2:],
        raw
    )
    
    # Step 3: Fix common LaTeX backslash issues in strings
    # This is the key fix - handle \frac, \sin, \cos, etc.
    # We need to double all backslashes that are part of LaTeX commands
    
    # Find all string content in the JSON
    def fix_string_content(content):
        # `content` is already the captured string (m.group(1)) — not a match object.
        # Double backslashes that are part of LaTeX commands
        # but only if they're not already doubled
        latex_commands = [
            'frac', 'sqrt', 'sin', 'cos', 'tan', 'log', 'ln',
            'lambda', 'phi', 'theta', 'alpha', 'beta', 'gamma',
            'delta', 'epsilon', 'zeta', 'eta', 'iota', 'kappa',
            'mu', 'nu', 'xi', 'pi', 'rho', 'sigma', 'tau',
            'upsilon', 'chi', 'psi', 'omega', 'Gamma', 'Delta',
            'Theta', 'Lambda', 'Xi', 'Pi', 'Sigma', 'Phi',
            'Psi', 'Omega', 'mathrm', 'mathbf', 'textit',
            'text', 'widehat', 'widetilde', 'rightarrow',
            'leftarrow', 'Rightarrow', 'Leftarrow', 'left',
            'right', 'cdot', 'times', 'pm', 'mp', 'leq', 'geq',
            'neq', 'approx', 'equiv', 'infty', 'partial',
            'sum', 'prod', 'int', 'iint', 'iiint', 'oint',
        ]
        
        # Don't modify if it's already properly escaped
        if '\\\\' in content:
            return content
        
        # Double backslashes before known LaTeX commands
        for cmd in latex_commands:
            content = content.replace(f'\\{cmd}', f'\\\\{cmd}')
        
        # Fix spacing commands
        content = content.replace('\\,', '\\\\,')
        content = content.replace('\\;', '\\\\;')
        content = content.replace('\\!', '\\\\!')
        
        # Fix \circ
        content = content.replace('\\circ', '\\\\circ')
        
        return content
    
    # Find and fix all string content in the JSON
    # This handles both double-quoted and single-quoted strings
    pattern = re.compile(r'"([^"\\]*(?:\\.[^"\\]*)*)"')
    raw = pattern.sub(lambda m: f'"{fix_string_content(m.group(1))}"', raw)
    
    # Also handle single-quoted strings in Python code
    pattern2 = re.compile(r"'([^'\\]*(?:\\.[^'\\]*)*)'")
    raw = pattern2.sub(lambda m: f"'{fix_string_content(m.group(1))}'", raw)
    
    # Step 4: Double all remaining single backslashes that aren't already doubled
    # But be careful not to double already-doubled ones
    raw = re.sub(r'(?<!\\)\\(?!\\)', r'\\\\', raw)
    
    # Step 5: Restore protected sequences
    raw = raw.replace(DB_PLACEHOLDER, '\\\\')
    raw = raw.replace(UNI_PLACEHOLDER, '\\u')
    
    # Step 6: Fix trailing commas in arrays and objects
    raw = re.sub(r',\s*}', '}', raw)
    raw = re.sub(r',\s*]', ']', raw)
    
    # Step 7: Fix missing quotes around keys
    raw = re.sub(r'([{,])\s*([a-zA-Z_][a-zA-Z0-9_]*)\s*:', r'\1"\2":', raw)
    
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

❌ WRONG — aligned_edge=CENTER:
    VGroup(...).arrange(DOWN, aligned_edge=CENTER, buff=0.15)
✅ CORRECT — ใช้ LEFT หรือ RIGHT เท่านั้น:
    VGroup(...).arrange(DOWN, aligned_edge=LEFT, buff=0.15)

❌ WRONG — VGroup(*[...]) list comprehension:
    VGroup(*[Text(line, font='TH Sarabun New', font_size=26) for line in lines])
✅ CORRECT:
    VGroup(Text('A', ...), Text('B', ...)).arrange(DOWN, aligned_edge=LEFT, buff=0.1)

❌ WRONG — LaTeX ใน Text():
    Text('หาความยาวคลื่น (\\lambda)', ...)
✅ CORRECT:
    Text('หาความยาวคลื่น (λ)', font='TH Sarabun New', font_size=26, color=GOLD_B)

❌ WRONG — Thai ใน MathTex():
    MathTex(r'\\text{{ระยะห่างบัพ}} = \\frac{{\\lambda}}{{2}}', ...)
✅ CORRECT:
    VGroup(Text('ระยะห่างบัพ', ...), MathTex(r'= \\frac{{\\lambda}}{{2}}', ...))

❌ WRONG — .move_to(scalar):
    group.move_to(bottom_zone_center_y)
✅ CORRECT:
    group.move_to(bottom_center)

ส่งคืนเฉพาะ JSON เท่านั้น:
{{"manim_code_lines": ["import numpy as np", "from manim import *", ...]}}
"""


LINE_FIX_PROMPT_TEMPLATE = """
คุณเป็น Manim developer ที่แก้บั๊กแบบ surgical — แก้เฉพาะบรรทัดที่ระบุเท่านั้น

{violation_blocks}

══ กฎเหล็ก — ดูตัวอย่างก่อน/หลังแล้วแก้ตามนี้เสมอ ══

⚠️ สำคัญที่สุด: context ที่แสดงให้ดูมีไว้เพื่อให้คุณเข้าใจชื่อตัวแปรที่เกี่ยวข้องเท่านั้น
ห้ามคืนค่า context เหล่านั้นซ้ำ และห้ามลบ/แก้ไขบรรทัดอื่นที่ไม่ใช่บรรทัดที่ระบุไว้โดยเด็ดขาด
คำตอบของคุณสำหรับแต่ละ context_id ต้องเป็น "ตัวแทนใหม่ของบรรทัดที่ถูกชี้เป้าเท่านั้น" —
ถ้าต้องเพิ่มบรรทัดใหม่ (เช่นเพิ่ม .scale_to_fit_width() ต่อท้าย) ให้เพิ่มเป็นบรรทัดถัดจากบรรทัดเดิม
ในลิสต์เดียวกันได้ แต่ห้ามพิมพ์ซ้ำบรรทัดใดๆ ที่อยู่ก่อนหรือหลังบรรทัดเป้าหมายในหน้าต่าง context

❌ WRONG — aligned_edge=CENTER:
    VGroup(...).arrange(DOWN, aligned_edge=CENTER, buff=0.15)
✅ CORRECT:
    VGroup(...).arrange(DOWN, aligned_edge=LEFT, buff=0.15)

❌ WRONG — LaTeX ใน Text(): Text('หาความยาวคลื่น (\\lambda)', ...)
✅ CORRECT: Text('หาความยาวคลื่น (λ)', ...)

❌ WRONG — MISSING_SCALING, บรรทัดเป้าหมายคือ:
    step1_group = VGroup(step1_title, eq1).arrange(DOWN, aligned_edge=LEFT, buff=0.15)
✅ CORRECT — คืนค่าเป็น 2 บรรทัดแทนบรรทัดเป้าหมายบรรทัดเดียว (ไม่แตะบรรทัดอื่น):
    ["        step1_group = VGroup(step1_title, eq1).arrange(DOWN, aligned_edge=LEFT, buff=0.15)",
     "        step1_group.scale_to_fit_width(frame_width * 0.88)"]

ส่งคืนเฉพาะ JSON โดยแต่ละ context_id คือ "บรรทัดทดแทนของบรรทัดเป้าหมายเท่านั้น" (1 บรรทัดขึ้นไป):
{{"fixes": {{"<context_id>": ["บรรทัดที่แก้ 1", "บรรทัดที่แก้ 2 (ถ้ามี)"]}}}}
"""


COUNT_PROMPT = """
    อ่านเนื้อหาที่ผู้ใช้ส่งมาและนับจำนวนโจทย์ฟิสิกส์ที่แยกจากกันได้ทั้งหมด
    ส่งคืน JSON เท่านั้น: {"question_count": <number>, "question_titles": ["...", "..."]}
    """


class Manim_Engine:
    def __init__(self, output_dir: str = "renders"):
        self.output_dir = output_dir
        os.makedirs(output_dir, exist_ok=True)
        os.makedirs(os.path.join(output_dir, "audio"), exist_ok=True)
        os.makedirs(os.path.join(output_dir, "final"), exist_ok=True)
        os.makedirs(os.path.join(output_dir, "videos"), exist_ok=True)
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
        """Find the rendered MP4 file."""
        stem = os.path.splitext(os.path.basename(scene_filepath))[0]
        path = os.path.join(self.output_dir, "videos", stem, "1920p60", "PhysicsScene.mp4")
        
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

    @staticmethod
    def _extract_meaningful_error(raw_output: str, tail_chars: int = 3000) -> str:
        """Extract meaningful error from manim output."""
        if not raw_output:
            return raw_output
        marker_idx = raw_output.rfind("Traceback (most recent call last)")
        if marker_idx != -1:
            return raw_output[marker_idx:][:tail_chars]
        return raw_output[-tail_chars:] if len(raw_output) > tail_chars else raw_output

    def _run_manim(self, filepath: str) -> tuple[bool, str]:
        """Run manim render with -ql (low quality for faster testing)."""
        cmd = ["manim", "-ql", filepath, "PhysicsScene", "--media_dir", self.output_dir]
        logger.info(f"🎬 Running manim command: {' '.join(cmd)}")
        
        try:
            result = subprocess.run(cmd, capture_output=True, text=True, check=True, timeout=300)
            output = result.stdout
            
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
            raw_error_output = exc.stderr or exc.stdout or ""
            logger.error(f"❌ Manim render failed with error code {exc.returncode}")
            meaningful_error = self._extract_meaningful_error(raw_error_output)
            logger.error(f"Error output (extracted, {len(meaningful_error)} chars): {meaningful_error}")
            return False, meaningful_error
        except subprocess.TimeoutExpired:
            logger.error("❌ Manim render timed out after 300 seconds.")
            return False, "Render timed out after 300 seconds."

    def _ask_gemini_to_fix(
        self,
        original_code: str,
        error_message: str,
        violation_summary: str | None = None,
    ) -> list[str] | None:
        """Ask Gemini to fix the code."""
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
                raw = re.sub(r"^```(?:json|python)?\s*", "", raw)
                raw = re.sub(r"\s*```$", "", raw)
                raw = smart_json_sanitize(raw)

                try:
                    parsed = json.loads(raw)
                except json.JSONDecodeError as e:
                    logger.error(f"Gemini fix JSON parse failed after sanitize: {e}")
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
                    logger.error(f"Gemini API quota exhausted (403): {exc}")
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
        """Targeted line fix for violations."""
        logger.info(f"🔧 Asking Gemini for targeted line fix ({len(violations)} violations)")
        
        lines = code.splitlines()

        blocks = []
        replace_ranges: dict[str, tuple[int, int]] = {}

        for i, v in enumerate(violations):
            ctx_id = f"v{i}_{v.rule}"
            line_idx = v.line - 1
            start = max(0, line_idx - context_radius)
            end = min(len(lines) - 1, line_idx + context_radius)

            numbered = "\n".join(
                f"{n + 1}: {lines[n]}" for n in range(start, end + 1)
            )
            blocks.append(
                f"--- context_id: {ctx_id} ---\n"
                f"[{v.rule}] {v.description}\n"
                f"บรรทัดที่ต้องแก้คือบรรทัด {v.line} เท่านั้น "
                f"(context ด้านล่างมีไว้ให้ดูชื่อตัวแปรที่เกี่ยวข้อง ห้ามคืนค่าบรรทัดอื่นนอกจากบรรทัด {v.line}):\n"
                f"{numbered}\n"
            )
            # IMPORTANT: only the single flagged line is ever spliced back in,
            # never the full context window — this guarantees neighboring
            # lines (e.g. variable definitions used by the flagged line)
            # can never be silently dropped by a short Gemini response.
            replace_ranges[ctx_id] = (line_idx, line_idx)

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
                    return None

                fixes = parsed.get("fixes")
                if not isinstance(fixes, dict) or not fixes:
                    logger.warning("Gemini line-fix response had no usable 'fixes' field.")
                    return None

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
        """Ensure episode count matches expected."""
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
                "problem_desc": "",
                "core_vocabulary": [],
                "video_plan": {"estimated_duration_seconds": 60, "visual_cues": "", "audio_cues": ""},
                "script": {"hook": "", "main_body": "", "example_or_trick": "", "call_to_action": ""},
                "voiceover_script": [],
                "diagram_code_lines": [],
                "steps": [],
            })
        lesson_json["episodes"] = episodes
        lesson_json["total_episodes"] = expected_count
        logger.info(f"✅ Episode count enforced: now {len(episodes)} episodes")
        return lesson_json

    def _validate_and_fix_fragment(self, fragment: list[str], ep_num, allow_gemini: bool = True) -> list[str]:
        """Run the deterministic auto-fixers + detectors over ONLY the diagram
        fragment (wrapped in the boilerplate so names resolve), optionally ask
        Gemini for targeted line fixes, and return the best fragment we have."""
        for fix_round in range(MAX_RETRIES + 1):
            val = preprocess_code(_wrap_fragment(fragment))
            if val.auto_fixes:
                logger.info(f"  🔧 Ep {ep_num} diagram auto-fixes ({len(val.auto_fixes)}):")
                for fix in val.auto_fixes:
                    logger.info(f"    • {fix}")

            fixed_code = val.fixed_code
            extracted = _extract_fragment(fixed_code)
            if extracted is not None:
                fragment = extracted

            # Only violations that point INSIDE the fragment are ours to fix;
            # BOTTOM_ZONE_EMPTY is meaningless here (the compiler owns that zone).
            s, e = _fragment_bounds(fixed_code.splitlines())
            relevant = []
            for v in val.violations:
                if v.rule == "BOTTOM_ZONE_EMPTY":
                    continue
                if v.rule == "SYNTAX_ERROR" or (s is not None and e is not None and s + 2 <= v.line <= e):
                    relevant.append(v)

            if not relevant:
                return fragment

            logger.warning(f"  ⚠️ Ep {ep_num}: {len(relevant)} diagram violation(s) after auto-fix:")
            for v in relevant:
                logger.warning(f"    [{v.rule}] line {v.line}: {str(v.snippet)[:60]}")

            if not allow_gemini or fix_round >= MAX_RETRIES:
                return fragment

            patched = self._ask_gemini_to_fix_lines(code=fixed_code, violations=relevant)
            new_frag = _extract_fragment(patched) if patched else None
            if not new_frag:
                return fragment
            fragment = normalize_diagram_lines(new_frag)
        return fragment

    async def render_episode(self, episode_data: dict, *, uid: str | None = None, lesson_id: str | None = None) -> dict:
        """Render one episode through the TEMPLATE pipeline:

            structured JSON -> sanitize -> EpisodeData -> validate diagram
            fragment -> compile_scene() -> manim -> audio -> upload

        Attempts 1..MAX_RETRIES+1 render the full scene (the diagram fragment is
        repaired by Gemini between attempts). The LAST attempt renders without
        the diagram so a bad diagram can never cost the user the whole video —
        title + equation steps are compiler-generated and always safe.
        """
        ep_num = episode_data.get("episode_number", 0)
        logger.info(f"🔄 ===== STARTING RENDER for episode {ep_num} =====")
        logger.info(f"   uid={uid}, lesson_id={lesson_id}")
        logger.info(f"   title={episode_data.get('title', 'Untitled')}")

        filename = f"scene_ep_{ep_num}.py"
        current_data = dict(episode_data)
        render_output = "No render attempted yet."

        # ── Step 0: sanitize + schema-validate ─────────────────────────────
        try:
            episode = EpisodeData.model_validate(sanitize_episode_dict(episode_data))
        except Exception as exc:
            msg = f"Episode {ep_num} does not match the EpisodeData schema: {exc}"
            logger.error(f"❌ {msg}")
            return {"status": "error", "message": msg, "attempts": 0}

        # ── Step 1: validate/fix ONLY the diagram fragment ─────────────────
        fragment = list(episode.diagram_code_lines)
        if any(l.strip() for l in fragment):
            fragment = self._validate_and_fix_fragment(fragment, ep_num)
        else:
            logger.info(f"  ℹ️ Ep {ep_num}: no diagram_code_lines — rendering title + steps only")

        total_attempts = MAX_RETRIES + 2          # last one = diagram-less fallback
        attempt = 0
        for attempt in range(1, total_attempts + 1):
            degraded = attempt == total_attempts
            if degraded and not any(l.strip() for l in fragment):
                break  # nothing to drop — the previous attempt already was diagram-less
            logger.info(
                f"📹 Episode {ep_num} — render attempt {attempt}/{total_attempts}"
                + (" (FALLBACK: no diagram)" if degraded else "")
            )

            # ── Step 2: compile (trusted by construction — never re-validated) ──
            current_data["manim_code_lines"] = compile_scene(episode, [] if degraded else fragment)
            filepath, code_string = self._write_scene_file(current_data, filename)

            # ── Step 3: syntax + security check on the final file ──────────────
            is_safe, safety_msg = self._validate_code(code_string)
            if is_safe:
                success, render_output = self._run_manim(filepath)
            else:
                logger.error(f"🔒 Validation failed: {safety_msg}")
                if os.path.exists(filepath):
                    os.remove(filepath)
                success, render_output = False, f"Validation failed: {safety_msg}"

            if success:
                logger.info(f"✅ Episode {ep_num} rendered OK on attempt {attempt}.")
                mp4_path = self._resolve_rendered_mp4_path(filepath)
                
                # ── Generate Audio ──────────────────────────────────────────
                audio_engine = AudioEngine(output_dir=os.path.join(self.output_dir, "audio"))
                audio_result = await audio_engine.generate_episode_audio(episode_data)
                
                final_video_path = None
                audio_path = audio_result.get("audio_path") if audio_result.get("status") in ["success", "partial"] else None
                
                if audio_path and os.path.exists(audio_path):
                    logger.info(f"✅ Audio generated: {audio_path}")
                    # ── Combine Video + Audio ──────────────────────────────
                    video_engine = VideoEngine(output_dir=os.path.join(self.output_dir, "final"))
                    final_video_path = video_engine.combine_video_audio(
                        video_path=mp4_path,
                        audio_path=audio_path,
                        episode_number=ep_num,
                    )
                    
                    if final_video_path and os.path.exists(final_video_path):
                        logger.info(f"✅ Final combined video created: {final_video_path}")
                        # Use final video for upload
                        upload_video_path = final_video_path
                    else:
                        logger.warning(f"⚠️ Video+Audio combination failed, using raw video")
                        upload_video_path = mp4_path
                else:
                    logger.warning(f"⚠️ Audio generation failed, using raw video")
                    upload_video_path = mp4_path
                
                # ── Upload to Cloudinary ─────────────────────────────────────────
                # IMPORTANT: a render that finishes locally but never makes it
                # into Cloudinary/Firestore is NOT a success from the caller's
                # point of view (nothing shows up in the app/DB). We track the
                # upload outcome explicitly and let it determine the episode's
                # final status instead of always reporting "success" the
                # moment Manim itself didn't crash.
                upload_doc = None
                upload_status = "skipped_no_uid"
                upload_error = None

                if uid:
                    if os.path.exists(upload_video_path):
                        logger.info(f"📤 Uploading final video to Cloudinary for episode {ep_num}...")
                        upload_doc = upload_episode_video(
                            upload_video_path,  # Use the combined video path
                            uid=uid,
                            episode_number=ep_num,
                            lesson_id=lesson_id,
                            # BUG FIX: episode JSON uses the key "title", not
                            # "question_title" (which never exists in the
                            # schema) — the old code silently uploaded every
                            # video with this metadata field set to None.
                            question_title=episode_data.get("title"),
                        )
                        if upload_doc is None:
                            upload_status = "failed"
                            upload_error = (
                                f"upload_episode_video() returned None for episode {ep_num} "
                                f"— see cloudinary_storage logs above for the underlying cause"
                            )
                            logger.error(f"❌ Episode {ep_num}: {upload_error}")
                        else:
                            upload_status = "uploaded"
                            logger.info(f"✅ Episode {ep_num} uploaded successfully!")
                            logger.info(f"   Video URL: {upload_doc.get('video_url')}")
                            logger.info(f"   Document ID: {upload_doc.get('doc_id')}")
                    else:
                        upload_status = "failed"
                        upload_error = (
                            f"Episode {ep_num}: expected rendered file not found at "
                            f"{upload_video_path} — nothing was uploaded"
                        )
                        logger.error(f"❌ {upload_error}")
                else:
                    logger.info(f"ℹ️ No uid provided, skipping upload for episode {ep_num}")

                # BUG FIX: this used to be unconditionally "success" as long
                # as Manim rendered locally, even when upload_doc was None or
                # the video file was missing — meaning the API and the app
                # would report a clean success while nothing ever reached
                # Cloudinary/Firestore. Now the episode is only "success" if
                # either no upload was requested (render-only mode) or the
                # upload genuinely completed.
                episode_status = "error" if upload_status == "failed" else "success"

                logger.info(
                    f"{'✅' if episode_status == 'success' else '❌'} "
                    f"Episode {ep_num} complete (status={episode_status}, upload={upload_status})"
                )
                return {
                    "status": episode_status,
                    "upload_status": upload_status,
                    "message": upload_error,  # None on success, explains failure otherwise
                    "filepath": filepath,
                    "video_path": upload_video_path,
                    "video_url": upload_doc["video_url"] if upload_doc else None,
                    "audio_result": audio_result if audio_result else None,
                    "output": render_output,
                    "attempts": attempt,
                    "degraded": degraded,  # True => rendered WITHOUT the diagram
                }

            logger.warning(
                f"❌ Episode {ep_num} attempt {attempt} render failed:\n"
                + render_output[:400]
            )
            # Gemini only repairs the diagram, and only before the fallback attempt.
            if not degraded and attempt <= MAX_RETRIES:
                fixed_lines = self._ask_gemini_to_fix(
                    original_code=_wrap_fragment(fragment),
                    error_message=render_output,
                )
                new_frag = _extract_fragment("\n".join(fixed_lines)) if fixed_lines else None
                if new_frag:
                    fragment = self._validate_and_fix_fragment(
                        normalize_diagram_lines(new_frag), ep_num, allow_gemini=False
                    )
                else:
                    logger.warning(f"⚠️ Ep {ep_num}: Gemini gave no usable diagram fix.")

        logger.error(f"❌ Episode {ep_num} failed after {attempt} attempts")
        return {
            "status": "error",
            "message": render_output,
            "attempts": attempt,
        }

    async def render_all_episodes(self, lesson_json: dict, *, uid: str | None = None, lesson_id: str | None = None) -> list[dict]:
        """Render all episodes with video + audio combination."""
        episodes = lesson_json.get("episodes", [])
        total = len(episodes)
        
        logger.info(f"🎬 ===== RENDERING ALL {total} EPISODES =====")
        logger.info(f"   uid={uid}, lesson_id={lesson_id}")
        
        results = []
        for i, episode in enumerate(episodes, 1):
            logger.info(f"📹 Processing episode {i}/{total}")
            try:
                result = await self.render_episode(episode, uid=uid, lesson_id=lesson_id)
            except Exception as exc:  # never let one episode abort the batch
                logger.error(f"❌ Episode {i} crashed: {exc}", exc_info=True)
                result = {"status": "error", "message": f"{type(exc).__name__}: {exc}", "attempts": 0}
            result["episode_number"] = episode.get("episode_number")
            results.append(result)
            
            status = result.get("status", "unknown")
            logger.info(f"📊 Episode {i} status: {status}")
            if status == "success":
                logger.info(f"   Video URL: {result.get('video_url', 'N/A')}")
            else:
                logger.warning(f"   Error: {(result.get('message') or 'Unknown error')[:100]}")
        
        success_count = sum(1 for r in results if r.get("status") == "success")
        logger.info(f"🏁 ===== RENDER COMPLETE: {success_count}/{total} episodes successful =====")

        return results

    # `render_all_episodes` intentionally still returns the raw per-episode
    # list — main.py's /api/generate-video endpoint is what turns that list
    # into a single overall status for the HTTP response, and it needs to
    # do that the same honest way render_episode itself now does (see the
    # fix comment above): count real successes instead of assuming success
    # just because this function returned without raising.

    def count_questions_first(self, page_content: str) -> int:
        """Count questions in the page content."""
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