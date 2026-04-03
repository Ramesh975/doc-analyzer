# API key middleware (X-API-Key header)

# auth.py
import os
from fastapi import Header, HTTPException

def verify_api_key(x_api_key: str = Header(...)):
    expected = os.getenv('API_KEY', '')
    if not expected:
        raise HTTPException(500, 'Server API key not configured')
    if x_api_key != expected:
        raise HTTPException(401, 'Invalid or missing API key')
    return x_api_key
