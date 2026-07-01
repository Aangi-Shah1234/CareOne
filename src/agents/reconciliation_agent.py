from pydantic import BaseModel, Field
from typing import List, Optional
import json
from src.agents.base_agent import BaseAgent

# Pydantic schemas for reconciliation output
class ReconciledEvent(BaseModel):
    activity: str = Field(
        ..., 
        description="The activity type: Meal, Medication, Hydration, Exercise, Rest, Medical check, Other."
    )
    inferred_time: str = Field(
        ..., 
        description="Reconciled inferred time in HH:MM format, or 'Unknown'."
    )
    status: str = Field(
        ..., 
        description="Reconciled status: Completed, Skipped, Delayed, Refused, Conflicting, Unknown."
    )
    caregivers: List[str] = Field(
        ..., 
        description="List of caregivers who reported this or related activities."
    )
    notes: str = Field(
        ..., 
        description="Synthesized notes combining details from all sources. Mention if times differed slightly."
    )

class ConflictItem(BaseModel):
    activity: str = Field(
        ..., 
        description="The care activity under conflict."
    )
    description: str = Field(
        ..., 
        description="Detailed description of the contradiction (e.g. 'Sarah reported morning meds taken, but John reported morning meds refused')."
    )
    caregivers_involved: List[str] = Field(
        ..., 
        description="Names of caregivers involved in the contradiction."
    )

class ReconciliationOutput(BaseModel):
    reconciled_events: List[ReconciledEvent] = Field(
        ..., 
        description="Consolidated list of care events after resolving duplicates."
    )
    conflicts: List[ConflictItem] = Field(
        ..., 
        description="List of unresolvable contradictions that need caregiver attention."
    )
    confidence_score: float = Field(
        ...,
        description="Confidence score between 0.0 and 1.0 of the logs reconciliation."
    )
    reasoning_path: str = Field(
        ...,
        description="Explanation of how events were merged and what contradictions were detected."
    )

class ReconciliationAgent(BaseAgent):
    def __init__(self):
        system_instruction = (
            "You are the Reconciliation Agent of CareOne. Your job is to consolidate care logs from the current day.\n"
            "You will be given a list of existing events that were already logged today, and a list of new events parsed from a new caregiver note.\n"
            "Follow these rules:\n"
            "1. Deduplicate: If an event in the new note matches an existing event (same activity, close time, e.g., lunch at 12:45 vs 13:00), merge them. Combine their notes and list both caregivers.\n"
            "2. Resolve Conflicts: If there is a direct contradiction (e.g., caregiver A says Dad 'skipped morning meds' and caregiver B says Dad 'took morning meds'), flag this under 'conflicts'. The reconciled event status should be set to 'Conflicting'.\n"
            "3. Build a consolidated timeline of care events for today."
        )
        super().__init__(name="ReconciliationAgent", system_instruction=system_instruction)

    def reconcile(self, existing_events: List[dict], new_events: List[dict]) -> dict:
        """
        Reconciles existing daily events with new parsed events.
        """
        prompt = (
            f"Existing daily events already logged today:\n{json.dumps(existing_events, indent=2)}\n\n"
            f"New incoming care events parsed from the latest caregiver note:\n{json.dumps(new_events, indent=2)}\n\n"
            f"Reconcile these lists into a single consolidated schema."
        )
        return self.call_llm(prompt, response_schema=ReconciliationOutput)
