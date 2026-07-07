from open_webui.utils.chat_retry import (
    assistant_response_has_content,
    get_retry_reason,
)


def test_empty_output_requests_retry():
    assert get_retry_reason([], '') == 'empty'
    assert get_retry_reason([{'type': 'message', 'content': [{'type': 'output_text', 'text': '  '}]}], '') == 'empty'


def test_message_text_skips_retry():
    output = [{'type': 'message', 'content': [{'type': 'output_text', 'text': 'Hello'}]}]
    assert assistant_response_has_content(output, '') is True
    assert get_retry_reason(output, '') is None


def test_reasoning_counts_as_content():
    output = [
        {
            'type': 'reasoning',
            'content': [{'type': 'output_text', 'text': 'thinking...'}],
        }
    ]
    assert assistant_response_has_content(output, '') is True
    assert get_retry_reason(output, '') is None


def test_tool_call_counts_as_content():
    output = [{'type': 'function_call', 'name': 'search_web', 'arguments': '{}'}]
    assert assistant_response_has_content(output, '') is True
    assert get_retry_reason(output, '') is None


def test_idle_timeout_requests_retry():
    assert get_retry_reason([], '', stream_timed_out=True) == 'timeout'
