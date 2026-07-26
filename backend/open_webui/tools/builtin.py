"""
Built-in tools for Open WebUI.

These tools are automatically available when native function calling is enabled.

IMPORTANT: DO NOT IMPORT THIS MODULE DIRECTLY IN OTHER PARTS OF THE CODEBASE.
"""

from open_webui.tools.knowledge_fs import kb_exec  # noqa: F401 — re-exported

import asyncio
import json
import logging
import re
import time
from typing import Optional

from fastapi import Request

from open_webui.models.channels import Channel, ChannelMember, Channels
from open_webui.models.chats import Chats
from open_webui.models.config import Config
from open_webui.models.groups import Groups
from open_webui.models.memories import Memories
from open_webui.models.messages import Message, Messages
from open_webui.models.notes import Notes
from open_webui.models.users import UserModel
from open_webui.retrieval.utils import get_content_from_url
from open_webui.retrieval.vector.async_client import ASYNC_VECTOR_DB_CLIENT
from open_webui.routers.images import (
    CreateImageForm,
    EditImageForm,
    image_edits,
    image_generations,
)
from open_webui.routers.memories import (
    AddMemoryForm,
    ListMemoryPathsForm,
    MemoryUpdateModel,
    ReadMemoryPathForm,
    SearchMemoriesForm,
    UpdateMemoriesForm,
    list_memory_paths as _list_memory_paths,
    read_memory_path as _read_memory_path,
    search_memories as _search_memories,
    update_memories as _update_memories,
    update_memory_by_id,
)
from open_webui.routers.memories import (
    add_memory as _add_memory,
    delete_memory_by_id as _delete_memory_by_id,
)
from open_webui.routers.retrieval import search_web as _search_web
from open_webui.utils.sanitize import sanitize_code

log = logging.getLogger(__name__)

MAX_KNOWLEDGE_BASE_SEARCH_ITEMS = 10_000


async def _has_read_access_to_file(
    file,
    user_id: str,
    user_role: str,
    model_knowledge: Optional[list[dict]] = None,
) -> bool:
    """Check if a user can read a file via ownership, admin role, model attachment, or access grants."""
    if file.user_id == user_id or user_role == 'admin':
        return True
    if model_knowledge and any(item.get('type') == 'file' and item.get('id') == file.id for item in model_knowledge):
        return True
    from open_webui.utils.access_control.files import has_access_to_file

    return await has_access_to_file(
        file_id=file.id,
        access_type='read',
        user=UserModel(**{'id': user_id, 'role': user_role}),
    )


# =============================================================================
# TIME UTILITIES
# =============================================================================


async def get_current_timestamp(
    __request__: Request = None,
    __user__: dict = None,
) -> str:
    """
    Get the current Unix timestamp in seconds.

    :return: JSON with current_timestamp (seconds), current_iso (UTC ISO format), and user_local_iso (user's local time)
    """
    try:
        import datetime
        from zoneinfo import ZoneInfo

        now = datetime.datetime.now(datetime.timezone.utc)
        result = {
            'current_timestamp': int(now.timestamp()),
            'current_iso': now.isoformat(),
        }

        # Include the user's local time if timezone is available
        tz_name = __user__.get('timezone') if __user__ else None
        if tz_name:
            try:
                user_tz = ZoneInfo(tz_name)
                user_now = now.astimezone(user_tz)
                result['user_local_iso'] = user_now.isoformat()
                result['user_timezone'] = tz_name
            except Exception:
                pass

        return json.dumps(result, ensure_ascii=False)
    except Exception as e:
        log.exception(f'get_current_timestamp error: {e}')
        return json.dumps({'error': str(e)})


async def calculate_timestamp(
    days_ago: int = 0,
    weeks_ago: int = 0,
    months_ago: int = 0,
    years_ago: int = 0,
    __request__: Request = None,
    __user__: dict = None,
) -> str:
    """
    Get the current Unix timestamp, optionally adjusted by days, weeks, months, or years.
    Use this to calculate timestamps for date filtering in search functions.
    Examples: "last week" = weeks_ago=1, "3 days ago" = days_ago=3, "a year ago" = years_ago=1

    :param days_ago: Number of days to subtract from current time (default: 0)
    :param weeks_ago: Number of weeks to subtract from current time (default: 0)
    :param months_ago: Number of months to subtract from current time (default: 0)
    :param years_ago: Number of years to subtract from current time (default: 0)
    :return: JSON with current_timestamp and calculated_timestamp (both in seconds)
    """
    try:
        import datetime

        from dateutil.relativedelta import relativedelta

        now = datetime.datetime.now(datetime.timezone.utc)
        current_ts = int(now.timestamp())

        # Calculate the adjusted time
        total_days = days_ago + (weeks_ago * 7)
        adjusted = now - datetime.timedelta(days=total_days)

        # Handle months and years separately (variable length)
        if months_ago > 0 or years_ago > 0:
            adjusted = adjusted - relativedelta(months=months_ago, years=years_ago)

        adjusted_ts = int(adjusted.timestamp())

        result = {
            'current_timestamp': current_ts,
            'current_iso': now.isoformat(),
            'calculated_timestamp': adjusted_ts,
            'calculated_iso': adjusted.isoformat(),
        }

        # Include the user's local time if timezone is available
        tz_name = __user__.get('timezone') if __user__ else None
        if tz_name:
            try:
                from zoneinfo import ZoneInfo

                user_tz = ZoneInfo(tz_name)
                result['user_local_iso'] = now.astimezone(user_tz).isoformat()
                result['calculated_local_iso'] = adjusted.astimezone(user_tz).isoformat()
                result['user_timezone'] = tz_name
            except Exception:
                pass

        return json.dumps(result, ensure_ascii=False)
    except ImportError:
        # Fallback without dateutil
        import datetime

        now = datetime.datetime.now(datetime.timezone.utc)
        current_ts = int(now.timestamp())
        total_days = days_ago + (weeks_ago * 7) + (months_ago * 30) + (years_ago * 365)
        adjusted = now - datetime.timedelta(days=total_days)
        adjusted_ts = int(adjusted.timestamp())
        result = {
            'current_timestamp': current_ts,
            'current_iso': now.isoformat(),
            'calculated_timestamp': adjusted_ts,
            'calculated_iso': adjusted.isoformat(),
        }

        tz_name = __user__.get('timezone') if __user__ else None
        if tz_name:
            try:
                from zoneinfo import ZoneInfo

                user_tz = ZoneInfo(tz_name)
                result['user_local_iso'] = now.astimezone(user_tz).isoformat()
                result['calculated_local_iso'] = adjusted.astimezone(user_tz).isoformat()
                result['user_timezone'] = tz_name
            except Exception:
                pass

        return json.dumps(result, ensure_ascii=False)
    except Exception as e:
        log.exception(f'calculate_timestamp error: {e}')
        return json.dumps({'error': str(e)})


# =============================================================================
# WEB SEARCH TOOLS
# =============================================================================

_FETCH_URL_MAX_BATCH = 5
_VIEW_CHAT_DEFAULT_MAX_MESSAGES = 50
_NOTE_EXCERPT_MAX_CHARS = 280
_MEMORY_EXCERPT_MAX_CHARS = 280
_DEFAULT_AUTO_QUERY_KB_COUNT = 5

_EXCHANGE_RATE_CACHE: dict[str, tuple[float, dict]] = {}
_EXCHANGE_RATE_CACHE_TTL = 3600
_exchange_rate_lock = asyncio.Lock()

_RELATIVE_DATE_OFFSETS = {
    'last_7_days': 7 * 86400,
    'last_week': 7 * 86400,
    'last_30_days': 30 * 86400,
    'last_month': 30 * 86400,
}


def _resolve_chat_timestamp(value: int | str | None) -> int | None:
    if value is None:
        return None
    if isinstance(value, int):
        return value
    if isinstance(value, float):
        return int(value)
    text = str(value).strip().lower()
    if not text:
        return None
    if text.isdigit():
        return int(text)
    offset = _RELATIVE_DATE_OFFSETS.get(text)
    if offset is not None:
        return int(time.time()) - offset
    return None


def _knowledge_chunk_relevance(chunk: dict) -> float | None:
    score = chunk.get('relevance')
    if isinstance(score, (int, float)):
        return float(score)
    distance = chunk.get('distance')
    if isinstance(distance, (int, float)):
        return float(distance)
    return None


def _filter_knowledge_chunks_by_threshold(chunks: list[dict], threshold: float) -> list[dict]:
    if threshold <= 0:
        return chunks

    filtered: list[dict] = []
    for chunk in chunks:
        if chunk.get('type') in {'note', 'external'}:
            filtered.append(chunk)
            continue
        relevance = _knowledge_chunk_relevance(chunk)
        if relevance is None or relevance >= threshold:
            filtered.append(chunk)
    return filtered


def _group_knowledge_chunks(chunks: list[dict]) -> list[dict]:
    grouped: dict[str, dict] = {}
    for chunk in chunks:
        file_id = chunk.get('file_id') or ''
        note_id = chunk.get('note_id') or ''
        source = chunk.get('source', 'Unknown')
        key = file_id or note_id or source
        entry = grouped.setdefault(
            key,
            {
                'source': source,
                'file_id': file_id or None,
                'note_id': note_id or None,
                'knowledge_id': chunk.get('knowledge_id'),
                'type': chunk.get('type', 'file'),
                'chunks': [],
            },
        )
        chunk_payload = {'content': chunk.get('content', '')}
        relevance = _knowledge_chunk_relevance(chunk)
        if relevance is not None:
            chunk_payload['relevance'] = relevance
        if chunk.get('truncated'):
            chunk_payload['truncated'] = True
        if chunk.get('read_more'):
            chunk_payload['read_more'] = chunk['read_more']
        entry['chunks'].append(chunk_payload)

    return list(grouped.values())


def _build_text_excerpt(content: str, query: str = '', max_chars: int = 280) -> tuple[str, bool]:
    text = (content or '').strip()
    if not text:
        return '', False
    if len(text) <= max_chars:
        return text, False

    lowered_query = (query or '').strip().lower()
    if lowered_query:
        idx = text.lower().find(lowered_query)
        if idx >= 0:
            start = max(0, idx - 80)
            end = min(len(text), start + max_chars)
            excerpt = ('...' if start > 0 else '') + text[start:end]
            if end < len(text):
                excerpt += '...'
            return excerpt, True

    return text[:max_chars] + '...', True


def _build_note_chunk(note, query: str = '') -> dict:
    full_content = note.data.get('content', {}).get('md', '')
    excerpt, truncated = _build_text_excerpt(full_content, query=query, max_chars=_NOTE_EXCERPT_MAX_CHARS)
    chunk = {
        'content': excerpt,
        'source': note.title,
        'note_id': note.id,
        'type': 'note',
    }
    if truncated:
        chunk['truncated'] = True
        chunk['read_more'] = 'Use view_note or view_note_lines with note_id for the full note.'
    return chunk


def _build_knowledge_overview(query: str, chunks: list[dict], limit: int = 3) -> str | None:
    parts: list[str] = []
    for chunk in chunks[:limit]:
        source = chunk.get('source', 'Unknown')
        content = (chunk.get('content') or '').strip()
        if not content:
            continue
        excerpt = content[:240] + ('...' if len(content) > 240 else '')
        parts.append(f'{source}: {excerpt}')
    overview = '\n\n'.join(parts).strip()
    return overview or None


def _build_knowledge_query_payload(
    query: str,
    chunks: list[dict],
    *,
    matched_knowledge_bases: list[dict] | None = None,
) -> dict:
    sources = _group_knowledge_chunks(chunks)
    payload = {
        'query': query,
        'sources': sources,
        'total_chunks': sum(len(source.get('chunks') or []) for source in sources),
    }
    overview = _build_knowledge_overview(query, chunks)
    if overview:
        payload['overview'] = overview
    if matched_knowledge_bases:
        payload['matched_knowledge_bases'] = matched_knowledge_bases
    return payload


async def _discover_knowledge_bases_by_query(
    request: Request,
    user_id: str,
    user_group_ids: list[str],
    query: str,
    count: int = _DEFAULT_AUTO_QUERY_KB_COUNT,
) -> list[dict]:
    import heapq

    from open_webui.models.knowledge import Knowledges
    from open_webui.retrieval.vector.async_client import ASYNC_VECTOR_DB_CLIENT
    from open_webui.routers.knowledge import KNOWLEDGE_BASES_COLLECTION

    embedding_function = request.app.state.EMBEDDING_FUNCTION
    if not embedding_function:
        return []

    query_embedding = await embedding_function(query)
    top_results_heap: list[tuple[float, str]] = []
    seen_ids: set[str] = set()
    page_offset = 0
    page_size = 100

    while True:
        accessible_knowledge_bases = await Knowledges.search_knowledge_bases(
            user_id,
            filter={'user_id': user_id, 'group_ids': user_group_ids},
            skip=page_offset,
            limit=page_size,
        )

        if not accessible_knowledge_bases.items:
            break

        accessible_ids = [kb.id for kb in accessible_knowledge_bases.items]
        search_results = await ASYNC_VECTOR_DB_CLIENT.search(
            collection_name=KNOWLEDGE_BASES_COLLECTION,
            vectors=[query_embedding],
            filter={'knowledge_base_id': {'$in': accessible_ids}},
            limit=count,
        )

        if search_results and search_results.ids and search_results.ids[0]:
            result_ids = search_results.ids[0]
            result_distances = search_results.distances[0] if search_results.distances else [0] * len(result_ids)

            for knowledge_base_id, distance in zip(result_ids, result_distances):
                if knowledge_base_id in seen_ids:
                    continue
                seen_ids.add(knowledge_base_id)

                if len(top_results_heap) < count:
                    heapq.heappush(top_results_heap, (distance, knowledge_base_id))
                elif distance > top_results_heap[0][0]:
                    heapq.heapreplace(top_results_heap, (distance, knowledge_base_id))

        page_offset += page_size
        if len(accessible_knowledge_bases.items) < page_size:
            break
        if page_offset >= MAX_KNOWLEDGE_BASE_SEARCH_ITEMS:
            break

    sorted_results = sorted(top_results_heap, key=lambda item: item[0], reverse=True)
    matched: list[dict] = []
    for distance, knowledge_base_id in sorted_results:
        knowledge_base = await Knowledges.get_knowledge_by_id(knowledge_base_id)
        if knowledge_base:
            matched.append(
                {
                    'id': knowledge_base.id,
                    'name': knowledge_base.name,
                    'description': knowledge_base.description or '',
                    'similarity': round(distance, 4),
                }
            )
    return matched


async def _fetch_url_entry(request: Request, url: str, max_length: int | None) -> dict:
    try:
        content, docs = await get_content_from_url(request, url)
        if content is None:
            content = ''

        truncated = False
        if max_length and max_length > 0 and len(content) > max_length:
            content = content[:max_length] + '\n\n[Content truncated...]'
            truncated = True

        metadata = docs[0].metadata if docs else {}
        title = metadata.get('title') or metadata.get('name') or url
        description = metadata.get('description')
        word_count = len(content.split()) if content else 0

        return {
            'url': url,
            'title': title,
            'description': description,
            'content': content,
            'truncated': truncated,
            'word_count': word_count,
        }
    except Exception as e:
        log.warning(f'fetch_url entry error for {url}: {e}')
        return {'url': url, 'error': str(e)}


def _dedupe_image_results(images: list[dict]) -> list[dict]:
    seen: set[str] = set()
    deduped: list[dict] = []
    for image in images:
        key = image.get('image_url') or image.get('thumbnail_url') or ''
        if not key or key in seen:
            continue
        seen.add(key)
        deduped.append(image)
    return deduped


async def _searxng_image_results(query: str, count: int, cache_scope: str | None = None) -> list[dict]:
    from types import SimpleNamespace

    from open_webui.retrieval.web.searxng import search_searxng, searxng_options_from_config

    query_url = await Config.get('web.search.searxng_query_url')
    if not query_url:
        return []

    filter_list = await Config.get('web.search.domain_filter_list')
    searxng_config = SimpleNamespace(
        SEARXNG_LANGUAGE=await Config.get('web.search.searxng_language'),
        SEARXNG_TIME_RANGE=await Config.get('web.search.searxng_time_range'),
        SEARXNG_CATEGORIES='images',
        SEARXNG_SAFESEARCH=await Config.get('web.search.searxng_safesearch'),
        SEARXNG_ENGINES=await Config.get('web.search.searxng_engines'),
        SEARXNG_AUTO_SPELLING_CORRECTION=await Config.get('web.search.searxng_auto_spelling_correction'),
        SEARXNG_FETCH_PAGE_2=await Config.get('web.search.searxng_fetch_page_2'),
        SEARXNG_MIN_SCORE_RATIO=await Config.get('web.search.searxng_min_score_ratio'),
        SEARXNG_MIN_ABSOLUTE_SCORE=await Config.get('web.search.searxng_min_absolute_score'),
        SEARXNG_MAX_RESULTS_PER_DOMAIN=await Config.get('web.search.searxng_max_results_per_domain'),
        WEB_SEARCH_CACHE_TTL=await Config.get('web.search.cache_ttl'),
    )
    options = searxng_options_from_config(searxng_config)
    response = await search_searxng(
        query_url,
        query,
        count,
        filter_list,
        options=options,
        cache_scope=cache_scope,
    )

    images: list[dict] = []
    for result in response.results:
        image_url = result.thumbnail or result.link
        if not image_url:
            continue
        images.append(
            {
                'title': result.title,
                'image_url': image_url,
                'thumbnail_url': result.thumbnail,
                'source_url': result.link,
                'snippet': result.snippet,
                'engine': 'searxng',
            }
        )
    return images


async def _brave_image_results(query: str, count: int) -> list[dict]:
    from open_webui.utils.session_pool import get_session

    api_key = await Config.get('web.search.brave_search_api_key')
    if not api_key:
        return []

    session = await get_session()
    async with session.get(
        'https://api.search.brave.com/res/v1/images/search',
        headers={
            'Accept': 'application/json',
            'Accept-Encoding': 'gzip',
            'X-Subscription-Token': api_key,
        },
        params={'q': query, 'count': count},
    ) as response:
        response.raise_for_status()
        payload = await response.json()

    images: list[dict] = []
    for item in (payload.get('results') or [])[:count]:
        thumbnail = (item.get('thumbnail') or {}).get('src')
        image_url = thumbnail or item.get('url')
        if not image_url:
            continue
        properties = item.get('properties') or {}
        images.append(
            {
                'title': item.get('title'),
                'image_url': image_url,
                'thumbnail_url': thumbnail,
                'source_url': properties.get('url') or item.get('url'),
                'source_name': item.get('source'),
                'engine': 'brave',
            }
        )
    return images


def _build_weather_forecast(forecast: dict) -> dict:
    daily = forecast.get('daily') or {}
    hourly = forecast.get('hourly') or {}
    daily_units = forecast.get('daily_units') or {}
    hourly_units = forecast.get('hourly_units') or {}

    daily_rows = []
    dates = daily.get('time') or []
    for idx, day in enumerate(dates[:7]):
        code = (daily.get('weather_code') or [None])[idx] if daily.get('weather_code') else None
        daily_rows.append(
            {
                'date': day,
                'weather_code': code,
                'description': _wmo_description(code),
                'temperature_max': (daily.get('temperature_2m_max') or [None])[idx],
                'temperature_min': (daily.get('temperature_2m_min') or [None])[idx],
                'precipitation_probability_max': (daily.get('precipitation_probability_max') or [None])[idx],
                'temperature_unit': daily_units.get('temperature_2m_max', '°C'),
            }
        )

    hourly_rows = []
    times = hourly.get('time') or []
    for idx, moment in enumerate(times[:24]):
        code = (hourly.get('weather_code') or [None])[idx] if hourly.get('weather_code') else None
        hourly_rows.append(
            {
                'time': moment,
                'weather_code': code,
                'description': _wmo_description(code),
                'temperature': (hourly.get('temperature_2m') or [None])[idx],
                'precipitation_probability': (hourly.get('precipitation_probability') or [None])[idx],
                'temperature_unit': hourly_units.get('temperature_2m', '°C'),
            }
        )

    return {'daily': daily_rows, 'hourly': hourly_rows}


async def search_web(
    query: str,
    count: Optional[int] = None,
    time_range: Optional[str] = None,
    category: Optional[str] = None,
    __request__: Request = None,
    __user__: dict = None,
    __chat_id__: str = None,
) -> str:
    """
    Search the public web for information. Best for current events, external references,
    or topics not covered in internal documents.

    Results include title, link, and snippet for each hit — snippets are often enough without
    calling fetch_url. Prefer one broad search and only fetch_url when snippets are insufficient
    (fetch_url defaults to depth=snippet and reuses cached search snippets).

    With SearXNG, also returns overview, direct answers, infoboxes, and related_queries when
    available. Use related_queries for follow-ups instead of inventing new terms.

    :param query: The search query to look up
    :param count: Number of results to return (default: admin-configured value)
    :param time_range: Optional recency filter for SearXNG: day, week, month, or year
    :param category: Optional SearXNG category: general, news, science, it, images, etc.
    :return: JSON search payload (rich structured object for SearXNG, result list for other engines)
    """
    if __request__ is None:
        return json.dumps({'error': 'Request context not available'})

    try:
        engine = await Config.get('web.search.engine')
        if not engine:
            return json.dumps(
                {
                    'error': (
                        'Web search engine is not configured on this server '
                        '(Admin → Settings → Web Search). Do not invent web-sourced facts.'
                    )
                }
            )

        user = UserModel(**__user__) if __user__ else None

        configured = await Config.get('web.search.result_count')
        max_count = 5 if configured is None else configured
        count = max(1, min(count, max_count)) if count is not None else max_count

        if engine == 'searxng':
            from types import SimpleNamespace

            from open_webui.retrieval.web.searxng import search_searxng, searxng_options_from_config

            query_url = await Config.get('web.search.searxng_query_url')
            if not query_url:
                return json.dumps({'error': 'SearXNG Query URL is not configured (Admin → Settings → Web Search).'})

            filter_list = await Config.get('web.search.domain_filter_list')
            searxng_config = SimpleNamespace(
                SEARXNG_LANGUAGE=await Config.get('web.search.searxng_language'),
                SEARXNG_TIME_RANGE=await Config.get('web.search.searxng_time_range'),
                SEARXNG_CATEGORIES=await Config.get('web.search.searxng_categories'),
                SEARXNG_SAFESEARCH=await Config.get('web.search.searxng_safesearch'),
                SEARXNG_ENGINES=await Config.get('web.search.searxng_engines'),
                SEARXNG_AUTO_SPELLING_CORRECTION=await Config.get('web.search.searxng_auto_spelling_correction'),
                SEARXNG_FETCH_PAGE_2=await Config.get('web.search.searxng_fetch_page_2'),
                SEARXNG_MIN_SCORE_RATIO=await Config.get('web.search.searxng_min_score_ratio'),
                SEARXNG_MIN_ABSOLUTE_SCORE=await Config.get('web.search.searxng_min_absolute_score'),
                SEARXNG_MAX_RESULTS_PER_DOMAIN=await Config.get('web.search.searxng_max_results_per_domain'),
                WEB_SEARCH_CACHE_TTL=await Config.get('web.search.cache_ttl'),
            )
            overrides = {}
            if time_range:
                overrides['time_range'] = time_range
            if category:
                overrides['categories'] = category
            options = searxng_options_from_config(searxng_config, overrides)
            response = await search_searxng(
                query_url,
                query,
                count,
                filter_list,
                options=options,
                cache_scope=__chat_id__,
            )

            if not response.has_content():
                return json.dumps(
                    {
                        'error': (
                            f'Web search returned no results for "{query}" (engine: searxng).'
                            ' If using SearXNG, upstream engines may be rate-limited — check SearXNG logs '
                            'or wait before retrying. '
                            'Tell the user search failed or returned nothing. '
                            'Do not invent facts or answer "what is X?" from memory — say you could not verify.'
                        ),
                        'query': query,
                        'results': [],
                        **({'engine_failures': response.engine_failures} if response.engine_failures else {}),
                    },
                    ensure_ascii=False,
                )

            from open_webui.retrieval.web.url_cache import cache_search_results

            cache_ttl = int(await Config.get('web.search.cache_ttl') or 60)
            payload = response.to_tool_payload(count=count)
            await cache_search_results(payload.get('results') or [], cache_ttl)
            return json.dumps(payload, ensure_ascii=False)

        results = await _search_web(__request__, engine, query, user)

        # Limit results
        results = results[:count] if results else []

        if not results:
            extra = ''
            if engine == 'searxng':
                extra = (
                    ' If using SearXNG, upstream engines may be rate-limited — check SearXNG logs '
                    'or wait before retrying.'
                )
            return json.dumps(
                {
                    'error': (
                        f'Web search returned no results for "{query}" (engine: {engine}).'
                        f'{extra} '
                        'Tell the user search failed or returned nothing. '
                        'Do not invent facts or answer "what is X?" from memory — say you could not verify.'
                    ),
                    'query': query,
                    'results': [],
                },
                ensure_ascii=False,
            )

        from open_webui.retrieval.web.url_cache import cache_search_results

        cache_ttl = int(await Config.get('web.search.cache_ttl') or 60)
        result_dicts = [{'title': r.title, 'link': r.link, 'snippet': r.snippet} for r in results]
        await cache_search_results(result_dicts, cache_ttl)
        return json.dumps(result_dicts, ensure_ascii=False)
    except Exception as e:
        log.exception(f'search_web error: {e}')
        err = str(e)
        guidance = (
            'Tell the user web search failed. Do not invent an answer or guess what the thing might be — '
            'especially for "what is X?" questions.'
        )
        lowered = err.lower()
        if '429' in lowered or 'too many' in lowered or 'rate' in lowered:
            guidance = (
                'Web search is temporarily rate-limited. Tell the user to try again later. '
                'Do not answer from memory — say you could not look it up.'
            )
        return json.dumps({'error': f'{err}. {guidance}'}, ensure_ascii=False)


