"""
server/app/main.py

Changes vs original:
  - FIX #3: count_questions_first() is now called BEFORE generation,
    and enforce_episode_count() is called AFTER to catch the "only 1 episode"
    bug where Gemini stops early even when the page has 3 questions.
"""

import os
import tempfile
from fastapi import FastAPI, UploadFile, File, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from google import genai
from google.genai import types
from dotenv import load_dotenv
from pydantic import BaseModel
from typing import List

from app.core.prompts import LESSON_SUMMARY_SYSTEM_INSTRUCTION, QUIZ_GENERATION_SYSTEM_INSTRUCTION
from app.services.manim_engine import Manim_Engine
from app.services.code_validator import validate_episode_count

import re
import json
import logging

logger = logging.getLogger(__name__)

current_dir = os.path.dirname(os.path.abspath(__file__))
server_dir = os.path.dirname(current_dir)
load_dotenv(os.path.join(server_dir, ".env"))

app = FastAPI(title="PageSpark API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

client = genai.Client()
engine = Manim_Engine(output_dir="renders")

# ── Add this dictionary to map Frontend IDs to Thai Curriculum Topics ──
TOPIC_MAPPER = {
    'mechanics_1': 'กลศาสตร์ 1 (การเคลื่อนที่แนวตรง, นิวตัน, สมดุลกล)',
    'mechanics_2': 'กลศาสตร์ 2 (งานและพลังงาน, โมเมนตัม, การเคลื่อนที่แนวโค้ง)',
    'waves_light_sound': 'คลื่น เสียง และแสง',
    'electricity_magnetism': 'ไฟฟ้าสถิต, ไฟฟ้ากระแส, และแม่เหล็ก',
    'thermal_matter': 'ความร้อน แก๊ส และของไหล',
    'modern_physics': 'ฟิสิกส์อะตอม, นิวเคลียร์ และฟิสิกส์อนุภาค'
}

# ─────────────────────────────────────────────────────────────────────────────
# Pydantic Schemas for Quiz Generation Endpoints
# ─────────────────────────────────────────────────────────────────────────────
class QuizRequest(BaseModel):
    topics: List[str]
    questions_per_topic: int = 5 # ── UPDATED: Replaced 'count' with 'questions_per_topic'

class QuizItemSchema(BaseModel):
    question: str
    options: List[str]  
    correct_answer: str 
    step_by_step_solution: str

class QuizResponseSchema(BaseModel):
    quizzes: List[QuizItemSchema]

# ... [TOPIC_MAPPER remains the same] ...

@app.post("/api/generate-quiz", response_model=QuizResponseSchema)
async def generate_quiz(request: QuizRequest):
    """
    Endpoint to generate custom academic physics quiz questions using structured outputs.
    Ensures 100% JSON parsing compliance via Gemini schema controls.
    """
    try:
        # Translate topics and build exact instructions for Gemini
        translated_topics = [TOPIC_MAPPER.get(topic, topic) for topic in request.topics]
        
        # ── ADDED: Explicitly map the count to EACH topic to prevent AI confusion ──
        topics_instructions = "\n".join([f"- {topic}: จำนวน {request.questions_per_topic} ข้อ" for topic in translated_topics])
        total_questions = len(request.topics) * request.questions_per_topic

        user_prompt = f"""
        จงสร้างชุดข้อสอบปรนัยรายวิชาฟิสิกส์รวมทั้งหมด {total_questions} ข้อ โดยแบ่งจำนวนข้อตามหัวข้ออย่างเคร่งครัดดังนี้:
        {topics_instructions}
        
        ข้อสอบจะต้องมีข้อที่เน้นแนวคิดความเข้าใจ และข้อคำนวณที่อิงจากหลักฟิสิกส์ ม.ปลาย ในระดับความยากที่เหมาะสม
        """

        response = client.models.generate_content(
            model='gemini-2.5-flash',
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
        
        print("\n" + "="*20 + f" GENERATED {total_questions} QUIZ QUESTIONS " + "="*20)
        print(json.dumps(parsed_data, indent=2, ensure_ascii=False))
        print("="*65 + "\n")

        return parsed_data

    except Exception as e:
        logger.error(f"generate_quiz failed: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/ingest")
async def ingest_and_summarize(file: UploadFile = File(...)):
    """
    Ingest a textbook page image/PDF and return a lesson summary JSON.
    This is the SUMMARY-only endpoint (no video rendering).
    """
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
            model='gemini-2.5-flash',
            contents=gemini_file,
            config=types.GenerateContentConfig(
                system_instruction=LESSON_SUMMARY_SYSTEM_INSTRUCTION,
                temperature=0.3,
            )
        )

        return {
            "status": "success",
            "filename": file.filename,
            "summary": response.text
        }

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

    finally:
        if temp_path and os.path.exists(temp_path):
            os.remove(temp_path)
        if gemini_file:
            client.files.delete(name=gemini_file.name)


@app.post("/api/generate-video")
async def generate_video(file: UploadFile = File(...)):
    """
    Full pipeline: upload page → count questions → generate lesson JSON
    → enforce episode count → render all episodes → return video paths.

    FIX #3: count_questions_first() is called before generation so we know
    how many episodes to expect, and enforce_episode_count() fills gaps if
    Gemini stops early.
    """
    temp_path = ""
    gemini_file = None

    try:
        suffix = os.path.splitext(file.filename)[1] or ".png"
        with tempfile.NamedTemporaryFile(delete=False, suffix=suffix) as temp_file:
            content = await file.read()
            temp_file.write(content)
            temp_path = temp_file.name

        # ── Step 1: Pre-scan to count questions ─────────────────────────────
        # Read the file as text for counting (works for images too — Gemini sees it)
        gemini_file_for_count = client.files.upload(file=temp_path)
        try:
            count_response = client.models.generate_content(
                model='gemini-2.5-flash',
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
            logger.info(f"Pre-scan found {expected_count} question(s): {question_titles}")
        except Exception as e:
            logger.warning(f"Pre-scan failed ({e}), defaulting to 1 episode")
            expected_count = 1
            question_titles = []
        finally:
            try:
                client.files.delete(name=gemini_file_for_count.name)
            except Exception:
                pass

        # ── Step 2: Generate lesson JSON (all episodes) ─────────────────────
        # Inject the expected episode count into the system prompt so Gemini
        # knows it MUST generate all N episodes, not just 1.
        dynamic_instruction = LESSON_SUMMARY_SYSTEM_INSTRUCTION + f"""

══════════════════════════════════════════════════
CRITICAL: จำนวน Episodes ที่ต้องสร้าง
══════════════════════════════════════════════════
หน้านี้มี {expected_count} โจทย์ คุณต้องสร้าง {expected_count} episodes เสมอ
(1 episode ต่อ 1 โจทย์) ห้ามหยุดหลัง episode แรกเด็ดขาด
total_episodes ต้องเป็น {expected_count} และ episodes array ต้องมี {expected_count} items
"""

        gemini_file = client.files.upload(file=temp_path)
        gen_response = client.models.generate_content(
            model='gemini-2.5-flash',
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
        except json.JSONDecodeError:
            fixed_raw = re.sub(r'\\(?!["\\/bfnrtu])', r'\\\\', raw_json)
            lesson_json = json.loads(fixed_raw)

        # ── Step 3: Enforce episode count ────────────────────────────────────
        # If Gemini only gave us 1 episode but we expected more, ask it to fill gaps.
        lesson_json = engine.enforce_episode_count(
            lesson_json=lesson_json,
            expected_count=expected_count,
            question_titles=question_titles,
        )

        # Validate the final count
        is_valid, validation_msg = validate_episode_count(lesson_json, expected_min=expected_count)
        if not is_valid:
            logger.warning(f"Episode count validation: {validation_msg}")
            # Continue anyway with whatever episodes we have — don't fail the whole request

        # ── Step 4: Render all episodes ──────────────────────────────────────
        render_results = engine.render_all_episodes(lesson_json)

        return {
            "status": "success",
            "filename": file.filename,
            "expected_episodes": expected_count,
            "question_titles": question_titles,
            "lesson_json": lesson_json,
            "render_results": render_results,
        }

    except Exception as e:
        logger.error(f"generate_video error: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))

    finally:
        if temp_path and os.path.exists(temp_path):
            os.remove(temp_path)
        if gemini_file:
            try:
                client.files.delete(name=gemini_file.name)
            except Exception:
                pass