import datetime
import os
from pathlib import Path
from typing import Any

from dotenv import load_dotenv
from fastapi import FastAPI, HTTPException
from fastapi.responses import FileResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from fpdf import FPDF
from pydantic import BaseModel

import src.db as db
from src.agents.gap_detector import GapDetectorAgent
from src.memory import (
    get_agent_events,
    get_day_record,
    get_history_range,
    load_care_plan,
    log_agent_event,
    save_day_record,
    get_patient_profiles,
    delete_patient_profile,
)
from src.pipeline import run_careone_pipeline

load_dotenv()
# db.seed_database()

ROOT = Path(__file__).resolve().parent
STATIC_DIR = ROOT / "studio"

app = FastAPI(
    title="CareOne Studio",
    description="Deployable SaaS frontend for CareOne.",
    version="1.0.0",
)
app.mount("/static", StaticFiles(directory=STATIC_DIR), name="static")


class LoginRequest(BaseModel):
    username: str
    password: str


class SignupRequest(BaseModel):
    name: str
    username: str
    password: str
    role: str = "Caregiver"


class ResetRequest(BaseModel):
    username: str
    password: str


class NoteRequest(BaseModel):
    patient_id: str = "ananya_78"
    caregiver: str
    note: str
    date: str | None = None


class ChecklistRequest(BaseModel):
    patient_id: str = "ananya_78"
    task_id: str
    checked: bool
    caregiver: str = "Lead Caregiver"
    date: str | None = None


class PatientRequest(BaseModel):
    patient_id: str
    name: str
    age: int
    relationship: str
    conditions: str
    preferences: list[str] = []
    daily_routine: list[dict] = []


class ConfigRequest(BaseModel):
    mongo_uri: str
    db_name: str
    gemini_key: str | None = None


FALLBACK_USERS: dict[str, dict[str, str]] = {
    "caregiver": {
        "password": "careone",
        "name": "Sarah Jenkins",
        "role": "Lead Nurse",
    }
}



def today() -> str:
    return datetime.date.today().strftime("%Y-%m-%d")


def clean_record(record: dict[str, Any] | None, date_str: str) -> dict[str, Any]:
    if record:
        return record
    return {
        "date": date_str,
        "raw_notes": [],
        "reconciled_events": [],
        "vitals": [],
        "conflicts": [],
        "interventions": [],
        "detected_gaps": [],
        "trends": {},
        "summary": {},
    }


def build_kpis(record: dict[str, Any], plan: dict[str, Any]) -> dict[str, Any]:
    events = record.get("reconciled_events", [])
    vitals = record.get("vitals", [])
    gaps = record.get("detected_gaps", [])
    conflicts = record.get("conflicts", [])
    completed = sum(1 for ev in events if ev.get("status") in ["Completed", "Delayed"])
    routine = plan.get("daily_routine", [])
    total = max(len(routine), 1)
    return {
        "completion": int((completed / total) * 100),
        "completed": completed,
        "total": total,
        "open_risks": len(gaps),
        "high_risks": sum(
            1
            for gap in gaps
            if str(gap.get("importance", "")).lower() == "high"
            or str(gap.get("confidence_score", "")).lower() == "high"
        ),
        "vitals": len(vitals),
        "vital_alerts": sum(
            1
            for vital in vitals
            if vital.get("status", "").lower() not in ["normal", "ok", "stable"]
        ),
        "conflicts": len(conflicts),
    }


def build_state(patient_id: str = "ananya_78", date_str: str | None = None) -> dict[str, Any]:
    date_str = date_str or today()
    record = clean_record(get_day_record(patient_id, date_str), date_str)
    history = get_history_range(patient_id, date_str, days=7)
    plan = load_care_plan(patient_id)
    return {
        "date": date_str,
        "patient": {
            "patient_id": patient_id,
            "name": plan.get("patient_name", "Ananya"),
            "age": plan.get("age", 78),
            "conditions": plan.get("conditions", "Diabetes Type 2, mild dementia, mobility risk"),
            "care_goal": "Reduce unconfirmed daily care tasks and improve shift handoff quality.",
        },
        "routine": plan.get("daily_routine", []),
        "record": record,
        "kpis": build_kpis(record, plan),
        "agent_events": get_agent_events(patient_id, date_str),
        "analytics": build_analytics(patient_id, history),
    }


