"""
Verified context token breakdown for llama.cpp via /apply-template + /tokenize.
"""

from __future__ import annotations

import asyncio
import copy
import logging
import time
from typing import Any

import aiohttp

from open_webui.env import AIOHTTP_CLIENT_SESSION_SSL

log = logging.getLogger(__name__)

LLAMACPP_CONVERSATION_ID_HEADER = 'X-Conversation-Id'

REASONING_EFFORT_TOKEN_BUDGETS: dict[str, int] = {
    'low': 512,
    'medium': 2048,
    'high': 8192,
    'max': -1,
}

DEFAULT_THINKING_EFFORT = 'medium'

BREAKDOWN_TIMEOUT_SECONDS = 2.0
CAPABILITY_CACHE_TTL_SECONDS = 600

_capability_cache: dict[str, tuple[bool, float]] = {}
_layer_count_cache: dict[str, tuple[dict, float]] = {}

TOOL_SOURCE_KEYS = ('user', 'builtin', 'mcp', 'external', 'terminal')


def llamacpp_conversation_id(chat_id: str | None, model_id: str | None = None) -> str | None:
    if not chat_id or chat_id.startswith('local:') or chat_id.startswith('channel:'):
        return None
    if model_id:
        return f'{chat_id}::{model_id}'
    return chat_id


def reasoning_effort_to_budget_tokens(effort: str | None) -> int | None:
    if effort is None:
        return None
    normalized = str(effort).strip().lower()
    if normalized in ('', 'none', 'off', 'false'):
        return 0
    if normalized in REASONING_EFFORT_TOKEN_BUDGETS:
        return REASONING_EFFORT_TOKEN_BUDGETS[normalized]
    return None


def openrouter_reasoning_payload(form_data: dict) -> dict | bool | None:
    kwargs = dict(form_data.get('chat_template_kwargs') or {})
    enable_thinking = kwargs.get('enable_thinking')
    effort = form_data.get('reasoning_effort')

    if enable_thinking is False:
        return {'enabled': False, 'effort': 'none'}

    if effort is not None:
        normalized = str(effort).strip().lower()
        if normalized in ('', 'none', 'off', 'false'):
            return {'enabled': False, 'effort': 'none'}
        return {'enabled': True, 'effort': normalized}

    if enable_thinking is True:
        return {'enabled': True, 'effort': 'medium'}

    return None


def _set_thinking_budget(form_data: dict, budget: int) -> None:
    form_data['thinking_budget_tokens'] = budget
    form_data['reasoning_budget_tokens'] = budget


def _explicit_thinking_budget(form_data: dict) -> int | None:
    for key in ('thinking_budget_tokens', 'reasoning_budget_tokens'):
        value = form_data.get(key)
        if value is None:
            continue
        try:
            return int(value)
        except (TypeError, ValueError):
            continue
    return None


def apply_llamacpp_reasoning_params(form_data: dict, model: dict) -> None:
    if model.get('provider') != 'llama.cpp':
        return

    kwargs = dict(form_data.get('chat_template_kwargs') or {})
    enable_thinking = kwargs.get('enable_thinking')
    effort = form_data.get('reasoning_effort')

    if enable_thinking is False:
        _set_thinking_budget(form_data, 0)
        form_data['reasoning'] = {'enabled': False, 'effort': 'none'}
        return

    if effort is not None:
        if enable_thinking is None:
            kwargs['enable_thinking'] = True
            form_data['chat_template_kwargs'] = kwargs
        budget = reasoning_effort_to_budget_tokens(str(effort))
        if budget is not None:
            _set_thinking_budget(form_data, budget)
        reasoning = openrouter_reasoning_payload(form_data)
        if reasoning is not None:
            form_data['reasoning'] = reasoning
        return

    if enable_thinking is True:
        _set_thinking_budget(form_data, REASONING_EFFORT_TOKEN_BUDGETS[DEFAULT_THINKING_EFFORT])
        form_data['reasoning'] = {'enabled': True, 'effort': DEFAULT_THINKING_EFFORT}
        return

    explicit_budget = _explicit_thinking_budget(form_data)
    if explicit_budget is not None:
        _set_thinking_budget(form_data, explicit_budget)
        if explicit_budget == 0:
            kwargs['enable_thinking'] = False
            form_data['chat_template_kwargs'] = kwargs
            form_data['reasoning'] = {'enabled': False, 'effort': 'none'}
        elif enable_thinking is None:
            kwargs['enable_thinking'] = True
            form_data['chat_template_kwargs'] = kwargs


