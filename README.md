# CareOne
Clinical-Grade Multi-Agent Care Coordination & Longitudinal Analytics
Kaggle AI Agents Capstone Project — "Agents for Good" (Healthcare/Caregiving) Track

---

## 1. Problem

Eldercare coordination is often fragmented and chaotic. Family members and professional caregivers log patient observations across text messages, notebooks, and verbal handoffs. This unstructured format results in:
* **Missed Medical Activities**: Critical duties like medication timings, food/fluid intake, and symptom monitoring are frequently unconfirmed.
* **Safety Gaps**: High-priority safety risks (e.g., elevated blood pressure, abnormal glucose levels, mobility flags) are ignored or not cross-referenced against historical trends.
* **Lack of Observability**: Families and care coordinators lack access to structured longitudinal trends, compliance summaries, or secure EMR systems.
* **Regulatory Compliance Issues**: Patient health information (PHI) is often transmitted over insecure channels, violating privacy and security standards.

---

## 2. Solution

CareOne solves this coordination challenge by serving as an automated, intelligent EMR and coordination hub.

### Core Capabilities:
* **Multi-Agent Orchestration**: Directs caregiver text entries through a pipeline of specialized AI agents that extract vitals, audit routines, compute safety indexes, and synthesize narrative briefs.
* **HIPAA-Compliant PHI Security**: Symmetrically encrypts all patient data and vital readings at rest using AES-based Fernet cryptography.
* **EMR Analytics**: Generates real-time, interactive SVG charts monitoring routine compliance, blood pressure, heart rate, hydration, medication logs, and safety scores.
* **Clinical Handoff Documentation**: Generates structured PDF and Microsoft Word summaries for clinical handoffs.
* **Robust Database Sync**: Syncs data to MongoDB Atlas with an automatic local JSON file fallback for offline availability.

---

## 3. Architecture

CareOne operates on a sequential, multi-agent pipeline using Pydantic structured output validation.

### Architecture Flowchart:
```
                        ┌─────────────────────────────────┐
                        │      FastAPI Studio Dashboard   │
                        │      (Port 8501 SaaS UI)        │
                        └────────────────┬────────────────┘
                                         │
                                         ▼
                        ┌─────────────────────────────────┐
                        │    Multi-Agent Pipeline         │
                        │    (Orchestrated via Pydantic)  │
                        └────────┬────────────────────────┘
                                 │
         ┌───────────────────────┼────────────────────────┐
         │                       │                        │
         ▼                       ▼                        ▼
┌──────────────────┐   ┌──────────────────┐   ┌──────────────────┐
│   Parser Agent   │   │   Vitals Agent   │   │Reconciliation Agt│
│  (Entity Ext.)   │   │  (Vital Mapping) │   │ (Event Reconcile)│
└──────────────────┘   └──────────────────┘   └──────────────────┘
         │                       │                        │
         ▼                       ▼                        ▼
┌──────────────────┐   ┌──────────────────┐   ┌──────────────────┐
│  Refusal Agent   │   │   Gaps Agent     │   │   Risk Agent     │
│ (Safety Inter.)  │   │  (Schedule Aud.) │   │  (Safety Index)  │
└──────────────────┘   └──────────────────┘   └──────────────────┘
         │                       │                        │
         ▼                       ▼                        ▼
┌──────────────────┐   ┌──────────────────┐   ┌──────────────────┐
│   Trends Agent   │   │  Summary Agent   │   │  Memory & Profile│
│  (7-day Trends)  │   │(Shift Narrative) │   │ (HIPAA Encrypted)│
└──────────────────┘   └──────────────────┘   └──────────────────┘
                                                           │
                                                           ▼
                                              ┌──────────────────┐
                                              │ MongoDB / JSON   │
                                              │ (Encrypted PHI)  │
                                              └──────────────────┘
```

---

## 4. Instructions for Setup

### 1. Prerequisites
Ensure Python 3.10+ is installed on your system.

### 2. Install Packages
```bash
# Clone the repository
git clone https://github.com/your-username/careone.git
cd careone

# Create and activate virtual environment
python -m venv .venv
source .venv/bin/activate  # On Windows: .venv\Scripts\activate

# Install requirements
pip install -r requirements.txt
```

### 3. Environment Variables
Create a `.env` file in the project root folder:
```env
# 1. Google Gemini configuration
GEMINI_API_KEY="your-api-key-here"

# 2. Database configuration
MONGO_URI="mongodb+srv://<db_user>:<db_password>@cluster.xxxxxx.mongodb.net/CareOne?retryWrites=true&w=majority"
MONGO_DB_NAME="CareOne"

# 3. Model configurations
CAREONE_LIVE_LLM=1 # Set to 1 for live Gemini models, 0 for fast local mock responses
```

### 4. Running the Dashboard
```bash
python web_app.py
```
*Access the SaaS studio dashboard at:* **`http://127.0.0.1:8501`**

### 5. Running the Sandbox Console
```bash
python app.py
```
*Access the sandbox at:* **`http://localhost:7860`**

### 6. Executing Unit Tests
```bash
python -m unittest test_pipeline.py
```
