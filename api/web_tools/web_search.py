"""DuckDuckGo lite HTML search for local ``web_search`` tool execution."""

from __future__ import annotations

import httpx

from .capped_bodies import read_httpx_response_body_capped
from .constants import (
    _MAX_SEARCH_RESULTS,
    _MAX_WEB_FETCH_RESPONSE_BYTES,
    _REQUEST_TIMEOUT_S,
    _WEB_TOOL_HTTP_HEADERS,
)
from .parsers import SearchResultParser


async def run_web_search(query: str) -> list[dict[str, str]]:
    async with (
        httpx.AsyncClient(
            timeout=_REQUEST_TIMEOUT_S,
            follow_redirects=True,
            headers=_WEB_TOOL_HTTP_HEADERS,
        ) as client,
        client.stream(
            "GET",
            "https://lite.duckduckgo.com/lite/",
            params={"q": query},
        ) as response,
    ):
        response.raise_for_status()
        body_bytes = await read_httpx_response_body_capped(
            response, _MAX_WEB_FETCH_RESPONSE_BYTES
        )
    text = body_bytes.decode("utf-8", errors="replace")
    parser = SearchResultParser()
    parser.feed(text)
    return parser.results[:_MAX_SEARCH_RESULTS]
