import os
from pathlib import Path
import re
from urllib.parse import urlparse

import streamlit as st

from gage_rr_companion.cornelius import (
    call_agent,
    generate_template,
    get_agent_backend,
    load_ai_secrets,
    get_openai_compatible_api_key,
    get_llama_cpp_filename,
    get_llama_cpp_repo_id,
    get_model_id,
    get_openai_compatible_api_base,
    get_openai_compatible_model_id,
)
from gage_rr_companion.cornelius_router import route_chat_turn
from gage_rr_companion.ui.sidebar import render_sidebar


st.set_page_config(
    page_title="Chat with Cornelius",
    page_icon="C",
    layout="wide",
    initial_sidebar_state="expanded",
)

LOCAL_SECRETS_PATH = Path(".streamlit") / "secrets.toml"
AI_SETTING_WIDGET_KEYS = {
    "openai_compatible_api_base": "cornelius_saved_openai_compatible_api_base",
    "openai_compatible_api_key": "cornelius_saved_openai_compatible_api_key",
    "openai_compatible_model_id": "cornelius_saved_openai_compatible_model_id",
    "hf_api_token": "cornelius_saved_hf_api_token",
    "hf_endpoint_url": "cornelius_saved_hf_endpoint_url",
    "hf_provider": "cornelius_saved_hf_provider",
}


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


def normalize_backend(backend: str | None) -> str:
    backend = (backend or "llama_cpp").strip().lower()
    if backend in {"local", "ollama"}:
        return "llama_cpp"
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
    if backend in {"hf", "huggingface", "hugging_face"}:
        return "hf"
    if backend in {"llama_cpp", "llamacpp", "embedded", "local_embedded"}:
        return "llama_cpp"
    if backend == "auto":
        return "openai_compatible"
    return "llama_cpp"


def initialize_sidebar_ai_settings() -> None:
    """Seed widget state once, then let it persist until the Streamlit session ends."""
    if "cornelius_backend" not in st.session_state:
        st.session_state.cornelius_backend = normalize_backend(get_agent_backend())

    defaults = {
        "openai_compatible_api_base": get_openai_compatible_api_base(),
        "openai_compatible_api_key": get_openai_compatible_api_key(),
        "openai_compatible_model_id": get_openai_compatible_model_id(),
        "hf_api_token": os.environ.get("HUGGINGFACE_API_TOKEN")
        or os.environ.get("HF_TOKEN")
        or "",
        "hf_endpoint_url": os.environ.get("HF_ENDPOINT_URL", ""),
        "hf_provider": os.environ.get("HF_PROVIDER", ""),
    }
    for widget_key, value in defaults.items():
        saved_key = AI_SETTING_WIDGET_KEYS[widget_key]
        if saved_key not in st.session_state:
            st.session_state[saved_key] = value
        if widget_key not in st.session_state:
            st.session_state[widget_key] = st.session_state[saved_key]


def selected_backend() -> str:
    return normalize_backend(st.session_state.get("cornelius_backend", get_agent_backend()))


def saved_ai_setting(widget_key: str) -> str:
    saved_key = AI_SETTING_WIDGET_KEYS[widget_key]
    if widget_key in st.session_state:
        st.session_state[saved_key] = str(st.session_state.get(widget_key, "")).strip()
    return str(st.session_state.get(saved_key, "")).strip()


def toml_string(value: str) -> str:
    escaped = value.replace("\\", "\\\\").replace('"', '\\"').replace("\n", "\\n")
    return f'"{escaped}"'


def save_ai_settings_to_local_secrets(values: dict[str, str]) -> None:
    LOCAL_SECRETS_PATH.parent.mkdir(parents=True, exist_ok=True)
    lines = (
        LOCAL_SECRETS_PATH.read_text(encoding="utf-8").splitlines()
        if LOCAL_SECRETS_PATH.exists()
        else []
    )

    updated_lines = []
    saved_keys = set()
    key_pattern = re.compile(r"^(\s*)([A-Z0-9_]+)(\s*=\s*)(.*)$")
    for line in lines:
        match = key_pattern.match(line)
        key = match.group(2) if match else None
        if key in values:
            updated_lines.append(f"{key} = {toml_string(values[key])}")
            saved_keys.add(key)
        else:
            updated_lines.append(line)

    if updated_lines and any(key not in saved_keys for key in values):
        updated_lines.append("")
    for key, value in values.items():
        if key not in saved_keys:
            updated_lines.append(f"{key} = {toml_string(value)}")

    LOCAL_SECRETS_PATH.write_text("\n".join(updated_lines).rstrip() + "\n", encoding="utf-8")


