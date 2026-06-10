from gage_rr_companion import cornelius


def test_legacy_local_backend_routes_to_llama_cpp(monkeypatch):
    calls = []

    def fake_llama_cpp(user_input, max_tokens=300, history=None):
        calls.append((user_input, max_tokens, history))
        return "local answer"

    monkeypatch.setattr(cornelius, "call_agent_llama_cpp", fake_llama_cpp)

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



def test_configured_llama_cpp_aliases(monkeypatch):
    monkeypatch.setenv("CORNELIUS_BACKEND", "embedded")

    assert cornelius.get_agent_backend() == "llama_cpp"


def test_call_agent_uses_llama_cpp_backend(monkeypatch):
    calls = []

    def fake_llama_cpp(user_input, max_tokens=300, history=None):
        calls.append((user_input, max_tokens, history))
        return "embedded answer"

    monkeypatch.setattr(cornelius, "call_agent_llama_cpp", fake_llama_cpp)

    response = cornelius.call_agent("why is ndc low?", backend="llama_cpp")

    assert response == "embedded answer"
    assert calls[0][0] == "why is ndc low?"


def test_llama_cpp_backend_uses_chat_completion(monkeypatch):
    request = {}

    class FakeLlama:
        def create_chat_completion(self, **kwargs):
            request.update(kwargs)
            return {
                "choices": [
                    {
                        "message": {
                            "content": "embedded answer",
                        },
                    }
                ]
            }

    monkeypatch.setattr(cornelius, "_get_llama_cpp_model", lambda: FakeLlama())

    response = cornelius.call_agent_llama_cpp("why is ndc low?", max_tokens=40)

    assert response == "embedded answer"
    assert request["max_tokens"] == 40
    assert request["messages"][0]["role"] == "system"


def test_llama_cpp_backend_can_omit_max_tokens(monkeypatch):
    request = {}

    class FakeLlama:
        def create_chat_completion(self, **kwargs):
            request.update(kwargs)
            return {
                "choices": [
                    {
                        "message": {
                            "content": "embedded answer",
                        },
                    }
                ]
            }

    monkeypatch.setattr(cornelius, "_get_llama_cpp_model", lambda: FakeLlama())

    response = cornelius.call_agent_llama_cpp("interpret this Gage R&R result", max_tokens=None)

    assert response == "embedded answer"
    assert "max_tokens" not in request

def test_configured_openai_compatible_aliases(monkeypatch):
    monkeypatch.setenv("CORNELIUS_BACKEND", "api")

    assert cornelius.get_agent_backend() == "openai_compatible"


def test_model_presets_use_backend_specific_defaults(monkeypatch):
    monkeypatch.setenv("HF_MODEL_ID", "qwen/qwen3")
    monkeypatch.delenv("OPENAI_COMPATIBLE_MODEL_ID", raising=False)
    monkeypatch.delenv("CORNELIUS_MODEL_ID", raising=False)
    monkeypatch.delenv("LLAMA_CPP_REPO_ID", raising=False)

    assert cornelius.get_model_id() == "Qwen/Qwen2.5-Coder-3B-Instruct"
    assert cornelius.get_openai_compatible_model_id() == "gemma-4-31b"
    assert cornelius.get_llama_cpp_repo_id() == "Qwen/Qwen2.5-Coder-3B-Instruct-GGUF"


def test_openai_compatible_model_can_be_configured(monkeypatch):
    monkeypatch.setenv("OPENAI_COMPATIBLE_MODEL_ID", "gpt-4o-mini")

    assert cornelius.get_openai_compatible_model_id() == "gpt-4o-mini"


def test_openai_compatible_timeout_can_be_configured(monkeypatch):
    monkeypatch.setenv("OPENAI_COMPATIBLE_TIMEOUT_SECONDS", "20")

    assert cornelius.get_openai_compatible_timeout_seconds() == 20


def test_openai_compatible_timeout_ignores_invalid_override(monkeypatch):
    monkeypatch.setenv("OPENAI_COMPATIBLE_TIMEOUT_SECONDS", "not-a-number")

    assert cornelius.get_openai_compatible_timeout_seconds() == cornelius.DEFAULT_OPENAI_COMPATIBLE_TIMEOUT_SECONDS


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
        "call_agent_llama_cpp",
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
        "call_agent_llama_cpp",
        lambda user_input, max_tokens=300, history=None: "local answer",
    )

    assert cornelius.call_agent("interpret my gage result", backend="auto") == "hf answer"


def test_call_agent_defaults_to_configured_backend(monkeypatch):
    monkeypatch.setenv("CORNELIUS_BACKEND", "local")
    monkeypatch.setattr(
        cornelius,
        "call_agent_llama_cpp",
        lambda user_input, max_tokens=300, history=None: "local answer",
    )

    assert cornelius.call_agent("interpret my gage result") == "local answer"


def test_call_agent_defaults_to_embedded_local_backend(monkeypatch):
    monkeypatch.delenv("CORNELIUS_BACKEND", raising=False)
    monkeypatch.setattr(
        cornelius,
        "call_agent_llama_cpp",
        lambda user_input, max_tokens=300, history=None: "local answer",
    )

    response = cornelius.call_agent("interpret my gage result")

    assert response == "local answer"
