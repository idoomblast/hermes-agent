"""Out-of-process steering: a supervisor queues JSONL in HERMES_FLEET_STEER_FILE
and core delivers it through the SAME trusted channel as an in-process /steer —
a standalone role:"user" marker row after the newest tool result.

Delivery must never be smeared onto a tool result: models correctly refuse
instructions that arrive through tool output as prompt injection.
"""

from __future__ import annotations

import json

import pytest

from agent.agent_runtime_helpers import (
    _EXTERNAL_STEER_ENV,
    _drain_external_steer,
    apply_pending_steer_to_tool_results,
)


class _Agent:
    """Minimal surface used by apply_pending_steer_to_tool_results."""

    def __init__(self, pending: str | None = None):
        self._pending = pending

    def _drain_pending_steer(self):
        value, self._pending = self._pending, None
        return value


def _queue(path, *texts):
    path.write_text("".join(json.dumps({"text": t}) + "\n" for t in texts), encoding="utf-8")


@pytest.fixture()
def steer_file(tmp_path, monkeypatch):
    path = tmp_path / "steer.jsonl"
    monkeypatch.setenv(_EXTERNAL_STEER_ENV, str(path))
    return path


def test_drain_reads_jsonl_and_consumes_once(steer_file):
    _queue(steer_file, "focus on tests", "skip the legacy admin")
    assert _drain_external_steer() == "focus on tests\n\nskip the legacy admin"
    assert _drain_external_steer() == ""


def test_drain_noop_without_env(tmp_path, monkeypatch):
    monkeypatch.delenv(_EXTERNAL_STEER_ENV, raising=False)
    path = tmp_path / "unused.jsonl"
    _queue(path, "never delivered")
    assert _drain_external_steer() == ""
    assert path.read_text(encoding="utf-8") != ""


def test_drain_fails_open_on_missing_or_garbage(steer_file):
    assert _drain_external_steer() == ""  # file absent
    steer_file.write_text("not json\n" + json.dumps({"text": "real"}) + "\n", encoding="utf-8")
    assert _drain_external_steer() == "real"


def test_delivered_as_user_steer_row_not_tool_output(steer_file):
    _queue(steer_file, "narrow the scope to src/api")
    messages = [
        {"role": "assistant", "content": "", "tool_calls": [{"id": "c1"}]},
        {"role": "tool", "content": "exit 0", "tool_call_id": "c1"},
    ]
    apply_pending_steer_to_tool_results(_Agent(), messages, num_tool_msgs=1)

    assert messages[0]["content"] == ""
    assert messages[1]["content"] == "exit 0"  # tool result untouched
    row = messages[-1]
    assert row["role"] == "user"
    assert row["display_kind"] == "steer"
    assert "OUT-OF-BAND USER MESSAGE" in row["content"]
    assert "narrow the scope to src/api" in row["content"]


def test_in_process_and_external_steer_merge(steer_file):
    _queue(steer_file, "external half")
    messages = [
        {"role": "assistant", "content": ""},
        {"role": "tool", "content": "ok"},
    ]
    apply_pending_steer_to_tool_results(_Agent("in-process half"), messages, num_tool_msgs=1)

    content = messages[-1]["content"]
    assert "in-process half" in content
    assert "external half" in content
    assert messages[-1]["role"] == "user"


def test_no_steer_means_no_message(steer_file):
    messages = [{"role": "assistant", "content": ""}, {"role": "tool", "content": "ok"}]
    apply_pending_steer_to_tool_results(_Agent(), messages, num_tool_msgs=1)
    assert len(messages) == 2
