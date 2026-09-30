"""Custom provider `supports_reasoning` declaration → reasoning extra_body gate.

Covers:
  agent/agent_init.py — _custom_provider_supports_reasoning_for_agent()
  run_agent.py — _supports_reasoning_extra_body() custom-provider branch

Custom providers (base_url NOT allowlisted, e.g. self-hosted proxies such as
OmniRoute / LiteLLM) were previously hard-blocked from emitting
`extra_body.reasoning` even when the user explicitly declared reasoning
support. The per-model `supports_reasoning` key mirrors the existing
`supports_vision` declaration and lets `/reasoning <level>` work for custom
providers instead of forcing users to hand-edit `extra_body` in config.yaml.
"""

from types import SimpleNamespace

from agent.agent_init import _custom_provider_supports_reasoning_for_agent
from run_agent import AIAgent


# ── helper: _custom_provider_supports_reasoning_for_agent ─────────────


def test_no_reasoning_declaration_returns_none():
    result = _custom_provider_supports_reasoning_for_agent(
        provider="custom",
        model="go/deepseek-v4-flash",
        base_url="https://omni.idoom.me/v1",
        custom_providers=[
            {
                "name": "Omni",
                "base_url": "https://omni.idoom.me/v1",
                "models": {
                    "go/deepseek-v4-flash": {"context_length": 512000},
                },
            }
        ],
    )
    assert result is None


def test_per_model_supports_reasoning_true():
    result = _custom_provider_supports_reasoning_for_agent(
        provider="custom",
        model="go/deepseek-v4-flash",
        base_url="https://omni.idoom.me/v1",
        custom_providers=[
            {
                "name": "Omni",
                "base_url": "https://omni.idoom.me/v1",
                "models": {
                    "go/deepseek-v4-flash": {"supports_reasoning": True},
                },
            }
        ],
    )
    assert result is True


def test_per_model_supports_reasoning_false_explicit_disable():
    result = _custom_provider_supports_reasoning_for_agent(
        provider="custom",
        model="go/deepseek-v4-flash",
        base_url="https://omni.idoom.me/v1",
        custom_providers=[
            {
                "name": "Omni",
                "base_url": "https://omni.idoom.me/v1",
                "models": {
                    "go/deepseek-v4-flash": {"supports_reasoning": False},
                },
            }
        ],
    )
    assert result is False


def test_per_model_wins_over_entry_level():
    result = _custom_provider_supports_reasoning_for_agent(
        provider="custom",
        model="go/deepseek-v4-flash",
        base_url="https://omni.idoom.me/v1",
        custom_providers=[
            {
                "name": "Omni",
                "base_url": "https://omni.idoom.me/v1",
                "supports_reasoning": True,
                "models": {
                    "go/deepseek-v4-flash": {"supports_reasoning": False},
                },
            }
        ],
    )
    assert result is False


def test_entry_level_supports_reasoning_for_single_model_entry():
    result = _custom_provider_supports_reasoning_for_agent(
        provider="custom",
        model="deepseek-v4-flash",
        base_url="https://omni.idoom.me/v1",
        custom_providers=[
            {
                "name": "Omni",
                "base_url": "https://omni.idoom.me/v1",
                "model": "deepseek-v4-flash",
                "supports_reasoning": True,
            }
        ],
    )
    assert result is True


def test_named_provider_key_matches():
    result = _custom_provider_supports_reasoning_for_agent(
        provider="custom:omni",
        model="glm-5.2",
        base_url="https://omni.idoom.me/v1",
        custom_providers=[
            {
                "provider_key": "omni",
                "name": "Omni",
                "base_url": "https://omni.idoom.me/v1",
                "models": {"glm-5.2": {"supports_reasoning": True}},
            }
        ],
    )
    assert result is True


def test_other_provider_entry_ignored():
    result = _custom_provider_supports_reasoning_for_agent(
        provider="custom:omni",
        model="glm-5.2",
        base_url="https://omni.idoom.me/v1",
        custom_providers=[
            {
                "provider_key": "other",
                "name": "Other",
                "base_url": "https://omni.idoom.me/v1",
                "models": {"glm-5.2": {"supports_reasoning": True}},
            }
        ],
    )
    assert result is None


def test_base_url_trailing_slash_normalized():
    result = _custom_provider_supports_reasoning_for_agent(
        provider="custom",
        model="go/deepseek-v4-flash",
        base_url="https://omni.idoom.me/v1",
        custom_providers=[
            {
                "name": "Omni",
                "base_url": "https://omni.idoom.me/v1/",
                "models": {
                    "go/deepseek-v4-flash": {"supports_reasoning": True},
                },
            }
        ],
    )
    assert result is True


def test_non_custom_provider_returns_none():
    result = _custom_provider_supports_reasoning_for_agent(
        provider="openrouter",
        model="deepseek/deepseek-v4",
        base_url="https://openrouter.ai/api/v1",
        custom_providers=[],
    )
    assert result is None


# ── integration: _supports_reasoning_extra_body gate ──────────────────


def _stub_agent(**overrides):
    attrs = {
        "provider": "custom",
        "model": "go/deepseek-v4-flash",
        "base_url": "https://omni.idoom.me/v1",
        "_base_url_lower": "https://omni.idoom.me/v1",
        "_custom_providers": [
            {
                "name": "Omni",
                "base_url": "https://omni.idoom.me/v1",
                "models": {
                    "go/deepseek-v4-flash": {"supports_reasoning": True},
                },
            }
        ],
    }
    attrs.update(overrides)
    stub = SimpleNamespace(**attrs)
    stub._supports_reasoning_extra_body = (
        AIAgent._supports_reasoning_extra_body.__get__(stub)
    )
    return stub


def test_gate_opens_for_declared_custom_provider():
    agent = _stub_agent()
    assert agent._supports_reasoning_extra_body() is True


def test_gate_stays_closed_for_undeclared_custom_provider():
    agent = _stub_agent(
        _custom_providers=[
            {
                "name": "Omni",
                "base_url": "https://omni.idoom.me/v1",
                "models": {"go/deepseek-v4-flash": {}},
            }
        ]
    )
    assert agent._supports_reasoning_extra_body() is False


def test_gate_stays_closed_for_unknown_non_openrouter_provider():
    agent = _stub_agent(
        provider="acme",
        model="acme-model",
        base_url="https://acme.example/v1",
        _base_url_lower="https://acme.example/v1",
        _custom_providers=[],
    )
    assert agent._supports_reasoning_extra_body() is False


def test_openrouter_path_unchanged_for_custom_with_openrouter_host():
    # A custom provider routed through an openrouter-hosted endpoint still
    # honors the declared flag; without the declaration the legacy path wins.
    agent = _stub_agent(
        base_url="https://openrouter.ai/api/v1",
        _base_url_lower="https://openrouter.ai/api/v1",
        _custom_providers=[],
    )
    assert agent._supports_reasoning_extra_body() is False