def disable_thinking(form_data: dict) -> None:
    params = dict(form_data.get('params') or {})
    params['think'] = False
    form_data['params'] = params
    form_data['think'] = False
    chat_template_kwargs = dict(form_data.get('chat_template_kwargs') or {})
    chat_template_kwargs['enable_thinking'] = False
    form_data['chat_template_kwargs'] = chat_template_kwargs
    form_data.pop('reasoning_effort', None)
    _set_thinking_budget(form_data, 0)
    form_data['reasoning'] = {'enabled': False, 'effort': 'none'}


def apply_task_thinking_policy(
    form_data: dict,
    metadata: dict | None,
    *,
    model: dict | None = None,
    api_config: dict | None = None,
) -> None:
    if not metadata:
        return

    features = metadata.get('features') or {}
    if not metadata.get('task') and not features.get('voice'):
        return

    disable_thinking(form_data)

    provider = (model or {}).get('provider') or (api_config or {}).get('provider')
    if provider == 'llama.cpp':
        apply_llamacpp_reasoning_params(form_data, {'provider': 'llama.cpp'})


def apply_llamacpp_provider_payload(payload: dict) -> None:
    tools = payload.get('tools')
    if isinstance(tools, list) and len(tools) >= 2 and 'parallel_tool_calls' not in payload:
        payload['parallel_tool_calls'] = True


def normalize_llamacpp_base(url: str) -> str:
    normalized = (url or '').strip().rstrip('/')
    for suffix in ('/openai/v1', '/v1'):
        if normalized.endswith(suffix):
            normalized = normalized[: -len(suffix)]
    return normalized.rstrip('/')


def snapshot_messages(messages: list | None) -> list:
    if not messages:
        return []
    return copy.deepcopy(messages)


def non_system_messages(messages: list | None) -> list:
    if not messages:
        return []
    return [message for message in messages if message.get('role') != 'system']


def collect_tool_specs_by_source(tools_dict: dict, provider_tools: list | None) -> dict[str, list]:
    by_name: dict[str, str] = {}
    for name, entry in (tools_dict or {}).items():
        spec = entry.get('spec') or {}
        fn_name = spec.get('name', name)
        tool_type = entry.get('type') or 'user'
        if tool_type not in TOOL_SOURCE_KEYS:
            if entry.get('server'):
                tool_type = 'external'
            else:
                tool_type = 'user'
        by_name[fn_name] = tool_type

    result: dict[str, list] = {key: [] for key in TOOL_SOURCE_KEYS}
    for tool in provider_tools or []:
        fn = (tool.get('function') or {}).get('name')
        if not fn:
            continue
        category = by_name.get(fn, 'user')
        result[category].append(tool)
    return result


def _tools_without_category(all_tools: list, category_tools: list) -> list:
    if not category_tools:
        return list(all_tools or [])
    remove_names = {
        (tool.get('function') or {}).get('name')
        for tool in category_tools
        if (tool.get('function') or {}).get('name')
    }
    return [
        tool
        for tool in all_tools or []
        if (tool.get('function') or {}).get('name') not in remove_names
    ]


def _capability_cache_key(url_idx: int | str, base_url: str) -> str:
    return f'{url_idx}:{base_url}'


