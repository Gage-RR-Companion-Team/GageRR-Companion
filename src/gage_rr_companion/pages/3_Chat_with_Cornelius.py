import os
import re

import streamlit as st

from gage_rr_companion.cornelius import (
    CORNELIUS_API_VERSION,
    call_agent,
    generate_template,
    get_model_id,
    recommend_study_type,
)


st.set_page_config(page_title="Chat with Cornelius", page_icon="C", layout="wide")


def load_hugging_face_secrets() -> None:
    """Copy Streamlit secrets into environment variables used by cornelius.py."""
    try:
        token = st.secrets.get("HUGGINGFACE_API_TOKEN") or st.secrets.get("HF_TOKEN")
        endpoint_url = st.secrets.get("HF_ENDPOINT_URL")
        provider = st.secrets.get("HF_PROVIDER")
        model_id = st.secrets.get("HF_MODEL_ID")
    except Exception:
        token = None
        endpoint_url = None
        provider = None
        model_id = None

    if token:
        os.environ["HUGGINGFACE_API_TOKEN"] = token
    if endpoint_url:
        os.environ["HF_ENDPOINT_URL"] = endpoint_url
    if provider:
        os.environ["HF_PROVIDER"] = provider
    if model_id:
        os.environ["HF_MODEL_ID"] = model_id


def has_hugging_face_token() -> bool:
    return bool(os.environ.get("HUGGINGFACE_API_TOKEN") or os.environ.get("HF_TOKEN"))


def detect_template_request(prompt: str) -> str | None:
    """Return the requested template type when the chat should create a file."""
    text = prompt.lower()
    wants_file = any(
        word in text
        for word in ["template", "excel", "spreadsheet", "xlsx", "download", "file"]
    )
    if not wants_file:
        return None

    study_type = detect_study_type(prompt)
    if study_type:
        return study_type
    return "known"


def detect_study_type(prompt: str) -> str | None:
    text = prompt.lower()
    if re.search(r"\btype\s*1\b|\btype1\b", text):
        return "type1"
    if "nested" in text:
        return "nested"
    if "crossed" in text or "cross" in text:
        return "crossed"
    return None


def detect_measurement_context(prompt: str) -> str | None:
    """Pull a short measurement description from simple user phrasing."""
    text = prompt.strip()
    patterns = [
        r"(?:measuring|measure|measurement(?:\s+is|\s+of)?|for)\s+([A-Za-z][A-Za-z0-9 /_-]{1,40})",
        r"(?:called|named)\s+([A-Za-z][A-Za-z0-9 /_-]{1,40})",
    ]
    for pattern in patterns:
        match = re.search(pattern, text, flags=re.IGNORECASE)
        if match:
            value = re.split(r"[.?!,;]", match.group(1).strip())[0].strip()
            if value.lower() not in {"crossed", "nested", "type", "template", "excel"}:
                return value
    return None


def template_followup_question(study_type: str | None) -> str:
    if study_type is None or study_type == "known":
        return (
            "I can make that, but I need two details first: which study type "
            "should the template use: Type 1, Crossed, or Nested? Also, what "
            "measurement are you recording, such as length, diameter, or torque?"
        )

    return (
        "I can make that template. Before I export it, what measurement are you "
        "recording, such as length, diameter, torque, or conductivity?"
    )


def template_chat_response(study_type: str, measurement_context: str | None = None) -> str:
    labels = {
        "type1": "Type 1",
        "nested": "Nested",
        "crossed": "Crossed",
    }
    headers = {
        "type1": "<Measurement Name>",
        "nested": "Operator, Part, Trial, Value",
        "crossed": "Operator, Part, Trial, Value",
    }
    notes = {
        "type1": "Use one row per repeated measurement of the same reference part.",
        "nested": "Use one row per measurement; parts are nested within operator.",
        "crossed": "Use one row per measurement; every operator measures every part for each trial.",
    }
    measurement_note = (
        f"Measurement recorded: {measurement_context}.\n\n"
        if measurement_context
        else ""
    )
    return (
        f"I created the {labels[study_type]} Excel template for you.\n\n"
        f"{measurement_note}"
        f"Headers: `{headers[study_type]}`\n\n"
        f"{notes[study_type]} The template is long format, so it does not use "
        "`Measurement 1`, `Measurement 2`, or other wide-format trial columns."
    )


