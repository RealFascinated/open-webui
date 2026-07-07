"""
Claude-style deferred tool loading.

OpenAI-compatible providers: filter tools client-side; builtin tool_search
activates tools between middleware loop iterations.

Anthropic API: send all tools with defer_loading plus native tool_search_tool_bm25;
the API handles search and tool_reference expansion server-side.
"""

from __future__ import annotations

import copy
import json
import logging
import re
from typing import Any

from open_webui.env import (
    DEFERRED_TOOL_CONTEXT_RATIO,
    DEFERRED_TOOL_COUNT_THRESHOLD,
    DEFERRED_TOOL_SEARCH_RESULT_LIMIT,
)

log = logging.getLogger(__name__)

TOOL_SEARCH_NAME = 'tool_search'

ANTHROPIC_TOOL_SEARCH_TYPE = 'tool_search_tool_bm25_20251119'
ANTHROPIC_TOOL_SEARCH_NAME = 'tool_search_tool_bm25'
ANTHROPIC_ADVANCED_TOOL_USE_BETA = 'advanced-tool-use-2025-11-20'

# Non-deferred tools — always in model context when deferral is active (client-side path).
ALWAYS_LOADED_TOOL_NAMES = frozenset(
    {
        TOOL_SEARCH_NAME,
        'search_web',
        'fetch_url',
        'get_current_timestamp',
    }
)

# Anthropic native path uses server tool search; keep these hot without defer_loading.
ANTHROPIC_ALWAYS_LOADED_TOOL_NAMES = frozenset(
    {
        'search_web',
        'fetch_url',
        'get_current_timestamp',
    }
)


def _tool_name(tool_entry: dict) -> str:
    return (tool_entry.get('spec') or {}).get('name', '')


def summarize_tool_entry(tool_entry: dict) -> dict:
    spec = tool_entry.get('spec') or {}
    name = spec.get('name', '')
    description = spec.get('description', '')
    parameters = spec.get('parameters') or {}
    properties = parameters.get('properties') or {}
    required = set(parameters.get('required') or [])

    param_summary = {}
    for param_name, param_schema in properties.items():
        if param_name.startswith('__'):
            continue
        param_summary[param_name] = {
            'type': param_schema.get('type', 'any'),
            'description': param_schema.get('description', ''),
            'required': param_name in required,
        }

    return {
        'name': name,
        'description': description,
        'type': tool_entry.get('type', ''),
        'tool_id': tool_entry.get('tool_id', ''),
        'parameters': param_summary,
    }


def _estimate_tools_tokens(tools_dict: dict) -> int:
    total_chars = sum(len(json.dumps(entry.get('spec') or {}, ensure_ascii=False)) for entry in tools_dict.values())
    return total_chars // 4


def _model_context_length(model: dict) -> int:
    info = model.get('info') or {}
    meta = info.get('meta') or {}
    for key in ('max_context_tokens', 'context_length', 'max_tokens'):
        value = meta.get(key) or info.get(key)
        if isinstance(value, int) and value > 0:
            return value
    return 128_000


def should_enable_deferred_loading(tools_dict: dict, model: dict) -> bool:
    if len(tools_dict) <= DEFERRED_TOOL_COUNT_THRESHOLD:
        return False

    estimated_tokens = _estimate_tools_tokens(tools_dict)
    context_length = _model_context_length(model)
    if context_length > 0 and (estimated_tokens / context_length) >= DEFERRED_TOOL_CONTEXT_RATIO:
        return True

    return len(tools_dict) > DEFERRED_TOOL_COUNT_THRESHOLD


def uses_anthropic_native_deferred(model: dict) -> bool:
    return model.get('owned_by') == 'anthropic'


def init_deferred_loading(
    tools_dict: dict,
    metadata: dict,
    model: dict,
    *,
    native_anthropic: bool = False,
) -> bool:
    """Mark tools deferred and seed active_tool_names. Mutates tools_dict entries."""
    if not tools_dict:
        metadata['deferred_loading'] = False
        metadata['deferred_loading_mode'] = None
        metadata['active_tool_names'] = []
        return False

    if not should_enable_deferred_loading(tools_dict, model):
        metadata['deferred_loading'] = False
        metadata['deferred_loading_mode'] = None
        metadata['active_tool_names'] = sorted(tools_dict.keys())
        for entry in tools_dict.values():
            entry['defer_loading'] = False
        return False

    always_loaded = ANTHROPIC_ALWAYS_LOADED_TOOL_NAMES if native_anthropic else ALWAYS_LOADED_TOOL_NAMES
    active: set[str] = set()
    for name in always_loaded:
        if name in tools_dict:
            active.add(name)

    if not native_anthropic:
        if TOOL_SEARCH_NAME not in active and TOOL_SEARCH_NAME in tools_dict:
            active.add(TOOL_SEARCH_NAME)

    for name, entry in tools_dict.items():
        if native_anthropic and name == TOOL_SEARCH_NAME:
            entry['defer_loading'] = True
            continue
        entry['defer_loading'] = name not in active

    metadata['deferred_loading'] = True
    metadata['deferred_loading_mode'] = 'anthropic' if native_anthropic else 'client'
    metadata['active_tool_names'] = sorted(active)

    log.debug(
        'Deferred tool loading enabled (%s): %d total, %d active, %d deferred',
        metadata['deferred_loading_mode'],
        len(tools_dict),
        len(active),
        len(tools_dict) - len(active),
    )
    return True


