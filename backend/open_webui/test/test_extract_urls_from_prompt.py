from open_webui.utils.misc import extract_urls_from_prompt, sanitize_extracted_url


def test_extract_bare_url():
    assert extract_urls_from_prompt('Summarize https://example.com/article please') == [
        'https://example.com/article'
    ]


def test_strip_trailing_punctuation():
    assert sanitize_extracted_url('https://example.com).') == 'https://example.com'
    assert extract_urls_from_prompt('See https://example.com).') == ['https://example.com']


def test_skip_fenced_code_blocks():
    text = 'Use this:\n```\nhttps://secret.example.com\n```\nThanks'
    assert extract_urls_from_prompt(text) == []


def test_skip_inline_code():
    assert extract_urls_from_prompt('Run `https://example.com` in terminal') == []


def test_skip_markdown_link_destinations():
    assert extract_urls_from_prompt('Read [docs](https://example.com/docs) here') == []


def test_extract_bare_url_alongside_markdown_link():
    text = 'See https://example.com and [docs](https://other.com/page)'
    assert extract_urls_from_prompt(text) == ['https://example.com']


def test_deduplicate_urls():
    text = 'https://example.com https://example.com'
    assert extract_urls_from_prompt(text) == ['https://example.com']


def test_max_urls_limit():
    text = 'https://a.com https://b.com https://c.com https://d.com'
    assert extract_urls_from_prompt(text, max_urls=2) == ['https://a.com', 'https://b.com']
