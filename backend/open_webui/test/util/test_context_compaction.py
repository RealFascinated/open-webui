from open_webui.utils.context_compaction import (
    _compaction_token_threshold,
    _context_from_model_entry,
    _get_model_context_length,
    _resolve_context_percent,
)


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
