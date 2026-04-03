# Setup guide + API docs + sample curl

# AI Document Analysis API

Extracts structured information from PDF, DOCX, and image files using AI.

## Base URL

https://your-app.up.railway.app

## Authentication

All requests require header:
X-API-Key: your-api-key

## Endpoints

### POST /analyze

Accepts multipart/form-data

- file: PDF, DOCX, or image
- type (optional): pdf | docx | image

### GET /health

Returns {"status": "ok"}

## Sample Curl

curl -X POST https://your-app.up.railway.app/analyze \
 -H "X-API-Key: your-api-key" \
 -F "file=@document.pdf"
