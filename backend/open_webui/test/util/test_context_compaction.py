from open_webui.utils.context_compaction import (
    _compaction_token_threshold,
    _context_from_model_entry,
    _exceeds_token_threshold,
    _find_compaction_boundary,
    _get_model_context_length,
    _resolve_context_percent,
    _retained_checkpoint_message_id,
)
from open_webui.utils.response import merge_usage, normalize_usage


def test_compaction_token_threshold_from_percent():
    assert _compaction_token_threshold(128000, 80) == 102400
    assert _compaction_token_threshold(8192, 50) == 4096


def test_resolve_context_percent_uses_model_override_when_lower():
    metadata = {'params': {'compact_context_percent': 60}}
    assert _resolve_context_percent(80, metadata) == 60


def test_resolve_context_percent_caps_model_override_at_global():
    metadata = {'params': {'compact_context_percent': 95}}
    assert _resolve_context_percent(80, metadata) == 80


def test_context_from_model_entry_reads_nested_fields():
    assert _context_from_model_entry({'context_length': 32000}) == 32000
    assert _context_from_model_entry({'info': {'params': {'num_ctx': 16384}}}) == 16384
    assert _context_from_model_entry({'meta': {'n_ctx': 4096}}) == 4096


def test_get_model_context_length_prefers_model_entry():
    models = {
        'gpt-test': {
            'info': {'params': {'num_ctx': 8192}},
            'context_length': 128000,
        }
    }
    assert _get_model_context_length('gpt-test', models, {}) == 128000


def test_get_model_context_length_falls_back_to_params_num_ctx():
    assert _get_model_context_length('missing', {}, {'params': {'num_ctx': 2048}}) == 2048


def test_normalize_usage_stamps_last_input_tokens():
    usage = normalize_usage({'prompt_tokens': 120000, 'completion_tokens': 500})
    assert usage['input_tokens'] == 120000
    assert usage['last_input_tokens'] == 120000
    assert usage['last_output_tokens'] == 500


def test_merge_usage_keeps_last_call_context_size():
    first = normalize_usage({'prompt_tokens': 40000, 'completion_tokens': 100})
    second = normalize_usage({'prompt_tokens': 80000, 'completion_tokens': 200})
    merged = merge_usage(first, second)
    assert merged['input_tokens'] == 120000
    assert merged['last_input_tokens'] == 80000
    assert merged['last_output_tokens'] == 200


def test_exceeds_token_threshold_uses_last_input_not_additive_total():
    messages = [
        {'role': 'user', 'content': 'hello'},
        {
            'role': 'assistant',
            'content': 'hi',
            'usage': {
                'input_tokens': 240000,
                'output_tokens': 300,
                'last_input_tokens': 80000,
                'last_output_tokens': 100,
            },
        },
    ]
    assert not _exceeds_token_threshold(messages, '', None, 100000)
    assert _exceeds_token_threshold(messages, '', None, 70000)


def test_retained_checkpoint_message_id_returns_first_retained_id():
    recent = [
        {'role': 'user', 'content': 'a', 'id': 'msg-1'},
        {'role': 'assistant', 'content': 'b', 'id': 'msg-2'},
    ]
    assert _retained_checkpoint_message_id(recent) == 'msg-1'


def test_find_compaction_boundary_splits_on_user_turns():
    messages = [
        {'role': 'user', 'content': '1'},
        {'role': 'assistant', 'content': '1', 'output': [{'type': 'tool_call'}]},
        {'role': 'tool', 'content': 'result'},
        {'role': 'assistant', 'content': 'done'},
        {'role': 'user', 'content': '2'},
        {'role': 'assistant', 'content': '2'},
    ]
    boundary = _find_compaction_boundary(messages)
    assert boundary == 4
    assert messages[boundary]['role'] == 'user'