async def fetch_url(
    url: Optional[str] = None,
    urls: Optional[list[str]] = None,
    depth: Optional[str] = 'snippet',
    __request__: Request = None,
    __user__: dict = None,
) -> str:
    """
    Fetch and extract the main text content from one or more web page URLs.

    URLs recently returned by search_web may be served from cache when depth=snippet
    (default), avoiding duplicate HTTP fetches. Use depth=full for the full page body.

    Prefer batching multiple URLs in one call instead of repeated single-URL fetches.

    :param url: A single URL to fetch
    :param urls: Multiple URLs to fetch in parallel (max 5)
    :param depth: snippet (default, use search cache when available) or full (always fetch page)
    :return: Structured JSON with title, description, content, and metadata per URL
    """
    if __request__ is None:
        return json.dumps({'error': 'Request context not available'})

    target_urls: list[str] = []
    if urls:
        if isinstance(urls, str):
            try:
                urls = json.loads(urls)
            except json.JSONDecodeError:
                urls = [urls]
        if isinstance(urls, list):
            target_urls.extend(str(item).strip() for item in urls if str(item).strip())
    if url and str(url).strip():
        if str(url).strip() not in target_urls:
            target_urls.insert(0, str(url).strip())

    if not target_urls:
        return json.dumps({'error': 'Provide url or urls to fetch.'})

    target_urls = list(dict.fromkeys(target_urls))[:_FETCH_URL_MAX_BATCH]

    fetch_depth = (depth or 'snippet').strip().lower()
    if fetch_depth not in {'snippet', 'full'}:
        fetch_depth = 'snippet'

    try:
        from open_webui.retrieval.web.url_cache import (
            cached_snippet_to_fetch_entry,
            get_cached_snippet,
            set_cached_full,
        )

        max_length = await Config.get('web.fetch.max_content_length')
        concurrent_limit = await Config.get('web.loader.concurrent_requests')
        if not concurrent_limit or concurrent_limit < 1:
            concurrent_limit = 2
        cache_ttl = int(await Config.get('web.search.cache_ttl') or 60)

        semaphore = asyncio.Semaphore(concurrent_limit)

        async def fetch_with_limit(single_url: str):
            if fetch_depth != 'full':
                cached = await get_cached_snippet(single_url, cache_ttl)
                if cached:
                    return cached_snippet_to_fetch_entry(cached)

            async with semaphore:
                entry = await _fetch_url_entry(__request__, single_url, max_length)
            if not entry.get('error'):
                entry['depth'] = 'full'
                entry['from_cache'] = False
                await set_cached_full(single_url, entry, cache_ttl)
            return entry

        entries = await asyncio.gather(*(fetch_with_limit(single_url) for single_url in target_urls))

        if len(entries) == 1:
            entry = entries[0]
            if entry.get('error') and not entry.get('content'):
                return json.dumps({'error': entry['error'], 'url': entry.get('url')}, ensure_ascii=False)
            return json.dumps(entry, ensure_ascii=False)

        results = [entry for entry in entries if not entry.get('error') or entry.get('content')]
        errors = [{'url': entry.get('url'), 'error': entry.get('error')} for entry in entries if entry.get('error')]
        return json.dumps({'results': results, 'errors': errors}, ensure_ascii=False)
    except Exception as e:
        log.warning(f'fetch_url error: {e}')
        return json.dumps({'error': str(e)})


# =============================================================================
# IMAGE GENERATION TOOLS
# =============================================================================


async def generate_image(
    prompt: str,
    __request__: Request = None,
    __user__: dict = None,
    __event_emitter__: callable = None,
    __chat_id__: str = None,
    __message_id__: str = None,
) -> str:
    """
    Generate an image based on a text prompt.

    :param prompt: A detailed description of the image to generate
    :return: Confirmation that the image was generated, or an error message
    """
    if __request__ is None:
        return json.dumps({'error': 'Request context not available'})

    try:
        user = UserModel(**__user__) if __user__ else None

        images = await image_generations(
            request=__request__,
            form_data=CreateImageForm(prompt=prompt),
            user=user,
        )

        # Prepare file entries for the images
        image_files = [{'type': 'image', 'url': img['url']} for img in images]

        # Persist files to DB if chat context is available
        if __chat_id__ and __message_id__ and images:
            db_files = await Chats.add_message_files_by_id_and_message_id(
                __chat_id__,
                __message_id__,
                image_files,
            )
            if db_files is not None:
                image_files = db_files

        # Emit the images to the UI if event emitter is available
        if __event_emitter__ and image_files:
            await __event_emitter__(
                {
                    'type': 'chat:message:files',
                    'data': {
                        'files': image_files,
                    },
                }
            )
            # Return a message indicating the image is already displayed
            return json.dumps(
                {
                    'status': 'success',
                    'message': 'The image has been successfully generated and is already visible to the user in the chat. You do not need to display or embed the image again - just acknowledge that it has been created.',
                    'images': images,
                },
                ensure_ascii=False,
            )

        return json.dumps({'status': 'success', 'images': images}, ensure_ascii=False)
    except Exception as e:
        log.exception(f'generate_image error: {e}')
        return json.dumps({'error': str(e)})


async def edit_image(
    prompt: str,
    image_urls: list[str],
    __request__: Request = None,
    __user__: dict = None,
    __event_emitter__: callable = None,
    __chat_id__: str = None,
    __message_id__: str = None,
) -> str:
    """
    Transform one or more existing images according to a text prompt.
    Supports targeted edits such as adding, removing, replacing, inpainting, extending, or compositing image content.

    :param prompt: A description of the transformation to apply to the provided images
    :param image_urls: Source image URLs to modify or use as composition inputs
    :return: Confirmation that the images were edited, or an error message
    """
    if __request__ is None:
        return json.dumps({'error': 'Request context not available'})

    try:
        user = UserModel(**__user__) if __user__ else None

        images = await image_edits(
            request=__request__,
            form_data=EditImageForm(prompt=prompt, image=image_urls),
            user=user,
        )

        # Prepare file entries for the images
        image_files = [{'type': 'image', 'url': img['url']} for img in images]

        # Persist files to DB if chat context is available
        if __chat_id__ and __message_id__ and images:
            db_files = await Chats.add_message_files_by_id_and_message_id(
                __chat_id__,
                __message_id__,
                image_files,
            )
            if db_files is not None:
                image_files = db_files

        # Emit the images to the UI if event emitter is available
        if __event_emitter__ and image_files:
            await __event_emitter__(
                {
                    'type': 'chat:message:files',
                    'data': {
                        'files': image_files,
                    },
                }
            )
            # Return a message indicating the image is already displayed
            return json.dumps(
                {
                    'status': 'success',
                    'message': 'The edited image has been successfully generated and is already visible to the user in the chat. You do not need to display or embed the image again - just acknowledge that it has been created.',
                    'images': images,
                },
                ensure_ascii=False,
            )

        return json.dumps({'status': 'success', 'images': images}, ensure_ascii=False)
    except Exception as e:
        log.exception(f'edit_image error: {e}')
        return json.dumps({'error': str(e)})


# =============================================================================
# CODE INTERPRETER TOOLS
# =============================================================================


async def execute_code(
    code: str,
    __request__: Request = None,
    __user__: dict = None,
    __event_emitter__: callable = None,
    __event_call__: callable = None,
    __chat_id__: str = None,
    __message_id__: str = None,
    __metadata__: dict = None,
) -> str:
    """
    Execute Python code in a sandboxed environment and return the output.
    Use this to perform calculations, data analysis, generate visualizations,
    or run any Python code that would help answer the user's question.

    :param code: The Python code to execute
    :return: JSON with stdout, stderr, and result from execution
    """
    from uuid import uuid4

    if __request__ is None:
        return json.dumps({'error': 'Request context not available'})

    try:
        # Sanitize code (strips ANSI codes and markdown fences)
        code = sanitize_code(code)

        # Import blocked modules from config (same as middleware)
        from open_webui.config import CODE_INTERPRETER_BLOCKED_MODULES

        # Add import blocking code if there are blocked modules
        if CODE_INTERPRETER_BLOCKED_MODULES:
            import textwrap

            blocking_code = textwrap.dedent(
                f"""
                import builtins

                BLOCKED_MODULES = {CODE_INTERPRETER_BLOCKED_MODULES}

                _real_import = builtins.__import__
                def restricted_import(name, globals=None, locals=None, fromlist=(), level=0):
                    if name.split('.')[0] in BLOCKED_MODULES:
                        importer_name = globals.get('__name__') if globals else None
                        if importer_name == '__main__':
                            raise ImportError(
                                f"Direct import of module {{name}} is restricted."
                            )
                    return _real_import(name, globals, locals, fromlist, level)

                builtins.__import__ = restricted_import
                """
            )
            code = blocking_code + '\n' + code

        engine = await Config.get('code_interpreter.engine', 'pyodide')
        if engine == 'pyodide':
            # Execute via frontend pyodide using bidirectional event call
            if __event_call__ is None:
                return json.dumps(
                    {'error': 'Event call not available. WebSocket connection required for pyodide execution.'}
                )

            output = await __event_call__(
                {
                    'type': 'execute:python',
                    'data': {
                        'id': str(uuid4()),
                        'code': code,
                        'session_id': (__metadata__.get('session_id') if __metadata__ else None),
                        'files': (__metadata__.get('files', []) if __metadata__ else []),
                    },
                }
            )

            # Parse the output - pyodide returns dict with stdout, stderr, result
            if isinstance(output, dict):
                # Handle error responses from event_caller (e.g. session disconnected, timeout)
                if output.get('error') and not output.get('stdout') and not output.get('result'):
                    stderr = output['error']
                    stdout = ''
                    result = ''
                else:
                    stdout = output.get('stdout', '')
                    stderr = output.get('stderr', '')
                    result = output.get('result', '')
            else:
                stdout = ''
                stderr = ''
                result = str(output) if output else ''

        elif engine == 'jupyter':
            from open_webui.utils.code_interpreter import execute_code_jupyter

            jupyter_auth = await Config.get('code_interpreter.jupyter.auth')

            output = await execute_code_jupyter(
                await Config.get('code_interpreter.jupyter.url'),
                code,
                (await Config.get('code_interpreter.jupyter.auth_token') if jupyter_auth == 'token' else None),
                (await Config.get('code_interpreter.jupyter.auth_password') if jupyter_auth == 'password' else None),
                await Config.get('code_interpreter.jupyter.timeout'),
            )

            stdout = output.get('stdout', '')
            stderr = output.get('stderr', '')
            result = output.get('result', '')

        else:
            return json.dumps({'error': f'Unknown code interpreter engine: {engine}'})

        # Handle image outputs (base64 encoded) - replace with uploaded URLs
        # Get actual user object for image upload (upload_image requires user.id attribute)
        if __user__ and __user__.get('id'):
            from open_webui.models.users import Users
            from open_webui.utils.files import get_image_url_from_base64

            user = await Users.get_user_by_id(__user__['id'])

            # Extract and upload images from stdout
            if stdout and isinstance(stdout, str):
                stdout_lines = stdout.split('\n')
                for idx, line in enumerate(stdout_lines):
                    if 'data:image/png;base64' in line:
                        image_url = await get_image_url_from_base64(
                            __request__,
                            line,
                            __metadata__ or {},
                            user,
                        )
                        if image_url:
                            stdout_lines[idx] = f'![Output Image]({image_url})'
                stdout = '\n'.join(stdout_lines)

            # Extract and upload images from result
            if result and isinstance(result, str):
                result_lines = result.split('\n')
                for idx, line in enumerate(result_lines):
                    if 'data:image/png;base64' in line:
                        image_url = await get_image_url_from_base64(
                            __request__,
                            line,
                            __metadata__ or {},
                            user,
                        )
                        if image_url:
                            result_lines[idx] = f'![Output Image]({image_url})'
                result = '\n'.join(result_lines)

        response = {
            'status': 'success',
            'stdout': stdout,
            'stderr': stderr,
            'result': result,
        }

        return json.dumps(response, ensure_ascii=False)
    except Exception as e:
        log.exception(f'execute_code error: {e}')
        return json.dumps({'error': str(e)})


# =============================================================================
# MEMORY TOOLS
# =============================================================================


async def list_memory_paths(
    query: str = '',
    count: int = 100,
    type: str = 'all',
    __request__: Request = None,
    __user__: dict = None,
) -> str:
    """
    List saved memory paths to find existing memory groups before writing or moving memories.

    :param query: Optional query to filter memory paths or contents
    :param count: Maximum number of paths to return
    :param type: "user", "context", or "all"
    :return: JSON with memory paths, counts, children, and update times
    """
    try:
        user = UserModel(**__user__) if __user__ else None
        result = await _list_memory_paths(
            ListMemoryPathsForm(
                query=query or None,
                type=type if type in {'user', 'context', 'all'} else 'all',
                limit=count,
            ),
            user,
        )
        return json.dumps(result, ensure_ascii=False)
    except Exception as e:
        log.exception(f'list_memory_paths error: {e}')
        return json.dumps({'error': str(e)})


async def read_memory_path(
    path: str,
    count: int = 50,
    type: str = 'all',
    include_children: bool = True,
    __request__: Request = None,
    __user__: dict = None,
) -> str:
    """
    Read saved memories at a memory path, including nearby parent and child paths.

    :param path: Memory path to read
    :param count: Maximum number of memories to return
    :param type: "user", "context", or "all"
    :param include_children: Include memories under child paths
    :return: JSON with parent paths, child paths, and memories at the path
    """
    try:
        user = UserModel(**__user__) if __user__ else None
        result = await _read_memory_path(
            ReadMemoryPathForm(
                path=path,
                type=type if type in {'user', 'context', 'all'} else 'all',
                include_children=include_children,
                limit=count,
            ),
            user,
        )
        return json.dumps(result, ensure_ascii=False)
    except Exception as e:
        log.exception(f'read_memory_path error: {e}')
        return json.dumps({'error': str(e)})


async def search_memories(
    query: str = '',
    count: int = 5,
    type: str = 'all',
    path: Optional[str] = None,
    memory_id: Optional[str] = None,
    __request__: Request = None,
    __user__: dict = None,
) -> str:
    """
    Search or browse saved memories by content, path, type, or memory ID.

    Returns excerpts by default. Use read_memory_path with memory_id or path for full content.

    :param query: Optional query to search memory content and path
    :param count: Number of memories to return (default 5)
    :param type: "user", "context", or "all"
    :param path: Optional memory path to search around
    :param memory_id: Optional exact memory ID to read (returns full content)
    :return: JSON with matching memories, excerpts, and metadata
    """
    if __request__ is None:
        return json.dumps({'error': 'Request context not available'})

    try:
        user = UserModel(**__user__) if __user__ else None

        memories = await _search_memories(
            SearchMemoriesForm(
                query=query or None,
                type=type if type in {'user', 'context', 'all'} else 'all',
                path=path,
                memory_id=memory_id,
                limit=count,
            ),
            user,
        )

        if not memories:
            return json.dumps([])

        results = []
        include_full_content = bool(memory_id)
        for memory in memories:
            entry = {
                'id': memory.id,
                'type': memory.type,
                'path': memory.path,
                'created_at': time.strftime('%Y-%m-%d', time.localtime(memory.created_at)),
                'updated_at': time.strftime('%Y-%m-%d', time.localtime(memory.updated_at)),
            }
            if include_full_content:
                entry['content'] = memory.content
            else:
                excerpt, truncated = _build_text_excerpt(
                    memory.content or '',
                    query=query or '',
                    max_chars=_MEMORY_EXCERPT_MAX_CHARS,
                )
                entry['excerpt'] = excerpt
                if truncated:
                    entry['truncated'] = True
                    entry['read_more'] = 'Use read_memory_path with memory_id or path for full content.'
            results.append(entry)

        return json.dumps(results, ensure_ascii=False)
    except Exception as e:
        log.exception(f'search_memories error: {e}')
        return json.dumps({'error': str(e)})


async def add_memory(
    content: str,
    type: str = 'user',
    path: Optional[str] = None,
    __request__: Request = None,
    __user__: dict = None,
) -> str:
    """
    Save enduring information that can improve future chats.

    Save stable preferences, goals, projects, relationships, habits, and standing instructions.
    Do not save one-off activity, meals, routine daily events, temporary mood, or other short-lived details
    unless the user explicitly asks you to remember them.

    :param content: The memory content to store
    :param type: Use "user" for facts/preferences about the user, or "context" for other durable context
    :param path: Optional stable memory address for grouping related memories
    :return: Confirmation that the memory was stored
    """
    if __request__ is None:
        return json.dumps({'error': 'Request context not available'})

    try:
        user = UserModel(**__user__) if __user__ else None

        memory = await _add_memory(
            __request__,
            AddMemoryForm(content=content, type=Memories.normalize_memory_type(type), path=path),
            user,
        )

        return json.dumps(
            {'status': 'success', 'id': memory.id, 'type': memory.type, 'path': memory.path},
            ensure_ascii=False,
        )
    except Exception as e:
        log.exception(f'add_memory error: {e}')
        return json.dumps({'error': str(e)})


async def update_memory(
    operations: list[dict],
    __request__: Request = None,
    __user__: dict = None,
) -> str:
    """
    Apply a batch of memory changes after learning enduring information.

    Use type "user" for facts, preferences, or instructions about the user.
    Use type "context" for other durable context that may help future chats.
    Do not save one-off activity, meals, routine daily events, temporary mood, or other short-lived details
    unless the user explicitly asks you to remember them.
    Path is optional. Use it as a stable memory address to group related memories.
    Prefer an existing path from list_memory_paths when one fits.
    Leave path empty when no useful grouping is clear.

    Operation shapes:
    - {"action": "add", "content": "...", "type": "user"|"context", "path": "..."}
    - {"action": "replace", "id": "...", "content": "...", "type": "user"|"context", "path": "..."}
    - {"action": "move", "id": "...", "path": "..."}
    - {"action": "remove", "id": "..."}

    :param operations: Memory operations to apply in one request
    :return: JSON with operation results
    """
    if __request__ is None:
        return json.dumps({'error': 'Request context not available'})

    try:
        user = UserModel(**__user__) if __user__ else None
        operation_results = await _update_memories(
            __request__,
            UpdateMemoriesForm(operations=operations),
            user,
        )
        return json.dumps(operation_results, ensure_ascii=False)
    except Exception as e:
        log.exception(f'update_memory error: {e}')
        return json.dumps({'error': str(e)})


async def replace_memory_content(
    memory_id: str,
    content: str,
    type: Optional[str] = None,
    path: Optional[str] = None,
    __request__: Request = None,
    __user__: dict = None,
) -> str:
    """
    Update an existing saved memory by its ID when its content needs correction.

    :param memory_id: The ID of the memory to update
    :param content: The new content for the memory
    :param type: Optional "user" or "context" type for the updated memory
    :param path: Optional stable memory address for grouping related memories
    :return: Confirmation that the memory was updated
    """
    if __request__ is None:
        return json.dumps({'error': 'Request context not available'})

    try:
        user = UserModel(**__user__) if __user__ else None

        memory = await update_memory_by_id(
            memory_id=memory_id,
            request=__request__,
            form_data=MemoryUpdateModel(
                content=content,
                type=Memories.normalize_memory_type(type) if type else None,
                path=path,
            ),
            user=user,
        )

        return json.dumps(
            {
                'status': 'success',
                'id': memory.id,
                'type': memory.type,
                'path': memory.path,
                'content': memory.content,
            },
            ensure_ascii=False,
        )
    except Exception as e:
        log.exception(f'replace_memory_content error: {e}')
        return json.dumps({'error': str(e)})


async def delete_memory(
    memory_id: str,
    __request__: Request = None,
    __user__: dict = None,
) -> str:
    """
    Delete a saved memory by its ID.

    :param memory_id: The ID of the memory to delete
    :return: Confirmation that the memory was deleted
    """
    if __request__ is None:
        return json.dumps({'error': 'Request context not available'})

    try:
        user = UserModel(**__user__) if __user__ else None

        memory = await Memories.get_memory_by_id(memory_id)
        if not memory or memory.user_id != user.id:
            return json.dumps({'error': 'Memory not found or access denied'})

        result = await _delete_memory_by_id(memory_id, __request__, user)

        if result:
            return json.dumps(
                {'status': 'success', 'message': f'Memory {memory_id} deleted'},
                ensure_ascii=False,
            )
        else:
            return json.dumps({'error': 'Memory not found or access denied'})
    except Exception as e:
        log.exception(f'delete_memory error: {e}')
        return json.dumps({'error': str(e)})


async def list_memories(
    __request__: Request = None,
    __user__: dict = None,
) -> str:
    """
    List all stored memories for the user, including IDs and timestamps.

    :return: JSON list of all memories with id, content, and dates
    """
    if __request__ is None:
        return json.dumps({'error': 'Request context not available'})

    try:
        user = UserModel(**__user__) if __user__ else None

        memories = await Memories.get_memories_by_user_id(user.id)

        if memories:
            memory_rows = [
                {
                    'id': m.id,
                    'type': m.type,
                    'path': m.path,
                    'content': m.content,
                    'created_at': time.strftime('%Y-%m-%d %H:%M', time.localtime(m.created_at)),
                    'updated_at': time.strftime('%Y-%m-%d %H:%M', time.localtime(m.updated_at)),
                }
                for m in memories
            ]
            return json.dumps(memory_rows, ensure_ascii=False)
        else:
            return json.dumps([])
    except Exception as e:
        log.exception(f'list_memories error: {e}')
        return json.dumps({'error': str(e)})


# =============================================================================
# NOTES TOOLS
# =============================================================================


def _get_note_markdown(note) -> str:
    if note.data and note.data.get('content', {}).get('md'):
        return note.data['content']['md']
    return ''


async def _get_note_read_access(note_id: str, __user__: dict):
    """Return (note, error_json) — error_json is set when access is denied or note is missing."""
    note = await Notes.get_note_by_id(note_id)
    if not note:
        return None, json.dumps({'error': 'Note not found'})

    user_id = __user__.get('id')
    user_group_ids = [group.id for group in await Groups.get_groups_by_member_id(user_id)]

    from open_webui.models.access_grants import AccessGrants

    if note.user_id != user_id and not await AccessGrants.has_access(
        user_id=user_id,
        resource_type='note',
        resource_id=note.id,
        permission='read',
        user_group_ids=set(user_group_ids),
    ):
        return None, json.dumps({'error': 'Access denied'})

    return note, None


