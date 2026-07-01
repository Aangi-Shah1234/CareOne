from pydantic import BaseModel, Field
from typing import List
import json
from src.agents.base_agent import BaseAgent

# Pydantic schemas for gap detector output
class CareGap(BaseModel):
    task_id: str = Field(
        ..., 
        description="The ID of the task in the care plan, or 'custom' if it does not map directly to a scheduled task."
    )
    task_name: str = Field(
        ..., 
        description="User-friendly name of the expected care task."
    )
    category: str = Field(
        ..., 
        description="Category of the task (e.g. Meal, Medication, Hydration, Exercise, Rest, Vitals)."
    )
    importance: str = Field(
        ..., 
        description="Importance of this task: High, Medium, Low."
    )
    confidence_score: float = Field(
        ..., 
        description="Confidence that this task was actually missed/skipped as a float between 0.0 and 1.0. Consider time of day (e.g. if current notes only cover up to afternoon, evening tasks should have Low confidence)."
    )
    explanation: str = Field(
        ..., 
        description="Why this is considered a gap. You MUST use the word 'unconfirmed' and NEVER use 'missed' (e.g., 'Morning medications are unconfirmed in todays log')."
    )

class GapDetectorOutput(BaseModel):
    detected_gaps: List[CareGap] = Field(
        ..., 
        description="List of care tasks that are missing or skipped today."
    )
    confidence_score: float = Field(
        ...,
        description="Confidence score between 0.0 and 1.0 of the gap detection audit."
    )
    reasoning_path: str = Field(
        ...,
        description="Logical explanation comparing schedule baseline requirements against reconciled caregiver timeline events."
    )

class GapDetectorAgent(BaseAgent):
    def __init__(self):
        system_instruction = (
            "You are the Gap Detector Agent of CareOne. Your job is to check if any scheduled care tasks are unconfirmed today.\n"
            "You will be given the baseline Care Plan (expected daily tasks) and the Reconciled Daily Timeline of events logged so far today.\n"
            "For each expected task in the Care Plan, check if there is a corresponding completed activity in the Reconciled Daily Timeline.\n"
            "If an activity is missing, or was explicitly marked as 'Skipped' or 'Refused', identify it as an unconfirmed care task.\n"
            "CRITICAL: Every gap alert you generate must be phrased using the word 'unconfirmed' (e.g., 'Morning medications are unconfirmed today'), NEVER use the word 'missed'. Language matters in caregiving.\n"
            "Provide a concise, clear explanation for why this is marked as an unconfirmed task."
        )
        super().__init__(name="GapDetectorAgent", system_instruction=system_instruction)

    def detect_gaps(self, care_plan: dict, reconciled_events: List[dict], current_time_context: str = "") -> dict:
        """
        Detects care gaps by comparing reconciled events against the care plan.
        We can pass current_time_context (e.g. '18:00') to help the agent grade the gap confidence.
        """
        prompt = (
            f"Patient Care Plan (Scheduled Daily Tasks):\n{json.dumps(care_plan, indent=2)}\n\n"
            f"Reconciled Daily Care Events Logged So Far:\n{json.dumps(reconciled_events, indent=2)}\n\n"
            f"Current Context (e.g. Time/Day info if available): {current_time_context}\n\n"
            f"Analyze and identify all care gaps."
        )
        return self.call_llm(prompt, response_schema=GapDetectorOutput)
