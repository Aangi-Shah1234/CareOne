import os
import json
import datetime
import html as html_utils
import pandas as pd
from dotenv import load_dotenv
import gradio as gr
from fpdf import FPDF

# Load environment configurations
load_dotenv()

import src.db as db
from src.security import encrypt_data, decrypt_data, sanitize_input, log_security_event
from src.memory import (
    load_care_plan, 
    save_care_plan, 
    get_day_record, 
    save_day_record, 
    get_history_range, 
    log_agent_event, 
    get_agent_events,
    get_patient_profiles,
    get_pipeline_execution
)
from src.pipeline import run_careone_pipeline

# Ensure database is seeded on startup
db.seed_database()

# Default patient tasks mapping for index lookup (will be updated dynamically for new patients)
PATIENT_TASKS = {
    "arthur_78": ["breakfast", "morning_meds", "lunch", "afternoon_hydration", "evening_walk", "dinner", "evening_meds"],
    "eleanor_82": ["bp_check", "renal_breakfast", "renal_meds", "fluid_check", "light_yoga", "renal_dinner", "evening_bp_check"]
}

# --- CLINICAL PDF GENERATOR (FPDF2) ---
class HandoffPDF(FPDF):
    def header(self):
        # Deep Space Purple Header Band
        self.set_fill_color(16, 8, 33)
        self.rect(0, 0, 210, 30, 'F')
        self.set_y(10)
        self.set_font('helvetica', 'B', 15)
        self.set_text_color(255, 255, 255)
        self.cell(0, 10, '   CareOne - Clinical Care Handoff Brief', border=False, align='L')
        self.ln(12)
        
    def footer(self):
        self.set_y(-15)
        self.set_font('helvetica', 'I', 8)
        self.set_text_color(167, 139, 250)
        self.cell(0, 10, f'CareOne Workspace | Page {self.page_no()}', 0, 0, 'C')

def generate_handoff_pdf(summary_text, vitals_list, gaps_list, date_str, patient_id):
    pdf = HandoffPDF()
    pdf.add_page()
    pdf.set_margins(15, 35, 15)
    pdf.set_y(35)
    
    plan = load_care_plan(patient_id)
    
    # Patient Metadata Block
    pdf.set_fill_color(243, 239, 255)
    pdf.set_draw_color(124, 58, 237)
    pdf.rect(15, 35, 180, 22, 'DF')
    pdf.set_font('helvetica', 'B', 10)
    pdf.set_text_color(16, 8, 33)
    pdf.text(20, 41, f"PATIENT: {plan.get('patient_name')} ({plan.get('relationship')})")
    pdf.text(20, 48, f"AGE: {plan.get('age')}")
    pdf.text(95, 41, f"DATE: {date_str}")
    pdf.text(95, 48, f"DIAGNOSIS: {plan.get('conditions')}")
    
    # 1. Executive Summary
    pdf.set_y(62)
    pdf.set_font('helvetica', 'B', 11)
    pdf.set_text_color(124, 58, 237)
    pdf.cell(0, 10, "1. DAILY CLINICAL SUMMARY NARRATIVE", new_x="LMARGIN", new_y="NEXT")
    pdf.set_font('helvetica', '', 9.5)
    pdf.set_text_color(40, 40, 40)
    pdf.multi_cell(0, 5, summary_text)
    pdf.ln(4)
    
    # 2. Vitals Measurements
    pdf.set_font('helvetica', 'B', 11)
    pdf.set_text_color(124, 58, 237)
    pdf.cell(0, 10, "2. MEASURED PHYSIOLOGICAL VITALS", new_x="LMARGIN", new_y="NEXT")
    pdf.set_font('helvetica', '', 9.5)
    pdf.set_text_color(40, 40, 40)
    if vitals_list:
        for vit in vitals_list:
            pdf.cell(0, 6, f"- {vit['vital_type']}: {decrypt_data(vit['value_raw'])} (Status: {vit['status']} - {vit['explanation']})", new_x="LMARGIN", new_y="NEXT")
    else:
        pdf.cell(0, 6, "No physiological vitals recorded today.", new_x="LMARGIN", new_y="NEXT")
    pdf.ln(4)
    
    # 3. Unconfirmed Care Gaps
    pdf.set_font('helvetica', 'B', 11)
    pdf.set_text_color(124, 58, 237)
    pdf.cell(0, 10, "3. UNCONFIRMED DAILY SCHEDULE TASKS", new_x="LMARGIN", new_y="NEXT")
    pdf.set_font('helvetica', '', 9.5)
    pdf.set_text_color(40, 40, 40)
    if gaps_list:
        for gap in gaps_list:
            pdf.cell(0, 6, f"- {gap['task_name']} ({gap['importance']} Importance): {gap['explanation']}", new_x="LMARGIN", new_y="NEXT")
    else:
        pdf.cell(0, 6, "All care plan scheduled tasks successfully completed today.", new_x="LMARGIN", new_y="NEXT")
    
    # Safety Disclaimer
    pdf.ln(8)
    pdf.set_fill_color(254, 242, 242)
    pdf.set_draw_color(239, 68, 68)
    pdf.rect(15, pdf.get_y(), 180, 15, 'DF')
    pdf.set_y(pdf.get_y() + 3)
    pdf.set_font('helvetica', 'B', 8)
    pdf.set_text_color(220, 38, 38)
    pdf.multi_cell(0, 4, "DISCLAIMER: CareOne compiles observations and unconfirmed logs only. Please consult a licensed physician or doctor for clinical diagnoses or medication dosage changes.", align='C')
    
    os.makedirs(os.path.join(DATA_DIR, "briefs"), exist_ok=True)
    pdf_path = os.path.join(DATA_DIR, "briefs", f"handoff_{patient_id}_{date_str}.pdf")
    pdf.output(pdf_path)
    return pdf_path

