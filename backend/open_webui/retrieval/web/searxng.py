from __future__ import annotations

import asyncio
import hashlib
import logging
import re
import time
from html import unescape
from urllib.parse import urlunparse, urlparse

from langchain_core.documents import Document
from open_webui.retrieval.web.main import SearchResult, get_filtered_results
from open_webui.utils.session_pool import get_session
from pydantic import BaseModel, Field

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

_HTML_TAG_RE = re.compile(r'<[^>]+>')
_GENERAL_TEMPLATES = frozenset({'default.html', '', None})
_IMAGE_TEMPLATES = frozenset({'images.html', 'image.html'})

_cache: dict[str, tuple[float, 'SearxngSearchResponse']] = {}
_cache_lock = asyncio.Lock()


class SearxngSearchOptions(BaseModel):
    language: str = 'all'
    safesearch: str = '1'
    time_range: str = ''
    categories: str = ''
    engines: str = ''
    auto_spelling_correction: bool = False
    fetch_page_2: bool = True
    min_score_ratio: float = 0.05
    min_absolute_score: float = 0.15
    max_results_per_domain: int = 2
    cache_ttl: int = 60


class SearxngAnswer(BaseModel):
    answer: str
    url: str | None = None
    engine: str | None = None


class SearxngInfobox(BaseModel):
    title: str | None = None
    content: str | None = None
    infobox_type: str | None = None
    img_src: str | None = None
    attributes: list[dict[str, str]] = Field(default_factory=list)
    urls: list[dict[str, str]] = Field(default_factory=list)
    related_topics: list[dict] = Field(default_factory=list)


class SearxngSearchResponse(BaseModel):
    query: str
    number_of_results: int | None = None
    results: list[SearchResult] = Field(default_factory=list)
    answers: list[SearxngAnswer] = Field(default_factory=list)
    infoboxes: list[SearxngInfobox] = Field(default_factory=list)
    suggestions: list[str] = Field(default_factory=list)
    corrections: list[str] = Field(default_factory=list)
    engine_failures: list[str] = Field(default_factory=list)
    corrected_query: str | None = None
    pages_fetched: int = 1

    def has_content(self) -> bool:
        return bool(self.results or self.answers or self.infoboxes)

    def build_overview(self) -> str | None:
        parts: list[str] = []

        for answer in self.answers:
            if answer.answer:
                line = answer.answer
                if answer.url:
                    line = f'{line} ({answer.url})'
                parts.append(line)

        for box in self.infoboxes:
            block: list[str] = []
            if box.title:
                block.append(box.title)
            if box.content:
                block.append(box.content)
            for attr in box.attributes:
                block.append(f"{attr['label']}: {attr['value']}")
            if block:
                parts.append('\n'.join(block))

        if not parts:
            for result in self.results[:2]:
                title = result.title or result.link
                snippet = (result.snippet or '')[:280].strip()
                if snippet:
                    parts.append(f'{title}: {snippet}')

        overview = '\n\n'.join(parts).strip()
        return overview or None

    def to_tool_payload(self, *, count: int | None = None) -> dict:
        """Serialize for the search_web tool — rich context without extra HTTP calls."""
        results = self.results[:count] if count else self.results
        payload: dict = {
            'query': self.query,
            'results': [result.model_dump(exclude_none=True) for result in results],
        }

        overview = self.build_overview()
        if overview:
            payload['overview'] = overview

        if self.number_of_results is not None:
            payload['number_of_results'] = self.number_of_results

        if self.corrected_query and self.corrected_query.lower() != self.query.lower():
            payload['corrected_query'] = self.corrected_query

        if self.answers:
            payload['direct_answers'] = [answer.model_dump(exclude_none=True) for answer in self.answers]

        if self.infoboxes:
            payload['infoboxes'] = [box.model_dump(exclude_none=True) for box in self.infoboxes]

        if self.suggestions:
            payload['related_queries'] = self.suggestions
            payload['related_queries_hint'] = (
                'Use related_queries for follow-up searches instead of inventing new query terms.'
            )

        if self.corrections:
            payload['spelling_corrections'] = self.corrections

        if self.engine_failures:
            payload['engine_failures'] = self.engine_failures

        if self.pages_fetched > 1:
            payload['pages_fetched'] = self.pages_fetched

        return payload