def render_template_download(
    study_type: str, key: str, measurement_context: str | None = None
) -> None:
    measurement_name = measurement_context if study_type == "type1" else None
    filename, excel_bytes = generate_template(study_type, measurement_name)
    st.download_button(
        "Download Excel template",
        data=excel_bytes,
        file_name=filename,
        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        key=key,
    )


def render_chat_content(role: str, content: str) -> None:
    if role == "assistant":
        with st.container(height=360, border=False):
            st.markdown(content)
    else:
        st.markdown(content)


load_hugging_face_secrets()

st.title("Chat with Cornelius")
st.caption("Gage R&R study design, templates, and practical MSA interpretation.")

with st.sidebar:
    st.subheader("Cornelius")
    st.write(f"Model: `{get_model_id()}`")
    st.caption(f"Agent API: `{CORNELIUS_API_VERSION}`")
    if os.environ.get("HF_ENDPOINT_URL"):
        st.success("Using Hugging Face endpoint")
    elif has_hugging_face_token():
        st.warning("No endpoint URL configured")
        st.write(f"Provider: `{os.environ.get('HF_PROVIDER', 'auto')}`")
        st.caption("If provider routing fails, use a dedicated HF Inference Endpoint.")
    else:
        st.warning("Missing Hugging Face token")
        st.caption("Add HUGGINGFACE_API_TOKEN to .streamlit/secrets.toml.")

    if st.button("Clear chat"):
        st.session_state.cornelius_messages = []
        st.rerun()


tab_chat, tab_recommend, tab_template, tab_interpret = st.tabs(
    ["Chat", "Study Recommender", "Template Generator", "Result Interpreter"]
)


with tab_chat:
    st.subheader("Ask Cornelius")

    if not has_hugging_face_token():
        st.error(
            "Hugging Face token not found. Add HUGGINGFACE_API_TOKEN to "
            ".streamlit/secrets.toml, then restart Streamlit."
        )

    if "cornelius_messages" not in st.session_state:
        st.session_state.cornelius_messages = [
            {
                "role": "assistant",
                "content": "Hi, I am Cornelius. Tell me your operators, parts, trials, and whether the measurement is destructive.",
            }
        ]
    if "pending_template_request" not in st.session_state:
        st.session_state.pending_template_request = None
    if "selected_study_type" not in st.session_state:
        st.session_state.selected_study_type = None
    if "measurement_context" not in st.session_state:
        st.session_state.measurement_context = None

    for message in st.session_state.cornelius_messages:
        with st.chat_message(message["role"]):
            render_chat_content(message["role"], message["content"])
            if message.get("template_type"):
                render_template_download(
                    message["template_type"],
                    key=f"download-{message['template_type']}-{id(message)}",
                    measurement_context=message.get("measurement_context"),
                )

    prompt = st.chat_input("Ask about Gage R&R, study setup, or MSA results")
    if prompt:
        st.session_state.cornelius_messages.append({"role": "user", "content": prompt})
        with st.chat_message("user"):
            st.markdown(prompt)

        with st.chat_message("assistant"):
            pending_template = st.session_state.pending_template_request
            template_type = detect_template_request(prompt)
            detected_study_type = detect_study_type(prompt)
            measurement_context = detect_measurement_context(prompt)

            if detected_study_type:
                st.session_state.selected_study_type = detected_study_type
            if measurement_context:
                st.session_state.measurement_context = measurement_context

            if template_type == "known":
                template_type = st.session_state.selected_study_type

            if pending_template:
                template_type = template_type or pending_template.get("study_type")
                measurement_context = (
                    measurement_context or pending_template.get("measurement_context")
                )
                if not measurement_context and len(prompt.strip()) <= 40:
                    measurement_context = prompt.strip()
            else:
                measurement_context = (
                    measurement_context or st.session_state.measurement_context
                )

            if template_type == "known":
                response = template_followup_question(None)
                render_chat_content("assistant", response)
            elif template_type and not measurement_context:
                st.session_state.pending_template_request = {
                    "study_type": template_type,
                    "measurement_context": None,
                }
                response = template_followup_question(template_type)
                render_chat_content("assistant", response)
            elif pending_template and measurement_context:
                response = template_chat_response(template_type, measurement_context)
                render_chat_content("assistant", response)
                render_template_download(
                    template_type,
                    key=f"download-{template_type}-{len(st.session_state.cornelius_messages)}",
                    measurement_context=measurement_context,
                )
                st.session_state.pending_template_request = None
            elif template_type:
                response = template_chat_response(template_type, measurement_context)
                render_chat_content("assistant", response)
                render_template_download(
                    template_type,
                    key=f"download-{template_type}-{len(st.session_state.cornelius_messages)}",
                    measurement_context=measurement_context,
                )
            else:
                with st.spinner("Cornelius is thinking..."):
                    response = call_agent(
                        prompt,
                        history=st.session_state.cornelius_messages,
                    )
                render_chat_content("assistant", response)

        assistant_message = {"role": "assistant", "content": response}
        if template_type and measurement_context:
            assistant_message["template_type"] = template_type
            assistant_message["measurement_context"] = measurement_context
        st.session_state.cornelius_messages.append(assistant_message)


