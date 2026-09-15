import io
import json
import time
from dotenv import load_dotenv
import streamlit as st
from pypdf import PdfReader
from docx import Document

from agent import run_audit_agent

load_dotenv()

st.set_page_config(
    page_title="MedAudit AI — Clinical Chart Review",
    page_icon="🩺",
    layout="wide",
    initial_sidebar_state="expanded",
)
st.markdown("""
<style>
    .stApp { background: #f8fafc; }
    #MainMenu, footer { visibility: hidden; }

    .hero {
        background: linear-gradient(135deg, #0f766e 0%, #0ea5e9 100%);
        padding: 2rem 2rem;
        border-radius: 18px;
        color: white;
        margin-bottom: 1.5rem;
        box-shadow: 0 10px 25px rgba(14, 165, 233, 0.15);
    }
    .hero h1 {
        margin: 0;
        font-size: 2.1rem;
        font-weight: 700;
        letter-spacing: -0.5px;
    }
    .hero p {
        margin: 0.5rem 0 0;
        opacity: 0.95;
        font-size: 1rem;
    }

    .guide-card {
        background: white;
        border-radius: 12px;
        padding: 1.2rem;
        box-shadow: 0 2px 8px rgba(0,0,0,0.03);
        border: 1px solid #e2e8f0;
        height: 100%;
    }
    .guide-card h4 {
        color: #0f766e;
        margin: 0 0 0.5rem;
        font-size: 0.95rem;
    }
    .guide-card p, .guide-card li {
        color: #475569;
        font-size: 0.88rem;
        line-height: 1.5;
        margin: 0;
    }
    .guide-card ul { padding-left: 1.1rem; margin: 0; }

    div[data-testid="stMetric"] {
        background: white;
        padding: 1rem;
        border-radius: 12px;
        border: 1px solid #e2e8f0;
        box-shadow: 0 1px 4px rgba(0,0,0,0.02);
    }
    div[data-testid="stMetricLabel"] { font-weight: 600; color: #64748b; }
    div[data-testid="stMetricValue"] { font-size: 1.7rem; color: #0f172a; }

    .finding {
        padding: 1rem 1.1rem;
        border-radius: 12px;
        margin-bottom: 0.8rem;
        background: white;
        border: 1px solid #e2e8f0;
        border-left: 5px solid #cbd5e0;
        box-shadow: 0 1px 4px rgba(0,0,0,0.02);
    }
    .finding.high     { border-left-color: #dc2626; background: #fef2f2; }
    .finding.moderate { border-left-color: #ea580c; background: #fff7ed; }
    .finding.low      { border-left-color: #16a34a; background: #f0fdf4; }
    .finding.info     { border-left-color: #0284c7; background: #f0f9ff; }

    .badge {
        display: inline-block;
        padding: 3px 10px;
        border-radius: 12px;
        font-size: 10px;
        font-weight: 800;
        text-transform: uppercase;
        letter-spacing: 0.5px;
    }
    .badge.high     { background: #fee2e2; color: #991b1b; }
    .badge.moderate { background: #fed7aa; color: #9a3412; }
    .badge.low      { background: #dcfce7; color: #166534; }
    .badge.info     { background: #dbeafe; color: #1e40af; }

    .finding-title {
        font-weight: 700;
        color: #0f172a;
        font-size: 0.95rem;
        margin-left: 6px;
    }
    .finding-line {
        color: #334155;
        font-size: 0.9rem;
        line-height: 1.5;
        margin: 6px 0 2px;
    }

    .stButton > button {
        background: linear-gradient(135deg, #0f766e, #0ea5e9);
        color: white;
        border: none;
        padding: 0.75rem 1.8rem;
        border-radius: 10px;
        font-weight: 600;
        font-size: 0.98rem;
        transition: all 0.2s;
        box-shadow: 0 4px 12px rgba(14, 165, 233, 0.2);
    }
    .stButton > button:hover {
        transform: translateY(-1px);
        box-shadow: 0 6px 16px rgba(14, 165, 233, 0.3);
    }
</style>
""", unsafe_allow_html=True)

