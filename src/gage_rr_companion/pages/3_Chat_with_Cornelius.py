import os
from urllib.parse import urlparse

import requests
import streamlit as st

from gage_rr_companion.cornelius import (
    call_agent,
    generate_template,
    get_agent_backend,
    load_ai_secrets,
    get_openai_compatible_api_key,
    get_local_model_id,
    get_model_id,
    get_openai_compatible_api_base,
    get_openai_compatible_model_id,
)
from gage_rr_companion.cornelius_router import route_chat_turn


st.set_page_config(page_title="Chat with Cornelius", page_icon="C", layout="wide")


def has_hugging_face_token() -> bool:
    return bool(os.environ.get("HUGGINGFACE_API_TOKEN") or os.environ.get("HF_TOKEN"))


def validate_openai_compatible_config() -> str | None:
    api_base = get_openai_compatible_api_base()
    api_key = os.environ.get("OPENAI_COMPATIBLE_API_KEY") or os.environ.get("CORNELIUS_API_KEY")
    model_id = get_openai_compatible_model_id()

    if not api_base:
        return "API base URL is required."
    parsed = urlparse(api_base)
    if parsed.scheme not in {"http", "https"} or not parsed.netloc:
        return "API base URL must be a full http(s) URL, such as https://api.example.com/v1."
    if api_base.endswith("/chat/completions"):
        return "API base URL should end at /v1. The app adds /chat/completions automatically."
    if not api_key:
        return "API key is required."
    if not model_id:
        return "Model is required."
    return None


def has_openai_compatible_config() -> bool:
    return validate_openai_compatible_config() is None


def selected_backend() -> str:
    backend = st.session_state.get("cornelius_backend", get_agent_backend())
    return "openai_compatible" if backend == "auto" else backend


def call_cornelius(prompt: str, history=None) -> str:
    os.environ["CORNELIUS_BACKEND"] = selected_backend()
    return call_agent(
        prompt,
        history=history,
        backend=selected_backend(),
        include_context=False,
    )


def test_backend_connection() -> str:
    if selected_backend() == "local":
        try:
            response = requests.get("http://localhost:11434/api/tags", timeout=5)
            response.raise_for_status()
            models = {
                model.get("name")
                for model in response.json().get("models", [])
                if isinstance(model, dict)
            }
            if get_local_model_id() not in models:
                return f"Error: Ollama is running, but `{get_local_model_id()}` is not installed."
            return "Successful"
        except Exception as exc:
            return f"Error: local Ollama unavailable: {exc}"

    if selected_backend() == "openai_compatible":
        config_error = validate_openai_compatible_config()
        if config_error:
            return f"Error: {config_error}"

    previous_timeout = os.environ.get("OPENAI_COMPATIBLE_TIMEOUT_SECONDS")
    os.environ["OPENAI_COMPATIBLE_TIMEOUT_SECONDS"] = "20"
    try:
        result = call_agent(
            "Say OK.",
            max_tokens=20,
            history=[],
            backend=selected_backend(),
            include_context=False,
        )
    finally:
        if previous_timeout is None:
            os.environ.pop("OPENAI_COMPATIBLE_TIMEOUT_SECONDS", None)
        else:
            os.environ["OPENAI_COMPATIBLE_TIMEOUT_SECONDS"] = previous_timeout
    return result if result.startswith("Error:") else "Successful"


def apply_sidebar_ai_settings() -> None:
    os.environ["CORNELIUS_BACKEND"] = selected_backend()

    openai_base = st.session_state.get("openai_compatible_api_base", "").strip()
    openai_key = st.session_state.get("openai_compatible_api_key", "").strip()
    openai_model = st.session_state.get("openai_compatible_model_id", "").strip()
    os.environ["OPENAI_COMPATIBLE_API_BASE"] = openai_base
    os.environ["OPENAI_COMPATIBLE_API_KEY"] = openai_key
    os.environ["OPENAI_COMPATIBLE_MODEL_ID"] = openai_model

    hf_token = st.session_state.get("hf_api_token", "").strip()
    hf_endpoint = st.session_state.get("hf_endpoint_url", "").strip()
    hf_provider = st.session_state.get("hf_provider", "").strip()
    os.environ["HUGGINGFACE_API_TOKEN"] = hf_token
    os.environ["HF_ENDPOINT_URL"] = hf_endpoint
    os.environ["HF_PROVIDER"] = hf_provider


def template_kwargs_from_context(template_context: dict | None) -> dict:
    template_context = template_context or {}
    return {
        "num_operators": template_context.get("operators"),
        "num_parts": template_context.get("parts"),
        "num_trials": template_context.get("trials"),
    }


def render_template_download(
    study_type: str,
    key: str,
    measurement_context: str | None = None,
    template_context: dict | None = None,
) -> None:
    measurement_name = measurement_context if study_type == "type1" else None
    filename, excel_bytes = generate_template(
        study_type,
        measurement_name,
        **template_kwargs_from_context(template_context),
    )
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


load_ai_secrets()

st.title("Chat with Cornelius")
st.caption("Gage R&R study design, templates, and practical MSA interpretation.")

