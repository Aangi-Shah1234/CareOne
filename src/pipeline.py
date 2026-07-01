import datetime
from zoneinfo import ZoneInfo
import json
import time
from src.memory import (
    load_care_plan, 
    save_care_plan, 
    get_day_record, 
    save_day_record, 
    get_history_range, 
    log_agent_event, 
    log_pipeline_execution
)
from src.agents.parser_agent import ParserAgent
from src.agents.vitals_agent import VitalsAgent
from src.agents.reconciliation_agent import ReconciliationAgent
from src.agents.refusal_agent import RefusalAgent
from src.agents.gap_detector import GapDetectorAgent
from src.agents.trend_agent import TrendAgent
from src.agents.summary_agent import SummaryAgent
from src.agents.risk_agent import RiskAgent

def run_careone_pipeline(patient_id: str, date_str: str, caregiver_name: str = None, raw_note: str = None) -> tuple[dict, dict]:
    """
    Executes the advanced multi-agent CareOne pipeline:
    1. Safety Check (intercepts clinical questions)
    2. Note Parser Agent (if note provided)
    3. Vitals Validator Agent (if note provided)
    4. Reconciliation Agent (if note provided)
    5. Refusal Intervention Agent (routine checks)
    6. Gap Detector Agent
    7. Risk Assessment Agent [NEW]
    8. Trend Analysis Agent (reads past 7 days)
    9. Care Summary Agent
    """
    # Initialize agents
    parser = ParserAgent()
    vitals_agent = VitalsAgent()
    reconciler = ReconciliationAgent()
    refusal_handler = RefusalAgent()
    detector = GapDetectorAgent()
    risk_analyzer = RiskAgent()
    trend_analyzer = TrendAgent()
    summarizer = SummaryAgent()

    # Load memory / baseline contexts
    patient_profile = load_care_plan(patient_id)
    day_record = get_day_record(patient_id, date_str)
    
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
            "risk_assessment": {},
            "summary": {}
        }

    # Trace log for observability
    trace_logs = {
        "pipeline_metadata": {
            "timestamp": datetime.datetime.now(ZoneInfo("Asia/Kolkata")).isoformat(),
            "patient_id": patient_id,
            "date_processed": date_str,
            "caregiver": caregiver_name or "System Refresh",
            "has_new_note": raw_note is not None
        },
        "parser": {"duration_ms": 0, "confidence_score": 1.0, "reasoning_path": "Skipped", "retrieved_memory": "None", "output": {}},
        "vitals_validator": {"duration_ms": 0, "confidence_score": 1.0, "reasoning_path": "Skipped", "retrieved_memory": "None", "output": {}},
        "reconciliation": {"duration_ms": 0, "confidence_score": 1.0, "reasoning_path": "Skipped", "retrieved_memory": "None", "output": {}},
        "refusal_handler": {"duration_ms": 0, "confidence_score": 1.0, "reasoning_path": "Skipped", "retrieved_memory": "None", "output": {}},
        "gap_detector": {"duration_ms": 0, "confidence_score": 1.0, "reasoning_path": "Pending", "retrieved_memory": "None", "output": {}},
        "risk_assessment": {"duration_ms": 0, "confidence_score": 1.0, "reasoning_path": "Pending", "retrieved_memory": "None", "output": {}},
        "trend_analyzer": {"duration_ms": 0, "confidence_score": 1.0, "reasoning_path": "Pending", "retrieved_memory": "None", "output": {}},
        "summary": {"duration_ms": 0, "confidence_score": 1.0, "reasoning_path": "Pending", "retrieved_memory": "None", "output": {}}
    }

    # 1. Safety Check (Refusal Agent intercepts medical queries)
    if raw_note and caregiver_name:
        print("[RefusalAgent] Running safety intercept check...")
        start_t = time.time()
        safety_res = refusal_handler.check_medical_safety(raw_note)
        duration_ms = int((time.time() - start_t) * 1000)
        
        trace_logs["refusal_handler"]["safety_check"] = safety_res
        trace_logs["refusal_handler"]["duration_ms"] = duration_ms
        trace_logs["refusal_handler"]["confidence_score"] = safety_res.get("confidence_score", 1.0)
        trace_logs["refusal_handler"]["reasoning_path"] = safety_res.get("reasoning_path", "Check finished.")
        
        if safety_res.get("is_medical_query"):
            # Blocked: dosage recommendation request - out of scope
            block_action = safety_res.get("explanation", "dosage recommendation request — out of scope")
            log_agent_event(patient_id, "Refusal Agent", f"Blocked: {block_action}")
            
            # Formulate the response and save it as today's blocked summary
            safety_msg = f"CareOne surfaces care information only. Please consult {patient_profile.get('patient_name')}'s doctor for medical decisions."
            day_record["raw_notes"].append({
                "caregiver": caregiver_name,
                "text": f"[BLOCKED QUERY] {raw_note}",
                "timestamp": datetime.datetime.now(ZoneInfo("Asia/Kolkata")).strftime("%H:%M")
            })
            day_record["summary"] = {
                "executive_summary": safety_msg,
                "recommended_actions": ["Consult physician immediately regarding this request."],
                "safety_alerts": [f"Caregiver requested out-of-scope medical advice: {block_action}"]
            }
            save_day_record(patient_id, date_str, day_record)
            log_pipeline_execution(patient_id, date_str, trace_logs)
            
            # Return immediately
            return day_record, trace_logs

    # Phase A: Note Ingestion, Vitals Extraction, and Event Reconciliation
    if raw_note and caregiver_name:
        # Save raw caregiver note
        day_record["raw_notes"].append({
            "caregiver": caregiver_name,
            "text": raw_note,
            "timestamp": datetime.datetime.now(ZoneInfo("Asia/Kolkata")).strftime("%H:%M")
        })

        # 2. Parse Events
        print("[ParserAgent] Parsing caregiver note...")
        start_t = time.time()
        parser_res = parser.parse_note(raw_note, caregiver_name)
        duration_ms = int((time.time() - start_t) * 1000)
        
        trace_logs["parser"]["duration_ms"] = duration_ms
        trace_logs["parser"]["confidence_score"] = parser_res.get("confidence_score", 0.9)
        trace_logs["parser"]["reasoning_path"] = parser_res.get("reasoning_path", "")
        trace_logs["parser"]["output"] = parser_res
        
        new_events = parser_res.get("events", [])
        events_count = len(new_events)
        log_agent_event(patient_id, "Parser Agent", f"Extracted {events_count} care activities from raw text")

        # 3. Extract Vitals
        print("[VitalsAgent] Extracting vitals from note...")
        start_t = time.time()
        vitals_res = vitals_agent.extract_vitals(raw_note)
        duration_ms = int((time.time() - start_t) * 1000)
        
        trace_logs["vitals_validator"]["duration_ms"] = duration_ms
        trace_logs["vitals_validator"]["confidence_score"] = vitals_res.get("confidence_score", 0.95)
        trace_logs["vitals_validator"]["reasoning_path"] = vitals_res.get("reasoning_path", "")
        trace_logs["vitals_validator"]["output"] = vitals_res
        
        new_vitals = vitals_res.get("readings", [])
        for vital in new_vitals:
            vital["caregiver"] = caregiver_name
            vital["timestamp"] = datetime.datetime.now(ZoneInfo("Asia/Kolkata")).strftime("%H:%M")
            day_record["vitals"].append(vital)
            log_agent_event(patient_id, "Vitals Agent", f"{vital['vital_type']} {vital['value_raw']} logged — status: {vital['status']}")

        # Inject vitals as 'Medical check' events into the reconciliation pipeline
        for vital in new_vitals:
            vital_event = {
                "activity": "Medical check",
                "time_raw": "at check-in",
                "inferred_time": datetime.datetime.now(ZoneInfo("Asia/Kolkata")).strftime("%H:%M"),
                "status": "Completed",
                "notes": f"Measured {vital['vital_type']}: {vital['value_raw']} (Status: {vital['status']} - {vital['explanation']})",
                "caregiver": caregiver_name
            }
            new_events.append(vital_event)

        # 4. Reconcile Events
        print("[ReconciliationAgent] Reconciling caregiver events...")
        start_t = time.time()
        reconciliation_res = reconciler.reconcile(
            existing_events=day_record["reconciled_events"],
            new_events=new_events
        )
        duration_ms = int((time.time() - start_t) * 1000)
        
        trace_logs["reconciliation"]["duration_ms"] = duration_ms
        trace_logs["reconciliation"]["confidence_score"] = reconciliation_res.get("confidence_score", 0.95)
        trace_logs["reconciliation"]["reasoning_path"] = reconciliation_res.get("reasoning_path", "")
        trace_logs["reconciliation"]["output"] = reconciliation_res
        
        day_record["reconciled_events"] = reconciliation_res.get("reconciled_events", [])
        day_record["conflicts"] = reconciliation_res.get("conflicts", [])
        
        confl_count = len(day_record["conflicts"])
        if confl_count > 0:
            log_agent_event(patient_id, "Reconciler Agent", f"Merged caregiver logs — flagged {confl_count} contradictions")
        else:
            log_agent_event(patient_id, "Reconciler Agent", f"Merged caregiver logs — no contradictions found")

    # Phase B: Longitudinal Analysis & Safety Interventions (Always runs on update)
    
    # 5. Run Refusal Handler Agent (Context Memory: feeds patient preferences)
    print("[RefusalAgent] Generating task interventions...")
    start_t = time.time()
    prefs = patient_profile.get("preferences", [])
    refusal_res = refusal_handler.generate_interventions(day_record["reconciled_events"], preferences=prefs)
    duration_ms = int((time.time() - start_t) * 1000)
    
    trace_logs["refusal_handler"]["duration_ms"] = duration_ms
    trace_logs["refusal_handler"]["confidence_score"] = refusal_res.get("confidence_score", 0.9)
    trace_logs["refusal_handler"]["reasoning_path"] = refusal_res.get("reasoning_path", "")
    trace_logs["refusal_handler"]["retrieved_memory"] = f"Retrieved {len(prefs)} patient preferences."
    trace_logs["refusal_handler"]["output"] = refusal_res
    day_record["interventions"] = refusal_res.get("interventions", [])
    
    for inter in day_record["interventions"]:
        log_agent_event(patient_id, "Refusal Agent", f"Refusal intervention strategy generated for {inter['activity']}")

    # 6. Run Gap Detector Agent
    print("[GapDetectorAgent] Auditing care schedule compliance...")
    start_t = time.time()
    detector_res = detector.detect_gaps(
        care_plan=patient_profile,
        reconciled_events=day_record["reconciled_events"],
        current_time_context=f"Analysis date: {date_str}"
    )
    duration_ms = int((time.time() - start_t) * 1000)
    
    trace_logs["gap_detector"]["duration_ms"] = duration_ms
    trace_logs["gap_detector"]["confidence_score"] = detector_res.get("confidence_score", 0.95)
    trace_logs["gap_detector"]["reasoning_path"] = detector_res.get("reasoning_path", "")
    trace_logs["gap_detector"]["output"] = detector_res
    day_record["detected_gaps"] = detector_res.get("detected_gaps", [])
    
    for gap in day_record["detected_gaps"]:
        log_agent_event(patient_id, "Gaps Agent", f"{gap['task_name']} unconfirmed — alert raised")

    # 7. Run Risk Assessment Agent
    print("[RiskAgent] Calculating safety risk parameters...")
    start_t = time.time()
    risk_res = risk_analyzer.assess_risk(
        reconciled_events=day_record["reconciled_events"],
        conflicts=day_record["conflicts"],
        vitals=day_record["vitals"],
        gaps=day_record["detected_gaps"],
        patient_conditions=patient_profile.get("conditions", "")
    )
    duration_ms = int((time.time() - start_t) * 1000)
    
    trace_logs["risk_assessment"]["duration_ms"] = duration_ms
    trace_logs["risk_assessment"]["confidence_score"] = risk_res.get("confidence_score", 0.9)
    trace_logs["risk_assessment"]["reasoning_path"] = risk_res.get("reasoning_path", "")
    trace_logs["risk_assessment"]["output"] = risk_res
    day_record["risk_assessment"] = risk_res
    log_agent_event(patient_id, "Risk Agent", f"Safety risk calculated: {risk_res.get('risk_level')}")

    # 8. Run Trend Agent (Memory: fetches past 7 days)
    print("[TrendAgent] Analyzing 7-day wellness trends...")
    start_t = time.time()
    past_logs = get_history_range(patient_id, date_str, days=7)
    trend_res = trend_analyzer.analyze_trends(past_logs)
    duration_ms = int((time.time() - start_t) * 1000)
    
    trace_logs["trend_analyzer"]["duration_ms"] = duration_ms
    trace_logs["trend_analyzer"]["confidence_score"] = trend_res.get("confidence_score", 0.9)
    trace_logs["trend_analyzer"]["reasoning_path"] = trend_res.get("reasoning_path", "")
    trace_logs["trend_analyzer"]["retrieved_memory"] = f"Retrieved {len(past_logs)} days of historical logs."
    trace_logs["trend_analyzer"]["output"] = trend_res
    day_record["trends"] = trend_res
    
    # Trend Agent writes identified recurring care gaps back to patient profile memory
    recurring = trend_res.get("recurring_gaps", [])
    if recurring:
        updated_prefs = False
        for gap_task in recurring:
            gap_pref = f"Recurring Care Gap Alert: {gap_task} is frequently unconfirmed."
            if gap_pref not in patient_profile.get("preferences", []):
                patient_profile.setdefault("preferences", []).append(gap_pref)
                updated_prefs = True
        if updated_prefs:
            save_care_plan(patient_id, patient_profile)
            log_agent_event(patient_id, "Trends Agent", f"Updated patient preferences with recurring gaps: {', '.join(recurring)}")
    
    # Extract any vital trends to log in the feed
    bps = [v["value_raw"] for log in past_logs for v in log.get("vitals", []) if v.get("vital_type") == "Blood Pressure"]
    if bps:
        sys_vals = [int(bp.split("/")[0]) for bp in bps if "/" in bp]
        if sys_vals:
            avg_sys = int(sum(sys_vals) / len(sys_vals))
            trend_dir = "upward" if sys_vals[-1] > avg_sys else "stable"
            log_agent_event(patient_id, "Trends Agent", f"BP systolic 7-day avg {avg_sys} mmHg — {trend_dir} trend analyzed")

    # 9. Run Summary Agent
    print("[SummaryAgent] Compiling daily narrative brief...")
    start_t = time.time()
    summary_res = summarizer.generate_summary(
        reconciled_events=day_record["reconciled_events"],
        conflicts=day_record["conflicts"],
        detected_gaps=day_record["detected_gaps"]
    )
    duration_ms = int((time.time() - start_t) * 1000)
    
    trace_logs["summary"]["duration_ms"] = duration_ms
    trace_logs["summary"]["confidence_score"] = summary_res.get("confidence_score", 0.95)
    trace_logs["summary"]["reasoning_path"] = summary_res.get("reasoning_path", "")
    trace_logs["summary"]["output"] = summary_res
    day_record["summary"] = summary_res
    
    log_agent_event(patient_id, "Summary Agent", "Daily care brief and safety warnings generated")

    # Save to Database / fallback files
    save_day_record(patient_id, date_str, day_record)
    log_pipeline_execution(patient_id, date_str, trace_logs)

    return day_record, trace_logs