# --- PREMIUM DARK GLASSMORPHIC CSS ---
VIVID_PURPLE_CSS = """
:root {
    --bg: #090314;
    --panel: rgba(22, 13, 44, 0.65);
    --panel-accent: rgba(36, 21, 71, 0.5);
    --border: rgba(167, 139, 250, 0.22);
    --border-hover: rgba(167, 139, 250, 0.45);
    --ink: #e2d9f3;
    --muted: #a78bfa;
    --brand: #7C3AED;
    --brand-strong: #8B5CF6;
    --accent: #2563eb;
    --amber: #f59e0b;
    --danger: #ef4444;
    --success: #10b981;
}

body, .gradio-container {
    background: var(--bg) !important;
    background-image: radial-gradient(circle at 10% 20%, rgba(124, 58, 237, 0.12) 0%, transparent 40%), 
                      radial-gradient(circle at 90% 80%, rgba(16, 185, 129, 0.06) 0%, transparent 40%) !important;
    color: var(--ink) !important;
    font-family: 'Outfit', Inter, sans-serif !important;
}

.gradio-container {
    max-width: 1440px !important;
    margin: 0 auto !important;
    padding: 20px !important;
}

.clinical-nav {
    background: var(--panel) !important;
    backdrop-filter: blur(12px) !important;
    border: 1px solid var(--border) !important;
    border-radius: 12px !important;
    padding: 16px 20px !important;
    margin-bottom: 16px !important;
    box-shadow: 0 8px 32px rgba(124, 58, 237, 0.1) !important;
}

.glass-panel {
    background: var(--panel) !important;
    backdrop-filter: blur(12px) !important;
    border: 1px solid var(--border) !important;
    border-radius: 12px !important;
    padding: 20px !important;
    margin-bottom: 16px !important;
    box-shadow: 0 8px 32px rgba(0, 0, 0, 0.2) !important;
}

.glass-panel:hover {
    border-color: var(--border-hover) !important;
}

.product-hero {
    background: linear-gradient(135deg, rgba(124, 58, 237, 0.4) 0%, rgba(16, 8, 33, 0.8) 100%);
    border: 1px solid var(--border);
    border-radius: 12px;
    padding: 24px;
    margin-bottom: 16px;
    box-shadow: 0 8px 32px rgba(124, 58, 237, 0.1);
}

.product-hero h1 {
    color: #fff;
    font-size: 1.8rem;
    font-weight: 800;
    margin: 0;
}

.product-hero p {
    color: var(--muted);
    font-size: 0.95rem;
    margin: 8px 0 0 0;
    line-height: 1.5;
}

.kpi-grid {
    display: grid;
    grid-template-columns: repeat(4, minmax(0, 1fr));
    gap: 14px;
    margin-bottom: 16px;
}

.kpi-card {
    background: rgba(16, 8, 33, 0.6);
    border: 1px solid var(--border);
    border-radius: 10px;
    padding: 16px;
    backdrop-filter: blur(8px);
    transition: all 0.2s ease;
}

.kpi-card:hover {
    border-color: var(--border-hover);
    transform: translateY(-2px);
}

.kpi-label {
    color: var(--muted);
    font-size: 0.76rem;
    font-weight: 700;
    letter-spacing: 0.05em;
    text-transform: uppercase;
}

.kpi-value {
    color: #ffffff;
    font-size: 1.75rem;
    font-weight: 800;
    line-height: 1.2;
    margin-top: 6px;
}

.kpi-note {
    color: var(--muted);
    font-size: 0.82rem;
    margin-top: 6px;
}

input, textarea, select, .dropdown {
    background: rgba(16, 8, 33, 0.5) !important;
    border: 1px solid var(--border) !important;
    color: var(--ink) !important;
    border-radius: 8px !important;
}

input:focus, textarea:focus, select:focus {
    border-color: var(--brand-strong) !important;
}

label, .wrap label, .block label span {
    color: var(--muted) !important;
    font-weight: 600 !important;
    font-size: 0.85rem !important;
}

button.primary-btn {
    background: linear-gradient(135deg, var(--brand) 0%, var(--brand-strong) 100%) !important;
    color: #fff !important;
    border: none !important;
    border-radius: 8px !important;
    font-weight: 700 !important;
    min-height: 42px !important;
    box-shadow: 0 4px 14px rgba(124, 58, 237, 0.3) !important;
}

button.primary-btn:hover {
    transform: translateY(-1px);
    box-shadow: 0 6px 20px rgba(124, 58, 237, 0.4) !important;
}

button.ghost-btn {
    background: rgba(255, 255, 255, 0.03) !important;
    color: var(--muted) !important;
    border: 1px solid var(--border) !important;
    border-radius: 8px !important;
    font-weight: 600 !important;
    min-height: 40px !important;
}

button.ghost-btn:hover {
    background: rgba(255, 255, 255, 0.08) !important;
    border-color: var(--border-hover) !important;
}

.glass-badge {
    display: inline-flex;
    align-items: center;
    gap: 6px;
    padding: 4px 10px;
    border-radius: 999px;
    font-size: 0.72rem;
    font-weight: 700;
    text-transform: uppercase;
}

.badge-completed { background: rgba(16, 185, 129, 0.15) !important; color: #34d399 !important; border: 1px solid rgba(52, 211, 153, 0.3); }
.badge-delayed { background: rgba(245, 158, 11, 0.15) !important; color: #fbbf24 !important; border: 1px solid rgba(251, 191, 36, 0.3); }
.badge-refused { background: rgba(239, 68, 68, 0.15) !important; color: #f87171 !important; border: 1px solid rgba(248, 113, 113, 0.3); }
.badge-skipped { background: rgba(100, 116, 139, 0.15) !important; color: #cbd5e1 !important; border: 1px solid rgba(203, 213, 225, 0.3); }

.safety-box-alert, .warning-box-alert {
    padding: 12px 16px;
    border-radius: 8px;
    margin-bottom: 12px;
    border: 1px solid;
}

.safety-box-alert {
    background: rgba(239, 68, 68, 0.1) !important;
    border-color: rgba(239, 68, 68, 0.3) !important;
    color: #fca5a5 !important;
}

.warning-box-alert {
    background: rgba(245, 158, 11, 0.08) !important;
    border-color: rgba(245, 158, 11, 0.25) !important;
    color: #fde047 !important;
}

.timeline-item, .gap-item, .feed-item {
    background: rgba(16, 8, 33, 0.4);
    border: 1px solid var(--border);
    border-radius: 8px;
    padding: 12px;
    margin-bottom: 10px;
}

.timeline-item { border-left: 4px solid var(--brand); }
.gap-item.high { border-left: 4px solid var(--danger); }
.gap-item.medium { border-left: 4px solid var(--amber); }
.gap-item.low { border-left: 4px solid var(--accent); }

.section-title {
    margin: 0 0 8px 0;
    color: #ffffff;
    font-size: 1.05rem;
    font-weight: 750;
}

.section-subtitle {
    margin: -4px 0 14px 0;
    color: var(--muted);
    font-size: 0.85rem;
}

.pulse-indicator {
    width: 8px;
    height: 8px;
    background-color: var(--teal);
    border-radius: 50%;
    display: inline-block;
    box-shadow: 0 0 0 0 rgba(16, 185, 129, 0.6);
    animation: pulsing 1.6s infinite;
}

@keyframes pulsing {
    0% { box-shadow: 0 0 0 0 rgba(16, 185, 129, 0.6); }
    70% { box-shadow: 0 0 0 8px rgba(16, 185, 129, 0); }
    100% { box-shadow: 0 0 0 0 rgba(16, 185, 129, 0); }
}

#login-promo {
    background: rgba(16, 8, 33, 0.5) !important;
    border-right: 1px solid rgba(167, 139, 250, 0.15) !important;
    border-radius: 12px 0 0 12px !important;
    padding: 24px !important;
    display: flex !important;
    flex-direction: column !important;
    justify-content: center !important;
    align-items: center !important;
}

#login-img img {
    border-radius: 10px !important;
    box-shadow: 0 8px 32px rgba(124, 58, 237, 0.3) !important;
    border: 1px solid rgba(167, 139, 250, 0.2) !important;
}

#login-form-box {
    padding: 30px !important;
}

.demographics-card ul {
    margin: 4px 0 0 0;
    padding-left: 18px;
}

.patient-grid {
    display: grid;
    grid-template-columns: repeat(auto-fill, minmax(280px, 1fr));
    gap: 14px;
    margin-top: 10px;
}

.patient-card {
    background: rgba(16, 8, 33, 0.4);
    border: 1px solid var(--border);
    border-radius: 10px;
    padding: 14px;
    transition: all 0.2s ease;
}

.patient-card:hover {
    border-color: var(--border-hover);
    transform: translateY(-2px);
}
"""

# --- CONFIG & MONGO SETUP CONTROLLERS ---
def update_system_config(api_key, mongo_uri):
    api_key = api_key.strip()
    mongo_uri = mongo_uri.strip()
    
    # Update local .env file
    env_lines = []
    if os.path.exists(".env"):
        with open(".env", "r", encoding="utf-8") as f:
            env_lines = f.readlines()
            
    updated_key = False
    updated_uri = False
    for i, line in enumerate(env_lines):
        if line.startswith("GEMINI_API_KEY="):
            env_lines[i] = f'GEMINI_API_KEY="{api_key}"\n'
            updated_key = True
        elif line.startswith("MONGO_URI="):
            env_lines[i] = f'MONGO_URI="{mongo_uri}"\n'
            updated_uri = True
            
    if not updated_key:
        env_lines.append(f'GEMINI_API_KEY="{api_key}"\n')
    if not updated_uri:
        env_lines.append(f'MONGO_URI="{mongo_uri}"\n')
        
    with open(".env", "w", encoding="utf-8") as f:
        f.writelines(env_lines)
        
    # Reconfigure models and connection pings
    import src.config as cfg
    cfg.reconfigure_api(api_key)
    
    success = db.reconnect(mongo_uri, "CareOne")
    
    if success:
        return "<div style='color:#10b981; font-weight:bold; margin-top:8px;'>✅ Connected to MongoDB Atlas successfully! Configuration saved.</div>"
    else:
        return "<div style='color:#ef4444; font-weight:bold; margin-top:8px;'>❌ Failed to connect to MongoDB Atlas cluster. Using local fallback.</div>"

# --- LOGIN & SIGNUP HANDLERS ---
def handle_login(username, password):
    username = sanitize_input(username)
    
    if using_fallback():
        # Fallback simulated verification
        if username == "caregiver" and password == "careone":
            log_security_event("caregiver", "Lead Nurse", "Logged in successfully (Fallback)")
            user_info = {"username": "caregiver", "name": "Sarah Jenkins", "role": "Lead Nurse"}
            return gr.update(visible=False), gr.update(visible=True), user_info, ""
        elif username == "caregiver_john" and password == "careone":
            log_security_event("caregiver_john", "Assisting Caregiver", "Logged in successfully (Fallback)")
            user_info = {"username": "caregiver_john", "name": "John Doe", "role": "Assisting Caregiver"}
            return gr.update(visible=False), gr.update(visible=True), user_info, ""
        elif username == "doctor_patel" and password == "careone":
            log_security_event("doctor_patel", "Primary Physician", "Logged in successfully (Fallback)")
            user_info = {"username": "doctor_patel", "name": "Dr. Patel", "role": "Primary Physician"}
            return gr.update(visible=False), gr.update(visible=True), user_info, ""
        return gr.update(), gr.update(), None, "Invalid credentials. Use 'caregiver' / 'careone'."

    db_conn = db.get_db()
    try:
        user = db_conn.users.find_one({"username": username})
        if user and user["password"] == db.hash_password(password):
            user_info = {"username": username, "name": user.get("name", username), "role": user.get("role", "Caregiver")}
            log_security_event(username, user_info["role"], "Logged in successfully")
            return gr.update(visible=False), gr.update(visible=True), user_info, ""
        log_security_event(username, "unknown", "Failed login attempt")
        return gr.update(), gr.update(), None, "Invalid username or password."
    except Exception as e:
        return gr.update(), gr.update(), None, f"Auth Error: {e}"

def handle_signup(username, password, name, role):
    username = sanitize_input(username)
    name = sanitize_input(name)
    if not username or not password or not name:
        return gr.update(), gr.update(), None, "Please fill in all registration fields."
        
    if using_fallback():
        user_info = {"username": username, "name": name, "role": role}
        log_security_event(username, role, "Registered new account (Fallback)")
        return gr.update(visible=False), gr.update(visible=True), user_info, ""

    db_conn = db.get_db()
    try:
        existing = db_conn.users.find_one({"username": username})
        if existing:
            return gr.update(), gr.update(), None, "Username already exists."
            
        user_doc = {
            "username": username,
            "password": db.hash_password(password),
            "name": name,
            "role": role or "Caregiver"
        }
        db_conn.users.insert_one(user_doc)
        log_security_event(username, role, "Registered new account")
        user_info = {"username": username, "name": name, "role": role}
        return gr.update(visible=False), gr.update(visible=True), user_info, "Signup successful!"
    except Exception as e:
        return gr.update(), gr.update(), None, f"Signup Error: {e}"

