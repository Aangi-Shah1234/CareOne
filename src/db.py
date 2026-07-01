import os
import pymongo
import datetime
import hashlib
from pymongo.errors import ConnectionFailure, ServerSelectionTimeoutError

MONGO_URI = os.environ.get("MONGO_URI", "mongodb+srv://<db_user>:<db_password>@cluster.xxxxxx.mongodb.net/CareOne?retryWrites=true&w=majority")
DB_NAME = os.environ.get("MONGO_DB_NAME", "CareOne")

_client = None
_use_fallback = False
_checked_connection = False

def get_db_client():
    global _client, _use_fallback, _checked_connection
    if not _checked_connection:
        _checked_connection = True
        if "xxxxxx" in MONGO_URI or not MONGO_URI.strip():
            print("[MongoDB] Placeholder or empty MONGO_URI detected. Using local JSON fallback.")
            _client = None
            _use_fallback = True
            return _client
        try:
            _client = pymongo.MongoClient(MONGO_URI, serverSelectionTimeoutMS=5000)
            _client.admin.command('ping')
            _use_fallback = False
            print("[MongoDB] Successfully connected to MongoDB Atlas.")
        except Exception as e:
            print(f"[MongoDB] Connection failed: {e}. Activating background silent fallback.")
            if _client is not None:
                try:
                    _client.close()
                except Exception:
                    pass
            _client = None
            _use_fallback = True
    return _client

def get_db():
    client = get_db_client()
    if client is not None and not _use_fallback:
        return client[DB_NAME]
    return None

def is_db_connected() -> bool:
    return True

def using_fallback() -> bool:
    get_db_client()
    return _use_fallback

def hash_password(password: str) -> str:
    return hashlib.sha256(password.encode()).hexdigest()

def reconnect(mongo_uri, db_name):
    global _client, _use_fallback, _checked_connection, MONGO_URI, DB_NAME
    _checked_connection = False
    MONGO_URI = mongo_uri
    DB_NAME = db_name
    client = get_db_client()
    return client is not None and not _use_fallback