with tab_recommend:
    st.subheader("Choose a Study Type")

    col_left, col_right = st.columns(2)
    with col_left:
        num_operators = st.number_input("Operators/appraisers", min_value=1, value=3)
        num_parts = st.number_input("Parts/samples", min_value=1, value=10)
    with col_right:
        num_trials = st.number_input("Trials per part", min_value=1, value=3)
        measurement_type = st.selectbox(
            "Measurement type",
            ["non-destructive", "destructive"],
            help="Destructive measurements cannot reuse the same physical part.",
        )

    if st.button("Get recommendation", type="primary"):
        recommendation = recommend_study_type(
            num_operators=num_operators,
            num_parts=num_parts,
            num_trials=num_trials,
            measurement_type=measurement_type,
        )
        st.success(f"Recommended: {recommendation['recommended']}")
        st.write(recommendation["reason"])
        st.caption(recommendation["setup"])


with tab_template:
    st.subheader("Generate an Excel Template")

    col_left, col_right = st.columns(2)
    with col_left:
        study_type = st.selectbox(
            "Study type",
            ["type1", "crossed", "nested"],
            format_func={
                "type1": "Type 1",
                "crossed": "Crossed",
                "nested": "Nested",
            }.get,
        )

    measurement_name = None
    with col_right:
        if study_type == "type1":
            measurement_name = st.text_input(
                "Measurement name",
                placeholder="Length, diameter, torque...",
            )

    if st.button("Generate template", type="primary"):
        try:
            filename, excel_bytes = generate_template(study_type, measurement_name)
        except Exception as exc:
            st.error(f"Could not generate template: {exc}")
        else:
            st.success(f"Generated {filename}")
            st.download_button(
                "Download template",
                data=excel_bytes,
                file_name=filename,
                mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            )


with tab_interpret:
    st.subheader("Interpret Results")

    results_input = st.text_area(
        "Paste computed results",
        height=170,
        placeholder='Example:\n{"ndc": 8, "repeatability": 0.15, "reproducibility": 0.08}',
    )

    if st.button("Interpret results", type="primary"):
        if not results_input.strip():
            st.warning("Paste results first.")
        else:
            prompt = (
                "Interpret these Gage R&R / MSA results. Explain whether the "
                "measurement system is acceptable and what the user should check next:\n\n"
                f"{results_input}"
            )
            with st.spinner("Cornelius is reviewing the results..."):
                st.markdown(call_agent(prompt))
