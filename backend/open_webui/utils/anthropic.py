import json
import logging

import aiohttp
from open_webui.env import (
    AIOHTTP_CLIENT_SESSION_SSL,
    AIOHTTP_CLIENT_TIMEOUT_MODEL_LIST,
    ENABLE_FORWARD_USER_INFO_HEADERS,
)
from open_webui.models.users import UserModel
from open_webui.utils.headers import include_user_info_headers

log = logging.getLogger(__name__)


def is_anthropic_url(url: str) -> bool:
    """Check if the URL is an Anthropic API endpoint."""
    return 'api.anthropic.com' in url


async def get_anthropic_models(url: str, key: str, user: UserModel = None) -> dict:
    """
    Fetch models from Anthropic's /v1/models endpoint with pagination.
    Normalizes the response to OpenAI format.
    """
    timeout = aiohttp.ClientTimeout(total=AIOHTTP_CLIENT_TIMEOUT_MODEL_LIST)
    all_models = []
    after_id = None

    try:
        async with aiohttp.ClientSession(timeout=timeout, trust_env=True) as session:
            headers = {
                'x-api-key': key,
                'anthropic-version': '2023-06-01',
            }

            if ENABLE_FORWARD_USER_INFO_HEADERS and user:
                headers = include_user_info_headers(headers, user)

            while True:
                params = {'limit': 1000}
                if after_id:
                    params['after_id'] = after_id

                async with session.get(
                    f'{url}/models',
                    headers=headers,
                    params=params,
                    ssl=AIOHTTP_CLIENT_SESSION_SSL,
                ) as response:
                    if response.status != 200:
                        error_detail = f'HTTP Error: {response.status}'
                        try:
                            res = await response.json()
                            if 'error' in res:
                                error_detail = f'External Error: {res["error"]}'
                        except Exception:
                            pass
                        return {'object': 'list', 'data': [], 'error': error_detail}

                    data = await response.json()

                    for model in data.get('data', []):
                        all_models.append(
                            {
                                'id': model.get('id'),
                                'object': 'model',
                                'created': 0,
                                'owned_by': 'anthropic',
                                'name': model.get('display_name', model.get('id')),
                            }
                        )

                    if not data.get('has_more', False):
                        break
                    after_id = data.get('last_id')

    except Exception as e:
        log.error(f'Anthropic connection error: {e}')
        return None

    return {'object': 'list', 'data': all_models}


##############################
#
# Anthropic Messages API Conversion Utilities
#
##############################


def _copy_cache_control(source: dict, target: dict) -> dict:
    if isinstance(source, dict) and 'cache_control' in source:
        target['cache_control'] = source['cache_control']
    return target


def _has_cache_control(blocks: list) -> bool:
    return any(isinstance(block, dict) and 'cache_control' in block for block in blocks)


def _finalize_openai_content(blocks: list) -> str | list:
    if not blocks:
        return ''

    if len(blocks) == 1 and blocks[0].get('type') == 'text' and not _has_cache_control(blocks):
        return blocks[0].get('text', '')

    return blocks