with st.sidebar:
    st.image("https://img.icons8.com/color/96/medical-doctor.png", width=64)
    st.title("MedAudit AI")
    st.caption("Clinical Chart Review Engine")
    
    st.divider()
    st.markdown("""
    ### 🛡️ System Features
    - 🏥 **Real-time NIH ICD-10** coding checks
    - 💊 **FDA Drug Label** boxed warning analysis
    - ⚡ **OpenFDA Adverse Event** interaction signals
    - 📋 **Automated Entity Extraction** & evidence trail
    """)
    st.divider()

st.markdown("""
<div class="hero">
    <h1>🩺 MedAudit AI Engine</h1>
    <p>Real-time clinical chart auditing — Instant safety, coding & interaction checks powered by FDA & NLM APIs</p>
</div>
""", unsafe_allow_html=True)

with st.expander("📖 Quick Guide & Sample Instructions", expanded=False):
    c1, c2, c3 = st.columns(3)
    with c1:
        st.markdown("""
<div class="guide-card">
    <h4>1. Input Document </h4>
    <p>Upload a clinical note (<strong>PDF/DOCX</strong>) </p>
</div>
""", unsafe_allow_html=True)
    with c2:
        st.markdown("""
<div class="guide-card">
    <h4>2. Run Clinical Audit</h4>
    <p>Click <strong>Run Clinical Audit</strong>. The engine executes parallel database lookups automatically.</p>
</div>
""", unsafe_allow_html=True)
    with c3:
        st.markdown("""
<div class="guide-card">
    <h4>3. Review Evidence & Export</h4>
    <p>Inspect severity flags, supporting FDA/NIH citations, and download JSON reports.</p>
</div>
""", unsafe_allow_html=True)

st.write("")
st.subheader("📄 Clinical Document Input")

note_text = ""
uploaded = st.file_uploader(
    "Drop a PDF or DOCX file here",
    type=["pdf", "docx"],
    label_visibility="collapsed",
    key="file_uploader_key"
)
if uploaded is not None:
    file_size_kb = len(uploaded.getvalue()) / 1024
    if uploaded.name.lower().endswith(".pdf"):
        try:
            reader = PdfReader(io.BytesIO(uploaded.getvalue()))
            note_text = "\n".join((page.extract_text() or "") for page in reader.pages)
            st.success(f"✅ **{uploaded.name}** loaded — {len(reader.pages)} page(s), {file_size_kb:.1f} KB")
        except Exception as e:
            st.error(f"Could not read PDF: {e}")
    elif uploaded.name.lower().endswith(".docx"):
        try:
            doc = Document(io.BytesIO(uploaded.getvalue()))
            note_text = "\n".join([p.text for p in doc.paragraphs if p.text])
            st.success(f"✅ **{uploaded.name}** loaded — {len(doc.paragraphs)} paragraph(s), {file_size_kb:.1f} KB")
        except Exception as e:
            st.error(f"Could not read DOCX: {e}")

if note_text:
    with st.expander("👁️ Inspect Loaded Note Text", expanded=False):
        st.text_area("Note Text", note_text, height=140, disabled=True, label_visibility="collapsed")

st.write("")

if not note_text.strip():
    st.info("⬆️ Upload a document above to begin audit.")
    run = False
else:
    run = st.button("🔍 Run Clinical Audit", type="primary", use_container_width=True)

