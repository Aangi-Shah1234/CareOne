import os
from dotenv import load_dotenv
from google import genai

# Load .env file if it exists
load_dotenv()

# Configure the Gemini API Key
api_key = os.environ.get("GEMINI_API_KEY") or os.environ.get("GOOGLE_API_KEY")

# We default to gemini-2.5-flash for fast, modern, and cheap structured output
MODEL_NAME = os.environ.get("CAREONE_MODEL", "gemini-2.5-flash")

_client = None

def get_client():
    """
    Returns a configured Google GenAI Client instance.
    """
    global _client
    if _client is None:
        # If API key is explicitly configured, use it, otherwise fall back to environment variables
        if api_key:
            _client = genai.Client(api_key=api_key)
        else:
            _client = genai.Client()
    return _client

def is_configured():
    """
    Check if the Gemini API is configured either in config or environment.
    """
    return api_key is not None or os.environ.get("GEMINI_API_KEY") is not None

def reconfigure_api(new_key):
    global api_key, _client
    api_key = new_key
    _client = None
    if api_key:
        from google import genai
        _client = genai.Client(api_key=api_key)