def convert_anthropic_to_openai_payload(anthropic_payload: dict) -> dict:
    """
    Convert an Anthropic Messages API request to OpenAI Chat Completions format.

    Anthropic format:
        {model, messages: [{role, content}], system, max_tokens, ...}
    OpenAI format:
        {model, messages: [{role, content}], max_tokens, ...}
    """
    openai_payload = {}

    # Model
    openai_payload['model'] = anthropic_payload.get('model', '')

    # Build messages list
    messages = []

    # System prompt (Anthropic has it as top-level, OpenAI as a system message)
    system = anthropic_payload.get('system')
    if system:
        if isinstance(system, str):
            messages.append({'role': 'system', 'content': system})
        elif isinstance(system, list):
            openai_content = []
            for block in system:
                if isinstance(block, dict) and block.get('type') == 'text':
                    openai_content.append(
                        _copy_cache_control(
                            block,
                            {
                                'type': 'text',
                                'text': block.get('text', ''),
                            },
                        )
                    )
                elif isinstance(block, str):
                    openai_content.append({'type': 'text', 'text': block})
            messages.append({'role': 'system', 'content': _finalize_openai_content(openai_content)})

    # Convert messages
    for msg in anthropic_payload.get('messages', []):
        role = msg.get('role', 'user')
        content = msg.get('content')

        if isinstance(content, str):
            messages.append({'role': role, 'content': content})
        elif isinstance(content, list):
            # Convert Anthropic content blocks to OpenAI format
            openai_content = []
            tool_calls = []

            for block in content:
                block_type = block.get('type', 'text')

                if block_type == 'text':
                    openai_content.append(
                        _copy_cache_control(
                            block,
                            {
                                'type': 'text',
                                'text': block.get('text', ''),
                            },
                        )
                    )
                elif block_type == 'image':
                    source = block.get('source', {})
                    if source.get('type') == 'base64':
                        media_type = source.get('media_type', 'image/png')
                        data = source.get('data', '')
                        openai_content.append(
                            _copy_cache_control(
                                block,
                                {
                                    'type': 'image_url',
                                    'image_url': {
                                        'url': f'data:{media_type};base64,{data}',
                                    },
                                },
                            )
                        )
                    elif source.get('type') == 'url':
                        openai_content.append(
                            _copy_cache_control(
                                block,
                                {
                                    'type': 'image_url',
                                    'image_url': {'url': source.get('url', '')},
                                },
                            )
                        )
                elif block_type == 'tool_use':
                    tool_calls.append(
                        {
                            'id': block.get('id', ''),
                            'type': 'function',
                            'function': {
                                'name': block.get('name', ''),
                                'arguments': (
                                    json.dumps(block.get('input', {}))
                                    if isinstance(block.get('input'), dict)
                                    else str(block.get('input', '{}'))
                                ),
                            },
                        }
                    )
                elif block_type == 'tool_result':
                    # Tool results become separate tool messages in OpenAI format
                    tool_result_content = block.get('content', '')
                    tool_content: str | list = ''

                    if isinstance(tool_result_content, str):
                        tool_content = tool_result_content
                    elif isinstance(tool_result_content, list):
                        # Build a multimodal content array to preserve
                        # images and other non-text content types.
                        converted_parts = []
                        for content_block in tool_result_content:
                            if not isinstance(content_block, dict):
                                continue
                            content_type = content_block.get('type', 'text')

                            if content_type == 'text':
                                converted_parts.append(
                                    _copy_cache_control(
                                        content_block,
                                        {
                                            'type': 'text',
                                            'text': content_block.get('text', ''),
                                        },
                                    )
                                )
                            elif content_type == 'image':
                                source = content_block.get('source', {})
                                if source.get('type') == 'base64':
                                    media_type = source.get('media_type', 'image/png')
                                    data = source.get('data', '')
                                    converted_parts.append(
                                        _copy_cache_control(
                                            content_block,
                                            {
                                                'type': 'image_url',
                                                'image_url': {
                                                    'url': f'data:{media_type};base64,{data}',
                                                },
                                            },
                                        )
                                    )
                                elif source.get('type') == 'url':
                                    converted_parts.append(
                                        _copy_cache_control(
                                            content_block,
                                            {
                                                'type': 'image_url',
                                                'image_url': {
                                                    'url': source.get('url', ''),
                                                },
                                            },
                                        )
                                    )
                            elif content_type == 'document':
                                # Documents have no direct OpenAI equivalent;
                                # convert to a text representation.
                                document_source = content_block.get('source', {})
                                document_title = content_block.get('title', 'Document')
                                document_context = content_block.get('context', '')
                                document_text = f'[Document: {document_title}]'
                                if document_context:
                                    document_text += f'\n{document_context}'
                                if document_source.get('type') == 'text' and document_source.get('data'):
                                    document_text += f'\n{document_source["data"]}'
                                converted_parts.append({'type': 'text', 'text': document_text})
                            elif content_type == 'search_result':
                                # Convert search results to a text
                                # representation with source attribution.
                                search_title = content_block.get('title', '')
                                search_url = content_block.get('source', '')
                                search_content_blocks = content_block.get('content', [])
                                search_texts = []
                                for search_block in search_content_blocks:
                                    if isinstance(search_block, dict) and search_block.get('type') == 'text':
                                        search_texts.append(search_block.get('text', ''))
                                search_body = '\n'.join(search_texts)
                                search_text = f'[Search Result: {search_title}]'
                                if search_url:
                                    search_text += f'\nSource: {search_url}'
                                if search_body:
                                    search_text += f'\n{search_body}'
                                converted_parts.append({'type': 'text', 'text': search_text})

                        # Flatten to string when only text parts are present
                        if all(part.get('type') == 'text' for part in converted_parts) and not _has_cache_control(
                            converted_parts
                        ):
                            tool_content = '\n'.join(part.get('text', '') for part in converted_parts)
                        elif converted_parts:
                            tool_content = converted_parts
                        else:
                            tool_content = ''

                    # Propagate error status if present
                    if block.get('is_error'):
                        if isinstance(tool_content, str):
                            tool_content = f'Error: {tool_content}'
                        elif isinstance(tool_content, list):
                            tool_content.insert(
                                0,
                                {
                                    'type': 'text',
                                    'text': 'Error: ',
                                },
                            )

                    messages.append(
                        {
                            'role': 'tool',
                            'tool_call_id': block.get('tool_use_id', ''),
                            'content': tool_content,
                        }
                    )

            # Build the message
            if tool_calls:
                # Assistant message with tool calls
                msg_dict = {'role': role}
                if openai_content:
                    msg_dict['content'] = _finalize_openai_content(openai_content)
                else:
                    msg_dict['content'] = ''
                msg_dict['tool_calls'] = tool_calls
                messages.append(msg_dict)
            elif openai_content:
                messages.append({'role': role, 'content': _finalize_openai_content(openai_content)})
        else:
            messages.append({'role': role, 'content': str(content) if content else ''})

    openai_payload['messages'] = messages

    # max_tokens
    if 'max_tokens' in anthropic_payload:
        openai_payload['max_tokens'] = anthropic_payload['max_tokens']

    # Common parameters
    for param in ('temperature', 'top_p', 'top_k', 'stop_sequences', 'stream', 'metadata', 'service_tier'):
        if param in anthropic_payload:
            if param == 'stop_sequences':
                openai_payload['stop'] = anthropic_payload[param]
            else:
                openai_payload[param] = anthropic_payload[param]

    # Tools conversion: Anthropic → OpenAI
    if 'tools' in anthropic_payload:
        openai_tools = []
        for tool in anthropic_payload['tools']:
            tool_type = tool.get('type', '')
            if isinstance(tool_type, str) and tool_type.startswith('tool_search_tool'):
                continue

            function_dict = {
                'name': tool.get('name', ''),
                'description': tool.get('description', ''),
                'parameters': tool.get('input_schema', {}),
            }
            if tool.get('defer_loading'):
                function_dict['defer_loading'] = True

            openai_tools.append(
                _copy_cache_control(
                    tool,
                    {
                        'type': 'function',
                        'function': function_dict,
                    },
                )
            )
        if openai_tools:
            openai_payload['tools'] = openai_tools

    # tool_choice
    if 'tool_choice' in anthropic_payload:
        tool_choice = anthropic_payload['tool_choice']
        if isinstance(tool_choice, dict):
            tool_choice_type = tool_choice.get('type', 'auto')
            if tool_choice_type == 'auto':
                openai_payload['tool_choice'] = 'auto'
            elif tool_choice_type == 'any':
                openai_payload['tool_choice'] = 'required'
            elif tool_choice_type == 'tool':
                openai_payload['tool_choice'] = {
                    'type': 'function',
                    'function': {'name': tool_choice.get('name', '')},
                }

    return openai_payload


