"""Tests for ``api.messaging_workspace`` path/url helpers."""

from __future__ import annotations

import os
import tempfile

from api.messaging_workspace import (
    messaging_proxy_v1_url,
    plans_directory_relative_to_workspace,
    resolve_claude_data_dir_abs,
    resolve_cli_workspace_abs,
)
from config.settings import Settings


def test_resolve_cli_workspace_abs_prefers_allowed_dir() -> None:
    with tempfile.TemporaryDirectory() as tmp:
        s = Settings(allowed_dir=tmp)
        assert resolve_cli_workspace_abs(s) == os.path.abspath(tmp)


def test_resolve_cli_workspace_abs_fallback_cwd(monkeypatch, tmp_path) -> None:
    monkeypatch.chdir(tmp_path)
    s = Settings(allowed_dir="")
    assert resolve_cli_workspace_abs(s) == os.path.abspath(str(tmp_path))


def test_resolve_claude_data_dir_abs() -> None:
    with tempfile.TemporaryDirectory() as tmp:
        s = Settings(claude_workspace=tmp)
        assert resolve_claude_data_dir_abs(s) == os.path.abspath(tmp)


def test_plans_directory_relative_to_workspace(tmp_path) -> None:
    workspace = tmp_path / "ws"
    data = tmp_path / "agent"
    workspace.mkdir()
    data.mkdir()
    rel = plans_directory_relative_to_workspace(str(workspace), str(data))
    plans_abs = os.path.abspath(os.path.join(str(data), "plans"))
    assert os.path.abspath(os.path.join(str(workspace), rel)) == plans_abs


def test_messaging_proxy_v1_url() -> None:
    s = Settings(host="127.0.0.1", port=8787)
    assert messaging_proxy_v1_url(s) == "http://127.0.0.1:8787/v1"