def _is_capability_cached(url_idx: int | str, base_url: str) -> bool | None:
    key = _capability_cache_key(url_idx, base_url)
    entry = _capability_cache.get(key)
    if not entry:
        return None
    supported, expiry = entry
    if expiry <= time.time():
        _capability_cache.pop(key, None)
        return None
    return supported


def _set_capability_cached(url_idx: int | str, base_url: str, supported: bool) -> None:
    key = _capability_cache_key(url_idx, base_url)
    _capability_cache[key] = (
        supported,
        time.time() + CAPABILITY_CACHE_TTL_SECONDS,
    )


async def _post_json(
    session: aiohttp.ClientSession,
    url: str,
    payload: dict,
    headers: dict | None,
    cookies: dict | None,
) -> dict | None:
    try:
        async with session.post(
            url,
            json=payload,
            headers=headers,
            cookies=cookies,
            ssl=AIOHTTP_CLIENT_SESSION_SSL,
        ) as response:
            if response.status >= 400:
                return None
            data = await response.json()
            return data if isinstance(data, dict) else None
    except Exception:
        return None


async def count_templated_tokens(
    session: aiohttp.ClientSession,
    base_url: str,
    *,
    model: str,
    messages: list,
    tools: list | None,
    headers: dict | None,
    cookies: dict | None,
) -> int | None:
    apply_url = f'{base_url}/apply-template'
    tokenize_url = f'{base_url}/tokenize'

    body: dict[str, Any] = {'messages': messages}
    if model:
        body['model'] = model
    if tools:
        body['tools'] = tools

    applied = await _post_json(session, apply_url, body, headers, cookies)
    if not applied or not isinstance(applied.get('prompt'), str):
        return None

    tokenized = await _post_json(
        session,
        tokenize_url,
        {'content': applied['prompt']},
        headers,
        cookies,
    )
    if not tokenized:
        return None

    tokens = tokenized.get('tokens')
    if not isinstance(tokens, list):
        return None

    return len(tokens)


async def _count_many(
    session: aiohttp.ClientSession,
    base_url: str,
    model: str,
    headers: dict | None,
    cookies: dict | None,
    jobs: list[tuple[str, list, list | None]],
) -> dict[str, int | None]:
    async def _one(job_key: str, messages: list, tools: list | None) -> tuple[str, int | None]:
        value = await count_templated_tokens(
            session,
            base_url,
            model=model,
            messages=messages,
            tools=tools,
            headers=headers,
            cookies=cookies,
        )
        return job_key, value

    results = await asyncio.gather(*[_one(key, msgs, tools) for key, msgs, tools in jobs])
    return dict(results)


