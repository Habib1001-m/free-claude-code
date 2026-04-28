"""Platform-neutral voice note helpers."""

from __future__ import annotations

import asyncio
from collections.abc import Awaitable, Callable
from pathlib import Path

from loguru import logger

from .models import IncomingMessage


class PendingVoiceRegistry:
    """Track voice notes that are still waiting on transcription."""

    def __init__(self) -> None:
        self._pending: dict[tuple[str, str], tuple[str, str]] = {}
        self._lock = asyncio.Lock()

    async def register(
        self, chat_id: str, voice_msg_id: str, status_msg_id: str
    ) -> None:
        async with self._lock:
            entry = (voice_msg_id, status_msg_id)
            self._pending[(chat_id, voice_msg_id)] = entry
            self._pending[(chat_id, status_msg_id)] = entry

    async def cancel(self, chat_id: str, reply_id: str) -> tuple[str, str] | None:
        async with self._lock:
            entry = self._pending.pop((chat_id, reply_id), None)
            if entry is None:
                return None
            voice_msg_id, status_msg_id = entry
            self._pending.pop((chat_id, voice_msg_id), None)
            self._pending.pop((chat_id, status_msg_id), None)
            return entry

    async def is_pending(self, chat_id: str, voice_msg_id: str) -> bool:
        async with self._lock:
            return (chat_id, voice_msg_id) in self._pending

    async def complete(
        self, chat_id: str, voice_msg_id: str, status_msg_id: str
    ) -> None:
        async with self._lock:
            self._pending.pop((chat_id, voice_msg_id), None)
            self._pending.pop((chat_id, status_msg_id), None)


class VoiceTranscriptionService:
    """Run configured transcription backends off the event loop."""

    def __init__(
        self,
        *,
        hf_token: str = "",
        nvidia_nim_api_key: str = "",
    ) -> None:
        self._hf_token = hf_token
        self._nvidia_nim_api_key = nvidia_nim_api_key

    async def transcribe(
        self,
        file_path: Path,
        mime_type: str,
        *,
        whisper_model: str,
        whisper_device: str,
    ) -> str:
        from .transcription import transcribe_audio

        return await asyncio.to_thread(
            transcribe_audio,
            file_path,
            mime_type,
            whisper_model=whisper_model,
            whisper_device=whisper_device,
            hf_token=self._hf_token,
            nvidia_nim_api_key=self._nvidia_nim_api_key,
        )


async def finalize_voice_note_after_transcription(
    pending: PendingVoiceRegistry,
    *,
    chat_id: str,
    voice_msg_id: str,
    status_msg_id: str,
    transcribed: str,
    build_incoming: Callable[[], IncomingMessage],
    handler: Callable[[IncomingMessage], Awaitable[None]],
    delete_status_message: Callable[[str, str], Awaitable[None]],
    log_raw_messaging_content: bool,
    logger_prefix: str,
) -> None:
    """If still pending after transcription, complete registry and dispatch; else drop status message."""
    if not await pending.is_pending(chat_id, voice_msg_id):
        await delete_status_message(chat_id, status_msg_id)
        return

    await pending.complete(chat_id, voice_msg_id, status_msg_id)
    incoming = build_incoming()

    if log_raw_messaging_content:
        preview = transcribed[:80] + ("..." if len(transcribed) > 80 else "")
        logger.info(
            "{}: chat_id={} message_id={} transcribed={!r}",
            logger_prefix,
            chat_id,
            voice_msg_id,
            preview,
        )
    else:
        logger.info(
            "{}: chat_id={} message_id={} transcribed_len={}",
            logger_prefix,
            chat_id,
            voice_msg_id,
            len(transcribed),
        )

    await handler(incoming)
