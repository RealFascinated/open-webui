from open_webui.tools.builtin import (
    _build_knowledge_overview,
    _build_knowledge_query_payload,
    _build_note_chunk,
    _build_text_excerpt,
    _build_weather_forecast,
    _dedupe_image_results,
    _filter_knowledge_chunks_by_threshold,
    _group_knowledge_chunks,
    _wmo_description,
)


def test_filter_knowledge_chunks_by_threshold():
    chunks = [
        {'content': 'good', 'distance': 0.9, 'type': 'file'},
        {'content': 'weak', 'distance': 0.1, 'type': 'file'},
        {'content': 'note body', 'type': 'note'},
    ]

    filtered = _filter_knowledge_chunks_by_threshold(chunks, 0.5)

    assert len(filtered) == 2
    assert filtered[0]['content'] == 'good'
    assert filtered[1]['type'] == 'note'


def test_group_knowledge_chunks():
    chunks = [
        {'content': 'a1', 'source': 'doc.pdf', 'file_id': 'f1', 'relevance': 0.9},
        {'content': 'a2', 'source': 'doc.pdf', 'file_id': 'f1', 'relevance': 0.8},
        {'content': 'b1', 'source': 'other.md', 'file_id': 'f2', 'relevance': 0.7},
    ]

    grouped = _group_knowledge_chunks(chunks)

    assert len(grouped) == 2
    assert grouped[0]['chunks']
    assert len(grouped[0]['chunks']) == 2


def test_build_knowledge_query_payload_includes_overview():
    chunks = [
        {'content': 'First chunk content', 'source': 'guide.pdf', 'file_id': '1', 'relevance': 0.95},
        {'content': 'Second chunk content', 'source': 'notes.md', 'file_id': '2', 'relevance': 0.8},
    ]

    payload = _build_knowledge_query_payload('deployment steps', chunks)

    assert payload['query'] == 'deployment steps'
    assert payload['total_chunks'] == 2
    assert payload['overview']
    assert 'guide.pdf' in payload['overview']


def test_build_knowledge_overview_limits_excerpt_length():
    long_content = 'x' * 400
    overview = _build_knowledge_overview('q', [{'source': 'big.txt', 'content': long_content}])

    assert overview is not None
    assert len(overview) < len(long_content)


def test_build_knowledge_query_payload_includes_matched_kbs():
    payload = _build_knowledge_query_payload(
        'deployment',
        [{'content': 'chunk', 'source': 'guide.pdf', 'file_id': '1'}],
        matched_knowledge_bases=[{'id': 'kb1', 'name': 'Ops', 'similarity': 0.9}],
    )

    assert payload['matched_knowledge_bases'][0]['id'] == 'kb1'


def test_build_text_excerpt_truncates_long_content():
    excerpt, truncated = _build_text_excerpt('a' * 400, max_chars=100)
    assert truncated is True
    assert len(excerpt) < 400


def test_build_text_excerpt_centers_on_query():
    content = 'prefix ' + ('x' * 200) + 'needle' + ('y' * 200)
    excerpt, truncated = _build_text_excerpt(content, query='needle', max_chars=120)
    assert truncated is True
    assert 'needle' in excerpt


def test_build_note_chunk_returns_excerpt():
    class _Note:
        id = 'note-1'
        title = 'My Note'

        data = {'content': {'md': 'short'}}

    chunk = _build_note_chunk(_Note())
    assert chunk['content'] == 'short'
    assert chunk['note_id'] == 'note-1'
    assert 'truncated' not in chunk

    class _LongNote:
        id = 'note-2'
        title = 'Long Note'
        data = {'content': {'md': 'z' * 500}}

    long_chunk = _build_note_chunk(_LongNote())
    assert long_chunk['truncated'] is True
    assert len(long_chunk['content']) < 500
    assert 'view_note' in long_chunk['read_more']


def test_dedupe_image_results():
    images = [
        {'image_url': 'https://example.com/a.jpg', 'title': 'A'},
        {'image_url': 'https://example.com/a.jpg', 'title': 'A duplicate'},
        {'image_url': 'https://example.com/b.jpg', 'title': 'B'},
    ]

    deduped = _dedupe_image_results(images)

    assert len(deduped) == 2


def test_build_weather_forecast_shapes_daily_and_hourly():
    forecast = {
        'daily': {
            'time': ['2026-07-16', '2026-07-17'],
            'weather_code': [0, 3],
            'temperature_2m_max': [22.0, 19.0],
            'temperature_2m_min': [12.0, 11.0],
            'precipitation_probability_max': [5, 40],
        },
        'daily_units': {'temperature_2m_max': '°C'},
        'hourly': {
            'time': ['2026-07-16T10:00', '2026-07-16T11:00'],
            'weather_code': [0, 1],
            'temperature_2m': [18.0, 19.0],
            'precipitation_probability': [0, 10],
        },
        'hourly_units': {'temperature_2m': '°C'},
    }

    shaped = _build_weather_forecast(forecast)

    assert len(shaped['daily']) == 2
    assert shaped['daily'][0]['description'] == _wmo_description(0)
    assert len(shaped['hourly']) == 2
    assert shaped['hourly'][1]['temperature'] == 19.0
