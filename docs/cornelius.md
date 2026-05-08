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

- `Auto fallback`
  - Tries Hugging Face first.
  - If Hugging Face returns an error, Cornelius pivots to local Ollama mode.

- `Hugging Face`
  - Uses the configured Hugging Face model and API token.
  - Best when a hosted model is available and API quota is healthy.

- `Local Ollama`
  - Uses a local Ollama model through `http://localhost:11434/api/chat`.
  - Useful when Hugging Face quota is exhausted or offline/local testing is
    preferred.

Local routing and template generation do not require either model backend.
Only open-ended model-backed answers need Hugging Face or Ollama.

The central `call_agent(...)` function defaults to `Auto fallback`. Future app
pages, such as design-of-experiment or analysis pages, can call
`call_agent(prompt)` directly and inherit Hugging Face-to-Ollama fallback
without duplicating the chat page's backend handling.

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

## Changing The Local Model

Preferred method: set `OLLAMA_MODEL_ID` in `.streamlit/secrets.toml`.

Example:

```toml
CORNELIUS_BACKEND = "auto"
OLLAMA_MODEL_ID = "qwen2.5-coder:7b"
OLLAMA_TIMEOUT_SECONDS = "240"
```

You can also set environment variables before starting Streamlit:

```bash
export CORNELIUS_BACKEND="auto"
export OLLAMA_MODEL_ID="qwen2.5-coder:7b"
export OLLAMA_TIMEOUT_SECONDS="300"
```

Then run the app:

```bash
streamlit run src/gage_rr_companion/Home.py
```

Available local models can be checked with:

```bash
ollama list
```

If you switch to a model that is not installed, pull it first:

```bash
ollama pull <model-name>
```

Examples:

```bash
ollama pull qwen2.5-coder:3b
ollama pull qwen2.5-coder:7b
ollama pull qwen:7b
```

## Changing The Hugging Face Model

Set `HF_MODEL_ID` in `.streamlit/secrets.toml`:

```toml
HUGGINGFACE_API_TOKEN = "your_huggingface_token_here"
HF_MODEL_ID = "google/gemma-2-9b-it"
```

You can also use environment variables:

```bash
export HUGGINGFACE_API_TOKEN="your_huggingface_token_here"
export HF_MODEL_ID="google/gemma-2-9b-it"
```

## App-Wide Backend Selection

Set `CORNELIUS_BACKEND` to control default behavior for any code path that
calls `call_agent(...)` without explicitly passing a backend.

Valid values:

```toml
CORNELIUS_BACKEND = "auto"   # default; try Hugging Face, then local Ollama on error
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

Future users should copy the example file:

```bash
cp .streamlit/secrets.example.toml .streamlit/secrets.toml
```

Then they should edit `.streamlit/secrets.toml` with their own API keys and
local model preferences.

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
  OLLAMA_MODEL_ID="qwen2.5-coder:3b" \
  ~/software-development/venv/bin/python \
  -c "from gage_rr_companion.cornelius import call_agent; print(call_agent('What is crossed Gage R&R? Answer in one sentence.', max_tokens=40, backend='local'))"
```

## Troubleshooting Local Mode

If local mode times out:

- confirm Ollama is running
- use `ollama list` to confirm the model is installed
- try a smaller model such as `qwen2.5-coder:3b`
- increase `OLLAMA_TIMEOUT_SECONDS`
- reduce other local workloads

If Hugging Face fails:

- check the API token
- check quota/credits
- switch the sidebar backend to `Local Ollama`
- use `Auto fallback` to let Cornelius pivot when the API call returns an error

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

- Local model quality and speed depend heavily on the user's machine and chosen
  model. The current default is `qwen2.5-coder:3b` because it is lighter, but it
  may be less capable than larger models.
  Future fix: document recommended model tiers, for example small/fast,
  balanced, and higher-quality options.

- Auto fallback only triggers after a Hugging Face call returns an error. It
  does not yet proactively detect exhausted quota before attempting the call.
  Future fix: add clearer UI handling for quota/auth errors and a one-click
  switch to local mode anywhere Cornelius is called.

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