async def _get_note_write_access(note_id: str, __user__: dict):
    """Return (note, error_json) — error_json is set when write access is denied or note is missing."""
    note = await Notes.get_note_by_id(note_id)
    if not note:
        return None, json.dumps({'error': 'Note not found'})

    user_id = __user__.get('id')
    user_group_ids = [group.id for group in await Groups.get_groups_by_member_id(user_id)]

    from open_webui.models.access_grants import AccessGrants

    if note.user_id != user_id and not await AccessGrants.has_access(
        user_id=user_id,
        resource_type='note',
        resource_id=note.id,
        permission='write',
        user_group_ids=set(user_group_ids),
    ):
        return None, json.dumps({'error': 'Write access denied'})

    return note, None


def _normalize_note_line_range(
    start_line: int,
    end_line: Optional[int],
    total_lines: int,
) -> tuple[int, int] | str:
    """Return (start_idx, end_idx) as 0-based inclusive indices, or an error string."""
    if isinstance(start_line, str):
        try:
            start_line = int(start_line)
        except ValueError:
            return 'start_line must be an integer'
    if end_line is None:
        end_line = start_line
    elif isinstance(end_line, str):
        try:
            end_line = int(end_line)
        except ValueError:
            return 'end_line must be an integer'

    if start_line < 1 or end_line < 1:
        return 'Line numbers are 1-indexed and must be positive'
    if start_line > end_line:
        return 'start_line must be less than or equal to end_line'
    if start_line > total_lines:
        return f'start_line {start_line} is beyond the note length ({total_lines} lines)'

    end_line = min(end_line, total_lines)
    return start_line - 1, end_line - 1


async def _request_user_confirmation(
    title: str,
    message: str,
    __event_call__: callable = None,
) -> bool:
    if __event_call__ is None:
        return False

    result = await __event_call__(
        {
            'type': 'confirmation',
            'data': {
                'title': title,
                'message': message,
            },
        }
    )

    if result is True:
        return True
    if isinstance(result, dict) and result.get('confirmed'):
        return True
    return bool(result)


async def search_notes(
    query: str,
    count: int = 5,
    start_timestamp: Optional[int] = None,
    end_timestamp: Optional[int] = None,
    __request__: Request = None,
    __user__: dict = None,
) -> str:
    """
    Search the user's saved notes by title and content.

    :param query: The search query to find matching notes
    :param count: Maximum number of results to return (default: 5)
    :param start_timestamp: Only include notes updated after this Unix timestamp (seconds)
    :param end_timestamp: Only include notes updated before this Unix timestamp (seconds)
    :return: JSON with matching notes containing id, title, and content snippet
    """
    if __request__ is None:
        return json.dumps({'error': 'Request context not available'})

    if not __user__:
        return json.dumps({'error': 'User context not available'})

    try:
        user_id = __user__.get('id')
        user_group_ids = [group.id for group in await Groups.get_groups_by_member_id(user_id)]

        result = await Notes.search_notes(
            user_id=user_id,
            filter={
                'query': query,
                'user_id': user_id,
                'group_ids': user_group_ids,
                'permission': 'read',
            },
            skip=0,
            limit=count * 3,  # Fetch more for filtering
        )

        # Convert timestamps to nanoseconds for comparison
        start_ts = start_timestamp * 1_000_000_000 if start_timestamp else None
        end_ts = end_timestamp * 1_000_000_000 if end_timestamp else None

        notes = []
        for note in result.items:
            # Apply date filters (updated_at is in nanoseconds)
            if start_ts and note.updated_at < start_ts:
                continue
            if end_ts and note.updated_at > end_ts:
                continue

            # Extract a snippet from the markdown content
            content_snippet = ''
            if note.data and note.data.get('content', {}).get('md'):
                md_content = note.data['content']['md']
                content_lower = md_content.lower()

                # Find the first matching word to center the snippet around.
                search_words = query.lower().split()
                match_pos = -1
                match_len = len(query)
                for word in search_words:
                    found_pos = content_lower.find(word)
                    if found_pos != -1:
                        match_pos = found_pos
                        match_len = len(word)
                        break

                if match_pos != -1:
                    snippet_start = max(0, match_pos - 50)
                    snippet_end = min(len(md_content), match_pos + match_len + 100)
                    content_snippet = (
                        ('...' if snippet_start > 0 else '')
                        + md_content[snippet_start:snippet_end]
                        + ('...' if snippet_end < len(md_content) else '')
                    )
                else:
                    content_snippet = md_content[:150] + ('...' if len(md_content) > 150 else '')

            notes.append(
                {
                    'id': note.id,
                    'title': note.title,
                    'snippet': content_snippet,
                    'updated_at': note.updated_at,
                }
            )

            if len(notes) >= count:
                break

        return json.dumps(notes, ensure_ascii=False)
    except Exception as e:
        log.exception(f'search_notes error: {e}')
        return json.dumps({'error': str(e)})


async def view_note(
    note_id: str,
    __request__: Request = None,
    __user__: dict = None,
) -> str:
    """
    Get the full content of a note by its ID.

    :param note_id: The ID of the note to retrieve
    :return: JSON with the note's id, title, and full markdown content
    """
    if __request__ is None:
        return json.dumps({'error': 'Request context not available'})

    if not __user__:
        return json.dumps({'error': 'User context not available'})

    try:
        note = await Notes.get_note_by_id(note_id)

        if not note:
            return json.dumps({'error': 'Note not found'})

        # Check access permission
        user_id = __user__.get('id')
        user_group_ids = [group.id for group in await Groups.get_groups_by_member_id(user_id)]

        from open_webui.models.access_grants import AccessGrants

        if note.user_id != user_id and not await AccessGrants.has_access(
            user_id=user_id,
            resource_type='note',
            resource_id=note.id,
            permission='read',
            user_group_ids=set(user_group_ids),
        ):
            return json.dumps({'error': 'Access denied'})

        # Extract markdown content
        content = ''
        if note.data and note.data.get('content', {}).get('md'):
            content = note.data['content']['md']

        return json.dumps(
            {
                'id': note.id,
                'title': note.title,
                'content': content,
                'updated_at': note.updated_at,
                'created_at': note.created_at,
            },
            ensure_ascii=False,
        )
    except Exception as e:
        log.exception(f'view_note error: {e}')
        return json.dumps({'error': str(e)})


async def write_note(
    title: str,
    content: str,
    __request__: Request = None,
    __user__: dict = None,
) -> str:
    """
    Create a new note with the given title and content.

    :param title: The title of the new note
    :param content: The markdown content for the note
    :return: JSON with success status and new note id
    """
    if __request__ is None:
        return json.dumps({'error': 'Request context not available'})

    if not __user__:
        return json.dumps({'error': 'User context not available'})

    try:
        from open_webui.models.notes import NoteForm

        user_id = __user__.get('id')

        form = NoteForm(
            title=title,
            data={'content': {'md': content}},
            access_grants=[],  # Private by default - only owner can access
        )

        new_note = await Notes.insert_new_note(user_id, form)

        if not new_note:
            return json.dumps({'error': 'Failed to create note'})

        return json.dumps(
            {
                'status': 'success',
                'id': new_note.id,
                'title': new_note.title,
                'created_at': new_note.created_at,
            },
            ensure_ascii=False,
        )
    except Exception as e:
        log.exception(f'write_note error: {e}')
        return json.dumps({'error': str(e)})


async def replace_note_content(
    note_id: str,
    content: str,
    title: Optional[str] = None,
    __request__: Request = None,
    __user__: dict = None,
) -> str:
    """
    Update the markdown content, and optionally the title, of an existing note.

    :param note_id: The ID of the note to update
    :param content: The new markdown content for the note
    :param title: Optional new title for the note
    :return: JSON with success status and updated note info
    """
    if __request__ is None:
        return json.dumps({'error': 'Request context not available'})

    if not __user__:
        return json.dumps({'error': 'User context not available'})

    try:
        from open_webui.models.notes import NoteUpdateForm

        note = await Notes.get_note_by_id(note_id)

        if not note:
            return json.dumps({'error': 'Note not found'})

        # Check write permission
        user_id = __user__.get('id')
        user_group_ids = [group.id for group in await Groups.get_groups_by_member_id(user_id)]

        from open_webui.models.access_grants import AccessGrants

        if note.user_id != user_id and not await AccessGrants.has_access(
            user_id=user_id,
            resource_type='note',
            resource_id=note.id,
            permission='write',
            user_group_ids=set(user_group_ids),
        ):
            return json.dumps({'error': 'Write access denied'})

        # Build update form
        update_data = {'data': {'content': {'md': content}}}
        if title:
            update_data['title'] = title

        form = NoteUpdateForm(**update_data)
        updated_note = await Notes.update_note_by_id(note_id, form)

        if not updated_note:
            return json.dumps({'error': 'Failed to update note'})

        return json.dumps(
            {
                'status': 'success',
                'id': updated_note.id,
                'title': updated_note.title,
                'updated_at': updated_note.updated_at,
            },
            ensure_ascii=False,
        )
    except Exception as e:
        log.exception(f'replace_note_content error: {e}')
        return json.dumps({'error': str(e)})


async def view_note_lines(
    note_id: str,
    start_line: int,
    end_line: Optional[int] = None,
    line_numbers: bool = True,
    __request__: Request = None,
    __user__: dict = None,
) -> str:
    """
    Read a specific line range from a note without loading the entire content.
    Use this to inspect part of a long note before making targeted edits.

    :param note_id: The ID of the note to read
    :param start_line: First line to read (1-indexed)
    :param end_line: Last line to read, inclusive (1-indexed; defaults to start_line)
    :param line_numbers: Prefix each line with its line number (default: true)
    :return: JSON with id, title, content slice, and line metadata
    """
    if __request__ is None:
        return json.dumps({'error': 'Request context not available'})

    if not __user__:
        return json.dumps({'error': 'User context not available'})

    try:
        note, error = await _get_note_read_access(note_id, __user__)
        if error:
            return error

        lines = _get_note_markdown(note).split('\n')
        line_range = _normalize_note_line_range(start_line, end_line, len(lines) or 1)
        if isinstance(line_range, str):
            return json.dumps({'error': line_range})

        start_idx, end_idx = line_range
        selected = lines[start_idx : end_idx + 1]
        if line_numbers:
            content = '\n'.join(f'{start_idx + i + 1}: {line}' for i, line in enumerate(selected))
        else:
            content = '\n'.join(selected)

        return json.dumps(
            {
                'id': note.id,
                'title': note.title,
                'content': content,
                'start_line': start_idx + 1,
                'end_line': end_idx + 1,
                'total_lines': len(lines),
            },
            ensure_ascii=False,
        )
    except Exception as e:
        log.exception(f'view_note_lines error: {e}')
        return json.dumps({'error': str(e)})


async def update_note_content(
    note_id: str,
    start_line: int,
    content: str,
    end_line: Optional[int] = None,
    __request__: Request = None,
    __user__: dict = None,
) -> str:
    """
    Replace a specific line range in a note without rewriting the entire note.
    Use view_note_lines first to inspect the target section.

    :param note_id: The ID of the note to update
    :param start_line: First line to replace (1-indexed)
    :param content: New markdown content for the line range (may span multiple lines)
    :param end_line: Last line to replace, inclusive (1-indexed; defaults to start_line)
    :return: JSON with success status and updated line metadata
    """
    if __request__ is None:
        return json.dumps({'error': 'Request context not available'})

    if not __user__:
        return json.dumps({'error': 'User context not available'})

    try:
        from open_webui.models.notes import NoteUpdateForm

        note, error = await _get_note_write_access(note_id, __user__)
        if error:
            return error

        lines = _get_note_markdown(note).split('\n')
        total_lines = len(lines)
        line_range = _normalize_note_line_range(start_line, end_line, total_lines or 1)
        if isinstance(line_range, str):
            return json.dumps({'error': line_range})

        start_idx, end_idx = line_range
        replacement_lines = content.split('\n')
        updated_lines = lines[:start_idx] + replacement_lines + lines[end_idx + 1 :]
        updated_content = '\n'.join(updated_lines)

        form = NoteUpdateForm(data={'content': {'md': updated_content}})
        updated_note = await Notes.update_note_by_id(note_id, form)

        if not updated_note:
            return json.dumps({'error': 'Failed to update note'})

        return json.dumps(
            {
                'status': 'success',
                'id': updated_note.id,
                'title': updated_note.title,
                'start_line': start_idx + 1,
                'end_line': end_idx + 1,
                'replaced_line_count': end_idx - start_idx + 1,
                'inserted_line_count': len(replacement_lines),
                'total_lines': len(updated_lines),
                'updated_at': updated_note.updated_at,
            },
            ensure_ascii=False,
        )
    except Exception as e:
        log.exception(f'update_note_content error: {e}')
        return json.dumps({'error': str(e)})


async def delete_note(
    note_id: str,
    __request__: Request = None,
    __user__: dict = None,
    __event_call__: callable = None,
) -> str:
    """
    Permanently delete a note. Requires user confirmation in the chat UI.

    :param note_id: The ID of the note to delete
    :return: JSON with success status or cancellation/error details
    """
    if __request__ is None:
        return json.dumps({'error': 'Request context not available'})

    if not __user__:
        return json.dumps({'error': 'User context not available'})

    try:
        note, error = await _get_note_write_access(note_id, __user__)
        if error:
            return error

        if __event_call__ is None:
            return json.dumps({'error': 'Delete requires an active browser session for confirmation'})

        confirmed = await _request_user_confirmation(
            title='Delete note?',
            message=f'This will permanently delete "{note.title}".',
            __event_call__=__event_call__,
        )
        if not confirmed:
            return json.dumps(
                {
                    'status': 'cancelled',
                    'message': 'Note deletion cancelled by user',
                }
            )

        deleted = await Notes.delete_note_by_id(note_id)
        if not deleted:
            return json.dumps({'error': 'Failed to delete note'})

        return json.dumps(
            {
                'status': 'success',
                'id': note_id,
                'title': note.title,
            },
            ensure_ascii=False,
        )
    except Exception as e:
        log.exception(f'delete_note error: {e}')
        return json.dumps({'error': str(e)})


# =============================================================================
# CHATS TOOLS
# =============================================================================


async def search_chats(
    query: str,
    count: int = 5,
    start_timestamp: Optional[int | str] = None,
    end_timestamp: Optional[int | str] = None,
    __request__: Request = None,
    __user__: dict = None,
    __chat_id__: str = None,
) -> str:
    """
    Search the user's previous chat conversations by title and message content.
    Helpful for finding details from earlier conversations.

    :param query: The search query to find matching chats
    :param count: Maximum number of results to return (default: 5)
    :param start_timestamp: Only include chats updated after this time — Unix seconds or
        relative: last_7_days, last_week, last_30_days, last_month
    :param end_timestamp: Only include chats updated before this time — Unix seconds or relative
    :return: JSON with matching chats containing id, title, updated_at, and content snippet
    """
    if __request__ is None:
        return json.dumps({'error': 'Request context not available'})

    if not __user__:
        return json.dumps({'error': 'User context not available'})

    try:
        user_id = __user__.get('id')
        resolved_start = _resolve_chat_timestamp(start_timestamp)
        resolved_end = _resolve_chat_timestamp(end_timestamp)

        chats = await Chats.get_chats_by_user_id_and_search_text(
            user_id=user_id,
            search_text=query,
            include_archived=False,
            skip=0,
            limit=count * 3,  # Fetch more for filtering
        )

        results = []
        for chat in chats:
            # Skip the current chat to avoid showing it in search results
            if __chat_id__ and chat.id == __chat_id__:
                continue

            # Apply date filters (updated_at is in seconds)
            if resolved_start and chat.updated_at < resolved_start:
                continue
            if resolved_end and chat.updated_at > resolved_end:
                continue

            # Find a matching message snippet
            snippet = ''
            messages = (getattr(chat, 'chat', None) or {}).get('history', {}).get('messages', {})
            lower_query = query.lower()

            for msg_id, msg in messages.items():
                content = msg.get('content', '')
                if isinstance(content, str) and lower_query in content.lower():
                    idx = content.lower().find(lower_query)
                    start = max(0, idx - 50)
                    end = min(len(content), idx + len(query) + 100)
                    snippet = ('...' if start > 0 else '') + content[start:end] + ('...' if end < len(content) else '')
                    break

            if not snippet and lower_query in chat.title.lower():
                snippet = f'Title match: {chat.title}'

            results.append(
                {
                    'id': chat.id,
                    'title': chat.title,
                    'snippet': snippet,
                    'updated_at': chat.updated_at,
                }
            )

            if len(results) >= count:
                break

        return json.dumps(results, ensure_ascii=False)
    except Exception as e:
        log.exception(f'search_chats error: {e}')
        return json.dumps({'error': str(e)})


async def view_chat(
    chat_id: str,
    max_messages: int = _VIEW_CHAT_DEFAULT_MAX_MESSAGES,
    offset: int = 0,
    __request__: Request = None,
    __user__: dict = None,
) -> str:
    """
    Get the conversation history of a chat by its ID after a relevant previous chat
    has been identified. Results are paginated to avoid huge context payloads.

    :param chat_id: The ID of the chat to retrieve
    :param max_messages: Maximum messages to return per call (default: 50)
    :param offset: Number of chronological messages to skip (for pagination)
    :return: JSON with the chat's id, title, messages slice, and pagination metadata
    """
    if __request__ is None:
        return json.dumps({'error': 'Request context not available'})

    if not __user__:
        return json.dumps({'error': 'User context not available'})

    try:
        user_id = __user__.get('id')

        chat = await Chats.get_chat_by_id_and_user_id(chat_id, user_id)

        if not chat:
            return json.dumps({'error': 'Chat not found or access denied'})

        # Extract messages from history
        messages = []
        history = chat.chat.get('history', {})
        msg_dict = history.get('messages', {})

        # Build message chain from currentId
        current_id = history.get('currentId')
        visited = set()

        while current_id and current_id not in visited:
            visited.add(current_id)
            msg = msg_dict.get(current_id)
            if msg:
                messages.append(
                    {
                        'role': msg.get('role', ''),
                        'content': msg.get('content', ''),
                    }
                )
            current_id = msg.get('parentId') if msg else None

        # Reverse to get chronological order
        messages.reverse()

        total_messages = len(messages)
        safe_offset = max(0, int(offset or 0))
        safe_limit = max(1, min(int(max_messages or _VIEW_CHAT_DEFAULT_MAX_MESSAGES), 200))
        page = messages[safe_offset : safe_offset + safe_limit]
        next_offset = safe_offset + len(page) if safe_offset + len(page) < total_messages else None

        return json.dumps(
            {
                'id': chat.id,
                'title': chat.title,
                'messages': page,
                'updated_at': chat.updated_at,
                'created_at': chat.created_at,
                'pagination': {
                    'total_messages': total_messages,
                    'offset': safe_offset,
                    'returned': len(page),
                    'truncated': next_offset is not None,
                    'next_offset': next_offset,
                },
            },
            ensure_ascii=False,
        )
    except Exception as e:
        log.exception(f'view_chat error: {e}')
        return json.dumps({'error': str(e)})


async def update_chat(
    chat_id: str,
    title: Optional[str] = None,
    tags: Optional[list[str]] = None,
    __request__: Request = None,
    __user__: dict = None,
) -> str:
    """
    Update a chat's title and/or tags.

    :param chat_id: The ID of the chat to update
    :param title: Optional new title for the chat
    :param tags: Optional list of tag names to set on the chat
    :return: JSON with the updated chat metadata
    """
    if __request__ is None:
        return json.dumps({'error': 'Request context not available'})

    if not __user__:
        return json.dumps({'error': 'User context not available'})

    if title is None and tags is None:
        return json.dumps({'error': 'Provide at least one of title or tags to update'})

    try:
        from types import SimpleNamespace

        user_id = __user__.get('id')
        chat = await Chats.get_chat_by_id_and_user_id(chat_id, user_id)

        if not chat:
            return json.dumps({'error': 'Chat not found or access denied'})

        updated_chat = chat
        if title is not None:
            updated = await Chats.update_chat_title_by_id(chat_id, title)
            if not updated:
                return json.dumps({'error': 'Failed to update chat title'})
            updated_chat = updated

        if tags is not None:
            updated = await Chats.update_chat_tags_by_id(chat_id, tags, SimpleNamespace(id=user_id))
            if not updated:
                return json.dumps({'error': 'Failed to update chat tags'})
            updated_chat = updated

        return json.dumps(
            {
                'status': 'success',
                'id': updated_chat.id,
                'title': updated_chat.title,
                'tags': updated_chat.meta.get('tags', []),
                'updated_at': updated_chat.updated_at,
            },
            ensure_ascii=False,
        )
    except Exception as e:
        log.exception(f'update_chat error: {e}')
        return json.dumps({'error': str(e)})


async def archive_chat(
    chat_id: str,
    __request__: Request = None,
    __user__: dict = None,
) -> str:
    """
    Archive a chat so it is hidden from the main chat list.

    :param chat_id: The ID of the chat to archive
    :return: JSON with success status and archived chat metadata
    """
    if __request__ is None:
        return json.dumps({'error': 'Request context not available'})

    if not __user__:
        return json.dumps({'error': 'User context not available'})

    try:
        user_id = __user__.get('id')
        chat = await Chats.get_chat_by_id_and_user_id(chat_id, user_id)

        if not chat:
            return json.dumps({'error': 'Chat not found or access denied'})

        if chat.archived:
            return json.dumps(
                {
                    'status': 'already_archived',
                    'id': chat.id,
                    'title': chat.title,
                },
                ensure_ascii=False,
            )

        updated_chat = await Chats.toggle_chat_archive_by_id(chat_id)
        if not updated_chat:
            return json.dumps({'error': 'Failed to archive chat'})

        tag_ids = updated_chat.meta.get('tags', [])
        if tag_ids:
            await Chats.delete_orphan_tags_for_user(tag_ids, user_id)

        return json.dumps(
            {
                'status': 'success',
                'id': updated_chat.id,
                'title': updated_chat.title,
                'archived': updated_chat.archived,
            },
            ensure_ascii=False,
        )
    except Exception as e:
        log.exception(f'archive_chat error: {e}')
        return json.dumps({'error': str(e)})


async def list_projects(
    __request__: Request = None,
    __user__: dict = None,
) -> str:
    """
    List chat projects the user can access.
    Use the returned project id with move_chat_to_project (write permission required).

    :return: JSON list of projects with id, name, parent_id, owned, and permission
    """
    if __request__ is None:
        return json.dumps({'error': 'Request context not available'})

    if not __user__:
        return json.dumps({'error': 'User context not available'})

    try:
        from open_webui.internal.db import get_async_db_context
        from open_webui.models.projects import Projects
        from open_webui.models.users import Users
        from open_webui.utils.access_control import has_permission

        user_id = __user__.get('id')
        config = await Config.get_many('projects.enable', 'user.permissions')

        if config.get('projects.enable') is False:
            return json.dumps({'error': 'Projects are disabled'})

        if __user__.get('role') != 'admin' and not await has_permission(
            user_id,
            'features.projects',
            config.get('user.permissions'),
        ):
            return json.dumps({'error': 'Access denied'})

        async with get_async_db_context() as db:
            owned_projects = await Projects.get_projects_by_user_id(user_id, db=db)
            groups = await Groups.get_groups_by_member_id(user_id, db=db)
            group_ids = {group.id for group in groups}
            shared_perms = await Projects.get_shared_project_ids_for_user(user_id, group_ids, db=db)

            projects = []
            seen_ids = set()

            for project in owned_projects:
                projects.append(
                    {
                        'id': project.id,
                        'name': project.name,
                        'parent_id': project.parent_id,
                        'owned': True,
                        'permission': 'write',
                    }
                )
                seen_ids.add(project.id)

            owner_cache = {}
            for project_id, permission in shared_perms.items():
                if project_id in seen_ids:
                    continue

                shared_project = await Projects.get_project_by_id(project_id, db=db)
                if not shared_project or shared_project.user_id == user_id:
                    continue

                if shared_project.user_id not in owner_cache:
                    owner = await Users.get_user_by_id(shared_project.user_id, db=db)
                    owner_cache[shared_project.user_id] = owner.name if owner else 'Unknown'

                projects.append(
                    {
                        'id': shared_project.id,
                        'name': shared_project.name,
                        'parent_id': shared_project.parent_id,
                        'owned': False,
                        'owner_name': owner_cache[shared_project.user_id],
                        'permission': permission,
                    }
                )
                seen_ids.add(shared_project.id)

            # Include sub-projects of shared projects (inherit parent permission)
            for entry in list(projects):
                if entry.get('owned'):
                    continue
                root = await Projects.get_project_by_id(entry['id'], db=db)
                if not root:
                    continue
                children = await Projects.get_children_projects_by_id_and_user_id(root.id, root.user_id, db=db)
                if not children:
                    continue
                for child in children:
                    if child.id in seen_ids:
                        continue
                    projects.append(
                        {
                            'id': child.id,
                            'name': child.name,
                            'parent_id': child.parent_id,
                            'owned': False,
                            'owner_name': owner_cache.get(child.user_id, 'Unknown'),
                            'permission': entry['permission'],
                        }
                    )
                    seen_ids.add(child.id)

            projects.sort(key=lambda f: (f.get('name') or '').lower())

            return json.dumps(
                {
                    'projects': projects,
                    'total': len(projects),
                },
                ensure_ascii=False,
            )
    except Exception as e:
        log.exception(f'list_projects error: {e}')
        return json.dumps({'error': str(e)})


