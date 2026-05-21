# Cornelius

Cornelius is the Gage R&R assistant used by the Streamlit app. It helps users
choose a study type, generate app-compatible Excel templates, answer MSA
questions, and interpret gage results.

## Architecture

Cornelius has three main layers:

- `src/gage_rr_companion/cornelius_router.py`
  - Local routing brain.
  - Does not call Streamlit, Hugging Face, Tavily, or Ollama.
  - Decides whether a chat turn should ask a follow-up, generate a template,
    redirect an unrelated prompt, or call a model.

- `src/gage_rr_companion/cornelius.py`
  - Model and tool layer.
  - Holds the Cornelius system prompt, internal-doc retrieval, web-search helper,
    Hugging Face call, local Ollama call, and template generation.

- `src/gage_rr_companion/pages/3_Chat_with_Cornelius.py`
  - Streamlit UI layer.
  - Renders chat, sidebar settings, template downloads, and model responses.

The router is intentionally testable locally. The app can check Cornelius's
routing behavior without running Streamlit or spending Hugging Face API credits.

## Model Backends

Cornelius supports three model backend modes in the Streamlit sidebar:

- `Hugging Face`
  - Uses the preset Hugging Face model and the user's API token.
  - Best when a hosted model is available and API quota is healthy.

- `OpenAI-compatible API`
  - Uses any provider that exposes `/v1/chat/completions`.
  - Works with OpenAI, OpenRouter, LiteLLM proxies, LM Studio, vLLM, and similar
    hosted or local gateways.
  - Best when users want to bring their own API key without changing
    application code.

- `Local Ollama`
  - Uses a local Ollama model through `http://localhost:11434/api/chat`.
  - Useful when Hugging Face quota is exhausted or offline/local testing is
    preferred.

Local routing and template generation do not require either model backend.
Only open-ended model-backed answers need a configured model backend.

The central `call_agent(...)` function defaults to `OpenAI-compatible API`. Future app
pages, such as design-of-experiment or analysis pages, can call
`call_agent(prompt)` directly and inherit the configured backend
without duplicating the chat page's backend handling.

## Bring Your Own API

The recommended generic hosted path is `OpenAI-compatible API`. Users only need
an API base URL and an API key. Cornelius uses preset models for each backend:

- OpenAI-compatible API: `gemma-4-31b`
- Hugging Face API: `google/gemma-2-9b-it`
- Local Ollama: `qwen2.5-coder:3b`

Example:

```toml
CORNELIUS_BACKEND = "openai_compatible"
OPENAI_COMPATIBLE_API_BASE = "https://your-provider.example/v1"
OPENAI_COMPATIBLE_API_KEY = "your_api_key_here"
```

Common examples:

```toml
# OpenAI
OPENAI_COMPATIBLE_API_BASE = "https://api.openai.com/v1"
```

```toml
# OpenRouter
OPENAI_COMPATIBLE_API_BASE = "https://openrouter.ai/api/v1"
```

```toml
# LiteLLM proxy
OPENAI_COMPATIBLE_API_BASE = "https://your-litellm-proxy.example/v1"
```

```toml
# LM Studio
OPENAI_COMPATIBLE_API_BASE = "http://localhost:1234/v1"
OPENAI_COMPATIBLE_API_KEY = "lm-studio"
```

For OpenAI-compatible providers, the app always calls:

```text
{OPENAI_COMPATIBLE_API_BASE}/chat/completions
```

So the base URL should usually end at `/v1`, not `/v1/chat/completions`.

## Local Mode Requirements

Important: `pip install -e .` installs the Python package dependencies for the
app, but it does not install external model services or local LLM weights.

This command installs Python libraries such as Streamlit, pandas, requests,
`huggingface_hub`, Altair, SciPy, and statsmodels:

```bash
pip install -e .
```

It does not install:

- Ollama
- local Ollama models
- Hugging Face API credentials
- Tavily API credentials

Those must be installed or configured separately.

Install and run Ollama, then pull a local model:

```bash
ollama pull qwen2.5-coder:3b
```

Start Ollama if it is not already running:

```bash
ollama serve
```

The current default local model is:

```text
qwen2.5-coder:3b
```