def build_analytics(patient_id: str, history: list[dict[str, Any]]) -> dict[str, Any]:
    plan = load_care_plan(patient_id)
    routine = plan.get("daily_routine", [])
    total_routine = max(len(routine), 1)
    rows = []
    bp_points = []
    for log in sorted(history, key=lambda row: row.get("date", "")):
        done = sum(
            1
            for event in log.get("reconciled_events", [])
            if event.get("status") in ["Completed", "Delayed"]
        )
        rows.append(
            {
                "date": log.get("date", ""),
                "completion": int((done / total_routine) * 100),
            }
        )
        for vital in log.get("vitals", []):
            raw = vital.get("value_raw", "")
            if vital.get("vital_type") == "Blood Pressure" and "/" in raw:
                sys_val, dia_val = raw.split("/", 1)
                if sys_val.isdigit() and dia_val.isdigit():
                    bp_points.append(
                        {
                            "date": log.get("date", ""),
                            "systolic": int(sys_val),
                            "diastolic": int(dia_val),
                        }
                    )
    return {
        "completion": rows,
        "blood_pressure": bp_points,
        "insight": "Completion and vital trends are calculated from persisted 7-day care memory.",
    }


def demo_note(kind: str) -> dict[str, str]:
    if kind == "b":
        return {
            "caregiver": "Caregiver B (Night Shift)",
            "note": "Gave Dad evening meds. Checked his blood pressure (120/80). He rested most of the afternoon, but skipped evening hydration.",
        }
    return {
        "caregiver": "Caregiver A (Morning Shift)",
        "note": "Gave Dad lunch, but morning meds were delayed. He refused his morning walk because his knees were hurting. Checked his blood pressure: 145/92.",
    }


@app.get("/")
@app.get("/login")
@app.get("/auth")
@app.get("/dashboard")
@app.get("/studio")
@app.get("/agents")
@app.get("/memory")
@app.get("/analytics")
@app.get("/notifications")
@app.get("/settings")
@app.get("/profile")
def serve_spa_pages() -> FileResponse:
    return FileResponse(STATIC_DIR / "index.html")


@app.get("/styles.css")
def root_styles() -> FileResponse:
    return FileResponse(STATIC_DIR / "styles.css")


@app.get("/app.js")
def root_script() -> FileResponse:
    return FileResponse(STATIC_DIR / "app.js")


@app.get("/api/health")
def health() -> dict[str, Any]:
    return {"ok": True, "mode": "deterministic" if os.environ.get("CAREONE_LIVE_LLM", "0") != "1" else "live_llm"}


@app.post("/api/login")
def login(payload: LoginRequest) -> dict[str, Any]:
    db_conn = db.get_db()
    if db_conn is not None:
        user = db_conn.users.find_one({"username": payload.username})
        if user and user.get("password") == db.hash_password(payload.password):
            return {
                "ok": True,
                "user": {
                    "username": payload.username,
                    "name": user.get("name", payload.username),
                    "role": user.get("role", "Caregiver"),
                },
            }
    fallback = FALLBACK_USERS.get(payload.username)
    if fallback and fallback["password"] == payload.password:
        return {"ok": True, "user": {k: v for k, v in fallback.items() if k != "password"} | {"username": payload.username}}
    raise HTTPException(status_code=401, detail="Invalid credentials. Demo login is caregiver / careone.")


@app.post("/api/signup")
def signup(payload: SignupRequest) -> dict[str, Any]:
    if not payload.username or not payload.password or not payload.name:
        raise HTTPException(status_code=400, detail="Name, username, and password are required.")
    db_conn = db.get_db()
    if db_conn is not None:
        if db_conn.users.find_one({"username": payload.username}):
            raise HTTPException(status_code=409, detail="Username already exists.")
        db_conn.users.insert_one(
            {
                "username": payload.username,
                "password": db.hash_password(payload.password),
                "name": payload.name,
                "role": payload.role,
            }
        )
    else:
        FALLBACK_USERS[payload.username] = {
            "password": payload.password,
            "name": payload.name,
            "role": payload.role,
        }
    return {"ok": True, "user": {"username": payload.username, "name": payload.name, "role": payload.role}}


