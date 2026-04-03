# FastAPI app entry point, route definitions

# main.py
import os
from fastapi import FastAPI, File, UploadFile, Form, Depends, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from dotenv import load_dotenv

from src.models import AnalyzeResponse
from src.extractor import extract_text
from src.analyzer import analyze_text
from src.auth import verify_api_key
from src.utils import detect_file_type, clean_text

load_dotenv()
app = FastAPI(title='Doc Analyzer API', version='1.0.0')

app.add_middleware(CORSMiddleware,
    allow_origins=['*'], allow_methods=['*'], allow_headers=['*'])

@app.get('/health')
async def health():
    return {'status': 'ok', 'version': '1.0.0'}

@app.post('/analyze', response_model=AnalyzeResponse)
async def analyze(
    file: UploadFile = File(...),
    type: str = Form(None),
    api_key: str = Depends(verify_api_key)
):
    file_bytes = await file.read()
    file_type = type or detect_file_type(file.filename, file.content_type)

    if file_type not in ('pdf', 'docx', 'image'):
        raise HTTPException(400, 'Unsupported file type')

    raw_text = extract_text(file_bytes, file_type)
    if not raw_text or len(raw_text.strip()) < 10:
        raise HTTPException(422, 'Could not extract readable text')

    text = clean_text(raw_text)
    result = analyze_text(text)
    result['filename'] = file.filename
    result['word_count'] = len(text.split())
    return AnalyzeResponse(**result)
