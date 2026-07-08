from __future__ import annotations

import logging
from typing import Any
from urllib.parse import urlparse

from open_webui.utils.session_pool import get_session

log = logging.getLogger(__name__)

WEB_SEARCH_ENGINE_LABELS: dict[str, str] = {
    'ollama_cloud': 'Ollama Cloud',
    'perplexity_search': 'Perplexity Search',
    'searxng': 'SearXNG',
    'yacy': 'YaCy',
    'google_pse': 'Google PSE',
    'brave': 'Brave',
    'brave_llm_context': 'Brave LLM Context',
    'kagi': 'Kagi',
    'mojeek': 'Mojeek',
    'bocha': 'Bocha',
    'serpstack': 'SerpStack',
    'serper': 'Serper',
    'serphouse': 'SerpHouse',
    'serply': 'Serply',
    'duckduckgo': 'DuckDuckGo',
    'tavily': 'Tavily',
    'searchapi': 'SearchAPI',
    'serpapi': 'SerpAPI',
    'jina': 'Jina',
    'bing': 'Bing',
    'exa': 'Exa',
    'perplexity': 'Perplexity',
    'microsoft_web_iq': 'Microsoft Web IQ',
    'sougou': 'Sogou',
    'firecrawl': 'Firecrawl',
    'external': 'External',
    'yandex': 'Yandex',
    'youcom': 'You.com',
    'linkup': 'Linkup',
    'azure': 'Azure AI Search',
}


def get_web_search_engine_label(engine: str | None) -> str:
    if not engine:
        return 'Web search'
    return WEB_SEARCH_ENGINE_LABELS.get(engine, engine.replace('_', ' ').title())


def _has_value(value: Any) -> bool:
    if value is None:
        return False
    if isinstance(value, str):
        return bool(value.strip())
    return bool(value)


def _missing_fields(config: Any, *fields: str) -> list[str]:
    return [field for field in fields if not _has_value(getattr(config, field, None))]


def is_web_search_configured(config: Any) -> tuple[bool, str | None]:
    engine = getattr(config, 'WEB_SEARCH_ENGINE', None) or ''
    if not engine:
        return False, 'No engine selected'

    checks: dict[str, tuple[str, ...]] = {
        'ollama_cloud': ('OLLAMA_CLOUD_WEB_SEARCH_API_KEY',),
        'perplexity_search': ('PERPLEXITY_API_KEY',),
        'searxng': ('SEARXNG_QUERY_URL',),
        'yacy': ('YACY_QUERY_URL',),
        'google_pse': ('GOOGLE_PSE_API_KEY', 'GOOGLE_PSE_ENGINE_ID'),
        'brave': ('BRAVE_SEARCH_API_KEY',),
        'brave_llm_context': ('BRAVE_SEARCH_API_KEY',),
        'kagi': ('KAGI_SEARCH_API_KEY',),
        'mojeek': ('MOJEEK_SEARCH_API_KEY',),
        'bocha': ('BOCHA_SEARCH_API_KEY',),
        'serpstack': ('SERPSTACK_API_KEY',),
        'serper': ('SERPER_API_KEY',),
        'serphouse': ('SERPHOUSE_API_KEY',),
        'serply': ('SERPLY_API_KEY',),
        'tavily': ('TAVILY_API_KEY',),
        'searchapi': ('SEARCHAPI_API_KEY',),
        'serpapi': ('SERPAPI_API_KEY',),
        'bing': ('BING_SEARCH_V7_SUBSCRIPTION_KEY', 'BING_SEARCH_V7_ENDPOINT'),
        'exa': ('EXA_API_KEY',),
        'microsoft_web_iq': ('MICROSOFT_WEB_IQ_API_KEY',),
        'sougou': ('SOUGOU_API_SID', 'SOUGOU_API_SK'),
        'external': ('EXTERNAL_WEB_SEARCH_URL',),
        'yandex': ('YANDEX_WEB_SEARCH_URL',),
        'youcom': ('YOUCOM_API_KEY',),
        'linkup': ('LINKUP_API_KEY',),
        'azure': ('AZURE_AI_SEARCH_API_KEY', 'AZURE_AI_SEARCH_ENDPOINT', 'AZURE_AI_SEARCH_INDEX_NAME'),
    }

    required = checks.get(engine)
    if required is None:
        return True, None

    missing = _missing_fields(config, *required)
    if missing:
        return False, f'Missing {", ".join(missing)}'

    return True, None


