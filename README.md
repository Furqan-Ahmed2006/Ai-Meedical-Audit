# 🩺 MedAudit AI — Clinical Chart Review Engine

MedAudit AI is a high-performance clinical chart review and audit engine that automates evidence-based chart abstraction and compliance checks. It was built to solve the slow, manual, and error-prone process of clinical chart review by extracting structured clinical entities, validating diagnostic codes, detecting safety concerns from regulatory sources, and producing prioritized, citation-backed audit findings.


---

## Problem Statement

Clinical chart review is labor-intensive and inconsistent: manual reviewers must read unstructured notes, identify diagnoses, medications, and relevant findings, then cross-check codes and safety warnings against external authoritative sources. This process is time-consuming, expensive, and susceptible to human error. MedAudit AI addresses these challenges by automating extraction, verification, and evidence-based reporting so teams can perform scalable, reproducible audits.

---

## What this project solves

- Rapidly extracts clinical entities (diagnoses, procedures, medications, signs/symptoms) from unstructured clinical text and common document formats (PDF/DOCX).
- Verifies ICD-10 and related clinical concepts against NIH/NLM Clinical Tables to reduce coding errors.
- Screens medication data against FDA drug label endpoints and OpenFDA signals to flag warnings, contraindications, and interactions.
- Produces severity-ranked, evidence-backed audit findings with exact citations and machine-verifiable JSON output for downstream processing.

---

## What I implemented

- Entity extraction pipeline using LLM-based parsing and deterministic post-processing to produce structured JSON records.
- Parallel tool execution engine that performs concurrent lookups to NLM Clinical Tables, FDA Drug Label APIs, and OpenFDA event endpoints to maximize throughput and minimize latency.
- Multi-model LLM failover and JSON-repair routines to improve resilience against model hallucination and malformed outputs.
- LRU API response caching and concurrent threading to achieve audit response times of 5–10 seconds in typical cases.
- Interactive Streamlit dashboard for uploading charts (PDF/DOCX) or pasting text, reviewing findings, and exporting audit reports.

---

## Key features

- Fast, evidence-based clinical audits in 5–10 seconds.
- Parallel API lookups to authoritative sources (NLM, FDA, OpenFDA).
- Robust JSON verification and automatic repair logic.
- Dual input modes: upload PDF/DOCX or paste text.
- Severity-ranked findings (`HIGH`, `MODERATE`, `LOW`, `INFO`) with source citations and links.
- Exportable audit reports and machine-readable JSON for integration with downstream systems.

---

## System architecture

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

---

## Quickstart — Local Development

1. Prerequisites

- Python 3.10 or newer

2. Clone and install

```bash
git clone https://github.com/Furqan-Ahmed2006/Ai-Meedical-Audit.git
cd Ai-Meedical-Audit
pip install -r requirements.txt
```

3. Environment

Create a `.env` file in the project root and add required secrets. Example:

```env
GROQ_API_KEY=your_groq_api_key_here
```

(If additional API keys are required for NLM/FDA access, add them similarly.)

4. Run the app

```bash
streamlit run app.py
```

---



---

## Live demo

Try the running demo here:

https://ai-meedical-audit-pw7qvxmq3m6rpxusstkzmd.streamlit.app/

---

## Contributing

Contributions, bug reports, and improvements are welcome. Please open issues or pull requests with clear descriptions and reproducible steps.

---