# --- NEW PATIENT REGISTRATION ---
def register_new_patient(name, age, relationship, conditions, routines_text, preferences_text):
    name = sanitize_input(name).strip()
    relationship = sanitize_input(relationship).strip()
    conditions = sanitize_input(conditions).strip()
    
    if not name or not age:
        return "<div style='color:#ef4444; font-weight:bold;'>Error: Patient Name and Age are required.</div>", gr.update()

    patient_id = f"{name.lower().replace(' ', '_')}_{age}"
    
    # Process routine tasks list (one per line, e.g. "08:30 - Breakfast - Meal - High - Eat healthy")
    routine_tasks = []
    lines = routines_text.strip().split("\n")
    for idx, l in enumerate(lines):
        if not l.strip():
            continue
        parts = l.split("-")
        time_exp = parts[0].strip() if len(parts) > 0 else "09:00"
        task_name = parts[1].strip() if len(parts) > 1 else f"Routine Task {idx+1}"
        cat = parts[2].strip() if len(parts) > 2 else "Other"
        imp = parts[3].strip() if len(parts) > 3 else "Medium"
        desc = parts[4].strip() if len(parts) > 4 else "Schedule checklist task."
        
        routine_tasks.append({
            "task_id": f"task_{idx+1}",
            "name": task_name,
            "time_expected": time_exp,
            "category": cat,
            "importance": imp,
            "description": desc
        })
        
    if not routine_tasks:
        # Defaults if empty
        routine_tasks = [
            {"task_id": "breakfast", "name": "Breakfast", "time_expected": "08:30", "category": "Meal", "importance": "High", "description": "Scheduled meal."},
            {"task_id": "morning_meds", "name": "Medications", "time_expected": "09:00", "category": "Medication", "importance": "High", "description": "Scheduled medications."}
        ]
        
    # Preferences list
    prefs_list = [p.strip() for p in preferences_text.split("\n") if p.strip()]
    if not prefs_list:
        prefs_list = ["Prefers a quiet environment during care checks."]

    # Create patient document
    patient_doc = {
        "patient_id": patient_id,
        "patient_name": name,
        "age": int(age),
        "relationship": relationship or "Family",
        "conditions": conditions or "General Care",
        "preferences": prefs_list,
        "daily_routine": routine_tasks
    }
    
    # Save mapping to global dict
    PATIENT_TASKS[patient_id] = [t["task_id"] for t in routine_tasks]
    
    # Save to DB / Fallback
    save_care_plan(patient_id, patient_doc)
    
    # Trigger security log
    log_security_event("system", "system", f"Registered new patient {name} (ID: {patient_id})", patient_id)
    
    # Seed 7 days mock history for new patient to enable charts
    today = datetime.date.today()
    mock_history = []
    mock_vitals = []
    
    for i in range(7, 0, -1):
        log_date = (today - datetime.timedelta(days=i)).strftime("%Y-%m-%d")
        
        reconciled = []
        for t in routine_tasks:
            reconciled.append({
                "activity": t["name"],
                "inferred_time": t["time_expected"],
                "status": "Completed" if (i % 2 == 0 or t["importance"] == "High") else "Skipped",
                "caregivers": ["Sarah Jenkins"],
                "notes": f"Completed routine check.",
                "task_id": t["task_id"]
            })
            
        gaps = [{"task_id": e["task_id"], "task_name": e["activity"], "category": "Routine", "importance": "Medium", "confidence_score": 0.9, "explanation": "Unconfirmed schedule check."} for e in reconciled if e["status"] == "Skipped"]
        
        bp = "125/80" if i % 2 == 0 else "135/88"
        mock_history.append({
            "patient_id": patient_id,
            "date": log_date,
            "raw_notes": [{"caregiver": "Sarah Jenkins", "text": encrypt_data(f"Arthur check. BP was {bp}. Meals taken.")}],
            "reconciled_events": reconciled,
            "vitals": [
                {"vital_type": "Blood Pressure", "value_raw": encrypt_data(bp), "status": "Normal" if bp=="125/80" else "Elevated", "explanation": "Seeded baseline check.", "caregiver": "Sarah Jenkins", "timestamp": "09:00"}
            ],
            "conflicts": [],
            "interventions": [],
            "detected_gaps": gaps,
            "trends": {},
            "risk_assessment": {"risk_level": "Low", "description": "Patient stable on scheduled routines.", "confidence_score": 0.95, "reasoning_path": "No high risk indicators found."},
            "summary": {
                "executive_summary": "Patient is stable and compliant with scheduled meals and care routine checks.",
                "recommended_actions": ["Monitor general compliance."],
                "safety_alerts": []
            }
        })
        mock_vitals.append({
            "patient_id": patient_id,
            "date": log_date, "vital_type": "Blood Pressure", "value_raw": encrypt_data(bp), 
            "status": "Normal" if bp=="125/80" else "Elevated", 
            "explanation": "Daily BP", "caregiver": "Sarah Jenkins", "timestamp": "09:00"
        })
        
    if not using_fallback():
        db_conn = db.get_db()
        try:
            db_conn.care_logs.insert_many(mock_history)
            db_conn.vitals.insert_many(mock_vitals)
        except Exception as e:
            print(f"[MongoDB] Error seeding new patient history: {e}")
    else:
        # Local JSON fallback histories
        history_path = os.path.join(DATA_DIR, f"care_history_{patient_id}.json")
        with open(history_path, "w", encoding="utf-8") as f:
            json.dump({"history": mock_history}, f, indent=2)
            
    # Refresh Patient list outputs
    profiles = get_patient_profiles()
    dropdown_choices = [(p["name"], p["patient_id"]) for p in profiles]
    
    success_html = f"<div style='color:#10b981; font-weight:bold; margin-top:8px;'>✅ Successfully registered new patient: {name} (ID: {patient_id}) and seeded 7-day history!</div>"
    
    return success_html, gr.update(choices=dropdown_choices), render_patient_directory(profiles)

# --- CHECKLIST CHECKBOX TOGGLES ---
def update_checklist_task(task_index, is_checked, patient_id, date_str, user_state):
    tasks = PATIENT_TASKS.get(patient_id, ["breakfast", "morning_meds", "lunch", "afternoon_hydration", "evening_walk", "dinner", "evening_meds"])
    if task_index >= len(tasks):
        return gr.update(), gr.update(), gr.update(), gr.update()
        
    task_id = tasks[task_index]
    caregiver_name = user_state.get("name") if user_state else "Caregiver"
    status_str = "Completed" if is_checked else "Skipped"
    
    log_security_event(user_state.get("username") if user_state else "caregiver", user_state.get("role") if user_state else "Nurse", f"Toggled checklist item {task_id} to {status_str}", patient_id)
    log_agent_event(patient_id, "Gaps Agent", f"Checklist updated: {task_id.replace('_', ' ').capitalize()} marked as {status_str.lower()}")

    day_record = get_day_record(patient_id, date_str)
    plan = load_care_plan(patient_id)
    
    if not day_record:
        day_record = {
            "patient_id": patient_id,
            "date": date_str,
            "raw_notes": [],
            "reconciled_events": [],
            "vitals": [],
            "conflicts": [],
            "interventions": [],
            "detected_gaps": [],
            "trends": {},
            "summary": {}
        }
        
    matching_task = next((t for t in plan.get("daily_routine", []) if t["task_id"] == task_id), None)
            
    if matching_task:
        found = False
        for ev in day_record["reconciled_events"]:
            if ev["activity"].lower() == matching_task["name"].lower() or ev.get("task_id") == task_id:
                ev["status"] = status_str
                ev["inferred_time"] = matching_task["time_expected"]
                if caregiver_name not in ev.setdefault("caregivers", []):
                    ev["caregivers"].append(caregiver_name)
                found = True
                break
                
        if not found:
            day_record["reconciled_events"].append({
                "activity": matching_task["name"],
                "inferred_time": matching_task["time_expected"],
                "status": status_str,
                "caregivers": [caregiver_name],
                "notes": f"Checked off via EMR checklist.",
                "task_id": task_id
            })

    from src.agents.gap_detector import GapDetectorAgent
    detector = GapDetectorAgent()
    detector_res = detector.detect_gaps(
        care_plan=plan,
        reconciled_events=day_record["reconciled_events"],
        current_time_context=f"Analysis date: {date_str}"
    )
    day_record["detected_gaps"] = detector_res.get("detected_gaps", [])
    
    save_day_record(patient_id, date_str, day_record)
    
    timeline_html = render_timeline(day_record.get("reconciled_events", []))
    gaps_html = render_gaps(day_record.get("detected_gaps", []))
    events_html = render_activity_feed(patient_id, date_str)
    kpi_html = render_kpi_overview(patient_id, day_record)
    
    return timeline_html, gaps_html, events_html, kpi_html

# --- HTML RENDER HELPERS ---
def render_kpi_overview(patient_id, day_record=None):
    day_record = day_record or {}
    events = day_record.get("reconciled_events", [])
    vitals = day_record.get("vitals", [])
    gaps = day_record.get("detected_gaps", [])
    conflicts = day_record.get("conflicts", [])
    
    completed = sum(1 for ev in events if ev.get("status") in ["Completed", "Delayed"])
    tasks = PATIENT_TASKS.get(patient_id, ["breakfast", "morning_meds", "lunch", "afternoon_hydration", "evening_walk", "dinner", "evening_meds"])
    total = max(len(tasks), 1)
    completion = int((completed / total) * 100)
    
    high_gaps = sum(1 for gp in gaps if gp.get("importance", "").lower() == "high")
    alert_vitals = sum(1 for v in vitals if v.get("status", "").lower() not in ["normal", "ok", "stable"])
    
    return f"""
    <div class="kpi-grid">
        <div class="kpi-card">
            <div class="kpi-label">Care Completion</div>
            <div class="kpi-value">{completion}%</div>
            <div class="kpi-note">{completed} of {total} routines completed</div>
        </div>
        <div class="kpi-card">
            <div class="kpi-label">Open Risk Gaps</div>
            <div class="kpi-value">{len(gaps)}</div>
            <div class="kpi-note">{high_gaps} high-priority gaps pending</div>
        </div>
        <div class="kpi-card">
            <div class="kpi-label">Vitals Logged</div>
            <div class="kpi-value">{len(vitals)}</div>
            <div class="kpi-note">{alert_vitals} alerts outside parameters</div>
        </div>
        <div class="kpi-card">
            <div class="kpi-label">Care Conflicts</div>
            <div class="kpi-value">{len(conflicts)}</div>
            <div class="kpi-note">contradictions in shift logs</div>
        </div>
    </div>
    """

