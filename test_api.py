import base64
import requests
import json
import os

# --- CONFIGURE THESE THREE VARIABLES ---
API_URL = "https://YOUR-RAILWAY-APP.up.railway.app/api/document-analyze" 
API_KEY = "YOUR_ACTUAL_API_KEY"
FILE_TO_TEST = "sample_invoice.pdf" # Put a real PDF, DOCX, or Image in the same folder
# ---------------------------------------

def test_live_api():
    if not os.path.exists(FILE_TO_TEST):
        print(f"Error: Could not find {FILE_TO_TEST}")
        return

    # 1. Convert the file to Base64
    with open(FILE_TO_TEST, "rb") as f:
        encoded_string = base64.b64encode(f.read()).decode("utf-8")
    
    # 2. Determine file type for the payload
    ext = FILE_TO_TEST.split('.')[-1].lower()
    file_type = "image" if ext in ['png', 'jpg', 'jpeg'] else ext

    # 3. Build the exact JSON payload the judges will use
    payload = {
        "fileName": FILE_TO_TEST,
        "fileType": file_type,
        "fileBase64": encoded_string
    }

    headers = {
        "Content-Type": "application/json",
        "x-api-key": API_KEY
    }

    print(f"Sending {FILE_TO_TEST} to {API_URL}...")
    
    # 4. Send the request
    response = requests.post(API_URL, json=payload, headers=headers)
    
    # 5. Print the results
    print(f"\nStatus Code: {response.status_code}")
    try:
        print("Response JSON:")
        print(json.dumps(response.json(), indent=2))
    except Exception:
        print("Error: Did not return valid JSON. Raw response:")
        print(response.text)

if __name__ == "__main__":
    test_live_api()