from pydantic import BaseModel, Field
from typing import List, Optional
import json
from src.agents.base_agent import BaseAgent

class RefusalIntervention(BaseModel):
    activity: str = Field(
        ..., 
        description="The care task that was refused or skipped today (e.g., Morning Walk, Medication)."
    )
    stated_reason: str = Field(
        ..., 
        description="The reason for the refusal stated in the log (e.g. 'knees hurt', 'too tired')."
    )
    severity: str = Field(
        ..., 
        description="How critical this refusal is for patient safety: High, Medium, Low."
    )
    strategy: str = Field(
        ..., 
        description="A clear, actionable care tip or alternative suggestion for the next caregiver shift to gently resolve the issue. If patient preferences are provided, customize this using those preferences."
    )

class RefusalOutput(BaseModel):
    interventions: List[RefusalIntervention] = Field(
        ..., 
        description="List of care intervention strategies for refused activities."
    )
    confidence_score: float = Field(
        ...,
        description="Confidence score between 0.0 and 1.0 of the generated interventions."
    )
    reasoning_path: str = Field(
        ...,
        description="Explanation of how the interventions were generated using patient preferences and clinical care practices."
    )

class SafetyCheckOutput(BaseModel):
    is_medical_query: bool = Field(
        ...,
        description="Set to True if the caregiver note requests medication changes, dosage advice, diagnosis, or clinical advice."
    )
    query_type: str = Field(
        ...,
        description="Category of request: 'dosage_change', 'diagnosis', 'medication_alteration', or 'none'."
    )
    explanation: str = Field(
        ...,
        description="A short explanation of what was intercepted (e.g. 'dosage recommendation request — out of scope')."
    )
    confidence_score: float = Field(
        ...,
        description="Confidence score between 0.0 and 1.0 of the safety check."
    )
    reasoning_path: str = Field(
        ...,
        description="Logical path used to classify this note as medical advice query or safe caregiver logging."
    )

class RefusalAgent(BaseAgent):
    def __init__(self):
        system_instruction = (
            "You are the Refusal Handling Agent of CareOne. Your job is to:\n"
            "1. Intercept medical queries (medication changes, dosage advice, diagnostic requests) for patient safety.\n"
            "2. Suggest caregiver strategies for routine tasks marked as 'Refused' or 'Skipped' in daily logs.\n"
            "\n"
            "Safety Guardrails:\n"
            "- If a caregiver note asks for clinical guidance (e.g. 'should I double the Metformin?', 'what diagnosis fits his fever?'), "
            "you must flag it as is_medical_query = True. Explain what was blocked (e.g. 'dosage recommendation request — out of scope').\n"
            "- CRITICAL: Your safety check must block clinical/dosage instructions and output: 'CareOne surfaces care information only. Please consult Arthur's/Eleanor's doctor for medical decisions.'\n"
            "\n"
            "Routine Refusal Tips:\n"
            "- If daily exercises or meals are refused, generate empathetic strategies to resolve them during future caregiver shifts. "
            "Incorporate patient preferences (like using heating pads for joint pain before walking, or offering low-sodium options)."
        )
        super().__init__(name="RefusalAgent", system_instruction=system_instruction)

    def check_medical_safety(self, note: str) -> dict:
        """
        Inspects raw caregiver note to intercept unsafe medical requests.
        """
        prompt = (
            f"Review the caregiver note below. Determine if the user is asking for medical advice, "
            f"dosage modifications, medication changes, or diagnosis:\n\n{note}"
        )
        return self.call_llm(prompt, response_schema=SafetyCheckOutput)

    def generate_interventions(self, reconciled_events: List[dict], preferences: List[str] = None) -> dict:
        """
        Scans daily reconciled events and drafts intervention protocols, incorporating patient preferences.
        """
        refused_events = [e for e in reconciled_events if e.get("status") in ["Refused", "Skipped", "Conflicting"]]
        
        if not refused_events:
            return {"interventions": [], "confidence_score": 1.0, "reasoning_path": "No refused or skipped events found."}
            
        prompt = (
            f"Patient Preferences from Memory:\n{json.dumps(preferences, indent=2) if preferences else 'None'}\n\n"
            f"Daily Reconciled Events to address:\n{json.dumps(refused_events, indent=2)}\n\n"
            f"Create actionable alternative strategies for these refused/skipped tasks."
        )
        return self.call_llm(prompt, response_schema=RefusalOutput)
