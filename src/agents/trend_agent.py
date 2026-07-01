from pydantic import BaseModel, Field
from typing import List
import json
from src.agents.base_agent import BaseAgent

class ActivityCompletion(BaseModel):
    activity_name: str = Field(
        ..., 
        description="Name of the daily activity category or specific scheduled task."
    )
    completed_count: int = Field(
        ..., 
        description="Number of times this activity was successfully completed in the past week."
    )
    total_expected: int = Field(
        ..., 
        description="Number of times this activity was expected over the past week (usually 7)."
    )

class WeeklyTrend(BaseModel):
    trend_type: str = Field(
        ..., 
        description="Category: Physical Mobility, Cognitive/Mood, Hydration/Nutrition, Medical/Vitals, Medication Adherence, General."
    )
    observation: str = Field(
        ..., 
        description="Description of the trend (e.g., 'Complained of knee pain on 3 separate days' or 'Missed afternoon hydration twice')."
    )
    impact: str = Field(
        ..., 
        description="Potential health or wellness risk (e.g., 'Reduced water intake increases dehydration risk, especially with heat')."
    )

class TrendOutput(BaseModel):
    completion_rates: List[ActivityCompletion] = Field(
        ..., 
        description="Vitals and activity execution counts over the past 7 days."
    )
    observed_trends: List[WeeklyTrend] = Field(
        ..., 
        description="Identified behavioral or medical trends over the week."
    )
    recurring_gaps: List[str] = Field(
        ...,
        description="List of care plan tasks frequently unconfirmed (e.g. ['evening_walk', 'afternoon_hydration']) to update patient preferences memory."
    )
    summary_insight: str = Field(
        ..., 
        description="An empathetic summary of the patient's weekly wellness trajectory."
    )
    confidence_score: float = Field(
        ...,
        description="Confidence score between 0.0 and 1.0 of the trend analysis."
    )
    reasoning_path: str = Field(
        ...,
        description="Detailed explanation of the trend metrics and identified behavioral patterns."
    )

class TrendAgent(BaseAgent):
    def __init__(self):
        system_instruction = (
            "You are the Trend Analysis Agent of CareOne. Your job is to perform longitudinal assessments of the patient "
            "by reviewing the daily logs from the past 7 days.\n"
            "Analyze the historical record to:\n"
            "1. Count how many times scheduled tasks (Meals, Medications, Exercise, Hydration) were completed out of 7 days.\n"
            "2. Identify behavioral, physical, or medical patterns (e.g., repeating joint pain, mood declines, sleeping too much, declining water intake).\n"
            "3. Identify recurring care plan tasks that were frequently unconfirmed (e.g., walk refused multiple times).\n"
            "4. Formulate a synthesized weekly insight.\n"
            "Be realistic, fact-based, and empathetic."
        )
        super().__init__(name="TrendAgent", system_instruction=system_instruction)

    def analyze_trends(self, history_logs: List[dict]) -> dict:
        """
        Runs longitudinal analysis over a list of past care records.
        """
        if not history_logs:
            return {
                "completion_rates": [],
                "observed_trends": [],
                "recurring_gaps": [],
                "summary_insight": "No historical log data available to analyze trends yet. Keep logging daily caregiver notes.",
                "confidence_score": 1.0,
                "reasoning_path": "No history logs provided."
            }
            
        # Clean history logs for context size
        simplified_logs = []
        for log in history_logs:
            simplified_logs.append({
                "date": log.get("date"),
                "reconciled_events": [
                    {
                        "activity": e.get("activity"),
                        "status": e.get("status"),
                        "notes": e.get("notes")
                    } for e in log.get("reconciled_events", [])
                ],
                "vitals": [
                    {
                        "vital_type": v.get("vital_type"),
                        "status": v.get("status")
                    } for v in log.get("vitals", [])
                ],
                "detected_gaps": [
                    {
                        "task_name": g.get("task_name")
                    } for g in log.get("detected_gaps", [])
                ]
            })
            
        prompt = f"Caregiver history logs for the past 7 days:\n\n{json.dumps(simplified_logs, indent=2)}"
        return self.call_llm(prompt, response_schema=TrendOutput)
