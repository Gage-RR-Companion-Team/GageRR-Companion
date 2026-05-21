import io
import os
from typing import Optional

import pandas as pd
from huggingface_hub import InferenceClient
from huggingface_hub.errors import HfHubHTTPError, InferenceTimeoutError

import streamlit as st
import requests

DEFAULT_MODEL_ID = "google/gemma-2-9b-it"
DEFAULT_LOCAL_MODEL_ID = "qwen2.5-coder:3b"
DEFAULT_OPENAI_COMPATIBLE_MODEL_ID = "gemma-4-31b"
DEFAULT_OPENAI_COMPATIBLE_TIMEOUT_SECONDS = 180
DEFAULT_LOCAL_TIMEOUT_SECONDS = 600
CORNELIUS_API_VERSION = "multi-backend-chat-2026-05-20"


def get_model_id() -> str:
    return DEFAULT_MODEL_ID


def get_local_model_id() -> str:
    return DEFAULT_LOCAL_MODEL_ID


def get_openai_compatible_api_base() -> str:
    return (
        os.environ.get("OPENAI_COMPATIBLE_API_BASE")
        or os.environ.get("CORNELIUS_API_BASE")
        or ""
    ).strip().rstrip("/")


def get_openai_compatible_api_key() -> str:
    return (
        os.environ.get("OPENAI_COMPATIBLE_API_KEY")
        or os.environ.get("CORNELIUS_API_KEY")
        or ""
    ).strip()


def get_openai_compatible_model_id() -> str:
    return (
        os.environ.get("OPENAI_COMPATIBLE_MODEL_ID")
        or os.environ.get("CORNELIUS_MODEL_ID")
        or DEFAULT_OPENAI_COMPATIBLE_MODEL_ID
    ).strip()


def get_openai_compatible_timeout_seconds() -> float:
    raw_timeout = (
        os.environ.get("OPENAI_COMPATIBLE_TIMEOUT_SECONDS")
        or os.environ.get("CORNELIUS_TIMEOUT_SECONDS")
    )
    if raw_timeout:
        try:
            timeout = float(raw_timeout)
        except ValueError:
            return DEFAULT_OPENAI_COMPATIBLE_TIMEOUT_SECONDS
        if timeout > 0:
            return timeout
    return DEFAULT_OPENAI_COMPATIBLE_TIMEOUT_SECONDS


def load_ai_secrets() -> None:
    """Copy supported Streamlit secrets into environment variables."""
    try:
        values = {
            "HUGGINGFACE_API_TOKEN": st.secrets.get("HUGGINGFACE_API_TOKEN")
            or st.secrets.get("HF_TOKEN"),
            "HF_ENDPOINT_URL": st.secrets.get("HF_ENDPOINT_URL"),
            "HF_PROVIDER": st.secrets.get("HF_PROVIDER"),
            "CORNELIUS_BACKEND": st.secrets.get("CORNELIUS_BACKEND"),
            "OPENAI_COMPATIBLE_API_BASE": st.secrets.get("OPENAI_COMPATIBLE_API_BASE")
            or st.secrets.get("CORNELIUS_API_BASE"),
            "OPENAI_COMPATIBLE_API_KEY": st.secrets.get("OPENAI_COMPATIBLE_API_KEY")
            or st.secrets.get("CORNELIUS_API_KEY"),
            "OPENAI_COMPATIBLE_MODEL_ID": st.secrets.get("OPENAI_COMPATIBLE_MODEL_ID")
            or st.secrets.get("CORNELIUS_MODEL_ID"),
        }
    except Exception:
        values = {}

    for key, value in values.items():
        if value:
            os.environ[key] = str(value)


def get_agent_backend() -> str:
    backend = os.environ.get("CORNELIUS_BACKEND", "openai_compatible").strip().lower()
    if backend in {"hf", "huggingface", "hugging_face"}:
        return "hf"
    if backend in {"local", "ollama"}:
        return "local"
    if backend in {
        "api",
        "remote",
        "openai",
        "openai_compatible",
        "custom_api",
        "cornelius",
        "cornelius_api",
    }:
        return "openai_compatible"
    if backend == "auto":
        return "auto"
    return "openai_compatible"


