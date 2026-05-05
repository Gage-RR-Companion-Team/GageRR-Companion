import io
import os
from typing import Optional

import pandas as pd
from huggingface_hub import InferenceClient
from huggingface_hub.errors import HfHubHTTPError, InferenceTimeoutError

import streamlit as st
import requests

DEFAULT_MODEL_ID = "google/gemma-2-9b-it"
CORNELIUS_API_VERSION = "hf-chat-only-2026-04-30"


def get_model_id() -> str:
    return os.environ.get("HF_MODEL_ID", DEFAULT_MODEL_ID)


TEMPLATE_SPECS = {
    "type1": {
        "filename": "type1-template.xlsx",
        "headers": ["<Measurement Name>"],
    },
    "nested": {
        "filename": "nested-template.xlsx",
        "headers": ["Operator", "Part", "Trial", "Value"],
    },
    "crossed": {
        "filename": "crossed-template.xlsx",
        "headers": ["Operator", "Part", "Trial", "Value"],
    },
}


SYSTEM_PROMPT = """You are Cornelius, a focused Gage R&R assistant.

You help with:
- Gage study selection (Type 1, Nested, Crossed, and Expanded when appropriate)
- Excel template structure
- Measurement System Analysis (MSA)
- Interpreting results

Scope policy:
- Directly answer questions about Gage R&R, MSA, measurement systems, repeatability,
  reproducibility, bias, linearity, stability, NDC, ANOVA, variance components,
  study setup, templates, uploaded data, and result interpretation.
- Briefly answer adjacent quality or statistics questions only when they help the user
  understand a measurement study. Tie the answer back to the gage study.
- For unrelated requests, do not answer the unrelated task. Say you are focused on
  Gage R&R and measurement-system analysis, then offer a relevant way to help.
- If a request might be related but lacks context, ask one targeted clarifying question.
- Never say "SOW", "scope of work", or use bureaucratic refusal language.

Study selection guidance:
- Type 1: one operator or setup repeatedly measures one reference part.
- Crossed: non-destructive measurement where each operator can measure each part.
- Nested: destructive measurement, or parts cannot be shared across operators.
- Expanded: consider when the user suspects additional factors beyond operator and part,
  such as probes, fixtures, pump flow rates, methods, sites, shifts, or environmental
  conditions. Mention that expanded studies are generally not the first recommendation
  because they increase scope, data requirements, and analysis complexity. If Expanded
  seems relevant, recommend it as an escalation/next step, and offer a simpler nested or
  crossed starting point when appropriate.
- If the user asks "why nested over expanded" or compares study types, answer the
  comparison directly instead of repeating the original recommendation.
- Nested is better when the immediate design constraint is destructive testing and the
  main question is operator/part measurement variation.
- Expanded is better when the study goal is to quantify additional suspected sources of
  variation, such as probe-to-probe differences or pump-flow-rate effects.
- If both are true, say that Nested is the simpler starting design, while Expanded is the
  more complete design if the user can afford the added factors, runs, and analysis
  complexity.

Column guidance:
- In the app's standard templates, `Value` is the measured response/readout, not the
  experimental setting. For conductivity testing, `Value` should usually be the
  conductivity readout. Pump flow rate, probe ID, fixture, method, or site are study
  factors/settings. They belong in an expanded design or in controlled/held-constant
  study notes, not in the `Value` column.
- Standard app-compatible crossed and nested template headers must remain exactly:
  Operator, Part, Trial, Value. Do not rename `Part` to the measured item such as
  Membrane, Coupon, Sample, or Roll.

Use internal documentation when available.
Be concise and practical.
"""


# -----------------------------
# Scope Classification
# -----------------------------
DIRECT_SCOPE_KEYWORDS = [
    "msa", "measurement system", "gage", "gauge", "g r&r", "g r and r",
    "r&r", "repeatability", "reproducibility", "ndc", "bias", "linearity",
    "stability", "type 1", "type1", "crossed", "nested", "operator",
    "appraiser", "part", "trial", "variance component", "anova",
    "template", "xlsx", "excel", "csv", "upload", "destructive",
    "non-destructive", "calibration", "inspection", "measurement",
    "value", "readout", "conductivity", "probe", "pump", "flow rate",
    "membrane", "fixture", "method", "expanded",
    "why", "better",
]

