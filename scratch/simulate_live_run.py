import os
import sys

# Add parent directory to path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.pipeline import run_careone_pipeline
from src.memory import save_day_record

def main():
    date_str = "2026-06-24"
    
    # Reset today's record to start fresh
    save_day_record(date_str, None)
    
    print("[CareOne] Triggering Live CareOne 7-Agent Pipeline...")
    print("Ingesting caregiver report...")
    
    note = (
        "Gave Dad lunch, but morning meds were delayed. "
        "He refused his morning walk because his knees were hurting. "
        "Checked his blood pressure: 145/92."
    )
    
    try:
        record, trace = run_careone_pipeline(
            date_str=date_str,
            caregiver_name="Caregiver A (Morning Shift)",
            raw_note=note
        )
        
        print("\n[OK] Pipeline completed successfully! Live LLM outputs retrieved.\n")
        print("="*60)
        print("DAILY EXECUTIVE SUMMARY")
        print("="*60)
        print(record["summary"].get("executive_summary"))
        print("\n" + "="*60)
        
        print("EXTRACTED VITALS:")
        for vit in record.get("vitals", []):
            print(f"- {vit['vital_type']}: {vit['value_raw']} (Classification: {vit['status']})")
            print(f"  Rationale: {vit['explanation']}")
            
        print("\nCLINICAL SAFETY ALERTS:")
        for alert in record["summary"].get("safety_alerts", []):
            print(f"- {alert}")
            
        print("\nREFUSAL INTERVENTIONS:")
        for inter in record.get("interventions", []):
            print(f"- Activity: {inter['activity']}")
            print(f"  Reason: {inter['stated_reason']}")
            print(f"  Caregiver Strategy: {inter['strategy']}")
            
        print("\nDETECTED CARE GAPS:")
        for gap in record.get("detected_gaps", []):
            print(f"- {gap['task_name']} (Importance: {gap['importance']})")
            print(f"  Explanation: {gap['explanation']}")
            
    except Exception as e:
        print(f"\n[Error] during live run: {e}")
        print("Please check that your GEMINI_API_KEY is valid and has sufficient quota.")

if __name__ == "__main__":
    main()
