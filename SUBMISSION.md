# CareOne Kaggle Capstone Submission
## Clinical-Grade Multi-Agent Care Coordination & Longitudinal Analytics

### Track Fit
CareOne is framed for the **Healthcare/Caregiving ("Agents for Good") Track**. It addresses the massive social impact challenge of eldercare coordination, reducing care plan compliance gaps, preventing medical dosage errors, and streamlining shift handoffs for family caregivers.

---

### What The Demo Shows (Collaborative Scenario)
1. **Onboarding Authentication**: Sign in using collaborative caregiver accounts (e.g. `caregiver` / `careone` for Lead Nurse Sarah Jenkins, or `caregiver_john` / `careone` for Assistant John Doe).
2. **Multi-Patient Selection**: Use the dropdown in the navbar to switch between **Arthur** (Diabetes & Dementia) and **Eleanor** (Stage 3 CKD & Severe Hypertension) to dynamically reload clinical records.
3. **Checklist Sidebar**: Check off tasks to immediately write to the database and re-audit compliance gaps.
4. **Note Processing (Multi-Caregiver Collaboration)**: 
   - Click `Load Scenario A` (Sarah Jenkins logs first notes/vitals) and click `Process Care Note`.
   - Click `Load Scenario B` (John Doe logs subsequent shift events) and click `Process Care Note`.
5. **Observability Feed**: Open the **Observability Trace** tab to inspect execution durations (ms), confidence scores, memory context retrieved, reasoning paths, and raw output JSON for all 8 agents.
6. **Clinical PDF Export**: Click `Generate Handoff Brief` and download the formatted PDF handoff report.

---

### Multi-Agent Architecture
CareOne orchestrates **8 specialized agents** communicating via structured Pydantic schemas:
- **Note Parser Agent**: Extracts daily events, times, statuses, and qualitative notes.
- **Vitals Validator Agent**: Parses BP, glucose, and fluids against adult clinical parameters.
- **Reconciliation Agent**: Synthesizes multiple caregiver reports and flags direct contradictions.
- **Refusal Handling Agent**: Suggests compliance strategies and intercepts out-of-scope medical requests.
- **Gap Detector Agent**: Checks completed logs against the baseline care plan routine (phrased as `"unconfirmed"`).
- **Risk Assessment Agent [NEW]**: Calculates a daily safety risk score (Critical, High, Medium, Low) with indicators.
- **Trend Analysis Agent**: Queries 7-day logs to evaluate longitudinal wellness trends and writes recurring gaps back to memory.
- **Care Summary Agent**: Generates the final daily caregiver briefings.

---

### Reliability & Deployment
- **API key**: Uses `google-genai` SDK.
- **Storage**: MongoDB with automatic local encrypted JSON file fallback.
- **Security**: Symmetrically encrypts PHI data (notes and vitals) in storage via `cryptography.fernet`. Writes immutable logs to `security_audit_log`.

#### Run Locally
```bash
.venv\Scripts\python.exe app.py
```
Open: `http://localhost:8501`

#### Docker Compose (App + MongoDB)
```bash
docker-compose up --build
```

#### Evaluation Tests
```bash
.venv\Scripts\python.exe -m unittest test_pipeline.py
```