def searxng_options_from_config(config: object, overrides: dict | None = None) -> SearxngSearchOptions:
    """Build SearXNG options from admin config, with optional per-request overrides."""
    overrides = overrides or {}

    def _get(name: str, default):
        if name in overrides and overrides[name] is not None:
            return overrides[name]
        return getattr(config, name, default)

    categories = overrides.get('categories')
    if categories is None:
        categories = _get('SEARXNG_CATEGORIES', '')
    if isinstance(categories, list):
        categories = ''.join(categories)

    return SearxngSearchOptions(
        language=str(overrides.get('language') or _get('SEARXNG_LANGUAGE', 'all') or 'all'),
        safesearch=str(overrides.get('safesearch') or _get('SEARXNG_SAFESEARCH', '1') or '1'),
        time_range=str(overrides.get('time_range') or _get('SEARXNG_TIME_RANGE', '') or ''),
        categories=str(categories or ''),
        engines=str(overrides.get('engines') or _get('SEARXNG_ENGINES', '') or ''),
        auto_spelling_correction=bool(
            overrides.get('auto_spelling_correction', _get('SEARXNG_AUTO_SPELLING_CORRECTION', False))
        ),
        fetch_page_2=bool(overrides.get('fetch_page_2', _get('SEARXNG_FETCH_PAGE_2', True))),
        min_score_ratio=float(overrides.get('min_score_ratio', _get('SEARXNG_MIN_SCORE_RATIO', 0.05)) or 0.05),
        min_absolute_score=float(
            overrides.get('min_absolute_score', _get('SEARXNG_MIN_ABSOLUTE_SCORE', 0.15)) or 0.15
        ),
        max_results_per_domain=int(
            overrides.get('max_results_per_domain', _get('SEARXNG_MAX_RESULTS_PER_DOMAIN', 2)) or 2
        ),
        cache_ttl=int(overrides.get('cache_ttl', _get('WEB_SEARCH_CACHE_TTL', 60)) or 0),
    )


def searxng_response_to_documents(response: SearxngSearchResponse) -> list[Document]:
    """Convert a rich SearXNG response into RAG documents without fetching pages."""
    docs: list[Document] = []

    overview = response.build_overview()
    if overview:
        docs.append(
            Document(
                page_content=overview,
                metadata={
                    'source': 'searxng:overview',
                    'title': 'Search overview',
                    'type': 'overview',
                    'query': response.query,
                },
            )
        )

    for index, answer in enumerate(response.answers):
        docs.append(
            Document(
                page_content=answer.answer,
                metadata={
                    'source': answer.url or f'searxng:answer:{index}',
                    'title': 'Direct answer',
                    'type': 'direct_answer',
                    'url': answer.url,
                    'engine': answer.engine,
                    'query': response.query,
                },
            )
        )

    for index, box in enumerate(response.infoboxes):
        parts = []
        if box.title:
            parts.append(box.title)
        if box.content:
            parts.append(box.content)
        for attr in box.attributes:
            parts.append(f"{attr['label']}: {attr['value']}")
        link = box.urls[0]['url'] if box.urls else f'searxng:infobox:{index}'
        docs.append(
            Document(
                page_content='\n'.join(parts),
                metadata={
                    'source': link,
                    'title': box.title or 'Infobox',
                    'type': 'infobox',
                    'query': response.query,
                },
            )
        )

    for result in response.results:
        if not result.snippet:
            continue
        metadata = result.model_dump(exclude_none=True)
        metadata.update({'source': result.link, 'type': 'result', 'query': response.query})
        docs.append(Document(page_content=result.snippet, metadata=metadata))

    return docs


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


def _strip_html(text: str | None) -> str | None:
    if not text:
        return None
    cleaned = _HTML_TAG_RE.sub(' ', unescape(text))
    cleaned = re.sub(r'\s+', ' ', cleaned).strip()
    return cleaned or None


def _normalize_url(url: str) -> str:
    parsed = urlparse(url.strip())
    if not parsed.scheme or not parsed.netloc:
        return url.strip().lower()

    host = (parsed.hostname or '').lower()
    port = parsed.port
    netloc = f'{host}:{port}' if port and port not in (80, 443) else host
    path = parsed.path.rstrip('/') or '/'
    return urlunparse((parsed.scheme.lower(), netloc, path, '', '', ''))


def _result_domain(url: str) -> str:
    return (urlparse(url).hostname or '').lower()


def _first_non_empty(*values: object) -> str | None:
    for value in values:
        if value is None:
            continue
        text = str(value).strip()
        if text:
            return text
    return None


def _should_include_template(item: dict, categories: str) -> bool:
    template = item.get('template') or 'default.html'
    normalized_categories = (categories or '').lower()

    if 'images' in normalized_categories:
        return template in _IMAGE_TEMPLATES or template in _GENERAL_TEMPLATES
    if 'videos' in normalized_categories:
        return 'video' in str(template).lower() or template in _GENERAL_TEMPLATES
    if normalized_categories and normalized_categories not in ('general', ''):
        return True

    if template in _GENERAL_TEMPLATES:
        return True
    return 'default' in str(template).lower()