def _openai_message_content_to_text(content) -> str:
    if isinstance(content, str):
        return content
    if isinstance(content, list):
        return '\n'.join(
            part.get('text', '')
            for part in content
            if isinstance(part, dict) and part.get('type') in ('text', 'input_text', 'output_text')
        )
    return str(content) if content else ''


def convert_openai_tools_to_anthropic(openai_tools: list, metadata: dict | None = None) -> list[dict]:
    from open_webui.utils.deferred_tools import (
        ANTHROPIC_TOOL_SEARCH_NAME,
        ANTHROPIC_TOOL_SEARCH_TYPE,
        TOOL_SEARCH_NAME,
    )

    metadata = metadata or {}
    anthropic_tools: list[dict] = []

    if metadata.get('deferred_loading_mode') == 'anthropic':
        anthropic_tools.append(
            {
                'type': ANTHROPIC_TOOL_SEARCH_TYPE,
                'name': ANTHROPIC_TOOL_SEARCH_NAME,
            }
        )

    for tool in openai_tools or []:
        if not isinstance(tool, dict) or tool.get('type') != 'function':
            continue

        func = tool.get('function') or {}
        name = func.get('name', '')
        if not name:
            continue
        if metadata.get('deferred_loading_mode') == 'anthropic' and name == TOOL_SEARCH_NAME:
            continue

        anthropic_tool = _copy_cache_control(
            tool,
            {
                'name': name,
                'description': func.get('description', ''),
                'input_schema': func.get('parameters') or {'type': 'object', 'properties': {}},
            },
        )
        if func.get('defer_loading'):
            anthropic_tool['defer_loading'] = True
        anthropic_tools.append(anthropic_tool)

    return anthropic_tools


def _convert_openai_content_to_anthropic(content, role: str = 'user'):
    if isinstance(content, str):
        return content
    if not isinstance(content, list):
        return str(content) if content else ''

    converted_blocks = []
    for part in content:
        if not isinstance(part, dict):
            continue
        part_type = part.get('type')
        if part_type in ('text', 'input_text', 'output_text'):
            converted_blocks.append({'type': 'text', 'text': part.get('text', '')})
        elif part_type == 'image_url':
            image_url = part.get('image_url', {})
            url = image_url.get('url', '') if isinstance(image_url, dict) else image_url
            if isinstance(url, str) and url.startswith('data:'):
                header, _, data = url.partition(',')
                media_type = header.split(';')[0].replace('data:', '') or 'image/png'
                converted_blocks.append(
                    {
                        'type': 'image',
                        'source': {'type': 'base64', 'media_type': media_type, 'data': data},
                    }
                )
            elif url:
                converted_blocks.append({'type': 'image', 'source': {'type': 'url', 'url': url}})
    return converted_blocks or ''


