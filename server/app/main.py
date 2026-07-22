"""
server/app/main.py
"""
import os
import tempfile
import re  # IMPORT re at the top
import json
import logging

from fastapi import FastAPI, UploadFile, File, Form, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from google import genai
from google.genai import types
from dotenv import load_dotenv
from pydantic import BaseModel
from typing import List, Optional
from firebase_admin import credentials, firestore, auth

from app.core.prompts import LESSON_SUMMARY_SYSTEM_INSTRUCTION, QUIZ_GENERATION_SYSTEM_INSTRUCTION
from app.services.code_validator import validate_episode_count
from app.api.videos import router as videos_router
from app.services.manim_engine import smart_json_sanitize, Manim_Engine

# Enhanced logging configuration
logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

current_dir = os.path.dirname(os.path.abspath(__file__))
server_dir = os.path.dirname(current_dir)
load_dotenv(os.path.join(server_dir, ".env"))

app = FastAPI(title="PageSpark API")

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include video router
app.include_router(videos_router)

# Initialize clients
client = genai.Client()
engine = Manim_Engine(output_dir="renders")

# Topic mapper
TOPIC_MAPPER = {
    'mechanics_1': 'กลศาสตร์ 1 (การเคลื่อนที่แนวตรง, นิวตัน, สมดุลกล)',
    'mechanics_2': 'กลศาสตร์ 2 (งานและพลังงาน, โมเมนตัม, การเคลื่อนที่แนวโค้ง)',
    'waves_light_sound': 'คลื่น เสียง และแสง',
    'electricity_magnetism': 'ไฟฟ้าสถิต, ไฟฟ้ากระแส, และแม่เหล็ก',
    'thermal_matter': 'ความร้อน แก๊ส และของไหล',
    'modern_physics': 'ฟิสิกส์อะตอม, นิวเคลียร์ และฟิสิกส์อนุภาค'
}


class QuizRequest(BaseModel):
    topics: List[str]
    questions_per_topic: int = 5


class QuizItemSchema(BaseModel):
    question: str
    options: List[str]
    correct_answer: str
    step_by_step_solution: str


class QuizResponseSchema(BaseModel):
    quizzes: List[QuizItemSchema]


def get_friendly_error_message(e: Exception) -> str:
    error_str = str(e).lower()

    if "429" in error_str or "resource_exhausted" in error_str or "quota" in error_str:
        if "per day" in error_str or "daily" in error_str:
            return "คุณใช้โควต้ารายวันหมดแล้ว กรุณาลองใหม่พรุ่งนี้ (Daily request limit reached — try again tomorrow)"
        return "มีการเรียกใช้งานถี่เกินไป กรุณารอสักครู่แล้วลองใหม่ (Rate limit hit — please wait a moment and retry)"

    if "503" in error_str or "unavailable" in error_str or "overloaded" in error_str:
        return "โมเดลกำลังมีผู้ใช้งานหนาแน่น กรุณาลองใหม่อีกครั้งในภายหลัง (Model is experiencing high demand — please try again later)"

    if "500" in error_str or "internal" in error_str:
        return "เกิดข้อผิดพลาดจากฝั่งเซิร์ฟเวอร์ Gemini กรุณาลองใหม่ (Gemini server error — please retry)"

    if "400" in error_str or "invalid" in error_str:
        return "รูปภาพหรือข้อมูลที่ส่งไปมีปัญหา กรุณาลองถ่ายรูปใหม่ (Invalid input — try a clearer photo)"

    if "truncat" in error_str or "json parsing failed" in error_str or "expecting value" in error_str:
        return "การสร้างเนื้อหายาวเกินไปและถูกตัดขาดกลางคัน กรุณาลองใหม่อีกครั้ง (Response was too long and got cut off — please retry)"

    return f"เกิดข้อผิดพลาดที่ไม่คาดคิด: {str(e)[:100]}"


