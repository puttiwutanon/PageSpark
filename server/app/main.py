"""
server/app/main.py
"""
import os
import tempfile
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
from app.services.manim_engine import Manim_Engine
from app.services.code_validator import validate_episode_count
from app.api.videos import router as videos_router

import re
import json
import logging

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

# Topic mapper (keep your existing one)
TOPIC_MAPPER = {
    'mechanics_1': 'กลศาสตร์ 1 (การเคลื่อนที่แนวตรง, นิวตัน, สมดุลกล)',
    'mechanics_2': 'กลศาสตร์ 2 (งานและพลังงาน, โมเมนตัม, การเคลื่อนที่แนวโค้ง)',
    'waves_light_sound': 'คลื่น เสียง และแสง',
    'electricity_magnetism': 'ไฟฟ้าสถิต, ไฟฟ้ากระแส, และแม่เหล็ก',
    'thermal_matter': 'ความร้อน แก๊ส และของไหล',
    'modern_physics': 'ฟิสิกส์อะตอม, นิวเคลียร์ และฟิสิกส์อนุภาค'
}

# ─────────────────────────────────────────────────────────────────────────────
# Pydantic Schemas (keep your existing ones)
# ─────────────────────────────────────────────────────────────────────────────
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

# ─────────────────────────────────────────────────────────────────────────────
# Endpoints (keep your existing ones)
# ─────────────────────────────────────────────────────────────────────────────

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
        logger.error(f"generate_quiz failed: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/ingest")
async def ingest_and_summarize(
    file: UploadFile = File(...),
    render: bool = Query(False, description="If true, also render videos and upload to Cloudinary"),
    uid: str = Query("anonymous", description="User ID for video uploads"),
    lesson_id: Optional[str] = Query(None, description="Lesson ID for grouping videos"),
):
    """
    Ingest a textbook page image/PDF and return a lesson summary JSON.
    
    By default, this is SUMMARY-ONLY (no video rendering).
    
    To also render videos and upload to Cloudinary, pass ?render=true:
    POST /api/ingest?render=true&uid=test_user&lesson_id=lesson_001
    """
    logger.info("=" * 60)
    logger.info(f"📥 /api/ingest called")
    logger.info(f"   file: {file.filename}")
    logger.info(f"   render: {render}")
    logger.info(f"   uid: {uid}")
    logger.info(f"   lesson_id: {lesson_id}")
    
    if render:
        logger.info("🔄 render=True detected — delegating to full video generation pipeline...")
        return await generate_video(file=file, uid=uid, lesson_id=lesson_id)
    
    # Summary-only mode
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
        raise HTTPException(status_code=500, detail=str(e))

    finally:
        if temp_path and os.path.exists(temp_path):
            os.remove(temp_path)
        if gemini_file:
            client.files.delete(name=gemini_file.name)


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
        logger.info("🔍 Step 1: Pre-scanning for question count...")
        gemini_file_for_count = client.files.upload(file=temp_path)
        try:
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
            logger.warning(f"⚠️ Pre-scan failed ({e}), defaulting to 1 episode")
            expected_count = 1
            question_titles = []
        finally:
            try:
                client.files.delete(name=gemini_file_for_count.name)
            except Exception:
                pass

        # ── Step 2: Generate lesson JSON ─────────────────────────────────────
        logger.info("📝 Step 2: Generating lesson JSON...")
        dynamic_instruction = LESSON_SUMMARY_SYSTEM_INSTRUCTION + f"""

══════════════════════════════════════════════════
CRITICAL: จำนวน Episodes ที่ต้องสร้าง
══════════════════════════════════════════════════
หน้านี้มี {expected_count} โจทย์ คุณต้องสร้าง {expected_count} episodes เสมอ
(1 episode ต่อ 1 โจทย์) ห้ามหยุดหลัง episode แรกเด็ดขาด
total_episodes ต้องเป็น {expected_count} และ episodes array ต้องมี {expected_count} items
"""

        gemini_file = client.files.upload(file=temp_path)
        logger.info("⏳ Waiting for Gemini to generate lesson content...")
        gen_response = client.models.generate_content(
            model='gemini-3.5-flash',
            contents=gemini_file,
            config=types.GenerateContentConfig(
                system_instruction=dynamic_instruction,
                temperature=0.3,
                response_mime_type="application/json",
            )
        )

        raw_json = gen_response.text.strip()
        raw_json = re.sub(r"^```(?:json)?\s*", "", raw_json)
        raw_json = re.sub(r"\s*```$", "", raw_json)

        try:
            lesson_json = json.loads(raw_json)
            logger.info(f"✅ Generated JSON with {len(lesson_json.get('episodes', []))} episodes")
        except json.JSONDecodeError as e:
            logger.warning(f"⚠️ JSON decode error, attempting fix: {e}")
            fixed_raw = re.sub(r'\\(?!["\\/bfnrtu])', r'\\\\', raw_json)
            lesson_json = json.loads(fixed_raw)
            logger.info("✅ Fixed JSON successfully")

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
        render_results = engine.render_all_episodes(lesson_json, uid=uid, lesson_id=lesson_id)

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

    except Exception as e:
        logger.error(f"❌ generate_video error: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))

    finally:
        if temp_path and os.path.exists(temp_path):
            os.remove(temp_path)
        if gemini_file:
            try:
                client.files.delete(name=gemini_file.name)
            except Exception:
                pass


# ── Health Check and Firebase Test ─────────────────────────────────────────────
@app.get("/api/health")
async def health_check():
    """Health check endpoint."""
    return {"status": "healthy", "service": "PageSpark API"}


@app.get("/api/test-firebase")
async def test_firebase():
    """Test if Firebase is properly configured."""
    try:
        from app.storage.firebase_client import db
        # Test Firestore
        test_ref = db.collection("test").document("test")
        test_ref.set({"test": "success", "timestamp": firestore.SERVER_TIMESTAMP})
        test_ref.delete()
        return {"status": "Firebase connected successfully!"}
    except Exception as e:
        return {"status": "error", "error": str(e)}