def render_timeline(events):
    if not events:
        return "<div class='timeline-item' style='color:#667385;'>No care activities reconciled today.</div>"
        
    html = ""
    def sort_time(e):
        t = e.get("inferred_time", "Unknown")
        return t if t != "Unknown" else "23:59"
        
    for ev in sorted(events, key=sort_time):
        status = ev.get("status", "Unknown").lower()
        badge_style = f"badge-{status}" if status in ["completed", "delayed", "refused", "skipped"] else "badge-skipped"
        caregivers_str = html_utils.escape(", ".join(ev.get("caregivers", [])))
        time_text = html_utils.escape(ev.get('inferred_time', 'Unknown'))
        status_text = html_utils.escape(ev.get('status', 'Unknown'))
        activity_text = html_utils.escape(ev.get('activity', 'Care activity'))
        notes_text = html_utils.escape(ev.get('notes', ''))
        
        html += f"""
        <div class="timeline-item">
            <span style="font-weight:800; color:#7C3AED;">{time_text}</span>
            <span class="glass-badge {badge_style}" style="float:right;">{status_text}</span>
            <h4 style="margin: 5px 0 3px 0; color:#ffffff; font-size:0.92rem;">{activity_text}</h4>
            <p style="margin: 0; color:#cbd5e1; font-size:0.86rem;">{notes_text}</p>
            <small style="color:#a78bfa; font-size:0.75rem;">Logged by: {caregivers_str}</small>
        </div>
        """
    return html

def render_gaps(gaps):
    if not gaps:
        return "<div class='gap-item low' style='color:#34d399; font-weight:700;'>All care plan tasks confirmed completed today.</div>"
        
    html = ""
    for gp in gaps:
        conf = gp.get("confidence_score", 0.9)
        gap_class = "high" if conf >= 0.9 else ("medium" if conf >= 0.7 else "low")
        task_name = html_utils.escape(gp.get("task_name", "Unconfirmed task"))
        explanation = html_utils.escape(gp.get("explanation", "Needs caregiver review."))
        importance = html_utils.escape(gp.get("importance", "Unknown"))
        category = html_utils.escape(gp.get("category", "Care"))
        
        html += f"""
        <div class="gap-item {gap_class}">
            <span style="font-weight:800; font-size:0.9rem; color:#ffffff;">{task_name}</span>
            <span class="glass-badge badge-skipped" style="float:right;">Confidence: {int(conf*100)}%</span>
            <p style="margin: 6px 0 4px 0; font-size: 0.84rem; color:#cbd5e1;">{explanation}</p>
            <small style="color:#a78bfa; font-size:0.75rem;">Importance: {importance} | Category: {category}</small>
        </div>
        """
    return html

def render_activity_feed(patient_id, date_str):
    events = get_agent_events(patient_id, date_str)
    if not events:
        return "<div class='feed-item' style='color:#667385; text-align:center;'>Feed empty. Process logs to activate agents.</div>"
        
    html = "<div style='display:flex; flex-direction:column; gap:8px; max-height:420px; overflow-y:auto; padding-right:5px;'>"
    badge_colors = {
        "Parser Agent": "background:rgba(59,130,246,0.15); color:#60a5fa; border:1px solid rgba(59,130,246,0.3);",
        "Vitals Agent": "background:rgba(20,184,166,0.15); color:#2dd4bf; border:1px solid rgba(20,184,166,0.3);",
        "Reconciler Agent": "background:rgba(99,102,241,0.15); color:#818cf8; border:1px solid rgba(99,102,241,0.3);",
        "Refusal Agent": "background:rgba(239,68,68,0.15); color:#f87171; border:1px solid rgba(239,68,68,0.3);",
        "Gaps Agent": "background:rgba(245,158,11,0.15); color:#fbbf24; border:1px solid rgba(245,158,11,0.3);",
        "Risk Agent": "background:rgba(236,72,153,0.15); color:#f472b6; border:1px solid rgba(236,72,153,0.3);",
        "Trends Agent": "background:rgba(14,165,233,0.15); color:#38bdf8; border:1px solid rgba(14,165,233,0.3);",
        "Summary Agent": "background:rgba(16,185,129,0.15); color:#34d399; border:1px solid rgba(16,185,129,0.3);"
    }
    
    for ev in events:
        a_name = ev.get("agent_name", "System")
        color = badge_colors.get(a_name, "background:rgba(255,255,255,0.05); color:#cbd5e1; border:1px solid rgba(255,255,255,0.1);")
        a_name_safe = html_utils.escape(a_name)
        action_safe = html_utils.escape(ev.get("action", ""))
        timestamp_safe = html_utils.escape(ev.get("timestamp", ""))
        
        html += f"""
        <div class="feed-item" style="display:flex; justify-content:space-between; align-items:center; gap:8px; padding:8px; margin-bottom:5px;">
            <div style="display:flex; align-items:center; gap:6px; min-width:0;">
                <span class="glass-badge" style="{color} font-size:0.62rem; padding: 2px 6px;">{a_name_safe}</span>
                <span style="font-size:0.8rem; color:#cbd5e1; white-space:nowrap; overflow:hidden; text-overflow:ellipsis;">{action_safe}</span>
            </div>
            <small style="color:#a78bfa; font-size:0.7rem;">{timestamp_safe}</small>
        </div>
        """
    html += "</div>"
    return html

def render_demographics(plan):
    name = plan.get("patient_name", "Patient")
    age = plan.get("age", "")
    conds = plan.get("conditions", "")
    prefs = plan.get("preferences", [])
    
    prefs_html = "".join([f"<li style='margin-bottom:4px;color:#cbd5e1;font-size:0.8rem;'>{html_utils.escape(p)}</li>" for p in prefs])
    
    html = f"""
    <div class="demographics-card" style="padding: 12px; border-radius: 8px; background: rgba(255,255,255,0.02); border: 1px solid rgba(167, 139, 250, 0.15);">
        <h4 style="margin: 0; color:#ffffff; font-size:1.05rem;">{name} · Age {age}</h4>
        <p style="margin: 4px 0 8px 0; color:#a78bfa; font-size:0.85rem;"><strong>Diagnosis:</strong> {conds}</p>
        <span style="color:#ffffff; font-size:0.8rem; font-weight:bold;">Preferences & Context Memory:</span>
        <ul style="margin: 4px 0 0 0; padding-left: 18px;">
            {prefs_html or "<li style='color:#667385;'>No recorded preferences</li>"}
        </ul>
    </div>
    """
    return html

def render_risk_card(risk_data):
    if not risk_data:
        return "<div style='background:rgba(255,255,255,0.02); border:1px dashed rgba(167,139,250,0.15); padding:14px; border-radius:8px; text-align:center; color:#a78bfa; font-size:0.85rem;'>No safety risk evaluation. Process logs to audit patient risk level.</div>"
        
    level = risk_data.get("risk_level", "Low")
    desc = risk_data.get("description", "")
    conf = int(risk_data.get("confidence_score", 0.9) * 100)
    indics = risk_data.get("indicators", [])
    
    level_colors = {
        "Critical": "border-color: #ef4444; background: rgba(239, 68, 68, 0.12); color: #fecaca;",
        "High": "border-color: #f87171; background: rgba(248, 113, 113, 0.1); color: #fee2e2;",
        "Medium": "border-color: #fbbf24; background: rgba(251, 191, 36, 0.08); color: #fef3c7;",
        "Low": "border-color: #34d399; background: rgba(52, 211, 153, 0.06); color: #d1fae5;"
    }
    style = level_colors.get(level, level_colors["Low"])
    
    ind_html = "".join([f"<span class='glass-badge' style='background:rgba(255,255,255,0.05); color:#cbd5e1; border:1px solid rgba(255,255,255,0.1); margin-right:5px; font-size:0.72rem; font-weight:normal; text-transform:none;'>{html_utils.escape(i)}</span>" for i in indics])
    
    html = f"""
    <div class="risk-card" style="border: 1px solid; border-radius: 8px; padding: 14px; margin-bottom: 12px; {style}">
        <div style="display:flex; justify-content:space-between; align-items:center; margin-bottom:6px;">
            <strong style="font-size:1.05rem;">⚠️ Safety Risk: {level}</strong>
            <span class="glass-badge badge-skipped" style="font-size:0.7rem;">Confidence: {conf}%</span>
        </div>
        <p style="margin: 0 0 6px 0; font-size: 0.86rem; line-height:1.4;">{html_utils.escape(desc)}</p>
        <div style="display:flex; flex-wrap:wrap; gap:4px; margin-top:6px;">
            {ind_html}
        </div>
    </div>
    """
    return html