async def create_project(
    name: str,
    parent_id: Optional[str] = None,
    __request__: Request = None,
    __user__: dict = None,
) -> str:
    """
    Create a new chat project, optionally nested under a parent project.

    :param name: The project name
    :param parent_id: Optional parent project ID for a sub-project
    :return: JSON with the new project id, name, and parent_id
    """
    if __request__ is None:
        return json.dumps({'error': 'Request context not available'})

    if not __user__:
        return json.dumps({'error': 'User context not available'})

    if not name or not name.strip():
        return json.dumps({'error': 'Project name is required'})

    try:
        from open_webui.internal.db import get_async_db_context
        from open_webui.models.projects import ProjectForm, Projects
        from open_webui.utils.access_control import has_permission
        from open_webui.utils.access_control.projects import has_project_access

        user_id = __user__.get('id')
        config = await Config.get_many('projects.enable', 'user.permissions')

        if config.get('projects.enable') is False:
            return json.dumps({'error': 'Projects are disabled'})

        if __user__.get('role') != 'admin' and not await has_permission(
            user_id,
            'features.projects',
            config.get('user.permissions'),
        ):
            return json.dumps({'error': 'Access denied'})

        form_data = ProjectForm(name=name.strip(), parent_id=parent_id)

        async with get_async_db_context() as db:
            existing = await Projects.get_project_by_parent_id_and_user_id_and_name(
                parent_id, user_id, form_data.name, db=db
            )
            if existing:
                return json.dumps({'error': 'Project already exists'})

            owner_id = user_id
            if parent_id:
                parent = await Projects.get_project_by_id(parent_id, db=db)
                if not parent:
                    return json.dumps({'error': 'Parent project not found'})
                if parent.user_id != user_id:
                    if __user__.get('role') != 'admin' and not await has_project_access(
                        user_id, parent, 'write', db
                    ):
                        return json.dumps({'error': 'Write access denied for parent project'})
                    owner_id = parent.user_id

            project = await Projects.insert_new_project(owner_id, form_data, parent_id, db=db)
            if not project:
                return json.dumps({'error': 'Failed to create project'})

            return json.dumps(
                {
                    'status': 'success',
                    'id': project.id,
                    'name': project.name,
                    'parent_id': project.parent_id,
                },
                ensure_ascii=False,
            )
    except Exception as e:
        log.exception(f'create_project error: {e}')
        return json.dumps({'error': str(e)})


async def move_chat_to_project(
    chat_id: str,
    project_id: Optional[str] = None,
    __request__: Request = None,
    __user__: dict = None,
) -> str:
    """
    Move a chat into a project, or remove it from its current project.

    :param chat_id: The ID of the chat to move
    :param project_id: Target project ID, or omit/null to remove the chat from any project
    :return: JSON with success status and updated project assignment
    """
    if __request__ is None:
        return json.dumps({'error': 'Request context not available'})

    if not __user__:
        return json.dumps({'error': 'User context not available'})

    try:
        from open_webui.internal.db import get_async_db_context
        from open_webui.models.projects import Projects
        from open_webui.utils.access_control.projects import has_project_access

        user_id = __user__.get('id')

        async with get_async_db_context() as db:
            chat = await Chats.get_chat_by_id_and_user_id(chat_id, user_id, db=db)

            if not chat:
                return json.dumps({'error': 'Chat not found or access denied'})

            if project_id:
                if not await Projects.get_project_by_id_and_user_id(project_id, user_id, db=db):
                    shared_project = await Projects.get_project_by_id(project_id, db=db)
                    if not shared_project or not await has_project_access(user_id, shared_project, 'write', db):
                        return json.dumps({'error': 'Project not found or write access denied'})

            updated_chat = await Chats.update_chat_project_id_by_id_and_user_id(
                chat_id, user_id, project_id, db=db
            )

            if not updated_chat:
                return json.dumps({'error': 'Failed to move chat'})

            return json.dumps(
                {
                    'status': 'success',
                    'id': updated_chat.id,
                    'title': updated_chat.title,
                    'project_id': updated_chat.project_id,
                },
                ensure_ascii=False,
            )
    except Exception as e:
        log.exception(f'move_chat_to_project error: {e}')
        return json.dumps({'error': str(e)})


# =============================================================================
# CHANNELS TOOLS
# =============================================================================


async def search_channels(
    query: str,
    count: int = 5,
    __request__: Request = None,
    __user__: dict = None,
) -> str:
    """
    Search channels by name and description to find accessible team spaces.

    :param query: The search query to find matching channels
    :param count: Maximum number of results to return (default: 5)
    :return: JSON with matching channels containing id, name, description, and type
    """
    if __request__ is None:
        return json.dumps({'error': 'Request context not available'})

    if not __user__:
        return json.dumps({'error': 'User context not available'})

    try:
        user_id = __user__.get('id')

        # Get all channels the user has access to
        all_channels = await Channels.get_channels_by_user_id(user_id)

        # Filter by query
        lower_query = query.lower()
        matching_channels = []

        for channel in all_channels:
            name_match = lower_query in channel.name.lower() if channel.name else False
            desc_match = lower_query in (channel.description or '').lower()

            if name_match or desc_match:
                matching_channels.append(
                    {
                        'id': channel.id,
                        'name': channel.name,
                        'description': channel.description or '',
                        'type': channel.type or 'public',
                    }
                )

            if len(matching_channels) >= count:
                break

        return json.dumps(matching_channels, ensure_ascii=False)
    except Exception as e:
        log.exception(f'search_channels error: {e}')
        return json.dumps({'error': str(e)})


async def search_channel_messages(
    query: str,
    count: int = 10,
    start_timestamp: Optional[int] = None,
    end_timestamp: Optional[int] = None,
    __request__: Request = None,
    __user__: dict = None,
) -> str:
    """
    Search messages in channels the user is a member of, including thread replies.
    Helpful for finding prior team/channel discussion.

    :param query: The search query to find matching messages
    :param count: Maximum number of results to return (default: 10)
    :param start_timestamp: Only include messages created after this Unix timestamp (seconds)
    :param end_timestamp: Only include messages created before this Unix timestamp (seconds)
    :return: JSON with matching messages containing channel info, message content, and thread context
    """
    if __request__ is None:
        return json.dumps({'error': 'Request context not available'})

    if not __user__:
        return json.dumps({'error': 'User context not available'})

    try:
        user_id = __user__.get('id')

        # Get all channels the user has access to
        user_channels = await Channels.get_channels_by_user_id(user_id)
        channel_ids = [c.id for c in user_channels]
        channel_map = {c.id: c for c in user_channels}

        if not channel_ids:
            return json.dumps([])

        # Convert timestamps to nanoseconds (Message.created_at is in nanoseconds)
        start_ts = start_timestamp * 1_000_000_000 if start_timestamp else None
        end_ts = end_timestamp * 1_000_000_000 if end_timestamp else None

        # Search messages using the model method
        matching_messages = await Messages.search_messages_by_channel_ids(
            channel_ids=channel_ids,
            query=query,
            start_timestamp=start_ts,
            end_timestamp=end_ts,
            limit=count,
        )

        results = []
        for msg in matching_messages:
            channel = channel_map.get(msg.channel_id)

            # Extract snippet around the match
            content = msg.content or ''
            lower_query = query.lower()
            idx = content.lower().find(lower_query)
            if idx != -1:
                start = max(0, idx - 50)
                end = min(len(content), idx + len(query) + 100)
                snippet = ('...' if start > 0 else '') + content[start:end] + ('...' if end < len(content) else '')
            else:
                snippet = content[:150] + ('...' if len(content) > 150 else '')

            results.append(
                {
                    'channel_id': msg.channel_id,
                    'channel_name': channel.name if channel else 'Unknown',
                    'message_id': msg.id,
                    'content_snippet': snippet,
                    'is_thread_reply': msg.parent_id is not None,
                    'parent_id': msg.parent_id,
                    'created_at': msg.created_at,
                }
            )

        return json.dumps(results, ensure_ascii=False)
    except Exception as e:
        log.exception(f'search_channel_messages error: {e}')
        return json.dumps({'error': str(e)})


async def view_channel_message(
    message_id: str,
    __request__: Request = None,
    __user__: dict = None,
) -> str:
    """
    Get the full content of a channel message by its ID, including thread replies.

    :param message_id: The ID of the message to retrieve
    :return: JSON with the message content, channel info, and thread replies if any
    """
    if __request__ is None:
        return json.dumps({'error': 'Request context not available'})

    if not __user__:
        return json.dumps({'error': 'User context not available'})

    try:
        user_id = __user__.get('id')

        message = await Messages.get_message_by_id(message_id)

        if not message:
            return json.dumps({'error': 'Message not found'})

        # Verify user has access to the channel
        channel = await Channels.get_channel_by_id(message.channel_id)
        if not channel:
            return json.dumps({'error': 'Channel not found'})

        # Check if user has access to the channel
        user_channels = await Channels.get_channels_by_user_id(user_id)
        channel_ids = [c.id for c in user_channels]

        if message.channel_id not in channel_ids:
            return json.dumps({'error': 'Access denied'})

        # Build response with thread information
        result = {
            'id': message.id,
            'channel_id': message.channel_id,
            'channel_name': channel.name,
            'content': message.content,
            'user_id': message.user_id,
            'is_thread_reply': message.parent_id is not None,
            'parent_id': message.parent_id,
            'reply_count': message.reply_count,
            'created_at': message.created_at,
            'updated_at': message.updated_at,
        }

        # Include user info if available
        if message.user:
            result['user_name'] = message.user.name

        return json.dumps(result, ensure_ascii=False)
    except Exception as e:
        log.exception(f'view_channel_message error: {e}')
        return json.dumps({'error': str(e)})


async def view_channel_thread(
    parent_message_id: str,
    __request__: Request = None,
    __user__: dict = None,
) -> str:
    """
    Get all messages in a channel thread, including the parent message and all replies.

    :param parent_message_id: The ID of the parent message that started the thread
    :return: JSON with the parent message and all thread replies in chronological order
    """
    if __request__ is None:
        return json.dumps({'error': 'Request context not available'})

    if not __user__:
        return json.dumps({'error': 'User context not available'})

    try:
        user_id = __user__.get('id')

        # Get the parent message
        parent_message = await Messages.get_message_by_id(parent_message_id)

        if not parent_message:
            return json.dumps({'error': 'Message not found'})

        # Verify user has access to the channel
        channel = await Channels.get_channel_by_id(parent_message.channel_id)
        if not channel:
            return json.dumps({'error': 'Channel not found'})

        user_channels = await Channels.get_channels_by_user_id(user_id)
        channel_ids = [c.id for c in user_channels]

        if parent_message.channel_id not in channel_ids:
            return json.dumps({'error': 'Access denied'})

        # Get all thread replies
        thread_replies = await Messages.get_thread_replies_by_message_id(parent_message_id)

        # Build the response
        messages = []

        # Add parent message first
        messages.append(
            {
                'id': parent_message.id,
                'content': parent_message.content,
                'user_id': parent_message.user_id,
                'user_name': parent_message.user.name if parent_message.user else None,
                'is_parent': True,
                'created_at': parent_message.created_at,
            }
        )

        # Add thread replies (reverse to get chronological order)
        for reply in reversed(thread_replies):
            messages.append(
                {
                    'id': reply.id,
                    'content': reply.content,
                    'user_id': reply.user_id,
                    'user_name': reply.user.name if reply.user else None,
                    'is_parent': False,
                    'reply_to_id': reply.reply_to_id,
                    'created_at': reply.created_at,
                }
            )

        return json.dumps(
            {
                'channel_id': parent_message.channel_id,
                'channel_name': channel.name,
                'thread_id': parent_message_id,
                'message_count': len(messages),
                'messages': messages,
            },
            ensure_ascii=False,
        )
    except Exception as e:
        log.exception(f'view_channel_thread error: {e}')
        return json.dumps({'error': str(e)})


# =============================================================================
# KNOWLEDGE BASE TOOLS
# =============================================================================


async def search_knowledge_bases(
    query: str,
    count: int = 5,
    skip: int = 0,
    __request__: Request = None,
    __user__: dict = None,
) -> str:
    """
    Search the user's accessible knowledge bases by name and description to find
    a relevant internal source.

    :param query: The search query to find matching knowledge bases
    :param count: Maximum number of results to return (default: 5)
    :param skip: Number of results to skip for pagination (default: 0)
    :return: JSON with matching KBs containing id, name, description, and file_count
    """
    if __request__ is None:
        return json.dumps({'error': 'Request context not available'})

    if not __user__:
        return json.dumps({'error': 'User context not available'})

    try:
        from open_webui.models.knowledge import Knowledges

        user_id = __user__.get('id')
        user_group_ids = [group.id for group in await Groups.get_groups_by_member_id(user_id)]

        result = await Knowledges.search_knowledge_bases(
            user_id,
            filter={
                'query': query,
                'user_id': user_id,
                'group_ids': user_group_ids,
            },
            skip=skip,
            limit=count,
        )

        knowledge_bases = []
        for knowledge_base in result.items:
            files = await Knowledges.get_files_by_id(knowledge_base.id)
            file_count = len(files) if files else 0

            knowledge_bases.append(
                {
                    'id': knowledge_base.id,
                    'name': knowledge_base.name,
                    'description': knowledge_base.description or '',
                    'file_count': file_count,
                    'updated_at': knowledge_base.updated_at,
                }
            )

        return json.dumps(knowledge_bases, ensure_ascii=False)
    except Exception as e:
        log.exception(f'search_knowledge_bases error: {e}')
        return json.dumps({'error': str(e)})


# =============================================================================
# FILES TOOLS
# =============================================================================

MAX_VIEW_FILE_CHARS = 100_000
DEFAULT_VIEW_FILE_MAX_CHARS = 10_000


async def search_files(
    query: str = '*',
    count: int = 20,
    __request__: Request = None,
    __user__: dict = None,
) -> str:
    """
    Search the user's uploaded files by filename.
    Supports wildcards (e.g. "*.pdf", "report*"). Use view_file to read a file's content.

    :param query: Filename search text or glob pattern (default: all files)
    :param count: Maximum number of results to return (default: 20)
    :return: JSON list of matching files with id, filename, and timestamps
    """
    if __request__ is None:
        return json.dumps({'error': 'Request context not available'})

    if not __user__:
        return json.dumps({'error': 'User context not available'})

    try:
        from open_webui.config import BYPASS_ADMIN_ACCESS_CONTROL
        from open_webui.models.files import Files

        user_id = __user__.get('id')
        user_role = __user__.get('role', 'user')

        if isinstance(count, str):
            try:
                count = int(count)
            except ValueError:
                count = 20

        count = max(1, min(count, 100))

        filename = query.strip() if query else '*'
        if filename and '*' not in filename and '?' not in filename:
            filename = f'*{filename}*'

        search_user_id = user_id
        if user_role == 'admin' and BYPASS_ADMIN_ACCESS_CONTROL:
            search_user_id = None

        files = await Files.search_files(
            user_id=search_user_id,
            filename=filename,
            skip=0,
            limit=count,
        )

        results = []
        for file in files:
            meta = file.meta.model_dump() if hasattr(file.meta, 'model_dump') else (file.meta or {})
            results.append(
                {
                    'id': file.id,
                    'filename': file.filename,
                    'created_at': file.created_at,
                    'updated_at': file.updated_at,
                    'content_type': meta.get('content_type'),
                }
            )

        return json.dumps(
            {
                'files': results,
                'total': len(results),
            },
            ensure_ascii=False,
        )
    except Exception as e:
        log.exception(f'search_files error: {e}')
        return json.dumps({'error': str(e)})


async def view_file(
    file_id: str,
    offset: int = 0,
    max_chars: int = DEFAULT_VIEW_FILE_MAX_CHARS,
    line_numbers: bool = False,
    start_line: Optional[int] = None,
    end_line: Optional[int] = None,
    __request__: Request = None,
    __user__: dict = None,
    __model_knowledge__: Optional[list[dict]] = None,
) -> str:
    """
    Get the content of a file by its ID. Supports pagination for large files.

    :param file_id: The ID of the file to retrieve
    :param offset: Character offset to start reading from (default: 0)
    :param max_chars: Maximum characters to return (default: 10000, hard cap: 100000)
    :param line_numbers: If true, prefix each line with its 1-indexed line number
    :param start_line: Optional 1-indexed start line (overrides offset/max_chars when set)
    :param end_line: Optional 1-indexed end line (inclusive)
    :return: JSON with the file's id, filename, content, and pagination metadata if truncated
    """
    if __request__ is None:
        return json.dumps({'error': 'Request context not available'})

    if not __user__:
        return json.dumps({'error': 'User context not available'})

    # Coerce parameters from LLM tool calls (may come as strings)
    if isinstance(offset, str):
        try:
            offset = int(offset)
        except ValueError:
            offset = 0
    if isinstance(max_chars, str):
        try:
            max_chars = int(max_chars)
        except ValueError:
            max_chars = DEFAULT_VIEW_FILE_MAX_CHARS

    # Enforce hard cap
    max_chars = min(max(max_chars, 1), MAX_VIEW_FILE_CHARS)
    offset = max(offset, 0)

    try:
        from open_webui.models.files import Files

        user_id = __user__.get('id')
        user_role = __user__.get('role', 'user')

        file = await Files.get_file_by_id(file_id)
        if not file:
            return json.dumps({'error': 'File not found'})

        if not await _has_read_access_to_file(file, user_id, user_role, __model_knowledge__):
            return json.dumps({'error': 'File not found'})

        content = ''
        if file.data:
            content = file.data.get('content', '')

        total_chars = len(content)

        # Line-based addressing (overrides char-based offset/max_chars)
        if start_line is not None:
            all_lines = content.split('\n')
            total_lines = len(all_lines)
            s = max(1, int(start_line)) - 1  # 1-indexed to 0-indexed
            e = min(total_lines, int(end_line) if end_line else s + 100)
            selected = all_lines[s:e]
            sliced = '\n'.join(f'{s + i + 1}: {line}' for i, line in enumerate(selected))
            is_truncated = e < total_lines
            result = {
                'id': file.id,
                'filename': file.filename,
                'content': sliced,
                'updated_at': file.updated_at,
                'created_at': file.created_at,
                'total_lines': total_lines,
                'showing_lines': f'{s + 1}-{e}',
            }
            if is_truncated:
                result['truncated'] = True
                result['next_start_line'] = e + 1
            return json.dumps(result, ensure_ascii=False)

        sliced = content[offset : offset + max_chars]
        is_truncated = (offset + len(sliced)) < total_chars

        if line_numbers:
            start_ln = content[:offset].count('\n') + 1
            lines = sliced.split('\n')
            sliced = '\n'.join(f'{start_ln + i}: {line}' for i, line in enumerate(lines))

        result = {
            'id': file.id,
            'filename': file.filename,
            'content': sliced,
            'updated_at': file.updated_at,
            'created_at': file.created_at,
        }

        if is_truncated or offset > 0:
            result['truncated'] = is_truncated
            result['total_chars'] = total_chars
            result['returned_chars'] = len(sliced)
            result['offset'] = offset
            if is_truncated:
                result['next_offset'] = offset + len(sliced)

        return json.dumps(result, ensure_ascii=False)
    except Exception as e:
        log.exception(f'view_file error: {e}')
        return json.dumps({'error': str(e)})


