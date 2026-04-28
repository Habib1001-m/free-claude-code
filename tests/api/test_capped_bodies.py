"""Tests for bounded HTTP body readers."""

from unittest.mock import MagicMock

import pytest

from api.web_tools.capped_bodies import (
    drain_aiohttp_body_capped,
    read_aiohttp_body_capped,
)


@pytest.mark.asyncio
async def test_read_aiohttp_body_capped_truncates_single_oversized_chunk() -> None:
    cap = 400

    async def iter_chunked(_size: int):
        yield b"x" * (cap * 15)

    response = MagicMock()
    response.content.iter_chunked = iter_chunked

    out = await read_aiohttp_body_capped(response, cap)
    assert len(out) == cap
    assert out == b"x" * cap


@pytest.mark.asyncio
async def test_drain_aiohttp_body_capped_stops_after_first_chunk_when_oversized() -> (
    None
):
    cap = 200
    chunk_calls = {"n": 0}

    async def iter_chunked(_size: int):
        chunk_calls["n"] += 1
        yield b"w" * (cap * 5)

    response = MagicMock()
    response.content.iter_chunked = iter_chunked

    await drain_aiohttp_body_capped(response, cap)
    assert chunk_calls["n"] == 1