This default was chosen because it is lighter and responded more reliably in
local smoke testing than the larger 7B model.

Then run the app:

```bash
streamlit run src/gage_rr_companion/Home.py
```

Available local models can be checked with:

```bash
ollama list
```

## App-Wide Backend Selection

Set `CORNELIUS_BACKEND` to control default behavior for any code path that
calls `call_agent(...)` without explicitly passing a backend.

Valid values:

```toml
CORNELIUS_BACKEND = "openai_compatible"  # default; bring-your-own OpenAI-compatible API
CORNELIUS_BACKEND = "hf"     # Hugging Face only
CORNELIUS_BACKEND = "local"  # Ollama only
```

Future app pages should prefer:

```python
from gage_rr_companion.cornelius import call_agent

response = call_agent(prompt)
```

They should only pass `backend=...` when they need to override the app-wide
setting for that specific call.

## Internet Search

Cornelius can use Tavily as a web fallback for selected MSA, gage, quality, and
standards-related questions.

Set:

```toml
TAVILY_API_KEY = "your_tavily_key_here"
```

If no Tavily key is configured, Cornelius still works. It simply skips web
search and relies on internal docs plus the selected model backend.

## Secrets Files

Use this pattern:

```text
.streamlit/secrets.toml          # local private keys, ignored by Git
.streamlit/secrets.example.toml  # placeholders, committed to Git
```

Future users do not need to edit secrets files. They can choose a backend and
enter API details directly in the Streamlit sidebar. `.streamlit/secrets.toml`
is still supported for developers who want local defaults.

Do not put real API keys in `.streamlit/secrets.example.toml`.

## Local Testing

Run router tests:

```bash
cd ~/GageRR-Companion
env PYTHONPATH=~/GageRR-Companion/src \
  ~/software-development/venv/bin/python \
  -m pytest tests/test_cornelius_router.py -q
```

Run backend tests:

```bash
env PYTHONPATH=~/GageRR-Companion/src \
  ~/software-development/venv/bin/python \
  -m pytest tests/test_cornelius_backends.py -q
```

Run the full suite:

```bash
env PYTHONPATH=~/GageRR-Companion/src \
  ~/software-development/venv/bin/python \
  -m pytest -q
```

Run a local model smoke test:

```bash
env PYTHONPATH=~/GageRR-Companion/src \
  ~/software-development/venv/bin/python \
  -c "from gage_rr_companion.cornelius import call_agent; print(call_agent('What is crossed Gage R&R? Answer in one sentence.', max_tokens=40, backend='local'))"
```

## Troubleshooting Local Mode

If local mode times out:

- confirm Ollama is running
- use `ollama list` to confirm the model is installed
- reduce other local workloads

If Hugging Face fails:

- check the API token
- check quota/credits
- switch the sidebar backend to `Local Ollama`
- choose `Local Ollama` in the sidebar if hosted API access fails

## Known Limitations And Future Fixes

- `pip install -e .` does not install Ollama or local model weights.
  Future fix: add a setup script or README section that checks for Ollama,
  verifies the configured model exists, and prints the exact `ollama pull`
  command when it is missing.

- Local mode currently assumes Ollama is reachable at:

  ```text
  http://localhost:11434/api/chat
  ```

  Future fix: add `OLLAMA_HOST` or `OLLAMA_BASE_URL` configuration so users can
  point Cornelius at a different Ollama server.

- Local model quality and speed depend heavily on the user's machine. The
  current preset is `qwen2.5-coder:3b` because it is lighter and easier to run.

- The Streamlit chat page exposes backend selection, but future pages may need
  their own UI hints if they call Cornelius for analysis. The core `call_agent`
  fallback is centralized, but the user-facing controls are still page-specific.
  Future fix: create a shared Cornelius settings component for all pages.

- Expanded Gage R&R remains a guided conversation rather than a full uploader
  and analysis workflow.
  Future fix: add a dedicated expanded-study design and analysis path once the
  expected file format and statistical model are finalized.

- Router tests cover deterministic decision behavior, not full free-form LLM
  answer quality.
  Future fix: add answer-quality evals or human-reviewed golden examples for
  model-backed responses.