async def query_knowledge_files(
    query: str,
    knowledge_ids: Optional[list[str]] = None,
    count: int = 5,
    auto_query: bool = True,
    kb_count: int = _DEFAULT_AUTO_QUERY_KB_COUNT,
    __request__: Request = None,
    __user__: dict = None,
    __model_knowledge__: list[dict] = None,
) -> str:
    """
    Search knowledge base files using semantic/vector search. Searches across collections (KBs),
    individual files, and notes that the user has access to.
    Helpful for internal documentation, uploaded knowledge, and attached model knowledge.

    With auto_query=true (default), semantically discovers the most relevant knowledge bases and
    queries them in one call — no separate query_knowledge_bases step needed.

    Note attachments return excerpts only; use view_note or view_note_lines for full note content.

    :param query: The search query to find semantically relevant content
    :param knowledge_ids: Optional list of KB ids to limit search to specific knowledge bases
    :param count: Maximum number of results to return (default: 5)
    :param auto_query: When true and knowledge_ids omitted, discover relevant KBs automatically (default: true)
    :param kb_count: How many knowledge bases to consider when auto_query is enabled (default: 5)
    :return: JSON with overview, grouped sources, matched_knowledge_bases, and relevance-scored chunks
    """
    if __request__ is None:
        return json.dumps({'error': 'Request context not available'})

    if not __user__:
        return json.dumps({'error': 'User context not available'})

    # Coerce parameters from LLM tool calls (may come as strings)
    if isinstance(count, str):
        try:
            count = int(count)
        except ValueError:
            count = 5  # Default fallback

    if isinstance(auto_query, str):
        auto_query = auto_query.strip().lower() not in {'false', '0', 'no', 'off'}

    if isinstance(kb_count, str):
        try:
            kb_count = int(kb_count)
        except ValueError:
            kb_count = _DEFAULT_AUTO_QUERY_KB_COUNT

    # Handle knowledge_ids being string "None", "null", or empty
    if isinstance(knowledge_ids, str):
        if knowledge_ids.lower() in ('none', 'null', ''):
            knowledge_ids = None
        else:
            # Try to parse as JSON array if it looks like one
            try:
                knowledge_ids = json.loads(knowledge_ids)
            except json.JSONDecodeError:
                # Treat as single ID
                knowledge_ids = [knowledge_ids]

    try:
        from open_webui.models.access_grants import AccessGrants
        from open_webui.models.files import Files
        from open_webui.models.knowledge import Knowledges
        from open_webui.models.notes import Notes
        from open_webui.retrieval.external import retrieve_external_knowledge
        from open_webui.retrieval.utils import query_collection

        user_id = __user__.get('id')
        user_role = __user__.get('role', 'user')
        user_group_ids = [group.id for group in await Groups.get_groups_by_member_id(user_id)]

        embedding_function = __request__.app.state.EMBEDDING_FUNCTION
        if not embedding_function:
            return json.dumps({'error': 'Embedding function not configured'})

        collection_names = []
        external_knowledges = []
        note_results = []  # Notes aren't vectorized, handle separately
        matched_knowledge_bases: list[dict] = []

        # If model has attached knowledge, use those
        if __model_knowledge__:
            for item in __model_knowledge__:
                item_type = item.get('type')
                item_id = item.get('id')

                if item_type == 'collection':
                    # Knowledge base - use KB ID as collection name
                    knowledge = await Knowledges.get_knowledge_by_id(item_id)
                    if knowledge and (
                        user_role == 'admin'
                        or knowledge.user_id == user_id
                        or await AccessGrants.has_access(
                            user_id=user_id,
                            resource_type='knowledge',
                            resource_id=knowledge.id,
                            permission='read',
                            user_group_ids=set(user_group_ids),
                        )
                    ):
                        if (knowledge.meta or {}).get('source') == 'external':
                            external_knowledges.append(knowledge)
                        else:
                            collection_names.append(item_id)

                elif item_type == 'file':
                    # Individual file - use file-{id} as collection name
                    file = await Files.get_file_by_id(item_id)
                    if file:
                        collection_names.append(f'file-{item_id}')

                elif item_type == 'note':
                    # Note - return excerpt; use view_note for full content
                    note = await Notes.get_note_by_id(item_id)
                    if note and (
                        user_role == 'admin'
                        or note.user_id == user_id
                        or await AccessGrants.has_access(
                            user_id=user_id,
                            resource_type='note',
                            resource_id=note.id,
                            permission='read',
                        )
                    ):
                        note_results.append(_build_note_chunk(note, query=query))

        elif knowledge_ids:
            # User specified specific KBs
            for knowledge_id in knowledge_ids:
                knowledge = await Knowledges.get_knowledge_by_id(knowledge_id)
                if knowledge and (
                    user_role == 'admin'
                    or knowledge.user_id == user_id
                    or await AccessGrants.has_access(
                        user_id=user_id,
                        resource_type='knowledge',
                        resource_id=knowledge.id,
                        permission='read',
                        user_group_ids=set(user_group_ids),
                    )
                ):
                    if (knowledge.meta or {}).get('source') == 'external':
                        external_knowledges.append(knowledge)
                    else:
                        collection_names.append(knowledge_id)
        else:
            safe_kb_count = max(1, min(int(kb_count or _DEFAULT_AUTO_QUERY_KB_COUNT), 20))
            if auto_query:
                matched_knowledge_bases = await _discover_knowledge_bases_by_query(
                    __request__,
                    user_id,
                    user_group_ids,
                    query,
                    count=safe_kb_count,
                )
                for kb in matched_knowledge_bases:
                    knowledge = await Knowledges.get_knowledge_by_id(kb['id'])
                    if not knowledge:
                        continue
                    if (knowledge.meta or {}).get('source') == 'external':
                        external_knowledges.append(knowledge)
                    else:
                        collection_names.append(knowledge.id)
            else:
                # Legacy wide search across all accessible KBs
                result = await Knowledges.search_knowledge_bases(
                    user_id,
                    filter={
                        'query': '',
                        'user_id': user_id,
                        'group_ids': user_group_ids,
                    },
                    skip=0,
                    limit=50,
                )
                for knowledge_base in result.items:
                    if (knowledge_base.meta or {}).get('source') == 'external':
                        external_knowledges.append(knowledge_base)
                    else:
                        collection_names.append(knowledge_base.id)

        chunks = []

        # Add note results first
        chunks.extend(note_results)

        # Query vector collections if any
        if collection_names:
            query_results = await query_collection(
                __request__,
                collection_names=collection_names,
                queries=[query],
                embedding_function=embedding_function,
                k=max(count * 3, count, 10),
            )

            if query_results and 'documents' in query_results:
                documents = query_results.get('documents', [[]])[0]
                metadatas = query_results.get('metadatas', [[]])[0]
                distances = query_results.get('distances', [[]])[0]

                for idx, doc in enumerate(documents):
                    chunk_info = {
                        'content': doc,
                        'source': metadatas[idx].get('source', metadatas[idx].get('name', 'Unknown')),
                        'file_id': metadatas[idx].get('file_id', ''),
                    }
                    if idx < len(distances):
                        chunk_info['distance'] = distances[idx]
                        chunk_info['relevance'] = distances[idx]
                    chunks.append(chunk_info)

        for knowledge in external_knowledges:
            query_results = await retrieve_external_knowledge(
                __request__,
                knowledge,
                queries=[query],
                count=max(count * 3, count, 10),
                user=type('UserContext', (), {'id': user_id, 'role': user_role})(),
            )
            documents = query_results.get('documents', [[]])[0]
            metadatas = query_results.get('metadatas', [[]])[0]
            distances = query_results.get('distances', [[]])[0]

            for idx, doc in enumerate(documents):
                metadata = metadatas[idx] if idx < len(metadatas) else {}
                chunk_info = {
                    'content': doc,
                    'source': metadata.get('source', metadata.get('name', knowledge.name)),
                    'file_id': metadata.get('file_id', f'external-{knowledge.id}'),
                    'type': 'external',
                    'knowledge_id': knowledge.id,
                }
                if idx < len(distances):
                    chunk_info['distance'] = distances[idx]
                    chunk_info['relevance'] = distances[idx]
                chunks.append(chunk_info)

        relevance_threshold = await Config.get('rag.relevance_threshold', 0.0) or 0.0
        chunks = _filter_knowledge_chunks_by_threshold(chunks, float(relevance_threshold))
        chunks.sort(
            key=lambda chunk: _knowledge_chunk_relevance(chunk) if _knowledge_chunk_relevance(chunk) is not None else -1.0,
            reverse=True,
        )
        chunks = chunks[:count]

        if not chunks:
            return json.dumps(
                {
                    'query': query,
                    'overview': None,
                    'sources': [],
                    'total_chunks': 0,
                    'message': 'No knowledge chunks met the relevance threshold for this query.',
                },
                ensure_ascii=False,
            )

        return json.dumps(
            _build_knowledge_query_payload(query, chunks, matched_knowledge_bases=matched_knowledge_bases or None),
            ensure_ascii=False,
        )
    except Exception as e:
        log.exception(f'query_knowledge_files error: {e}')
        return json.dumps({'error': str(e)})


async def query_knowledge_bases(
    query: str,
    count: int = 5,
    __request__: Request = None,
    __user__: dict = None,
) -> str:
    """
    Search knowledge bases by semantic similarity to query.
    Finds KBs whose name/description match the meaning of your query.

    Prefer query_knowledge_files with auto_query=true — it discovers relevant KBs and
    returns matching chunks in one call.

    :param query: Natural language query describing what you're looking for
    :param count: Maximum results (default: 5)
    :return: JSON with matching KBs (id, name, description, similarity)
    """
    if __request__ is None:
        return json.dumps({'error': 'Request context not available'})

    if not __user__:
        return json.dumps({'error': 'User context not available'})

    try:
        user_id = __user__.get('id')
        user_group_ids = [group.id for group in await Groups.get_groups_by_member_id(user_id)]

        if isinstance(count, str):
            try:
                count = int(count)
            except ValueError:
                count = 5

        matching_knowledge_bases = await _discover_knowledge_bases_by_query(
            __request__,
            user_id,
            user_group_ids,
            query,
            count=max(1, min(count, 20)),
        )

        return json.dumps(matching_knowledge_bases, ensure_ascii=False)

    except Exception as e:
        log.exception(f'query_knowledge_bases error: {e}')
        return json.dumps({'error': str(e)})


# =============================================================================
# SKILLS TOOLS
# =============================================================================


async def search_skills(
    query: str,
    count: int = 5,
    __request__: Request = None,
    __user__: dict = None,
) -> str:
    """
    Search available skills by name, description, or id.
    Use view_skill to load the full instructions for a matching skill.

    :param query: Search text to match against skill name, description, or id
    :param count: Maximum number of results to return (default: 5)
    :return: JSON list of matching skills with id, name, and description
    """
    if __request__ is None:
        return json.dumps({'error': 'Request context not available'})

    if not __user__:
        return json.dumps({'error': 'User context not available'})

    try:
        from open_webui.models.skills import Skills

        user_id = __user__.get('id')
        user_group_ids = [group.id for group in await Groups.get_groups_by_member_id(user_id)]

        if isinstance(count, str):
            try:
                count = int(count)
            except ValueError:
                count = 5

        result = await Skills.search_skills(
            user_id=user_id,
            filter={
                'query': query,
                'user_id': user_id,
                'group_ids': user_group_ids,
                'permission': 'read',
            },
            skip=0,
            limit=count,
        )

        skills = []
        for skill in result.items:
            if not skill.is_active:
                continue
            skills.append(
                {
                    'id': skill.id,
                    'name': skill.name,
                    'description': skill.description or '',
                }
            )

        return json.dumps(
            {
                'skills': skills,
                'total': result.total,
            },
            ensure_ascii=False,
        )
    except Exception as e:
        log.exception(f'search_skills error: {e}')
        return json.dumps({'error': str(e)})


async def view_skill(
    id: str,
    __request__: Request = None,
    __user__: dict = None,
) -> str:
    """
    Load the full instructions of a skill by its id from the available skills manifest.
    Use this when you need detailed instructions for a skill listed in <available_skills>.

    :param id: The id of the skill to load (as shown in the manifest)
    :return: The full skill instructions as markdown content
    """
    if __request__ is None:
        return json.dumps({'error': 'Request context not available'})

    if not __user__:
        return json.dumps({'error': 'User context not available'})

    try:
        from open_webui.models.access_grants import AccessGrants
        from open_webui.models.skills import Skills

        user_id = __user__.get('id')

        # Direct DB lookup by id (case-insensitive since IDs are stored lowercase)
        skill = await Skills.get_skill_by_id(id.lower())

        if not skill or not skill.is_active:
            return json.dumps({'error': f"Skill '{id}' not found"})

        # Check user access
        user_role = __user__.get('role', 'user')
        if user_role != 'admin' and skill.user_id != user_id:
            user_group_ids = [group.id for group in await Groups.get_groups_by_member_id(user_id)]
            if not await AccessGrants.has_access(
                user_id=user_id,
                resource_type='skill',
                resource_id=skill.id,
                permission='read',
                user_group_ids=set(user_group_ids),
            ):
                return json.dumps({'error': 'Access denied'})

        return json.dumps(
            {
                'name': skill.name,
                'content': skill.content,
            },
            ensure_ascii=False,
        )
    except Exception as e:
        log.exception(f'view_skill error: {e}')
        return json.dumps({'error': str(e)})


# =============================================================================
# TASK MANAGEMENT TOOLS
# =============================================================================

from typing import Literal

from pydantic import BaseModel, Field

VALID_TASK_STATUSES = {'pending', 'in_progress', 'completed', 'cancelled'}


class TaskItem(BaseModel):
    id: Optional[str] = Field(None, description='Unique identifier for the task. Auto-generated if omitted.')
    content: str = Field(..., description='Task description.')
    status: Literal['pending', 'in_progress', 'completed', 'cancelled'] = Field('pending', description='Task status.')


def _task_summary(all_tasks: list[dict]) -> dict:
    """Build summary counts for a task list."""
    pending = sum(1 for t in all_tasks if t['status'] == 'pending')
    in_progress = sum(1 for t in all_tasks if t['status'] == 'in_progress')
    completed = sum(1 for t in all_tasks if t['status'] == 'completed')
    cancelled = sum(1 for t in all_tasks if t['status'] == 'cancelled')
    return {
        'total': len(all_tasks),
        'pending': pending,
        'in_progress': in_progress,
        'completed': completed,
        'cancelled': cancelled,
    }


async def _emit_tasks(event_emitter, all_tasks: list[dict]):
    """Persist task state to the UI."""
    if event_emitter:
        await event_emitter(
            {
                'type': 'chat:message:tasks',
                'data': {
                    'tasks': all_tasks,
                },
            }
        )


async def create_tasks(
    tasks: list[TaskItem],
    __chat_id__: str = None,
    __message_id__: str = None,
    __event_emitter__: callable = None,
    __request__: Request = None,
    __user__: dict = None,
) -> str:
    """
    Create a visible task checklist for multi-step work so progress can be shown in chat.

    :param tasks: List of task items. Each item: content (string, required), status (pending|in_progress|completed|cancelled, default pending), id (optional, auto-generated).
    :return: JSON with the full task list and summary counts
    """
    if __chat_id__ is None:
        return json.dumps({'error': 'Chat context not available'})

    try:
        all_tasks = []
        for idx, task in enumerate(tasks):
            if hasattr(task, 'model_dump'):
                d = task.model_dump(exclude_none=True)
            elif isinstance(task, dict):
                d = task
            else:
                d = dict(task)

            content = str(d.get('content', '')).strip()
            if not content:
                continue

            item_id = str(d.get('id', '') or '').strip() or str(idx + 1)
            status = str(d.get('status', 'pending')).strip().lower()
            if status not in VALID_TASK_STATUSES:
                status = 'pending'

            all_tasks.append({'id': item_id, 'content': content, 'status': status})

        await Chats.update_chat_tasks_by_id(__chat_id__, all_tasks)
        await _emit_tasks(__event_emitter__, all_tasks)

        return json.dumps(
            {'tasks': all_tasks, 'summary': _task_summary(all_tasks)},
            ensure_ascii=False,
        )
    except Exception as e:
        log.exception(f'tasks error: {e}')
        return json.dumps({'error': str(e)})


async def update_task(
    id: str,
    status: str = 'completed',
    __chat_id__: str = None,
    __message_id__: str = None,
    __event_emitter__: callable = None,
    __request__: Request = None,
    __user__: dict = None,
) -> str:
    """
    Mark a single visible task item as completed, in_progress, pending, or cancelled.

    :param id: The task ID to update
    :param status: New status: completed, in_progress, pending, or cancelled (default: completed)
    :return: JSON with the updated task list and summary counts
    """
    if __chat_id__ is None:
        return json.dumps({'error': 'Chat context not available'})

    try:
        status = status.strip().lower()
        if status not in VALID_TASK_STATUSES:
            return json.dumps(
                {'error': f'Invalid status: {status}. Must be one of: {", ".join(sorted(VALID_TASK_STATUSES))}'}
            )

        all_tasks = await Chats.get_chat_tasks_by_id(__chat_id__)

        found = False
        for task in all_tasks:
            if task['id'] == id:
                task['status'] = status
                found = True
                break

        if not found:
            return json.dumps({'error': f'Task with id "{id}" not found'})

        await Chats.update_chat_tasks_by_id(__chat_id__, all_tasks)
        await _emit_tasks(__event_emitter__, all_tasks)

        return json.dumps(
            {'tasks': all_tasks, 'summary': _task_summary(all_tasks)},
            ensure_ascii=False,
        )
    except Exception as e:
        log.exception(f'update_task_status error: {e}')
        return json.dumps({'error': str(e)})


# =============================================================================
# AUTOMATION TOOLS
# =============================================================================


async def create_automation(
    name: str,
    prompt: str,
    rrule: str,
    __request__: Request = None,
    __user__: dict = None,
    __metadata__: dict = None,
) -> str:
    """
    Create a scheduled automation that runs a prompt on a recurring or one-time schedule.
    Use this when the user wants to schedule a task to run automatically.
    The automation will use the current chat model.

    The rrule parameter must be a valid iCalendar RRULE string. Common examples:
    - Every day at 9am: "DTSTART:20250101T090000\\nRRULE:FREQ=DAILY"
    - Every Monday at 8am: "DTSTART:20250106T080000\\nRRULE:FREQ=WEEKLY;BYDAY=MO"
    - Every hour: "RRULE:FREQ=HOURLY;INTERVAL=1"
    - Every 30 minutes: "RRULE:FREQ=MINUTELY;INTERVAL=30"
    - Once at a specific time: "DTSTART:20250415T140000\\nRRULE:FREQ=DAILY;COUNT=1"
    - First day of every month: "DTSTART:20250101T090000\\nRRULE:FREQ=MONTHLY;BYMONTHDAY=1"

    The DTSTART time should reflect the desired execution time. Use COUNT=1 for one-time automations.

    :param name: A short descriptive name for the automation
    :param prompt: The prompt/instructions to execute on each run
    :param rrule: An iCalendar RRULE string defining the schedule
    :return: JSON with the created automation details including id, next scheduled runs
    """
    if __request__ is None:
        return json.dumps({'error': 'Request context not available'})

    if not __user__:
        return json.dumps({'error': 'User context not available'})

    try:
        from open_webui.models.automations import AutomationData, AutomationForm, Automations
        from open_webui.models.users import Users
        from open_webui.utils.automations import next_n_runs_ns, next_run_ns, validate_rrule

        user_id = __user__.get('id')
        user = await Users.get_user_by_id(user_id)
        if not user:
            return json.dumps({'error': 'User not found'})

        # Fall back to model dict ID since __metadata__ may predate model_id assignment
        metadata = __metadata__ or {}
        model_id = metadata.get('model_id') or (
            metadata.get('model', {}).get('id') if isinstance(metadata.get('model'), dict) else None
        )
        if not model_id:
            return json.dumps({'error': 'Could not detect current model'})

        # Validate the RRULE
        try:
            validate_rrule(rrule, tz=user.timezone)
        except ValueError as e:
            return json.dumps({'error': f'Invalid schedule: {e}'})

        tz = user.timezone
        form = AutomationForm(
            name=name,
            data=AutomationData(
                prompt=prompt,
                model_id=model_id,
                rrule=rrule,
            ),
            is_active=True,
        )

        automation = await Automations.insert(user_id, form, next_run_ns(rrule, tz=tz))

        return json.dumps(
            {
                'status': 'success',
                'id': automation.id,
                'name': automation.name,
                'model_id': model_id,
                'is_active': automation.is_active,
                'next_runs': next_n_runs_ns(rrule, tz=tz),
            },
            ensure_ascii=False,
        )
    except Exception as e:
        log.exception(f'create_automation error: {e}')
        return json.dumps({'error': str(e)})


async def update_automation(
    automation_id: str,
    name: Optional[str] = None,
    prompt: Optional[str] = None,
    rrule: Optional[str] = None,
    model_id: Optional[str] = None,
    __request__: Request = None,
    __user__: dict = None,
) -> str:
    """
    Update an existing automation. Only the provided fields are changed; omitted fields stay the same.

    :param automation_id: The ID of the automation to update
    :param name: New name for the automation (optional)
    :param prompt: New prompt/instructions (optional)
    :param rrule: New iCalendar RRULE schedule string (optional). See create_automation for format examples.
    :param model_id: New model ID to use (optional)
    :return: JSON with the updated automation details
    """
    if __request__ is None:
        return json.dumps({'error': 'Request context not available'})

    if not __user__:
        return json.dumps({'error': 'User context not available'})

    try:
        from open_webui.models.automations import AutomationData, AutomationForm, Automations
        from open_webui.models.users import Users
        from open_webui.utils.automations import next_n_runs_ns, next_run_ns, validate_rrule

        user_id = __user__.get('id')
        user = await Users.get_user_by_id(user_id)

        automation = await Automations.get_by_id(automation_id)
        if not automation:
            return json.dumps({'error': 'Automation not found'})
        if automation.user_id != user_id:
            return json.dumps({'error': 'Access denied'})

        # Merge provided fields with existing values
        new_name = name if name is not None else automation.name
        new_prompt = prompt if prompt is not None else automation.data.get('prompt', '')
        new_model_id = model_id if model_id is not None else automation.data.get('model_id', '')
        new_rrule = rrule if rrule is not None else automation.data.get('rrule', '')

        # Validate RRULE if changed
        if rrule is not None:
            try:
                validate_rrule(new_rrule, tz=user.timezone if user else None)
            except ValueError as e:
                return json.dumps({'error': f'Invalid schedule: {e}'})

        tz = user.timezone if user else None
        form = AutomationForm(
            name=new_name,
            data=AutomationData(
                prompt=new_prompt,
                model_id=new_model_id,
                rrule=new_rrule,
            ),
            is_active=automation.is_active,
        )

        updated = await Automations.update_by_id(automation_id, form, next_run_ns(new_rrule, tz=tz))

        return json.dumps(
            {
                'status': 'success',
                'id': updated.id,
                'name': updated.name,
                'model_id': new_model_id,
                'is_active': updated.is_active,
                'next_runs': next_n_runs_ns(new_rrule, tz=tz),
            },
            ensure_ascii=False,
        )
    except Exception as e:
        log.exception(f'update_automation error: {e}')
        return json.dumps({'error': str(e)})


async def list_automations(
    status: Optional[str] = None,
    count: int = 10,
    __request__: Request = None,
    __user__: dict = None,
) -> str:
    """
    List the user's scheduled automations.

    :param status: Filter by status: "active", "paused", or omit for all
    :param count: Maximum number of automations to return (default: 10)
    :return: JSON list of automations with id, name, prompt snippet, schedule, status, and next runs
    """
    if __request__ is None:
        return json.dumps({'error': 'Request context not available'})

    if not __user__:
        return json.dumps({'error': 'User context not available'})

    try:
        from open_webui.models.automations import Automations
        from open_webui.models.users import Users
        from open_webui.utils.automations import next_n_runs_ns

        user_id = __user__.get('id')
        user = await Users.get_user_by_id(user_id)

        result = await Automations.search_automations(
            user_id=user_id,
            status=status,
            skip=0,
            limit=count,
        )

        automations = []
        for item in result.items:
            rrule = item.data.get('rrule', '')
            prompt_text = item.data.get('prompt', '')
            snippet = prompt_text[:100] + ('...' if len(prompt_text) > 100 else '')

            automations.append(
                {
                    'id': item.id,
                    'name': item.name,
                    'prompt_snippet': snippet,
                    'model_id': item.data.get('model_id', ''),
                    'rrule': rrule,
                    'is_active': item.is_active,
                    'last_run_at': item.last_run_at,
                    'next_runs': next_n_runs_ns(rrule, tz=user.timezone if user else None),
                }
            )

        return json.dumps(
            {'automations': automations, 'total': result.total},
            ensure_ascii=False,
        )
    except Exception as e:
        log.exception(f'list_automations error: {e}')
        return json.dumps({'error': str(e)})


async def toggle_automation(
    automation_id: str,
    __request__: Request = None,
    __user__: dict = None,
) -> str:
    """
    Pause or resume a scheduled automation. If active, it will be paused. If paused, it will be resumed.

    :param automation_id: The ID of the automation to toggle
    :return: JSON with the updated automation status
    """
    if __request__ is None:
        return json.dumps({'error': 'Request context not available'})

    if not __user__:
        return json.dumps({'error': 'User context not available'})

    try:
        from open_webui.models.automations import Automations
        from open_webui.models.users import Users
        from open_webui.utils.automations import next_run_ns

        user_id = __user__.get('id')
        user = await Users.get_user_by_id(user_id)

        automation = await Automations.get_by_id(automation_id)
        if not automation:
            return json.dumps({'error': 'Automation not found'})
        if automation.user_id != user_id:
            return json.dumps({'error': 'Access denied'})

        rrule = automation.data.get('rrule', '')
        toggled = await Automations.toggle(
            automation_id,
            next_run_ns(rrule, tz=user.timezone if user else None),
        )

        return json.dumps(
            {
                'status': 'success',
                'id': toggled.id,
                'name': toggled.name,
                'is_active': toggled.is_active,
            },
            ensure_ascii=False,
        )
    except Exception as e:
        log.exception(f'toggle_automation error: {e}')
        return json.dumps({'error': str(e)})


async def delete_automation(
    automation_id: str,
    __request__: Request = None,
    __user__: dict = None,
) -> str:
    """
    Delete a scheduled automation and all its run history.

    :param automation_id: The ID of the automation to delete
    :return: JSON confirming the automation was deleted
    """
    if __request__ is None:
        return json.dumps({'error': 'Request context not available'})

    if not __user__:
        return json.dumps({'error': 'User context not available'})

    try:
        from open_webui.models.automations import AutomationRuns, Automations

        user_id = __user__.get('id')

        automation = await Automations.get_by_id(automation_id)
        if not automation:
            return json.dumps({'error': 'Automation not found'})
        if automation.user_id != user_id:
            return json.dumps({'error': 'Access denied'})

        name = automation.name
        await AutomationRuns.delete_by_automation(automation_id)
        await Automations.delete(automation_id)

        return json.dumps(
            {
                'status': 'success',
                'message': f'Automation "{name}" deleted',
            },
            ensure_ascii=False,
        )
    except Exception as e:
        log.exception(f'delete_automation error: {e}')
        return json.dumps({'error': str(e)})


# =============================================================================
# CALENDAR TOOLS
# =============================================================================


