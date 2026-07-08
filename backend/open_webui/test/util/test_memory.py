from types import SimpleNamespace

import pytest
from fastapi import HTTPException

from open_webui.utils.memory import (
    clean_memory_path,
    memory_always_include,
    memory_visible_in_scope,
    parse_always_include_paths,
    project_memory_path,
    render_memory_sections,
    truncate_section_lines,
)


def test_project_memory_path():
    assert project_memory_path('abc123') == 'projects/abc123'
    assert project_memory_path('abc123', 'decisions') == 'projects/abc123/decisions'
    assert project_memory_path(None, 'core/preferences') == 'core/preferences'


def test_memory_visible_in_scope():
    global_memory = SimpleNamespace(path='core/preferences')
    project_memory = SimpleNamespace(path='projects/p1/decisions')
    other_project_memory = SimpleNamespace(path='projects/p2/decisions')

    assert memory_visible_in_scope(global_memory, None) is True
    assert memory_visible_in_scope(project_memory, None) is False
    assert memory_visible_in_scope(project_memory, 'p1') is True
    assert memory_visible_in_scope(other_project_memory, 'p1') is False


def test_memory_always_include():
    memory = SimpleNamespace(path='core/preferences', meta={'always_include': False})
    assert memory_always_include(memory, ['core']) is True

    memory = SimpleNamespace(path='work/team', meta=None)
    assert memory_always_include(memory, ['core']) is False

    memory = SimpleNamespace(path='work/team', meta={'always_include': True})
    assert memory_always_include(memory, []) is True


def test_parse_always_include_paths():
    assert parse_always_include_paths('core, work/team ,') == ['core', 'work/team']


def test_truncate_section_lines_respects_boundaries():
    lines = ['short', 'this is a much longer memory line', 'tail']
    result = truncate_section_lines(lines, char_limit=30, count_limit=3)
    assert result == ['short']


def test_render_memory_sections():
    rendered = render_memory_sections(
        {
            'user': ['Prefers dark mode'],
            'neighborhood': ['Team uses Rust'],
            'context': ['Project deadline in May'],
        },
        user_char_limit=500,
        context_char_limit=500,
        user_count_limit=5,
        context_count_limit=5,
    )
    assert rendered is not None
    assert '[User Memory]' in rendered
    assert '[Relevant Context]' in rendered


def test_clean_memory_path_rejects_invalid():
    with pytest.raises(HTTPException):
        clean_memory_path('../secrets')
