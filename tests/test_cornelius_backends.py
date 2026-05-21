from gage_rr_companion import cornelius


def test_call_agent_uses_local_backend(monkeypatch):
    calls = []

    def fake_local(user_input, max_tokens=300, history=None):
        calls.append((user_input, max_tokens, history))
        return "local answer"

    monkeypatch.setattr(cornelius, "call_agent_local", fake_local)

    response = cornelius.call_agent("why is ndc low?", backend="local")

    assert response == "local answer"
    assert calls[0][0] == "why is ndc low?"


def test_call_agent_uses_openai_compatible_backend(monkeypatch):
    calls = []

    def fake_openai_compatible(user_input, max_tokens=300, history=None):
        calls.append((user_input, max_tokens, history))
        return "remote answer"

    monkeypatch.setattr(cornelius, "call_agent_openai_compatible", fake_openai_compatible)

    response = cornelius.call_agent("why is ndc low?", backend="openai_compatible")

    assert response == "remote answer"
    assert calls[0][0] == "why is ndc low?"


def test_configured_openai_compatible_aliases(monkeypatch):
    monkeypatch.setenv("CORNELIUS_BACKEND", "api")

    assert cornelius.get_agent_backend() == "openai_compatible"


def test_hf_and_local_model_presets_ignore_environment_overrides(monkeypatch):
    monkeypatch.setenv("HF_MODEL_ID", "qwen/qwen3")
    monkeypatch.setenv("OLLAMA_MODEL_ID", "llama3.1")

    assert cornelius.get_model_id() == "google/gemma-2-9b-it"
    assert cornelius.get_local_model_id() == "qwen2.5-coder:3b"


def test_openai_compatible_model_can_be_configured(monkeypatch):
    monkeypatch.setenv("OPENAI_COMPATIBLE_MODEL_ID", "gpt-4o-mini")

    assert cornelius.get_openai_compatible_model_id() == "gpt-4o-mini"


def test_openai_compatible_timeout_can_be_configured(monkeypatch):
    monkeypatch.setenv("OPENAI_COMPATIBLE_TIMEOUT_SECONDS", "20")

    assert cornelius.get_openai_compatible_timeout_seconds() == 20


def test_openai_compatible_timeout_ignores_invalid_override(monkeypatch):
    monkeypatch.setenv("OPENAI_COMPATIBLE_TIMEOUT_SECONDS", "not-a-number")

    assert cornelius.get_openai_compatible_timeout_seconds() == cornelius.DEFAULT_OPENAI_COMPATIBLE_TIMEOUT_SECONDS


def test_local_timeout_preset_allows_slow_local_model():
    assert cornelius.DEFAULT_LOCAL_TIMEOUT_SECONDS == 600


def test_openai_compatible_backend_posts_to_chat_completions(monkeypatch):
    posted = {}

    class FakeResponse:
        def raise_for_status(self):
            return None

        def json(self):
            return {
                "choices": [
                    {
                        "message": {
                            "content": "remote answer",
                        },
                    }
                ]
            }

    def fake_post(url, headers=None, json=None, timeout=None):
        posted["url"] = url
        posted["headers"] = headers
        posted["json"] = json
        posted["timeout"] = timeout
        return FakeResponse()

    monkeypatch.setenv("OPENAI_COMPATIBLE_API_BASE", "https://example.test/v1/")
    monkeypatch.setenv("OPENAI_COMPATIBLE_API_KEY", "secret-token")
    monkeypatch.setattr(cornelius.requests, "post", fake_post)

    response = cornelius.call_agent_openai_compatible("why is ndc low?")

    assert response == "remote answer"
    assert posted["url"] == "https://example.test/v1/chat/completions"
    assert posted["headers"]["Authorization"] == "Bearer secret-token"
    assert posted["json"]["model"] == "gemma-4-31b"
    assert posted["json"]["messages"][0]["role"] == "system"


def test_openai_compatible_backend_can_omit_max_tokens(monkeypatch):
    posted = {}

    class FakeResponse:
        def raise_for_status(self):
            return None

        def json(self):
            return {
                "choices": [
                    {
                        "message": {
                            "content": "remote answer",
                        },
                    }
                ]
            }

    def fake_post(url, headers=None, json=None, timeout=None):
        posted["json"] = json
        return FakeResponse()

    monkeypatch.setenv("OPENAI_COMPATIBLE_API_BASE", "https://example.test/v1/")
    monkeypatch.setenv("OPENAI_COMPATIBLE_API_KEY", "secret-token")
    monkeypatch.setattr(cornelius.requests, "post", fake_post)

    response = cornelius.call_agent_openai_compatible("interpret this Gage R&R result", max_tokens=None)

    assert response == "remote answer"
    assert "max_tokens" not in posted["json"]


def test_call_agent_auto_falls_back_to_local_on_hf_error(monkeypatch):
    monkeypatch.setattr(
        cornelius,
        "call_agent_via_api",
        lambda user_input, max_tokens=300, history=None: "Error: HF quota exceeded",
    )
    monkeypatch.setattr(
        cornelius,
        "call_agent_local",
        lambda user_input, max_tokens=300, history=None: "local answer",
    )

    response = cornelius.call_agent("interpret my gage result", backend="auto")

    assert "local mode" in response
    assert "local answer" in response


def test_call_agent_auto_returns_hf_answer_when_available(monkeypatch):
    monkeypatch.setattr(
        cornelius,
        "call_agent_via_api",
        lambda user_input, max_tokens=300, history=None: "hf answer",
    )
    monkeypatch.setattr(
        cornelius,
        "call_agent_local",
        lambda user_input, max_tokens=300, history=None: "local answer",
    )

    assert cornelius.call_agent("interpret my gage result", backend="auto") == "hf answer"


def test_call_agent_defaults_to_configured_backend(monkeypatch):
    monkeypatch.setenv("CORNELIUS_BACKEND", "local")
    monkeypatch.setattr(
        cornelius,
        "call_agent_local",
        lambda user_input, max_tokens=300, history=None: "local answer",
    )

    assert cornelius.call_agent("interpret my gage result") == "local answer"


def test_call_agent_defaults_to_openai_compatible_backend(monkeypatch):
    monkeypatch.delenv("CORNELIUS_BACKEND", raising=False)
    monkeypatch.setattr(
        cornelius,
        "call_agent_openai_compatible",
        lambda user_input, max_tokens=300, history=None: "remote answer",
    )

    response = cornelius.call_agent("interpret my gage result")

    assert response == "remote answer"