async def compute_context_breakdown(
    *,
    snapshots: dict,
    tools: list | None,
    tools_dict: dict | None,
    model_id: str,
    base_url: str,
    url_idx: int | str,
    headers: dict | None,
    cookies: dict | None,
    payload_messages: list | None = None,
) -> dict | None:
    cached_capability = _is_capability_cached(url_idx, base_url)
    if cached_capability is False:
        return None

    middleware_final = snapshots.get('final')
    base_messages = snapshots.get('base')
    if not middleware_final or base_messages is None:
        return None

    # Model params system prompt is applied in openai.py after middleware snapshots.
    send_messages = payload_messages if payload_messages is not None else middleware_final

    tools_list = list(tools or [])
    specs_by_source = collect_tool_specs_by_source(tools_dict or {}, tools_list)

    jobs: list[tuple[str, list, list | None]] = [
        ('total', send_messages, tools_list or None),
        ('no_tools', send_messages, None),
        ('conversation', non_system_messages(base_messages), None),
    ]

    layer_pairs = [
        ('memory', 'pre_memory', 'post_memory'),
        ('skills', 'pre_skills', 'post_skills'),
        ('files', 'pre_files', 'post_files'),
    ]
    active_layers: list[str] = []
    for layer, pre_key, post_key in layer_pairs:
        if pre_key in snapshots and post_key in snapshots:
            active_layers.append(layer)
            jobs.append((f'{layer}_pre', snapshots[pre_key], tools_list or None))
            jobs.append((f'{layer}_post', snapshots[post_key], tools_list or None))

    if 'pre_rag' in snapshots:
        active_layers.append('knowledge')
        jobs.append(('knowledge_pre', snapshots['pre_rag'], tools_list or None))
        jobs.append(('knowledge_post', middleware_final, tools_list or None))

    tool_categories = [key for key in TOOL_SOURCE_KEYS if specs_by_source.get(key)]
    remaining_tools = list(tools_list)
    for category in ('mcp', 'external', 'terminal', 'builtin'):
        if category not in tool_categories:
            continue
        category_tools = specs_by_source.get(category) or []
        jobs.append((f'tools_with_{category}', send_messages, remaining_tools or None))
        remaining_tools = _tools_without_category(remaining_tools, category_tools)
        jobs.append((f'tools_without_{category}', send_messages, remaining_tools or None))

    try:
        timeout = aiohttp.ClientTimeout(total=BREAKDOWN_TIMEOUT_SECONDS)
        async with aiohttp.ClientSession(timeout=timeout, trust_env=True) as session:
            counts = await asyncio.wait_for(
                _count_many(session, base_url, model_id, headers, cookies, jobs),
                timeout=BREAKDOWN_TIMEOUT_SECONDS,
            )
    except Exception:
        log.debug('llama.cpp context breakdown timed out or failed', exc_info=True)
        _set_capability_cached(url_idx, base_url, False)
        return None

    if any(counts.get(job[0]) is None for job in jobs):
        _set_capability_cached(url_idx, base_url, False)
        return None

    total = int(counts['total'])  # type: ignore[arg-type]
    no_tools = int(counts['no_tools'])  # type: ignore[arg-type]
    conversation = int(counts['conversation'])  # type: ignore[arg-type]
    tools_total = total - no_tools

    memory = 0
    skills = 0
    files = 0
    knowledge = 0

    if 'memory' in active_layers:
        memory = int(counts['memory_post']) - int(counts['memory_pre'])  # type: ignore[arg-type]
    if 'skills' in active_layers:
        skills = int(counts['skills_post']) - int(counts['skills_pre'])  # type: ignore[arg-type]
    if 'files' in active_layers:
        files = int(counts['files_post']) - int(counts['files_pre'])  # type: ignore[arg-type]
    if 'knowledge' in active_layers:
        knowledge = int(counts['knowledge_post']) - int(counts['knowledge_pre'])  # type: ignore[arg-type]

    tools_detail: dict[str, int] = {key: 0 for key in TOOL_SOURCE_KEYS}
    remaining_tools = list(tools_list)
    for category in ('mcp', 'external', 'terminal', 'builtin'):
        if category not in tool_categories:
            continue
        with_count = int(counts[f'tools_with_{category}'])  # type: ignore[arg-type]
        without_count = int(counts[f'tools_without_{category}'])  # type: ignore[arg-type]
        tools_detail[category] = with_count - without_count
        remaining_tools = _tools_without_category(remaining_tools, specs_by_source.get(category) or [])

    if specs_by_source.get('user'):
        tools_detail['user'] = tools_total - sum(tools_detail[key] for key in TOOL_SOURCE_KEYS if key != 'user')

    system = total - tools_total - memory - skills - files - knowledge - conversation
    if system < 0:
        _set_capability_cached(url_idx, base_url, False)
        return None

    _set_capability_cached(url_idx, base_url, True)

    return {
        'verified': True,
        'source': 'llama.cpp',
        'total': total,
        'system': system,
        'conversation': conversation,
        'tools': tools_total,
        'tools_detail': tools_detail,
        'memory': memory,
        'skills': skills,
        'files': files,
        'knowledge': knowledge,
    }


def attach_context_breakdown(usage: dict | None, breakdown: dict | None) -> dict | None:
    if not breakdown:
        return usage
    result = dict(usage or {})
    result['context_breakdown'] = breakdown
    return result