def convert_openai_to_anthropic_payload(openai_payload: dict, metadata: dict | None = None) -> dict:
    """
    Convert an OpenAI Chat Completions request to Anthropic Messages API format.
    """
    metadata = metadata or {}
    anthropic_payload: dict = {
        'model': openai_payload.get('model', ''),
        'max_tokens': openai_payload.get('max_tokens')
        or openai_payload.get('max_completion_tokens')
        or 4096,
    }

    system_parts: list[str] = []
    anthropic_messages: list[dict] = []

    raw_messages = openai_payload.get('messages', [])
    idx = 0
    while idx < len(raw_messages):
        msg = raw_messages[idx]
        role = msg.get('role', 'user')

        if role == 'system':
            system_parts.append(_openai_message_content_to_text(msg.get('content')))
            idx += 1
            continue

        if role == 'tool':
            tool_results = []
            while idx < len(raw_messages) and raw_messages[idx].get('role') == 'tool':
                tool_msg = raw_messages[idx]
                tool_results.append(
                    {
                        'type': 'tool_result',
                        'tool_use_id': tool_msg.get('tool_call_id', ''),
                        'content': _openai_message_content_to_text(tool_msg.get('content')),
                    }
                )
                idx += 1
            anthropic_messages.append({'role': 'user', 'content': tool_results})
            continue

        if role == 'assistant' and msg.get('tool_calls'):
            blocks: list[dict] = []
            text = _openai_message_content_to_text(msg.get('content'))
            if text.strip():
                blocks.append({'type': 'text', 'text': text})

            for tool_call in msg.get('tool_calls', []):
                function = tool_call.get('function') or {}
                raw_args = function.get('arguments', '{}')
                try:
                    tool_input = json.loads(raw_args) if isinstance(raw_args, str) else raw_args
                except (json.JSONDecodeError, TypeError):
                    tool_input = {}

                blocks.append(
                    {
                        'type': 'tool_use',
                        'id': tool_call.get('id', ''),
                        'name': function.get('name', ''),
                        'input': tool_input if isinstance(tool_input, dict) else {},
                    }
                )

            anthropic_messages.append({'role': 'assistant', 'content': blocks})
            idx += 1
            continue

        anthropic_messages.append(
            {
                'role': role,
                'content': _convert_openai_content_to_anthropic(msg.get('content'), role),
            }
        )
        idx += 1

    if system_parts:
        anthropic_payload['system'] = '\n\n'.join(part for part in system_parts if part)

    anthropic_payload['messages'] = anthropic_messages

    if 'tools' in openai_payload:
        anthropic_payload['tools'] = convert_openai_tools_to_anthropic(openai_payload.get('tools', []), metadata)

    if openai_payload.get('stream'):
        anthropic_payload['stream'] = True

    for param in ('temperature', 'top_p', 'top_k', 'metadata', 'stop'):
        if param in openai_payload:
            if param == 'stop':
                stop = openai_payload[param]
                if isinstance(stop, str):
                    anthropic_payload['stop_sequences'] = [stop]
                elif isinstance(stop, list):
                    anthropic_payload['stop_sequences'] = stop
            else:
                anthropic_payload[param] = openai_payload[param]

    if 'tool_choice' in openai_payload:
        tool_choice = openai_payload['tool_choice']
        if tool_choice == 'auto':
            anthropic_payload['tool_choice'] = {'type': 'auto'}
        elif tool_choice == 'required':
            anthropic_payload['tool_choice'] = {'type': 'any'}
        elif isinstance(tool_choice, dict) and tool_choice.get('type') == 'function':
            anthropic_payload['tool_choice'] = {
                'type': 'tool',
                'name': tool_choice.get('function', {}).get('name', ''),
            }

    return anthropic_payload