@app.post("/api/auth/reset-password")
def reset_password(payload: ResetRequest) -> dict[str, Any]:
    db_conn = db.get_db()
    if db_conn is not None:
        user = db_conn.users.find_one({"username": payload.username})
        if user:
            db_conn.users.update_one(
                {"username": payload.username},
                {"$set": {"password": db.hash_password(payload.password)}}
            )
            return {"ok": True, "message": "Password updated successfully in database."}
            
    if payload.username in FALLBACK_USERS:
        FALLBACK_USERS[payload.username]["password"] = payload.password
        return {"ok": True, "message": "Password updated successfully in fallback memory."}
        
    raise HTTPException(status_code=404, detail="Username not found.")


def update_env_file(mongo_uri: str, db_name: str, gemini_key: str | None = None):
    env_path = Path(__file__).resolve().parent / ".env"
    lines = []
    if env_path.exists():
        with open(env_path, "r", encoding="utf-8") as f:
            lines = f.readlines()
            
    updated_uri = False
    updated_db = False
    updated_key = False
    
    for i, line in enumerate(lines):
        if line.strip().startswith("MONGO_URI="):
            lines[i] = f'MONGO_URI="{mongo_uri}"\n'
            updated_uri = True
        elif line.strip().startswith("MONGO_DB_NAME="):
            lines[i] = f'MONGO_DB_NAME="{db_name}"\n'
            updated_db = True
        elif gemini_key and line.strip().startswith("GEMINI_API_KEY="):
            lines[i] = f'GEMINI_API_KEY="{gemini_key}"\n'
            updated_key = True
            
    if not updated_uri:
        lines.append(f'MONGO_URI="{mongo_uri}"\n')
    if not updated_db:
        lines.append(f'MONGO_DB_NAME="{db_name}"\n')
    if gemini_key and not updated_key:
        lines.append(f'GEMINI_API_KEY="{gemini_key}"\n')
        
    with open(env_path, "w", encoding="utf-8") as f:
        f.writelines(lines)


@app.get("/api/state")
def state(patient_id: str = "ananya_78", date: str | None = None) -> dict[str, Any]:
    return build_state(patient_id, date)


@app.get("/api/scenario/{kind}")
def scenario(kind: str) -> dict[str, str]:
    return demo_note(kind.lower())


@app.post("/api/process-note")
def process_note(payload: NoteRequest) -> dict[str, Any]:
    if not payload.caregiver or not payload.note:
        raise HTTPException(status_code=400, detail="Caregiver and note are required.")
    date_str = payload.date or today()
    record, trace = run_careone_pipeline(payload.patient_id, date_str, payload.caregiver, payload.note)
    return {"ok": True, "record": record, "trace": trace, "state": build_state(payload.patient_id, date_str)}


@app.post("/api/checklist")
def checklist(payload: ChecklistRequest) -> dict[str, Any]:
    date_str = payload.date or today()
    caregiver = payload.caregiver or "Lead Caregiver"
    status = "Completed" if payload.checked else "Skipped"
    record = clean_record(get_day_record(payload.patient_id, date_str), date_str)
    plan = load_care_plan(payload.patient_id)
    task = next((item for item in plan.get("daily_routine", []) if item.get("task_id") == payload.task_id), None)
    if not task:
        raise HTTPException(status_code=404, detail="Task not found in care plan.")

    found = False
    for event in record["reconciled_events"]:
        if event.get("task_id") == payload.task_id or event.get("activity", "").lower() == task.get("name", "").lower():
            event["status"] = status
            event["inferred_time"] = task.get("time_expected", "Unknown")
            event.setdefault("caregivers", [])
            if caregiver not in event["caregivers"]:
                event["caregivers"].append(caregiver)
            found = True
            break
    if not found:
        record["reconciled_events"].append(
            {
                "task_id": payload.task_id,
                "activity": task.get("name"),
                "inferred_time": task.get("time_expected"),
                "status": status,
                "caregivers": [caregiver],
                "notes": "Updated from CareOne Studio checklist.",
            }
        )

    detector = GapDetectorAgent()
    gaps = detector.detect_gaps(plan, record["reconciled_events"], f"Analysis date: {date_str}")
    record["detected_gaps"] = gaps.get("detected_gaps", [])
    save_day_record(payload.patient_id, date_str, record)
    log_agent_event(payload.patient_id, "Gaps Agent", f"Checklist updated: {task.get('name')} marked {status.lower()}")
    return {"ok": True, "state": build_state(payload.patient_id, date_str)}


