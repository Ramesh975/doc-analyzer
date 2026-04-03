import os
import base64
from fastapi import FastAPI, Header, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from dotenv import load_dotenv

from src.models import DocumentRequest, AnalyzeResponse, EntitiesResponse
from src.extractor import extract_text
from src.analyzer import analyze_text
from src.utils import detect_file_type, clean_text

load_dotenv()
app = FastAPI(title='Doc Analyzer API', version='1.0.0')

app.add_middleware(CORSMiddleware,
    allow_origins=['*'], allow_methods=['*'], allow_headers=['*'])

@app.get('/health')
async def health():
    return {'status': 'ok', 'version': '1.0.0'}

@app.post('/api/document-analyze', response_model=AnalyzeResponse)
async def analyze(request: DocumentRequest, x_api_key: str = Header(...)):
    # Auth check
    expected = os.getenv('API_KEY', '')
    if x_api_key != expected:
        raise HTTPException(401, 'Invalid or missing API key')

    # Decode base64 file
    try:
        file_bytes = base64.b64decode(request.fileBase64)
    except Exception:
        raise HTTPException(400, 'Invalid base64 encoding')

    # Detect file type
    file_type = request.fileType.lower()
    if file_type not in ('pdf', 'docx', 'image'):
        file_type = detect_file_type(request.fileName, '')
    if file_type not in ('pdf', 'docx', 'image'):
        raise HTTPException(400, 'Unsupported file type')

    # Extract text
    try:
        raw_text = extract_text(file_bytes, file_type)
    except Exception as e:
        return AnalyzeResponse(
            status='error',
            fileName=request.fileName,
            summary='Could not extract text from document.',
            entities=EntitiesResponse(names=[], dates=[], organizations=[], amounts=[]),
            sentiment='Neutral'
        )

    if not raw_text or len(raw_text.strip()) < 10:
        raise HTTPException(422, 'Could not extract readable text')

    text = clean_text(raw_text)

    # AI analysis
    result = analyze_text(text)

    return AnalyzeResponse(
        status='success',
        fileName=request.fileName,
        summary=result.get('summary', ''),
        entities=EntitiesResponse(**result.get('entities', {
            'names': [], 'dates': [], 'organizations': [], 'amounts': []
        })),
        sentiment=result.get('sentiment', 'Neutral')
    )