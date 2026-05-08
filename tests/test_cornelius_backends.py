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


def test_call_agent_default_auto_falls_back_for_future_callers(monkeypatch):
    monkeypatch.delenv("CORNELIUS_BACKEND", raising=False)
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

    response = cornelius.call_agent("interpret my gage result")

    assert "local mode" in response
    assert "local answer" in response
