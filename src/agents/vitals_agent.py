from pydantic import BaseModel, Field
from typing import List, Optional
from src.agents.base_agent import BaseAgent

class VitalReading(BaseModel):
    vital_type: str = Field(
        ..., 
        description="Type of vital. Must be one of: Blood Pressure, Blood Glucose, Temperature, Weight, Heart Rate, Oxygen Level, Fluid Intake, Other."
    )
    value_raw: str = Field(
        ..., 
        description="The raw value from the caregiver note (e.g. '145/92', '98.6 F', '112', '1400ml')."
    )
    status: str = Field(
        ..., 
        description="Classification of the measurement. Must be one of: Normal, Elevated, High/Alert, Low, Warning, Unknown."
    )
    explanation: str = Field(
        ..., 
        description="Brief clinical rationale for the status (e.g. 'Systolic pressure of 145 mmHg is Stage 2 Hypertension', 'Fluid intake of 1650ml exceeds target 1500ml limit')."
    )

class VitalsOutput(BaseModel):
    readings: List[VitalReading] = Field(
        ..., 
        description="List of parsed vital readings."
    )
    confidence_score: float = Field(
        ...,
        description="Confidence score between 0.0 and 1.0 of the vitals extraction and validation."
    )
    reasoning_path: str = Field(
        ...,
        description="Explanation of how the vitals were extracted and classified against clinical limits."
    )

class VitalsAgent(BaseAgent):
    def __init__(self):
        system_instruction = (
            "You are the Medical Vitals Validator Agent of CareOne. Your job is to extract and validate health metrics "
            "from unstructured caregiver logs.\n"
            "Analyze the text carefully. Look for measurements such as blood pressure (BP), blood glucose, heart rate (pulse), oxygen levels, temperature, and fluid intake.\n"
            "Classify each reading using standard adult clinical baselines:\n"
            "- Blood Pressure: Normal (<120/80), Elevated (120-129/<80), High/Alert (>=130 systolic OR >=80 diastolic, e.g. 140/90 is High/Alert).\n"
            "- Blood Glucose: Normal (70-100 fasting, <140 post-meal), Elevated (100-125 fasting, 140-199 post-meal), High/Alert (>=126 fasting or >=200 post-meal, or generally >180).\n"
            "- Temperature: Normal (97.0F - 99.0F), Elevated (99.1F - 100.3F), High/Alert (>=100.4F / fever, or <95.0F / hypothermia).\n"
            "- Heart Rate: Normal (60-100 bpm), High/Alert (>100 bpm or <60 bpm).\n"
            "- Oxygen Level (SpO2): Normal (95%-100%), Low/Alert (<95%).\n"
            "- Fluid Intake (especially for CKD patients): Normal (<= 1500ml), Warning (> 1500ml).\n"
            "If no measurements are mentioned, return an empty list of readings."
        )
        super().__init__(name="VitalsAgent", system_instruction=system_instruction)

    def extract_vitals(self, note: str) -> dict:
        """
        Parses caregiver note to extract and validate vitals.
        """
        prompt = f"Caregiver Note to analyze:\n\n{note}"
        return self.call_llm(prompt, response_schema=VitalsOutput)