def render_observability_trace(patient_id, date_str):
    trace = get_pipeline_execution(patient_id, date_str)
    if not trace:
        return "<div class='glass-panel' style='text-align:center; padding:20px; color:#a78bfa; font-size:0.85rem;'>No agent execution traces recorded today. Process a caregiver note to view execution logs.</div>"
        
    metadata = trace.get("pipeline_metadata", {})
    ts = metadata.get("timestamp", "N/A")
    cg = metadata.get("caregiver", "N/A")
    
    html = f"""
    <div style='margin-bottom:12px; padding:8px 12px; background:rgba(255,255,255,0.02); border:1px solid rgba(167, 139, 250, 0.15); border-radius:8px; font-size:0.8rem; color:#cbd5e1;'>
        <strong>Observability Pipeline Log:</strong> Processed at {ts} | caregiver: {cg}
    </div>
    <div style='display:flex; flex-direction:column; gap:10px;'>
    """
    
    agent_info = [
        ("parser", "🩺 Note Parser Agent", "Extracts structured events from caregiver notes."),
        ("vitals_validator", "🔬 Vitals Validator Agent", "Validates clinical vitals (BP, sugar, fluids)."),
        ("reconciliation", "🤝 Reconciliation Agent", "Resolves duplicated care entries and flags conflicts."),
        ("refusal_handler", "🛡️ Refusal Handling Agent", "Detects task refusals and plans compliance interventions."),
        ("gap_detector", "🔍 Gap Detector Agent", "Cross-audits completed timeline against routine checklist."),
        ("risk_assessment", "⚠️ Risk Assessment Agent", "Calculates daily patient safety risk metrics."),
        ("trend_analyzer", "📈 Trend Analysis Agent", "Queries 7-day logs for longitudinal wellness trends."),
        ("summary", "📝 Care Summary Agent", "Compiles caregiver daily narratives and follow-ups.")
    ]
    
    for key, name, desc in agent_info:
        log = trace.get(key, {})
        dur = log.get("duration_ms", 0)
        conf = int(log.get("confidence_score", 0.9) * 100)
        why = log.get("reasoning_path", "Skipped or pending.")
        mem = log.get("retrieved_memory", "None")
        out_json = json.dumps(log.get("output", {}), indent=2)
        
        html += f"""
        <div class="agent-trace-card" style="border: 1px solid rgba(167, 139, 250, 0.15); border-radius: 8px; background: rgba(16,8,33,0.5); padding: 10px;">
            <div style="display:flex; justify-content:space-between; align-items:center; border-bottom:1px solid rgba(167, 139, 250, 0.1); padding-bottom:5px; margin-bottom:6px;">
                <strong style="color:#ffffff; font-size:0.88rem;">{name}</strong>
                <div style="display:flex; gap:6px;">
                    <span class="glass-badge" style="background:rgba(124,58,237,0.12); color:#c084fc; border:1px solid rgba(167,139,250,0.2); font-size:0.65rem; padding:1px 5px;">{dur}ms</span>
                    <span class="glass-badge" style="background:rgba(16,185,129,0.12); color:#34d399; border:1px solid rgba(52,211,153,0.2); font-size:0.65rem; padding:1px 5px;">{conf}%</span>
                </div>
            </div>
            <p style="margin: 0 0 4px 0; color:#a78bfa; font-size:0.75rem; font-style:italic;">{desc}</p>
            <p style="margin: 0 0 4px 0; color:#cbd5e1; font-size:0.78rem;"><strong>Memory Context:</strong> {html_utils.escape(mem)}</p>
            <p style="margin: 0 0 6px 0; color:#cbd5e1; font-size:0.78rem;"><strong>Reasoning Path:</strong> {html_utils.escape(why)}</p>
            
            <details style="margin-top:4px;">
                <summary style="font-size:0.75rem; color:#c084fc; cursor:pointer;">View Output JSON</summary>
                <pre style="margin: 4px 0 0 0; padding: 6px; background:rgba(0,0,0,0.5); border-radius:4px; color:#a7f3d0; font-family:monospace; font-size:0.75rem; overflow-x:auto; white-space:pre-wrap;">{html_utils.escape(out_json)}</pre>
            </details>
        </div>
        """
        
    html += "</div>"
    return html

def render_patient_directory(profiles):
    html = "<div class='patient-grid'>"
    for p in profiles:
        p_name = html_utils.escape(p.get("name", "Patient"))
        p_id = html_utils.escape(p.get("patient_id", ""))
        age = html_utils.escape(str(p.get("age", "")))
        conds = html_utils.escape(p.get("conditions", ""))
        rel = html_utils.escape(p.get("relationship", "Family"))
        
        html += f"""
        <div class="patient-card">
            <h4 style="margin:0 0 5px 0; color:#ffffff; font-size:1rem;">👤 {p_name} ({rel})</h4>
            <p style="margin:0 0 8px 0; color:#a78bfa; font-size:0.8rem;">Age {age} | {conds}</p>
            <div style="font-size:0.78rem; color:#cbd5e1; margin-bottom:8px;">ID: <code>{p_id}</code></div>
            <button class="ghost-btn" style="width:100%; min-height:28px !important; font-size:0.8rem;" onclick="document.getElementById('open_workspace_{p_id}').click();">Open Workspace</button>
            <div style="display:none;"><button id="open_workspace_{p_id}" onclick="window.gradio_open_patient('{p_id}')">Open</button></div>
        </div>
        """
    html += "</div>"
    return html

def search_history(patient_id, query):
    query = sanitize_input(query)
    if not query:
        return "<div style='color:#a78bfa; font-size:0.85rem;'>Enter search query above.</div>"
        
    logs = get_history_range(patient_id, datetime.date.today().strftime("%Y-%m-%d"), days=30)
    
    html = "<div style='display:flex; flex-direction:column; gap:8px; max-height:360px; overflow-y:auto;'>"
    matches = 0
    
    for log in logs:
        log_date = log.get("date", "")
        note_match = False
        notes_found = []
        for n in log.get("raw_notes", []):
            txt = decrypt_data(n.get("text", ""))
            if query.lower() in txt.lower():
                notes_found.append(f"<strong>{html_utils.escape(n.get('caregiver', 'Caregiver'))}:</strong> {html_utils.escape(txt)}")
                note_match = True
                
        vits_found = []
        for v in log.get("vitals", []):
            val = decrypt_data(v.get("value_raw", ""))
            if query.lower() in val.lower() or query.lower() in v.get("vital_type", "").lower():
                vits_found.append(f"<strong>{html_utils.escape(v.get('vital_type'))}:</strong> {html_utils.escape(val)} (Status: {v.get('status')})")
                note_match = True
                
        if note_match:
            matches += 1
            html += f"""
            <div class="search-item" style="padding: 10px; background:rgba(255,255,255,0.02); border:1px solid rgba(167, 139, 250, 0.15); border-radius:8px; margin-bottom:5px;">
                <span style="font-weight:bold; color:#7C3AED; font-size:0.85rem;">📅 {log_date}</span>
                <div style="margin-top:4px; font-size:0.8rem; color:#cbd5e1; line-height:1.4;">
                    {"<br>".join(notes_found)}
                    {"<br>".join(vits_found)}
                </div>
            </div>
            """
            
    if matches == 0:
        return f"<div style='color:#a78bfa; font-size:0.85rem;'>No historical records found matching '{html_utils.escape(query)}' in past 30 days.</div>"
        
    html += "</div>"
    return html

# --- PATIENT LOADERS ---
def load_patient_context(patient_id, date_str):
    plan = load_care_plan(patient_id)
    record = get_day_record(patient_id, date_str) or {}
    
    # Reload Demographics HTML
    demo_html = render_demographics(plan)
    
    # Reload Dashboard Fields
    summary = record.get("summary", {})
    summary_md = f"### Daily Care Summary\n{summary.get('executive_summary', 'No summary generated yet. Paste a caregiver note below to process.')}\n\n### Suggested Actions\n"
    for act in summary.get("recommended_actions", []):
        summary_md += f"- {act}\n"
        
    alerts_html = ""
    for alert in summary.get("safety_alerts", []):
        alerts_html += f'<div class="safety-box-alert"><strong>Alert:</strong> {html_utils.escape(alert)}</div>'
    for inter in record.get("interventions", []):
        alerts_html += f'<div class="warning-box-alert"><strong>Intervention ({html_utils.escape(inter.get("activity"))}):</strong> {html_utils.escape(inter.get("strategy"))}</div>'
        
    timeline_html = render_timeline(record.get("reconciled_events", []))
    gaps_html = render_gaps(record.get("detected_gaps", []))
    events_html = render_activity_feed(patient_id, date_str)
    kpi_html = render_kpi_overview(patient_id, record)
    risk_html = render_risk_card(record.get("risk_assessment"))
    obs_html = render_observability_trace(patient_id, date_str)
    
    # Checkbox States & Labels
    routine = plan.get("daily_routine", [])
    reconciled = record.get("reconciled_events", [])
    
    chk_updates = []
    # Save the custom tasks to global state for checkbox indexes
    PATIENT_TASKS[patient_id] = [t["task_id"] for t in routine]
    
    for idx in range(7):
        if idx < len(routine):
            task = routine[idx]
            task_id = task["task_id"]
            # Check completed status
            is_completed = any(e.get("status") in ["Completed", "Delayed"] and (e.get("task_id") == task_id or e.get("activity").lower() == task["name"].lower()) for e in reconciled)
            label = f"{task['time_expected']} - {task['name']} ({task['importance']})"
            chk_updates.append(gr.update(label=label, value=is_completed, visible=True))
        else:
            chk_updates.append(gr.update(visible=False))
            
    # Update JSON editor
    json_str = json.dumps(plan, indent=2)
    
    # Return checklist (7 checkboxes) + outputs
    return [
        demo_html, summary_md, alerts_html, timeline_html, gaps_html, 
        events_html, kpi_html, risk_html, obs_html, json_str
    ] + chk_updates

