import pytest

from open_webui.utils.images.gemini_web import (
    GEMINI_WEB_MODEL_LABELS,
    _generation_prompt,
    get_gemini_web_model_catalog,
)


@pytest.mark.parametrize(
    ('prompt', 'expected'),
    [
        ('a cute dog', 'Generate an image: a cute dog'),
        ('Generate an image of a cat', 'Generate an image of a cat'),
        ('generate image of a mountain', 'generate image of a mountain'),
    ],
)
def test_generation_prompt(prompt, expected):
    assert _generation_prompt(prompt) == expected


def test_gemini_web_model_catalog_contains_known_modes():
    catalog = get_gemini_web_model_catalog()
    ids = {entry['id'] for entry in catalog}

    assert 'gemini-3-flash' in ids
    assert 'gemini-3-flash-thinking' in ids
    assert 'gemini-3-pro' in ids
    assert len(catalog) >= len(GEMINI_WEB_MODEL_LABELS)
