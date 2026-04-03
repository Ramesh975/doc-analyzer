# Text extraction: PDF, DOCX, image→OCR

# extractor.py
import io, fitz, docx, pytesseract
from PIL import Image

def extract_text(file_bytes: bytes, file_type: str) -> str:
    if file_type == 'pdf':
        return _extract_pdf(file_bytes)
    elif file_type == 'docx':
        return _extract_docx(file_bytes)
    elif file_type == 'image':
        return _extract_image(file_bytes)
    raise ValueError(f'Unknown type: {file_type}')

def _extract_pdf(data: bytes) -> str:
    doc = fitz.open(stream=data, filetype='pdf')
    pages = []
    for page in doc:
        text = page.get_text('text')
        if text.strip():           # text-based PDF
            pages.append(text)
        else:                      # scanned PDF → OCR fallback
            pix = page.get_pixmap(dpi=200)
            img = Image.frombytes('RGB', [pix.width, pix.height], pix.samples)
            pages.append(pytesseract.image_to_string(img))
    return '\n'.join(pages)

def _extract_docx(data: bytes) -> str:
    d = docx.Document(io.BytesIO(data))
    parts = []
    for para in d.paragraphs:
        if para.text.strip():
            parts.append(para.text)
    for table in d.tables:
        for row in table.rows:
            parts.append(' | '.join(c.text for c in row.cells))
    return '\n'.join(parts)

def _extract_image(data: bytes) -> str:
    img = Image.open(io.BytesIO(data))
    # Upscale small images for better OCR accuracy
    if img.width < 1000:
        img = img.resize((img.width * 2, img.height * 2), Image.LANCZOS)
    return pytesseract.image_to_string(img, config='--psm 3')