def call_cornelius(prompt: str, history=None) -> str:
    os.environ["CORNELIUS_BACKEND"] = selected_backend()
    return call_agent(
        prompt,
        history=history,
        backend=selected_backend(),
        include_context=False,
    )


def test_backend_connection() -> str:
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
    backend = selected_backend()
    os.environ["CORNELIUS_BACKEND"] = backend

    openai_base = saved_ai_setting("openai_compatible_api_base")
    openai_key = saved_ai_setting("openai_compatible_api_key")
    openai_model = saved_ai_setting("openai_compatible_model_id")
    os.environ["OPENAI_COMPATIBLE_API_BASE"] = openai_base
    os.environ["OPENAI_COMPATIBLE_API_KEY"] = openai_key
    os.environ["OPENAI_COMPATIBLE_MODEL_ID"] = openai_model

    hf_token = saved_ai_setting("hf_api_token")
    hf_endpoint = saved_ai_setting("hf_endpoint_url")
    hf_provider = saved_ai_setting("hf_provider")
    os.environ["HUGGINGFACE_API_TOKEN"] = hf_token
    os.environ["HF_ENDPOINT_URL"] = hf_endpoint
    os.environ["HF_PROVIDER"] = hf_provider
    settings = {
        "CORNELIUS_BACKEND": backend,
        "OPENAI_COMPATIBLE_API_BASE": openai_base,
        "OPENAI_COMPATIBLE_API_KEY": openai_key,
        "OPENAI_COMPATIBLE_MODEL_ID": openai_model,
        "HUGGINGFACE_API_TOKEN": hf_token,
        "HF_ENDPOINT_URL": hf_endpoint,
        "HF_PROVIDER": hf_provider,
    }
    try:
        save_ai_settings_to_local_secrets(settings)
    except OSError as exc:
        st.warning(f"Could not save Cornelius settings to local secrets: {exc}")


def template_kwargs_from_context(template_context: dict | None) -> dict:
    template_context = template_context or {}
    return {
        "num_operators": template_context.get("operators"),
        "num_parts": template_context.get("parts"),
        "num_trials": template_context.get("trials"),
    }


def expanded_parameter_names(prefix: str = "template") -> list[str]:
    count = int(st.session_state.get(f"{prefix}_expanded_parameter_count", 1))
    names = []
    for index in range(1, count + 1):
        default_name = f"Parameter {index}"
        names.append(st.session_state.get(f"{prefix}_expanded_parameter_{index}", default_name))
    return names


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
        parameter_names=expanded_parameter_names() if study_type == "expanded" else None,
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
    st.markdown(content)


load_ai_secrets()
initialize_sidebar_ai_settings()
render_sidebar("chat")

st.title("Chat with Cornelius")
st.caption("Gage R&R study design, templates, and practical MSA interpretation.")

