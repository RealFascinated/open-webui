import time

import pytest

from open_webui.retrieval.web.url_cache import (
    cache_search_results,
    cached_snippet_to_fetch_entry,
    get_cached_snippet,
    normalize_url,
)
from open_webui.tools.builtin import _resolve_chat_timestamp


def test_normalize_url_strips_trailing_slash():
    assert normalize_url('https://Example.com/path/') == normalize_url('https://example.com/path')


@pytest.mark.asyncio
async def test_url_cache_search_then_fetch_snippet():
    results = [
        {
            'link': 'https://example.com/article',
            'title': 'Example Article',
            'snippet': 'A short summary from search.',
        }
    ]
    await cache_search_results(results, ttl=60)

    cached = await get_cached_snippet('https://example.com/article/', 60)
    assert cached is not None
    assert cached['snippet'] == 'A short summary from search.'

    entry = cached_snippet_to_fetch_entry(cached)
    assert entry['from_cache'] is True
    assert entry['depth'] == 'snippet'
    assert entry['content'] == 'A short summary from search.'


@pytest.mark.asyncio
async def test_url_cache_expires():
    await cache_search_results(
        [{'link': 'https://example.com/expired', 'title': 'T', 'snippet': 'gone'}],
        ttl=0,
    )
    cached = await get_cached_snippet('https://example.com/expired', 0)
    assert cached is None


def test_resolve_chat_timestamp_unix():
    assert _resolve_chat_timestamp(1700000000) == 1700000000
    assert _resolve_chat_timestamp('1700000000') == 1700000000


def test_resolve_chat_timestamp_relative():
    now = int(time.time())
    resolved = _resolve_chat_timestamp('last_7_days')
    assert resolved is not None
    assert now - resolved == pytest.approx(7 * 86400, abs=5)


def test_resolve_chat_timestamp_unknown():
    assert _resolve_chat_timestamp('not-a-date') is None
    assert _resolve_chat_timestamp(None) is None