@app.post("/api/generate-quiz", response_model=QuizResponseSchema)
async def generate_quiz(request: QuizRequest):
    """Generate custom academic physics quiz questions."""
    try:
        translated_topics = [TOPIC_MAPPER.get(topic, topic) for topic in request.topics]
        topics_instructions = "\n".join([
            f"- {topic}: จำนวน {request.questions_per_topic} ข้อ"
            for topic in translated_topics
        ])
        total_questions = len(request.topics) * request.questions_per_topic

        user_prompt = f"""
        จงสร้างชุดข้อสอบปรนัยรายวิชาฟิสิกส์รวมทั้งหมด {total_questions} ข้อ โดยแบ่งจำนวนข้อตามหัวข้ออย่างเคร่งครัดดังนี้:
        {topics_instructions}
        
        ข้อสอบจะต้องมีข้อที่เน้นแนวคิดความเข้าใจ และข้อคำนวณที่อิงจากหลักฟิสิกส์ ม.ปลาย ในระดับความยากที่เหมาะสม
        """

        response = client.models.generate_content(
            model='gemini-3.5-flash',
            contents=user_prompt,
            config=types.GenerateContentConfig(
                system_instruction=QUIZ_GENERATION_SYSTEM_INSTRUCTION,
                temperature=0.4,
                response_mime_type="application/json",
                response_schema=QuizResponseSchema,
            )
        )

        raw_response = response.text.strip()
        parsed_data = json.loads(raw_response)

        print("\n" + "="*20 + f" GENERATED {total_questions} QUIZ QUESTIONS " + "="*20, flush=True)
        print(json.dumps(parsed_data, indent=2, ensure_ascii=False), flush=True)
        print("="*65 + "\n", flush=True)

        return parsed_data

    except Exception as e:
        logger.error(f"❌ generate_quiz error: {e}", exc_info=True)
        friendly_msg = get_friendly_error_message(e)
        raise HTTPException(status_code=500, detail=friendly_msg)


@app.post("/api/ingest")
async def ingest_and_summarize(
    file: UploadFile = File(...),
    render: bool = Query(False, description="If true, also render videos and upload to Cloudinary"),
    uid: str = Query("anonymous", description="User ID for video uploads"),
    lesson_id: Optional[str] = Query(None, description="Lesson ID for grouping videos"),
):
    """Ingest a textbook page image/PDF and return a lesson summary JSON."""
    logger.info("=" * 60)
    logger.info(f"📥 /api/ingest called")
    logger.info(f"   file: {file.filename}")
    logger.info(f"   render: {render}")
    logger.info(f"   uid: {uid}")
    logger.info(f"   lesson_id: {lesson_id}")

    if render:
        logger.info("🔄 render=True detected — delegating to full video generation pipeline...")
        return await generate_video(file=file, uid=uid, lesson_id=lesson_id)

    temp_path = ""
    gemini_file = None

    try:
        suffix = os.path.splitext(file.filename)[1] or ".png"
        with tempfile.NamedTemporaryFile(delete=False, suffix=suffix) as temp_file:
            content = await file.read()
            temp_file.write(content)
            temp_path = temp_file.name

        gemini_file = client.files.upload(file=temp_path)

        response = client.models.generate_content(
            model='gemini-3.5-flash',
            contents=gemini_file,
            config=types.GenerateContentConfig(
                system_instruction=LESSON_SUMMARY_SYSTEM_INSTRUCTION,
                temperature=0.3,
            )
        )

        print("\n" + "="*20 + " INGEST SUMMARY " + "="*20, flush=True)
        print(response.text, flush=True)
        print("="*56 + "\n", flush=True)

        return {
            "status": "success",
            "filename": file.filename,
            "summary": response.text,
            "note": "Summary only. To render videos, use /api/generate-video or add ?render=true"
        }

    except Exception as e:
        logger.error(f"❌ ingest_and_summarize error: {e}", exc_info=True)
        friendly_msg = get_friendly_error_message(e)
        raise HTTPException(status_code=500, detail=friendly_msg)

    finally:
        if temp_path and os.path.exists(temp_path):
            os.remove(temp_path)
        if gemini_file:
            client.files.delete(name=gemini_file.name)


def _is_finish_reason_truncated(response) -> bool:
    """Return True if Gemini's response was cut off due to hitting max_output_tokens."""
    try:
        candidate = response.candidates[0]
        finish_reason = str(candidate.finish_reason)
        return "MAX_TOKENS" in finish_reason
    except Exception:
        return False


def _try_parse_lesson_json(raw_json: str) -> tuple[dict | None, list[str]]:
    """Try all three parsing strategies. Returns (parsed_dict_or_None, list_of_error_strings)."""
    parse_errors = []

    # Strategy 1: Direct parse
    try:
        return json.loads(raw_json), parse_errors
    except json.JSONDecodeError as e:
        parse_errors.append(f"Direct parse: {e}")

    # Strategy 2: Smart sanitize
    try:
        sanitized = smart_json_sanitize(raw_json)
        return json.loads(sanitized), parse_errors
    except json.JSONDecodeError as e2:
        parse_errors.append(f"Smart sanitize: {e2}")

    # Strategy 3: Aggressive fallback - fix all backslashes
    try:
        fixed_raw = raw_json
        fixed_raw = re.sub(r'(?<!\\)\\(?!["\\/bfnrtu])', r'\\\\', fixed_raw)
        fixed_raw = re.sub(r',\s*}', '}', fixed_raw)
        fixed_raw = re.sub(r',\s*]', ']', fixed_raw)
        return json.loads(fixed_raw), parse_errors
    except json.JSONDecodeError as e3:
        parse_errors.append(f"Aggressive fallback: {e3}")

    return None, parse_errors