if run:
    status_box = st.status("🔍 Auditing Clinical Chart...", expanded=True)
    start_time = time.time()
    
    try:
        # Stage 1
        status_box.update(label="⚙️ Stage 1/3: Extracting clinical entities & planning audit...", state="running")
        status_box.write("⚙️ Stage 1: Parsing unstructured text and building tool parameters...")
        time.sleep(1.2)
        
        # Stage 2 Execution & Spinner Update
        status_box.update(label="⚡ Stage 2/3: Querying NIH ICD-10 & OpenFDA Databases...", state="running")
        status_box.write("⚡ Stage 2: Executing parallel API calls for drug warnings & ICD codes...")
        result = run_audit_agent(note_text)
        time.sleep(1.2)
        
        # Stage 3
        status_box.update(label="✍️ Stage 3/3: Synthesizing clinical evidence & writing audit report...", state="running")
        status_box.write("✍️ Stage 3: Compiling findings, severity risk signals, and final recommendations...")
        time.sleep(1.0)
        
        elapsed = time.time() - start_time
        status_box.update(label=f"✅ Audit Complete in {elapsed:.2f} seconds!", state="complete", expanded=False)
        
        st.session_state["audit_result"] = result
        st.session_state["elapsed"] = elapsed
        st.rerun()

    except Exception as e:
        status_box.update(label=f"❌ Audit Encountered an Issue: {e}", state="error", expanded=True)
        st.error(f"An unexpected error occurred during audit execution: {e}")

if "audit_result" in st.session_state:
    result = st.session_state["audit_result"]
    report = result.get("audit_report", {})
    tool_calls = result.get("tool_calls", [])
    extracted = result.get("extracted", {})
    findings = report.get("audit_findings", [])
    elapsed = st.session_state.get("elapsed", 0.0)

    st.divider()
    st.subheader("📊 Clinical Audit Summary")

    high_count = sum(1 for f in findings if (f.get("severity") or "").lower() == "high")
    mod_count = sum(1 for f in findings if (f.get("severity") or "").lower() == "moderate")

    m1, m2, m3, m4 = st.columns(4)
    m1.metric("Total Findings", len(findings))
    m2.metric("High-Risk Flags", high_count)
    m3.metric("API Lookups", len(tool_calls))
    m4.metric("Processing Time", f"{elapsed:.2f}s")

    if report.get("requires_human_review") or high_count > 0:
        st.error("🚨 **Human Review Required** — One or more high-severity clinical safety/interaction issues detected.")
    else:
        st.success("✅ **No High-Severity Risk Detected** — Routine physician/pharmacist review sufficient.")

    t1, t2, t3, t4 = st.tabs(
        ["🚩 Audit Findings", "📋 Extracted Data", "🧾 Evidence Trail", "📄 Full JSON Report"]
    )

    with t1:
        if report.get("summary"):
            st.info(f"**Executive Summary:** {report['summary']}")
            st.write("")

        if not findings:
            st.success("No audit flags or clinical warnings found.")
        else:
            for f in findings:
                sev = (f.get("severity") or "info").lower()
                st.markdown(f"""
<div class="finding {sev}">
    <span class="badge {sev}">{sev}</span>
    <span class="finding-title">[{f.get('category','').upper()}] {f.get('subject','')}</span>
    <p class="finding-line"><strong>Issue:</strong> {f.get('issue','')}</p>
    <p class="finding-line"><strong>Evidence:</strong> <em>{f.get('evidence','')}</em></p>
    <p class="finding-line"><strong>Recommendation:</strong> {f.get('recommendation','')}</p>
</div>
""", unsafe_allow_html=True)

    with t2:
        st.caption("Structured entities extracted from doctor note during audit planning.")
        st.json(extracted if extracted else {})

    with t3:
        st.caption(f"{len(tool_calls)} external NIH ICD-10 & FDA API lookups executed concurrently.")
        if not tool_calls:
            st.info("No external lookups were required for this chart.")
        for i, tc in enumerate(tool_calls, 1):
            title = tc.get("tool", "lookup").replace("_", " ").title()
            with st.expander(f"{i}. {title}"):
                st.markdown("**Query Input**")
                st.code(json.dumps(tc.get("input", {}), indent=2), language="json")
                st.markdown("**API Response Output**")
                st.code(tc.get("output") or "(no result)", language="text")

    with t4:
        st.json(report)
        st.download_button(
            "⬇️ Download Audit Report (JSON)",
            data=json.dumps(report, indent=2),
            file_name="clinical_audit_report.json",
            mime="application/json",
            use_container_width=True
        )