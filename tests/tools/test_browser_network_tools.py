import json
from unittest.mock import patch

from tools import browser_tool


def _run(result=None):
    return patch.object(
        browser_tool,
        "_run_browser_command",
        return_value=result or {"success": True, "data": {"ok": True}},
    )


def test_network_request_uses_positional_request_id():
    with patch.object(browser_tool, "_is_camofox_mode", return_value=False), _run() as call:
        payload = json.loads(
            browser_tool.browser_network("request", request_id="req-1", task_id="session")
        )

    assert payload["success"] is True
    call.assert_called_once_with("session", "network", ["request", "req-1"])


def test_har_stop_path_is_positional():
    with patch.object(browser_tool, "_is_camofox_mode", return_value=False), _run() as call:
        payload = json.loads(
            browser_tool.browser_har("stop", path="/tmp/capture.har", task_id="session")
        )

    assert payload["success"] is True
    call.assert_called_once_with(
        "session", "network", ["har", "stop", "/tmp/capture.har"]
    )


def test_route_pattern_is_positional_and_flags_follow():
    with patch.object(browser_tool, "_is_camofox_mode", return_value=False), _run() as call:
        payload = json.loads(
            browser_tool.browser_route(
                "route",
                "**/api/**",
                abort=True,
                resource_type="xhr",
                task_id="session",
            )
        )

    assert payload["success"] is True
    call.assert_called_once_with(
        "session",
        "network",
        ["route", "**/api/**", "--abort", "--resource-type", "xhr"],
    )


def test_network_tools_reject_camofox_backend():
    with patch.object(browser_tool, "_is_camofox_mode", return_value=True):
        payload = json.loads(browser_tool.browser_network())

    assert payload["success"] is False
    assert "Camofox" in payload["error"]