def _get_user_tz(user_dict: dict):
    """Get the user's timezone as a ZoneInfo, falling back to UTC."""
    from zoneinfo import ZoneInfo

    tz_name = None
    if user_dict:
        tz_name = user_dict.get('timezone')
    if tz_name:
        try:
            return ZoneInfo(tz_name)
        except Exception:
            pass
    return ZoneInfo('UTC')


def _dt_to_ns(dt_str: str, tz) -> int:
    """Convert a datetime string to nanoseconds since epoch, interpreting in the given timezone."""
    from datetime import datetime

    dt = datetime.fromisoformat(dt_str)
    # If naive (no timezone info), localize to user's timezone
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=tz)
    return int(dt.timestamp() * 1_000) * 1_000_000


def _ns_to_dt(ns: int, tz) -> str:
    """Convert nanoseconds since epoch to a datetime string in the given timezone."""
    from datetime import datetime

    seconds = ns / 1_000_000_000
    dt = datetime.fromtimestamp(seconds, tz=tz)
    return dt.strftime('%Y-%m-%d %H:%M')


def _event_to_dict(event, tz) -> dict:
    """Convert a calendar event model to a human-friendly dict with local timestamps."""
    alert_minutes = None
    if event.meta and 'alert_minutes' in event.meta:
        alert_minutes = event.meta['alert_minutes']
    return {
        'id': event.id,
        'calendar_id': event.calendar_id,
        'title': event.title,
        'description': event.description or '',
        'start': _ns_to_dt(event.start_at, tz),
        'end': _ns_to_dt(event.end_at, tz) if event.end_at else None,
        'all_day': event.all_day,
        'location': event.location or '',
        'reminder_minutes': alert_minutes if alert_minutes is not None else 10,
        'color': event.color,
        'is_cancelled': event.is_cancelled,
    }


async def list_calendars(
    __request__: Request = None,
    __user__: dict = None,
) -> str:
    """
    List calendars available to the user.
    Use the returned calendar_id when creating or updating events.

    :return: JSON list of calendars with id, name, color, and is_default
    """
    if __request__ is None:
        return json.dumps({'error': 'Request context not available'})

    if not __user__:
        return json.dumps({'error': 'User context not available'})

    try:
        from open_webui.models.calendar import Calendars

        user_id = __user__.get('id')
        calendars = await Calendars.get_calendars_by_user(user_id)

        return json.dumps(
            {
                'calendars': [
                    {
                        'id': cal.id,
                        'name': cal.name,
                        'color': cal.color,
                        'is_default': cal.is_default,
                    }
                    for cal in calendars
                ],
                'total': len(calendars),
            },
            ensure_ascii=False,
        )
    except Exception as e:
        log.exception(f'list_calendars error: {e}')
        return json.dumps({'error': str(e)})


async def search_calendar_events(
    query: Optional[str] = None,
    start: Optional[str] = None,
    end: Optional[str] = None,
    count: int = 10,
    __request__: Request = None,
    __user__: dict = None,
) -> str:
    """
    Search calendar events, reminders, and scheduled items by text and/or date range.
    Helpful for finding upcoming events, reminders, or schedule items.

    :param query: Search text to match against event title, description, or location (optional)
    :param start: Only return events starting at or after this datetime, e.g. "2026-04-20 00:00" (optional)
    :param end: Only return events starting before this datetime, e.g. "2026-04-27 00:00" (optional)
    :param count: Maximum number of events to return (default: 10)
    :return: JSON list of matching events with id, title, description, start, end, calendar_id, location
    """
    if __request__ is None:
        return json.dumps({'error': 'Request context not available'})

    if not __user__:
        return json.dumps({'error': 'User context not available'})

    try:
        from open_webui.models.calendar import CalendarEvents

        user_id = __user__.get('id')
        tz = _get_user_tz(__user__)

        if isinstance(count, str):
            try:
                count = int(count)
            except ValueError:
                count = 10

        if start or end:
            # Date range query — use get_events_by_range
            try:
                start_ns = _dt_to_ns(start, tz) if start else 0
            except (ValueError, TypeError) as e:
                return json.dumps({'error': f'Invalid start datetime: {e}'})

            try:
                end_ns = (
                    _dt_to_ns(end, tz)
                    if end
                    else int(time.time() * 1_000) * 1_000_000 + 365 * 86400 * 1_000_000_000_000
                )
            except (ValueError, TypeError) as e:
                return json.dumps({'error': f'Invalid end datetime: {e}'})

            items = await CalendarEvents.get_events_by_range(
                user_id=user_id,
                start=start_ns,
                end=end_ns,
            )

            # Apply text filter if query is also provided
            if query:
                q = query.lower()
                items = [
                    e
                    for e in items
                    if q in (e.title or '').lower()
                    or q in (e.description or '').lower()
                    or q in (e.location or '').lower()
                ]

            events = [_event_to_dict(item, tz) for item in items[:count]]
            return json.dumps(
                {'events': events, 'total': len(items)},
                ensure_ascii=False,
            )
        else:
            # Text-only search
            result = await CalendarEvents.search_events(
                user_id=user_id,
                query=query,
                skip=0,
                limit=count,
            )

            events = [_event_to_dict(item, tz) for item in result.items]
            return json.dumps(
                {'events': events, 'total': result.total},
                ensure_ascii=False,
            )
    except Exception as e:
        log.exception(f'search_calendar_events error: {e}')
        return json.dumps({'error': str(e)})


async def create_calendar_event(
    title: str,
    start: str,
    end: Optional[str] = None,
    description: Optional[str] = None,
    calendar_id: Optional[str] = None,
    all_day: bool = False,
    location: Optional[str] = None,
    reminder_minutes: Optional[int] = None,
    __request__: Request = None,
    __user__: dict = None,
) -> str:
    """
    Create a calendar event, reminder, or alarm. Use this when the user wants to
    schedule an event, set a reminder, create an alarm, or says things like
    "remind me", "don't let me forget", "notify me at", or "add to my calendar".
    For simple reminders, omit end/location/all_day and set reminder_minutes to 0.

    :param title: Event or reminder title (e.g. "Team standup", "Take medicine", "Call mom")
    :param start: Start datetime in the user's local time (e.g. "2026-04-20 09:00")
    :param end: End datetime in the user's local time (optional — omit for reminders or point-in-time events)
    :param description: Event description or notes (optional)
    :param calendar_id: Target calendar ID (optional, uses default calendar if omitted)
    :param all_day: Whether this is an all-day event (default: false)
    :param location: Event location (optional)
    :param reminder_minutes: Minutes before the event to send a notification (optional, default: 10). Use 0 for "at time of event", -1 for no notification.
    :return: JSON with the created event details including id
    """
    if __request__ is None:
        return json.dumps({'error': 'Request context not available'})

    if not __user__:
        return json.dumps({'error': 'User context not available'})

    try:
        from open_webui.models.calendar import CalendarEventForm, CalendarEvents, Calendars

        user_id = __user__.get('id')

        # Resolve calendar_id: use provided, or fall back to default
        if not calendar_id:
            calendars = await Calendars.get_calendars_by_user(user_id)
            default_cal = next((c for c in calendars if c.is_default), None)
            if not default_cal and calendars:
                default_cal = calendars[0]
            if not default_cal:
                return json.dumps({'error': 'No calendars found. Cannot create event.'})
            calendar_id = default_cal.id

        # Verify access
        cal = await Calendars.get_calendar_by_id(calendar_id)
        if not cal:
            return json.dumps({'error': 'Calendar not found'})
        if cal.user_id != user_id and __user__.get('role') != 'admin':
            from open_webui.models.access_grants import AccessGrants
            from open_webui.models.groups import Groups

            user_group_ids = [g.id for g in await Groups.get_groups_by_member_id(user_id)]
            if not await AccessGrants.has_access(
                user_id=user_id,
                resource_type='calendar',
                resource_id=cal.id,
                permission='write',
                user_group_ids=set(user_group_ids),
            ):
                return json.dumps({'error': 'Access denied to this calendar'})

        # Coerce boolean from LLM
        if isinstance(all_day, str):
            all_day = all_day.lower() in ('true', '1', 'yes')

        # Convert datetime strings to nanoseconds using user's timezone
        tz = _get_user_tz(__user__)
        try:
            start_ns = _dt_to_ns(start, tz)
        except (ValueError, TypeError) as e:
            return json.dumps({'error': f'Invalid start datetime: {e}. Use format like "2026-04-20 09:00"'})

        end_ns = None
        if end:
            try:
                end_ns = _dt_to_ns(end, tz)
            except (ValueError, TypeError) as e:
                return json.dumps({'error': f'Invalid end datetime: {e}. Use format like "2026-04-20 10:00"'})
        elif not all_day:
            # Default to 1 hour duration
            end_ns = start_ns + 3_600_000_000_000

        # Build meta with reminder setting
        meta = {}
        if reminder_minutes is not None:
            if isinstance(reminder_minutes, str):
                try:
                    reminder_minutes = int(reminder_minutes)
                except ValueError:
                    reminder_minutes = 10
            meta['alert_minutes'] = reminder_minutes
        else:
            meta['alert_minutes'] = 10

        form = CalendarEventForm(
            calendar_id=calendar_id,
            title=title,
            description=description,
            start_at=start_ns,
            end_at=end_ns,
            all_day=all_day,
            location=location,
            meta=meta,
        )

        event = await CalendarEvents.insert_new_event(user_id, form)
        if not event:
            return json.dumps({'error': 'Failed to create event'})

        return json.dumps(
            {
                'status': 'success',
                **_event_to_dict(event, tz),
            },
            ensure_ascii=False,
        )
    except Exception as e:
        log.exception(f'create_calendar_event error: {e}')
        return json.dumps({'error': str(e)})


async def update_calendar_event(
    event_id: str,
    title: Optional[str] = None,
    description: Optional[str] = None,
    start: Optional[str] = None,
    end: Optional[str] = None,
    all_day: Optional[bool] = None,
    location: Optional[str] = None,
    is_cancelled: Optional[bool] = None,
    reminder_minutes: Optional[int] = None,
    __request__: Request = None,
    __user__: dict = None,
) -> str:
    """
    Update an existing calendar event. Only provided fields are changed;
    omitted fields stay the same.

    :param event_id: The ID of the event to update
    :param title: New event title (optional)
    :param description: New event description (optional)
    :param start: New start datetime string in your local time, e.g. "2026-04-20 09:00" (optional)
    :param end: New end datetime string in your local time (optional)
    :param all_day: Whether this is an all-day event (optional)
    :param location: New event location (optional)
    :param is_cancelled: Set to true to cancel the event (optional)
    :param reminder_minutes: Minutes before the event to send a reminder notification (optional). Use 0 for "at time of event", -1 for no reminder. Accepts any positive integer for custom timing (e.g. 120 for 2 hours before).
    :return: JSON with the updated event details
    """
    if __request__ is None:
        return json.dumps({'error': 'Request context not available'})

    if not __user__:
        return json.dumps({'error': 'User context not available'})

    try:
        from open_webui.models.access_grants import AccessGrants
        from open_webui.models.calendar import CalendarEvents, CalendarEventUpdateForm, Calendars
        from open_webui.models.groups import Groups

        user_id = __user__.get('id')

        event = await CalendarEvents.get_event_by_id(event_id)
        if not event:
            return json.dumps({'error': 'Event not found'})

        # Check write access to the event's calendar
        if event.user_id != user_id and __user__.get('role') != 'admin':
            cal = await Calendars.get_calendar_by_id(event.calendar_id)
            if not cal:
                return json.dumps({'error': 'Access denied'})
            user_group_ids = [g.id for g in await Groups.get_groups_by_member_id(user_id)]
            if not await AccessGrants.has_access(
                user_id=user_id,
                resource_type='calendar',
                resource_id=cal.id,
                permission='write',
                user_group_ids=set(user_group_ids),
            ):
                return json.dumps({'error': 'Access denied'})

        # Coerce boolean strings from LLM
        if isinstance(all_day, str):
            all_day = all_day.lower() in ('true', '1', 'yes')
        if isinstance(is_cancelled, str):
            is_cancelled = is_cancelled.lower() in ('true', '1', 'yes')

        # Convert datetime strings to nanoseconds using user's timezone
        tz = _get_user_tz(__user__)
        start_ns = None
        if start is not None:
            try:
                start_ns = _dt_to_ns(start, tz)
            except (ValueError, TypeError) as e:
                return json.dumps({'error': f'Invalid start datetime: {e}'})

        end_ns = None
        if end is not None:
            try:
                end_ns = _dt_to_ns(end, tz)
            except (ValueError, TypeError) as e:
                return json.dumps({'error': f'Invalid end datetime: {e}'})

        # Build meta update with reminder setting if provided
        meta = None
        if reminder_minutes is not None:
            if isinstance(reminder_minutes, str):
                try:
                    reminder_minutes = int(reminder_minutes)
                except ValueError:
                    reminder_minutes = None
            if reminder_minutes is not None:
                meta = {'alert_minutes': reminder_minutes}

        form = CalendarEventUpdateForm(
            title=title,
            description=description,
            start_at=start_ns,
            end_at=end_ns,
            all_day=all_day,
            location=location,
            is_cancelled=is_cancelled,
            meta=meta,
        )

        updated = await CalendarEvents.update_event_by_id(event_id, form)
        if not updated:
            return json.dumps({'error': 'Failed to update event'})

        return json.dumps(
            {
                'status': 'success',
                **_event_to_dict(updated, tz),
            },
            ensure_ascii=False,
        )
    except Exception as e:
        log.exception(f'update_calendar_event error: {e}')
        return json.dumps({'error': str(e)})


async def delete_calendar_event(
    event_id: str,
    __request__: Request = None,
    __user__: dict = None,
) -> str:
    """
    Delete a calendar event permanently.

    :param event_id: The ID of the event to delete
    :return: JSON confirming the event was deleted
    """
    if __request__ is None:
        return json.dumps({'error': 'Request context not available'})

    if not __user__:
        return json.dumps({'error': 'User context not available'})

    try:
        from open_webui.models.access_grants import AccessGrants
        from open_webui.models.calendar import CalendarEvents, Calendars
        from open_webui.models.groups import Groups

        user_id = __user__.get('id')

        event = await CalendarEvents.get_event_by_id(event_id)
        if not event:
            return json.dumps({'error': 'Event not found'})

        # Check write access
        if event.user_id != user_id and __user__.get('role') != 'admin':
            cal = await Calendars.get_calendar_by_id(event.calendar_id)
            if not cal:
                return json.dumps({'error': 'Access denied'})
            user_group_ids = [g.id for g in await Groups.get_groups_by_member_id(user_id)]
            if not await AccessGrants.has_access(
                user_id=user_id,
                resource_type='calendar',
                resource_id=cal.id,
                permission='write',
                user_group_ids=set(user_group_ids),
            ):
                return json.dumps({'error': 'Access denied'})

        title = event.title
        result = await CalendarEvents.delete_event_by_id(event_id)
        if not result:
            return json.dumps({'error': 'Failed to delete event'})

        return json.dumps(
            {
                'status': 'success',
                'message': f'Event "{title}" deleted',
            },
            ensure_ascii=False,
        )
    except Exception as e:
        log.exception(f'delete_calendar_event error: {e}')
        return json.dumps({'error': str(e)})


# =============================================================================
# WEATHER, MAPS, CURRENCY, SPORTS & INTERACTIVE TOOLS
# =============================================================================

_WMO_WEATHER_DESCRIPTIONS = {
    0: 'Clear sky',
    1: 'Mainly clear',
    2: 'Partly cloudy',
    3: 'Overcast',
    45: 'Fog',
    48: 'Depositing rime fog',
    51: 'Light drizzle',
    53: 'Moderate drizzle',
    55: 'Dense drizzle',
    56: 'Light freezing drizzle',
    57: 'Dense freezing drizzle',
    61: 'Slight rain',
    63: 'Moderate rain',
    65: 'Heavy rain',
    66: 'Light freezing rain',
    67: 'Heavy freezing rain',
    71: 'Slight snow',
    73: 'Moderate snow',
    75: 'Heavy snow',
    77: 'Snow grains',
    80: 'Slight rain showers',
    81: 'Moderate rain showers',
    82: 'Violent rain showers',
    85: 'Slight snow showers',
    86: 'Heavy snow showers',
    95: 'Thunderstorm',
    96: 'Thunderstorm with slight hail',
    99: 'Thunderstorm with heavy hail',
}


def _wmo_description(code: int | None) -> str:
    if code is None:
        return 'Unknown'
    return _WMO_WEATHER_DESCRIPTIONS.get(int(code), 'Unknown')


async def _http_get_json(url: str, headers: dict | None = None, params: dict | None = None) -> dict | list:
    from open_webui.utils.session_pool import get_session

    session = await get_session()
    async with session.get(url, headers=headers or {}, params=params or {}) as response:
        response.raise_for_status()
        return await response.json()


async def _geocode_open_meteo(location: str) -> dict | None:
    payload = await _http_get_json(
        'https://geocoding-api.open-meteo.com/v1/search',
        params={'name': location, 'count': 1, 'language': 'en', 'format': 'json'},
    )
    results = payload.get('results') or []
    return results[0] if results else None


async def _reverse_geocode_open_meteo(latitude: float, longitude: float) -> str:
    try:
        payload = await _http_get_json(
            'https://geocoding-api.open-meteo.com/v1/reverse',
            params={'latitude': latitude, 'longitude': longitude, 'language': 'en'},
        )
        results = payload.get('results') or []
        if results:
            place = results[0]
            parts = [place.get('name'), place.get('admin1'), place.get('country')]
            return ', '.join(p for p in parts if p)
    except Exception:
        pass
    return f'{latitude:.4f}, {longitude:.4f}'


async def weather_fetch(
    location: Optional[str] = None,
    __event_call__: callable = None,
    __event_emitter__: callable = None,
    __metadata__: dict = None,
) -> str:
    """
    Fetch current weather and a short forecast for a location. If no location is given, requests the user's
    browser coordinates via geolocation.

    :param location: City or place name (optional — uses browser location if omitted)
    :return: JSON with current conditions plus daily (7-day) and hourly (24h) forecast
    """
    try:
        latitude = None
        longitude = None
        location_name = location

        if not location or not str(location).strip():
            if __event_call__ is None:
                return json.dumps({'error': 'Location required. Please specify a city or enable location access.'})

            coords = await __event_call__({'type': 'request:location', 'data': {}})
            if not isinstance(coords, dict) or coords.get('error'):
                return json.dumps(
                    {
                        'error': 'Location access denied or unavailable. Please specify a city name instead.',
                    }
                )

            latitude = float(coords['latitude'])
            longitude = float(coords['longitude'])
            location_name = await _reverse_geocode_open_meteo(latitude, longitude)
        else:
            geo = await _geocode_open_meteo(str(location).strip())
            if not geo:
                return json.dumps({'error': f'Could not find location: {location}'})
            latitude = float(geo['latitude'])
            longitude = float(geo['longitude'])
            location_name = ', '.join(
                p for p in [geo.get('name'), geo.get('admin1'), geo.get('country')] if p
            )

        forecast = await _http_get_json(
            'https://api.open-meteo.com/v1/forecast',
            params={
                'latitude': latitude,
                'longitude': longitude,
                'current': 'temperature_2m,relative_humidity_2m,apparent_temperature,weather_code,wind_speed_10m',
                'daily': 'weather_code,temperature_2m_max,temperature_2m_min,precipitation_probability_max',
                'hourly': 'temperature_2m,weather_code,precipitation_probability',
                'forecast_days': 7,
                'timezone': 'auto',
            },
        )
        current = forecast.get('current') or {}
        weather_code = current.get('weather_code')
        description = _wmo_description(weather_code)

        weather_data = {
            'location': location_name,
            'latitude': latitude,
            'longitude': longitude,
            'temperature': current.get('temperature_2m'),
            'temperature_unit': (forecast.get('current_units') or {}).get('temperature_2m', '°C'),
            'feels_like': current.get('apparent_temperature'),
            'humidity': current.get('relative_humidity_2m'),
            'wind_speed': current.get('wind_speed_10m'),
            'wind_speed_unit': (forecast.get('current_units') or {}).get('wind_speed_10m', 'km/h'),
            'weather_code': weather_code,
            'description': description,
            'time': current.get('time'),
            'forecast': _build_weather_forecast(forecast),
        }

        if __event_emitter__:
            await __event_emitter__({'type': 'chat:message:weather', 'data': weather_data})

        return json.dumps(
            {
                'status': 'success',
                'message': 'Weather card displayed to the user.',
                'weather': weather_data,
            },
            ensure_ascii=False,
        )
    except Exception as e:
        log.exception(f'weather_fetch error: {e}')
        return json.dumps({'error': str(e)})


async def image_search(
    query: str,
    count: Optional[int] = 8,
    __request__: Request = None,
    __user__: dict = None,
    __event_emitter__: callable = None,
    __chat_id__: str = None,
    __message_id__: str = None,
) -> str:
    """
    Search the web for images matching a query and display them inline in the chat.

    :param query: The image search query
    :param count: Number of images to return (default 8, max 12)
    :return: Confirmation with rich image metadata (title, source page, thumbnail)
    """
    if __request__ is None:
        return json.dumps({'error': 'Request context not available'})

    try:
        count = max(1, min(int(count or 8), 12))
        engine = await Config.get('web.search.engine')
        images: list[dict] = []

        if engine == 'searxng':
            images = await _searxng_image_results(query, count, cache_scope=__chat_id__)
        elif engine == 'brave':
            images = await _brave_image_results(query, count)
        else:
            images = await _searxng_image_results(query, count, cache_scope=__chat_id__)
            if not images:
                images = await _brave_image_results(query, count)

        images = _dedupe_image_results(images)[:count]

        if not images:
            return json.dumps({'error': f'No images found for query: {query}'})

        image_files = [{'type': 'image', 'url': image['image_url']} for image in images if image.get('image_url')]

        if __chat_id__ and __message_id__ and image_files:
            db_files = await Chats.add_message_files_by_id_and_message_id(
                __chat_id__,
                __message_id__,
                image_files,
            )
            if db_files is not None:
                image_files = db_files

        if __event_emitter__ and image_files:
            await __event_emitter__(
                {
                    'type': 'chat:message:files',
                    'data': {'files': image_files},
                }
            )
            return json.dumps(
                {
                    'status': 'success',
                    'message': (
                        'Images have been displayed inline in the chat. '
                        'Do not embed or link them again — acknowledge they are visible.'
                    ),
                    'count': len(image_files),
                    'images': images,
                },
                ensure_ascii=False,
            )

        return json.dumps({'status': 'success', 'count': len(image_files), 'images': images}, ensure_ascii=False)
    except Exception as e:
        log.exception(f'image_search error: {e}')
        return json.dumps({'error': str(e)})


async def present_options(
    question: str,
    options: list[str],
    __event_emitter__: callable = None,
) -> str:
    """
    Present the user with 2–4 tappable option buttons below your message text. Their selection arrives as their next message.

    Write any brief intro or explanation in your response first, then call this tool so buttons render under your prose.

    :param question: The question to present
    :param options: List of 2–4 short option labels
    :return: Confirmation that options were displayed
    """
    try:
        labels = [str(o).strip() for o in (options or []) if str(o).strip()]
        if len(labels) < 2:
            return json.dumps({'error': 'Provide at least 2 options.'})
        if len(labels) > 4:
            labels = labels[:4]

        payload = {'question': question, 'options': labels}

        if __event_emitter__:
            await __event_emitter__({'type': 'chat:message:options', 'data': payload})

        return json.dumps(
            {
                'status': 'success',
                'message': 'Options displayed. Wait for the user to select one.',
            },
            ensure_ascii=False,
        )
    except Exception as e:
        log.exception(f'present_options error: {e}')
        return json.dumps({'error': str(e)})


async def _get_exchange_rate_payload(from_code: str) -> dict:
    now = time.monotonic()
    async with _exchange_rate_lock:
        entry = _EXCHANGE_RATE_CACHE.get(from_code)
        if entry and entry[0] > now:
            return entry[1].copy()

    payload = await _http_get_json(f'https://open.er-api.com/v6/latest/{from_code}')
    if not isinstance(payload, dict):
        raise ValueError('Unexpected exchange-rate API response')

    async with _exchange_rate_lock:
        _EXCHANGE_RATE_CACHE[from_code] = (time.monotonic() + _EXCHANGE_RATE_CACHE_TTL, payload)
    return payload