@app.get("/api/handoff")
def handoff(patient_id: str = "ananya_78", date: str | None = None) -> JSONResponse:
    date_str = date or today()
    record = clean_record(get_day_record(patient_id, date_str), date_str)
    summary = record.get("summary", {})
    lines = [
        f"CareOne Handoff Brief - {date_str}",
        "",
        "Executive Summary",
        summary.get("executive_summary", "No summary has been generated yet."),
        "",
        "Vitals",
    ]
    for vital in record.get("vitals", []):
        lines.append(f"- {vital.get('vital_type')}: {vital.get('value_raw')} ({vital.get('status')})")
    if not record.get("vitals"):
        lines.append("- No vitals recorded.")
    lines.extend(["", "Unconfirmed Tasks"])
    for gap in record.get("detected_gaps", []):
        lines.append(f"- {gap.get('task_name')}: {gap.get('explanation')}")
    if not record.get("detected_gaps"):
        lines.append("- No unconfirmed tasks.")
    lines.extend(["", "Recommended Actions"])
    for action in summary.get("recommended_actions", []):
        lines.append(f"- {action}")
    return JSONResponse({"date": date_str, "brief": "\n".join(lines)})


@app.get("/api/handoff.pdf")
def handoff_pdf(patient_id: str = "ananya_78", date: str | None = None) -> FileResponse:
    date_str = date or today()
    record = clean_record(get_day_record(patient_id, date_str), date_str)
    plan = load_care_plan(patient_id)
    summary = record.get("summary", {})
    output_dir = ROOT / "data" / "briefs"
    output_dir.mkdir(parents=True, exist_ok=True)
    output_path = output_dir / f"CareOne_Handoff_{patient_id}_{date_str}.pdf"

    pdf = FPDF()
    pdf.add_page()
    pdf.set_auto_page_break(auto=True, margin=15)
    pdf.set_font("helvetica", "B", 18)
    pdf.set_text_color(15, 118, 110)
    pdf.cell(0, 10, "CareOne Clinical Shift Handoff", new_x="LMARGIN", new_y="NEXT")
    pdf.set_font("helvetica", "", 10)
    pdf.set_text_color(80, 80, 80)
    pdf.cell(0, 8, f"Patient: {plan.get('patient_name', patient_id)} | Date: {date_str}", new_x="LMARGIN", new_y="NEXT")
    pdf.ln(3)

    def section(title: str, body: str):
        pdf.set_font("helvetica", "B", 12)
        pdf.set_text_color(20, 78, 74)
        pdf.cell(0, 8, title, new_x="LMARGIN", new_y="NEXT")
        pdf.set_font("helvetica", "", 10)
        pdf.set_text_color(40, 50, 60)
        pdf.multi_cell(0, 5, body or "None recorded.")
        pdf.ln(2)

    section("Executive Summary", summary.get("executive_summary", "No summary has been generated yet."))
    vitals_text = "\n".join(
        f"- {v.get('vital_type')}: {v.get('value_raw')} ({v.get('status')})"
        for v in record.get("vitals", [])
    )
    section("Vitals", vitals_text)
    gaps_text = "\n".join(
        f"- {g.get('task_name')}: {g.get('explanation')}"
        for g in record.get("detected_gaps", [])
    )
    section("Unconfirmed Tasks", gaps_text)
    actions_text = "\n".join(f"- {a}" for a in summary.get("recommended_actions", []))
    section("Recommended Actions", actions_text)
    risk = record.get("risk_assessment", {})
    section("Risk Assessment", f"{risk.get('risk_level', 'Not calculated')}: {risk.get('description', 'No risk assessment yet.')}")

    pdf.output(str(output_path))
    return FileResponse(output_path, media_type="application/pdf", filename=output_path.name)


@app.get("/api/patients")
def get_patients() -> list[dict[str, Any]]:
    return get_patient_profiles()


@app.get("/api/pipeline-logs")
def get_pipeline_logs(patient_id: str, date: str | None = None) -> dict[str, Any]:
    date_str = date or today()
    db_conn = db.get_db()
    if db_conn is not None:
        doc = db_conn.pipeline_execution_logs.find_one({"patient_id": patient_id, "date": date_str})
        if doc:
            return {"ok": True, "trace": doc.get("trace", {})}
    # Fallback log loader
    try:
        import json
        trace_path = os.path.join("data", f"pipeline_execution_logs_{patient_id}.json")
        if os.path.exists(trace_path):
            with open(trace_path, "r", encoding="utf-8") as f:
                records = json.load(f)
                for r in reversed(records):
                    if r.get("date") == date_str:
                        return {"ok": True, "trace": r.get("trace", {})}
    except Exception:
        pass
    return {"ok": True, "trace": {}}


