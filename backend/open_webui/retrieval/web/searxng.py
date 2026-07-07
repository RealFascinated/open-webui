from __future__ import annotations

import logging

from open_webui.retrieval.web.main import SearchResult, get_filtered_results
from open_webui.utils.session_pool import get_session

log = logging.getLogger(__name__)

# SearXNG request headers — identifies the bot to instance operators.
_SEARXNG_HEADERS = {
    'User-Agent': 'Open WebUI (https://github.com/open-webui/open-webui) RAG Bot',
    'Accept': 'application/json',
    'Accept-Encoding': 'gzip, deflate',
    'Accept-Language': 'en-US,en;q=0.5',
    'Connection': 'keep-alive',
}

_RATE_LIMIT_HINTS = (
    'rate',
    'limit',
    'captcha',
    'too many',
    'blocked',
    'suspended',
    'timeout',
    '429',
    '403',
)


def _format_engine_failure(entry: object) -> str:
    if isinstance(entry, (list, tuple)) and entry:
        name = str(entry[0])
        reason = str(entry[1]) if len(entry) > 1 else ''
        return f'{name}: {reason}' if reason else name
    return str(entry)


def _engine_failures(payload: dict) -> list[str]:
    failures: list[str] = []
    for entry in payload.get('unresponsive_engines') or []:
        formatted = _format_engine_failure(entry)
        if formatted:
            failures.append(formatted)
    return failures


def _looks_rate_limited(failures: list[str]) -> bool:
    haystack = ' '.join(failures).lower()
    return any(hint in haystack for hint in _RATE_LIMIT_HINTS)


def _raise_if_searxng_unusable(payload: dict, query: str, *, filtered_all: bool = False) -> None:
    failures = _engine_failures(payload)
    raw_count = len(payload.get('results') or [])

    if filtered_all and raw_count > 0:
        raise RuntimeError(
            f'SearXNG returned {raw_count} results for "{query}" but all were removed by the '
            'web search domain filter. Check Admin → Settings → Web Search → Domain Filter List.'
        )

    if failures and not payload.get('results'):
        joined = '; '.join(failures[:6])
        if _looks_rate_limited(failures):
            raise RuntimeError(
                f'SearXNG upstream engines are rate-limited or blocked ({joined}). '
                'Wait and retry later, reduce parallel searches, or configure additional SearXNG engines.'
            )
        raise RuntimeError(f'SearXNG upstream engines failed ({joined}). Check your SearXNG instance.')

    if not payload.get('results') and payload.get('number_of_results', 0) == 0 and not failures:
        # Genuine empty SERP — caller may still want to treat as no results.
        return


async def search_searxng(
    query_url: str,
    query: str,
    count: int,
    filter_list: list[str | None] | None = None,
    **kwargs,
) -> list[SearchResult]:
    """Query a SearXNG instance and return results sorted by relevance score.

    Optional keyword arguments (language, safesearch, time_range, categories)
    are forwarded directly as SearXNG query parameters.
    """
    # Normalise legacy ``<query>``-style URLs by stripping any query string.
    if '<query>' in query_url:
        query_url = query_url.split('?')[0]

    params = {
        'q': query,
        'format': 'json',
        'pageno': 1,
        'safesearch': kwargs.get('safesearch', '1'),
        'language': kwargs.get('language', 'all').strip().rstrip(','),
        'time_range': kwargs.get('time_range', ''),
        'categories': ''.join(kwargs.get('categories', [])),
        'theme': 'simple',
        'image_proxy': 0,
    }

    log.debug('searching %s', query_url)

    session = await get_session()
    async with session.get(query_url, headers=_SEARXNG_HEADERS, params=params) as response:
        if response.status == 403:
            raise RuntimeError(
                'SearXNG returned 403 Forbidden. Enable JSON output in SearXNG settings.yml '
                '(search.formats must include json) and verify the instance allows API access.'
            )

        content_type = (response.headers.get('Content-Type') or '').lower()
        if response.status == 200 and 'json' not in content_type:
            preview = (await response.text())[:200].strip()
            if preview.startswith('<!'):
                raise RuntimeError(
                    'SearXNG returned HTML instead of JSON. Enable json in SearXNG settings.yml '
                    'and set the Query URL to http://your-instance/search (Open WebUI adds format=json).'
                )
            raise RuntimeError(f'SearXNG returned unexpected content type: {content_type or "unknown"}')

        response.raise_for_status()
        payload = await response.json()

    if not isinstance(payload, dict):
        raise RuntimeError('SearXNG returned an unexpected response payload.')

    raw_results = payload.get('results')
    if raw_results is None:
        raise RuntimeError(
            'SearXNG response is missing a results field. '
            'Check the Query URL points to the /search endpoint.'
        )

    results = sorted(raw_results, key=lambda x: x.get('score', 0), reverse=True)
    raw_count = len(results)

    if filter_list:
        results = get_filtered_results(results, filter_list)

    if not results:
        _raise_if_searxng_unusable(payload, query, filtered_all=raw_count > 0)

    return [
        SearchResult(
            link=item.get('url', ''),
            title=item.get('title'),
            snippet=item.get('content'),
        )
        for item in results[:count]
    ]
