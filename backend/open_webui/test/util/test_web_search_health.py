from open_webui.retrieval.web.health import get_web_search_engine_label, is_web_search_configured


class _Config:
    ENABLE_WEB_SEARCH = True
    WEB_SEARCH_ENGINE = 'duckduckgo'


class _SearxngConfig:
    ENABLE_WEB_SEARCH = True
    WEB_SEARCH_ENGINE = 'searxng'
    SEARXNG_QUERY_URL = ''


class _BraveConfig:
    ENABLE_WEB_SEARCH = True
    WEB_SEARCH_ENGINE = 'brave'
    BRAVE_SEARCH_API_KEY = ''


def test_web_search_engine_label():
    assert get_web_search_engine_label('duckduckgo') == 'DuckDuckGo'
    assert get_web_search_engine_label('searxng') == 'SearXNG'
    assert get_web_search_engine_label('') == 'Web search'


def test_is_web_search_configured_keyless_engine():
    configured, error = is_web_search_configured(_Config())
    assert configured is True
    assert error is None


def test_is_web_search_configured_missing_url():
    configured, error = is_web_search_configured(_SearxngConfig())
    assert configured is False
    assert error is not None


def test_is_web_search_configured_missing_api_key():
    configured, error = is_web_search_configured(_BraveConfig())
    assert configured is False
    assert 'BRAVE_SEARCH_API_KEY' in (error or '')
