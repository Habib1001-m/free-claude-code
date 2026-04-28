"""Pure path/url helpers for messaging + CLI composition from :class:`config.settings.Settings`."""

from __future__ import annotations

import os

from config.settings import Settings


def resolve_cli_workspace_abs(settings: Settings) -> str:
    """Absolute workspace directory for the Claude CLI (creates parent dirs is caller's responsibility)."""
    if settings.allowed_dir:
        return os.path.abspath(settings.allowed_dir)
    return os.getcwd()


def resolve_claude_data_dir_abs(settings: Settings) -> str:
    """Absolute path to persisted Claude workspace data (sessions, plans root)."""
    return os.path.abspath(settings.claude_workspace)


def plans_directory_relative_to_workspace(
    workspace_abs: str, claude_workspace_abs: str
) -> str:
    """``plans_directory`` argument for :class:`cli.manager.CLISessionManager`, relative to workspace."""
    plans_dir_abs = os.path.abspath(os.path.join(claude_workspace_abs, "plans"))
    return os.path.relpath(plans_dir_abs, workspace_abs)


def messaging_proxy_v1_url(settings: Settings) -> str:
    """Base URL for the local Anthropic-compatible API (e.g. ``http://127.0.0.1:8787/v1``)."""
    return f"http://{settings.host}:{settings.port}/v1"