def _filter_by_score(
    results: list[SearchResult],
    min_ratio: float,
    min_absolute: float,
) -> list[SearchResult]:
    if not results:
        return results

    top_score = max((result.score or 0.0) for result in results)
    if top_score <= 0:
        return results

    threshold = max(top_score * min_ratio, min_absolute)
    return [result for result in results if (result.score or 0.0) >= threshold]


def _apply_domain_diversity(results: list[SearchResult], max_per_domain: int) -> list[SearchResult]:
    if max_per_domain <= 0:
        return results

    counts: dict[str, int] = {}
    diverse: list[SearchResult] = []
    for result in results:
        domain = _result_domain(result.link)
        if counts.get(domain, 0) >= max_per_domain:
            continue
        counts[domain] = counts.get(domain, 0) + 1
        diverse.append(result)
    return diverse


def _parse_answer(entry: object) -> SearxngAnswer | None:
    if isinstance(entry, str):
        answer = entry.strip()
        return SearxngAnswer(answer=answer) if answer else None

    if not isinstance(entry, dict):
        return None

    answer = _first_non_empty(entry.get('answer'), entry.get('content'), entry.get('text'))
    if not answer:
        return None

    return SearxngAnswer(
        answer=answer,
        url=_first_non_empty(entry.get('url'), entry.get('link')),
        engine=_first_non_empty(entry.get('engine')),
    )


def _parse_infobox(entry: dict) -> SearxngInfobox | None:
    title = _first_non_empty(entry.get('title'), entry.get('infobox'))
    content = _strip_html(_first_non_empty(entry.get('content'), entry.get('description')))

    attributes: list[dict[str, str]] = []
    for attr in entry.get('attributes') or []:
        if not isinstance(attr, dict):
            continue
        label = _first_non_empty(attr.get('label'), attr.get('name'))
        value = _first_non_empty(attr.get('value'), attr.get('text'))
        if label and value:
            attributes.append({'label': label, 'value': value})

    urls: list[dict[str, str]] = []
    for link in entry.get('urls') or []:
        if not isinstance(link, dict):
            continue
        url = _first_non_empty(link.get('url'), link.get('href'))
        if not url:
            continue
        urls.append(
            {
                'title': _first_non_empty(link.get('title'), link.get('name'), url) or url,
                'url': url,
            }
        )

    related_topics: list[dict] = []
    for topic in entry.get('relatedTopics') or entry.get('related_topics') or []:
        if isinstance(topic, dict) and topic:
            related_topics.append(topic)

    if not any([title, content, attributes, urls, related_topics]):
        return None

    return SearxngInfobox(
        title=title,
        content=content,
        infobox_type=_first_non_empty(entry.get('infobox'), entry.get('template')),
        img_src=_first_non_empty(entry.get('img_src'), entry.get('thumbnail')),
        attributes=attributes,
        urls=urls,
        related_topics=related_topics,
    )


def _parse_result_item(item: dict) -> SearchResult | None:
    link = _first_non_empty(item.get('url'), item.get('link'), item.get('href'))
    if not link:
        return None

    snippet_parts: list[str] = []
    metadata = _first_non_empty(item.get('metadata'))
    content = _strip_html(_first_non_empty(item.get('content'), item.get('snippet')))
    if metadata:
        snippet_parts.append(metadata)
    if content:
        snippet_parts.append(content)

    engines_raw = item.get('engines')
    if isinstance(engines_raw, list):
        engines = [str(engine).strip() for engine in engines_raw if str(engine).strip()]
    else:
        single_engine = _first_non_empty(item.get('engine'))
        engines = [single_engine] if single_engine else None

    published = _first_non_empty(item.get('publishedDate'), item.get('pubdate'))
    author = _first_non_empty(item.get('author'))
    score = item.get('score')
    parsed_score = float(score) if isinstance(score, (int, float)) else None

    return SearchResult(
        link=link,
        title=_first_non_empty(item.get('title')),
        snippet='\n'.join(snippet_parts) if snippet_parts else None,
        published=published,
        engines=engines or None,
        score=parsed_score,
        author=author,
        category=_first_non_empty(item.get('category')),
        thumbnail=_first_non_empty(item.get('thumbnail'), item.get('img_src')),
    )


