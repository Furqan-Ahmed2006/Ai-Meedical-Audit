import os
import json
import re
from dotenv import load_dotenv
from langchain_groq import ChatGroq
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.output_parsers import StrOutputParser
from prompts import EXTRACTION_SYSTEM_PROMPT, EXTRACTION_USER_PROMPT
from models import ExtractedNote
load_dotenv()

def get_groq_api_key(custom_key: str = None) -> str:
    """Resolve Groq API key from custom input, env vars, or Streamlit secrets."""
    if custom_key and custom_key.strip():
        return custom_key.strip()
    
    key = os.getenv("GROQ_API_KEY")
    if key and key.strip():
        return key.strip()

    try:
        import streamlit as st
        if hasattr(st, "secrets") and "GROQ_API_KEY" in st.secrets:
            return st.secrets["GROQ_API_KEY"].strip()
    except Exception:
        pass

    return ""


def _get_llm(api_key: str = None):
    key = get_groq_api_key(api_key)
    if not key:
        raise ValueError("GROQ_API_KEY is missing. Please set GROQ_API_KEY in environment or sidebar.")
    return ChatGroq(
        model="openai/gpt-oss-120b",
        api_key=key,
        temperature=0,
        max_tokens=2000,
    )


def _clean_json(raw: str) -> str:
    raw = raw.strip()
    raw = re.sub(r"^```(?:json)?\s*", "", raw)
    raw = re.sub(r"\s*```$", "", raw)
    start = raw.find("{")
    end = raw.rfind("}")
    if start != -1 and end != -1:
        return raw[start:end + 1]
    return raw.strip()


def extract_note(note: str, api_key: str = None) -> dict:
    """Run LLM to extract structured data from a doctor's note with safe fallbacks."""
    if not note or not note.strip():
        return ExtractedNote().model_dump()

    try:
        prompt = ChatPromptTemplate.from_messages([
            ("system", EXTRACTION_SYSTEM_PROMPT),
            ("human", EXTRACTION_USER_PROMPT),
        ])
        chain = prompt | _get_llm(api_key) | StrOutputParser()
        raw_output = chain.invoke({"note": note})
        cleaned = _clean_json(raw_output)

        try:
            parsed = json.loads(cleaned)
        except json.JSONDecodeError:
            cleaned_fix = re.sub(r",\s*([\]}])", r"\1", cleaned)
            parsed = json.loads(cleaned_fix)

        return ExtractedNote(**parsed).model_dump()

    except Exception as e:
        return ExtractedNote(
            chief_complaint=f"Extraction completed with notice: {e}",
            symptoms=[s.strip() for s in note.split("\n") if s.strip()][:5],
        ).model_dump()