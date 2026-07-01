import os
import json
import datetime
from cryptography.fernet import Fernet
from src.db import get_db, using_fallback

# Path for persistent local encryption key
DATA_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "data")
KEY_PATH = os.path.join(DATA_DIR, ".encryption_key")
AUDIT_LOG_PATH = os.path.join(DATA_DIR, "security_audit.json")

# Ensure key exists and load it
def _get_or_create_key():
    os.makedirs(DATA_DIR, exist_ok=True)
    env_key = os.environ.get("CAREONE_ENCRYPTION_KEY")
    if env_key:
        try:
            # Validate it's a valid Fernet key
            Fernet(env_key.encode())
            return env_key.encode()
        except Exception:
            pass
            
    if os.path.exists(KEY_PATH):
        with open(KEY_PATH, "rb") as f:
            return f.read().strip()
            
    # Generate new key
    key = Fernet.generate_key()
    with open(KEY_PATH, "wb") as f:
        f.write(key)
    return key

# Initialize Fernet cipher
_CIPHER_KEY = _get_or_create_key()
_CIPHER = Fernet(_CIPHER_KEY)

def encrypt_data(text: str) -> str:
    """Symmetrically encrypt text data to protect PHI."""
    if not text:
        return ""
    try:
        return _CIPHER.encrypt(text.encode('utf-8')).decode('utf-8')
    except Exception as e:
        print(f"[Security] Encryption failed: {e}")
        return text

def decrypt_data(cipher_text: str) -> str:
    """Decrypt cipher text back to plain text."""
    if not cipher_text:
        return ""
    try:
        # Check if it looks like a Fernet token (usually starts with gAAAA)
        if cipher_text.startswith("gAAAA"):
            return _CIPHER.decrypt(cipher_text.encode('utf-8')).decode('utf-8')
    except Exception:
        # Fallback to returning original text if decryption fails (e.g. not encrypted yet)
        pass
    return cipher_text

def sanitize_input(text: str) -> str:
    """Clean text from script tags, prompt injection keywords, and other issues."""
    if not text:
        return ""
        
    # Remove HTML script tags
    cleaned = text
    cleaned = cleaned.replace("<script>", "").replace("</script>", "")
    
    # Prompt injection mitigation phrases
    injection_phrases = [
        "ignore previous instructions",
        "ignore the instructions",
        "ignore all previous",
        "ignore the system prompt",
        "you are now a",
        "forget your instructions"
    ]
    for phrase in injection_phrases:
        if phrase in cleaned.lower():
            # Replace injection target phrases
            cleaned = cleaned.replace(phrase, "[Mitigated Injection Phrase]")
            
    return cleaned

def log_security_event(username: str, role: str, action: str, patient_id: str = None):
    """
    Log an immutable security audit event to MongoDB or local JSON fallback.
    """
    os.makedirs(DATA_DIR, exist_ok=True)
    event = {
        "timestamp": datetime.datetime.now().isoformat(),
        "username": username or "system",
        "role": role or "system",
        "action": action,
        "patient_id": patient_id or "system",
    }
    
    if not using_fallback():
        db = get_db()
        try:
            db.security_audit_log.insert_one(event)
            print(f"[Security Audit] {username} ({role}): {action} for patient {patient_id}")
            return
        except Exception as e:
            print(f"[Security] Failed to write audit event to DB: {e}. Falling back to file.")
            
    # File fallback
    try:
        records = []
        if os.path.exists(AUDIT_LOG_PATH):
            with open(AUDIT_LOG_PATH, "r") as f:
                records = json.load(f)
        records.append(event)
        with open(AUDIT_LOG_PATH, "w") as f:
            json.dump(records, f, indent=2)
    except Exception as e:
        print(f"[Security] Failed to write audit event to file: {e}")

def get_security_audit_logs(days: int = 7) -> list:
    """Retrieve security audit events."""
    cutoff = datetime.datetime.now() - datetime.timedelta(days=days)
    
    if not using_fallback():
        db = get_db()
        try:
            cursor = db.security_audit_log.find({"timestamp": {"$gte": cutoff.isoformat()}}).sort("timestamp", -1)
            logs = []
            for doc in cursor:
                doc.pop("_id", None)
                logs.append(doc)
            return logs
        except Exception as e:
            print(f"[Security] Failed to retrieve audit logs from DB: {e}. Falling back.")
            
    # File fallback
    try:
        if os.path.exists(AUDIT_LOG_PATH):
            with open(AUDIT_LOG_PATH, "r") as f:
                records = json.load(f)
            # Filter and sort
            filtered = [r for r in records if r["timestamp"] >= cutoff.isoformat()]
            return sorted(filtered, key=lambda x: x["timestamp"], reverse=True)
    except Exception as e:
        print(f"[Security] Failed to read audit log file: {e}")
    return []
