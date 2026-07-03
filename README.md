# CareOne

AI-powered multi-agent platform for eldercare coordination, clinical note analysis, patient monitoring, and caregiver collaboration.

CareOne transforms unstructured caregiver notes into structured patient insights using a collaborative pipeline of specialized AI agents. The platform assists caregivers by extracting vitals, identifying care gaps, assessing potential risks, generating concise summaries, and maintaining a longitudinal patient record through an intuitive web interface.

---

## Table of Contents

- [Overview](#overview)
- [Problem Statement](#problem-statement)
- [Solution](#solution)
- [Key Features](#key-features)
- [Architecture](#architecture)
- [AI Agent Pipeline](#ai-agent-pipeline)
- [Technology Stack](#technology-stack)
- [Project Structure](#project-structure)
- [Installation](#installation)
- [Environment Variables](#environment-variables)
- [Running the Project](#running-the-project)
- [Future Enhancements](#future-enhancements)
- [Author](#author)

---

# Overview

CareOne is a full-stack AI-powered care coordination platform designed to improve communication between family caregivers and healthcare professionals.

Instead of manually reviewing long caregiver notes, CareOne analyzes patient observations using multiple specialized AI agents that transform free-text notes into structured clinical information, helping caregivers make informed decisions while maintaining a complete patient history.

---

# Problem Statement

Caregiver communication is often fragmented across notebooks, messaging applications, spreadsheets, and verbal handoffs. This fragmented workflow introduces several challenges:

- Medication schedules may be missed.
- Daily care activities become difficult to verify.
- Important symptoms are buried inside lengthy notes.
- Multiple caregivers often maintain inconsistent records.
- Patient progress becomes difficult to monitor over time.
- Manual documentation increases administrative workload.

As care becomes more complex, caregivers require intelligent assistance that can organize information, identify important observations, and generate meaningful summaries without replacing human decision-making.

---

# Solution

CareOne addresses these challenges through a modular multi-agent AI architecture that converts unstructured caregiver observations into structured patient insights.

The platform provides:

- Multi-agent AI pipeline for caregiver note processing
- Automatic extraction of patient vitals
- Detection of care gaps and missed activities
- Patient safety and risk assessment
- Longitudinal patient timeline
- Interactive analytics dashboard
- AI-generated caregiver handoff summaries
- PDF report generation
- Secure encrypted patient data storage
- MongoDB Atlas synchronization with local fallback support

---

# Key Features

- Multi-Agent AI Workflow
- Patient Management
- Clinical Note Analysis
- Automatic Vitals Extraction
- Risk Assessment
- Care Gap Detection
- Longitudinal Patient Timeline
- AI Summary Generation
- Analytics Dashboard
- Interactive Sandbox
- PDF Reports
- MongoDB Atlas Integration
- Local Offline Fallback
- Responsive User Interface
- Secure Authentication

---

# Architecture

CareOne follows a modular AI architecture where each specialized agent performs one focused task before passing structured information to the next stage.

```text
                              Caregiver Notes
                                     │
                                     ▼
                        ┌─────────────────────────┐
                        │   Multi-Agent Pipeline  │
                        └────────────┬────────────┘
                                     │
         ┌──────────────┬────────────┴────────────┬──────────────┐
         ▼              ▼                         ▼              ▼
    Parser Agent   Vitals Agent         Reconciliation Agent  Gap Detection Agent
         │              │                         │              │
         └──────────────┼─────────────────────────┴──────────────┘
                        │
                        ▼
               Risk Assessment Agent (Safety / Risk Index)
                        │
                        ▼
               Summary Agent (Daily Narrative Brief)
                        │
                        ▼
               Timeline Agent (Chronological ordering)
                        │
                        ▼
               Memory Agent (Long-Term Memory & Profile Sync)
                        │
                        ▼
           MongoDB Atlas / Encrypted Local Storage Fallback
```

---

# AI Agent Pipeline

| Agent | Responsibility |
|-------|----------------|
| Parser Agent | Extracts structured entities from caregiver notes |
| Vitals Agent | Identifies and validates patient vital signs |
| Reconciliation Agent | Merges related observations |
| Gap Detection Agent | Detects missing care activities |
| Risk Assessment Agent | Identifies potential safety concerns |
| Summary Agent | Generates concise shift summaries |
| Timeline Agent | Organizes patient events chronologically |
| Memory Agent | Maintains longitudinal patient history |

---

# Technology Stack

## Frontend

- HTML5
- CSS3 (Vanilla variables, glassmorphism design)
- JavaScript (Vanilla ES6 SPA router, SVG graphing)

## Backend

- FastAPI
- Python

## Database

- MongoDB Atlas (with local JSON fallback)

## Artificial Intelligence

- Google Gemini (Gemini 2.5 Flash)
- Pydantic (validation and structured outputs)
- Multi-Agent Architecture

## Security

- Fernet Encryption

## Deployment

- Render

---

# Project Structure

```text
CareOne
│
├── src/                  # Core Python modules
│   ├── agents/           # 8 specialized AI agents (Parser, Vitals, Reconciliation, etc.)
│   ├── config.py         # Google GenAI SDK client configurations
│   ├── db.py             # MongoDB connection and database seeding functions
│   ├── memory.py         # Patient profile management and local fallback handlers
│   ├── pipeline.py       # Orchestrator for the sequential multi-agent workflow
│   └── security.py       # AES-based Fernet data encryption and audit loggers
│
├── studio/               # Frontend SPA Web Client (HTML, CSS, JS)
│   ├── index.html        # Glassmorphic dashboard user interface
│   ├── styles.css        # Responsive dark/light theme stylesheet definitions
│   └── app.js            # Frontend state, API requests, and router logic
│
├── data/                 # Local encrypted JSON fallback database files
│
├── web_app.py            # FastAPI SaaS web application server
├── app.py                # Gradio dashboard sandbox application
├── test_pipeline.py      # Comprehensive pipeline unit tests
├── requirements.txt      # Python dependencies list
└── README.md             # Project documentation
```

---

# Installation

Clone the repository.

```bash
git clone https://github.com/Aangi-Shah1234/CareOne.git

cd CareOne
```

Create a virtual environment.

Windows

```bash
python -m venv .venv

.venv\Scripts\activate
```

Linux/macOS

```bash
python -m venv .venv

source .venv/bin/activate
```

Install dependencies.

```bash
pip install -r requirements.txt
```

---

# Environment Variables

Create a `.env` file.

```env
GEMINI_API_KEY=your_api_key

MONGO_URI=your_mongodb_connection_string

MONGO_DB_NAME=CareOne

CAREONE_LIVE_LLM=1
```

---

# Running the Project

Start the dashboard.

```bash
python web_app.py
```

Open:

```
http://127.0.0.1:8501
```

Run the Interactive Sandbox.

```bash
python app.py
```

---

# Future Enhancements

- Voice note processing
- Mobile application
- Medication reminders
- Wearable device integration
- Predictive health analytics
- Calendar scheduling
- Multi-language support

---

# Author

Aangi Shah
