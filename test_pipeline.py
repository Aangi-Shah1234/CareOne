import unittest
from unittest.mock import patch
import json
import os
import datetime

# Set dummy key for import checks
os.environ["GEMINI_API_KEY"] = os.environ.get("GEMINI_API_KEY", "dummy_key_for_testing")

from src.pipeline import run_careone_pipeline
from src.memory import save_day_record, get_day_record, get_agent_events

class TestCareOnePipeline(unittest.TestCase):
    
    def setUp(self):
        self.patient_id = "arthur_78"
        self.test_date = "2026-06-24"
        dummy_record = {
            "patient_id": self.patient_id,
            "date": self.test_date,
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
        save_day_record(self.patient_id, self.test_date, dummy_record)

    @patch('src.agents.base_agent.BaseAgent.call_llm')
    def test_complete_caregiver_flow(self, mock_call_llm):
        """
        Tests the 8-agent pipeline from raw caregiver note ingestion, safety checks,
        note parsing, reconciliation, refusal handling, gap detection, risk assessment,
        trend analysis, and summary generation.
        """
        # 1. Safety Check Response (Not a medical query)
        mock_safety_response = {
            "is_medical_query": False,
            "query_type": "none",
            "explanation": "No medical query detected.",
            "confidence_score": 1.0,
            "reasoning_path": "Safe log text."
        }

        # 2. Note Parser Response
        mock_parser_response = {
            "events": [
                {"activity": "Meal", "time_raw": "lunch", "inferred_time": "13:00", "status": "Completed", "notes": "Gave Dad lunch."},
                {"activity": "Medication", "time_raw": "morning meds", "inferred_time": "09:00", "status": "Delayed", "notes": "meds were delayed."},
                {"activity": "Exercise", "time_raw": "morning walk", "inferred_time": "09:30", "status": "Refused", "notes": "He refused his morning walk."}
            ],
            "confidence_score": 0.92,
            "reasoning_path": "Parsed activities."
        }
        
        # 3. Vitals Validator Response
        mock_vitals_response = {
            "readings": [
                {"vital_type": "Blood Pressure", "value_raw": "145/92", "status": "High/Alert", "explanation": "Systolic BP > 140 is Stage 2 hypertension."}
            ],
            "confidence_score": 0.98,
            "reasoning_path": "BP validation."
        }
        
        # 4. Reconciliation Response
        mock_reconciliation_response = {
            "reconciled_events": [
                {"activity": "Meal", "inferred_time": "13:00", "status": "Completed", "caregivers": ["Caregiver A"], "notes": "Gave Dad lunch."},
                {"activity": "Medication", "inferred_time": "09:00", "status": "Delayed", "caregivers": ["Caregiver A"], "notes": "Meds were delayed."},
                {"activity": "Exercise", "inferred_time": "09:30", "status": "Refused", "caregivers": ["Caregiver A"], "notes": "Refused his morning walk."},
                {"activity": "Medical check", "inferred_time": "13:15", "status": "Completed", "caregivers": ["Caregiver A"], "notes": "Measured Blood Pressure: 145/92."}
            ],
            "conflicts": [],
            "confidence_score": 0.95,
            "reasoning_path": "Reconciliation complete."
        }
        
        # 5. Refusal Intervention Response
        mock_refusal_response = {
            "interventions": [
                {"activity": "Morning Walk", "stated_reason": "Knees hurting", "severity": "Medium", "strategy": "Apply heating pad."}
            ],
            "confidence_score": 0.90,
            "reasoning_path": "Strategy planned."
        }
        
        # 6. Gap Detector Response
        mock_gap_response = {
            "detected_gaps": [
                {"task_id": "afternoon_hydration", "task_name": "Afternoon Hydration", "category": "Hydration", "importance": "Medium", "confidence_score": 0.95, "explanation": "Afternoon hydration is unconfirmed today."}
            ],
            "confidence_score": 0.95,
            "reasoning_path": "Routine audit."
        }

        # 7. Risk Assessment Agent Response [NEW]
        mock_risk_response = {
            "risk_level": "Medium",
            "description": "Systolic BP above 140 mmHg and unconfirmed tasks.",
            "indicators": ["BP 145/92", "Walk Refused"],
            "confidence_score": 0.92,
            "reasoning_path": "Evaluation of daily vitals & gaps."
        }
        
        # 8. Trend Analyzer Response
        mock_trend_response = {
            "completion_rates": [
                {"activity_name": "Morning Medications", "completed_count": 6, "total_expected": 7}
            ],
            "observed_trends": [
                {"trend_type": "Physical Mobility", "observation": "Dad refused morning walk 3 times.", "impact": "Decreased mobility."}
            ],
            "recurring_gaps": ["evening_walk"],
            "summary_insight": "Dad remains stable but walks are increasingly unconfirmed.",
            "confidence_score": 0.90,
            "reasoning_path": "Longitudinal scan."
        }
        
        # 9. Summary Agent Response
        mock_summary_response = {
            "executive_summary": "Dad had lunch, but morning medications are unconfirmed. He refused his walk. BP was 145/92.",
            "recommended_actions": ["Offer hydration since it was unconfirmed."],
            "safety_alerts": ["Blood pressure is elevated at 145/92."],
            "confidence_score": 0.95,
            "reasoning_path": "Synthesis of logs."
        }
        
        # Sequence LLM responses
        mock_call_llm.side_effect = [
            mock_safety_response,
            mock_parser_response,
            mock_vitals_response,
            mock_reconciliation_response,
            mock_refusal_response,
            mock_gap_response,
            mock_risk_response,
            mock_trend_response,
            mock_summary_response
        ]
        
        # Execute Pipeline
        record, trace = run_careone_pipeline(
            patient_id=self.patient_id,
            date_str=self.test_date,
            caregiver_name="Caregiver A",
            raw_note="Gave Dad lunch, but meds were delayed. He refused his morning walk. Checked his blood pressure: 145/92."
        )
        
        # Validation checks
        self.assertEqual(len(record["raw_notes"]), 1)
        self.assertEqual(record["vitals"][0]["vital_type"], "Blood Pressure")
        self.assertEqual(record["vitals"][0]["status"], "High/Alert")
        self.assertEqual(record["reconciled_events"][2]["status"], "Refused")
        self.assertEqual(record["interventions"][0]["activity"], "Morning Walk")
        self.assertEqual(len(record["detected_gaps"]), 1)
        self.assertIn("unconfirmed", record["detected_gaps"][0]["explanation"])
        self.assertEqual(record["trends"]["summary_insight"], "Dad remains stable but walks are increasingly unconfirmed.")
        self.assertEqual(record["risk_assessment"]["risk_level"], "Medium")

    @patch('src.agents.base_agent.BaseAgent.call_llm')
    def test_safety_intercept_blocked_flow(self, mock_call_llm):
        """
        Tests that requesting out-of-scope medical/dosage changes is intercepted
        and blocked by the Refusal Agent immediately.
        """
        mock_blocked_safety_response = {
            "is_medical_query": True,
            "query_type": "dosage_change",
            "explanation": "dosage recommendation request — out of scope",
            "confidence_score": 1.0,
            "reasoning_path": "Unsafe clinical query intercepted."
        }
        
        mock_call_llm.return_value = mock_blocked_safety_response
        
        # Execute Pipeline with unsafe note
        record, trace = run_careone_pipeline(
            patient_id=self.patient_id,
            date_str=self.test_date,
            caregiver_name="Caregiver A",
            raw_note="Should I double Arthur's Metformin dose to 1000mg since his blood sugar is high?"
        )
        
        # Assertions
        self.assertEqual(len(record["raw_notes"]), 1)
        self.assertIn("[BLOCKED QUERY]", record["raw_notes"][0]["text"])
        self.assertEqual(
            record["summary"]["executive_summary"],
            "CareOne surfaces care information only. Please consult Arthur's doctor for medical decisions."
        )
        
        # Check event logging
        events = get_agent_events(self.patient_id, datetime.date.today().strftime("%Y-%m-%d"))
        refusal_events = [e for e in events if e["agent_name"] == "Refusal Agent"]
        self.assertTrue(len(refusal_events) > 0)
        self.assertTrue(any("Blocked: dosage recommendation request" in e["action"] for e in refusal_events))

if __name__ == '__main__':
    unittest.main()
