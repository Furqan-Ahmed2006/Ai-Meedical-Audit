import requests
from functools import lru_cache
from langchain_core.tools import tool

HEADERS = {"User-Agent": "MedAuditAI/1.0 (Clinical Audit Engine)"}
DEFAULT_TIMEOUT = 4.0

@lru_cache(maxsize=128)
def _search_icd10_cached(condition: str) -> str:
    condition_clean = condition.strip().lower()
    if not condition_clean:
        return "No condition specified."
    try:
        url = "https://clinicaltables.nlm.nih.gov/api/icd10cm/v3/search"
        params = {"sf": "code,name", "terms": condition_clean, "maxList": 5}
        r = requests.get(url, params=params, headers=HEADERS, timeout=DEFAULT_TIMEOUT)
        r.raise_for_status()
        data = r.json()
        results = data[3] if len(data) > 3 else []
        if not results:
            return f"No ICD-10 code found for '{condition}'."
        lines = [f"ICD-10 results for '{condition}':"]
        for code, name in results:
            lines.append(f"  {code} — {name}")
        return "\n".join(lines)
    except Exception as e:
        return f"ICD-10 lookup for '{condition}' notice: {e}"


@lru_cache(maxsize=128)
def _get_drug_info_cached(drug_name: str) -> str:
    drug_clean = drug_name.strip().lower()
    if not drug_clean:
        return "No drug specified."
    try:
        url = "https://api.fda.gov/drug/label.json"
        params = {"search": f'openfda.generic_name:"{drug_clean}"', "limit": 1}
        r = requests.get(url, params=params, headers=HEADERS, timeout=DEFAULT_TIMEOUT)
        if r.status_code == 404:
            params = {"search": f'openfda.brand_name:"{drug_clean}"', "limit": 1}
            r = requests.get(url, params=params, headers=HEADERS, timeout=DEFAULT_TIMEOUT)
        if r.status_code == 404:
            return f"No FDA label details found for '{drug_name}'."
        r.raise_for_status()
        data = r.json()
        if not data.get("results"):
            return f"No FDA label found for '{drug_name}'."
        label = data["results"][0]
        out = [f"FDA Label for '{drug_name}':"]
        warnings = label.get("warnings") or label.get("boxed_warning") or []
        if warnings:
            out.append(f"\nWARNINGS:\n{warnings[0][:600]}")
        adverse = label.get("adverse_reactions") or []
        if adverse:
            out.append(f"\nADVERSE REACTIONS:\n{adverse[0][:600]}")
        indications = label.get("indications_and_usage") or []
        if indications:
            out.append(f"\nINDICATIONS:\n{indications[0][:400]}")
        return "\n".join(out) if len(out) > 1 else f"No detailed info for '{drug_name}'."
    except Exception as e:
        return f"FDA lookup notice for '{drug_name}': {e}"


@lru_cache(maxsize=128)
def _check_drug_interaction_cached(drug1: str, drug2: str) -> str:
    d1 = drug1.strip().upper()
    d2 = drug2.strip().upper()
    if not d1 or not d2:
        return "Invalid drug pair specified."
    try:
        url = "https://api.fda.gov/drug/event.json"
        search = (
            f'patient.drug.medicinalproduct:"{d1}"'
            f'+AND+patient.drug.medicinalproduct:"{d2}"'
        )
        params = {"search": search, "limit": 1}
        r = requests.get(url, params=params, headers=HEADERS, timeout=DEFAULT_TIMEOUT)
        if r.status_code == 404:
            return (
                f"No reported adverse events for {drug1} + {drug2} in OpenFDA database. "
                f"Clinical judgment advised."
            )
        r.raise_for_status()
        data = r.json()
        total = data.get("meta", {}).get("results", {}).get("total", 0)
        reactions = []
        if data.get("results"):
            reactions = [
                rx.get("reactionmeddrapt", "")
                for rx in data["results"][0].get("patient", {}).get("reaction", [])
            ]
        msg = f"OpenFDA reports {total} adverse events for {drug1} + {drug2}."
        if reactions:
            msg += f"\nTop reactions: {', '.join(reactions[:5])}"
        if total > 100:
            msg += "\nHIGH interaction signal — review clinically."
        return msg
    except Exception as e:
        return f"Interaction check notice for {drug1} + {drug2}: {e}"


@tool
def search_icd10(condition: str) -> str:
    """Search ICD-10 code for a medical condition using NLM Clinical Tables API."""
    return _search_icd10_cached(condition)


@tool
def get_drug_info(drug_name: str) -> str:
    """Get FDA drug label info: warnings, side effects, indications."""
    return _get_drug_info_cached(drug_name)


@tool
def check_drug_interaction(drug1: str, drug2: str) -> str:
    """Check reported adverse events when two drugs are taken together."""
    return _check_drug_interaction_cached(drug1, drug2)

ALL_TOOLS = [search_icd10, get_drug_info, check_drug_interaction]