@app.post("/api/patients")
def create_patient(payload: PatientRequest) -> dict[str, Any]:
    from src.memory import save_care_plan, ensure_fallback_files
    plan = {
        "patient_name": payload.name,
        "age": payload.age,
        "relationship": payload.relationship,
        "conditions": payload.conditions,
        "preferences": payload.preferences,
        "daily_routine": payload.daily_routine
    }
    save_care_plan(payload.patient_id, plan)
    ensure_fallback_files(payload.patient_id)
    return {"ok": True, "patient": payload.dict()}


@app.delete("/api/patients/{patient_id}")
def delete_patient(patient_id: str) -> dict[str, Any]:
    res = delete_patient_profile(patient_id)
    return {"ok": res}


@app.get("/api/db-status")
def db_status() -> dict[str, Any]:
    from src.db import using_fallback, MONGO_URI, DB_NAME
    is_live = not using_fallback()
    return {
        "status": "connected" if is_live else "fallback",
        "uri": MONGO_URI,
        "db_name": DB_NAME
    }


@app.post("/api/config")
def save_config(payload: ConfigRequest) -> dict[str, Any]:
    success = db.reconnect(payload.mongo_uri, payload.db_name)
    if success:
        # db.seed_database()
        update_env_file(payload.mongo_uri, payload.db_name, payload.gemini_key)
        if payload.gemini_key:
            from src.config import reconfigure_api
            reconfigure_api(payload.gemini_key)
        return {"ok": True, "message": "Successfully connected to MongoDB Atlas and saved configuration."}
    else:
        raise HTTPException(
            status_code=400,
            detail="Failed to connect to MongoDB Atlas with the provided connection string."
        )


class HistoryQueryRequest(BaseModel):
    patient_id: str
    query: str

def get_offline_history_answer(query: str, history: list[dict], patient_id: str | None = None) -> str:
    query_lower = query.lower()
    
    # Try to load care plan if patient_id is provided
    plan = {}
    if patient_id:
        try:
            from src.memory import load_care_plan
            plan = load_care_plan(patient_id) or {}
        except Exception:
            pass

    # 1. Look up diagnosis/disease/conditions from care plan
    if any(k in query_lower for k in ["disease", "condition", "diagnosis", "illness", "sick"]):
        if plan:
            name = plan.get("patient_name", "The patient")
            conds = plan.get("conditions", "None declared")
            return f"Based on the clinical care plan, {name} is diagnosed with: {conds}."
        return "I could not retrieve the patient's diagnosed conditions in offline fallback mode."

    # 2. Look up age
    if "age" in query_lower or "how old" in query_lower:
        if plan:
            name = plan.get("patient_name", "The patient")
            age = plan.get("age", "N/A")
            return f"{name} is {age} years old."
        return "I could not retrieve the patient's age in offline fallback mode."

    # 3. Look up caregiver relationship
    if "relationship" in query_lower or "relation" in query_lower:
        if plan:
            name = plan.get("patient_name", "the patient")
            rel = plan.get("relationship", "Family")
            return f"The caregiver's relationship to {name} is: {rel}."

    # 4. Look up patient preferences
    if "preference" in query_lower or "like" in query_lower:
        if plan and plan.get("preferences"):
            name = plan.get("patient_name", "the patient")
            pref = ", ".join(plan.get("preferences", []))
            return f"Recorded preferences for {name}: {pref}."

    # 5. Look up blood pressure vitals
    if "blood pressure" in query_lower or "bp" in query_lower:
        flagged_bp_count = 0
        for day in history:
            for vital in day.get("vitals", []):
                if vital.get("vital_type") == "Blood Pressure" and vital.get("status", "").lower() not in ["normal", "ok", "stable"]:
                    flagged_bp_count += 1
        return f"Based on the local memory logs, blood pressure has been flagged as elevated or abnormal {flagged_bp_count} times in the last 30 days."
        
    # 6. Look up medication tracking
    if "medication" in query_lower or "meds" in query_lower:
        evening_meds_taken = None
        for day in history:
            for event in day.get("reconciled_events", []):
                if "med" in event.get("activity", "").lower() and "evening" in event.get("activity", "").lower():
                    if event.get("status") == "Completed":
                        evening_meds_taken = f"Yes, they took their evening medication on {day.get('date')} (Completed)."
                    else:
                        evening_meds_taken = f"According to the logs for {day.get('date')}, the evening medication was not confirmed (Status: {event.get('status')})."
                    break
            if evening_meds_taken:
                break
        return evening_meds_taken or "I could not find a confirmed evening medication entry in the recent care timeline."
        
    # 7. Look up last caregiver note
    if "last caregiver note" in query_lower or "last note" in query_lower or "caregiver note" in query_lower:
        for day in history:
            notes = day.get("raw_notes", [])
            if notes:
                note_data = notes[-1]
                cg = note_data.get("caregiver", "Unknown Caregiver")
                from src.security import decrypt_data
                try:
                    txt = decrypt_data(note_data.get("text", ""))
                except Exception:
                    txt = note_data.get("text", note_data.get("note", ""))
                return f"The last recorded caregiver note on {day.get('date')} says: \"{txt}\" (logged by {cg})."
        return "No caregiver notes have been recorded in the last 30 days."
        
    return "This is a deterministic fallback answer. To get real-time clinical history analysis via LLM, please configure your GEMINI_API_KEY and enable Gemini Live Mode."

