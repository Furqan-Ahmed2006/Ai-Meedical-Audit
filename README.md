# 🩺 MedAudit AI — Clinical Chart Review Engine

High-speed, AI-powered clinical chart review and audit engine. Automatically extracts clinical entities, verifies ICD-10 codes with NIH Clinical Tables, detects FDA drug label warnings, and screens drug-drug interaction signals from OpenFDA adverse event databases.

---

## ⚡ Performance & Key Features

- **Ultra-Fast Speed**: Audits complete in **5 to 10 seconds** (down from 1-2 minutes).
- **Concurrent API Execution**: Uses multi-threaded parallel lookups to NIH NLM and FDA databases simultaneously.
- **Zero-Crash Resilience**: Multi-model LLM failover, robust JSON repair, and LRU API caching.
- **Dual Input Modes**: Upload clinical charts as **PDF / DOCX** or paste text directly into the UI.
- **Evidence-Based Reports**: Returns severity-ranked audit findings (`HIGH`, `MODERATE`, `LOW`, `INFO`) with exact citations.

---

## 🚀 Local Installation & Quickstart

### 1. Prerequisites
Ensure you have Python 3.10+ installed.

### 2. Clone & Install Dependencies
```bash
cd ai-medical-audit
pip install -r requirements.txt
```

### 3. Set Up Environment Variables
Create a `.env` file in the root directory:
```env
GROQ_API_KEY=your_groq_api_key_here
```

### 4. Run the Streamlit Application
```bash
streamlit run app.py
```

---

## ☁️ Deployment Guide (Streamlit Cloud)

Follow these steps to deploy this application to **Streamlit Cloud**:

1. **Push to GitHub**:
   Upload/push your `ai-medical-audit` directory to a GitHub repository.

2. **Deploy on Streamlit Cloud**:
   - Go to [share.streamlit.io](https://share.streamlit.io) and log in with your GitHub account.
   - Click **New app**.
   - Select your Repository, Branch (`main`), and set **Main file path** to `app.py`.

3. **Configure Secrets**:
   - Click **Advanced settings...** -> **Secrets**.
   - Add your Groq API Key:
     ```toml
     GROQ_API_KEY = "gsk_your_actual_groq_api_key_here"
     ```
   - Click **Deploy**!

---

## 🏗️ System Architecture

```
[Clinical Chart / PDF / Text Input]
               │
               ▼
[Stage 1: Entity Extraction & Tool Plan] ── (~2.0s)
               │
               ▼
[Stage 2: Parallel Tool Execution Engine] ── (~1.0s)
  ├── 🏥 NLM Clinical Tables (ICD-10 Search)
  ├── 💊 FDA Drug Label API (Warnings & Indications)
  └── ⚡ OpenFDA Event API (Drug Interaction Signals)
               │
               ▼
[Stage 3: Reporter Synthesis & JSON Verification] ── (~2.5s)
               │
               ▼
[Interactive Clinical Audit Dashboard UI]
```
