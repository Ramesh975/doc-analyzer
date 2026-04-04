# AI-Powered Document Analysis API

## Description

An intelligent REST API that extracts, analyses, and summarises content
from PDF, DOCX, and image files using AI. The system automatically
identifies key entities (names, dates, organizations, amounts) and
performs sentiment analysis on document content.

## Tech Stack

- **Framework:** FastAPI (Python 3.11)
- **PDF Extraction:** PyMuPDF (fitz)
- **DOCX Extraction:** python-docx
- **OCR:** Tesseract + Pillow
- **AI Model:** Groq API (llama-3.3-70b-versatile)
- **Deployment:** Railway

## Setup Instructions

1. Clone the repository
   git clone https://github.com/Ramesh975/doc-analyzer.git
   cd doc-analyzer

2. Install dependencies
   pip install -r requirements.txt

3. Install Tesseract OCR
   Ubuntu: apt-get install tesseract-ocr
   Mac: brew install tesseract
   Windows: https://github.com/UB-Mannheim/tesseract/wiki

4. Set environment variables
   cp .env.example .env
   Edit .env and add your keys

5. Run the application
   uvicorn src.main:app --reload --port 8000

## API Usage

### Endpoint

POST [doc-analyzer-production-5581.up.railway.app](https://doc-analyzer-production-5581.up.railway.app/api/document-analyze)

### Headers

Content-Type: application/json
x-api-key: a15fc642-3b35-4090-890e-0a564ecd4fa4

### Request Body

{
"fileName": "document.pdf",
"fileType": "pdf",
"fileBase64": "<base64 encoded file content>"
}

### Response

{
"status": "success",
"fileName": "document.pdf",
"summary": "AI generated summary...",
"entities": {
"names": ["John Smith"],
"dates": ["March 2024"],
"organizations": ["Acme Corp"],
"amounts": ["$10,000"]
},
"sentiment": "Neutral"
}

## Approach

### Text Extraction Strategy

- PDF: PyMuPDF extracts text preserving layout. Falls back to
  Tesseract OCR automatically for scanned/image-based PDFs.
- DOCX: python-docx reads all paragraphs and tables in order.
- Images: Tesseract OCR with image upscaling for better accuracy.

### AI Analysis Strategy

- Extracted text is sent to Groq API (llama-3.3-70b-versatile model)
- A structured system prompt instructs the model to return JSON with
  summary, grouped entities, and sentiment
- Response is validated with Pydantic before returning to client

### Entity Extraction

All entities are grouped by type:

- names: Real person names only
- dates: All temporal references
- organizations: Companies, institutions, agencies
- amounts: Currency, percentages, financial figures

### Sentiment Analysis

Document tone classified as Positive, Negative, or Neutral
based on overall language and context using LLM analysis.

## AI Tools Used

- Claude (Anthropic) — Used for code assistance, debugging,
  architecture planning, and prompt engineering during development
- Groq API (llama-3.3-70b-versatile) — Used at runtime for
  document summarisation, entity extraction, and sentiment analysis
- Google Gemini: Used as a pair-programming assistant for debugging deployment errors on Railway, optimizing Python regex patterns, and structuring the FastAPI routing.

## Known Limitations

- Free tier Groq API has rate limits (handled with model rotation)
- Very large files truncated to 6000 characters for AI analysis
- Scanned PDFs depend on image quality for OCR accuracy
- No persistent storage — stateless API