def convert_anthropic_message_to_openai(anthropic_response: dict, model: str = '') -> dict:
    """Convert a non-streaming Anthropic Messages response to OpenAI chat completion format."""
    import uuid as _uuid

    content_blocks = anthropic_response.get('content') or []
    message_content = ''
    tool_calls = []

    for block in content_blocks:
        block_type = block.get('type')
        if block_type == 'text':
            message_content += block.get('text', '')
        elif block_type == 'tool_use':
            tool_calls.append(
                {
                    'id': block.get('id', f'toolu_{_uuid.uuid4().hex[:24]}'),
                    'type': 'function',
                    'function': {
                        'name': block.get('name', ''),
                        'arguments': json.dumps(block.get('input') or {}),
                    },
                }
            )
        elif block_type == 'tool_reference':
            # Server-expanded tool reference from deferred loading — no OpenAI equivalent.
            continue

    stop_reason = anthropic_response.get('stop_reason', 'end_turn')
    finish_reason_map = {
        'end_turn': 'stop',
        'max_tokens': 'length',
        'tool_use': 'tool_calls',
        'stop_sequence': 'stop',
        'pause_turn': 'stop',
    }
    finish_reason = finish_reason_map.get(stop_reason, 'stop')
    if tool_calls:
        finish_reason = 'tool_calls'

    usage = anthropic_response.get('usage') or {}
    openai_usage = {
        'prompt_tokens': usage.get('input_tokens', 0),
        'completion_tokens': usage.get('output_tokens', 0),
        'total_tokens': usage.get('input_tokens', 0) + usage.get('output_tokens', 0),
    }
    if 'cache_creation_input_tokens' in usage:
        openai_usage['cache_creation_input_tokens'] = usage['cache_creation_input_tokens']
    if 'cache_read_input_tokens' in usage:
        openai_usage['cache_read_input_tokens'] = usage['cache_read_input_tokens']

    message = {'role': 'assistant', 'content': message_content or None}
    if tool_calls:
        message['tool_calls'] = tool_calls

    return {
        'id': anthropic_response.get('id', f'chatcmpl-{_uuid.uuid4().hex[:24]}'),
        'object': 'chat.completion',
        'model': model or anthropic_response.get('model', ''),
        'choices': [
            {
                'index': 0,
                'message': message,
                'finish_reason': finish_reason,
            }
        ],
        'usage': openai_usage,
    }


convert_openai_to_anthropic_response = convert_anthropic_message_to_openai


async def anthropic_stream_to_openai_stream(anthropic_stream_generator, model: str = ''):
    """Convert Anthropic Messages SSE to OpenAI Chat Completions SSE."""
    import uuid as _uuid

    completion_id = f'chatcmpl-{_uuid.uuid4().hex[:24]}'
    created = int(__import__('time').time())
    text_started = False
    tool_states: dict[int, dict] = {}

    async for chunk in anthropic_stream_generator:
        if isinstance(chunk, bytes):
            chunk = chunk.decode('utf-8', errors='ignore')

        event_name = None
        data_string = None
        for line in chunk.strip().split('\n'):
            line = line.strip()
            if line.startswith('event:'):
                event_name = line[6:].strip()
            elif line.startswith('data:'):
                data_string = line[5:].strip()

        if not data_string:
            continue

        try:
            data = json.loads(data_string)
        except (json.JSONDecodeError, TypeError):
            continue

        if event_name == 'message_start':
            payload = {
                'id': completion_id,
                'object': 'chat.completion.chunk',
                'created': created,
                'model': model or data.get('message', {}).get('model', ''),
                'choices': [{'index': 0, 'delta': {'role': 'assistant'}, 'finish_reason': None}],
            }
            yield f'data: {json.dumps(payload)}\n\n'.encode()

        elif event_name == 'content_block_start':
            index = data.get('index', 0)
            block = data.get('content_block') or {}
            if block.get('type') == 'tool_use':
                tool_states[index] = {
                    'id': block.get('id', f'toolu_{_uuid.uuid4().hex[:24]}'),
                    'name': block.get('name', ''),
                    'arguments': '',
                    'started': False,
                }

        elif event_name == 'content_block_delta':
            index = data.get('index', 0)
            delta = data.get('delta') or {}
            delta_type = delta.get('type')

            if delta_type == 'text_delta':
                text = delta.get('text', '')
                if text:
                    text_started = True
                    payload = {
                        'id': completion_id,
                        'object': 'chat.completion.chunk',
                        'created': created,
                        'model': model,
                        'choices': [{'index': 0, 'delta': {'content': text}, 'finish_reason': None}],
                    }
                    yield f'data: {json.dumps(payload)}\n\n'.encode()

            elif delta_type == 'input_json_delta':
                tool = tool_states.get(index)
                if not tool:
                    continue
                partial = delta.get('partial_json', '')
                tool['arguments'] += partial
                tool_delta = {
                    'index': index,
                    'id': tool['id'] if not tool['started'] else None,
                    'type': 'function',
                    'function': {
                        'name': tool['name'] if not tool['started'] else None,
                        'arguments': partial,
                    },
                }
                tool['started'] = True
                cleaned = {k: v for k, v in tool_delta.items() if v is not None}
                if cleaned.get('function'):
                    cleaned['function'] = {k: v for k, v in cleaned['function'].items() if v is not None}
                payload = {
                    'id': completion_id,
                    'object': 'chat.completion.chunk',
                    'created': created,
                    'model': model,
                    'choices': [{'index': 0, 'delta': {'tool_calls': [cleaned]}, 'finish_reason': None}],
                }
                yield f'data: {json.dumps(payload)}\n\n'.encode()

        elif event_name == 'message_delta':
            stop_reason = (data.get('delta') or {}).get('stop_reason')
            finish_reason = None
            if stop_reason == 'tool_use':
                finish_reason = 'tool_calls'
            elif stop_reason == 'max_tokens':
                finish_reason = 'length'
            elif stop_reason:
                finish_reason = 'stop'

            if finish_reason:
                payload = {
                    'id': completion_id,
                    'object': 'chat.completion.chunk',
                    'created': created,
                    'model': model,
                    'choices': [{'index': 0, 'delta': {}, 'finish_reason': finish_reason}],
                }
                yield f'data: {json.dumps(payload)}\n\n'.encode()

        elif event_name == 'message_stop':
            yield b'data: [DONE]\n\n'


