import os
import tempfile
from fastapi import FastAPI, UploadFile, File, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from google import genai
from google.genai import types  # <- Import types for Gemini configuration
from dotenv import load_dotenv

# Import your system instructions from the core module
from app.core.prompts import LESSON_SUMMARY_SYSTEM_INSTRUCTION

current_dir = os.path.dirname(os.path.abspath(__file__))
load_dotenv(os.path.join(current_dir, ".env"))

app = FastAPI(title="Summary Ingestion API")
client = genai.Client()

@app.post("/api/ingest")
async def ingest_and_summarize(file: UploadFile = File(...)):
    temp_path = ""
    gemini_file = None
    
    try:
        suffix = os.path.splitext(file.filename)[1] or ".png"
        with tempfile.NamedTemporaryFile(delete=False, suffix=suffix) as temp_file:
            content = await file.read()
            temp_file.write(content)
            temp_path = temp_file.name

        gemini_file = client.files.upload(file=temp_path)

        # Pass the system instruction via GenerateContentConfig
        response = client.models.generate_content(
            model='gemini-3.5-flash',
            contents=gemini_file,
            config=types.GenerateContentConfig(
                system_instruction=LESSON_SUMMARY_SYSTEM_INSTRUCTION,
                temperature=0.3 # Lower temperature for more accurate, factual summaries
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