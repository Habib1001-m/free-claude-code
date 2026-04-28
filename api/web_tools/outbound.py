"""Outbound web execution helpers used by streaming transport."""

from __future__ import annotations

from aiohttp import ClientSession
from loguru import logger

from .egress import WebFetchEgressPolicy
from .web_fetch import run_web_fetch as _run_web_fetch
from .web_search import run_web_search as _run_web_search
from .web_tool_logging import (
    log_web_tool_failure as _log_web_tool_failure,
)
from .web_tool_logging import (
    web_tool_client_error_summary as _web_tool_client_error_summary,
)

__all__ = [
    "ClientSession",
    "WebFetchEgressPolicy",
    "_log_web_tool_failure",
    "_run_web_fetch",
    "_run_web_search",
    "_web_tool_client_error_summary",
    "logger",
]
