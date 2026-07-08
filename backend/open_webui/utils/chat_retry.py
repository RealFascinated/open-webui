"""Auto-retry helpers for chat completions that stall or return no content."""

from __future__ import annotations

import asyncio
import logging
from collections.abc import AsyncIterator
from typing import Any

from open_webui.env import CHAT_RESPONSE_IDLE_TIMEOUT, CHAT_RESPONSE_MAX_EMPTY_RETRIES
from open_webui.utils.misc import get_output_text

log = logging.getLogger(__name__)


class StreamIdleTimeoutError(Exception):
    """Raised when an upstream stream emits no data within the idle timeout."""


async def aiter_with_idle_timeout(
    iterator: AsyncIterator[Any],
    timeout_seconds: float,
) -> AsyncIterator[Any]:
    """Yield items from an async iterator, aborting on idle timeout."""
    if timeout_seconds <= 0:
        async for item in iterator:
            yield item
        return

    aiter_obj = iterator.__aiter__()
    while True:
        try:
            item = await asyncio.wait_for(aiter_obj.__anext__(), timeout=timeout_seconds)
        except StopAsyncIteration:
            break
        except TimeoutError as exc:
            raise StreamIdleTimeoutError from exc
        yield item


async def aclose_streaming_response(response: Any) -> None:
    """Close an upstream streaming response body and release the connection."""
    body_iterator = getattr(response, 'body_iterator', None)
    if body_iterator is not None and hasattr(body_iterator, 'aclose'):
        try:
            await asyncio.shield(body_iterator.aclose())
        except Exception:
            pass


def assistant_response_has_content(output: list | None, content: str | None) -> bool:
    """Return True when the assistant produced any substantive output."""
    if content and str(content).strip():
        return True

    if not output or not isinstance(output, list):
        return False

    for item in output:
        if not isinstance(item, dict):
            continue

        item_type = item.get('type')
        if item_type == 'message':
            if get_output_text([item]).strip():
                return True
        elif item_type == 'reasoning':
            for part in item.get('content', []):
                if isinstance(part, dict) and (part.get('text') or '').strip():
                    return True
        elif item_type in ('function_call', 'open_webui:code_interpreter'):
            return True

    return False


def get_retry_reason(
    output: list | None,
    content: str | None,
    *,
    stream_timed_out: bool = False,
) -> str | None:
    """Return a retry reason key when the response should be retried."""
    if stream_timed_out:
        return 'timeout'
    if not assistant_response_has_content(output, content):
        return 'empty'
    return None


_RETRY_DESCRIPTIONS = {
    'empty': 'Model returned no response — retrying ({attempt}/{max_attempts})',
    'timeout': 'Model stopped responding — retrying ({attempt}/{max_attempts})',
}

_EXHAUSTED_DESCRIPTIONS = {
    'empty': 'Model returned no response — all {max_attempts} retry attempts failed',
    'timeout': 'Model stopped responding — all {max_attempts} retry attempts failed',
}


def upsert_status_entry(status_history: list | None, status: dict) -> list:
    """Replace the latest chat_retry status instead of appending another one."""
    history = list(status_history or [])
    if status.get('action') == 'chat_retry' and history and history[-1].get('action') == 'chat_retry':
        history[-1] = status
        return history
    history.append(status)
    return history


async def emit_chat_retry_status(
    event_emitter,
    attempt: int,
    max_attempts: int = CHAT_RESPONSE_MAX_EMPTY_RETRIES,
    reason: str = 'empty',
) -> None:
    if not event_emitter:
        return

    template = _RETRY_DESCRIPTIONS.get(reason, _RETRY_DESCRIPTIONS['empty'])
    await event_emitter(
        {
            'type': 'status',
            'data': {
                'action': 'chat_retry',
                'description': template.format(attempt=attempt, max_attempts=max_attempts),
                'done': False,
                'attempt': attempt,
                'max_attempts': max_attempts,
                'reason': reason,
            },
        }
    )


async def emit_chat_retry_exhausted(
    event_emitter,
    max_attempts: int = CHAT_RESPONSE_MAX_EMPTY_RETRIES,
    reason: str = 'empty',
) -> None:
    if not event_emitter:
        return

    template = _EXHAUSTED_DESCRIPTIONS.get(reason, _EXHAUSTED_DESCRIPTIONS['empty'])
    await event_emitter(
        {
            'type': 'status',
            'data': {
                'action': 'chat_retry',
                'description': template.format(max_attempts=max_attempts),
                'done': True,
                'max_attempts': max_attempts,
                'reason': reason,
            },
        }
    )


async def prepare_chat_retry(
    event_emitter,
    attempt: int,
    reason: str,
    *,
    response: Any | None = None,
) -> dict[str, Any]:
    """Emit retry status, close any hung stream, and return reset streaming state."""
    log.warning(
        'Chat response retry %s/%s for reason=%s',
        attempt,
        CHAT_RESPONSE_MAX_EMPTY_RETRIES,
        reason,
    )
    await emit_chat_retry_status(event_emitter, attempt, CHAT_RESPONSE_MAX_EMPTY_RETRIES, reason)

    if response is not None:
        await aclose_streaming_response(response)

    return {
        'output': [],
        'content': '',
        'prior_output': [],
        'tool_calls': [],
        'stream_timed_out': False,
    }
