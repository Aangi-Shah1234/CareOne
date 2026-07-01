import os
from dotenv import load_dotenv
import google.generativeai as genai

load_dotenv()

api_key = os.environ.get("GEMINI_API_KEY")
genai.configure(api_key=api_key)

test_models = [
    "gemini-2.0-flash",
    "gemini-2.5-flash",
    "gemini-3.5-flash",
    "gemini-flash-latest"
]

print("Starting generation diagnostics...")
for model_name in test_models:
    print(f"Testing model: {model_name}...")
    try:
        model = genai.GenerativeModel(model_name)
        response = model.generate_content("Hello. Reply with one word.")
        print(f"SUCCESS! Response: {response.text.strip()}")
    except Exception as e:
        print(f"FAILED for {model_name}: {str(e)[:150]}...")
