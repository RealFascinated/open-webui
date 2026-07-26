import json
from pathlib import Path

from open_webui.retrieval.web.searxng import (
    SearxngSearchOptions,
    SearxngSearchResponse,
    _apply_domain_diversity,
    _dedupe_results,
    _filter_by_score,
    _parse_result_item,
    _parse_searxng_payload,
    _should_include_template,
    searxng_response_to_documents,
)


FIXTURE_PATH = Path(__file__).resolve().parents[1] / 'fixtures' / 'searxng_scoresaber_reloaded.json'
DEFAULT_OPTIONS = SearxngSearchOptions()


def _load_fixture() -> dict:
    return json.loads(FIXTURE_PATH.read_text(encoding='utf-8'))


def test_parse_searxng_payload_scoresaber_fixture():
    payload = _load_fixture()
    response = _parse_searxng_payload(payload, 'scoresaber reloaded', count=10, options=DEFAULT_OPTIONS)

    assert isinstance(response, SearxngSearchResponse)
    assert response.query == 'scoresaber reloaded'
    assert 5 <= len(response.results) <= 10
    assert response.results[0].link == 'https://ssr.fascinated.cc/'
    assert response.results[0].score == 13.333333333333332
    assert response.results[0].engines == ['startpage', 'google cse', 'bing', 'duckduckgo']
    assert 'Beat Saber' in (response.results[0].snippet or '')
    assert response.engine_failures == [
        'brave: too many requests',
        'qwant: access denied',
        'wikidata: access denied',
        'yahoo: HTTP protocol error',
    ]


def test_score_filtering_removes_low_relevance_noise():
    payload = _load_fixture()
    strict_options = SearxngSearchOptions(min_score_ratio=0.2, min_absolute_score=1.0)
    response = _parse_searxng_payload(payload, 'scoresaber reloaded', count=20, options=strict_options)

    assert response.results
    assert all((result.score or 0) >= 1.0 for result in response.results)
    assert all('tiktok.com' not in result.link for result in response.results)


def test_template_filtering_skips_non_general_results():
    assert _should_include_template({'template': 'default.html'}, '') is True
    assert _should_include_template({'template': 'images.html'}, '') is False
    assert _should_include_template({'template': 'images.html'}, 'images') is True


def test_domain_diversity_limits_per_host():
    results = [
        _parse_result_item({'url': 'https://example.com/a', 'title': 'A', 'content': 'a', 'score': 3.0}),
        _parse_result_item({'url': 'https://example.com/b', 'title': 'B', 'content': 'b', 'score': 2.0}),
        _parse_result_item({'url': 'https://other.com/c', 'title': 'C', 'content': 'c', 'score': 1.0}),
    ]
    diverse = _apply_domain_diversity(results, max_per_domain=1)

    assert len(diverse) == 2
    assert {result.link for result in diverse} == {'https://example.com/a', 'https://other.com/c'}


def test_dedupe_results_keeps_highest_score():
    first = _parse_result_item(
        {
            'url': 'https://example.com/page/',
            'title': 'Short',
            'content': 'A',
            'score': 1.0,
        }
    )
    second = _parse_result_item(
        {
            'url': 'https://example.com/page',
            'title': 'Better',
            'content': 'Longer snippet here',
            'score': 5.0,
        }
    )

    deduped = _dedupe_results([first, second])

    assert len(deduped) == 1
    assert deduped[0].title == 'Better'
    assert deduped[0].score == 5.0


def test_filter_by_score_uses_ratio_and_absolute_floor():
    results = [
        _parse_result_item({'url': 'https://a.test', 'title': 'A', 'content': 'a', 'score': 10.0}),
        _parse_result_item({'url': 'https://b.test', 'title': 'B', 'content': 'b', 'score': 0.2}),
        _parse_result_item({'url': 'https://c.test', 'title': 'C', 'content': 'c', 'score': 0.5}),
    ]
    filtered = _filter_by_score(results, min_ratio=0.05, min_absolute=0.15)

    assert len(filtered) == 2
    assert filtered[0].link == 'https://a.test'
    assert filtered[1].link == 'https://c.test'


def test_to_tool_payload_includes_overview_and_failures():
    payload = _load_fixture()
    response = _parse_searxng_payload(payload, 'scoresaber reloaded', count=3, options=DEFAULT_OPTIONS)
    tool_payload = response.to_tool_payload(count=3)

    assert tool_payload['query'] == 'scoresaber reloaded'
    assert len(tool_payload['results']) == 3
    assert tool_payload['engine_failures']
    assert tool_payload['overview']
    assert tool_payload['results'][0]['score'] == 13.333333333333332


def test_parse_answers_and_infoboxes():
    payload = {
        'query': 'test',
        'number_of_results': 1,
        'results': [],
        'answers': [
            'Plain answer',
            {'answer': 'Structured answer', 'url': 'https://example.com', 'engine': 'wolframalpha'},
        ],
        'infoboxes': [
            {
                'title': 'Example',
                'content': '<p>HTML <b>summary</b></p>',
                'attributes': [{'label': 'Founded', 'value': '2020'}],
                'urls': [{'title': 'Official site', 'url': 'https://example.com'}],
            }
        ],
        'suggestions': ['related query'],
        'corrections': ['corrected query'],
        'unresponsive_engines': [],
    }

    response = _parse_searxng_payload(payload, 'test', count=5, options=DEFAULT_OPTIONS)

    assert len(response.answers) == 2
    assert response.answers[1].url == 'https://example.com'
    assert response.infoboxes[0].content == 'HTML summary'
    assert response.suggestions == ['related query']
    assert response.corrections == ['corrected query']
    assert response.build_overview()


def test_searxng_response_to_documents_includes_overview_and_answers():
    response = SearxngSearchResponse(
        query='test',
        answers=[{'answer': 'It is a test', 'url': 'https://example.com'}],
        results=[
            _parse_result_item(
                {
                    'url': 'https://example.com/page',
                    'title': 'Example',
                    'content': 'Example snippet',
                    'score': 2.0,
                }
            )
        ],
    )

    docs = searxng_response_to_documents(response)

    assert len(docs) >= 3
    assert docs[0].metadata['type'] == 'overview'
    assert any(doc.metadata.get('type') == 'direct_answer' for doc in docs)
    assert any(doc.metadata.get('type') == 'result' for doc in docs)