TEMPLATE_SPECS = {
    "type1": {
        "filename": "type1-template.xlsx",
        "headers": ["Test #", "<Measurement Name>"],
        "default_rows": 50,
    },
    "nested": {
        "filename": "nested-template.xlsx",
        "headers": ["Test #", "Operator", "Part", "Trial", "Value"],
        "default_rows": 50,
    },
    "crossed": {
        "filename": "crossed-template.xlsx",
        "headers": ["Test #", "Operator", "Part", "Trial", "Value"],
        "default_rows": 50,
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
- Standard app-compatible crossed and nested template headers are:
  Test #, Operator, Part, Trial, Value. `Test #` is pre-populated and ignored by
  the compute functions. Do not rename `Part` to the measured item such as
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


def _build_agent_messages(
    user_input: str,
    history=None,
    doc_k: int = 2,
    max_doc_chars: int | None = None,
    include_context: bool = True,
) -> list[dict[str, str]]:
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

    if include_context:
        # ---- Internal Docs ----
        doc_context = retrieve_relevant_docs(user_input, k=doc_k)
        if doc_context and max_doc_chars:
            doc_context = doc_context[:max_doc_chars]
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
    return messages


# -----------------------------
# Core Agent Calls
# -----------------------------
def call_agent_via_api(user_input: str, max_tokens: int | None = 300, history=None, include_context: bool = True) -> str:
    scope = classify_prompt_scope(user_input, history)
    if scope == "out_of_scope":
        return out_of_scope_response()
    if scope == "ambiguous":
        return ambiguous_scope_response()

    client = _get_hf_client()

    try:
        request_kwargs = {
            "messages": _build_agent_messages(
                user_input,
                history,
                include_context=include_context,
            ),
            "temperature": 0.3,
        }
        if max_tokens is not None:
            request_kwargs["max_tokens"] = max_tokens
        response = client.chat_completion(**request_kwargs)

        return response.choices[0].message.content.strip()

    except Exception as e:
        return f"Error: {e}"


def call_agent_local(user_input: str, max_tokens: int | None = 300, history=None, include_context: bool = True) -> str:
    scope = classify_prompt_scope(user_input, history)
    if scope == "out_of_scope":
        return out_of_scope_response()
    if scope == "ambiguous":
        return ambiguous_scope_response()

    try:
        request_json = {
            "model": get_local_model_id(),
            "messages": _build_agent_messages(
                user_input,
                history,
                doc_k=1,
                max_doc_chars=5000,
                include_context=include_context,
            ),
            "stream": False,
            "options": {
                "temperature": 0.3,
            },
        }
        if max_tokens is not None:
            request_json["options"]["num_predict"] = max_tokens
        response = requests.post(
            "http://localhost:11434/api/chat",
            json=request_json,
            timeout=DEFAULT_LOCAL_TIMEOUT_SECONDS,
        )
        response.raise_for_status()
        data = response.json()
        return data.get("message", {}).get("content", "").strip()
    except Exception as e:
        return f"Error: local model unavailable: {e}"


def call_agent_openai_compatible(
    user_input: str,
    max_tokens: int | None = 300,
    history=None,
    include_context: bool = True,
) -> str:
    scope = classify_prompt_scope(user_input, history)
    if scope == "out_of_scope":
        return out_of_scope_response()
    if scope == "ambiguous":
        return ambiguous_scope_response()

    api_base = get_openai_compatible_api_base()
    api_key = get_openai_compatible_api_key()
    if not api_base:
        return "Error: OPENAI_COMPATIBLE_API_BASE is not configured."
    if not api_key:
        return "Error: OPENAI_COMPATIBLE_API_KEY is not configured."

    try:
        url = f"{api_base}/chat/completions"
        request_json = {
            "model": get_openai_compatible_model_id(),
            "messages": _build_agent_messages(
                user_input,
                history,
                doc_k=1,
                max_doc_chars=5000,
                include_context=include_context,
            ),
            "temperature": 0.3,
        }
        if max_tokens is not None:
            request_json["max_tokens"] = max_tokens
        response = requests.post(
            url,
            headers={
                "Authorization": f"Bearer {api_key}",
                "Content-Type": "application/json",
            },
            json=request_json,
            timeout=get_openai_compatible_timeout_seconds(),
        )
        response.raise_for_status()
        data = response.json()
        return data["choices"][0]["message"]["content"].strip()
    except requests.HTTPError as e:
        status = e.response.status_code if e.response is not None else "unknown"
        body = ""
        if e.response is not None:
            body = e.response.text[:500]
        return (
            "Error: OpenAI-compatible API unavailable: "
            f"HTTP {status} for {url} using model `{get_openai_compatible_model_id()}`. "
            f"Response: {body}"
        )
    except Exception as e:
        return f"Error: OpenAI-compatible API unavailable: {e}"


def call_agent_cornelius_api(user_input: str, max_tokens: int | None = 300, history=None, include_context: bool = True) -> str:
    if include_context:
        return call_agent_openai_compatible(user_input, max_tokens, history)
    return call_agent_openai_compatible(
        user_input,
        max_tokens,
        history,
        include_context=False,
    )


def call_agent(
    user_input: str,
    max_tokens: int | None = 300,
    history=None,
    backend: str | None = None,
    include_context: bool = True,
) -> str:
    backend = backend or get_agent_backend()

    if backend == "local":
        if include_context:
            return call_agent_local(user_input, max_tokens, history)
        return call_agent_local(user_input, max_tokens, history, include_context=False)
    if backend == "openai_compatible":
        if include_context:
            return call_agent_openai_compatible(user_input, max_tokens, history)
        return call_agent_openai_compatible(
            user_input,
            max_tokens,
            history,
            include_context=False,
        )

    if include_context:
        response = call_agent_via_api(user_input, max_tokens, history)
    else:
        response = call_agent_via_api(
            user_input,
            max_tokens,
            history,
            include_context=False,
        )
    if backend == "auto" and response.startswith("Error:"):
        if include_context:
            local_response = call_agent_local(user_input, max_tokens, history)
        else:
            local_response = call_agent_local(
                user_input,
                max_tokens,
                history,
                include_context=False,
            )
        if not local_response.startswith("Error:"):
            return (
                "No huggingface API key detected, running in local mode. Response times may be slower.\n\n"
                f"{local_response}"
            )
    return response


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
def _positive_int(value) -> int | None:
    if value in {None, ""}:
        return None
    try:
        number = int(value)
    except (TypeError, ValueError):
        return None
    return number if number > 0 else None


def template_row_count(
    study_type: str,
    *,
    num_operators: int | None = None,
    num_parts: int | None = None,
    num_trials: int | None = None,
    row_count: int | None = None,
) -> int:
    key = study_type.lower()
    explicit_rows = _positive_int(row_count)
    if explicit_rows:
        return explicit_rows

    operators = _positive_int(num_operators)
    parts = _positive_int(num_parts)
    trials = _positive_int(num_trials)
    if key in {"crossed", "nested"} and operators and parts and trials:
        return operators * parts * trials

    return TEMPLATE_SPECS[key]["default_rows"]


def _template_rows(key: str, row_count: int):
    if key == "type1":
        rows = [["example:", 10]]
        rows.extend([[index, None] for index in range(1, row_count + 1)])
        return rows

    rows = [["example:", "Operator A", "Part 1", 1, 10]]
    rows.extend([[index, None, None, None, None] for index in range(1, row_count + 1)])
    return rows


def generate_template(
    study_type: str,
    measurement_name: Optional[str] = None,
    *,
    num_operators: int | None = None,
    num_parts: int | None = None,
    num_trials: int | None = None,
    row_count: int | None = None,
):

    key = study_type.lower()
    spec = TEMPLATE_SPECS[key]

    headers = list(spec["headers"])
    if key == "type1" and measurement_name:
        headers = ["Test #", measurement_name]

    output_rows = template_row_count(
        key,
        num_operators=num_operators,
        num_parts=num_parts,
        num_trials=num_trials,
        row_count=row_count,
    )

    output = io.BytesIO()
    pd.DataFrame(_template_rows(key, output_rows), columns=headers).to_excel(
        output,
        index=False,
    )
    output.seek(0)

    return spec["filename"], output.getvalue()