def apply_anthropic_request_headers(headers: dict, key: str, metadata: dict | None = None) -> dict:
    from open_webui.utils.deferred_tools import ANTHROPIC_ADVANCED_TOOL_USE_BETA

    headers = dict(headers)
    headers.pop('Authorization', None)
    if key:
        headers['x-api-key'] = key
    headers['anthropic-version'] = headers.get('anthropic-version', '2023-06-01')

    metadata = metadata or {}
    if metadata.get('deferred_loading_mode') == 'anthropic':
        existing = [part.strip() for part in headers.get('anthropic-beta', '').split(',') if part.strip()]
        if ANTHROPIC_ADVANCED_TOOL_USE_BETA not in existing:
            existing.append(ANTHROPIC_ADVANCED_TOOL_USE_BETA)
        headers['anthropic-beta'] = ','.join(existing)

    return headers
    """
    Convert a non-streaming OpenAI Chat Completions response to Anthropic Messages format.
    """
    import uuid as _uuid

    choice = {}
    if openai_response.get('choices'):
        choice = openai_response['choices'][0]

    message = choice.get('message', {})
    finish_reason = choice.get('finish_reason', 'stop')

    # Map finish_reason to stop_reason
    stop_reason_map = {
        'stop': 'end_turn',
        'length': 'max_tokens',
        'tool_calls': 'tool_use',
        'content_filter': 'end_turn',
    }
    stop_reason = stop_reason_map.get(finish_reason, 'end_turn')

    # Build content blocks
    content = []
    message_content = message.get('content')
    if message_content:
        content.append({'type': 'text', 'text': message_content})

    # Tool calls -> tool_use blocks
    tool_calls = message.get('tool_calls') or []
    for tool_call in tool_calls:
        function = tool_call.get('function', {})
        try:
            tool_input = json.loads(function.get('arguments', '{}'))
        except (json.JSONDecodeError, TypeError):
            tool_input = {}
        content.append(
            {
                'type': 'tool_use',
                'id': tool_call.get('id', f'toolu_{_uuid.uuid4().hex[:24]}'),
                'name': function.get('name', ''),
                'input': tool_input,
            }
        )

    # Usage
    openai_usage = openai_response.get('usage', {})
    usage = {
        'input_tokens': openai_usage.get('prompt_tokens', 0),
        'output_tokens': openai_usage.get('completion_tokens', 0),
    }
    if 'cache_creation_input_tokens' in openai_usage:
        usage['cache_creation_input_tokens'] = openai_usage['cache_creation_input_tokens']
    if 'cache_read_input_tokens' in openai_usage:
        usage['cache_read_input_tokens'] = openai_usage['cache_read_input_tokens']

    return {
        'id': openai_response.get('id', f'msg_{_uuid.uuid4().hex[:24]}'),
        'type': 'message',
        'role': 'assistant',
        'content': content,
        'model': model or openai_response.get('model', ''),
        'stop_reason': stop_reason,
        'stop_sequence': None,
        'usage': usage,
    }