with st.sidebar:
    st.subheader("Cornelius")
    configured_backend = selected_backend()
    backend_options = ["openai_compatible", "hf", "local"]
    backend_index = (
        backend_options.index(configured_backend)
        if configured_backend in backend_options
        else 0
    )
    st.selectbox(
        "Model backend",
        options=backend_options,
        index=backend_index,
        format_func={
            "openai_compatible": "OpenAI-compatible API (recommended)",
            "hf": "Hugging Face API",
            "local": "Local Ollama",
        }.get,
        key="cornelius_backend",
        help="Use OpenAI, OpenRouter, LiteLLM, LM Studio, vLLM, Hugging Face, or local Ollama.",
    )

    if selected_backend() == "openai_compatible":
        with st.expander("OpenAI-compatible API details", expanded=False):
            st.text_input(
                "API base URL",
                value=get_openai_compatible_api_base(),
                placeholder="https://api.openai.com/v1",
                key="openai_compatible_api_base",
            )
            st.text_input(
                "API key",
                value=get_openai_compatible_api_key(),
                type="password",
                key="openai_compatible_api_key",
            )
            st.text_input(
                "Model",
                value=get_openai_compatible_model_id(),
                key="openai_compatible_model_id",
                help="Use a smaller or provider-native model here if responses are timing out.",
            )
            if st.button("Test connection", key="test-openai-compatible"):
                apply_sidebar_ai_settings()
                with st.spinner("Testing API connection..."):
                    result = test_backend_connection()
                if result.startswith("Error:"):
                    st.error(result)
                else:
                    st.success(result)
    elif selected_backend() == "hf":
        with st.expander("Hugging Face API details", expanded=False):
            st.text_input(
                "Hugging Face token",
                value=os.environ.get("HUGGINGFACE_API_TOKEN") or os.environ.get("HF_TOKEN") or "",
                type="password",
                key="hf_api_token",
            )
            st.text_input(
                "Endpoint URL",
                value=os.environ.get("HF_ENDPOINT_URL", ""),
                placeholder="Optional dedicated inference endpoint",
                key="hf_endpoint_url",
            )
            st.text_input(
                "Provider",
                value=os.environ.get("HF_PROVIDER", ""),
                placeholder="Optional provider route",
                key="hf_provider",
            )
            st.caption(f"Preset model: `{get_model_id()}`")
            if st.button("Test connection", key="test-hf"):
                apply_sidebar_ai_settings()
                with st.spinner("Testing Hugging Face connection..."):
                    result = test_backend_connection()
                if result.startswith("Error:"):
                    st.error(result)
                else:
                    st.success(result)
    else:
        with st.expander("Local Ollama details", expanded=False):
            st.caption(f"Preset model: `{get_local_model_id()}`")
            if st.button("Test connection", key="test-local"):
                apply_sidebar_ai_settings()
                with st.spinner("Testing local Ollama connection..."):
                    result = test_backend_connection()
                if result.startswith("Error:"):
                    st.error(result)
                else:
                    st.success(result)

    apply_sidebar_ai_settings()
    if selected_backend() == "openai_compatible":
        config_error = validate_openai_compatible_config()
        if config_error:
            st.warning("Invalid API configuration")
            st.caption(config_error)
        else:
            st.success("Using OpenAI-compatible API")
            st.caption(f"API base: `{get_openai_compatible_api_base()}`")
    elif selected_backend() == "local":
        st.success("Using local Ollama mode")
        st.caption("Make sure Ollama is running before asking model-backed questions.")
    else:
        if os.environ.get("HF_ENDPOINT_URL"):
            st.success("Using Hugging Face endpoint")
        elif has_hugging_face_token():
            st.success("Using Hugging Face API")
            st.write(f"Provider: `{os.environ.get('HF_PROVIDER', 'auto')}`")
        else:
            st.warning("Missing Hugging Face token")
            st.caption("Enter a Hugging Face token above or choose a different backend.")

    if st.button("Clear chat"):
        st.session_state.cornelius_messages = []
        st.rerun()


tab_chat, tab_template = st.tabs(["Chat", "Template Generator"])


with tab_chat:
    st.subheader("Ask Cornelius")

    if selected_backend() == "hf" and not has_hugging_face_token():
        st.error(
            "Hugging Face token not found. Enter a token in the sidebar or switch backends."
        )
    elif selected_backend() == "openai_compatible" and not has_openai_compatible_config():
        st.error(f"OpenAI-compatible API is not configured correctly. {validate_openai_compatible_config()}")

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
                    template_context=message.get("template_context"),
                )
            if message.get("retry_user_prompt"):
                if st.button("Retry this turn in local mode", key=f"retry-local-{index}"):
                    with st.spinner("Cornelius is retrying locally..."):
                        local_response = call_agent(
                            message["retry_user_prompt"],
                            history=message.get("retry_history"),
                            backend="local",
                            include_context=False,
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
                    template_context=result.updated_state,
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
            assistant_message["template_context"] = result.updated_state
        st.session_state.cornelius_messages.append(assistant_message)


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
            st.number_input(
                "Template rows",
                min_value=25,
                value=50,
                step=1,
                key="template_type1_rows",
            )
        else:
            st.number_input("Operators/appraisers", min_value=1, value=3, key="template_num_operators")
            st.number_input(
                "Parts per operator" if study_type == "nested" else "Parts",
                min_value=1,
                value=10,
                key="template_num_parts",
            )
            st.number_input("Trials per part", min_value=1, value=3, key="template_num_trials")

    if st.button("Generate template", type="primary"):
        try:
            template_kwargs = {}
            if study_type == "type1":
                template_kwargs["row_count"] = st.session_state.get("template_type1_rows", 50)
            else:
                template_kwargs["num_operators"] = st.session_state.get("template_num_operators")
                template_kwargs["num_parts"] = st.session_state.get("template_num_parts")
                template_kwargs["num_trials"] = st.session_state.get("template_num_trials")
            filename, excel_bytes = generate_template(
                study_type,
                measurement_name,
                **template_kwargs,
            )
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
