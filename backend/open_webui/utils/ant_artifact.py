"""Parse and merge <antArtifact> blocks for chat history sent to the LLM."""

from __future__ import annotations

import re

OPEN_TAG_RE = re.compile(r'<antArtifact\b[^>]*>', re.IGNORECASE)
COMPLETE_ARTIFACT_RE = re.compile(
    r'<antArtifact([^>]*)>([\s\S]*?)</antArtifact>',
    re.IGNORECASE,
)
IDENTIFIER_RE = re.compile(r'identifier="([^"]*)"')
TYPE_RE = re.compile(r'type="([^"]*)"')
TITLE_RE = re.compile(r'title="([^"]*)"')


def _artifact_present_in_text(text: str, identifier: str, content: str) -> bool:
    if identifier and f'identifier="{identifier}"' in text:
        return True
    snippet = content[:120]
    return bool(snippet and snippet in text)


def parse_ant_artifacts(text: str) -> list[dict[str, str]]:
    artifacts: list[dict[str, str]] = []
    for match in COMPLETE_ARTIFACT_RE.finditer(text or ''):
        attrs = match.group(1) or ''
        body = (match.group(2) or '').strip()
        artifacts.append(
            {
                'identifier': (IDENTIFIER_RE.search(attrs) or ['', ''])[1],
                'type': (TYPE_RE.search(attrs) or ['', 'text/html'])[1],
                'title': (TITLE_RE.search(attrs) or ['', 'Artifact'])[1],
                'content': body,
            }
        )
    return artifacts


def serialize_ant_artifact(artifact: dict[str, str]) -> str:
    return (
        f'<antArtifact identifier="{artifact["identifier"]}" '
        f'type="{artifact["type"]}" title="{artifact["title"]}">\n'
        f'{artifact["content"]}\n'
        f'</antArtifact>'
    )


def merge_assistant_artifact_text(output_text: str, content: str | None) -> str:
    """Merge antArtifact blocks from message.content missing in structured output text."""
    cleaned_content = (content or '').strip()
    if not cleaned_content:
        return (output_text or '').strip()

    missing = [
        artifact
        for artifact in parse_ant_artifacts(cleaned_content)
        if not _artifact_present_in_text(output_text or '', artifact['identifier'], artifact['content'])
    ]
    if not missing:
        return (output_text or '').strip()

    appended = '\n\n'.join(serialize_ant_artifact(artifact) for artifact in missing)
    output_text = (output_text or '').strip()
    if output_text:
        return f'{output_text}\n\n{appended}'
    return appended


def append_missing_artifacts_to_output(output: list | None, content: str | None) -> list | None:
    """Ensure structured output message items include antArtifact text from message.content."""
    if not output or not isinstance(output, list):
        return output

    output_text = _get_output_text(output)
    merged_text = merge_assistant_artifact_text(output_text, content)
    if merged_text == output_text.strip():
        return output

    next_output = [dict(item) for item in output]
    for index in range(len(next_output) - 1, -1, -1):
        item = next_output[index]
        if item.get('type') != 'message':
            continue

        parts = [dict(part) for part in item.get('content') or []]
        if parts and parts[-1].get('type') == 'output_text':
            parts[-1]['text'] = merged_text
        else:
            parts.append({'type': 'output_text', 'text': merged_text})
        item['content'] = parts
        return next_output

    next_output.append(
        {
            'type': 'message',
            'role': 'assistant',
            'content': [{'type': 'output_text', 'text': merged_text}],
        }
    )
    return next_output


def _get_output_text(output: list) -> str:
    texts: list[str] = []
    for item in output:
        if not isinstance(item, dict) or item.get('type') != 'message':
            continue
        for part in item.get('content') or []:
            if isinstance(part, dict) and part.get('type') == 'output_text':
                text = part.get('text') or ''
                if isinstance(text, str) and text.strip():
                    texts.append(text)
    return '\n'.join(texts)