@app.post("/api/history-query")
def history_query(payload: HistoryQueryRequest) -> dict[str, Any]:
    import json
    date_str = today()
    history = get_history_range(payload.patient_id, date_str, days=30)
    
    # Construct context
    history_context = []
    from src.security import decrypt_data
    for log in history:
        raw_notes_decrypted = []
        for note in log.get("raw_notes", []):
            try:
                txt = decrypt_data(note.get("text", ""))
            except Exception:
                txt = note.get("text", note.get("note", ""))
            raw_notes_decrypted.append({
                "caregiver": note.get("caregiver"),
                "note": txt
            })
            
        vitals_decrypted = []
        for v in log.get("vitals", []):
            try:
                val = decrypt_data(v.get("value_raw", ""))
            except Exception:
                val = v.get("value_raw", "")
            vitals_decrypted.append({
                "vital_type": v.get("vital_type"),
                "value_raw": val,
                "status": v.get("status")
            })

        history_context.append({
            "date": log.get("date"),
            "raw_notes": raw_notes_decrypted,
            "reconciled_events": [
                {
                    "activity": e.get("activity"),
                    "status": e.get("status"),
                    "inferred_time": e.get("inferred_time"),
                    "caregivers": e.get("caregivers", [])
                } for e in log.get("reconciled_events", [])
            ],
            "vitals": vitals_decrypted,
            "detected_gaps": [
                {
                    "task_name": g.get("task_name"),
                    "explanation": g.get("explanation"),
                    "importance": g.get("importance")
                } for g in log.get("detected_gaps", [])
            ]
        })
        
    try:
        if os.environ.get("CAREONE_LIVE_LLM", "0") != "1":
            return {"answer": get_offline_history_answer(payload.query, history_context, payload.patient_id)}
            
        from src.config import get_client, MODEL_NAME
        from google.genai import types
        
        client = get_client()
        prompt = (
            f"You are the CareOne History Query assistant. Your job is to answer the user's query about a patient's care history based on the provided 30-day history log context.\n"
            f"Patient ID: {payload.patient_id}\n"
            f"Current Date: {date_str}\n\n"
            f"30-Day Care History Context:\n{json.dumps(history_context, indent=2)}\n\n"
            f"User Query: {payload.query}\n\n"
            f"Provide a clear, helpful, natural language response answering the query based on the context. If the information is not found in the logs, state that politely."
        )
        config = types.GenerateContentConfig(
            temperature=0.2,
            system_instruction="You are CareOne's empathetic care history assistant. You summarize, query, and verify past daily reports, vitals, and checklists."
        )
        response = client.models.generate_content(
            model=MODEL_NAME,
            contents=prompt,
            config=config
        )
        return {"answer": response.text}
    except Exception as e:
        print(f"Error querying history: {e}")
        return {"answer": get_offline_history_answer(payload.query, history_context, payload.patient_id)}