@app.post("/api/generate-video")
async def generate_video(
    file: UploadFile = File(...),
    uid: str = Form(default="anonymous"),
    lesson_id: str = Form(default=None),
):
    """
    Full pipeline: upload page → count questions → generate lesson JSON
    → enforce episode count → render all episodes → upload to Cloudinary.
    """
    logger.info("=" * 60)
    logger.info("🎬 /api/generate-video called")
    logger.info(f"   file: {file.filename}")
    logger.info(f"   uid: {uid}")
    logger.info(f"   lesson_id: {lesson_id}")
    logger.info("=" * 60)

    temp_path = ""
    gemini_file = None

    try:
        suffix = os.path.splitext(file.filename)[1] or ".png"
        with tempfile.NamedTemporaryFile(delete=False, suffix=suffix) as temp_file:
            content = await file.read()
            temp_file.write(content)
            temp_path = temp_file.name
        logger.info(f"📁 Saved uploaded file to: {temp_path}")

        # ── Step 1: Pre-scan to count questions ─────────────────────────────
        # NOTE: this is a best-effort pre-scan. If it fails (rate limit, bad
        # JSON, etc.) we do NOT want to kill the whole request — we fall back
        # to a safe default of 1 episode and let the main generation step
        # (Step 2) do the real work. Only Step 2 failing should abort the
        # request.
        logger.info("🔍 Step 1: Pre-scanning for question count...")
        expected_count = 1
        question_titles = []
        gemini_file_for_count = None

        try:
            gemini_file_for_count = client.files.upload(file=temp_path)
            count_response = client.models.generate_content(
                model='gemini-3.5-flash',
                contents=[
                    gemini_file_for_count,
                    "นับจำนวนโจทย์ฟิสิกส์ในหน้านี้ "
                    + "ส่งคืน JSON เท่านั้น: "
                    + '{"question_count": <number>, "question_titles": ["...", "..."]}'
                ],
                config=types.GenerateContentConfig(temperature=0.1),
            )
            raw_count = count_response.text.strip()
            raw_count = re.sub(r"^```(?:json)?\s*", "", raw_count)
            raw_count = re.sub(r"\s*```$", "", raw_count)
            count_data = json.loads(raw_count)
            expected_count = count_data.get("question_count", 1)
            question_titles = count_data.get("question_titles", [])
            logger.info(f"✅ Pre-scan found {expected_count} question(s): {question_titles}")
        except Exception as e:
            logger.warning(f"⚠️ Pre-scan failed ({e}), defaulting to 1 episode and continuing")
            expected_count = 1
            question_titles = []
        finally:
            if gemini_file_for_count:
                try:
                    client.files.delete(name=gemini_file_for_count.name)
                except Exception:
                    pass

        # ── Step 2: Generate lesson JSON (with truncation-aware retry) ───────
        logger.info("📝 Step 2: Generating lesson JSON...")
        dynamic_instruction = LESSON_SUMMARY_SYSTEM_INSTRUCTION + f"""

══════════════════════════════════════════════════
CRITICAL: จำนวน Episodes ที่ต้องสร้าง
══════════════════════════════════════════════════
หน้านี้มี {expected_count} โจทย์ คุณต้องสร้าง {expected_count} episodes เสมอ
(1 episode ต่อ 1 โจทย์) ห้ามหยุดหลัง episode แรกเด็ดขาด
total_episodes ต้องเป็น {expected_count} และ episodes array ต้องมี {expected_count} items

สำคัญมาก: ห้ามเขียนโค้ด Manim ยาวเกินความจำเป็น ให้กระชับที่สุดเท่าที่จะทำได้
เพื่อไม่ให้ response ถูกตัดขาดกลางคัน (truncated)
"""

        gemini_file = client.files.upload(file=temp_path)

        lesson_json = None
        parse_errors = []
        max_gen_attempts = 3
        # Escalate the token budget on each retry in case the previous
        # attempt was truncated.
        token_budgets = [8192, 16384, 24576]

        for gen_attempt in range(max_gen_attempts):
            logger.info(
                f"⏳ Waiting for Gemini to generate lesson content "
                f"(attempt {gen_attempt + 1}/{max_gen_attempts}, "
                f"max_output_tokens={token_budgets[gen_attempt]})..."
            )
            gen_response = client.models.generate_content(
                model='gemini-3.5-flash',
                contents=gemini_file,
                config=types.GenerateContentConfig(
                    system_instruction=dynamic_instruction,
                    temperature=0.3,
                    response_mime_type="application/json",
                    max_output_tokens=token_budgets[gen_attempt],
                )
            )

            was_truncated = _is_finish_reason_truncated(gen_response)
            if was_truncated:
                logger.warning(
                    f"⚠️ Gemini response was TRUNCATED (hit max_output_tokens="
                    f"{token_budgets[gen_attempt]}) on attempt {gen_attempt + 1}"
                )

            raw_json = (gen_response.text or "").strip()
            raw_json = re.sub(r"^```(?:json)?\s*", "", raw_json)
            raw_json = re.sub(r"\s*```$", "", raw_json)

            lesson_json, parse_errors = _try_parse_lesson_json(raw_json)

            if lesson_json is not None:
                logger.info(
                    f"✅ Generated JSON with {len(lesson_json.get('episodes', []))} "
                    f"episodes on attempt {gen_attempt + 1}"
                )
                break

            logger.warning(
                f"⚠️ JSON parse failed on attempt {gen_attempt + 1}/{max_gen_attempts}: "
                f"{parse_errors} (truncated={was_truncated})"
            )
            # loop again with a bigger token budget, unless out of attempts

        if lesson_json is None:
            logger.error(f"❌ All {max_gen_attempts} generation attempts failed to produce valid JSON: {parse_errors}")
            raise HTTPException(
                status_code=500,
                detail="การสร้างวิดีโอล้มเหลวเนื่องจากเนื้อหายาวเกินไปและถูกตัดขาดซ้ำหลายครั้ง "
                       "กรุณาลองใหม่ หรือลองถ่ายรูปเฉพาะโจทย์เดียวต่อครั้ง "
                       "(Video generation failed — content kept getting cut off. "
                       "Please retry, or try photographing one question at a time.)"
            )

        # ── Step 3: Enforce episode count ────────────────────────────────────
        logger.info(f"📊 Step 3: Enforcing episode count (expected={expected_count})...")
        lesson_json = engine.enforce_episode_count(
            lesson_json=lesson_json,
            expected_count=expected_count,
            question_titles=question_titles,
        )

        is_valid, validation_msg = validate_episode_count(lesson_json, expected_min=expected_count)
        if not is_valid:
            logger.warning(f"⚠️ Episode count validation: {validation_msg}")
        else:
            logger.info("✅ Episode count validation passed")

        print("\n" + "="*20 + " GENERATED MANIM JSON " + "="*20, flush=True)
        print(json.dumps(lesson_json, indent=2, ensure_ascii=False), flush=True)
        print("="*62 + "\n", flush=True)

        # ── Step 4: Render all episodes ──────────────────────────────────────
        logger.info(f"🎬 Step 4: Rendering {len(lesson_json.get('episodes', []))} episodes...")
        render_results = await engine.render_all_episodes(lesson_json, uid=uid, lesson_id=lesson_id)

        # Log final results
        logger.info("=" * 60)
        logger.info("📊 RENDER RESULTS SUMMARY:")
        success_count = 0
        for result in render_results:
            ep_num = result.get("episode_number", "?")
            status = result.get("status", "unknown")
            logger.info(f"   Episode {ep_num}: {status}")
            if status == "success":
                success_count += 1
                logger.info(f"      Video URL: {result.get('video_url', 'N/A')}")
            else:
                logger.info(f"      Error: {result.get('message', 'Unknown')[:100]}")
        logger.info(f"📊 Total: {success_count}/{len(render_results)} episodes successful")
        logger.info("=" * 60)

        return {
            "status": "success",
            "filename": file.filename,
            "expected_episodes": expected_count,
            "question_titles": question_titles,
            "lesson_json": lesson_json,
            "render_results": render_results,
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"❌ generate_video error: {e}", exc_info=True)
        friendly_msg = get_friendly_error_message(e)
        raise HTTPException(status_code=500, detail=friendly_msg)

    finally:
        if temp_path and os.path.exists(temp_path):
            os.remove(temp_path)
        if gemini_file:
            try:
                client.files.delete(name=gemini_file.name)
            except Exception:
                pass


@app.get("/api/health")
async def health_check():
    """Health check endpoint."""
    return {"status": "healthy", "service": "PageSpark API"}


@app.get("/api/test-firebase")
async def test_firebase():
    """Test if Firebase is properly configured."""
    try:
        from app.storage.firebase_client import db
        test_ref = db.collection("test").document("test")
        test_ref.set({"test": "success", "timestamp": firestore.SERVER_TIMESTAMP})
        test_ref.delete()
        return {"status": "Firebase connected successfully!"}
    except Exception as e:
        return {"status": "error", "error": str(e)}