def _format_probe_host(url: str | None) -> str | None:
    if not url:
        return None
    try:
        parsed = urlparse(url)
        if parsed.netloc:
            return parsed.netloc
    except Exception:
        pass
    return url


async def probe_web_search_reachability(config: Any) -> tuple[bool, str | None]:
    engine = getattr(config, 'WEB_SEARCH_ENGINE', None) or ''

    if engine == 'searxng':
        query_url = getattr(config, 'SEARXNG_QUERY_URL', None)
        if not query_url:
            return False, 'No SearXNG query URL configured'

        if '<query>' in query_url:
            query_url = query_url.split('?')[0]

        params = {'q': 'open-webui-health', 'format': 'json', 'pageno': 1}
        headers = {
            'User-Agent': 'Open WebUI (https://github.com/open-webui/open-webui) Health Check',
            'Accept': 'application/json',
        }

        try:
            session = await get_session()
            async with session.get(
                query_url,
                headers=headers,
                params=params,
                timeout=5,
            ) as response:
                if response.status >= 400:
                    return False, f'SearXNG returned HTTP {response.status}'
                content_type = (response.headers.get('Content-Type') or '').lower()
                if 'json' not in content_type:
                    return False, 'SearXNG did not return JSON'
        except Exception as exc:
            log.debug('SearXNG health probe failed: %s', exc)
            return False, str(exc)

        return True, None

    if engine == 'yacy':
        query_url = getattr(config, 'YACY_QUERY_URL', None)
        if not query_url:
            return False, 'No YaCy query URL configured'

        try:
            session = await get_session()
            async with session.get(query_url, timeout=5) as response:
                if response.status >= 400:
                    return False, f'YaCy returned HTTP {response.status}'
        except Exception as exc:
            log.debug('YaCy health probe failed: %s', exc)
            return False, str(exc)

        return True, None

    if engine == 'external':
        search_url = getattr(config, 'EXTERNAL_WEB_SEARCH_URL', None)
        if not search_url:
            return False, 'No external search URL configured'

        try:
            session = await get_session()
            async with session.get(search_url, timeout=5) as response:
                if response.status >= 500:
                    return False, f'External search returned HTTP {response.status}'
        except Exception as exc:
            log.debug('External web search health probe failed: %s', exc)
            return False, str(exc)

        return True, None

    # API-key and keyless engines are considered reachable when configured.
    return True, None


async def get_web_search_status(config: Any) -> dict[str, Any]:
    enabled = bool(getattr(config, 'ENABLE_WEB_SEARCH', False))
    engine = getattr(config, 'WEB_SEARCH_ENGINE', None) or ''
    label = get_web_search_engine_label(engine)

    if not enabled:
        return {
            'status': True,
            'enabled': False,
            'engine': engine,
            'engine_label': label,
            'configured': False,
            'healthy': False,
            'detail': 'Disabled',
            'host': None,
            'error': None,
        }

    configured, config_error = is_web_search_configured(config)
    if not configured:
        return {
            'status': True,
            'enabled': True,
            'engine': engine,
            'engine_label': label,
            'configured': False,
            'healthy': False,
            'detail': config_error or 'Not configured',
            'host': None,
            'error': config_error,
        }

    host = None
    if engine == 'searxng':
        host = _format_probe_host(getattr(config, 'SEARXNG_QUERY_URL', None))
    elif engine == 'yacy':
        host = _format_probe_host(getattr(config, 'YACY_QUERY_URL', None))
    elif engine == 'external':
        host = _format_probe_host(getattr(config, 'EXTERNAL_WEB_SEARCH_URL', None))
    elif engine == 'bing':
        host = _format_probe_host(getattr(config, 'BING_SEARCH_V7_ENDPOINT', None))

    healthy, probe_error = await probe_web_search_reachability(config)

    return {
        'status': True,
        'enabled': True,
        'engine': engine,
        'engine_label': label,
        'configured': True,
        'healthy': healthy,
        'detail': label if healthy else 'Unreachable',
        'host': host,
        'error': probe_error,
    }
