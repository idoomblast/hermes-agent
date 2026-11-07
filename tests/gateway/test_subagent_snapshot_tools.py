"""The canonical subagent projection carries the tool history.

Regression for the ``/agents`` detail pane: ``_SUBAGENT_FIELDS`` omitted ``tools``
while the shared ``SubagentSnapshot`` contract declares it and the legacy
``tui_gateway`` projection included it, so a child that called a dozen tools
rendered one row (the ``last_tool`` fallback) in the canonical client.
"""

from gateway import session_ancillary
from tui_gateway.contracts.registry import METHODS, check_result


RECORD = {
    'subagent_id': 'sub-1',
    'parent_id': 'parent-1',
    'depth': 1,
    'goal': 'map the plugin surface',
    'delegation_id': 'delegation-1',
    'model': 'gpt-6.1-sol',
    'started_at': 1762400000.0,
    'status': 'running',
    'tool_count': 3,
    'last_tool': 'terminal',
    'accepting_steer': True,
    'tools': ['read_file', 'grep', 'terminal'],
}


def _project(monkeypatch, records):
    monkeypatch.setattr(session_ancillary, '_require_current_route', lambda *_args: None)
    monkeypatch.setattr(
        session_ancillary, '_owner_objects', lambda *_args, **_kwargs: (None, records))
    return session_ancillary._project(object(), object(), {}, 'subagents')


def test_subagent_projection_carries_the_tool_history(monkeypatch):
    rows = _project(monkeypatch, [dict(RECORD)])['subagents']

    assert rows[0]['tools'] == ['read_file', 'grep', 'terminal']
    assert rows[0]['last_tool'] == 'terminal'


def test_subagent_projection_normalises_an_absent_history_to_an_empty_list(monkeypatch):
    record = {key: value for key, value in RECORD.items() if key != 'tools'}

    rows = _project(monkeypatch, [record])['subagents']

    # The wire contract declares ``tools`` as a non-null list: a child registers before its
    # first tool call, and ``None`` there fails result validation on ``subagent.list``.
    assert rows[0]['tools'] == []
    assert rows[0]['last_tool'] == 'terminal'


def test_subagent_projection_satisfies_the_dispatch_contract(monkeypatch):
    rows = _project(monkeypatch, [dict(RECORD)])['subagents']

    check_result(METHODS['subagent.list'], {'subagents': rows, 'delegations': []})


def test_subagent_projection_satisfies_the_contract_before_the_first_tool_call(monkeypatch):
    record = {key: value for key, value in RECORD.items() if key != 'tools'}

    rows = _project(monkeypatch, [record])['subagents']

    check_result(METHODS['subagent.list'], {'subagents': rows, 'delegations': []})
