from pydantic import BaseModel, Field
from typing import List
import json
from src.agents.base_agent import BaseAgent

class RiskAssessmentOutput(BaseModel):
    risk_level: str = Field(
        ...,
        description="The calculated overall daily safety risk level for the patient. Must be one of: Critical, High, Medium, Low."
    )
    description: str = Field(
        ...,
        description="Detailed description of why this risk level was assigned based on todays events."
    )
    indicators: List[str] = Field(
        ...,
        description="List of specific medical or behavioral indicators contributing to the risk level (e.g. 'Systolic BP of 155 mmHg', 'Morning meds skipped')."
    )
    confidence_score: float = Field(
        ...,
        description="Confidence score between 0.0 and 1.0 of the risk assessment accuracy."
    )
    reasoning_path: str = Field(
        ...,
        description="Clinical rationale explaining why these indicators lead to the selected risk level."
    )

class RiskAgent(BaseAgent):
    def __init__(self):
        system_instruction = (
            "You are the Risk Assessment Agent of CareOne. Your job is to analyze today's patient state and calculate "
            "an overall daily safety risk level (Critical, High, Medium, Low).\n"
            "Analyze:\n"
            "1. Vitals: Systolic BP >= 140 or Glucose >= 180 or Glucose < 70 or Fluid intake exceeding limits are High/Critical risks.\n"
            "2. Care Gaps: Skipped or refused high-importance medications are High/Critical risks. Gaps in meals are Medium risks.\n"
            "3. Caregiver Conflicts: Contradictions in medication status are High risks.\n"
            "Generate a realistic, clinically justified safety risk classification, highlighting specific indicators, "
            "along with a confidence score and a detailed reasoning path explaining your clinical judgment."
        )
        super().__init__(name="RiskAgent", system_instruction=system_instruction)

    def assess_risk(self, reconciled_events: List[dict], conflicts: List[dict], vitals: List[dict], gaps: List[dict], patient_conditions: str = "") -> dict:
        """
        Calculates patient safety risk based on daily events, conflicts, vitals, and gaps.
        """
        prompt = (
            f"Patient Diagnoses/Conditions: {patient_conditions}\n\n"
            f"Reconciled Care Events Today:\n{json.dumps(reconciled_events, indent=2)}\n\n"
            f"Conflicts Flagged:\n{json.dumps(conflicts, indent=2)}\n\n"
            f"Vitals Measurements:\n{json.dumps(vitals, indent=2)}\n\n"
            f"Detected Care Gaps:\n{json.dumps(gaps, indent=2)}\n\n"
            f"Analyze the safety metrics and output the structured risk assessment."
        )
        return self.call_llm(prompt, response_schema=RiskAssessmentOutput)