@app.get("/api/history")
def get_history(patient_id: str = "ananya_78", days: int = 7) -> list[dict[str, Any]]:
    date_str = today()
    history = get_history_range(patient_id, date_str, days=days)
    
    decrypted_history = []
    from src.security import decrypt_data
    for log in history:
        raw_notes_decrypted = []
        for note in log.get("raw_notes", []):
            try:
                txt = decrypt_data(note.get("text", ""))
            except Exception:
                txt = note.get("text", note.get("note", ""))
            raw_notes_decrypted.append({
                "caregiver": note.get("caregiver"),
                "note": txt
            })
            
        vitals_decrypted = []
        for v in log.get("vitals", []):
            try:
                val = decrypt_data(v.get("value_raw", ""))
            except Exception:
                val = v.get("value_raw", "")
            vitals_decrypted.append({
                "vital_type": v.get("vital_type"),
                "value_raw": val,
                "status": v.get("status")
            })

        decrypted_history.append({
            "date": log.get("date"),
            "raw_notes": raw_notes_decrypted,
            "reconciled_events": [
                {
                    "activity": e.get("activity"),
                    "status": e.get("status"),
                    "inferred_time": e.get("inferred_time"),
                    "caregivers": e.get("caregivers", [])
                } for e in log.get("reconciled_events", [])
            ],
            "vitals": vitals_decrypted,
            "detected_gaps": [
                {
                    "task_name": g.get("task_name"),
                    "explanation": g.get("explanation"),
                    "importance": g.get("importance")
                } for g in log.get("detected_gaps", [])
            ]
        })
        
    return decrypted_history

@app.get("/api/caregiver-load")
def caregiver_load(patient_id: str = "ananya_78") -> dict[str, Any]:
    date_str = today()
    history = get_history_range(patient_id, date_str, days=7)
    
    caregiver_days = {}
    for day in history:
        d = day.get("date")
        for note in day.get("raw_notes", []):
            cg = note.get("caregiver")
            if cg:
                caregiver_days.setdefault(cg, set()).add(d)
        for event in day.get("reconciled_events", []):
            for cg in event.get("caregivers", []):
                if cg:
                    caregiver_days.setdefault(cg, set()).add(d)
                    
    # Seed fallback data if none exists
    if not caregiver_days:
        today_dt = datetime.date.today()
        if patient_id == "eleanor_82":
            caregiver_days = {
                "Sarah Jenkins": { (today_dt - datetime.timedelta(days=x)).strftime("%Y-%m-%d") for x in [1, 2, 4, 5] },
                "John Doe": { (today_dt - datetime.timedelta(days=3)).strftime("%Y-%m-%d") }
            }
        elif patient_id == "anj_86":
            caregiver_days = {
                "Assisting Nurse": { (today_dt - datetime.timedelta(days=x)).strftime("%Y-%m-%d") for x in [1, 2, 3] },
                "Sarah Jenkins": { (today_dt - datetime.timedelta(days=4)).strftime("%Y-%m-%d") }
            }
        else: # ananya_78
            caregiver_days = {
                "Sarah Jenkins": { (today_dt - datetime.timedelta(days=x)).strftime("%Y-%m-%d") for x in [1, 2, 3, 5] },
                "Caregiver John": { (today_dt - datetime.timedelta(days=4)).strftime("%Y-%m-%d") }
            }
            
    load_data = []
    cg_counts = {cg: len(days) for cg, days in caregiver_days.items()}
    
    warning_message = None
    if len(cg_counts) > 1:
        for cg, count in cg_counts.items():
            others = [c for name, c in cg_counts.items() if name != cg]
            avg_others = sum(others) / len(others)
            if avg_others > 0 and count > 2 * avg_others:
                warning_message = f"{cg} is carrying most of this week's logging"
                break
                
    for cg, count in cg_counts.items():
        load_data.append({
            "name": cg,
            "days_logged": count,
            "total_days": 7,
            "is_overloaded": warning_message is not None and cg in warning_message
        })
        
    return {
        "caregivers": load_data,
        "warning": warning_message
    }


if __name__ == "__main__":
    import uvicorn
    # Use CAREONE_PORT or PORT env var, default to 8501 as seen in docker-compose / screenshot
    port = int(os.environ.get("PORT") or os.environ.get("CAREONE_PORT") or 8501)
    host = os.environ.get("CAREONE_HOST", "127.0.0.1")
    uvicorn.run("web_app:app", host=host, port=port, reload=True)