ADJACENT_SCOPE_KEYWORDS = [
    "quality", "six sigma", "asq", "aiag", "iso", "astm", "control chart",
    "capability", "cpk", "cp", "tolerance", "process variation",
    "standard deviation", "variance", "mean", "statistics", "confidence",
]

UNRELATED_TASK_PATTERNS = [
    "recipe", "cook", "bake", "meal plan", "shopping list",
    "write a story", "poem", "lyrics", "joke", "riddle",
    "travel itinerary", "stock pick", "dating advice",
]

FOLLOWUP_PATTERNS = [
    "yes", "yeah", "yep", "sure", "ok", "okay", "make it", "do it",
    "continue", "that one", "the template", "make the template",
    "what value", "which value", "what do i use", "which do i use",
    "do i input", "should i input", "what column", "which column",
    "what goes", "where do i put",
]


def _contains_any(text: str, patterns: list[str]) -> bool:
    return any(pattern in text for pattern in patterns)


def _history_has_scope(history) -> bool:
    if not history:
        return False

    recent = " ".join(
        message.get("content", "")
        for message in history[-6:]
        if isinstance(message, dict)
    ).lower()
    return _contains_any(recent, DIRECT_SCOPE_KEYWORDS + ADJACENT_SCOPE_KEYWORDS)


def classify_prompt_scope(query: str, history=None) -> str:
    """Classify a user prompt as direct, adjacent, ambiguous, or out_of_scope."""
    text = query.lower().strip()

    if not text:
        return "ambiguous"

    if text in {"hi", "hello", "hey", "good morning", "good afternoon"}:
        return "direct"

    if _contains_any(text, UNRELATED_TASK_PATTERNS):
        return "out_of_scope"

    if _contains_any(text, DIRECT_SCOPE_KEYWORDS):
        return "direct"

    if _contains_any(text, ADJACENT_SCOPE_KEYWORDS):
        return "adjacent"

    if _history_has_scope(history) and (
        _contains_any(text, FOLLOWUP_PATTERNS)
        or "?" in text
        or len(text.split()) <= 12
    ):
        return "direct"

    if any(word in text for word in ["measure", "measuring", "data", "study", "test"]):
        return "ambiguous"

    return "out_of_scope"


def out_of_scope_response() -> str:
    return (
        "I’m focused on Gage R&R and measurement-system analysis, so I can’t help much "
        "with that topic. If you’re working on a measurement process, I can help choose "
        "a study type, build the upload template, or interpret your results."
    )


def ambiguous_scope_response() -> str:
    return (
        "Is this related to a measurement system or inspection process? If so, tell me "
        "what you’re measuring and how the data will be collected."
    )


# -----------------------------
# Load Internal Docs
# -----------------------------
def load_docs():
    docs = []

    paths = [
        "README.md",
        "docs/agent.md",
        "docs/Interpret.md",
    ]

    for path in paths:
        try:
            with open(path, "r", encoding="utf-8") as f:
                docs.append(f.read())
        except:
            continue

    return docs


DOCS = load_docs()


# -----------------------------
# Retrieve Relevant Docs
# -----------------------------
def retrieve_relevant_docs(query: str, k: int = 2) -> str:
    query = query.lower()

    scored = []
    for doc in DOCS:
        score = sum(word in doc.lower() for word in query.split())
        if score > 0:
            scored.append((score, doc))

    scored.sort(reverse=True, key=lambda x: x[0])
    return "\n\n---\n\n".join(doc for _, doc in scored[:k])


