import copy
from unittest.mock import AsyncMock, patch

import pytest

from open_webui.utils.llamacpp_tokens import (
    collect_tool_specs_by_source,
    compute_context_breakdown,
    count_templated_tokens,
    non_system_messages,
    normalize_llamacpp_base,
    snapshot_messages,
)
from open_webui.utils.response import merge_usage


def test_normalize_llamacpp_base_strips_openai_suffixes():
    assert normalize_llamacpp_base('http://localhost:8080/v1/') == 'http://localhost:8080'
    assert normalize_llamacpp_base('http://localhost:8080/openai/v1') == 'http://localhost:8080'


def test_snapshot_messages_deep_copies():
    messages = [{'role': 'user', 'content': 'hello'}]
    snap = snapshot_messages(messages)
    snap[0]['content'] = 'changed'
    assert messages[0]['content'] == 'hello'


def test_non_system_messages_filters_system_role():
    messages = [
        {'role': 'system', 'content': 'sys'},
        {'role': 'user', 'content': 'hi'},
    ]
    assert non_system_messages(messages) == [{'role': 'user', 'content': 'hi'}]


def test_collect_tool_specs_by_source_maps_types():
    tools_dict = {
        'builtin_fn': {'type': 'builtin', 'spec': {'name': 'builtin_fn'}},
        'mcp_fn': {'type': 'mcp', 'spec': {'name': 'mcp_fn'}},
        'server_fn': {'server': 'srv', 'spec': {'name': 'server_fn'}},
        'user_fn': {'spec': {'name': 'user_fn'}},
    }
    provider_tools = [
        {'type': 'function', 'function': {'name': 'builtin_fn'}},
        {'type': 'function', 'function': {'name': 'mcp_fn'}},
        {'type': 'function', 'function': {'name': 'server_fn'}},
        {'type': 'function', 'function': {'name': 'user_fn'}},
    ]
    by_source = collect_tool_specs_by_source(tools_dict, provider_tools)
    assert len(by_source['builtin']) == 1
    assert len(by_source['mcp']) == 1
    assert len(by_source['external']) == 1
    assert len(by_source['user']) == 1


@pytest.mark.asyncio
async def test_count_templated_tokens_returns_token_length():
    session = AsyncMock()

    async def fake_post_json(session, url, payload, headers, cookies):
        if url.endswith('/apply-template'):
            return {'prompt': 'templated prompt'}
        if url.endswith('/tokenize'):
            return {'tokens': [1, 2, 3, 4]}
        return None

    with patch('open_webui.utils.llamacpp_tokens._post_json', side_effect=fake_post_json):
        count = await count_templated_tokens(
            session,
            'http://localhost:8080',
            model='test-model',
            messages=[{'role': 'user', 'content': 'hi'}],
            tools=None,
            headers=None,
            cookies=None,
        )

    assert count == 4


@pytest.mark.asyncio
async def test_count_templated_tokens_returns_none_on_apply_failure():
    session = AsyncMock()
    with patch('open_webui.utils.llamacpp_tokens._post_json', return_value=None):
        count = await count_templated_tokens(
            session,
            'http://localhost:8080',
            model='test-model',
            messages=[{'role': 'user', 'content': 'hi'}],
            tools=None,
            headers=None,
            cookies=None,
        )
    assert count is None


def _sample_snapshots():
    base = [
        {'role': 'system', 'content': 'sys'},
        {'role': 'user', 'content': 'hello'},
    ]
    return {
        'base': copy.deepcopy(base),
        'pre_memory': copy.deepcopy(base),
        'post_memory': copy.deepcopy(base),
        'pre_skills': copy.deepcopy(base),
        'post_skills': copy.deepcopy(base),
        'pre_files': copy.deepcopy(base),
        'post_files': copy.deepcopy(base),
        'pre_rag': copy.deepcopy(base),
        'final': copy.deepcopy(base),
    }


def _mcp_tool():
    return {'type': 'function', 'function': {'name': 'mcp_fn'}}


def _builtin_tool():
    return {'type': 'function', 'function': {'name': 'builtin_fn'}}


