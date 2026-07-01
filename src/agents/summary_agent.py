from pydantic import BaseModel, Field
from typing import List
import json
from src.agents.base_agent import BaseAgent

# Pydantic schema for summary agent output
class SummaryOutput(BaseModel):
    executive_summary: str = Field(
        ..., 
        description="A friendly, empathetic 2-3 paragraph summary of the patient's day based on logs. Note who cared for them, their activities, mood, and general state."
    )
    recommended_actions: List[str] = Field(
        ..., 
        description="Actionable, specific next steps for the caregivers to check, execute, or ask about."
    )
    safety_alerts: List[str] = Field(
        ..., 
        description="Critical warnings, e.g. regarding conflicting caregiver reports, refused/skipped high-importance meds, or lack of hydration."
    )
    confidence_score: float = Field(
        ...,
        description="Confidence score between 0.0 and 1.0 of the daily summary synthesis."
    )
    reasoning_path: str = Field(
        ...,
        description="Explanation of how the summary and actions were aggregated from the timeline, conflicts, and gap reports."
    )

class SummaryAgent(BaseAgent):
    def __init__(self):
        system_instruction = (
            "You are the Care Summary Agent of CareOne. Your job is to draft a daily summary and recommended next steps for a patient "
            "based on the caregiver logs, reconciled events, any conflicting inputs, and detected care gaps.\n"
            "Your output must be friendly, professional, empathetic, and clear. Family members rely on this summary to coordinate daily living and health.\n"
            "Be sure to emphasize any critical tasks that were missed or reports that contradict each other."
        )
        super().__init__(name="SummaryAgent", system_instruction=system_instruction)

    def generate_summary(self, reconciled_events: List[dict], conflicts: List[dict], detected_gaps: List[dict]) -> dict:
        """
        Generates a structured daily summary and next steps.
        """
        prompt = (
            f"Reconciled Care Events Today:\n{json.dumps(reconciled_events, indent=2)}\n\n"
            f"Conflicts Flagged:\n{json.dumps(conflicts, indent=2)}\n\n"
            f"Detected Gaps (unconfirmed tasks):\n{json.dumps(detected_gaps, indent=2)}\n\n"
            f"Create the daily summary and recommendations."
        )
        return self.call_llm(prompt, response_schema=SummaryOutput)