def build_all_tools_with_defer_flags(
    tools_dict: dict,
    metadata: dict,
    *,
    exclude_names: set[str] | None = None,
) -> list[dict]:
    """OpenAI-style tools array with defer_loading on each function spec."""
    exclude_names = exclude_names or set()
    payload: list[dict] = []

    for name, entry in tools_dict.items():
        if name in exclude_names:
            continue
        spec = copy.deepcopy(entry.get('spec') or {})
        if not spec.get('name'):
            continue
        if metadata.get('deferred_loading') and entry.get('defer_loading'):
            spec['defer_loading'] = True
        payload.append({'type': 'function', 'function': spec})

    return payload


def build_tools_payload_for_provider(tools_dict: dict, metadata: dict, model: dict) -> list[dict]:
    if not metadata.get('deferred_loading'):
        return [{'type': 'function', 'function': tool.get('spec', {})} for tool in tools_dict.values()]

    if metadata.get('deferred_loading_mode') == 'anthropic':
        return build_all_tools_with_defer_flags(
            tools_dict,
            metadata,
            exclude_names={TOOL_SEARCH_NAME},
        )

    return build_active_tools_payload(tools_dict, metadata)


def build_active_tools_payload(tools_dict: dict, metadata: dict) -> list[dict]:
    """OpenAI-style tools array for the provider — only active tools when deferral is on."""
    if not tools_dict:
        return []

    if not metadata.get('deferred_loading'):
        return [{'type': 'function', 'function': tool.get('spec', {})} for tool in tools_dict.values()]

    active_names = metadata.get('active_tool_names') or []
    payload = []
    for name in active_names:
        entry = tools_dict.get(name)
        if entry and entry.get('spec'):
            payload.append({'type': 'function', 'function': entry['spec']})
    return payload


def _searchable_text(tool_entry: dict) -> str:
    summary = summarize_tool_entry(tool_entry)
    parts = [
        summary.get('name', ''),
        summary.get('description', ''),
        summary.get('type', ''),
        summary.get('tool_id', ''),
    ]
    for param_name, param_info in (summary.get('parameters') or {}).items():
        parts.extend([param_name, param_info.get('description', '')])
    return ' '.join(p for p in parts if p).lower()


def _score_tool(query: str, tool_entry: dict) -> float:
    text = _searchable_text(tool_entry)
    if not text:
        return 0.0

    q = query.strip().lower()
    if not q:
        return 0.0

    if q in text:
        return 10.0

    score = 0.0
    tokens = [t for t in re.split(r'\W+', q) if t]
    for token in tokens:
        if token in text:
            score += 1.0
        if token in _tool_name(tool_entry).lower():
            score += 2.0

    return score


def search_tools_catalog(
    tools_dict: dict,
    metadata: dict,
    query: str,
    limit: int | None = None,
    *,
    deferred_only: bool = False,
) -> list[dict]:
    limit = limit or DEFERRED_TOOL_SEARCH_RESULT_LIMIT
    active_names = set(metadata.get('active_tool_names') or [])

    candidates: list[tuple[float, dict]] = []
    for name, entry in tools_dict.items():
        if name == TOOL_SEARCH_NAME:
            continue
        if deferred_only and name in active_names:
            continue
        if deferred_only and not entry.get('defer_loading', False) and metadata.get('deferred_loading'):
            continue

        score = _score_tool(query, entry)
        if score > 0:
            summary = summarize_tool_entry(entry)
            summary['type'] = 'tool_reference'
            candidates.append((score, summary))

    candidates.sort(key=lambda item: (-item[0], item[1]['name']))
    return [item[1] for item in candidates[:limit]]


def activate_tools(metadata: dict, tool_names: list[str]) -> list[str]:
    """Add tool names to active set. Returns newly activated names."""
    tools_dict = metadata.get('tools') or {}
    active = set(metadata.get('active_tool_names') or [])
    newly_activated: list[str] = []

    for name in tool_names:
        if name not in tools_dict or name == TOOL_SEARCH_NAME:
            continue
        if name not in active:
            active.add(name)
            newly_activated.append(name)
            tools_dict[name]['defer_loading'] = False

    metadata['active_tool_names'] = sorted(active)
    return newly_activated


def run_tool_search(metadata: dict, query: str, limit: int | None = None) -> dict[str, Any]:
    tools_dict = metadata.get('tools') or {}
    limit = limit or DEFERRED_TOOL_SEARCH_RESULT_LIMIT

    if not metadata.get('deferred_loading'):
        matches = search_tools_catalog(tools_dict, metadata, query, limit=limit, deferred_only=False)
        return {
            'status': 'success',
            'message': 'All tools are already loaded in context.',
            'tool_references': matches,
            'activated': [],
        }

    matches = search_tools_catalog(tools_dict, metadata, query, limit=limit, deferred_only=True)
    activated = activate_tools(metadata, [m['name'] for m in matches])

    if not matches:
        return {
            'status': 'success',
            'message': 'No matching deferred tools found. Try a different query.',
            'tool_references': [],
            'activated': [],
        }

    return {
        'status': 'success',
        'message': (
            f'Loaded {len(activated)} tool(s) into context. '
            'They are now available to call on the next step.'
        ),
        'tool_references': matches,
        'activated': activated,
    }