@pytest.mark.asyncio
async def test_compute_context_breakdown_partition_sums_to_total():
    snapshots = _sample_snapshots()
    tools = [_mcp_tool(), _builtin_tool()]
    tools_dict = {
        'mcp_fn': {'type': 'mcp', 'spec': {'name': 'mcp_fn'}},
        'builtin_fn': {'type': 'builtin', 'spec': {'name': 'builtin_fn'}},
    }

    async def fake_count_many(session, base_url, model_id, headers, cookies, jobs):
        fixed = {
            'total': 360,
            'no_tools': 350,
            'conversation': 100,
            'memory_pre': 350,
            'memory_post': 370,
            'skills_pre': 370,
            'skills_post': 385,
            'files_pre': 385,
            'files_post': 395,
            'knowledge_pre': 345,
            'knowledge_post': 360,
            'tools_with_mcp': 360,
            'tools_without_mcp': 355,
            'tools_with_builtin': 355,
            'tools_without_builtin': 350,
        }
        counts = {}
        for key, _messages, job_tools in jobs:
            if key in fixed:
                counts[key] = fixed[key]
            else:
                counts[key] = 350 + len(job_tools or []) * 5
        return counts

    with patch('open_webui.utils.llamacpp_tokens._count_many', side_effect=fake_count_many):
        breakdown = await compute_context_breakdown(
            snapshots=snapshots,
            tools=tools,
            tools_dict=tools_dict,
            model_id='test-model',
            base_url='http://localhost:8080',
            url_idx=0,
            headers=None,
            cookies=None,
        )

    assert breakdown is not None
    assert breakdown['verified'] is True
    assert breakdown['total'] == 360
    assert breakdown['tools'] == 10
    assert breakdown['memory'] == 20
    assert breakdown['skills'] == 15
    assert breakdown['files'] == 10
    assert breakdown['knowledge'] == 15
    assert breakdown['conversation'] == 100
    assert breakdown['system'] == 190
    assert (
        breakdown['system']
        + breakdown['memory']
        + breakdown['skills']
        + breakdown['files']
        + breakdown['knowledge']
        + breakdown['tools']
        + breakdown['conversation']
        == breakdown['total']
    )
    detail = breakdown['tools_detail']
    assert detail['mcp'] + detail['builtin'] == breakdown['tools']


@pytest.mark.asyncio
async def test_compute_context_breakdown_inactive_layers_are_zero():
    snapshots = {
        'base': [{'role': 'user', 'content': 'hello'}],
        'final': [{'role': 'user', 'content': 'hello'}],
    }

    async def fake_count_many(session, base_url, model_id, headers, cookies, jobs):
        counts = {}
        for key, _messages, job_tools in jobs:
            if key == 'total':
                counts[key] = 120
            elif key == 'no_tools':
                counts[key] = 100
            elif key == 'conversation':
                counts[key] = 100
            else:
                counts[key] = 100
        return counts

    with patch('open_webui.utils.llamacpp_tokens._count_many', side_effect=fake_count_many):
        breakdown = await compute_context_breakdown(
            snapshots=snapshots,
            tools=[],
            tools_dict={},
            model_id='test-model',
            base_url='http://localhost:8080',
            url_idx=1,
            headers=None,
            cookies=None,
        )

    assert breakdown is not None
    assert breakdown['memory'] == 0
    assert breakdown['skills'] == 0
    assert breakdown['files'] == 0
    assert breakdown['knowledge'] == 0
    assert breakdown['tools'] == 20


@pytest.mark.asyncio
async def test_compute_context_breakdown_returns_none_when_count_fails():
    snapshots = _sample_snapshots()

    async def fake_count_many(session, base_url, model_id, headers, cookies, jobs):
        return {key: None for key, _m, _t in jobs}

    with patch('open_webui.utils.llamacpp_tokens._count_many', side_effect=fake_count_many):
        breakdown = await compute_context_breakdown(
            snapshots=snapshots,
            tools=[],
            tools_dict={},
            model_id='test-model',
            base_url='http://localhost:8080',
            url_idx=2,
            headers=None,
            cookies=None,
        )

    assert breakdown is None


@pytest.mark.asyncio
async def test_compute_context_breakdown_uses_payload_messages_for_total():
    snapshots = _sample_snapshots()
    payload_messages = copy.deepcopy(snapshots['final'])
    payload_messages.insert(
        0,
        {'role': 'system', 'content': 'Large custom model system prompt'},
    )

    async def fake_count_many(session, base_url, model_id, headers, cookies, jobs):
        counts = {}
        for key, messages, job_tools in jobs:
            system_chars = sum(
                len(m.get('content', ''))
                for m in messages
                if m.get('role') == 'system' and isinstance(m.get('content'), str)
            )
            base = 300 + system_chars + len(job_tools or []) * 5
            if key == 'conversation':
                counts[key] = 100
            elif key == 'no_tools':
                counts[key] = base - len(job_tools or []) * 5
            else:
                counts[key] = base
        return counts

    with patch('open_webui.utils.llamacpp_tokens._count_many', side_effect=fake_count_many):
        without_payload = await compute_context_breakdown(
            snapshots=snapshots,
            tools=[],
            tools_dict={},
            model_id='test-model',
            base_url='http://localhost:8080',
            url_idx=3,
            headers=None,
            cookies=None,
        )
        with_payload = await compute_context_breakdown(
            snapshots=snapshots,
            tools=[],
            tools_dict={},
            model_id='test-model',
            base_url='http://localhost:8080',
            url_idx=4,
            headers=None,
            cookies=None,
            payload_messages=payload_messages,
        )

    assert without_payload is not None
    assert with_payload is not None
    assert with_payload['total'] > without_payload['total']
    assert with_payload['system'] > without_payload['system']


def test_merge_usage_preserves_latest_context_breakdown():
    first = {
        'prompt_tokens': 10,
        'context_breakdown': {'verified': True, 'total': 10},
    }
    second = {
        'completion_tokens': 5,
        'context_breakdown': {'verified': True, 'total': 20},
    }
    merged = merge_usage(first, second)
    assert merged['prompt_tokens'] == 10
    assert merged['completion_tokens'] == 5
    assert merged['context_breakdown']['total'] == 20
