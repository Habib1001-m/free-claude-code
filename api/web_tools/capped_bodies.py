"""Bounded reads for streaming HTTP response bodies (httpx + aiohttp)."""

from __future__ import annotations

from collections.abc import AsyncIterator

import aiohttp
import httpx

_CHUNK_SIZE = 65_536


async def iter_httpx_response_body_under_cap(
    response: httpx.Response, max_bytes: int
) -> AsyncIterator[bytes]:
    """Yield bytes from ``response`` until ``max_bytes`` total has been yielded."""
    if max_bytes <= 0:
        return
    received = 0
    async for chunk in response.aiter_bytes(chunk_size=_CHUNK_SIZE):
        if received >= max_bytes:
            break
        remaining = max_bytes - received
        if len(chunk) <= remaining:
            received += len(chunk)
            yield chunk
            if received >= max_bytes:
                break
        else:
            yield chunk[:remaining]
            break


async def drain_httpx_response_body_capped(
    response: httpx.Response, max_bytes: int
) -> None:
    async for _ in iter_httpx_response_body_under_cap(response, max_bytes):
        pass


async def read_httpx_response_body_capped(
    response: httpx.Response, max_bytes: int
) -> bytes:
    return b"".join(
        [
            piece
            async for piece in iter_httpx_response_body_under_cap(response, max_bytes)
        ]
    )


async def read_aiohttp_body_capped(
    response: aiohttp.ClientResponse, max_bytes: int
) -> bytes:
    received = 0
    parts: list[bytes] = []
    async for chunk in response.content.iter_chunked(_CHUNK_SIZE):
        if received >= max_bytes:
            break
        remaining = max_bytes - received
        if len(chunk) <= remaining:
            received += len(chunk)
            parts.append(chunk)
        else:
            parts.append(chunk[:remaining])
            break
    return b"".join(parts)


async def drain_aiohttp_body_capped(
    response: aiohttp.ClientResponse, max_bytes: int
) -> None:
    if max_bytes <= 0:
        return
    received = 0
    async for chunk in response.content.iter_chunked(_CHUNK_SIZE):
        received += len(chunk)
        if received >= max_bytes:
            break