# -----------------------------
# Tavily Search
# -----------------------------
def tavily_search(query: str, max_results: int = 3) -> str:
    api_key = st.secrets.get("TAVILY_API_KEY")

    if not api_key:
        return ""

    try:
        response = requests.post(
            "https://api.tavily.com/search",
            json={
                "api_key": api_key,
                "query": query,
                "max_results": max_results,
            },
            timeout=10,
        )

        data = response.json()

        allowed_keywords = [
            "measurement", "gage", "msa",
            "repeatability", "reproducibility",
            "bias", "linearity", "stability",
            "quality", "six sigma",
            "asq", "aiag", "iso", "astm"
        ]

        filtered = []
        for r in data.get("results", []):
            text = (r.get("title", "") + " " + r.get("content", "")).lower()
            if any(k in text for k in allowed_keywords):
                filtered.append(f"- {r['title']}: {r['content']}")

        return "\n".join(filtered)

    except Exception:
        return ""


def should_search(query: str) -> bool:
    keywords = [
        "msa", "gage", "standard",
        "astm", "iso", "asq",
        "six sigma", "quality"
    ]
    return any(k in query.lower() for k in keywords)


# -----------------------------
# HF Client
# -----------------------------
def _get_hf_client() -> InferenceClient:
    token = os.environ.get("HUGGINGFACE_API_TOKEN") or os.environ.get("HF_TOKEN")
    if not token:
        raise RuntimeError("Missing Hugging Face token.")

    return InferenceClient(
        model=get_model_id(),
        token=token,
    )


# -----------------------------
# Core Agent Call
# -----------------------------
def call_agent_via_api(user_input: str, max_tokens: int = 300, history=None) -> str:
    scope = classify_prompt_scope(user_input, history)
    if scope == "out_of_scope":
        return out_of_scope_response()
    if scope == "ambiguous":
        return ambiguous_scope_response()

    client = _get_hf_client()

    try:
        messages = [{"role": "system", "content": SYSTEM_PROMPT}]

        if history:
            messages.extend(
                {
                    "role": message["role"],
                    "content": message["content"],
                }
                for message in history[-8:]
                if isinstance(message, dict)
                and message.get("role") in {"user", "assistant"}
                and message.get("content")
            )

        # ---- Internal Docs ----
        doc_context = retrieve_relevant_docs(user_input)
        if doc_context:
            user_input = f"""
Use internal documentation as primary source:

{doc_context}

Question:
{user_input}
"""

        # ---- Web fallback ----
        web_context = ""
        if should_search(user_input):
            web_context = tavily_search(user_input)

        if web_context:
            user_input = f"""
Use web results only if needed:

{web_context}

{user_input}
"""

        messages.append({"role": "user", "content": user_input})

        response = client.chat_completion(
            messages=messages,
            max_tokens=max_tokens,
            temperature=0.3,
        )

        return response.choices[0].message.content.strip()

    except Exception as e:
        return f"Error: {e}"


def call_agent(user_input: str, max_tokens: int = 300, history=None) -> str:
    return call_agent_via_api(user_input, max_tokens, history)


# -----------------------------
# Study Recommendation
# -----------------------------
def recommend_study_type(
    num_operators: int,
    num_parts: int,
    num_trials: int,
    measurement_type: str = "non-destructive",
) -> dict[str, str]:

    if num_operators == 1 and num_parts == 1:
        return {
            "recommended": "Type 1",
            "reason": "Single operator, single part.",
        }

    if measurement_type == "destructive":
        return {
            "recommended": "Nested",
            "reason": "Parts cannot be reused.",
        }

    return {
        "recommended": "Crossed",
        "reason": "All operators measure all parts.",
    }


# -----------------------------
# Template Generator
# -----------------------------
def generate_template(study_type: str, measurement_name: Optional[str] = None):

    key = study_type.lower()
    spec = TEMPLATE_SPECS[key]

    headers = spec["headers"]
    if key == "type1" and measurement_name:
        headers = [measurement_name]

    output = io.BytesIO()
    pd.DataFrame(columns=headers).to_excel(output, index=False)
    output.seek(0)

    return spec["filename"], output.getvalue()
