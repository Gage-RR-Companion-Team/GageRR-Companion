import os

import streamlit as st

from gage_rr_companion.cornelius import (
    CORNELIUS_API_VERSION,
    call_agent,
    generate_template,
    get_local_model_id,
    get_model_id,
    recommend_study_type,
)
from gage_rr_companion.cornelius_router import route_chat_turn


st.set_page_config(page_title="Chat with Cornelius", page_icon="C", layout="wide")


def load_hugging_face_secrets() -> None:
    """Copy Streamlit secrets into environment variables used by cornelius.py."""
    try:
        token = st.secrets.get("HUGGINGFACE_API_TOKEN") or st.secrets.get("HF_TOKEN")
        endpoint_url = st.secrets.get("HF_ENDPOINT_URL")
        provider = st.secrets.get("HF_PROVIDER")
        model_id = st.secrets.get("HF_MODEL_ID")
        local_model_id = st.secrets.get("OLLAMA_MODEL_ID")
        local_timeout = st.secrets.get("OLLAMA_TIMEOUT_SECONDS")
        backend = st.secrets.get("CORNELIUS_BACKEND")
    except Exception:
        token = None
        endpoint_url = None
        provider = None
        model_id = None
        local_model_id = None
        local_timeout = None
        backend = None

    if token:
        os.environ["HUGGINGFACE_API_TOKEN"] = token
    if endpoint_url:
        os.environ["HF_ENDPOINT_URL"] = endpoint_url
    if provider:
        os.environ["HF_PROVIDER"] = provider
    if model_id:
        os.environ["HF_MODEL_ID"] = model_id
    if local_model_id:
        os.environ["OLLAMA_MODEL_ID"] = local_model_id
    if local_timeout:
        os.environ["OLLAMA_TIMEOUT_SECONDS"] = str(local_timeout)
    if backend:
        os.environ["CORNELIUS_BACKEND"] = backend


def has_hugging_face_token() -> bool:
    return bool(os.environ.get("HUGGINGFACE_API_TOKEN") or os.environ.get("HF_TOKEN"))


def selected_backend() -> str:
    return st.session_state.get("cornelius_backend", "auto")


def call_cornelius(prompt: str, history=None) -> str:
    os.environ["CORNELIUS_BACKEND"] = selected_backend()
    return call_agent(prompt, history=history, backend=selected_backend())


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
    st.radio(
        "Model backend",
        options=["auto", "hf", "local"],
        format_func={
            "auto": "Auto fallback",
            "hf": "Hugging Face",
            "local": "Local Ollama",
        }.get,
        key="cornelius_backend",
        help="Auto tries Hugging Face first, then pivots to local Ollama if the API call fails.",
    )
    st.write(f"HF model: `{get_model_id()}`")
    st.write(f"Local model: `{get_local_model_id()}`")
    st.caption(f"Agent API: `{CORNELIUS_API_VERSION}`")
    if selected_backend() == "local":
        st.success("Using local Ollama mode")
        st.caption("Make sure Ollama is running before asking model-backed questions.")
    else:
        if os.environ.get("HF_ENDPOINT_URL"):
            st.success("Using Hugging Face endpoint")
        elif has_hugging_face_token():
            st.warning("No endpoint URL configured")
            st.write(f"Provider: `{os.environ.get('HF_PROVIDER', 'auto')}`")
            st.caption("If provider routing fails, use a dedicated HF Inference Endpoint.")
        else:
            st.warning("Missing Hugging Face token")
            st.caption("Use Local Ollama mode or add HUGGINGFACE_API_TOKEN to .streamlit/secrets.toml.")

    if st.button("Clear chat"):
        st.session_state.cornelius_messages = []
        st.rerun()


tab_chat, tab_recommend, tab_template, tab_interpret = st.tabs(
    ["Chat", "Study Recommender", "Template Generator", "Result Interpreter"]
)


with tab_chat:
    st.subheader("Ask Cornelius")

    if selected_backend() == "hf" and not has_hugging_face_token():
        st.error(
            "Hugging Face token not found. Add HUGGINGFACE_API_TOKEN to "
            ".streamlit/secrets.toml, then restart Streamlit, or switch to Local Ollama mode."
        )
    elif selected_backend() == "auto" and not has_hugging_face_token():
        st.info("No Hugging Face token found. Auto fallback will use local Ollama for model-backed questions.")

    if "cornelius_messages" not in st.session_state:
        st.session_state.cornelius_messages = [
            {
                "role": "assistant",
                "content": "Hi, I am Cornelius. Tell me your operators, parts, trials, and whether the measurement is destructive.",
            }
        ]
    if "cornelius_router_state" not in st.session_state:
        st.session_state.cornelius_router_state = {}

    for index, message in enumerate(st.session_state.cornelius_messages):
        with st.chat_message(message["role"]):
            render_chat_content(message["role"], message["content"])
            if message.get("template_type"):
                render_template_download(
                    message["template_type"],
                    key=f"download-{message['template_type']}-{id(message)}",
                    measurement_context=message.get("measurement_context"),
                )
            if message.get("retry_user_prompt"):
                if st.button("Retry this turn in local mode", key=f"retry-local-{index}"):
                    with st.spinner("Cornelius is retrying locally..."):
                        local_response = call_agent(
                            message["retry_user_prompt"],
                            history=message.get("retry_history"),
                            backend="local",
                        )
                    st.session_state.cornelius_messages[index] = {
                        "role": "assistant",
                        "content": local_response,
                    }
                    st.session_state.cornelius_backend = "local"
                    st.rerun()

    prompt = st.chat_input("Ask about Gage R&R, study setup, or MSA results")
    if prompt:
        st.session_state.cornelius_messages.append({"role": "user", "content": prompt})
        with st.chat_message("user"):
            st.markdown(prompt)

        with st.chat_message("assistant"):
            router_state = dict(st.session_state.cornelius_router_state)
            router_state["messages"] = st.session_state.cornelius_messages
            result = route_chat_turn(prompt, router_state)
            st.session_state.cornelius_router_state = result.updated_state

            if result.action == "generate_template":
                response = result.message
                render_chat_content("assistant", response)
                render_template_download(
                    result.template_type,
                    key=f"download-{result.template_type}-{len(st.session_state.cornelius_messages)}",
                    measurement_context=result.measurement_context,
                )
            elif result.action in {"ask_followup", "redirect"}:
                response = result.message
                render_chat_content("assistant", response)
            else:
                with st.spinner("Cornelius is thinking..."):
                    response = call_cornelius(
                        prompt,
                        history=st.session_state.cornelius_messages,
                    )
                render_chat_content("assistant", response)

        assistant_message = {"role": "assistant", "content": response}
        if (
            selected_backend() == "hf"
            and response.startswith("Error:")
        ):
            assistant_message["content"] = (
                f"{response}\n\n"
                "The Hugging Face call failed. You can retry this turn in local mode "
                "if Ollama is running."
            )
            assistant_message["retry_user_prompt"] = prompt
            assistant_message["retry_history"] = st.session_state.cornelius_messages
        if result.action == "generate_template":
            assistant_message["template_type"] = result.template_type
            assistant_message["measurement_context"] = result.measurement_context
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
                response = call_cornelius(prompt)
                if selected_backend() == "hf" and response.startswith("Error:"):
                    st.error(response)
                    if st.button("Switch to local mode and retry interpretation"):
                        st.session_state.cornelius_backend = "local"
                        with st.spinner("Cornelius is reviewing locally..."):
                            st.markdown(call_agent(prompt, backend="local"))
                else:
                    st.markdown(response)
