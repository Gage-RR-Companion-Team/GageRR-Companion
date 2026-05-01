import io
import os
from typing import Optional

import pandas as pd
from huggingface_hub import InferenceClient
from huggingface_hub.errors import HfHubHTTPError, InferenceTimeoutError

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

SYSTEM_PROMPT = """You are Cornelius, a helpful Gage R&R assistant. You help with:
- Recommending gage study types: Type 1, Nested, Crossed
- Explaining when each study type is appropriate
- Helping users understand Excel template structures
- Interpreting measurement system analysis results
- Answering practical gage testing questions

If a user asks for an Excel/template/download file, do not invent a Markdown spreadsheet.
Ask for the study type and measurement being recorded if either is missing.
Tell them the app will generate the downloadable .xlsx file. Approved headers:
- Type 1: one column named after the measurement.
- Crossed: Operator, Part, Trial, Value.
- Nested: Operator, Part, Trial, Value.

Be concise, practical, and focused on measurement-system-analysis guidance.
"""


def _get_hf_client() -> InferenceClient:
    """
    Creates a Hugging Face inference client.

    Preferred:
      HF_ENDPOINT_URL = your dedicated Inference Endpoint URL

    Fallback:
      Uses MODEL_ID directly, if Hugging Face serverless/provider inference supports it.
    """
    token = os.environ.get("HUGGINGFACE_API_TOKEN") or os.environ.get("HF_TOKEN")
    if not token:
        raise RuntimeError(
            "Missing Hugging Face token. Set HUGGINGFACE_API_TOKEN or HF_TOKEN."
        )

    endpoint_url = os.environ.get("HF_ENDPOINT_URL")

    if endpoint_url:
        return InferenceClient(
            base_url=endpoint_url,
            token=token,
        )

    return InferenceClient(
        model=get_model_id(),
        provider=os.environ.get("HF_PROVIDER", "auto"),
        token=token,
    )


def call_agent_via_api(
    user_input: str,
    max_tokens: int = 300,
    history: list[dict[str, str]] | None = None,
) -> str:
    """
    Calls the configured Gemma model through Hugging Face instead of running locally.
    """
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
                if message.get("role") in {"user", "assistant"} and message.get("content")
            )
        messages.append({"role": "user", "content": user_input})

        response = client.chat_completion(
            messages=messages,
            max_tokens=max_tokens,
            temperature=0.3,
            top_p=0.9,
        )
        return response.choices[0].message.content.strip()

    except HfHubHTTPError as e:
        return _format_hf_http_error(e)

    except ValueError as e:
        return f"Hugging Face API value error: {e}"

    except InferenceTimeoutError:
        return "Hugging Face inference timed out. The model may be cold-starting or the endpoint may be too small."

    except StopIteration:
        return (
            "Hugging Face could not find a hosted provider for "
            f"`{get_model_id()}`. Try a compatible `HF_PROVIDER`, or create a dedicated "
            "Hugging Face Inference Endpoint and add its URL to "
            "`.streamlit/secrets.toml` as `HF_ENDPOINT_URL`."
        )

    except Exception as e:
        return f"Error calling Hugging Face API: {type(e).__name__}: {repr(e)}"


def _format_hf_http_error(error: HfHubHTTPError) -> str:
    status = getattr(error.response, "status_code", None)
    body = ""
    if getattr(error, "response", None) is not None:
        try:
            body = error.response.text
        except Exception:
            body = ""

    if status == 401:
        return "Hugging Face authentication failed. Check your token."
    if status == 403:
        return "Access denied. Make sure you accepted the Gemma model terms on Hugging Face and your token has access."
    if status == 400 and "Model not supported by provider" in body:
        return (
            f"`{get_model_id()}` is not supported by the selected Hugging Face provider. "
            "Remove `HF_PROVIDER` from your secrets to use automatic routing, set it "
            "to a compatible provider, or use a dedicated `HF_ENDPOINT_URL`."
        )
    if status == 404:
        return (
            f"Model or endpoint not found. Check HF_MODEL_ID={get_model_id()} "
            "or set HF_ENDPOINT_URL to your deployed Inference Endpoint."
        )
    if status == 503:
        return "The Hugging Face model/endpoint is loading or unavailable. Try again shortly."

    detail = body or repr(error)
    return f"Hugging Face API error ({status or 'unknown status'}): {detail}"


def call_agent(
    user_input: str,
    max_tokens: int = 300,
    history: list[dict[str, str]] | None = None,
) -> str:
    """Public app entry point for Cornelius chat."""
    return call_agent_via_api(user_input, max_tokens=max_tokens, history=history)


def recommend_study_type(
    num_operators: int,
    num_parts: int,
    num_trials: int,
    measurement_type: str = "non-destructive",
) -> dict[str, str]:
    """Recommend a practical gage study design from a few setup choices."""
    measurement_type = measurement_type.lower()

    if num_operators == 1 and num_parts == 1:
        return {
            "recommended": "Type 1",
            "reason": "Use a Type 1 study when one operator repeatedly measures one reference part.",
            "setup": f"{num_trials} repeated measurements of the same part",
        }

    if measurement_type == "destructive":
        return {
            "recommended": "Nested",
            "reason": "Use a nested study when parts cannot be remeasured by every operator.",
            "setup": f"{num_operators} operators x {num_parts} parts x {num_trials} trials",
        }

    if num_operators >= 2 and num_parts >= 5:
        return {
            "recommended": "Crossed",
            "reason": "Use a crossed study when every operator can measure every part multiple times.",
            "setup": f"{num_operators} operators x {num_parts} parts x {num_trials} trials each",
        }

    return {
        "recommended": "Crossed or Nested",
        "reason": "A crossed study is preferred if every operator can measure every part; otherwise use nested.",
        "setup": f"{num_operators} operators x {num_parts} parts x {num_trials} trials",
    }


def generate_template(study_type: str, measurement_name: Optional[str] = None) -> tuple[str, bytes]:
    """Generate a blank Excel template for a supported gage study type."""
    key = study_type.lower()
    if key not in TEMPLATE_SPECS:
        raise ValueError(f"Unknown study type: {study_type}")

    spec = TEMPLATE_SPECS[key]
    headers = spec["headers"]
    if key == "type1" and measurement_name:
        headers = [measurement_name]

    output = io.BytesIO()
    pd.DataFrame(columns=headers).to_excel(output, index=False, sheet_name="Data")
    output.seek(0)
    return spec["filename"], output.getvalue()


if __name__ == "__main__":
    question = (
        "I have 3 operators measuring 10 parts, each part measured 3 times. "
        "What gage study type should I use?"
    )

    print(call_agent_via_api(question))