with st.sidebar:
    st.subheader("Cornelius")
    backend_options = ["llama_cpp", "openai_compatible", "hf"]
    st.selectbox(
        "Model backend",
        options=backend_options,
        format_func={
            "openai_compatible": "OpenAI-compatible API",
            "llama_cpp": "Local llama.cpp",
            "hf": "Hugging Face API",
        }.get,
        key="cornelius_backend",
        help="Use embedded local llama.cpp by default, or connect through an OpenAI-compatible or Hugging Face API.",
    )

    if selected_backend() == "openai_compatible":
        with st.expander("OpenAI-compatible API details", expanded=False):
            st.text_input(
                "API base URL",
                placeholder="https://api.openai.com/v1",
                key="openai_compatible_api_base",
            )
            st.text_input(
                "API key",
                type="password",
                key="openai_compatible_api_key",
            )
            st.text_input(
                "Model",
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
    elif selected_backend() == "llama_cpp":
        with st.expander("Local llama.cpp details", expanded=False):
            st.caption(f"Model repo: `{get_llama_cpp_repo_id()}`")
            st.caption(f"Model file: `{get_llama_cpp_filename()}`")
            st.caption('Requires `pip install -e ".[local]" --extra-index-url https://abetlen.github.io/llama-cpp-python/whl/cpu`. The GGUF model downloads and caches on first use.')
            if st.button("Test connection", key="test-llama-cpp"):
                apply_sidebar_ai_settings()
                with st.spinner("Testing local llama.cpp model..."):
                    result = test_backend_connection()
                if result.startswith("Error:"):
                    st.error(result)
                else:
                    st.success(result)
    elif selected_backend() == "hf":
        with st.expander("Hugging Face API details", expanded=False):
            st.text_input(
                "Hugging Face token",
                type="password",
                key="hf_api_token",
            )
            st.text_input(
                "Endpoint URL",
                placeholder="Optional dedicated inference endpoint",
                key="hf_endpoint_url",
            )
            st.text_input(
                "Provider",
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
    apply_sidebar_ai_settings()
    if selected_backend() == "openai_compatible":
        config_error = validate_openai_compatible_config()
        if config_error:
            st.warning("Invalid API configuration")
            st.caption(config_error)
        else:
            st.success("Using OpenAI-compatible API")
            st.caption(f"API base: `{get_openai_compatible_api_base()}`")
    elif selected_backend() == "llama_cpp":
        st.success("Using local llama.cpp mode")
        st.caption("No model server or API key required after the GGUF model is cached.")
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

    chat_history = st.container(height=620, border=True)

    def render_chat_history() -> None:
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
                        st.session_state.cornelius_backend = "llama_cpp"
                        st.rerun()

    with chat_history:
        render_chat_history()

    prompt = st.chat_input("Ask about Gage R&R, study setup, or MSA results")
    if prompt:
        st.session_state.cornelius_messages.append({"role": "user", "content": prompt})
        with chat_history:
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
                "The Hugging Face call failed. You can retry this turn using the "
                "embedded local model."
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
            ["type1", "crossed", "nested", "expanded"],
            format_func={
                "type1": "Type 1",
                "crossed": "Crossed",
                "nested": "Nested",
                "expanded": "Expanded",
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
        elif study_type == "expanded":
            st.caption(
                "Expanded templates include Part, Operator, Trial, Value, and editable parameter columns "
                "for extra factors such as station, fixture, probe, method, site, or batch."
            )
            st.number_input("Operators/appraisers", min_value=1, value=3, key="template_expanded_num_operators")
            st.number_input("Parts", min_value=1, value=10, key="template_expanded_num_parts")
            st.number_input("Replicates/trials per part", min_value=1, value=3, key="template_expanded_num_trials")
            st.number_input(
                "Number of parameters",
                min_value=1,
                max_value=8,
                value=1,
                step=1,
                key="template_expanded_parameter_count",
            )
            parameter_count = int(st.session_state.get("template_expanded_parameter_count", 1))
            for index in range(1, parameter_count + 1):
                st.text_input(
                    f"Parameter {index} header",
                    value=st.session_state.get(f"template_expanded_parameter_{index}", f"Parameter {index}"),
                    key=f"template_expanded_parameter_{index}",
                )
            parameter_count = int(st.session_state.get("template_expanded_parameter_count", 1))
            estimated_rows = (
                int(st.session_state.get("template_expanded_num_operators", 3))
                * int(st.session_state.get("template_expanded_num_parts", 10))
                * int(st.session_state.get("template_expanded_num_trials", 3))
                * parameter_count
            )
            st.caption(f"Template will generate {estimated_rows:,} data rows plus the example row.")
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
            elif study_type == "expanded":
                template_kwargs["parameter_names"] = expanded_parameter_names()
                template_kwargs["num_operators"] = st.session_state.get("template_expanded_num_operators")
                template_kwargs["num_parts"] = st.session_state.get("template_expanded_num_parts")
                template_kwargs["num_trials"] = st.session_state.get("template_expanded_num_trials")
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
