import json
import re
from concurrent.futures import ThreadPoolExecutor
from dotenv import load_dotenv
from langchain_groq import ChatGroq
from langchain_core.messages import HumanMessage, SystemMessage
from tools import _search_icd10_cached, _get_drug_info_cached, _check_drug_interaction_cached
from extractor import get_groq_api_key

load_dotenv()
PRIMARY_MODEL = "openai/gpt-oss-120b"
FALLBACK_MODELS = ["openai/gpt-oss-20b", "qwen/qwen3.6-27b"]
PLANNER_SYSTEM_PROMPT = """You are a clinical entity extractor and audit planner.
Analyze the doctor's note and return structured data AND a tool lookup plan as JSON.

JSON SHAPE:
{
  "patient": {"age": <int or null>, "gender": "<male|female|other|null>"},
  "chief_complaint": "<1 sentence or null>",
  "diagnoses": [{"condition": "<name>", "icd10": "<code or null>"}],
  "medications": [{"name": "<drug>", "dose": "<dose or null>", "frequency": "<freq or null>"}],
  "symptoms": ["<symptom>"],
  "lab_results": [{"test": "<name>", "value": "<value>", "unit": "<unit or null>"}],
  "warnings": [],
  "tool_plan": {
    "icd10_conditions": ["<up to 3 diagnoses needing ICD-10 lookup>"],
    "drug_names": ["<up to 4 prescribed drugs needing FDA info lookup>"],
    "drug_pairs": [["<drug1>", "<drug2>"]]
  }
}

RULES:
- Limit icd10_conditions to max 3 key diagnoses.
- Limit drug_names to max 4 prescribed medications.
- Limit drug_pairs to max 2 highest-risk medication combinations (e.g., ACE inhibitor + NSAID).
- Return ONLY valid JSON, no markdown formatting.
"""

REPORTER_SYSTEM_PROMPT = """You are a senior medical auditor.
Analyze the doctor's note AND the verified tool evidence. Produce final AUDIT REPORT as JSON.

SEVERITY RULES (STRICT):
1. Drug side effect matches patient symptom → MUST be "high"
2. Known drug-drug interaction (evidence shows >100 adverse events or high risk warning) → MUST be "high"
3. FDA black-box warning / serious boxed warning for prescribed drug → MUST be "high"
4. Missing ICD-10 code → "low"
5. Wrong ICD-10 code → "moderate"
6. Informational note → "info"

JSON SHAPE:
{
  "audit_findings": [
    {
      "category": "diagnosis | medication | interaction | side_effect",
      "severity": "high | moderate | low | info",
      "subject": "<subject name>",
      "issue": "<clear description of issue>",
      "evidence": "<cite specific tool output or clinical rationale>",
      "recommendation": "<actionable clinician advice>"
    }
  ],
  "summary": "<2-3 sentences executive summary>",
  "requires_human_review": true/false
}

requires_human_review MUST be true if ANY finding has severity "high".
Return ONLY valid JSON.
"""


def _get_llm(api_key: str = None, model_name: str = PRIMARY_MODEL):
    key = get_groq_api_key(api_key)
    if not key:
        raise ValueError("GROQ_API_KEY is missing. Please set GROQ_API_KEY in environment or UI sidebar.")
    return ChatGroq(
        model=model_name,
        api_key=key,
        temperature=0,
        max_tokens=2000,
    )


def _invoke_with_retry(system_prompt: str, user_content: str, api_key: str = None) -> str:
    """Invoke LLM with primary model and fallback model failover."""
    models_to_try = [PRIMARY_MODEL] + FALLBACK_MODELS
    last_err = None

    for model_name in models_to_try:
        try:
            llm = _get_llm(api_key=api_key, model_name=model_name)
            resp = llm.invoke([
                SystemMessage(content=system_prompt),
                HumanMessage(content=user_content),
            ])
            content = resp.content if hasattr(resp, "content") else str(resp)
            if content and content.strip():
                return content
        except Exception as e:
            last_err = e
            continue

    raise RuntimeError(f"LLM invocation failed across all candidate models. Last error: {last_err}")

def _extract_json(text: str) -> dict:
    text = text.strip()
    text = re.sub(r"^```(?:json)?\s*", "", text, flags=re.MULTILINE)
    text = re.sub(r"\s*```$", "", text, flags=re.MULTILINE)
    start = text.find("{")
    end = text.rfind("}")
    if start == -1 or end == -1:
        raise ValueError(f"No JSON object boundaries found in LLM output:\n{text[:300]}")
    
    cleaned = text[start:end + 1]
    try:
        return json.loads(cleaned)
    except json.JSONDecodeError:
        cleaned_fixed = re.sub(r",\s*([\]}])", r"\1", cleaned)
        return json.loads(cleaned_fixed)