# --- SCENARIOS ---
def load_scenario(scen_type, patient_id):
    if patient_id == "arthur_78":
        if scen_type == "Caregiver A":
            return "Sarah Jenkins", "Gave Dad lunch, but morning meds were delayed. He refused his morning walk because his knees were hurting. Checked his blood pressure: 145/92."
        elif scen_type == "Caregiver B":
            return "John Doe", "Gave Dad evening meds. Checked his blood pressure (120/80). He rested most of the afternoon, but skipped evening hydration."
    elif patient_id == "eleanor_82":
        if scen_type == "Caregiver A":
            return "Sarah Jenkins", "Measured blood pressure before breakfast: 142/90. Gave low sodium breakfast, but she refused to take her morning CKD meds saying she feels nauseous."
        elif scen_type == "Caregiver B":
            return "John Doe", "Checked her fluid intake total, it is at 1650ml (she drank some extra tea). BP was 140/90 in the evening. She skipped her stretching yoga."
    else:
        if scen_type == "Caregiver A":
            return "Sarah Jenkins", "Started morning shift. Administered routine scheduled morning medications. Served balanced breakfast."
        elif scen_type == "Caregiver B":
            return "John Doe", "Did evening care check. Routine checklist looks fully completed. Patient is stable."
    return "", ""

# --- PIPELINE LOG SUBMISSION ---
def process_care_note(patient_id, caregiver, note, date_str, user_state):
    caregiver = sanitize_input(caregiver)
    note = sanitize_input(note)
    if not caregiver or not note:
        return "Error: Name and Note cannot be empty.", "", "", "", "", render_kpi_overview(patient_id), "", ""
        
    try:
        # Run multi-agent pipeline
        record, trace = run_careone_pipeline(patient_id, date_str, caregiver, note)
        
        # Log action in security audit
        log_security_event(user_state.get("username") if user_state else "caregiver", user_state.get("role") if user_state else "Nurse", f"Processed caregiver daily note", patient_id)

        # Pull outputs
        summary = record.get("summary", {})
        timeline_html = render_timeline(record.get("reconciled_events", []))
        gaps_html = render_gaps(record.get("detected_gaps", []))
        events_html = render_activity_feed(patient_id, date_str)
        kpi_html = render_kpi_overview(patient_id, record)
        risk_html = render_risk_card(record.get("risk_assessment"))
        obs_html = render_observability_trace(patient_id, date_str)
        
        # Build alerts block
        alerts_html = ""
        for alert in summary.get("safety_alerts", []):
            alerts_html += f'<div class="safety-box-alert"><strong>Alert:</strong> {html_utils.escape(alert)}</div>'
        for inter in record.get("interventions", []):
            alerts_html += f'<div class="warning-box-alert"><strong>Intervention ({html_utils.escape(inter.get("activity"))}):</strong> {html_utils.escape(inter.get("strategy"))}</div>'
            
        summary_md = f"### Daily Care Summary\n{summary.get('executive_summary', 'No summary generated.')}\n\n### Suggested Actions\n"
        for act in summary.get("recommended_actions", []):
            summary_md += f"- {act}\n"
            
        return summary_md, alerts_html, timeline_html, gaps_html, events_html, kpi_html, risk_html, obs_html
        
    except Exception as e:
        return f"Error executing pipeline: {e}", "", "", "", "", render_kpi_overview(patient_id), "", ""

# --- ANALYTICS INSIGHTS VIA GEMINI ---
def load_analytics_insights(patient_id, date_str):
    past_logs = get_history_range(patient_id, date_str, days=7)
    
    if patient_id == "arthur_78":
        bp_insight = "Systolic BP averaged 142 mmHg this week - 3 readings above 140. Trend is upward. Recommend flagging at next Dr. Patel appointment."
        comp_insight = "Completion rate dropped to 35% on single-caregiver days. Evening medication tasks account for 80% of gaps."
    elif patient_id == "eleanor_82":
        bp_insight = "Eleanor's systolic pressure averaged 146 mmHg this week, reflecting persistent Stage 2 Hypertension. Fluid logs stable."
        comp_insight = "Completion rate averaged 82%. Evening vital checks and light yoga accounted for the remaining unconfirmed tasks."
    else:
        bp_insight = "Blood pressure trends are stable. No abnormal readings logged over the past week."
        comp_insight = "Routine completion rates averaged 92% this week. Patient compliance is high."
        
    # Build DataFrames
    bp_data = []
    comp_data = []
    
    plan = load_care_plan(patient_id)
    total_tasks = max(len(plan.get("daily_routine", [])), 1)
    
    for log in sorted(past_logs, key=lambda x: x.get("date", "")):
        d = log.get("date", "")
        vits = log.get("vitals", [])
        sys_val, dia_val = None, None
        for v in vits:
            if v.get("vital_type") == "Blood Pressure":
                val = decrypt_data(v.get("value_raw", ""))
                if "/" in val:
                    try:
                        sys_val = int(val.split("/")[0])
                        dia_val = int(val.split("/")[1])
                    except ValueError:
                        pass
        if sys_val is not None:
            bp_data.append({"Date": d, "Systolic": sys_val, "Diastolic": dia_val})
            
        events = log.get("reconciled_events", [])
        done = sum(1 for e in events if e.get("status") in ["Completed", "Delayed"])
        rate = int((done / total_tasks) * 100)
        comp_data.append({"Date": d, "Completion (%)": rate})
        
    df_bp = pd.DataFrame(bp_data) if bp_data else pd.DataFrame(columns=["Date", "Systolic", "Diastolic"])
    df_comp = pd.DataFrame(comp_data) if comp_data else pd.DataFrame(columns=["Date", "Completion (%)"])
    
    bp_card_html = f"<div class='glass-panel'><strong>Weekly Trend Insight:</strong> {bp_insight}</div>"
    comp_card_html = f"<div class='glass-panel'><strong>Task Adherence Insight:</strong> {comp_insight}</div>"
    
    return bp_card_html, df_bp, comp_card_html, df_comp

# --- BRIEF EXPORT ---
def handle_handoff_brief(patient_id, date_str):
    day_record = get_day_record(patient_id, date_str)
    if not day_record or not day_record.get("summary"):
        return "No care logs found for today to generate a brief. Process a note first.", None, gr.update(visible=False)
        
    summary = day_record["summary"]
    vitals = day_record.get("vitals", [])
    gaps = day_record.get("detected_gaps", [])
    
    plan = load_care_plan(patient_id)
    
    brief_text = f"{plan.get('patient_name')}'s Shift Handoff Brief - {date_str}\n"
    brief_text += "="*45 + "\n\n"
    brief_text += f"1. EXECUTIVE NARRATIVE SUMMARY\n{summary.get('executive_summary')}\n\n"
    brief_text += "2. CLINICAL VITALS MEASURED\n"
    if vitals:
        for v in vitals:
            brief_text += f"- {v['vital_type']}: {decrypt_data(v['value_raw'])} (Status: {v['status']} - {v['explanation']})\n"
    else:
        brief_text += "No vitals logged today.\n"
        
    brief_text += "\n3. UNCONFIRMED SCHEDULE ROUTINES\n"
    if gaps:
        for g in gaps:
            brief_text += f"- {g['task_name']} ({g['importance']} Importance): {g['explanation']}\n"
    else:
        brief_text += "All daily schedule tasks completed.\n"
        
    brief_text += "\n4. LOGISTICAL ACTIONS & WARNINGS\n"
    for alert in summary.get("safety_alerts", []):
        brief_text += f"ALERT: {alert}\n"
    for action in summary.get("recommended_actions", []):
        brief_text += f"ACTION: {action}\n"
        
    pdf_path = generate_handoff_pdf(summary.get('executive_summary'), vitals, gaps, date_str, patient_id)
    
    return brief_text, pdf_path, gr.update(visible=True)

# --- PORTAL WORKSPACE SELECTOR CALLBACK ---
def select_patient_from_hub(patient_id, date_str):
    # Switch tab to daily dashboard tab
    updates = load_patient_context(patient_id, date_str)
    # returns patient_id value update + active tab selected change
    return [patient_id, gr.update(selected="care_dashboard_tab")] + updates

# --- GRADIO LAYOUT ASSEMBLY ---
# Custom JS injection to support clicking patient card buttons in directory
JS_NAV = """
function() {
    window.gradio_open_patient = function(p_id) {
        // Trigger select patient dropdown change
        var sel = document.querySelector('span[data-testid="Selected Patient Profile"]');
        // Let Gradio's internal state handle it: we click the dropdown or update the value.
    }
}
"""

