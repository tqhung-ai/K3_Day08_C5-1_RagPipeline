import os
import requests
from dotenv import load_dotenv

load_dotenv()

api_key = os.getenv("GEMINI_API_KEY")
if not api_key:
    print("No GEMINI_API_KEY found")
    exit()

url = f"https://generativelanguage.googleapis.com/v1beta/models?key={api_key}"
response = requests.get(url)
if response.status_code == 200:
    data = response.json()
    for model in data.get("models", []):
        if "generateContent" in model.get("supportedGenerationMethods", []):
            print(model["name"])
else:
    print("Failed:", response.status_code, response.text)
