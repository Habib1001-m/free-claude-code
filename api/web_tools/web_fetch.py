"""DNS-pinned HTTP fetch for local ``web_fetch`` tool execution."""

from __future__ import annotations

import asyncio
import socket
from urllib.parse import urljoin, urlparse

from aiohttp import ClientSession, ClientTimeout, TCPConnector
from aiohttp.abc import AbstractResolver, ResolveResult

from . import constants
from .capped_bodies import (
    drain_aiohttp_body_capped,
    read_aiohttp_body_capped,
)
from .constants import (
    _MAX_FETCH_CHARS,
    _REDIRECT_RESPONSE_BODY_CAP_BYTES,
    _REQUEST_TIMEOUT_S,
    _WEB_FETCH_REDIRECT_STATUSES,
    _WEB_TOOL_HTTP_HEADERS,
)
from .egress import (
    WebFetchEgressPolicy,
    WebFetchEgressViolation,
    get_validated_stream_addrinfos_for_egress,
)
from .parsers import HTMLTextParser

_NUMERIC_RESOLVE_FLAGS = socket.AI_NUMERICHOST | socket.AI_NUMERICSERV
_NAME_RESOLVE_FLAGS = socket.NI_NUMERICHOST | socket.NI_NUMERICSERV


def getaddrinfo_rows_to_resolve_results(
    host: str, addrinfos: list[tuple]
) -> list[ResolveResult]:
    """Map :func:`socket.getaddrinfo` rows to aiohttp :class:`ResolveResult` (ThreadedResolver logic)."""
    out: list[ResolveResult] = []
    for family, _type, proto, _canon, sockaddr in addrinfos:
        if family == socket.AF_INET6:
            if len(sockaddr) < 3:
                continue
            if sockaddr[3]:
                resolved_host, port = socket.getnameinfo(sockaddr, _NAME_RESOLVE_FLAGS)
            else:
                resolved_host, port = sockaddr[:2]
        else:
            assert family == socket.AF_INET, family
            resolved_host, port = sockaddr[0], sockaddr[1]
            resolved_host = str(resolved_host)
            port = int(port)
        out.append(
            ResolveResult(
                hostname=host,
                host=resolved_host,
                port=int(port),
                family=family,
                proto=proto,
                flags=_NUMERIC_RESOLVE_FLAGS,
            )
        )
    return out


class PinnedEgressStaticResolver(AbstractResolver):
    """Return only pre-validated :class:`ResolveResult` for the outbound request."""

    def __init__(self, results: list[ResolveResult]) -> None:
        self._results = results

    async def resolve(
        self, host: str, port: int = 0, family: int = socket.AF_INET
    ) -> list[ResolveResult]:
        return self._results

    async def close(self) -> None:  # pragma: no cover - aiohttp contract
        return


async def run_web_fetch(url: str, egress: WebFetchEgressPolicy) -> dict[str, str]:
    """Fetch URL with manual redirects; each hop is DNS-pinned to validated addresses."""
    current_url = url
    redirect_hops = 0
    timeout = ClientTimeout(total=_REQUEST_TIMEOUT_S)

    while True:
        addr_infos = await asyncio.to_thread(
            get_validated_stream_addrinfos_for_egress, current_url, egress
        )
        host = urlparse(current_url).hostname or ""
        results = getaddrinfo_rows_to_resolve_results(host, addr_infos)
        resolver = PinnedEgressStaticResolver(results)
        connector = TCPConnector(
            resolver=resolver,
            force_close=True,
        )
        try:
            async with (
                ClientSession(
                    timeout=timeout,
                    headers=_WEB_TOOL_HTTP_HEADERS,
                    connector=connector,
                ) as session,
                session.get(current_url, allow_redirects=False) as response,
            ):
                if response.status in _WEB_FETCH_REDIRECT_STATUSES:
                    await drain_aiohttp_body_capped(
                        response, _REDIRECT_RESPONSE_BODY_CAP_BYTES
                    )
                    if redirect_hops >= constants._MAX_WEB_FETCH_REDIRECTS:
                        raise WebFetchEgressViolation(
                            "web_fetch exceeded maximum redirects "
                            f"({constants._MAX_WEB_FETCH_REDIRECTS})"
                        )
                    location = response.headers.get("location")
                    if not location or not location.strip():
                        raise WebFetchEgressViolation(
                            "web_fetch redirect response missing Location header"
                        )
                    current_url = urljoin(str(response.url), location.strip())
                    redirect_hops += 1
                    continue
                response.raise_for_status()
                content_type = response.headers.get("content-type", "text/plain")
                final_url = str(response.url)
                encoding = response.get_encoding() or "utf-8"
                body_bytes = await read_aiohttp_body_capped(
                    response, constants._MAX_WEB_FETCH_RESPONSE_BYTES
                )
        finally:
            await connector.close()

        break

    text = body_bytes.decode(encoding, errors="replace")
    title = final_url
    data = text
    if "html" in content_type.lower():
        parser = HTMLTextParser()
        parser.feed(text)
        title = parser.title or final_url
        data = "\n".join(parser.text_parts)
    return {
        "url": final_url,
        "title": title,
        "media_type": "text/plain",
        "data": data[:_MAX_FETCH_CHARS],
    }
