import os
import json
import datetime
from zoneinfo import ZoneInfo
from src.db import get_db, using_fallback, is_db_connected
from src.security import encrypt_data, decrypt_data, log_security_event

DATA_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "data")

DEFAULT_PATIENTS = {
    "arthur_78": {
        "patient_id": "arthur_78",
        "name": "Arthur",
        "age": 78,
        "relationship": "Dad",
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
        ]
    },
    "eleanor_82": {
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
        ]
    },
    "anj_86": {
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
        ]
    }
}

def get_care_plan_path(patient_id):
    return os.path.join(DATA_DIR, f"care_plan_{patient_id}.json")

def get_care_history_path(patient_id):
    return os.path.join(DATA_DIR, f"care_history_{patient_id}.json")

def get_agent_events_path(patient_id):
    return os.path.join(DATA_DIR, f"agent_events_{patient_id}.json")

def ensure_fallback_files(patient_id):
    """Seed local fallback files for the selected patient if they do not exist."""
    os.makedirs(DATA_DIR, exist_ok=True)
    
    # Only seed default files for demo patients
    if patient_id not in ["arthur_78", "eleanor_82", "anj_86"]:
        return
        
    plan_path = get_care_plan_path(patient_id)
    history_path = get_care_history_path(patient_id)
    events_path = get_agent_events_path(patient_id)
    
    # 1. Plan Seeding
    if not os.path.exists(plan_path):
        p_data = DEFAULT_PATIENTS.get(patient_id, DEFAULT_PATIENTS["arthur_78"])
        with open(plan_path, "w") as f:
            json.dump({
                "patient_name": p_data["name"],
                "age": p_data["age"],
                "conditions": p_data["conditions"],
                "preferences": p_data["preferences"],
                "daily_routine": p_data["daily_routine"]
            }, f, indent=2)
            
    # 2. History Seeding (7 days of encrypted data)
    if not os.path.exists(history_path):
        today = datetime.datetime.now(ZoneInfo("Asia/Kolkata")).date()
        history_records = []
        
        if patient_id == "arthur_78":
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
                
                reconciled = [
                    {"activity": "Meal", "inferred_time": "08:30", "status": "Completed" if c_rate > 70 else "Skipped", "caregivers": [c_name], "notes": "Had breakfast."},
                    {"activity": "Medication", "inferred_time": "09:00", "status": "Completed", "caregivers": [c_name], "notes": "Morning Metformin taken."},
                    {"activity": "Hydration", "inferred_time": "14:00", "status": "Completed" if c_rate > 60 else "Skipped", "caregivers": [c_name], "notes": "Drank water."},
                    {"activity": "Meal", "inferred_time": "13:00", "status": "Completed", "caregivers": [c_name], "notes": "Finished lunch."},
                    {"activity": "Exercise", "inferred_time": "17:00", "status": "Completed" if c_rate > 80 else "Refused", "caregivers": [c_name], "notes": "Refused walking exercise." if c_rate <= 80 else "Took 15 min walk."},
                    {"activity": "Meal", "inferred_time": "19:00", "status": "Completed", "caregivers": [c_name], "notes": "Had light dinner."},
                    {"activity": "Medication", "inferred_time": "21:00", "status": "Completed" if c_rate > 70 else "Skipped", "caregivers": [c_name], "notes": "Evening medications taken."}
                ]
                
                gaps = [{"task_id": "custom", "task_name": ev["activity"], "category": "Routine", "importance": "Medium", "confidence_score": 0.95, "explanation": f"Task was {ev['status']}."} for ev in reconciled if ev["status"] in ["Skipped", "Refused"]]
                
                history_records.append({
                    "patient_id": patient_id,
                    "date": log_date,
                    "raw_notes": [{"caregiver": c_name, "text": encrypt_data(f"Gave Dad meals. BP was {bp}. Glucose was {glu}.")}],
                    "reconciled_events": reconciled,
                    "vitals": [
                        {"vital_type": "Blood Pressure", "value_raw": encrypt_data(bp), "status": "Elevated" if int(bp.split("/")[0]) > 130 else "Normal", "explanation": "Daily vital check.", "caregiver": c_name, "timestamp": "09:00"},
                        {"vital_type": "Blood Glucose", "value_raw": encrypt_data(glu), "status": "Elevated" if int(glu.split(" ")[0]) > 120 else "Normal", "explanation": "Daily vital check.", "caregiver": c_name, "timestamp": "09:00"}
                    ],
                    "conflicts": [],
                    "interventions": [],
                    "detected_gaps": gaps,
                    "trends": {},
                    "risk_assessment": {"risk_level": "Medium" if c_rate < 80 else "Low", "description": "Occasional task refusal and elevated vitals.", "confidence": 0.9, "reasoning": "Determined from completion rate and BP levels."},
                    "summary": {
                        "executive_summary": f"Arthur completed {c_rate}% of tasks today. BP was stable at {bp} and sugar was {glu}.",
                        "recommended_actions": ["Monitor his physical exercise completion."],
                        "safety_alerts": []
                    }
                })
        else: # eleanor_82
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
                
                reconciled = [
                    {"activity": "Vitals Check", "inferred_time": "08:00", "status": "Completed", "caregivers": [c_name], "notes": f"Morning BP check: {bp}."},
                    {"activity": "Meal", "inferred_time": "08:30", "status": "Completed", "caregivers": [c_name], "notes": "Ate low sodium oatmeal."},
                    {"activity": "Medication", "inferred_time": "09:00", "status": "Completed", "caregivers": [c_name], "notes": "CKD meds and vitamins taken."},
                    {"activity": "Hydration", "inferred_time": "14:00", "status": "Completed", "caregivers": [c_name], "notes": f"Logged fluid intake total: {fl}."},
                    {"activity": "Exercise", "inferred_time": "17:00", "status": "Completed" if c_rate > 80 else "Skipped", "caregivers": [c_name], "notes": "Completed yoga stretching." if c_rate > 80 else "Skipped exercise."},
                    {"activity": "Meal", "inferred_time": "19:00", "status": "Completed", "caregivers": [c_name], "notes": "Ate leached greens and chicken."},
                    {"activity": "Vitals Check", "inferred_time": "21:00", "status": "Completed" if c_rate > 70 else "Skipped", "caregivers": [c_name], "notes": "Evening vital check completed."}
                ]
                
                gaps = [{"task_id": "custom", "task_name": ev["activity"], "category": "Routine", "importance": "High" if ev["activity"] != "Exercise" else "Medium", "confidence_score": 0.95, "explanation": f"Task was skipped."} for ev in reconciled if ev["status"] == "Skipped"]
                
                history_records.append({
                    "patient_id": patient_id,
                    "date": log_date,
                    "raw_notes": [{"caregiver": c_name, "text": encrypt_data(f"Checked BP which was {bp}. Monitored fluid intake closely, recorded total of {fl}.")}],
                    "reconciled_events": reconciled,
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
                
        with open(history_path, "w") as f:
            json.dump({"history": history_records}, f, indent=2)
            
    # 3. Events Seeding
    if not os.path.exists(events_path):
        with open(events_path, "w") as f:
            json.dump({"events": []}, f, indent=2)

def get_patient_profiles(username: str | None = None) -> list:
    """Retrieve patient profile headers for selection, filtered by username if provided."""
    is_demo_user = (not username or username.strip().lower() in ["caregiver", "sarah", "nurse", "admin"])

    if not using_fallback():
        db = get_db()
        try:
            cursor = db.patients.find({})
            patients = []
            for doc in cursor:
                doc.pop("_id", None)
                created_by = doc.get("created_by")
                if is_demo_user:
                    patients.append(doc)
                else:
                    if created_by == username:
                        patients.append(doc)
            return sorted(patients, key=lambda x: x.get("name", ""))
        except Exception as e:
            print(f"[MongoDB] Error loading patient list: {e}. Falling back.")
            
    # Local fallback patient scanning
    local_patients = []
    if is_demo_user:
        ensure_fallback_files("arthur_78")
        ensure_fallback_files("eleanor_82")
        ensure_fallback_files("anj_86")
    
    try:
        import glob
        files = glob.glob(os.path.join(DATA_DIR, "care_plan_*.json"))
        for f in files:
            try:
                with open(f, "r") as pf:
                    pdata = json.load(pf)
                    p_id = os.path.basename(f).replace("care_plan_", "").replace(".json", "")
                    created_by = pdata.get("created_by")
                    if is_demo_user:
                        local_patients.append({
                            "patient_id": p_id,
                            "name": pdata.get("patient_name", "Unknown"),
                            "age": pdata.get("age", ""),
                            "relationship": pdata.get("relationship", "Family"),
                            "conditions": pdata.get("conditions", "")
                        })
                    else:
                        if created_by == username:
                            local_patients.append({
                                "patient_id": p_id,
                                "name": pdata.get("patient_name", "Unknown"),
                                "age": pdata.get("age", ""),
                                "relationship": pdata.get("relationship", "Family"),
                                "conditions": pdata.get("conditions", "")
                            })
            except Exception:
                pass
    except Exception:
        pass
        
    return sorted(local_patients, key=lambda x: x.get("name", ""))
        
def delete_patient_profile(patient_id: str) -> bool:
    """Delete a patient profile and their associated data (Mongo or fallback files)."""
    # 1. MongoDB deletion
    from src.db import get_db
    db_conn = get_db()
    if db_conn is not None:
        try:
            db_conn.patients.delete_one({"patient_id": patient_id})
            db_conn.care_logs.delete_many({"patient_id": patient_id})
            db_conn.vitals.delete_many({"patient_id": patient_id})
            db_conn.agent_events.delete_many({"patient_id": patient_id})
            db_conn.pipeline_execution_logs.delete_many({"patient_id": patient_id})
        except Exception as e:
            print(f"[MongoDB] Error deleting patient from DB: {e}")

    # 2. Local files deletion
    try:
        patterns = [
            f"care_plan_{patient_id}.json",
            f"care_logs_{patient_id}.json",
            f"vitals_{patient_id}.json",
            f"pipeline_execution_logs_{patient_id}.json",
            f"agent_events_{patient_id}.json"
        ]
        for pattern in patterns:
            path = os.path.join(DATA_DIR, pattern)
            if os.path.exists(path):
                os.remove(path)
    except Exception as e:
        print(f"[Fallback] Error deleting patient files: {e}")
        
    return True
        
    return [
        {
            "patient_id": "arthur_78",
            "name": "Arthur",
            "age": 78,
            "relationship": "Dad",
            "conditions": "Diabetes Type 2, Mild Dementia"
        },
        {
            "patient_id": "eleanor_82",
            "name": "Eleanor",
            "age": 82,
            "relationship": "Grandmother",
            "conditions": "Stage 3 Chronic Kidney Disease, Severe Hypertension"
        }
    ]


def load_care_plan(patient_id: str):
    """Load Care Plan details from MongoDB or JSON fallback for a specific patient."""
    log_security_event("system", "system", f"Retrieved care plan for patient {patient_id}", patient_id)
    if not using_fallback():
        db = get_db()
        try:
            patient = db.patients.find_one({"patient_id": patient_id})
            if patient:
                patient.pop("_id", None)
                return {
                    "patient_id": patient.get("patient_id", patient_id),
                    "patient_name": patient.get("name"),
                    "age": patient.get("age"),
                    "relationship": patient.get("relationship", "Family"),
                    "conditions": patient.get("conditions", ""),
                    "preferences": patient.get("preferences", []),
                    "daily_routine": patient.get("daily_routine", []),
                    "created_by": patient.get("created_by")
                }
        except Exception as e:
            print(f"[MongoDB] Error loading care plan: {e}. Falling back.")

    ensure_fallback_files(patient_id)
    try:
        with open(get_care_plan_path(patient_id), "r") as f:
            return json.load(f)
    except Exception as e:
        print(f"Error loading local plan: {e}")
        p_data = DEFAULT_PATIENTS.get(patient_id, DEFAULT_PATIENTS["arthur_78"])
        return {
            "patient_name": p_data["name"],
            "age": p_data["age"],
            "conditions": p_data["conditions"],
            "preferences": p_data["preferences"],
            "daily_routine": p_data["daily_routine"]
        }

def save_care_plan(patient_id: str, plan: dict):
    """Save Care Plan details to MongoDB or JSON fallback."""
    log_security_event("system", "system", f"Updated care plan for patient {patient_id}", patient_id)
    if not using_fallback():
        db = get_db()
        try:
            db.patients.update_one(
                {"patient_id": patient_id},
                {"$set": {
                    "patient_id": patient_id,
                    "name": plan.get("patient_name"),
                    "age": plan.get("age"),
                    "relationship": plan.get("relationship", "Family"),
                    "conditions": plan.get("conditions", ""),
                    "preferences": plan.get("preferences", []),
                    "daily_routine": plan.get("daily_routine", []),
                    "created_by": plan.get("created_by")
                }},
                upsert=True
            )
            return
        except Exception as e:
            print(f"[MongoDB] Error saving care plan: {e}. Falling back.")
            
    ensure_fallback_files(patient_id)
    with open(get_care_plan_path(patient_id), "w") as f:
        json.dump(plan, f, indent=2)

def decrypt_record(rec):
    """Deep copy and decrypt encrypted fields in a record for UI display."""
    if not rec:
        return rec
    import copy
    dec_rec = copy.deepcopy(rec)
    
    # Decrypt raw notes
    notes = dec_rec.get("raw_notes", [])
    for n in notes:
        n["text"] = decrypt_data(n.get("text", ""))
        
    # Decrypt vitals
    vits = dec_rec.get("vitals", [])
    for v in vits:
        v["value_raw"] = decrypt_data(v.get("value_raw", ""))
        
    return dec_rec

def get_day_record(patient_id: str, date_str: str):
    """Retrieve history record for a specific date from MongoDB or JSON fallback."""
    log_security_event("system", "system", f"Retrieved daily log record for {date_str}", patient_id)
    if not using_fallback():
        db = get_db()
        try:
            record = db.care_logs.find_one({"patient_id": patient_id, "date": date_str})
            if record:
                record.pop("_id", None)
                return decrypt_record(record)
            return None
        except Exception as e:
            print(f"[MongoDB] Error loading day record: {e}. Falling back.")

    ensure_fallback_files(patient_id)
    try:
        with open(get_care_history_path(patient_id), "r") as f:
            history = json.load(f)
            for rec in history.get("history", []):
                if rec.get("date") == date_str and rec.get("patient_id") == patient_id:
                    return decrypt_record(rec)
    except Exception as e:
        print(f"Error loading local day record: {e}")
    return None

def save_day_record(patient_id: str, date_str: str, record_data: dict):
    """Save daily care record in MongoDB or JSON fallback, encrypting PHI."""
    log_security_event("system", "system", f"Saved daily log record for {date_str}", patient_id)
    
    import copy
    enc_record = copy.deepcopy(record_data)
    
    # Encrypt raw notes
    if enc_record:
        notes = enc_record.get("raw_notes", [])
        for n in notes:
            n["text"] = encrypt_data(n.get("text", ""))
        # Encrypt vitals
        vits = enc_record.get("vitals", [])
        for v in vits:
            v["value_raw"] = encrypt_data(v.get("value_raw", ""))
        # Set patient id
        enc_record["patient_id"] = patient_id

    if not using_fallback():
        db = get_db()
        try:
            if enc_record is None:
                db.care_logs.delete_one({"patient_id": patient_id, "date": date_str})
            else:
                db.care_logs.replace_one({"patient_id": patient_id, "date": date_str}, enc_record, upsert=True)
            return
        except Exception as e:
            print(f"[MongoDB] Error saving day record: {e}. Falling back.")

    ensure_fallback_files(patient_id)
    try:
        with open(get_care_history_path(patient_id), "r") as f:
            history = json.load(f)
        records = history.get("history", [])
        
        updated = False
        for i, rec in enumerate(records):
            if rec.get("date") == date_str and rec.get("patient_id") == patient_id:
                if enc_record is None:
                    records.pop(i)
                else:
                    records[i] = enc_record
                updated = True
                break
                
        if not updated and enc_record is not None:
            records.append(enc_record)
            
        history["history"] = records
        with open(get_care_history_path(patient_id), "w") as f:
            json.dump(history, f, indent=2)
    except Exception as e:
        print(f"Error saving local day record: {e}")

def get_history_range(patient_id: str, end_date_str: str, days=7):
    """Retrieve historical logs for the last N days prior to end_date_str."""
    try:
        end_date = datetime.datetime.strptime(end_date_str, "%Y-%m-%d")
    except ValueError:
        end_date = datetime.datetime.now(ZoneInfo("Asia/Kolkata"))
        
    dates = [(end_date - datetime.timedelta(days=i)).strftime("%Y-%m-%d") for i in range(days)]
    
    records = []
    if not using_fallback():
        db = get_db()
        try:
            cursor = db.care_logs.find({"patient_id": patient_id, "date": {"$in": dates}})
            for doc in cursor:
                doc.pop("_id", None)
                records.append(decrypt_record(doc))
            return records
        except Exception as e:
            print(f"[MongoDB] Error loading historical range: {e}. Falling back.")
            
    ensure_fallback_files(patient_id)
    try:
        with open(get_care_history_path(patient_id), "r") as f:
            history = json.load(f)
            for rec in history.get("history", []):
                if rec.get("date") in dates and rec.get("patient_id") == patient_id:
                    records.append(decrypt_record(rec))
    except Exception as e:
        print(f"Error reading local history range: {e}")
    return records

def log_agent_event(patient_id: str, agent_name: str, action: str):
    """Logs an agent activity to MongoDB or JSON fallback."""
    date_str = datetime.datetime.now(ZoneInfo("Asia/Kolkata")).strftime("%Y-%m-%d")
    timestamp = datetime.datetime.now(ZoneInfo("Asia/Kolkata")).strftime("%H:%M")
    event_doc = {
        "patient_id": patient_id,
        "date": date_str,
        "agent_name": agent_name,
        "action": action,
        "timestamp": timestamp
    }
    
    if not using_fallback():
        db = get_db()
        try:
            db.agent_events.insert_one(event_doc)
            print(f"[MongoDB Log] [{patient_id}] [{agent_name}] {action} at {timestamp}")
            return
        except Exception as e:
            print(f"[MongoDB] Error logging event: {e}. Falling back.")
            
    ensure_fallback_files(patient_id)
    try:
        with open(get_agent_events_path(patient_id), "r") as f:
            data = json.load(f)
        events = data.get("events", [])
        events.append(event_doc)
        data["events"] = events
        with open(get_agent_events_path(patient_id), "w") as f:
            json.dump(data, f, indent=2)
    except Exception as e:
        print(f"Error logging local event: {e}")

def get_agent_events(patient_id: str, date_str: str):
    """Retrieve all agent events for a given date in reverse chronological order."""
    if not using_fallback():
        db = get_db()
        try:
            cursor = db.agent_events.find({"patient_id": patient_id, "date": date_str}).sort("timestamp", -1)
            events = []
            for doc in cursor:
                doc.pop("_id", None)
                events.append(doc)
            return events
        except Exception as e:
            print(f"[MongoDB] Error fetching agent events: {e}. Falling back.")
            
    ensure_fallback_files(patient_id)
    try:
        with open(get_agent_events_path(patient_id), "r") as f:
            data = json.load(f)
        day_events = [e for e in data.get("events", []) if e.get("date") == date_str and e.get("patient_id") == patient_id]
        return sorted(day_events, key=lambda x: x.get("timestamp", ""), reverse=True)
    except Exception as e:
        print(f"Error reading local events: {e}")
        return []

def log_pipeline_execution(patient_id: str, date_str: str, trace_logs: dict):
    """Log a complete pipeline trace event to MongoDB or JSON fallback."""
    os.makedirs(DATA_DIR, exist_ok=True)
    trace_doc = {
        "patient_id": patient_id,
        "date": date_str,
        "timestamp": datetime.datetime.now(ZoneInfo("Asia/Kolkata")).isoformat(),
        "trace": trace_logs
    }
    
    if not using_fallback():
        db = get_db()
        try:
            db.pipeline_execution_logs.replace_one(
                {"patient_id": patient_id, "date": date_str},
                trace_doc,
                upsert=True
            )
            return
        except Exception as e:
            print(f"[MongoDB] Error logging pipeline execution: {e}. Falling back.")
            
    # File fallback
    trace_path = os.path.join(DATA_DIR, f"pipeline_execution_logs_{patient_id}.json")
    try:
        records = []
        if os.path.exists(trace_path):
            with open(trace_path, "r") as f:
                records = json.load(f)
        # Deduplicate
        records = [r for r in records if r.get("date") != date_str]
        records.append(trace_doc)
        with open(trace_path, "w") as f:
            json.dump(records, f, indent=2)
    except Exception as e:
        print(f"Error logging local pipeline execution: {e}")

def get_pipeline_execution(patient_id: str, date_str: str) -> dict:
    """Retrieve the pipeline execution trace for a given patient and date."""
    if not using_fallback():
        db = get_db()
        try:
            doc = db.pipeline_execution_logs.find_one({"patient_id": patient_id, "date": date_str})
            if doc:
                doc.pop("_id", None)
                return doc.get("trace", {})
            return {}
        except Exception as e:
            print(f"[MongoDB] Error reading pipeline execution: {e}. Falling back.")
            
    # File fallback
    trace_path = os.path.join(DATA_DIR, f"pipeline_execution_logs_{patient_id}.json")
    try:
        if os.path.exists(trace_path):
            with open(trace_path, "r") as f:
                records = json.load(f)
            for r in records:
                if r.get("date") == date_str:
                    return r.get("trace", {})
    except Exception as e:
        print(f"Error reading local pipeline execution: {e}")
    return {}

