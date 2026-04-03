import base64
import requests
import json

# ── CONFIG ──────────────────────────────
API_URL = "http://localhost:8000/api/document-analyze"
API_KEY = "a15fc642-3b35-4090-890e-0a564ecd4fa4"

def test_file(filepath, file_type):
    print(f"\n Testing: {filepath}")
    
    # Read and encode file to base64
    with open(filepath, "rb") as f:
        file_bytes = f.read()
    file_base64 = base64.b64encode(file_bytes).decode("utf-8")
    
    # Build request
    payload = {
        "fileName": filepath.split("\\")[-1],
        "fileType": file_type,
        "fileBase64": file_base64
    }
    headers = {
        "Content-Type": "application/json",
        "x-api-key": API_KEY
    }
    
    # Send request
    response = requests.post(API_URL, json=payload, headers=headers)
    
    # Print result
    print(f"Status Code: {response.status_code}")
    print(json.dumps(response.json(), indent=2))
    print("-" * 50)

# ── TEST YOUR FILES HERE ─────────────────
# Change these paths to your actual sample files

test_file(r"D:\doc-analyzer\sample1-Technology Industry Analysis.pdf", "pdf")
test_file(r"D:\doc-analyzer\sample2-Cybersecurity Incident Report.docx", "docx")
test_file(r"D:\doc-analyzer\sample3.jpg", "image")