async def currency_convert(
    amount: float,
    from_currency: str,
    to_currency: Optional[str] = None,
    to_currencies: Optional[list[str]] = None,
    __event_emitter__: callable = None,
) -> str:
    """
    Convert an amount between currencies using live exchange rates.

    Rates are cached for one hour per source currency. Convert to multiple targets
    in one call with to_currencies instead of repeated single-pair calls.

    :param amount: The amount to convert
    :param from_currency: Source currency code (e.g. USD)
    :param to_currency: Single target currency code (e.g. EUR)
    :param to_currencies: Multiple target codes in one call (e.g. ["EUR", "GBP", "JPY"])
    :return: JSON with conversion result(s) and rate(s)
    """
    try:
        from_code = str(from_currency).strip().upper()
        targets: list[str] = []
        if to_currency and str(to_currency).strip():
            targets.append(str(to_currency).strip().upper())
        if to_currencies:
            parsed = to_currencies
            if isinstance(parsed, str):
                try:
                    parsed = json.loads(parsed)
                except json.JSONDecodeError:
                    parsed = [parsed]
            if isinstance(parsed, list):
                targets.extend(str(code).strip().upper() for code in parsed if str(code).strip())
        targets = list(dict.fromkeys(targets))

        if not from_code:
            return json.dumps({'error': 'from_currency is required.'})
        if not targets:
            return json.dumps({'error': 'Provide to_currency or to_currencies.'})

        payload = await _get_exchange_rate_payload(from_code)
        rates = payload.get('rates') or {}
        updated = payload.get('time_last_update_utc')
        amount_value = float(amount)

        conversions: list[dict] = []
        for to_code in targets:
            if to_code not in rates:
                return json.dumps({'error': f'Unknown currency code: {to_code}'})
            rate = float(rates[to_code])
            inverse_rate = round(1 / rate, 6) if rate else None
            conversions.append(
                {
                    'from': from_code,
                    'to': to_code,
                    'amount': amount_value,
                    'result': round(amount_value * rate, 4),
                    'rate': rate,
                    'inverse_rate': inverse_rate,
                    'updated': updated,
                }
            )

        if __event_emitter__ and conversions:
            await __event_emitter__({'type': 'chat:message:currency', 'data': conversions[0]})

        response: dict = {
            'status': 'success',
            'message': 'Currency card displayed to the user.',
            'from': from_code,
            'amount': amount_value,
            'updated': updated,
        }
        if len(conversions) == 1:
            response['conversion'] = conversions[0]
        else:
            response['conversions'] = conversions

        return json.dumps(response, ensure_ascii=False)
    except Exception as e:
        log.exception(f'currency_convert error: {e}')
        return json.dumps({'error': str(e)})


# =============================================================================
# UTILITY LOOKUP, CONVERSION & DIFF TOOLS
# =============================================================================

_WIKIMEDIA_HEADERS = {'User-Agent': 'Open WebUI (https://github.com/open-webui/open-webui)'}

_TZ_ALIASES = {
    'utc': 'UTC',
    'gmt': 'Etc/GMT',
    'tokyo': 'Asia/Tokyo',
    'jst': 'Asia/Tokyo',
    'london': 'Europe/London',
    'uk': 'Europe/London',
    'paris': 'Europe/Paris',
    'berlin': 'Europe/Berlin',
    'new york': 'America/New_York',
    'nyc': 'America/New_York',
    'est': 'America/New_York',
    'edt': 'America/New_York',
    'los angeles': 'America/Los_Angeles',
    'la': 'America/Los_Angeles',
    'pst': 'America/Los_Angeles',
    'pdt': 'America/Los_Angeles',
    'chicago': 'America/Chicago',
    'cst': 'America/Chicago',
    'denver': 'America/Denver',
    'mst': 'America/Denver',
    'sydney': 'Australia/Sydney',
    'aest': 'Australia/Sydney',
    'singapore': 'Asia/Singapore',
    'hong kong': 'Asia/Hong_Kong',
    'dubai': 'Asia/Dubai',
    'mumbai': 'Asia/Kolkata',
    'ist': 'Asia/Kolkata',
    'beijing': 'Asia/Shanghai',
    'shanghai': 'Asia/Shanghai',
}

_LENGTH_TO_METERS = {
    'm': 1.0,
    'meter': 1.0,
    'meters': 1.0,
    'km': 1000.0,
    'kilometer': 1000.0,
    'kilometers': 1000.0,
    'cm': 0.01,
    'centimeter': 0.01,
    'centimeters': 0.01,
    'mm': 0.001,
    'millimeter': 0.001,
    'millimeters': 0.001,
    'mi': 1609.344,
    'mile': 1609.344,
    'miles': 1609.344,
    'ft': 0.3048,
    'foot': 0.3048,
    'feet': 0.3048,
    'in': 0.0254,
    'inch': 0.0254,
    'inches': 0.0254,
    'yd': 0.9144,
    'yard': 0.9144,
    'yards': 0.9144,
}

_WEIGHT_TO_KG = {
    'kg': 1.0,
    'kilogram': 1.0,
    'kilograms': 1.0,
    'g': 0.001,
    'gram': 0.001,
    'grams': 0.001,
    'mg': 0.000001,
    'milligram': 0.000001,
    'milligrams': 0.000001,
    'lb': 0.45359237,
    'lbs': 0.45359237,
    'pound': 0.45359237,
    'pounds': 0.45359237,
    'oz': 0.028349523125,
    'ounce': 0.028349523125,
    'ounces': 0.028349523125,
    'ton': 1000.0,
    'tons': 1000.0,
    'tonne': 1000.0,
    'tonnes': 1000.0,
}

_DATA_TO_BYTES = {
    'b': 1.0,
    'byte': 1.0,
    'bytes': 1.0,
    'kb': 1000.0,
    'kilobyte': 1000.0,
    'kilobytes': 1000.0,
    'mb': 1000.0**2,
    'megabyte': 1000.0**2,
    'megabytes': 1000.0**2,
    'gb': 1000.0**3,
    'gigabyte': 1000.0**3,
    'gigabytes': 1000.0**3,
    'tb': 1000.0**4,
    'terabyte': 1000.0**4,
    'terabytes': 1000.0**4,
    'kib': 1024.0,
    'mib': 1024.0**2,
    'gib': 1024.0**3,
    'tib': 1024.0**4,
}

_UNIT_CATEGORY_MAP = {
    **_LENGTH_TO_METERS,
    **_WEIGHT_TO_KG,
    **_DATA_TO_BYTES,
}

_DIFF_MAX_INPUT_CHARS = 200_000
_DIFF_MAX_OUTPUT_CHARS = 30_000


def _normalize_unit(unit: str) -> str:
    return re.sub(r'\s+', ' ', str(unit).strip().lower())


def _resolve_timezone_name(name: str) -> str:
    cleaned = str(name).strip()
    if not cleaned:
        raise ValueError('Timezone is required.')
    alias = _TZ_ALIASES.get(cleaned.lower())
    return alias or cleaned


def _convert_temperature(value: float, from_unit: str, to_unit: str) -> float:
    from_u = _normalize_unit(from_unit)
    to_u = _normalize_unit(to_unit)
    if from_u not in {'c', 'celsius', 'f', 'fahrenheit', 'k', 'kelvin'}:
        raise ValueError(f'Unsupported temperature unit: {from_unit}')
    if to_u not in {'c', 'celsius', 'f', 'fahrenheit', 'k', 'kelvin'}:
        raise ValueError(f'Unsupported temperature unit: {to_unit}')

    if from_u in {'c', 'celsius'}:
        celsius = value
    elif from_u in {'f', 'fahrenheit'}:
        celsius = (value - 32) * 5 / 9
    else:
        celsius = value - 273.15

    if to_u in {'c', 'celsius'}:
        return celsius
    if to_u in {'f', 'fahrenheit'}:
        return celsius * 9 / 5 + 32
    return celsius + 273.15


def _convert_scalar_unit(value: float, from_unit: str, to_unit: str) -> float:
    from_key = _normalize_unit(from_unit)
    to_key = _normalize_unit(to_unit)

    if from_key in {'c', 'celsius', 'f', 'fahrenheit', 'k', 'kelvin'}:
        return _convert_temperature(value, from_key, to_key)

    if from_key not in _UNIT_CATEGORY_MAP or to_key not in _UNIT_CATEGORY_MAP:
        raise ValueError(f'Unsupported unit conversion: {from_unit} -> {to_unit}')

    from_factor = _UNIT_CATEGORY_MAP[from_key]
    to_factor = _UNIT_CATEGORY_MAP[to_key]

    length_from = from_key in _LENGTH_TO_METERS
    length_to = to_key in _LENGTH_TO_METERS
    weight_from = from_key in _WEIGHT_TO_KG
    weight_to = to_key in _WEIGHT_TO_KG
    data_from = from_key in _DATA_TO_BYTES
    data_to = to_key in _DATA_TO_BYTES

    if length_from != length_to or weight_from != weight_to or data_from != data_to:
        raise ValueError(f'Incompatible units: {from_unit} -> {to_unit}')

    base_value = value * from_factor
    return base_value / to_factor


def _unit_category(unit: str) -> str:
    key = _normalize_unit(unit)
    if key in {'c', 'celsius', 'f', 'fahrenheit', 'k', 'kelvin'}:
        return 'temperature'
    if key in _LENGTH_TO_METERS:
        return 'length'
    if key in _WEIGHT_TO_KG:
        return 'weight'
    if key in _DATA_TO_BYTES:
        return 'data'
    raise ValueError(f'Unknown unit: {unit}')


async def _wiktionary_lookup(term: str, language: str = 'en') -> dict | None:
    from urllib.parse import quote

    encoded = quote(term.replace(' ', '_'))
    url = f'https://{language}.wiktionary.org/api/rest_v1/page/definition/{encoded}'
    try:
        payload = await _http_get_json(url, headers=_WIKIMEDIA_HEADERS)
    except Exception:
        return None

    if not isinstance(payload, list):
        return None

    entries = []
    for entry in payload[:3]:
        part = entry.get('partOfSpeech')
        definitions = []
        for definition in (entry.get('definitions') or [])[:3]:
            text = definition.get('definition')
            if text:
                definitions.append(re.sub(r'<[^>]+>', '', text).strip())
        if definitions:
            entries.append({'part_of_speech': part, 'definitions': definitions})

    if not entries:
        return None

    return {
        'source': 'wiktionary',
        'term': term,
        'language': language,
        'entries': entries,
    }


async def _wikidata_lookup(term: str, language: str = 'en') -> dict | None:
    search_payload = await _http_get_json(
        'https://www.wikidata.org/w/api.php',
        headers=_WIKIMEDIA_HEADERS,
        params={
            'action': 'wbsearchentities',
            'search': term,
            'language': language,
            'format': 'json',
            'limit': 3,
        },
    )
    results = search_payload.get('search') or []
    if not results:
        return None

    top = results[0]
    entity_id = top.get('id')
    description = top.get('description')
    label = top.get('label') or term
    aliases = top.get('aliases') or []

    entity_payload = None
    if entity_id:
        try:
            entity_payload = await _http_get_json(
                'https://www.wikidata.org/w/api.php',
                headers=_WIKIMEDIA_HEADERS,
                params={
                    'action': 'wbgetentities',
                    'ids': entity_id,
                    'props': 'descriptions|aliases|claims',
                    'languages': language,
                    'format': 'json',
                },
            )
        except Exception:
            entity_payload = None

    extra_description = description
    if entity_payload:
        entities = entity_payload.get('entities') or {}
        entity = entities.get(entity_id) or {}
        descriptions = entity.get('descriptions') or {}
        if language in descriptions and descriptions[language].get('value'):
            extra_description = descriptions[language]['value']
        entity_aliases = entity.get('aliases') or {}
        if language in entity_aliases:
            aliases = [item.get('value') for item in entity_aliases[language][:5] if item.get('value')]

    return {
        'source': 'wikidata',
        'term': label,
        'entity_id': entity_id,
        'description': extra_description,
        'aliases': aliases,
        'url': f'https://www.wikidata.org/wiki/{entity_id}' if entity_id else None,
    }


async def _load_file_text_content(
    file_id: str,
    request: Request,
    user: dict,
    model_knowledge: list[dict] | None,
) -> tuple[str, str]:
    from open_webui.models.files import Files

    file = await Files.get_file_by_id(file_id)
    if not file:
        raise ValueError('File not found')
    user_id = user.get('id')
    user_role = user.get('role', 'user')
    if not await _has_read_access_to_file(file, user_id, user_role, model_knowledge):
        raise ValueError('File not found')
    content = (file.data or {}).get('content', '') if file.data else ''
    return str(content), file.filename or file_id


async def _load_artifact_text_content(artifact_id: str, user: dict) -> tuple[str, str]:
    from open_webui.models.artifacts import Artifacts

    artifact = await Artifacts.get_artifact_by_id(artifact_id)
    if not artifact:
        raise ValueError('Artifact not found')
    user_id = user.get('id')
    if artifact.user_id != user_id and user.get('role') != 'admin':
        raise ValueError('Access denied')
    _artifact_type, content = _editable_artifact_content(artifact)
    return str(content), artifact.title or artifact_id


def _build_text_diff(
    text_a: str,
    text_b: str,
    *,
    label_a: str = 'a',
    label_b: str = 'b',
    context_lines: int = 3,
    max_output_chars: int = _DIFF_MAX_OUTPUT_CHARS,
) -> dict:
    import difflib

    if len(text_a) > _DIFF_MAX_INPUT_CHARS or len(text_b) > _DIFF_MAX_INPUT_CHARS:
        raise ValueError(f'Each input must be at most {_DIFF_MAX_INPUT_CHARS} characters.')

    matcher = difflib.SequenceMatcher(None, text_a, text_b)
    ratio = round(matcher.ratio(), 4)
    lines_a = text_a.splitlines()
    lines_b = text_b.splitlines()

    diff_lines = list(
        difflib.unified_diff(
            lines_a,
            lines_b,
            fromfile=label_a,
            tofile=label_b,
            n=max(0, int(context_lines or 3)),
            lineterm='',
        )
    )
    diff_text = '\n'.join(diff_lines)
    truncated = False
    if len(diff_text) > max_output_chars:
        diff_text = diff_text[:max_output_chars] + '\n... [diff truncated]'
        truncated = True

    additions = sum(1 for line in diff_lines if line.startswith('+') and not line.startswith('+++'))
    deletions = sum(1 for line in diff_lines if line.startswith('-') and not line.startswith('---'))

    return {
        'label_a': label_a,
        'label_b': label_b,
        'similarity': ratio,
        'additions': additions,
        'deletions': deletions,
        'identical': ratio == 1.0 and text_a == text_b,
        'diff': diff_text,
        'truncated': truncated,
    }


def _json_value_type(value) -> str:
    if value is None:
        return 'null'
    if isinstance(value, bool):
        return 'boolean'
    if isinstance(value, int) and not isinstance(value, bool):
        return 'integer'
    if isinstance(value, float):
        return 'number'
    if isinstance(value, str):
        return 'string'
    if isinstance(value, list):
        return 'array'
    if isinstance(value, dict):
        return 'object'
    return type(value).__name__


def _format_json_text(
    text: str,
    *,
    action: str = 'pretty',
    indent: int = 2,
    sort_keys: bool = False,
) -> dict:
    try:
        parsed = json.loads(text)
    except json.JSONDecodeError as exc:
        return {
            'valid': False,
            'error': str(exc),
            'line': exc.lineno,
            'column': exc.colno,
            'position': exc.pos,
        }

    result = {
        'valid': True,
        'type': _json_value_type(parsed),
        'action': action,
    }

    if action == 'validate':
        if isinstance(parsed, dict):
            result['keys'] = len(parsed)
        elif isinstance(parsed, list):
            result['length'] = len(parsed)
        return result

    if action == 'minify':
        result['formatted'] = json.dumps(parsed, ensure_ascii=False, separators=(',', ':'), sort_keys=sort_keys)
        return result

    safe_indent = max(0, min(int(indent), 8))
    result['formatted'] = json.dumps(
        parsed,
        ensure_ascii=False,
        indent=safe_indent if safe_indent else None,
        sort_keys=sort_keys,
    )
    return result


def _clamp_byte(value: float) -> int:
    return max(0, min(255, int(round(value))))


def _parse_hex_color(color: str) -> tuple[int, int, int, float | None]:
    hex_digits = color.lstrip('#')
    if len(hex_digits) == 3:
        hex_digits = ''.join(ch * 2 for ch in hex_digits)
    if len(hex_digits) == 4:
        hex_digits = ''.join(ch * 2 for ch in hex_digits)
    if len(hex_digits) == 6:
        r = int(hex_digits[0:2], 16)
        g = int(hex_digits[2:4], 16)
        b = int(hex_digits[4:6], 16)
        return r, g, b, None
    if len(hex_digits) == 8:
        r = int(hex_digits[0:2], 16)
        g = int(hex_digits[2:4], 16)
        b = int(hex_digits[4:6], 16)
        a = int(hex_digits[6:8], 16) / 255
        return r, g, b, a
    raise ValueError(f'Invalid hex color: {color}')


def _parse_function_color(color: str) -> tuple[int, int, int, float | None]:
    match = re.match(
        r'^(rgba?|hsla?)\s*\(\s*([^)]+)\)$',
        color.strip(),
        flags=re.IGNORECASE,
    )
    if not match:
        raise ValueError(f'Unsupported color format: {color}')

    fn = match.group(1).lower()
    parts = [part.strip() for part in match.group(2).split(',')]
    if fn == 'rgb' and len(parts) == 3:
        return int(parts[0]), int(parts[1]), int(parts[2]), None
    if fn == 'rgba' and len(parts) == 4:
        alpha = float(parts[3].rstrip('%')) / 100 if parts[3].endswith('%') else float(parts[3])
        return int(parts[0]), int(parts[1]), int(parts[2]), alpha
    if fn == 'hsl' and len(parts) == 3:
        rgb = _hsl_to_rgb(float(parts[0]), _parse_percent(parts[1]), _parse_percent(parts[2]))
        return rgb[0], rgb[1], rgb[2], None
    if fn == 'hsla' and len(parts) == 4:
        rgb = _hsl_to_rgb(float(parts[0]), _parse_percent(parts[1]), _parse_percent(parts[2]))
        alpha = float(parts[3].rstrip('%')) / 100 if parts[3].endswith('%') else float(parts[3])
        return rgb[0], rgb[1], rgb[2], alpha
    raise ValueError(f'Unsupported color format: {color}')


def _parse_percent(value: str) -> float:
    text = value.strip()
    if text.endswith('%'):
        return float(text[:-1])
    return float(text)


def _parse_color_string(color: str) -> tuple[int, int, int, float | None]:
    cleaned = str(color).strip()
    if not cleaned:
        raise ValueError('color is required.')
    if cleaned.startswith('#'):
        return _parse_hex_color(cleaned)
    if cleaned.lower().startswith(('rgb', 'hsl')):
        return _parse_function_color(cleaned)
    if re.fullmatch(r'[0-9a-fA-F]{3,8}', cleaned):
        return _parse_hex_color(f'#{cleaned}')
    raise ValueError(f'Unsupported color format: {color}')


def _rgb_to_hsl(red: int, green: int, blue: int) -> tuple[float, float, float]:
    r = red / 255.0
    g = green / 255.0
    b = blue / 255.0
    max_c = max(r, g, b)
    min_c = min(r, g, b)
    lightness = (max_c + min_c) / 2
    if max_c == min_c:
        return 0.0, 0.0, round(lightness * 100, 2)

    delta = max_c - min_c
    saturation = delta / (2 - max_c - min_c) if lightness > 0.5 else delta / (max_c + min_c)
    if max_c == r:
        hue = ((g - b) / delta) % 6
    elif max_c == g:
        hue = ((b - r) / delta) + 2
    else:
        hue = ((r - g) / delta) + 4
    hue *= 60
    return round(hue, 2), round(saturation * 100, 2), round(lightness * 100, 2)


def _hsl_to_rgb(hue: float, saturation: float, lightness: float) -> tuple[int, int, int]:
    h = (hue % 360) / 360
    s = saturation / 100
    l = lightness / 100
    if s == 0:
        value = _clamp_byte(l * 255)
        return value, value, value

    def hue_to_rgb(p: float, q: float, t: float) -> float:
        if t < 0:
            t += 1
        if t > 1:
            t -= 1
        if t < 1 / 6:
            return p + (q - p) * 6 * t
        if t < 1 / 2:
            return q
        if t < 2 / 3:
            return p + (q - p) * (2 / 3 - t) * 6
        return p

    q = l * (1 + s) if l < 0.5 else l + s - l * s
    p = 2 * l - q
    red = hue_to_rgb(p, q, h + 1 / 3)
    green = hue_to_rgb(p, q, h)
    blue = hue_to_rgb(p, q, h - 1 / 3)
    return _clamp_byte(red * 255), _clamp_byte(green * 255), _clamp_byte(blue * 255)


def _color_to_hex(red: int, green: int, blue: int, alpha: float | None = None) -> str:
    if alpha is None:
        return f'#{red:02x}{green:02x}{blue:02x}'
    return f'#{red:02x}{green:02x}{blue:02x}{_clamp_byte(alpha * 255):02x}'


def _color_to_rgb(red: int, green: int, blue: int, alpha: float | None = None) -> str:
    if alpha is None:
        return f'rgb({red}, {green}, {blue})'
    return f'rgba({red}, {green}, {blue}, {round(alpha, 4)})'


def _color_to_hsl(red: int, green: int, blue: int, alpha: float | None = None) -> str:
    hue, saturation, lightness = _rgb_to_hsl(red, green, blue)
    if alpha is None:
        return f'hsl({hue}, {saturation}%, {lightness}%)'
    return f'hsla({hue}, {saturation}%, {lightness}%, {round(alpha, 4)})'


def _convert_color_formats(color: str, to_format: str = 'all') -> dict:
    red, green, blue, alpha = _parse_color_string(color)
    hue, saturation, lightness = _rgb_to_hsl(red, green, blue)
    formats = {
        'hex': _color_to_hex(red, green, blue, alpha),
        'rgb': _color_to_rgb(red, green, blue, alpha),
        'hsl': _color_to_hsl(red, green, blue, alpha),
        'rgba': {'r': red, 'g': green, 'b': blue, 'a': alpha},
        'hsl_values': {'h': hue, 's': saturation, 'l': lightness},
    }
    target = (to_format or 'all').strip().lower()
    if target == 'all':
        return {'input': color, 'formats': formats}
    if target not in {'hex', 'rgb', 'hsl'}:
        raise ValueError('to_format must be hex, rgb, hsl, or all.')
    return {'input': color, 'format': target, 'value': formats[target]}


async def define_term(
    term: str,
    language: str = 'en',
) -> str:
    """
    Look up a word or concept using Wiktionary and Wikidata for fast factual grounding.

    Prefer this over web search for definitions, etymology, and concise entity descriptions.

    :param term: The word or phrase to define
    :param language: Language code for results (default: en)
    :return: JSON with Wiktionary definitions and Wikidata entity summary when available
    """
    try:
        cleaned = str(term).strip()
        if not cleaned:
            return json.dumps({'error': 'term is required.'})

        lang = (language or 'en').strip().lower()[:5] or 'en'
        wiktionary = await _wiktionary_lookup(cleaned, language=lang)
        wikidata = await _wikidata_lookup(cleaned, language=lang)

        if not wiktionary and not wikidata:
            return json.dumps(
                {
                    'term': cleaned,
                    'error': f'No Wiktionary or Wikidata results found for "{cleaned}".',
                },
                ensure_ascii=False,
            )

        payload = {'term': cleaned, 'language': lang}
        if wiktionary:
            payload['wiktionary'] = wiktionary
        if wikidata:
            payload['wikidata'] = wikidata
        return json.dumps(payload, ensure_ascii=False)
    except Exception as e:
        log.exception(f'define_term error: {e}')
        return json.dumps({'error': str(e)})


