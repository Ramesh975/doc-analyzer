# Helpers: file type detection, text cleanup

# utils.py
import re

def detect_file_type(filename: str, content_type: str = '') -> str:
    name = (filename or '').lower()
    mime = (content_type or '').lower()
    if name.endswith('.pdf') or 'pdf' in mime:
        return 'pdf'
    if name.endswith('.docx') or 'wordprocessing' in mime:
        return 'docx'
    if any(name.endswith(e) for e in ('.png','.jpg','.jpeg','.tiff','.bmp','.webp')):
        return 'image'
    if 'image' in mime:
        return 'image'
    return 'unknown'

def clean_text(text: str) -> str:
    # Remove excessive whitespace / null bytes
    text = text.replace('\x00', '')
    text = re.sub(r'\n{3,}', '\n\n', text)
    text = re.sub(r' {2,}', ' ', text)
    return text.strip()
