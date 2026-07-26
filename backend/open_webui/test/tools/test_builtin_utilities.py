import json
from unittest.mock import AsyncMock, patch

import pytest

from open_webui.tools.builtin import (
    _build_text_diff,
    _resolve_timezone_name,
    color_convert,
    define_term,
    diff_text,
    json_format,
    timezone_convert,
    unit_convert,
)


@pytest.mark.asyncio
async def test_unit_convert_length():
    result = json.loads(await unit_convert(1, 'km', 'm'))
    assert result['result'] == 1000.0
    assert result['category'] == 'length'


@pytest.mark.asyncio
async def test_unit_convert_temperature():
    result = json.loads(await unit_convert(32, 'f', 'c'))
    assert result['result'] == 0.0


@pytest.mark.asyncio
async def test_unit_convert_data():
    result = json.loads(await unit_convert(1, 'gib', 'mib'))
    assert result['result'] == 1024.0


@pytest.mark.asyncio
async def test_unit_convert_incompatible_units():
    result = json.loads(await unit_convert(1, 'km', 'kg'))
    assert 'error' in result


def test_resolve_timezone_aliases():
    assert _resolve_timezone_name('Tokyo') == 'Asia/Tokyo'
    assert _resolve_timezone_name('UTC') == 'UTC'


def test_build_text_diff_detects_changes():
    result = _build_text_diff('alpha\nbeta', 'alpha\ngamma', label_a='old', label_b='new')
    assert result['additions'] >= 1
    assert result['deletions'] >= 1
    assert 'gamma' in result['diff']


@pytest.mark.asyncio
async def test_timezone_convert_tokyo_to_utc():
    result = json.loads(await timezone_convert('15:00', 'Asia/Tokyo', 'UTC', date='2026-07-16'))
    assert result['input']['timezone'] == 'Asia/Tokyo'
    assert result['output']['timezone'] == 'UTC'
    assert '06:00' in result['output']['local_iso']


@pytest.mark.asyncio
async def test_timezone_convert_uses_user_timezone():
    result = json.loads(
        await timezone_convert('09:00', 'UTC', None, date='2026-07-16', __user__={'timezone': 'America/New_York'})
    )
    assert result['output']['timezone'] == 'America/New_York'


@pytest.mark.asyncio
async def test_define_term_combines_sources():
    wiktionary_payload = [
        {
            'partOfSpeech': 'noun',
            'definitions': [{'definition': 'A test definition'}],
        }
    ]
    wikidata_search = {'search': [{'id': 'Q42', 'label': 'test', 'description': 'entity desc', 'aliases': []}]}
    wikidata_entity = {'entities': {'Q42': {'descriptions': {'en': {'value': 'entity desc'}}, 'aliases': {}}}}

    with patch('open_webui.tools.builtin._http_get_json', new_callable=AsyncMock) as mock_get:
        mock_get.side_effect = [wiktionary_payload, wikidata_search, wikidata_entity]
        result = json.loads(await define_term('test'))

    assert result['wiktionary']['entries'][0]['definitions'][0] == 'A test definition'
    assert result['wikidata']['entity_id'] == 'Q42'


@pytest.mark.asyncio
async def test_diff_text_inline():
    result = json.loads(await diff_text(text_a='foo', text_b='bar', __request__=object(), __user__={'id': 'u1'}))
    assert 'diff' in result
    assert result['similarity'] < 1.0


@pytest.mark.asyncio
async def test_json_format_pretty_print():
    result = json.loads(await json_format('{"b":1,"a":2}', sort_keys=True))
    assert result['valid'] is True
    assert '"a": 2' in result['formatted']
    assert result['formatted'].index('"a"') < result['formatted'].index('"b"')


@pytest.mark.asyncio
async def test_json_format_validate_invalid():
    result = json.loads(await json_format('{bad json}', action='validate'))
    assert result['valid'] is False
    assert result['line'] >= 1


@pytest.mark.asyncio
async def test_json_format_minify():
    result = json.loads(await json_format('{\n  "a": 1\n}\n', action='minify'))
    assert result['formatted'] == '{"a":1}'


@pytest.mark.asyncio
async def test_color_convert_hex_to_all():
    result = json.loads(await color_convert('#ff8000'))
    assert result['formats']['hex'] == '#ff8000'
    assert result['formats']['rgb'] == 'rgb(255, 128, 0)'


@pytest.mark.asyncio
async def test_color_convert_hsl_to_hex():
    result = json.loads(await color_convert('hsl(0, 100%, 50%)', to_format='hex'))
    assert result['value'] == '#ff0000'