async def unit_convert(
    amount: float,
    from_unit: str,
    to_unit: str,
) -> str:
    """
    Convert a value between compatible units (length, weight, temperature, or data sizes).

    Examples: meters to feet, celsius to fahrenheit, GB to GiB, kg to lb.

    :param amount: Numeric value to convert
    :param from_unit: Source unit (e.g. km, lb, c, gb, mib)
    :param to_unit: Target unit (e.g. mi, kg, f, gib)
    :return: JSON with converted result and unit category
    """
    try:
        result_value = _convert_scalar_unit(float(amount), from_unit, to_unit)
        category = _unit_category(from_unit)
        return json.dumps(
            {
                'amount': float(amount),
                'from_unit': _normalize_unit(from_unit),
                'to_unit': _normalize_unit(to_unit),
                'category': category,
                'result': round(result_value, 8),
            },
            ensure_ascii=False,
        )
    except Exception as e:
        log.exception(f'unit_convert error: {e}')
        return json.dumps({'error': str(e)})


async def json_format(
    text: str,
    action: str = 'pretty',
    indent: int = 2,
    sort_keys: bool = False,
) -> str:
    """
    Validate, pretty-print, or minify JSON text.

    :param text: Raw JSON string to process
    :param action: pretty (default), minify, or validate
    :param indent: Spaces per level when pretty-printing (default: 2, max: 8)
    :param sort_keys: Sort object keys alphabetically when formatting
    :return: JSON with validation result and formatted output when applicable
    """
    try:
        if not str(text).strip():
            return json.dumps({'error': 'text is required.'})

        normalized_action = (action or 'pretty').strip().lower()
        if normalized_action not in {'pretty', 'minify', 'validate'}:
            normalized_action = 'pretty'

        if isinstance(sort_keys, str):
            sort_keys = sort_keys.strip().lower() in {'true', '1', 'yes', 'on'}
        if isinstance(indent, str):
            try:
                indent = int(indent)
            except ValueError:
                indent = 2

        result = _format_json_text(
            str(text),
            action=normalized_action,
            indent=indent,
            sort_keys=bool(sort_keys),
        )
        return json.dumps(result, ensure_ascii=False)
    except Exception as e:
        log.exception(f'json_format error: {e}')
        return json.dumps({'error': str(e)})


async def color_convert(
    color: str,
    to_format: Optional[str] = 'all',
) -> str:
    """
    Convert a color between hex, rgb/rgba, and hsl/hsla.

    Accepts #hex, rgb(), rgba(), hsl(), and hsla() inputs.

    :param color: Color string to convert
    :param to_format: Target format: hex, rgb, hsl, or all (default)
    :return: JSON with converted color value(s)
    """
    try:
        result = _convert_color_formats(color, to_format or 'all')
        return json.dumps(result, ensure_ascii=False)
    except Exception as e:
        log.exception(f'color_convert error: {e}')
        return json.dumps({'error': str(e)})


async def timezone_convert(
    time: str,
    from_timezone: str,
    to_timezone: Optional[str] = None,
    date: Optional[str] = None,
    __user__: dict = None,
) -> str:
    """
    Convert a local time from one timezone to another.

    Use for questions like "what is 3pm Tokyo in my time?". Defaults to the user's
    profile timezone when to_timezone is omitted.

    :param time: Local time as HH:MM, HH:MM:SS, or ISO-8601 datetime
    :param from_timezone: Source IANA timezone or common alias (e.g. Asia/Tokyo, Tokyo, UTC)
    :param to_timezone: Target timezone (defaults to user profile timezone, else UTC)
    :param date: Optional YYYY-MM-DD for clock times without a date (defaults to today in source tz)
    :return: JSON with converted ISO timestamps and timezone labels
    """
    try:
        import datetime
        from zoneinfo import ZoneInfo

        if not str(time).strip():
            return json.dumps({'error': 'time is required.'})
        if not str(from_timezone).strip():
            return json.dumps({'error': 'from_timezone is required.'})

        from_tz = ZoneInfo(_resolve_timezone_name(from_timezone))
        target_name = to_timezone or (__user__ or {}).get('timezone') or 'UTC'
        to_tz = ZoneInfo(_resolve_timezone_name(target_name))

        raw_time = str(time).strip()
        parsed: datetime.datetime | None = None

        try:
            if 'T' in raw_time or raw_time.endswith('Z') or '+' in raw_time[10:]:
                parsed = datetime.datetime.fromisoformat(raw_time.replace('Z', '+00:00'))
                if parsed.tzinfo is None:
                    parsed = parsed.replace(tzinfo=from_tz)
                else:
                    parsed = parsed.astimezone(from_tz)
            else:
                time_part = raw_time
                date_part = (date or '').strip()
                if not date_part:
                    date_part = datetime.datetime.now(from_tz).date().isoformat()
                parsed = datetime.datetime.fromisoformat(f'{date_part}T{time_part}')
                parsed = parsed.replace(tzinfo=from_tz)
        except ValueError as exc:
            return json.dumps({'error': f'Could not parse time "{time}": {exc}'})

        converted = parsed.astimezone(to_tz)
        return json.dumps(
            {
                'input': {
                    'local_iso': parsed.isoformat(),
                    'timezone': str(from_tz),
                },
                'output': {
                    'local_iso': converted.isoformat(),
                    'timezone': str(to_tz),
                },
                'utc_iso': converted.astimezone(datetime.timezone.utc).isoformat(),
            },
            ensure_ascii=False,
        )
    except Exception as e:
        log.exception(f'timezone_convert error: {e}')
        return json.dumps({'error': str(e)})


async def diff_text(
    text_a: Optional[str] = None,
    text_b: Optional[str] = None,
    file_id_a: Optional[str] = None,
    file_id_b: Optional[str] = None,
    artifact_id_a: Optional[str] = None,
    artifact_id_b: Optional[str] = None,
    label_a: Optional[str] = None,
    label_b: Optional[str] = None,
    context_lines: int = 3,
    __request__: Request = None,
    __user__: dict = None,
    __model_knowledge__: list[dict] = None,
) -> str:
    """
    Compare two text sources and return a unified diff.

    Pass inline text and/or file/artifact ids. Useful for code review and document comparison.

    :param text_a: First text (optional if file_id_a or artifact_id_a provided)
    :param text_b: Second text (optional if file_id_b or artifact_id_b provided)
    :param file_id_a: First uploaded file id
    :param file_id_b: Second uploaded file id
    :param artifact_id_a: First saved artifact id
    :param artifact_id_b: Second saved artifact id
    :param label_a: Optional label for the first side in the diff
    :param label_b: Optional label for the second side in the diff
    :param context_lines: Unified diff context lines (default: 3)
    :return: JSON with unified diff, similarity ratio, and change counts
    """
    if __request__ is None:
        return json.dumps({'error': 'Request context not available'})
    if not __user__:
        return json.dumps({'error': 'User context not available'})

    try:
        left_text = text_a
        left_label = label_a
        right_text = text_b
        right_label = label_b

        if file_id_a:
            loaded_text, loaded_label = await _load_file_text_content(
                file_id_a, __request__, __user__, __model_knowledge__
            )
            left_text = loaded_text
            left_label = left_label or loaded_label
        if artifact_id_a:
            loaded_text, loaded_label = await _load_artifact_text_content(artifact_id_a, __user__)
            left_text = loaded_text
            left_label = left_label or loaded_label

        if file_id_b:
            loaded_text, loaded_label = await _load_file_text_content(
                file_id_b, __request__, __user__, __model_knowledge__
            )
            right_text = loaded_text
            right_label = right_label or loaded_label
        if artifact_id_b:
            loaded_text, loaded_label = await _load_artifact_text_content(artifact_id_b, __user__)
            right_text = loaded_text
            right_label = right_label or loaded_label

        if left_text is None or right_text is None:
            return json.dumps({'error': 'Provide text_a/text_b or matching file/artifact ids for both sides.'})

        result = _build_text_diff(
            str(left_text),
            str(right_text),
            label_a=left_label or 'a',
            label_b=right_label or 'b',
            context_lines=context_lines,
        )
        return json.dumps(result, ensure_ascii=False)
    except Exception as e:
        log.exception(f'diff_text error: {e}')
        return json.dumps({'error': str(e)})


async def _geocode_nominatim(query: str) -> dict | None:
    payload = await _http_get_json(
        'https://nominatim.openstreetmap.org/search',
        headers={'User-Agent': 'Open WebUI (https://github.com/open-webui/open-webui)'},
        params={'q': query, 'format': 'json', 'limit': 1},
    )
    if isinstance(payload, list) and payload:
        item = payload[0]
        return {
            'lat': float(item['lat']),
            'lng': float(item['lon']),
            'label': item.get('display_name', query),
        }
    return None


async def map_display(
    location: str | dict,
    zoom: Optional[int] = 13,
    markers: Optional[list[dict]] = None,
    __event_emitter__: callable = None,
) -> str:
    """
    Display an interactive map with one or more location markers.

    :param location: Place name or dict with lat/lng keys
    :param zoom: Map zoom level (default 13)
    :param markers: Optional list of {lat, lng, label} marker dicts
    :return: Confirmation that the map was displayed
    """
    try:
        lat = None
        lng = None
        label = None

        if isinstance(location, dict):
            lat = location.get('lat', location.get('latitude'))
            lng = location.get('lng', location.get('longitude'))
            label = location.get('label') or location.get('name')
        else:
            geo = await _geocode_nominatim(str(location).strip())
            if not geo:
                return json.dumps({'error': f'Could not find location: {location}'})
            lat = geo['lat']
            lng = geo['lng']
            label = geo['label']

        if lat is None or lng is None:
            return json.dumps({'error': 'Valid location with lat/lng is required.'})

        marker_list = []
        for marker in markers or []:
            if isinstance(marker, dict):
                m_lat = marker.get('lat', marker.get('latitude'))
                m_lng = marker.get('lng', marker.get('longitude'))
                if m_lat is not None and m_lng is not None:
                    marker_list.append(
                        {
                            'lat': float(m_lat),
                            'lng': float(m_lng),
                            'label': marker.get('label') or marker.get('name') or '',
                        }
                    )

        if not marker_list:
            marker_list = [{'lat': float(lat), 'lng': float(lng), 'label': label or str(location)}]

        map_data = {
            'lat': float(lat),
            'lng': float(lng),
            'zoom': int(zoom or 13),
            'label': label or str(location),
            'markers': marker_list,
        }

        if __event_emitter__:
            await __event_emitter__({'type': 'chat:message:map', 'data': map_data})

        return json.dumps(
            {
                'status': 'success',
                'message': 'Map displayed to the user.',
                'map': map_data,
            },
            ensure_ascii=False,
        )
    except Exception as e:
        log.exception(f'map_display error: {e}')
        return json.dumps({'error': str(e)})


async def sports_scores(
    team_name: str,
    __event_emitter__: callable = None,
) -> str:
    """
    Fetch recent results and upcoming fixtures for a sports team.

    :param team_name: The team name to look up
    :return: JSON summary of recent and upcoming matches
    """
    try:
        search_payload = await _http_get_json(
            'https://www.thesportsdb.com/api/v1/json/3/searchteams.php',
            params={'t': team_name},
        )
        teams = search_payload.get('teams') or []
        if not teams:
            return json.dumps({'error': f'No team found matching: {team_name}'})

        team = teams[0]
        team_id = team.get('idTeam')
        team_label = team.get('strTeam', team_name)
        league = team.get('strLeague', '')

        last_payload = await _http_get_json(
            'https://www.thesportsdb.com/api/v1/json/3/eventslast.php',
            params={'id': team_id},
        )
        next_payload = await _http_get_json(
            'https://www.thesportsdb.com/api/v1/json/3/eventsnext.php',
            params={'id': team_id},
        )

        def _format_event(event: dict, team_label: str) -> dict:
            home = event.get('strHomeTeam', '')
            away = event.get('strAwayTeam', '')
            is_home = home.lower() == team_label.lower()
            opponent = away if is_home else home
            score = None
            if event.get('intHomeScore') is not None and event.get('intAwayScore') is not None:
                score = f"{event.get('intHomeScore')}-{event.get('intAwayScore')}"
            return {
                'opponent': opponent,
                'home': home,
                'away': away,
                'score': score,
                'date': event.get('dateEvent') or event.get('strTimestamp'),
                'competition': event.get('strLeague') or league,
                'venue': event.get('strVenue'),
            }

        recent = [_format_event(e, team_label) for e in (last_payload.get('results') or [])[:5]]
        upcoming = [_format_event(e, team_label) for e in (next_payload.get('events') or [])[:5]]

        sports_data = {
            'team': team_label,
            'league': league,
            'badge': team.get('strBadge') or team.get('strTeamBadge'),
            'recent': recent,
            'upcoming': upcoming,
        }

        if __event_emitter__:
            await __event_emitter__({'type': 'chat:message:sports', 'data': sports_data})

        return json.dumps(
            {
                'status': 'success',
                'message': 'Sports scores card displayed to the user.',
                'sports': sports_data,
            },
            ensure_ascii=False,
        )
    except Exception as e:
        log.exception(f'sports_scores error: {e}')
        return json.dumps({'error': str(e)})


async def suggest_followups(
    suggestions: list[str],
    __event_emitter__: callable = None,
) -> str:
    """
    Show 2–3 suggested follow-up prompts as tappable chips at the end of a response.

    :param suggestions: List of 2–3 short follow-up prompt strings
    :return: Confirmation that follow-up chips were displayed
    """
    try:
        items = [str(s).strip() for s in (suggestions or []) if str(s).strip()]
        if len(items) < 2:
            return json.dumps({'error': 'Provide at least 2 follow-up suggestions.'})
        if len(items) > 3:
            items = items[:3]

        if __event_emitter__:
            await __event_emitter__(
                {
                    'type': 'chat:message:followups',
                    'data': {'suggestions': items},
                }
            )

        return json.dumps(
            {
                'status': 'success',
                'message': 'Follow-up chips displayed. Do not repeat them in prose.',
            },
            ensure_ascii=False,
        )
    except Exception as e:
        log.exception(f'suggest_followups error: {e}')
        return json.dumps({'error': str(e)})


# =============================================================================
# ARTIFACT TOOLS (saved library)
# =============================================================================


def _parse_artifact_meta(meta: Optional[str]) -> dict:
    if not meta:
        return {}
    try:
        parsed = json.loads(meta)
        return parsed if isinstance(parsed, dict) else {}
    except Exception:
        return {}


_ARTIFACT_IN_CHAT_BUILD_ERROR = (
    'Do not use artifact library tools for new build/create/make requests. '
    'Output the full source in an <antArtifact> tag in your chat response instead. '
    'list_artifacts / read_artifact / update_artifact are only for artifacts the user '
    'explicitly asked to edit in their saved library (e.g. "update my saved clicker game"). '
    'In-chat revisions reuse the same <antArtifact identifier="…"> — no library tool calls.'
)


def _artifact_library_tool_allowed(user_prompt: Optional[str]) -> bool:
    """Block library artifact writes when the user asked for a new in-chat build."""
    if not user_prompt or not str(user_prompt).strip():
        return True

    prompt = str(user_prompt).lower()

    library_cues = (
        'saved artifact',
        'saved game',
        'my library',
        'artifact library',
        'published artifact',
        'in my library',
        'from my library',
        'previously saved',
        'saved to',
    )
    if any(cue in prompt for cue in library_cues):
        return True

    if re.search(r'\b(update|edit|modify|revise|change|fix)\s+(my|the)\s+saved\b', prompt):
        return True

    build_cues = (
        'build me',
        'build a',
        'build an',
        'create a',
        'create me',
        'create an',
        'make me',
        'make a',
        'make an',
        'write me',
        'write a',
        'write an',
        'design a',
        'design me',
        'code me',
        'code a',
        'generate a',
        'generate me',
        'in chat',
        'using react',
        'using tailwind',
        'with react',
        'with tailwind',
    )
    if any(cue in prompt for cue in build_cues):
        return False

    return True


def _prepare_artifact_storage(content: str, artifact_type: str) -> tuple[str, str, Optional[str]]:
    normalized = (artifact_type or 'iframe').lower().strip()
    if normalized == 'react':
        from open_webui.utils.react_artifact import build_react_html

        meta = json.dumps(
            {
                'mime_type': 'application/vnd.ant.react',
                'react_source': content,
            },
            ensure_ascii=False,
        )
        return 'iframe', build_react_html(content), meta
    if normalized == 'markdown':
        meta = json.dumps({'mime_type': 'text/markdown'}, ensure_ascii=False)
        return 'markdown', content, meta
    if normalized == 'svg':
        return 'svg', content, None
    return 'iframe', content, None


def _editable_artifact_content(artifact) -> tuple[str, str]:
    meta = _parse_artifact_meta(artifact.meta)
    if meta.get('react_source'):
        return 'react', meta['react_source']
    if meta.get('mime_type') == 'text/markdown' or artifact.type == 'markdown':
        return 'markdown', artifact.code
    if artifact.type == 'svg':
        return 'svg', artifact.code
    return 'iframe', artifact.code


async def _artifacts_access_error(__request__: Request = None, __user__: dict = None) -> Optional[str]:
    if __request__ is None:
        return 'Request context not available'
    if not __user__:
        return 'User context not available'
    if not await Config.get('artifacts.enable'):
        return 'Artifacts feature is disabled'
    if __user__.get('role') == 'admin':
        return None
    from open_webui.utils.access_control import has_permission

    if not await has_permission(
        __user__.get('id'),
        'features.artifacts',
        await Config.get('user.permissions'),
    ):
        return 'Access denied — artifacts permission required'
    return None


async def list_artifacts(
    count: int = 50,
    __request__: Request = None,
    __user__: dict = None,
    __metadata__: dict = None,
) -> str:
    """
    List artifacts in the user's saved library (published via the panel Save button).

    Do NOT call for new build/create/make requests — output <antArtifact> in chat instead.
    Only call when the user explicitly refers to their saved/published library.

    :param count: Maximum number of artifacts to return (default: 50)
    :return: JSON list with id, title, type, artifact_type, updated_at
    """
    if err := await _artifacts_access_error(__request__, __user__):
        return json.dumps({'error': err})

    user_prompt = (__metadata__ or {}).get('user_prompt')
    if not _artifact_library_tool_allowed(user_prompt):
        return json.dumps({'error': _ARTIFACT_IN_CHAT_BUILD_ERROR})

    try:
        from open_webui.models.artifacts import Artifacts

        user_id = __user__.get('id')
        count = max(1, min(int(count or 50), 50))
        artifacts = await Artifacts.get_artifacts_by_user_id(user_id, skip=0, limit=count)

        results = []
        for artifact in artifacts:
            artifact_type, _ = _editable_artifact_content(artifact)
            results.append(
                {
                    'id': artifact.id,
                    'title': artifact.title,
                    'type': artifact.type,
                    'artifact_type': artifact_type,
                    'chat_id': artifact.chat_id,
                    'updated_at': artifact.updated_at,
                }
            )

        return json.dumps(results, ensure_ascii=False)
    except Exception as e:
        log.exception(f'list_artifacts error: {e}')
        return json.dumps({'error': str(e)})


async def read_artifact(
    artifact_id: str,
    __request__: Request = None,
    __user__: dict = None,
    __metadata__: dict = None,
) -> str:
    """
    Read editable source of an artifact already in the user's saved library.

    Do NOT call for new build/create/make requests — output <antArtifact> in chat instead.
    Call only after list_artifacts when the user asked to edit a specific saved artifact.

    :param artifact_id: The artifact ID from list_artifacts
    :return: JSON with id, title, type, artifact_type, and content (editable source)
    """
    if err := await _artifacts_access_error(__request__, __user__):
        return json.dumps({'error': err})

    user_prompt = (__metadata__ or {}).get('user_prompt')
    if not _artifact_library_tool_allowed(user_prompt):
        return json.dumps({'error': _ARTIFACT_IN_CHAT_BUILD_ERROR})

    try:
        from open_webui.models.artifacts import Artifacts

        artifact = await Artifacts.get_artifact_by_id(artifact_id)
        if not artifact:
            return json.dumps({'error': 'Artifact not found'})

        user_id = __user__.get('id')
        if artifact.user_id != user_id and __user__.get('role') != 'admin':
            return json.dumps({'error': 'Access denied'})

        artifact_type, content = _editable_artifact_content(artifact)

        return json.dumps(
            {
                'id': artifact.id,
                'title': artifact.title,
                'type': artifact.type,
                'artifact_type': artifact_type,
                'content': content,
                'chat_id': artifact.chat_id,
                'updated_at': artifact.updated_at,
            },
            ensure_ascii=False,
        )
    except Exception as e:
        log.exception(f'read_artifact error: {e}')
        return json.dumps({'error': str(e)})


async def update_artifact(
    artifact_id: str,
    content: str,
    title: Optional[str] = None,
    artifact_type: Optional[str] = None,
    __request__: Request = None,
    __user__: dict = None,
    __metadata__: dict = None,
) -> str:
    """
    Replace source of an artifact already in the user's saved library.

    NEVER use for build/create/make requests — output <antArtifact> in chat instead.
    NEVER use to deliver new interactive content. Only when the user explicitly asked
    to edit a saved/published library artifact. Requires list_artifacts → read_artifact first.
    After updating, also output an <antArtifact> tag so the in-chat panel refreshes.

    :param artifact_id: The artifact ID to update
    :param content: Complete replacement source (not a diff)
    :param title: Optional new title
    :param artifact_type: Optional type override: iframe, svg, react, or markdown
    :return: JSON with updated artifact metadata
    """
    if err := await _artifacts_access_error(__request__, __user__):
        return json.dumps({'error': err})

    user_prompt = (__metadata__ or {}).get('user_prompt')
    if not _artifact_library_tool_allowed(user_prompt):
        return json.dumps({'error': _ARTIFACT_IN_CHAT_BUILD_ERROR})

    if not content or not str(content).strip():
        return json.dumps({'error': 'Content is required'})

    try:
        from open_webui.models.artifacts import ArtifactUpdateForm, Artifacts

        existing = await Artifacts.get_artifact_by_id(artifact_id)
        if not existing:
            return json.dumps({'error': 'Artifact not found'})

        user_id = __user__.get('id')
        if existing.user_id != user_id and __user__.get('role') != 'admin':
            return json.dumps({'error': 'Access denied'})

        resolved_type = artifact_type
        if not resolved_type:
            resolved_type, _ = _editable_artifact_content(existing)

        db_type, code, meta = _prepare_artifact_storage(str(content), resolved_type)
        form = ArtifactUpdateForm(
            title=title.strip() if title else None,
            type=db_type,
            code=code,
            meta=meta,
        )
        updated = await Artifacts.update_artifact_by_id(artifact_id, form)
        if not updated:
            return json.dumps({'error': 'Failed to update artifact'})

        saved_type, editable = _editable_artifact_content(updated)
        return json.dumps(
            {
                'status': 'success',
                'id': updated.id,
                'title': updated.title,
                'type': updated.type,
                'artifact_type': saved_type,
                'content': editable,
                'message': 'Artifact updated. Output an <antArtifact> tag to refresh the panel.',
            },
            ensure_ascii=False,
        )
    except Exception as e:
        log.exception(f'update_artifact error: {e}')
        return json.dumps({'error': str(e)})


async def delete_artifact(
    artifact_id: str,
    __request__: Request = None,
    __user__: dict = None,
) -> str:
    """
    Delete (unpublish) a saved artifact from the user's library.

    :param artifact_id: The artifact ID to delete
    :return: JSON with deletion status
    """
    if err := await _artifacts_access_error(__request__, __user__):
        return json.dumps({'error': err})

    try:
        from open_webui.models.artifacts import Artifacts

        existing = await Artifacts.get_artifact_by_id(artifact_id)
        if not existing:
            return json.dumps({'error': 'Artifact not found'})

        user_id = __user__.get('id')
        if existing.user_id != user_id and __user__.get('role') != 'admin':
            return json.dumps({'error': 'Access denied'})

        await Artifacts.delete_artifact_by_id(artifact_id)
        return json.dumps(
            {'status': 'success', 'id': artifact_id, 'deleted': True},
            ensure_ascii=False,
        )
    except Exception as e:
        log.exception(f'delete_artifact error: {e}')
        return json.dumps({'error': str(e)})
