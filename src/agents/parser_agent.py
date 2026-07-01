from pydantic import BaseModel, Field
from typing import List, Optional
from src.agents.base_agent import BaseAgent

# Pydantic schemas for structured parsing output
class CareEvent(BaseModel):
    activity: str = Field(
        ..., 
        description="The type of activity. Must be one of: Meal, Medication, Hydration, Exercise, Rest, Medical check, Other."
    )
    time_raw: str = Field(
        ..., 
        description="The raw time expression found in the text (e.g. 'breakfast', 'at 10', 'around noon', 'evening')."
    )
    inferred_time: str = Field(
        ..., 
        description="Inferred time in 24h clock format 'HH:MM' (e.g. '08:30', '12:00', '17:00'). Use 'Unknown' if no time context exists."
    )
    status: str = Field(
        ..., 
        description="Status of the activity. Must be one of: Completed, Skipped, Delayed, Refused, Unknown."
    )
    notes: str = Field(
        ..., 
        description="Any extra qualitative details (e.g., 'refused joint meds', 'BP was 120/80', 'complained of tiredness'). Use empty string if no extra details."
    )

class ParserOutput(BaseModel):
    events: List[CareEvent] = Field(
        ..., 
        description="List of care events extracted from the text."
    )
    confidence_score: float = Field(
        ...,
        description="Confidence score between 0.0 and 1.0 of the extraction accuracy."
    )
    reasoning_path: str = Field(
        ...,
        description="Explanation of how the parser mapped text segments to the structured list of events."
    )

class ParserAgent(BaseAgent):
    def __init__(self):
        system_instruction = (
            "You are the Note Parser Agent of CareOne. Your job is to extract structured care events from unstructured caregiver daily notes.\n"
            "Analyze the input notes carefully and identify all care activities relating to the patient.\n"
            "Categorize each event (Meal, Medication, Hydration, Exercise, Rest, Medical check, Other), parse the raw time mention, "
            "infer a 24-hour timestamp (HH:MM), identify the status (Completed, Skipped, Delayed, Refused, Unknown), and pull relevant details into notes.\n"
            "Be conservative and precise. Do not invent events that were not mentioned."
        )
        super().__init__(name="ParserAgent", system_instruction=system_instruction)

    def parse_note(self, note: str, caregiver_name: str) -> dict:
        """
        Parses a raw note from a specific caregiver.
        Returns a dictionary matching the ParserOutput schema, injecting the caregiver's name into each event.
        """
        prompt = f"Caregiver: {caregiver_name}\nNote: {note}"
        parsed = self.call_llm(prompt, response_schema=ParserOutput)
        
        # Inject caregiver metadata into each event
        if "events" in parsed:
            for event in parsed["events"]:
                event["caregiver"] = caregiver_name
                
        return parsed