def _dedupe_results(results: list[SearchResult]) -> list[SearchResult]:
    deduped: dict[str, SearchResult] = {}
    for result in results:
        key = _normalize_url(result.link)
        existing = deduped.get(key)
        if existing is None:
            deduped[key] = result
            continue

        existing_score = existing.score if existing.score is not None else -1.0
        new_score = result.score if result.score is not None else -1.0
        if new_score > existing_score:
            deduped[key] = result
            continue

        if new_score == existing_score and len(result.snippet or '') > len(existing.snippet or ''):
            deduped[key] = result

    ordered = sorted(
        deduped.values(),
        key=lambda result: result.score if result.score is not None else 0.0,
        reverse=True,
    )
    return ordered


def _parse_searxng_payload(
    payload: dict,
    query: str,
    count: int,
    options: SearxngSearchOptions,
) -> SearxngSearchResponse:
    raw_results = payload.get('results') or []
    filtered_raw = [item for item in raw_results if _should_include_template(item, options.categories)]
    parsed_results = [parsed for item in filtered_raw if (parsed := _parse_result_item(item)) is not None]
    parsed_results.sort(key=lambda result: result.score if result.score is not None else 0.0, reverse=True)
    parsed_results = _dedupe_results(parsed_results)
    parsed_results = _filter_by_score(
        parsed_results,
        options.min_score_ratio,
        options.min_absolute_score,
    )
    parsed_results = _apply_domain_diversity(parsed_results, options.max_results_per_domain)

    answers: list[SearxngAnswer] = []
    for entry in payload.get('answers') or []:
        if answer := _parse_answer(entry):
            answers.append(answer)

    infoboxes: list[SearxngInfobox] = []
    for entry in payload.get('infoboxes') or []:
        if isinstance(entry, dict) and (box := _parse_infobox(entry)):
            infoboxes.append(box)

    suggestions = [
        suggestion.strip()
        for suggestion in (payload.get('suggestions') or [])
        if isinstance(suggestion, str) and suggestion.strip()
    ]
    corrections = [
        correction.strip()
        for correction in (payload.get('corrections') or [])
        if isinstance(correction, str) and correction.strip()
    ]

    number_of_results = payload.get('number_of_results')
    parsed_count = int(number_of_results) if isinstance(number_of_results, int) else None

    return SearxngSearchResponse(
        query=str(payload.get('query') or query),
        number_of_results=parsed_count,
        results=parsed_results[:count],
        answers=answers,
        infoboxes=infoboxes,
        suggestions=suggestions,
        corrections=corrections,
        engine_failures=_engine_failures(payload),
    )


def _merge_responses(
    primary: SearxngSearchResponse,
    secondary: SearxngSearchResponse,
    count: int,
    *,
    max_results_per_domain: int,
) -> SearxngSearchResponse:
    seen_answers = {answer.answer for answer in primary.answers}
    for answer in secondary.answers:
        if answer.answer not in seen_answers:
            primary.answers.append(answer)
            seen_answers.add(answer.answer)

    seen_boxes = {(box.title, box.content) for box in primary.infoboxes}
    for box in secondary.infoboxes:
        key = (box.title, box.content)
        if key not in seen_boxes:
            primary.infoboxes.append(box)
            seen_boxes.add(key)

    merged_results = _dedupe_results(primary.results + secondary.results)
    merged_results = _apply_domain_diversity(merged_results, max_results_per_domain)
    primary.results = merged_results[:count]

    for suggestion in secondary.suggestions:
        if suggestion not in primary.suggestions:
            primary.suggestions.append(suggestion)

    for failure in secondary.engine_failures:
        if failure not in primary.engine_failures:
            primary.engine_failures.append(failure)

    primary.pages_fetched = primary.pages_fetched + secondary.pages_fetched
    if secondary.number_of_results and not primary.number_of_results:
        primary.number_of_results = secondary.number_of_results
    return primary