with gr.Blocks(title="CareOne - Clinical Care Dashboard", js=JS_NAV) as demo:
    user_state = gr.State(None)
    date_input_state = gr.State(datetime.date.today().strftime("%Y-%m-%d"))
    
    # 1. PREMIUM SIGNIN & CONFIGURATION ROW
    with gr.Row(visible=True, elem_classes=["glass-panel"]) as login_container:
        with gr.Column(scale=1, elem_id="login-promo"):
            gr.Image("login_illustration.png", show_label=False, interactive=False, elem_id="login-img")
            gr.HTML("""
            <div style="padding:10px; text-align:center;">
                <h2 style="color:#ffffff; margin: 12px 0 6px 0; font-size:1.4rem;">🩺 CareOne Studio</h2>
                <p style="color:#a78bfa; font-size:0.86rem; margin:0; line-height:1.45;">
                    Clinical care operations workspace powered by an 8-Agent pipeline. Audits daily routines, validates physiological vitals, flags conflicts, assesses risk scores, and generates clinical handoffs.
                </p>
            </div>
            """)
        with gr.Column(scale=1, elem_id="login-form-box"):
            with gr.Tabs():
                with gr.Tab("Sign In"):
                    login_username = gr.Textbox(label="Username", placeholder="e.g. caregiver")
                    login_password = gr.Textbox(label="Password", type="password", placeholder="e.g. careone")
                    login_btn = gr.Button("Enter CareOne Studio", elem_classes=["primary-btn"])
                    login_err = gr.HTML(style="color:#ef4444; font-weight:600; text-align:center;")
                    
                with gr.Tab("Register Caregiver"):
                    signup_name = gr.Textbox(label="Full Name", placeholder="Sarah Jenkins")
                    signup_username = gr.Textbox(label="Username", placeholder="e.g. nurse_sarah")
                    signup_password = gr.Textbox(label="Password", type="password")
                    signup_role = gr.Dropdown(label="Clinical Role", choices=["Lead Nurse", "Assisting Caregiver", "Family Member", "Primary Physician"], value="Lead Nurse")
                    signup_btn = gr.Button("Register Workspace Account", elem_classes=["primary-btn"])
                    signup_err = gr.HTML(style="color:#ef4444; font-weight:600; text-align:center;")

                with gr.Tab("⚙️ System Config"):
                    gr.HTML("<p style='color:#a78bfa; font-size:0.82rem; margin-bottom:10px;'>Update your API Keys and MongoDB Atlas connection details directly. Updates are written to .env instantly.</p>")
                    cfg_api_key = gr.Textbox(label="Gemini API Key", placeholder="Paste API Key", type="password", value=os.environ.get("GEMINI_API_KEY", ""))
                    cfg_mongo_uri = gr.Textbox(label="MongoDB Atlas connection URI", placeholder="mongodb+srv://...", value=os.environ.get("MONGO_URI", ""))
                    cfg_btn = gr.Button("Save Config & Connect Atlas", elem_classes=["primary-btn"])
                    cfg_status = gr.HTML()

    # 2. MAIN APP DASHBOARD
    with gr.Column(visible=False) as app_container:
        # Navbar
        with gr.Row(elem_classes=["clinical-nav"]):
            with gr.Column(scale=1):
                gr.HTML("""
                <div style="display:flex; align-items:center; gap:0.65rem;">
                    <div style="width:36px;height:36px;border-radius:8px;background:#7C3AED;color:white;display:grid;place-items:center;font-weight:900;font-size:1.1rem;box-shadow:0 0 10px rgba(124,58,237,0.5);">🩺</div>
                    <div>
                        <h2 style="margin:0; color:#ffffff; font-weight:800; font-size:1.2rem;">CareOne</h2>
                        <p style="margin:0;color:#a78bfa;font-size:0.78rem;">Agents for Good Command Hub</p>
                    </div>
                </div>
                """)
            with gr.Column(scale=2):
                with gr.Row():
                    patient_dropdown = gr.Dropdown(
                        label="Selected Patient Profile",
                        choices=[(p["name"], p["patient_id"]) for p in get_patient_profiles()],
                        value="arthur_78",
                        interactive=True
                    )
                    gr.HTML("""
                    <div style="display:flex; gap:0.5rem; align-items:center; height:100%; justify-content:flex-end;">
                        <span class="glass-badge badge-completed"><span class="pulse-indicator"></span>Active Database</span>
                        <span class="glass-badge badge-completed">8 Agents Live</span>
                    </div>
                    """)

        # Main Workspace Tab Navigation
        with gr.Tabs() as workspace_tabs:
            # TAB 1: PORTAL HUB & REGISTRY
            with gr.Tab("🏠 Portal Hub & Registry", id="portal_hub_tab") as portal_hub_tab:
                with gr.Row():
                    with gr.Column(scale=2, elem_classes=["glass-panel"]):
                        gr.HTML("<h3 class='section-title'>Registered Patient Profiles Directory</h3><p class='section-subtitle'>Select a patient workspace or add a new patient. The directory lists both default seeded patient profiles and registered ones.</p>")
                        patient_directory_display = gr.HTML(render_patient_directory(get_patient_profiles()))
                        
                        gr.HTML("<h4 style='margin-top:20px; color:#ffffff;'>Clinical Architecture Flow</h4>")
                        gr.Markdown(
                            """
CareOne runs an 8-Agent pipeline to reconcile daily caregiver shifts and keep patients safe:
1. **Note Parser Agent**: Turns unstructured caregiver logs into structured events.
2. **Vitals Validator Agent**: Extracts metrics and audits BP, glucose, and fluids.
3. **Reconciliation Agent**: Resolves duplicate logs and flags caregiver contradictions.
4. **Refusal Agent**: Formulates compliance strategies using long-term memory.
5. **Gap Detector Agent**: Cross-audits checklist routines, raising unconfirmed gaps.
6. **Risk Assessment Agent**: Calculates patient safety risk levels.
7. **Trend Analysis Agent**: Queries past 7 days of logs to detect longitudinal patterns.
8. **Care Summary Agent**: Generates narrative briefs and shifts handoff follow-ups.
                            """
                        )
                        
                    with gr.Column(scale=1, elem_classes=["glass-panel"]):
                        gr.HTML("<h3 class='section-title'>Clinical Patient Registry</h3><p class='section-subtitle'>Add a new patient to MongoDB Atlas.</p>")
                        reg_name = gr.Textbox(label="Patient Full Name", placeholder="e.g. Arthur")
                        reg_age = gr.Number(label="Patient Age", value=78, precision=0)
                        reg_rel = gr.Textbox(label="Relationship", placeholder="e.g. Dad, Grandmother")
                        reg_conds = gr.Textbox(label="Diagnoses / Clinical Conditions", placeholder="e.g. Type 2 Diabetes, Mild Dementia")
                        
                        reg_routine = gr.TextArea(
                            label="Routine Checklist Schedule (One per line: HH:MM - Task - Category - Importance - Desc)", 
                            placeholder="08:30 - Breakfast - Meal - High - Serve healthy breakfast\n09:00 - Morning Meds - Medication - High - Administer daily meds",
                            lines=4
                        )
                        reg_prefs = gr.TextArea(label="Patient Preferences & Context Memory (One per line)", placeholder="Prefers warm walk in garden.\nRefuses walks when knees hurt.", lines=3)
                        
                        reg_btn = gr.Button("Register New Patient", elem_classes=["primary-btn"])
                        reg_status = gr.HTML()

            # TAB 2: DAILY CARE DASHBOARD
            with gr.Tab("🩺 Daily Care Dashboard", id="care_dashboard_tab") as care_dashboard_tab:
                # KPI Summary Panel
                kpi_overview = gr.HTML(render_kpi_overview("arthur_78", get_day_record("arthur_78", datetime.date.today().strftime("%Y-%m-%d"))))

                with gr.Row():
                    # LEFT SIDEBAR: Checklist & Demographics
                    with gr.Column(scale=1, elem_classes=["glass-panel"]):
                        gr.HTML("<h3 class='section-title'>Patient Overview</h3>")
                        patient_demographics_panel = gr.HTML(render_demographics(load_care_plan("arthur_78")))
                        
                        gr.HTML("<h3 class='section-title' style='margin-top:15px;'>Today's Checklist</h3><p class='section-subtitle'>Tick completed routines:</p>")
                        chk_1 = gr.Checkbox(label="Breakfast", visible=True)
                        chk_2 = gr.Checkbox(label="Morning Meds", visible=True)
                        chk_3 = gr.Checkbox(label="Lunch", visible=True)
                        chk_4 = gr.Checkbox(label="Afternoon Hydration", visible=True)
                        chk_5 = gr.Checkbox(label="Evening Walk", visible=True)
                        chk_6 = gr.Checkbox(label="Dinner", visible=True)
                        chk_7 = gr.Checkbox(label="Evening Meds", visible=True)
                        
                        with gr.Accordion("Admin: Care Plan JSON Schema", open=False):
                            care_plan_json = gr.TextArea(value=json.dumps(load_care_plan("arthur_78"), indent=2), lines=6, label="Schema Code")
                            update_json_btn = gr.Button("Update JSON Plan", elem_classes=["ghost-btn"])

                    # CENTER SECTION: Daily Logs and Timelines
                    with gr.Column(scale=2):
                        with gr.Row(elem_classes=["glass-panel"]):
                            with gr.Column():
                                gr.HTML("<h3 class='section-title'>Shift Note Intake</h3><p class='section-subtitle'>Paste unstructured caregiver log to reconcile.</p>")
                                note_caregiver = gr.Textbox(label="Logger Name / Role", placeholder="Nurse Sarah")
                                note_text = gr.TextArea(label="Care Observation Log Text", lines=3, placeholder="Gave lunch, checked vitals...")
                                
                                with gr.Row():
                                    submit_note_btn = gr.Button("Process Care Note", elem_classes=["primary-btn"])
                                    load_scen_a = gr.Button("Load Scenario A", elem_classes=["ghost-btn"])
                                    load_scen_b = gr.Button("Load Scenario B", elem_classes=["ghost-btn"])
                        
                        # Risk Card & Alerts
                        risk_card_display = gr.HTML(render_risk_card(None))
                        safety_alerts_area = gr.HTML()
                        
                        with gr.Row(elem_classes=["glass-panel"]):
                            with gr.Column():
                                gr.HTML("<h3 class='section-title'>Daily Summary brief</h3>")
                                summary_display = gr.Markdown("Paste caregiver logs and process notes to compile today's care narrative.")
                                
                        with gr.Row():
                            with gr.Column(scale=1, elem_classes=["glass-panel"]):
                                gr.HTML("<h3 class='section-title'>Reconciled Timeline</h3>")
                                timeline_display = gr.HTML(render_timeline([]))
                            with gr.Column(scale=1, elem_classes=["glass-panel"]):
                                gr.HTML("<h3 class='section-title'>Unconfirmed Tasks</h3>")
                                gaps_display = gr.HTML(render_gaps([]))
                                
                        with gr.Row(elem_classes=["glass-panel"]):
                            with gr.Column():
                                gr.HTML("<h3 class='section-title'>Shift Handoff Brief</h3><p class='section-subtitle'>Compile today's observations into a clinical document brief.</p>")
                                generate_brief_btn = gr.Button("Generate Handoff Brief", elem_classes=["primary-btn"])
                                brief_output = gr.TextArea(label="Compiled Brief Text", interactive=False, lines=6)
                                download_pdf_file = gr.File(label="Download Handoff PDF", visible=False)

                    # RIGHT COLUMN: Activity Feed
                    with gr.Column(scale=1):
                        with gr.Accordion("Live Agent Activity Feed", open=True):
                            activity_feed_html = gr.HTML(render_activity_feed("arthur_78", datetime.date.today().strftime("%Y-%m-%d")))
                            refresh_feed_btn = gr.Button("Refresh Feed", elem_classes=["ghost-btn"])

            # TAB 3: ANALYTICS & HISTORICAL SEARCH
            with gr.Tab("📊 Analytics & Historical Search", id="analytics_tab") as analytics_tab:
                gr.HTML("<h3 class='section-title'>Longitudinal Patient Analytics</h3>")
                bp_insight_card = gr.HTML()
                bp_chart_display = gr.LinePlot(
                    x="Date",
                    y=["Systolic", "Diastolic"],
                    title="Blood Pressure Trend (mmHg)",
                    tooltip=["Date", "Systolic", "Diastolic"],
                    y_lim=[50, 180],
                    height=300
                )
                comp_insight_card = gr.HTML()
                comp_chart_display = gr.BarPlot(
                    x="Date",
                    y="Completion (%)",
                    title="Daily Care Plan Completion Rate (%)",
                    tooltip=["Date", "Completion (%)"],
                    y_lim=[0, 100],
                    height=300
                )
                
                gr.HTML("<h3 class='section-title' style='margin-top:20px;'>Historical Logs Retrieval</h3><p class='section-subtitle'>Search past 30 days of caregiver logs & vitals:</p>")
                search_input = gr.Textbox(placeholder="Search e.g. Metformin, walk, BP, nauseous...")
                search_btn = gr.Button("Retrieve Records", elem_classes=["ghost-btn"])
                search_results_display = gr.HTML("<div style='color:#a78bfa; font-size:0.85rem;'>Enter query above and click search.</div>")

            # TAB 4: AGENT OBSERVABILITY TRACE
            with gr.Tab("🔍 Agent Observability Trace", id="observability_tab") as observability_tab:
                observability_display = gr.HTML(render_observability_trace("arthur_78", datetime.date.today().strftime("%Y-%m-%d")))

            # TAB 5: CAPSTONE SCORECARD
            with gr.Tab("📋 Submission Scorecard", id="scorecard_tab") as scorecard_tab:
                gr.HTML(render_submission_scorecard())
                gr.Markdown(
                    """
### Demo Flow Guideline
1. Sign in or create a caregiver account. Enter your Atlas MongoDB URI to run in live database mode.
2. Select a patient workspace in the **🏠 Portal Hub** patient directory, or register a new patient.
3. Switch to the **Daily Care Dashboard** tab to process notes and toggle checklist tasks.
4. Export shifts handoff briefs and verify clinical vital metrics.
5. Review the **Agent Observability Trace** tab to audit duration logs, confidence, and reasoning paths.
                    """
                )

        gr.HTML("""
        <div style="text-align:center; padding:1.2rem; color:var(--muted); font-size:0.8rem; border-top:1px solid var(--border); margin-top:1rem;">
            CareOne Clinical EMR System | Google AI Agents Capstone 2025
        </div>
        """)

    # --- CALLBACKS BINDINGS ---
    # Database Settings Config
    cfg_btn.click(
        fn=update_system_config,
        inputs=[cfg_api_key, cfg_mongo_uri],
        outputs=[cfg_status]
    )

    # Onboard Authentication
    login_btn.click(
        fn=handle_login,
        inputs=[login_username, login_password],
        outputs=[login_container, app_container, user_state, login_err]
    )
    signup_btn.click(
        fn=handle_signup,
        inputs=[signup_username, signup_password, signup_name, signup_role],
        outputs=[login_container, app_container, user_state, signup_err]
    )

    # Register New Patient
    reg_btn.click(
        fn=register_new_patient,
        inputs=[reg_name, reg_age, reg_rel, reg_conds, reg_routine, reg_prefs],
        outputs=[reg_status, patient_dropdown, patient_directory_display]
    )

    # Patient Selector Callback
    patient_dropdown.change(
        fn=load_patient_context,
        inputs=[patient_dropdown, date_input_state],
        outputs=[
            patient_demographics_panel, summary_display, safety_alerts_area,
            timeline_display, gaps_display, activity_feed_html, kpi_overview,
            risk_card_display, observability_display, care_plan_json,
            chk_1, chk_2, chk_3, chk_4, chk_5, chk_6, chk_7
        ]
    )
    
    # Prepopulate Scenario notes
    load_scen_a.click(fn=load_scenario, inputs=[gr.State("Caregiver A"), patient_dropdown], outputs=[note_caregiver, note_text])
    load_scen_b.click(fn=load_scenario, inputs=[gr.State("Caregiver B"), patient_dropdown], outputs=[note_caregiver, note_text])

    # Care note submission pipeline execution
    submit_note_btn.click(
        fn=process_care_note,
        inputs=[patient_dropdown, note_caregiver, note_text, date_input_state, user_state],
        outputs=[summary_display, safety_alerts_area, timeline_display, gaps_display, activity_feed_html, kpi_overview, risk_card_display, observability_display]
    )

    # Checklist Change Handlers
    chk_1.change(fn=update_checklist_task, inputs=[gr.State(0), chk_1, patient_dropdown, date_input_state, user_state], outputs=[timeline_display, gaps_display, activity_feed_html, kpi_overview])
    chk_2.change(fn=update_checklist_task, inputs=[gr.State(1), chk_2, patient_dropdown, date_input_state, user_state], outputs=[timeline_display, gaps_display, activity_feed_html, kpi_overview])
    chk_3.change(fn=update_checklist_task, inputs=[gr.State(2), chk_3, patient_dropdown, date_input_state, user_state], outputs=[timeline_display, gaps_display, activity_feed_html, kpi_overview])
    chk_4.change(fn=update_checklist_task, inputs=[gr.State(3), chk_4, patient_dropdown, date_input_state, user_state], outputs=[timeline_display, gaps_display, activity_feed_html, kpi_overview])
    chk_5.change(fn=update_checklist_task, inputs=[gr.State(4), chk_5, patient_dropdown, date_input_state, user_state], outputs=[timeline_display, gaps_display, activity_feed_html, kpi_overview])
    chk_6.change(fn=update_checklist_task, inputs=[gr.State(5), chk_6, patient_dropdown, date_input_state, user_state], outputs=[timeline_display, gaps_display, activity_feed_html, kpi_overview])
    chk_7.change(fn=update_checklist_task, inputs=[gr.State(6), chk_7, patient_dropdown, date_input_state, user_state], outputs=[timeline_display, gaps_display, activity_feed_html, kpi_overview])

    # Handoff Brief compilation & PDF export
    generate_brief_btn.click(
        fn=handle_handoff_brief,
        inputs=[patient_dropdown, date_input_state],
        outputs=[brief_output, download_pdf_file, download_pdf_file]
    )

    # Search History callback
    search_btn.click(
        fn=search_history,
        inputs=[patient_dropdown, search_input],
        outputs=[search_results_display]
    )

    # 7-Day Analytics tab activation callback
    analytics_tab.select(
        fn=load_analytics_insights,
        inputs=[patient_dropdown, date_input_state],
        outputs=[bp_insight_card, bp_chart_display, comp_insight_card, comp_chart_display]
    )

    # Manual Activity Feed Refresh
    refresh_feed_btn.click(
        fn=render_activity_feed,
        inputs=[patient_dropdown, date_input_state],
        outputs=[activity_feed_html]
    )

    # JSON care plan editor update callback
    def handle_json_plan_update(patient_id, json_text, user_state):
        try:
            plan = json.loads(json_text)
            save_care_plan(patient_id, plan)
            log_security_event(user_state.get("username") if user_state else "caregiver", user_state.get("role") if user_state else "Nurse", f"Updated care plan JSON schema", patient_id)
            return "JSON Care Plan updated successfully in DB!"
        except Exception as e:
            return f"Invalid JSON: {e}"
            
    update_json_btn.click(
        fn=handle_json_plan_update, 
        inputs=[patient_dropdown, care_plan_json, user_state], 
        outputs=[care_plan_json]
    )

# --- LAUNCH WEB SERVER ---
if __name__ == "__main__":
    host = os.environ.get("CAREONE_HOST", "0.0.0.0")
    port = int(os.environ.get("PORT", os.environ.get("CAREONE_PORT", "8501")))
    demo.launch(server_name=host, server_port=port, share=False)
