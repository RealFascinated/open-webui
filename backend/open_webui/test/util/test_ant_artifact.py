from open_webui.utils.ant_artifact import (
    append_missing_artifacts_to_output,
    merge_assistant_artifact_text,
    parse_ant_artifacts,
)


def test_parse_ant_artifacts():
    text = """<antArtifact identifier="demo" type="text/html" title="Demo">
<p>Hello</p>
</antArtifact>"""
    artifacts = parse_ant_artifacts(text)
    assert len(artifacts) == 1
    assert artifacts[0]['identifier'] == 'demo'
    assert artifacts[0]['content'] == '<p>Hello</p>'


def test_merge_assistant_artifact_text_appends_missing_blocks():
    output_text = 'Here is your app.'
    content = """Here is your app.

<antArtifact identifier="demo" type="text/html" title="Demo">
<p>Hello</p>
</antArtifact>"""

    merged = merge_assistant_artifact_text(output_text, content)
    assert 'Here is your app.' in merged
    assert '<antArtifact identifier="demo"' in merged
    assert '<p>Hello</p>' in merged


def test_append_missing_artifacts_to_output_updates_message_item():
    output = [
        {
            'type': 'message',
            'content': [{'type': 'output_text', 'text': 'Intro only.'}],
        }
    ]
    content = """Intro only.

<antArtifact identifier="demo" type="text/html" title="Demo">
<p>Hello</p>
</antArtifact>"""

    enriched = append_missing_artifacts_to_output(output, content)
    assert enriched is not output
    text = enriched[0]['content'][0]['text']
    assert '<antArtifact identifier="demo"' in text
    assert '<p>Hello</p>' in text
