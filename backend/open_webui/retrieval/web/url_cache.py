"""Shared URL snippet cache for search_web and fetch_url."""

from __future__ import annotations

import asyncio
import time
from urllib.parse import urlparse, urlunparse

_cache: dict[str, tuple[float, dict]] = {}
_cache_lock = asyncio.Lock()


def normalize_url(url: str) -> str:
    parsed = urlparse(url.strip())
    if not parsed.scheme or not parsed.netloc:
        return url.strip().lower()

    host = (parsed.hostname or '').lower()
    port = parsed.port
    netloc = f'{host}:{port}' if port and port not in (80, 443) else host
    path = parsed.path.rstrip('/') or '/'
    return urlunparse((parsed.scheme.lower(), netloc, path, '', '', ''))


async def cache_search_results(results: list[dict], ttl: int) -> None:
    if ttl <= 0 or not results:
        return

    expires = time.monotonic() + ttl
    async with _cache_lock:
        for result in results:
            if not isinstance(result, dict):
                continue
            url = result.get('link') or result.get('url')
            if not url:
                continue
            key = normalize_url(str(url))
            snippet = (result.get('snippet') or result.get('content') or '').strip()
            if not snippet:
                continue
            _cache[key] = (
                expires,
                {
                    'url': str(url),
                    'title': result.get('title') or str(url),
                    'description': result.get('description'),
                    'snippet': snippet,
                    'source': 'search',
                },
            )


async def get_cached_snippet(url: str, ttl: int) -> dict | None:
    if ttl <= 0:
        return None

    key = normalize_url(url)
    now = time.monotonic()
    async with _cache_lock:
        entry = _cache.get(key)
        if not entry:
            return None
        expires, payload = entry
        if expires <= now:
            _cache.pop(key, None)
            return None
        return payload.copy()


async def set_cached_full(url: str, entry: dict, ttl: int) -> None:
    if ttl <= 0:
        return

    key = normalize_url(url)
    snippet = (entry.get('content') or entry.get('snippet') or '').strip()
    expires = time.monotonic() + ttl
    async with _cache_lock:
        _cache[key] = (
            expires,
            {
                'url': url,
                'title': entry.get('title') or url,
                'description': entry.get('description'),
                'snippet': snippet[:2000] if snippet else '',
                'content': entry.get('content'),
                'source': 'fetch',
            },
        )


def cached_snippet_to_fetch_entry(cached: dict) -> dict:
    snippet = cached.get('snippet') or ''
    return {
        'url': cached.get('url'),
        'title': cached.get('title'),
        'description': cached.get('description'),
        'content': snippet,
        'truncated': False,
        'word_count': len(snippet.split()) if snippet else 0,
        'depth': 'snippet',
        'from_cache': True,
    }