async def openai_stream_to_anthropic_stream(openai_stream_generator, model: str = ''):
    """
    Convert an OpenAI SSE streaming response to Anthropic Messages SSE format.

    OpenAI sends: data: {"choices": [{"delta": {"content": "..."}}]}
    Anthropic sends: event: content_block_delta\\ndata: {"type": "content_block_delta", ...}

    Handles text content, tool calls, and mixed content with proper
    multi-block indexing as required by Anthropic's streaming protocol.

    Tool calls are tracked by their unique id (not OpenAI index) so that
    parallel calls sharing the same index get distinct Anthropic tool_use
    blocks. Each block follows the Anthropic lifecycle: start -> delta -> stop.
    """
    import uuid as _uuid

    message_id = f'msg_{_uuid.uuid4().hex[:24]}'
    input_tokens = 0
    output_tokens = 0
    stop_reason = 'end_turn'

    # Track content blocks with a running index.
    # Each text block or tool_use block gets its own index.
    current_block_index = 0
    text_block_open = False

    # Accumulated state for each tool call, keyed by tool call id.
    # Parallel calls that share the same OpenAI index get distinct entries.
    # Each entry: {id, name, arguments, block_index, started, stopped}
    tracked_tool_calls = {}
    # Map OpenAI tool call index -> tool call id for routing
    # argument-only deltas (deltas that carry arguments but no id).
    index_to_tool_id = {}
    # Whether any tool call block has been emitted (suppresses further text)
    has_tool_calls = False

    # Emit message_start
    message_start = {
        'type': 'message_start',
        'message': {
            'id': message_id,
            'type': 'message',
            'role': 'assistant',
            'content': [],
            'model': model,
            'stop_reason': None,
            'stop_sequence': None,
            'usage': {'input_tokens': 0, 'output_tokens': 0},
        },
    }
    yield f'event: message_start\ndata: {json.dumps(message_start)}\n\n'.encode()

    try:
        async for chunk in openai_stream_generator:
            if isinstance(chunk, bytes):
                chunk = chunk.decode('utf-8', errors='ignore')

            for line in chunk.strip().split('\n'):
                line = line.strip()

                if not line or not line.startswith('data:'):
                    continue

                data_string = line[5:].strip()
                if data_string == '[DONE]':
                    continue
                if data_string == '{}':
                    continue

                try:
                    data = json.loads(data_string)
                except (json.JSONDecodeError, TypeError):
                    continue

                choices = data.get('choices', [])
                if not choices:
                    # Check for usage in the final chunk
                    if data.get('usage'):
                        input_tokens = data['usage'].get('prompt_tokens', input_tokens)
                        output_tokens = data['usage'].get('completion_tokens', output_tokens)
                    continue

                delta = choices[0].get('delta', {})
                finish_reason = choices[0].get('finish_reason')
                message = choices[0].get('message') or {}

                # Update usage if present
                if data.get('usage'):
                    input_tokens = data['usage'].get('prompt_tokens', input_tokens)
                    output_tokens = data['usage'].get('completion_tokens', output_tokens)

                # --- Handle text content ---
                # Anthropic expects text blocks before tool blocks, so skip
                # text deltas once any tool call has started.
                content = delta.get('content')
                if content and not has_tool_calls:
                    if not text_block_open:
                        block_start = {
                            'type': 'content_block_start',
                            'index': current_block_index,
                            'content_block': {'type': 'text', 'text': ''},
                        }
                        yield f'event: content_block_start\ndata: {json.dumps(block_start)}\n\n'.encode()
                        text_block_open = True

                    block_delta = {
                        'type': 'content_block_delta',
                        'index': current_block_index,
                        'delta': {'type': 'text_delta', 'text': content},
                    }
                    yield f'event: content_block_delta\ndata: {json.dumps(block_delta)}\n\n'.encode()

                # --- Handle tool calls ---
                # Some providers put tool_calls on the final message object
                # instead of the delta; fall back to that when needed.
                tool_calls = delta.get('tool_calls') or []
                if not tool_calls and message.get('tool_calls'):
                    tool_calls = message['tool_calls']

                if tool_calls:
                    # Close text block if one is open (text comes before tools)
                    if text_block_open:
                        block_stop = {
                            'type': 'content_block_stop',
                            'index': current_block_index,
                        }
                        yield f'event: content_block_stop\ndata: {json.dumps(block_stop)}\n\n'.encode()
                        text_block_open = False
                        current_block_index += 1

                    for tool_call in tool_calls:
                        tool_call_index = tool_call.get('index', 0)
                        tool_call_id = tool_call.get('id', '')
                        tool_call_name = (tool_call.get('function') or {}).get('name', '')
                        arguments_chunk = (tool_call.get('function') or {}).get('arguments', '')

                        # Resolve which tracked tool call this delta belongs to.
                        # A delta with an id starts or identifies a specific tool.
                        # A delta without an id carries arguments for the most
                        # recent tool at this OpenAI index.
                        if tool_call_id:
                            if tool_call_id not in tracked_tool_calls:
                                tracked_tool_calls[tool_call_id] = {
                                    'id': tool_call_id,
                                    'name': tool_call_name,
                                    'arguments': '',
                                    'block_index': -1,
                                    'started': False,
                                    'stopped': False,
                                }
                            index_to_tool_id[tool_call_index] = tool_call_id
                            tool = tracked_tool_calls[tool_call_id]
                        elif tool_call_index in index_to_tool_id:
                            tool = tracked_tool_calls[index_to_tool_id[tool_call_index]]
                        else:
                            # First delta for this index with no id; create a
                            # provisional entry with a generated fallback id.
                            fallback_id = f'toolu_{_uuid.uuid4().hex[:24]}'
                            tracked_tool_calls[fallback_id] = {
                                'id': fallback_id,
                                'name': tool_call_name,
                                'arguments': '',
                                'block_index': -1,
                                'started': False,
                                'stopped': False,
                            }
                            index_to_tool_id[tool_call_index] = fallback_id
                            tool = tracked_tool_calls[fallback_id]

                        # Update name if provided on a later delta
                        if tool_call_name and not tool['name']:
                            tool['name'] = tool_call_name

                        # Emit content_block_start once we have a name
                        if not tool['started'] and tool['name']:
                            tool['block_index'] = current_block_index
                            tool['started'] = True
                            has_tool_calls = True

                            block_start = {
                                'type': 'content_block_start',
                                'index': current_block_index,
                                'content_block': {
                                    'type': 'tool_use',
                                    'id': tool['id'],
                                    'name': tool['name'],
                                    'input': {},
                                },
                            }
                            yield f'event: content_block_start\ndata: {json.dumps(block_start)}\n\n'.encode()
                            current_block_index += 1

                        # Buffer arguments and emit as input_json_delta
                        if arguments_chunk:
                            tool['arguments'] += arguments_chunk

                            if tool['started'] and not tool['stopped']:
                                block_delta = {
                                    'type': 'content_block_delta',
                                    'index': tool['block_index'],
                                    'delta': {
                                        'type': 'input_json_delta',
                                        'partial_json': arguments_chunk,
                                    },
                                }
                                yield f'event: content_block_delta\ndata: {json.dumps(block_delta)}\n\n'.encode()

                            # Close the block once arguments form complete JSON
                            if tool['started'] and not tool['stopped']:
                                try:
                                    json.loads(tool['arguments'])
                                    tool['stopped'] = True
                                    block_stop = {
                                        'type': 'content_block_stop',
                                        'index': tool['block_index'],
                                    }
                                    yield f'event: content_block_stop\ndata: {json.dumps(block_stop)}\n\n'.encode()
                                except (json.JSONDecodeError, ValueError):
                                    pass

                # --- Handle finish reason ---
                if finish_reason is not None:
                    stop_reason_map = {
                        'stop': 'end_turn',
                        'length': 'max_tokens',
                        'tool_calls': 'tool_use',
                    }
                    stop_reason = stop_reason_map.get(finish_reason, 'end_turn')

    except Exception as e:
        log.error(f'Error in Anthropic stream conversion: {e}')

    # Flush any tools that buffered arguments but never emitted a block
    for tool in tracked_tool_calls.values():
        if not tool['started'] and tool['name']:
            tool['block_index'] = current_block_index
            tool['started'] = True

            block_start = {
                'type': 'content_block_start',
                'index': current_block_index,
                'content_block': {
                    'type': 'tool_use',
                    'id': tool['id'],
                    'name': tool['name'],
                    'input': {},
                },
            }
            yield f'event: content_block_start\ndata: {json.dumps(block_start)}\n\n'.encode()
            current_block_index += 1

            if tool['arguments']:
                block_delta = {
                    'type': 'content_block_delta',
                    'index': tool['block_index'],
                    'delta': {
                        'type': 'input_json_delta',
                        'partial_json': tool['arguments'],
                    },
                }
                yield f'event: content_block_delta\ndata: {json.dumps(block_delta)}\n\n'.encode()

    # Close any open text block
    if text_block_open:
        block_stop = {'type': 'content_block_stop', 'index': current_block_index}
        yield f'event: content_block_stop\ndata: {json.dumps(block_stop)}\n\n'.encode()

    # Close any tool call blocks that are still open
    for tool in tracked_tool_calls.values():
        if tool['started'] and not tool['stopped']:
            block_stop = {'type': 'content_block_stop', 'index': tool['block_index']}
            yield f'event: content_block_stop\ndata: {json.dumps(block_stop)}\n\n'.encode()

    # Emit message_delta with stop reason
    message_delta = {
        'type': 'message_delta',
        'delta': {
            'stop_reason': stop_reason,
            'stop_sequence': None,
        },
        'usage': {'output_tokens': output_tokens},
    }
    yield f'event: message_delta\ndata: {json.dumps(message_delta)}\n\n'.encode()

    # Emit message_stop
    yield f'event: message_stop\ndata: {json.dumps({"type": "message_stop"})}\n\n'.encode()