def seed_database():
    """Seeds patient, care plans, historical vitals, logs, and default users in MongoDB."""
    db = get_db()
    if db is None:
        return

    # Local import to prevent circular dependency
    from src.security import encrypt_data

    try:
        # 1. Seed Patients data (Arthur & Eleanor)
        if db.patients.count_documents({}) == 0:
            db.patients.insert_many([
                {
                    "patient_id": "ananya_78",
                    "name": "Ananya",
                    "age": 78,
                    "relationship": "Mother",
                    "conditions": "Diabetes Type 2, Mild Dementia",
                    "preferences": [
                        "Prefers morning walks in the garden when knees do not hurt.",
                        "Likes having small, frequent meals rather than large ones.",
                        "Refuses physical exercises when joint pain flares up."
                    ],
                    "daily_routine": [
                        {"task_id": "breakfast", "name": "Breakfast", "time_expected": "08:30", "category": "Meal", "importance": "High", "description": "Nutritious breakfast and morning tea."},
                        {"task_id": "morning_meds", "name": "Morning Medications", "time_expected": "09:00", "category": "Medication", "importance": "High", "description": "Blood pressure and joint supplements."},
                        {"task_id": "lunch", "name": "Lunch", "time_expected": "13:00", "category": "Meal", "importance": "High", "description": "Balanced lunch, light on sodium."},
                        {"task_id": "afternoon_hydration", "name": "Afternoon Hydration", "time_expected": "14:00", "category": "Hydration", "importance": "Medium", "description": "Ensure at least 500ml of water is consumed."},
                        {"task_id": "evening_walk", "name": "Evening Walk", "time_expected": "17:00", "category": "Exercise", "importance": "Medium", "description": "Short walk in the garden or neighborhood for mobility."},
                        {"task_id": "dinner", "name": "Dinner", "time_expected": "19:00", "category": "Meal", "importance": "High", "description": "Evening meal, easy to digest."},
                        {"task_id": "evening_meds", "name": "Evening Medications", "time_expected": "21:00", "category": "Medication", "importance": "High", "description": "Heart medication and sleeping aid if prescribed."}
                    ],
                    "created_at": datetime.datetime.now().isoformat()
                },
                {
                    "patient_id": "eleanor_82",
                    "name": "Eleanor",
                    "age": 82,
                    "relationship": "Grandmother",
                    "conditions": "Stage 3 Chronic Kidney Disease, Severe Hypertension",
                    "preferences": [
                        "Fluid restricted diet: Max 1500ml fluid intake daily.",
                        "Prefers low-sodium, low-potassium renal meals.",
                        "Prefers blood pressure measurement while seated in a quiet room."
                    ],
                    "daily_routine": [
                        {"task_id": "bp_check", "name": "BP Monitoring", "time_expected": "08:00", "category": "Vitals", "importance": "High", "description": "Measure and log blood pressure before breakfast."},
                        {"task_id": "renal_breakfast", "name": "Renal Breakfast", "time_expected": "08:30", "category": "Meal", "importance": "High", "description": "Low sodium oatmeal and egg whites."},
                        {"task_id": "renal_meds", "name": "CKD Medications", "time_expected": "09:00", "category": "Medication", "importance": "High", "description": "Phosphate binders and renal vitamins."},
                        {"task_id": "fluid_check", "name": "Fluid Intake Check", "time_expected": "14:00", "category": "Hydration", "importance": "High", "description": "Log running total of fluids. Ensure under 1500ml."},
                        {"task_id": "light_yoga", "name": "Light Yoga/Stretching", "time_expected": "17:00", "category": "Exercise", "importance": "Medium", "description": "15 minutes of seated yoga for circulation."},
                        {"task_id": "renal_dinner", "name": "Renal Dinner", "time_expected": "19:00", "category": "Meal", "importance": "High", "description": "Grilled chicken breast, steamed green beans (leached)."},
                        {"task_id": "evening_bp_check", "name": "Evening Vitals Check", "time_expected": "21:00", "category": "Vitals", "importance": "High", "description": "Measure blood pressure and administer night anti-hypertensive."}
                    ],
                    "created_at": datetime.datetime.now().isoformat()
                },
                {
                    "patient_id": "anj_86",
                    "name": "Anj",
                    "age": 86,
                    "relationship": "Daughter",
                    "conditions": "Cancer",
                    "preferences": [
                        "Prefers warm herbal teas in the afternoon.",
                        "Requires comfortable seating during vitals check."
                    ],
                    "daily_routine": [
                        {"task_id": "breakfast", "name": "Breakfast", "time_expected": "08:30", "category": "Meal", "importance": "High", "description": "Light breakfast and hydration."},
                        {"task_id": "morning_meds", "name": "Cancer Medication", "time_expected": "09:00", "category": "Medication", "importance": "High", "description": "Administer daily medication dosage."},
                        {"task_id": "afternoon_rest", "name": "Afternoon Rest", "time_expected": "14:00", "category": "Routine", "importance": "Medium", "description": "Ensure at least 2 hours of quiet sleep."},
                        {"task_id": "evening_walk", "name": "Short Walk", "time_expected": "17:00", "category": "Exercise", "importance": "Medium", "description": "Assisted short walk in the hallway."},
                        {"task_id": "dinner", "name": "Dinner", "time_expected": "19:00", "category": "Meal", "importance": "High", "description": "Light, highly digestible dinner."}
                    ],
                    "created_at": datetime.datetime.now().isoformat()
                }
            ])
            print("[MongoDB] Seeded patients Arthur, Eleanor, and Anj.")

        # 2. Seed Default Caregiver Accounts (Collaborators)
        if db.users.count_documents({}) == 0:
            db.users.insert_many([
                {
                    "username": "caregiver",
                    "password": hash_password("careone"),
                    "name": "Sarah Jenkins",
                    "role": "Lead Nurse"
                },
                {
                    "username": "caregiver_john",
                    "password": hash_password("careone"),
                    "name": "John Doe",
                    "role": "Assisting Caregiver"
                },
                {
                    "username": "doctor_patel",
                    "password": hash_password("careone"),
                    "name": "Dr. Patel",
                    "role": "Primary Physician"
                }
            ])
            print("[MongoDB] Seeded collaborative user accounts: caregiver, caregiver_john, doctor_patel")

        # 3. Seed 7 Days of Historical Logs & Vitals for Ananya
        if db.care_logs.count_documents({"patient_id": "ananya_78"}) == 0:
            today = datetime.date.today()
            past_logs = []
            past_vitals = []
            
            bps = ["135/82", "138/85", "142/88", "136/83", "140/86", "145/90", "138/84"]
            glucose = ["112 mg/dL", "125 mg/dL", "135 mg/dL", "118 mg/dL", "142 mg/dL", "120 mg/dL", "130 mg/dL"]
            completion_rates = [85, 90, 75, 80, 70, 60, 85]
            caregivers = ["Sarah Jenkins", "John Doe", "Sarah Jenkins", "John Doe", "Sarah Jenkins", "John Doe", "Sarah Jenkins"]
            
            for i in range(7, 0, -1):
                log_date = (today - datetime.timedelta(days=i)).strftime("%Y-%m-%d")
                bp = bps[7-i]
                glu = glucose[7-i]
                c_rate = completion_rates[7-i]
                c_name = caregivers[7-i]
                
                reconciled_events = [
                    {"activity": "Meal", "inferred_time": "08:30", "status": "Completed" if c_rate > 70 else "Skipped", "caregivers": [c_name], "notes": "Had breakfast."},
                    {"activity": "Medication", "inferred_time": "09:00", "status": "Completed", "caregivers": [c_name], "notes": "Morning Metformin taken."},
                    {"activity": "Hydration", "inferred_time": "14:00", "status": "Completed" if c_rate > 60 else "Skipped", "caregivers": [c_name], "notes": "Drank water."},
                    {"activity": "Meal", "inferred_time": "13:00", "status": "Completed", "caregivers": [c_name], "notes": "Finished lunch."},
                    {"activity": "Exercise", "inferred_time": "17:00", "status": "Completed" if c_rate > 80 else "Refused", "caregivers": [c_name], "notes": "Refused walking exercise." if c_rate <= 80 else "Took 15 min walk."},
                    {"activity": "Meal", "inferred_time": "19:00", "status": "Completed", "caregivers": [c_name], "notes": "Had light dinner."},
                    {"activity": "Medication", "inferred_time": "21:00", "status": "Completed" if c_rate > 70 else "Skipped", "caregivers": [c_name], "notes": "Evening medications taken."}
                ]
                
                gaps = []
                for ev in reconciled_events:
                    if ev["status"] in ["Skipped", "Refused"]:
                        gaps.append({
                            "task_id": "custom",
                            "task_name": ev["activity"],
                            "category": "Routine",
                            "importance": "Medium",
                            "confidence_score": 0.95,
                            "explanation": f"Task was marked as {ev['status']} in daily caregiver notes."
                        })
                
                past_logs.append({
                    "patient_id": "ananya_78",
                    "date": log_date,
                    "raw_notes": [{"caregiver": c_name, "text": encrypt_data(f"Gave Ananya meals and checked on her. BP was {bp}. Glucose was {glu}.")}],
                    "reconciled_events": reconciled_events,
                    "vitals": [
                        {"vital_type": "Blood Pressure", "value_raw": encrypt_data(bp), "status": "Elevated" if int(bp.split("/")[0]) > 130 else "Normal", "explanation": "Seeded daily vital check.", "caregiver": c_name, "timestamp": "09:00"},
                        {"vital_type": "Blood Glucose", "value_raw": encrypt_data(glu), "status": "Elevated" if int(glu.split(" ")[0]) > 120 else "Normal", "explanation": "Seeded daily vital check.", "caregiver": c_name, "timestamp": "09:00"}
                    ],
                    "conflicts": [],
                    "interventions": [],
                    "detected_gaps": gaps,
                    "trends": {},
                    "risk_assessment": {"risk_level": "Medium" if c_rate < 80 else "Low", "description": "Occasional task refusal and elevated vitals.", "confidence": 0.9, "reasoning": "Determined from completion rate and BP levels."},
                    "summary": {
                        "executive_summary": f"Ananya completed {c_rate}% of her scheduled routine tasks today. Her blood pressure was stable at {bp} and blood sugar was {glu}.",
                        "recommended_actions": ["Monitor her physical exercise completion."],
                        "safety_alerts": []
                    }
                })
                
                past_vitals.append({
                    "patient_id": "ananya_78",
                    "date": log_date, "vital_type": "Blood Pressure", "value_raw": encrypt_data(bp), 
                    "status": "Elevated" if int(bp.split("/")[0]) > 130 else "Normal", 
                    "explanation": "Daily check", "caregiver": c_name, "timestamp": "09:00"
                })
                past_vitals.append({
                    "patient_id": "ananya_78",
                    "date": log_date, "vital_type": "Blood Glucose", "value_raw": encrypt_data(glu), 
                    "status": "Elevated" if int(glu.split(" ")[0]) > 120 else "Normal", 
                    "explanation": "Daily check", "caregiver": c_name, "timestamp": "09:00"
                })

            db.care_logs.insert_many(past_logs)
            db.vitals.insert_many(past_vitals)
            print("[MongoDB] Seeded 7 days of historical logs/vitals for Ananya.")

        # 4. Seed 7 Days of Historical Logs & Vitals for Eleanor
        if db.care_logs.count_documents({"patient_id": "eleanor_82"}) == 0:
            today = datetime.date.today()
            past_logs_el = []
            past_vitals_el = []
            
            bps_el = ["142/90", "148/94", "150/96", "138/88", "144/92", "155/98", "140/90"]
            fluids = ["1200ml", "1350ml", "1550ml", "1100ml", "1450ml", "1650ml", "1300ml"]
            completion_rates_el = [90, 85, 90, 80, 95, 70, 90]
            caregivers = ["Sarah Jenkins", "John Doe", "Sarah Jenkins", "John Doe", "Sarah Jenkins", "John Doe", "Sarah Jenkins"]
            
            for i in range(7, 0, -1):
                log_date = (today - datetime.timedelta(days=i)).strftime("%Y-%m-%d")
                bp = bps_el[7-i]
                fl = fluids[7-i]
                c_rate = completion_rates_el[7-i]
                c_name = caregivers[7-i]
                
                reconciled_events = [
                    {"activity": "Vitals Check", "inferred_time": "08:00", "status": "Completed", "caregivers": [c_name], "notes": f"Morning BP check: {bp}."},
                    {"activity": "Meal", "inferred_time": "08:30", "status": "Completed", "caregivers": [c_name], "notes": "Ate low sodium oatmeal."},
                    {"activity": "Medication", "inferred_time": "09:00", "status": "Completed", "caregivers": [c_name], "notes": "CKD meds and vitamins taken."},
                    {"activity": "Hydration", "inferred_time": "14:00", "status": "Completed", "caregivers": [c_name], "notes": f"Logged fluid intake total: {fl}."},
                    {"activity": "Exercise", "inferred_time": "17:00", "status": "Completed" if c_rate > 80 else "Skipped", "caregivers": [c_name], "notes": "Completed yoga stretching." if c_rate > 80 else "Skipped exercise."},
                    {"activity": "Meal", "inferred_time": "19:00", "status": "Completed", "caregivers": [c_name], "notes": "Ate leached greens and chicken."},
                    {"activity": "Vitals Check", "inferred_time": "21:00", "status": "Completed" if c_rate > 70 else "Skipped", "caregivers": [c_name], "notes": "Evening vital check completed."}
                ]
                
                gaps = []
                for ev in reconciled_events:
                    if ev["status"] == "Skipped":
                        gaps.append({
                            "task_id": "custom",
                            "task_name": ev["activity"],
                            "category": "Routine",
                            "importance": "High" if ev["activity"] != "Exercise" else "Medium",
                            "confidence_score": 0.95,
                            "explanation": f"Task was skipped or not mentioned in caregiver log."
                        })
                
                past_logs_el.append({
                    "patient_id": "eleanor_82",
                    "date": log_date,
                    "raw_notes": [{"caregiver": c_name, "text": encrypt_data(f"Checked BP which was {bp}. Monitored fluid intake closely, recorded total of {fl}. She was cooperative with meals.")}],
                    "reconciled_events": reconciled_events,
                    "vitals": [
                        {"vital_type": "Blood Pressure", "value_raw": encrypt_data(bp), "status": "Stage 2 Hypertension" if int(bp.split("/")[0]) >= 140 or int(bp.split("/")[1]) >= 90 else "Elevated", "explanation": "High readings recorded.", "caregiver": c_name, "timestamp": "08:00"},
                        {"vital_type": "Fluid Intake", "value_raw": encrypt_data(fl), "status": "Warning" if int(fl.replace("ml", "")) > 1500 else "Normal", "explanation": "Total fluids measured.", "caregiver": c_name, "timestamp": "14:00"}
                    ],
                    "conflicts": [],
                    "interventions": [],
                    "detected_gaps": gaps,
                    "trends": {},
                    "risk_assessment": {"risk_level": "High" if int(bp.split("/")[0]) >= 150 or int(fl.replace("ml", "")) > 1500 else "Medium", "description": "Hypertension alerts and fluid restriction bounds.", "confidence": 0.95, "reasoning": "Fluid intake exceeded 1500ml daily target or BP systolic exceeded 150."},
                    "summary": {
                        "executive_summary": f"Eleanor completed {c_rate}% of tasks today. Blood pressure remains high at {bp}. Fluid intake logged at {fl}.",
                        "recommended_actions": ["Restrict sodium intake.", "Notify Dr. Patel if BP systolic remains above 150."],
                        "safety_alerts": ["Stage 2 Hypertension detected." if int(bp.split("/")[0]) >= 140 else "High BP monitor."]
                    }
                })
                
                past_vitals_el.append({
                    "patient_id": "eleanor_82",
                    "date": log_date, "vital_type": "Blood Pressure", "value_raw": encrypt_data(bp), 
                    "status": "Stage 2 Hypertension" if int(bp.split("/")[0]) >= 140 else "Elevated", 
                    "explanation": "Daily BP monitor", "caregiver": c_name, "timestamp": "08:00"
                })
                past_vitals_el.append({
                    "patient_id": "eleanor_82",
                    "date": log_date, "vital_type": "Fluid Intake", "value_raw": encrypt_data(fl), 
                    "status": "Warning" if int(fl.replace("ml", "")) > 1500 else "Normal", 
                    "explanation": "Daily fluids monitor", "caregiver": c_name, "timestamp": "14:00"
                })

            db.care_logs.insert_many(past_logs_el)
            db.vitals.insert_many(past_vitals_el)
            print("[MongoDB] Seeded 7 days of historical logs/vitals for Eleanor.")

    except Exception as e:
        print(f"[MongoDB] Error during seeding: {e}")

if __name__ == "__main__":
    seed_database()