def _is_weak_response(response: SearxngSearchResponse, count: int) -> bool:
    if response.answers or response.infoboxes:
        return False
    if len(response.results) < max(1, count // 2):
        return True
    if not response.results:
        return True
    top_score = response.results[0].score or 0.0
    return top_score < 0.5


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
        return


def _build_request_params(query: str, options: SearxngSearchOptions, *, pageno: int = 1) -> dict:
    params = {
        'q': query,
        'format': 'json',
        'pageno': pageno,
        'safesearch': options.safesearch,
        'language': options.language.strip().rstrip(','),
        'time_range': options.time_range,
        'categories': options.categories,
        'theme': 'simple',
        'image_proxy': 0,
    }
    if options.engines:
        params['engines'] = options.engines
    return params


def _cache_key(query_url: str, query: str, options: SearxngSearchOptions, cache_scope: str | None) -> str:
    material = '|'.join(
        [
            query_url,
            query,
            options.language,
            options.safesearch,
            options.time_range,
            options.categories,
            options.engines,
            cache_scope or '',
        ]
    )
    return hashlib.sha256(material.encode()).hexdigest()


async def _cache_get(key: str, ttl: int) -> SearxngSearchResponse | None:
    if ttl <= 0:
        return None
    async with _cache_lock:
        entry = _cache.get(key)
        if not entry:
            return None
        expires_at, response = entry
        if time.monotonic() > expires_at:
            _cache.pop(key, None)
            return None
        return response.model_copy(deep=True)


async def _cache_set(key: str, ttl: int, response: SearxngSearchResponse) -> None:
    if ttl <= 0:
        return
    async with _cache_lock:
        _cache[key] = (time.monotonic() + ttl, response.model_copy(deep=True))


async def _fetch_searxng_payload(query_url: str, query: str, options: SearxngSearchOptions, *, pageno: int = 1) -> dict:
    if '<query>' in query_url:
        query_url = query_url.split('?')[0]

    params = _build_request_params(query, options, pageno=pageno)
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
    if payload.get('results') is None:
        raise RuntimeError(
            'SearXNG response is missing a results field. '
            'Check the Query URL points to the /search endpoint.'
        )
    return payload


async def search_searxng(
    query_url: str,
    query: str,
    count: int,
    filter_list: list[str | None] | None = None,
    *,
    options: SearxngSearchOptions | None = None,
    cache_scope: str | None = None,
    **kwargs,
) -> SearxngSearchResponse:
    """Query a SearXNG instance and return rich structured results."""
    resolved = options or SearxngSearchOptions(
        language=str(kwargs.get('language', 'all')),
        safesearch=str(kwargs.get('safesearch', '1')),
        time_range=str(kwargs.get('time_range', '')),
        categories=(
            kwargs.get('categories', '')
            if isinstance(kwargs.get('categories'), str)
            else ''.join(kwargs.get('categories', []))
        ),
        engines=str(kwargs.get('engines', '')),
        auto_spelling_correction=bool(kwargs.get('auto_spelling_correction', False)),
        fetch_page_2=bool(kwargs.get('fetch_page_2', True)),
        min_score_ratio=float(kwargs.get('min_score_ratio', 0.05)),
        min_absolute_score=float(kwargs.get('min_absolute_score', 0.15)),
        max_results_per_domain=int(kwargs.get('max_results_per_domain', 2)),
        cache_ttl=int(kwargs.get('cache_ttl', 60)),
    )

    cache_key = _cache_key(query_url, query, resolved, cache_scope)
    cached = await _cache_get(cache_key, resolved.cache_ttl)
    if cached is not None:
        cached.results = cached.results[:count]
        return cached

    log.debug('searching %s', query_url)

    payload = await _fetch_searxng_payload(query_url, query, resolved, pageno=1)
    raw_count = len(payload.get('results') or [])
    if filter_list:
        payload = {**payload, 'results': get_filtered_results(payload.get('results') or [], filter_list)}

    response_data = _parse_searxng_payload(payload, query, count, resolved)
    if not response_data.has_content():
        _raise_if_searxng_unusable(payload, query, filtered_all=raw_count > 0 and not payload.get('results'))

    if resolved.auto_spelling_correction and _is_weak_response(response_data, count):
        correction = next(
            (item for item in response_data.corrections if item.lower() != query.lower()),
            None,
        )
        if correction:
            corrected_payload = await _fetch_searxng_payload(query_url, correction, resolved, pageno=1)
            if filter_list:
                corrected_payload = {
                    **corrected_payload,
                    'results': get_filtered_results(corrected_payload.get('results') or [], filter_list),
                }
            corrected_response = _parse_searxng_payload(corrected_payload, correction, count, resolved)
            if corrected_response.has_content() and (
                not response_data.has_content() or len(corrected_response.results) > len(response_data.results)
            ):
                response_data = corrected_response
                response_data.corrected_query = correction

    if resolved.fetch_page_2 and _is_weak_response(response_data, count):
        page2_payload = await _fetch_searxng_payload(query_url, response_data.query, resolved, pageno=2)
        if filter_list:
            page2_payload = {
                **page2_payload,
                'results': get_filtered_results(page2_payload.get('results') or [], filter_list),
            }
        page2_response = _parse_searxng_payload(page2_payload, response_data.query, count, resolved)
        page2_response.pages_fetched = 1
        if page2_response.has_content():
            response_data = _merge_responses(
                response_data,
                page2_response,
                count,
                max_results_per_domain=resolved.max_results_per_domain,
            )

    await _cache_set(cache_key, resolved.cache_ttl, response_data)
    return response_data