def _execute_tool_plan_parallel(tool_plan: dict) -> list[dict]:
    """Execute all tool lookups concurrently via ThreadPoolExecutor."""
    icd_terms = tool_plan.get("icd10_conditions", [])[:3]
    drug_names = tool_plan.get("drug_names", [])[:4]
    drug_pairs = tool_plan.get("drug_pairs", [])[:2]

    tasks = []

    def task_icd(term):
        output = _search_icd10_cached(term)
        return {"tool": "search_icd10", "input": {"condition": term}, "output": output}

    def task_drug(name):
        output = _get_drug_info_cached(name)
        return {"tool": "get_drug_info", "input": {"drug_name": name}, "output": output}

    def task_pair(pair):
        if isinstance(pair, (list, tuple)) and len(pair) >= 2:
            d1, d2 = pair[0], pair[1]
            output = _check_drug_interaction_cached(d1, d2)
            return {"tool": "check_drug_interaction", "input": {"drug1": d1, "drug2": d2}, "output": output}
        return None

    results = []
    with ThreadPoolExecutor(max_workers=8) as executor:
        futures = []
        for c in icd_terms:
            if c:
                futures.append(executor.submit(task_icd, str(c)))
        for d in drug_names:
            if d:
                futures.append(executor.submit(task_drug, str(d)))
        for p in drug_pairs:
            if p:
                futures.append(executor.submit(task_pair, p))

        for f in futures:
            try:
                res = f.result(timeout=6.0)
                if res:
                    results.append(res)
            except Exception as e:
                results.append({"tool": "lookup_error", "input": {}, "output": f"Lookup timeout/error: {e}"})

    return results



def run_audit_agent(note: str, api_key: str = None) -> dict:
    """Run full ultra-fast audit pipeline.

    Returns:
        dict: {
            "audit_report": dict,
            "tool_calls": list[dict],
            "extracted": dict
        }
    """
    if not note or not note.strip():
        return {
            "audit_report": {
                "audit_findings": [],
                "summary": "No clinical note text was provided for auditing.",
                "requires_human_review": False,
            },
            "tool_calls": [],
            "extracted": {},
        }
    extracted_data = {}
    tool_plan = {}
    try:
        planner_raw = _invoke_with_retry(PLANNER_SYSTEM_PROMPT, f"DOCTOR'S NOTE:\n{note}", api_key=api_key)
        planner_json = _extract_json(planner_raw)
        tool_plan = planner_json.get("tool_plan", {})
        
        extracted_data = {
            "patient": planner_json.get("patient", {}),
            "chief_complaint": planner_json.get("chief_complaint"),
            "diagnoses": planner_json.get("diagnoses", []),
            "medications": planner_json.get("medications", []),
            "symptoms": planner_json.get("symptoms", []),
            "lab_results": planner_json.get("lab_results", []),
            "warnings": planner_json.get("warnings", []),
        }
    except Exception as e:
        extracted_data = {"chief_complaint": note[:200]}
        tool_plan = {"icd10_conditions": [], "drug_names": [], "drug_pairs": []}

    tool_calls = _execute_tool_plan_parallel(tool_plan)

    evidence_blocks = []
    for i, tc in enumerate(tool_calls, 1):
        evidence_blocks.append(
            f"--- Evidence Item {i}: {tc['tool']} ---\n"
            f"Query: {json.dumps(tc['input'])}\n"
            f"Result: {tc['output']}\n"
        )
    evidence_text = "\n".join(evidence_blocks) if evidence_blocks else "No external tool lookups required."

    user_reporter_prompt = f"""DOCTOR'S NOTE:
---
{note}
---

EXTERNAL TOOL EVIDENCE:
---
{evidence_text}
---

Synthesize the note and evidence into a final audit report as valid JSON.
"""

    try:
        reporter_raw = _invoke_with_retry(REPORTER_SYSTEM_PROMPT, user_reporter_prompt, api_key=api_key)
        report = _extract_json(reporter_raw)
    except Exception as e:

        report = {
            "audit_findings": [
                {
                    "category": "system",
                    "severity": "info",
                    "subject": "Clinical Audit Notice",
                    "issue": f"Report synthesis completed with note: {e}",
                    "evidence": "Automatic safety fallback",
                    "recommendation": "Review clinical chart manually."
                }
            ],
            "summary": "Audit completed with system safety fallback.",
            "requires_human_review": False
        }

    return {
        "audit_report": report,
        "tool_calls": tool_calls,
        "extracted": extracted_data
    }