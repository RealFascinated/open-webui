"""
Built-in tools for Open WebUI.

These tools are automatically available when native function calling is enabled.

IMPORTANT: DO NOT IMPORT THIS MODULE DIRECTLY IN OTHER PARTS OF THE CODEBASE.
"""

from open_webui.tools.knowledge_fs import kb_exec  # noqa: F401 — re-exported

import asyncio
import json
import logging
import re
import time
from typing import Optional

from fastapi import Request

from open_webui.models.channels import Channel, ChannelMember, Channels
from open_webui.models.chats import Chats
from open_webui.models.config import Config
from open_webui.models.groups import Groups
from open_webui.models.memories import Memories
from open_webui.models.messages import Message, Messages
from open_webui.models.notes import Notes
from open_webui.models.users import UserModel
from open_webui.retrieval.utils import get_content_from_url
from open_webui.retrieval.vector.async_client import ASYNC_VECTOR_DB_CLIENT
from open_webui.routers.images import (
    CreateImageForm,
    EditImageForm,
    image_edits,
    image_generations,
)
from open_webui.routers.memories import (
    AddMemoryForm,
    ListMemoryPathsForm,
    MemoryUpdateModel,
    ReadMemoryPathForm,
    SearchMemoriesForm,
    UpdateMemoriesForm,
    list_memory_paths as _list_memory_paths,
    read_memory_path as _read_memory_path,
    search_memories as _search_memories,
    update_memories as _update_memories,
    update_memory_by_id,
)
from open_webui.routers.memories import (
    add_memory as _add_memory,
)
from open_webui.routers.retrieval import search_web as _search_web
from open_webui.utils.sanitize import sanitize_code

log = logging.getLogger(__name__)

MAX_KNOWLEDGE_BASE_SEARCH_ITEMS = 10_000


async def _has_read_access_to_file(
    file,
    user_id: str,
    user_role: str,
    model_knowledge: Optional[list[dict]] = None,
) -> bool:
    """Check if a user can read a file via ownership, admin role, model attachment, or access grants."""
    if file.user_id == user_id or user_role == 'admin':
        return True
    if model_knowledge and any(item.get('type') == 'file' and item.get('id') == file.id for item in model_knowledge):
        return True
    from open_webui.utils.access_control.files import has_access_to_file

    return await has_access_to_file(
        file_id=file.id,
        access_type='read',
        user=UserModel(**{'id': user_id, 'role': user_role}),
    )


# =============================================================================
# TIME UTILITIES
# =============================================================================


async def get_current_timestamp(
    __request__: Request = None,
    __user__: dict = None,
) -> str:
    """
    Get the current Unix timestamp in seconds.

    :return: JSON with current_timestamp (seconds), current_iso (UTC ISO format), and user_local_iso (user's local time)
    """
    try:
        import datetime
        from zoneinfo import ZoneInfo

        now = datetime.datetime.now(datetime.timezone.utc)
        result = {
            'current_timestamp': int(now.timestamp()),
            'current_iso': now.isoformat(),
        }

        # Include the user's local time if timezone is available
        tz_name = __user__.get('timezone') if __user__ else None
        if tz_name:
            try:
                user_tz = ZoneInfo(tz_name)
                user_now = now.astimezone(user_tz)
                result['user_local_iso'] = user_now.isoformat()
                result['user_timezone'] = tz_name
            except Exception:
                pass

        return json.dumps(result, ensure_ascii=False)
    except Exception as e:
        log.exception(f'get_current_timestamp error: {e}')
        return json.dumps({'error': str(e)})


async def calculate_timestamp(
    days_ago: int = 0,
    weeks_ago: int = 0,
    months_ago: int = 0,
    years_ago: int = 0,
    __request__: Request = None,
    __user__: dict = None,
) -> str:
    """
    Get the current Unix timestamp, optionally adjusted by days, weeks, months, or years.
    Use this to calculate timestamps for date filtering in search functions.
    Examples: "last week" = weeks_ago=1, "3 days ago" = days_ago=3, "a year ago" = years_ago=1

    :param days_ago: Number of days to subtract from current time (default: 0)
    :param weeks_ago: Number of weeks to subtract from current time (default: 0)
    :param months_ago: Number of months to subtract from current time (default: 0)
    :param years_ago: Number of years to subtract from current time (default: 0)
    :return: JSON with current_timestamp and calculated_timestamp (both in seconds)
    """
    try:
        import datetime

        from dateutil.relativedelta import relativedelta

        now = datetime.datetime.now(datetime.timezone.utc)
        current_ts = int(now.timestamp())

        # Calculate the adjusted time
        total_days = days_ago + (weeks_ago * 7)
        adjusted = now - datetime.timedelta(days=total_days)

        # Handle months and years separately (variable length)
        if months_ago > 0 or years_ago > 0:
            adjusted = adjusted - relativedelta(months=months_ago, years=years_ago)

        adjusted_ts = int(adjusted.timestamp())

        result = {
            'current_timestamp': current_ts,
            'current_iso': now.isoformat(),
            'calculated_timestamp': adjusted_ts,
            'calculated_iso': adjusted.isoformat(),
        }

        # Include the user's local time if timezone is available
        tz_name = __user__.get('timezone') if __user__ else None
        if tz_name:
            try:
                from zoneinfo import ZoneInfo

                user_tz = ZoneInfo(tz_name)
                result['user_local_iso'] = now.astimezone(user_tz).isoformat()
                result['calculated_local_iso'] = adjusted.astimezone(user_tz).isoformat()
                result['user_timezone'] = tz_name
            except Exception:
                pass

        return json.dumps(result, ensure_ascii=False)
    except ImportError:
        # Fallback without dateutil
        import datetime

        now = datetime.datetime.now(datetime.timezone.utc)
        current_ts = int(now.timestamp())
        total_days = days_ago + (weeks_ago * 7) + (months_ago * 30) + (years_ago * 365)
        adjusted = now - datetime.timedelta(days=total_days)
        adjusted_ts = int(adjusted.timestamp())
        result = {
            'current_timestamp': current_ts,
            'current_iso': now.isoformat(),
            'calculated_timestamp': adjusted_ts,
            'calculated_iso': adjusted.isoformat(),
        }

        tz_name = __user__.get('timezone') if __user__ else None
        if tz_name:
            try:
                from zoneinfo import ZoneInfo

                user_tz = ZoneInfo(tz_name)
                result['user_local_iso'] = now.astimezone(user_tz).isoformat()
                result['calculated_local_iso'] = adjusted.astimezone(user_tz).isoformat()
                result['user_timezone'] = tz_name
            except Exception:
                pass

        return json.dumps(result, ensure_ascii=False)
    except Exception as e:
        log.exception(f'calculate_timestamp error: {e}')
        return json.dumps({'error': str(e)})


# =============================================================================
# WEB SEARCH TOOLS
# =============================================================================


async def search_web(
    query: str,
    count: Optional[int] = None,
    __request__: Request = None,
    __user__: dict = None,
) -> str:
    """
    Search the public web for information. Best for current events, external references,
    or topics not covered in internal documents.

    :param query: The search query to look up
    :param count: Number of results to return (default: admin-configured value)
    :return: JSON with search results containing title, link, and snippet for each result
    """
    if __request__ is None:
        return json.dumps({'error': 'Request context not available'})

    try:
        engine = await Config.get('web.search.engine')
        user = UserModel(**__user__) if __user__ else None

        configured = await Config.get('web.search.result_count')
        max_count = 5 if configured is None else configured
        count = max(1, min(count, max_count)) if count is not None else max_count

        results = await _search_web(__request__, engine, query, user)

        # Limit results
        results = results[:count] if results else []

        return json.dumps(
            [{'title': r.title, 'link': r.link, 'snippet': r.snippet} for r in results],
            ensure_ascii=False,
        )
    except Exception as e:
        log.exception(f'search_web error: {e}')
        return json.dumps({'error': str(e)})


async def fetch_url(
    url: str,
    __request__: Request = None,
    __user__: dict = None,
) -> str:
    """
    Fetch and extract the main text content from a web page URL.

    :param url: The URL to fetch content from
    :return: The extracted text content from the page
    """
    if __request__ is None:
        return json.dumps({'error': 'Request context not available'})

    try:
        content, _ = await get_content_from_url(__request__, url)

        # Truncate if configured (WEB_FETCH_MAX_CONTENT_LENGTH)
        # Guard: content may be None if the web loader silently failed
        if content is not None:
            max_length = await Config.get('web.fetch.max_content_length')
            if max_length and max_length > 0 and len(content) > max_length:
                content = content[:max_length] + '\n\n[Content truncated...]'
        else:
            content = ''

        return content
    except Exception as e:
        log.warning(f'fetch_url error: {e}')
        return json.dumps({'error': str(e)})


# =============================================================================
# IMAGE GENERATION TOOLS
# =============================================================================


async def generate_image(
    prompt: str,
    __request__: Request = None,
    __user__: dict = None,
    __event_emitter__: callable = None,
    __chat_id__: str = None,
    __message_id__: str = None,
) -> str:
    """
    Generate an image based on a text prompt.

    :param prompt: A detailed description of the image to generate
    :return: Confirmation that the image was generated, or an error message
    """
    if __request__ is None:
        return json.dumps({'error': 'Request context not available'})

    try:
        user = UserModel(**__user__) if __user__ else None

        images = await image_generations(
            request=__request__,
            form_data=CreateImageForm(prompt=prompt),
            user=user,
        )

        # Prepare file entries for the images
        image_files = [{'type': 'image', 'url': img['url']} for img in images]

        # Persist files to DB if chat context is available
        if __chat_id__ and __message_id__ and images:
            db_files = await Chats.add_message_files_by_id_and_message_id(
                __chat_id__,
                __message_id__,
                image_files,
            )
            if db_files is not None:
                image_files = db_files

        # Emit the images to the UI if event emitter is available
        if __event_emitter__ and image_files:
            await __event_emitter__(
                {
                    'type': 'chat:message:files',
                    'data': {
                        'files': image_files,
                    },
                }
            )
            # Return a message indicating the image is already displayed
            return json.dumps(
                {
                    'status': 'success',
                    'message': 'The image has been successfully generated and is already visible to the user in the chat. You do not need to display or embed the image again - just acknowledge that it has been created.',
                    'images': images,
                },
                ensure_ascii=False,
            )

        return json.dumps({'status': 'success', 'images': images}, ensure_ascii=False)
    except Exception as e:
        log.exception(f'generate_image error: {e}')
        return json.dumps({'error': str(e)})


async def edit_image(
    prompt: str,
    image_urls: list[str],
    __request__: Request = None,
    __user__: dict = None,
    __event_emitter__: callable = None,
    __chat_id__: str = None,
    __message_id__: str = None,
) -> str:
    """
    Transform one or more existing images according to a text prompt.
    Supports targeted edits such as adding, removing, replacing, inpainting, extending, or compositing image content.

    :param prompt: A description of the transformation to apply to the provided images
    :param image_urls: Source image URLs to modify or use as composition inputs
    :return: Confirmation that the images were edited, or an error message
    """
    if __request__ is None:
        return json.dumps({'error': 'Request context not available'})

    try:
        user = UserModel(**__user__) if __user__ else None

        images = await image_edits(
            request=__request__,
            form_data=EditImageForm(prompt=prompt, image=image_urls),
            user=user,
        )

        # Prepare file entries for the images
        image_files = [{'type': 'image', 'url': img['url']} for img in images]

        # Persist files to DB if chat context is available
        if __chat_id__ and __message_id__ and images:
            db_files = await Chats.add_message_files_by_id_and_message_id(
                __chat_id__,
                __message_id__,
                image_files,
            )
            if db_files is not None:
                image_files = db_files

        # Emit the images to the UI if event emitter is available
        if __event_emitter__ and image_files:
            await __event_emitter__(
                {
                    'type': 'chat:message:files',
                    'data': {
                        'files': image_files,
                    },
                }
            )
            # Return a message indicating the image is already displayed
            return json.dumps(
                {
                    'status': 'success',
                    'message': 'The edited image has been successfully generated and is already visible to the user in the chat. You do not need to display or embed the image again - just acknowledge that it has been created.',
                    'images': images,
                },
                ensure_ascii=False,
            )

        return json.dumps({'status': 'success', 'images': images}, ensure_ascii=False)
    except Exception as e:
        log.exception(f'edit_image error: {e}')
        return json.dumps({'error': str(e)})


# =============================================================================
# CODE INTERPRETER TOOLS
# =============================================================================


async def execute_code(
    code: str,
    __request__: Request = None,
    __user__: dict = None,
    __event_emitter__: callable = None,
    __event_call__: callable = None,
    __chat_id__: str = None,
    __message_id__: str = None,
    __metadata__: dict = None,
) -> str:
    """
    Execute Python code in a sandboxed environment and return the output.
    Use this to perform calculations, data analysis, generate visualizations,
    or run any Python code that would help answer the user's question.

    :param code: The Python code to execute
    :return: JSON with stdout, stderr, and result from execution
    """
    from uuid import uuid4

    if __request__ is None:
        return json.dumps({'error': 'Request context not available'})

    try:
        # Sanitize code (strips ANSI codes and markdown fences)
        code = sanitize_code(code)

        # Import blocked modules from config (same as middleware)
        from open_webui.config import CODE_INTERPRETER_BLOCKED_MODULES

        # Add import blocking code if there are blocked modules
        if CODE_INTERPRETER_BLOCKED_MODULES:
            import textwrap

            blocking_code = textwrap.dedent(
                f"""
                import builtins

                BLOCKED_MODULES = {CODE_INTERPRETER_BLOCKED_MODULES}

                _real_import = builtins.__import__
                def restricted_import(name, globals=None, locals=None, fromlist=(), level=0):
                    if name.split('.')[0] in BLOCKED_MODULES:
                        importer_name = globals.get('__name__') if globals else None
                        if importer_name == '__main__':
                            raise ImportError(
                                f"Direct import of module {{name}} is restricted."
                            )
                    return _real_import(name, globals, locals, fromlist, level)

                builtins.__import__ = restricted_import
                """
            )
            code = blocking_code + '\n' + code

        engine = await Config.get('code_interpreter.engine', 'pyodide')
        if engine == 'pyodide':
            # Execute via frontend pyodide using bidirectional event call
            if __event_call__ is None:
                return json.dumps(
                    {'error': 'Event call not available. WebSocket connection required for pyodide execution.'}
                )

            output = await __event_call__(
                {
                    'type': 'execute:python',
                    'data': {
                        'id': str(uuid4()),
                        'code': code,
                        'session_id': (__metadata__.get('session_id') if __metadata__ else None),
                        'files': (__metadata__.get('files', []) if __metadata__ else []),
                    },
                }
            )

            # Parse the output - pyodide returns dict with stdout, stderr, result
            if isinstance(output, dict):
                # Handle error responses from event_caller (e.g. session disconnected, timeout)
                if output.get('error') and not output.get('stdout') and not output.get('result'):
                    stderr = output['error']
                    stdout = ''
                    result = ''
                else:
                    stdout = output.get('stdout', '')
                    stderr = output.get('stderr', '')
                    result = output.get('result', '')
            else:
                stdout = ''
                stderr = ''
                result = str(output) if output else ''

        elif engine == 'jupyter':
            from open_webui.utils.code_interpreter import execute_code_jupyter

            jupyter_auth = await Config.get('code_interpreter.jupyter.auth')

            output = await execute_code_jupyter(
                await Config.get('code_interpreter.jupyter.url'),
                code,
                (await Config.get('code_interpreter.jupyter.auth_token') if jupyter_auth == 'token' else None),
                (await Config.get('code_interpreter.jupyter.auth_password') if jupyter_auth == 'password' else None),
                await Config.get('code_interpreter.jupyter.timeout'),
            )

            stdout = output.get('stdout', '')
            stderr = output.get('stderr', '')
            result = output.get('result', '')

        else:
            return json.dumps({'error': f'Unknown code interpreter engine: {engine}'})

        # Handle image outputs (base64 encoded) - replace with uploaded URLs
        # Get actual user object for image upload (upload_image requires user.id attribute)
        if __user__ and __user__.get('id'):
            from open_webui.models.users import Users
            from open_webui.utils.files import get_image_url_from_base64

            user = await Users.get_user_by_id(__user__['id'])

            # Extract and upload images from stdout
            if stdout and isinstance(stdout, str):
                stdout_lines = stdout.split('\n')
                for idx, line in enumerate(stdout_lines):
                    if 'data:image/png;base64' in line:
                        image_url = await get_image_url_from_base64(
                            __request__,
                            line,
                            __metadata__ or {},
                            user,
                        )
                        if image_url:
                            stdout_lines[idx] = f'![Output Image]({image_url})'
                stdout = '\n'.join(stdout_lines)

            # Extract and upload images from result
            if result and isinstance(result, str):
                result_lines = result.split('\n')
                for idx, line in enumerate(result_lines):
                    if 'data:image/png;base64' in line:
                        image_url = await get_image_url_from_base64(
                            __request__,
                            line,
                            __metadata__ or {},
                            user,
                        )
                        if image_url:
                            result_lines[idx] = f'![Output Image]({image_url})'
                result = '\n'.join(result_lines)

        response = {
            'status': 'success',
            'stdout': stdout,
            'stderr': stderr,
            'result': result,
        }

        return json.dumps(response, ensure_ascii=False)
    except Exception as e:
        log.exception(f'execute_code error: {e}')
        return json.dumps({'error': str(e)})


# =============================================================================
# MEMORY TOOLS
# =============================================================================


async def list_memory_paths(
    query: str = '',
    count: int = 100,
    type: str = 'all',
    __request__: Request = None,
    __user__: dict = None,
) -> str:
    """
    List saved memory paths to find existing memory groups before writing or moving memories.

    :param query: Optional query to filter memory paths or contents
    :param count: Maximum number of paths to return
    :param type: "user", "context", or "all"
    :return: JSON with memory paths, counts, children, and update times
    """
    try:
        user = UserModel(**__user__) if __user__ else None
        result = await _list_memory_paths(
            ListMemoryPathsForm(
                query=query or None,
                type=type if type in {'user', 'context', 'all'} else 'all',
                limit=count,
            ),
            user,
        )
        return json.dumps(result, ensure_ascii=False)
    except Exception as e:
        log.exception(f'list_memory_paths error: {e}')
        return json.dumps({'error': str(e)})


async def read_memory_path(
    path: str,
    count: int = 50,
    type: str = 'all',
    include_children: bool = True,
    __request__: Request = None,
    __user__: dict = None,
) -> str:
    """
    Read saved memories at a memory path, including nearby parent and child paths.

    :param path: Memory path to read
    :param count: Maximum number of memories to return
    :param type: "user", "context", or "all"
    :param include_children: Include memories under child paths
    :return: JSON with parent paths, child paths, and memories at the path
    """
    try:
        user = UserModel(**__user__) if __user__ else None
        result = await _read_memory_path(
            ReadMemoryPathForm(
                path=path,
                type=type if type in {'user', 'context', 'all'} else 'all',
                include_children=include_children,
                limit=count,
            ),
            user,
        )
        return json.dumps(result, ensure_ascii=False)
    except Exception as e:
        log.exception(f'read_memory_path error: {e}')
        return json.dumps({'error': str(e)})


async def search_memories(
    query: str = '',
    count: int = 5,
    type: str = 'all',
    path: Optional[str] = None,
    memory_id: Optional[str] = None,
    __request__: Request = None,
    __user__: dict = None,
) -> str:
    """
    Search or browse saved memories by content, path, type, or memory ID.

    :param query: Optional query to search memory content and path
    :param count: Number of memories to return (default 5)
    :param type: "user", "context", or "all"
    :param path: Optional memory path to search around
    :param memory_id: Optional exact memory ID to read
    :return: JSON with matching memories and their dates
    """
    if __request__ is None:
        return json.dumps({'error': 'Request context not available'})

    try:
        user = UserModel(**__user__) if __user__ else None

        memories = await _search_memories(
            SearchMemoriesForm(
                query=query or None,
                type=type if type in {'user', 'context', 'all'} else 'all',
                path=path,
                memory_id=memory_id,
                limit=count,
            ),
            user,
        )

        if not memories:
            return json.dumps([])

        return json.dumps(
            [
                {
                    'id': memory.id,
                    'type': memory.type,
                    'path': memory.path,
                    'content': memory.content,
                    'created_at': time.strftime('%Y-%m-%d', time.localtime(memory.created_at)),
                    'updated_at': time.strftime('%Y-%m-%d', time.localtime(memory.updated_at)),
                }
                for memory in memories
            ],
            ensure_ascii=False,
        )
    except Exception as e:
        log.exception(f'search_memories error: {e}')
        return json.dumps({'error': str(e)})


async def add_memory(
    content: str,
    type: str = 'user',
    path: Optional[str] = None,
    __request__: Request = None,
    __user__: dict = None,
) -> str:
    """
    Save enduring information that can improve future chats.

    Save stable preferences, goals, projects, relationships, habits, and standing instructions.
    Do not save one-off activity, meals, routine daily events, temporary mood, or other short-lived details
    unless the user explicitly asks you to remember them.

    :param content: The memory content to store
    :param type: Use "user" for facts/preferences about the user, or "context" for other durable context
    :param path: Optional stable memory address for grouping related memories
    :return: Confirmation that the memory was stored
    """
    if __request__ is None:
        return json.dumps({'error': 'Request context not available'})

    try:
        user = UserModel(**__user__) if __user__ else None

        memory = await _add_memory(
            __request__,
            AddMemoryForm(content=content, type=Memories.normalize_memory_type(type), path=path),
            user,
        )

        return json.dumps(
            {'status': 'success', 'id': memory.id, 'type': memory.type, 'path': memory.path},
            ensure_ascii=False,
        )
    except Exception as e:
        log.exception(f'add_memory error: {e}')
        return json.dumps({'error': str(e)})


async def update_memory(
    operations: list[dict],
    __request__: Request = None,
    __user__: dict = None,
) -> str:
    """
    Apply a batch of memory changes after learning enduring information.

    Use type "user" for facts, preferences, or instructions about the user.
    Use type "context" for other durable context that may help future chats.
    Do not save one-off activity, meals, routine daily events, temporary mood, or other short-lived details
    unless the user explicitly asks you to remember them.
    Path is optional. Use it as a stable memory address to group related memories.
    Prefer an existing path from list_memory_paths when one fits.
    Leave path empty when no useful grouping is clear.

    Operation shapes:
    - {"action": "add", "content": "...", "type": "user"|"context", "path": "..."}
    - {"action": "replace", "id": "...", "content": "...", "type": "user"|"context", "path": "..."}
    - {"action": "move", "id": "...", "path": "..."}
    - {"action": "remove", "id": "..."}

    :param operations: Memory operations to apply in one request
    :return: JSON with operation results
    """
    if __request__ is None:
        return json.dumps({'error': 'Request context not available'})

    try:
        user = UserModel(**__user__) if __user__ else None
        operation_results = await _update_memories(
            __request__,
            UpdateMemoriesForm(operations=operations),
            user,
        )
        return json.dumps(operation_results, ensure_ascii=False)
    except Exception as e:
        log.exception(f'update_memory error: {e}')
        return json.dumps({'error': str(e)})


async def replace_memory_content(
    memory_id: str,
    content: str,
    type: Optional[str] = None,
    path: Optional[str] = None,
    __request__: Request = None,
    __user__: dict = None,
) -> str:
    """
    Update an existing saved memory by its ID when its content needs correction.

    :param memory_id: The ID of the memory to update
    :param content: The new content for the memory
    :param type: Optional "user" or "context" type for the updated memory
    :param path: Optional stable memory address for grouping related memories
    :return: Confirmation that the memory was updated
    """
    if __request__ is None:
        return json.dumps({'error': 'Request context not available'})

    try:
        user = UserModel(**__user__) if __user__ else None

        memory = await update_memory_by_id(
            memory_id=memory_id,
            request=__request__,
            form_data=MemoryUpdateModel(
                content=content,
                type=Memories.normalize_memory_type(type) if type else None,
                path=path,
            ),
            user=user,
        )

        return json.dumps(
            {
                'status': 'success',
                'id': memory.id,
                'type': memory.type,
                'path': memory.path,
                'content': memory.content,
            },
            ensure_ascii=False,
        )
    except Exception as e:
        log.exception(f'replace_memory_content error: {e}')
        return json.dumps({'error': str(e)})


async def delete_memory(
    memory_id: str,
    __request__: Request = None,
    __user__: dict = None,
) -> str:
    """
    Delete a saved memory by its ID.

    :param memory_id: The ID of the memory to delete
    :return: Confirmation that the memory was deleted
    """
    if __request__ is None:
        return json.dumps({'error': 'Request context not available'})

    try:
        user = UserModel(**__user__) if __user__ else None

        result = await Memories.delete_memory_by_id_and_user_id(memory_id, user.id)

        if result:
            await ASYNC_VECTOR_DB_CLIENT.delete(collection_name=f'user-memory-{user.id}', ids=[memory_id])
            return json.dumps(
                {'status': 'success', 'message': f'Memory {memory_id} deleted'},
                ensure_ascii=False,
            )
        else:
            return json.dumps({'error': 'Memory not found or access denied'})
    except Exception as e:
        log.exception(f'delete_memory error: {e}')
        return json.dumps({'error': str(e)})


async def list_memories(
    __request__: Request = None,
    __user__: dict = None,
) -> str:
    """
    List all stored memories for the user, including IDs and timestamps.

    :return: JSON list of all memories with id, content, and dates
    """
    if __request__ is None:
        return json.dumps({'error': 'Request context not available'})

    try:
        user = UserModel(**__user__) if __user__ else None

        memories = await Memories.get_memories_by_user_id(user.id)

        if memories:
            memory_rows = [
                {
                    'id': m.id,
                    'type': m.type,
                    'path': m.path,
                    'content': m.content,
                    'created_at': time.strftime('%Y-%m-%d %H:%M', time.localtime(m.created_at)),
                    'updated_at': time.strftime('%Y-%m-%d %H:%M', time.localtime(m.updated_at)),
                }
                for m in memories
            ]
            return json.dumps(memory_rows, ensure_ascii=False)
        else:
            return json.dumps([])
    except Exception as e:
        log.exception(f'list_memories error: {e}')
        return json.dumps({'error': str(e)})


# =============================================================================
# NOTES TOOLS
# =============================================================================


def _get_note_markdown(note) -> str:
    if note.data and note.data.get('content', {}).get('md'):
        return note.data['content']['md']
    return ''


async def _get_note_read_access(note_id: str, __user__: dict):
    """Return (note, error_json) — error_json is set when access is denied or note is missing."""
    note = await Notes.get_note_by_id(note_id)
    if not note:
        return None, json.dumps({'error': 'Note not found'})

    user_id = __user__.get('id')
    user_group_ids = [group.id for group in await Groups.get_groups_by_member_id(user_id)]

    from open_webui.models.access_grants import AccessGrants

    if note.user_id != user_id and not await AccessGrants.has_access(
        user_id=user_id,
        resource_type='note',
        resource_id=note.id,
        permission='read',
        user_group_ids=set(user_group_ids),
    ):
        return None, json.dumps({'error': 'Access denied'})

    return note, None


async def _get_note_write_access(note_id: str, __user__: dict):
    """Return (note, error_json) — error_json is set when write access is denied or note is missing."""
    note = await Notes.get_note_by_id(note_id)
    if not note:
        return None, json.dumps({'error': 'Note not found'})

    user_id = __user__.get('id')
    user_group_ids = [group.id for group in await Groups.get_groups_by_member_id(user_id)]

    from open_webui.models.access_grants import AccessGrants

    if note.user_id != user_id and not await AccessGrants.has_access(
        user_id=user_id,
        resource_type='note',
        resource_id=note.id,
        permission='write',
        user_group_ids=set(user_group_ids),
    ):
        return None, json.dumps({'error': 'Write access denied'})

    return note, None


def _normalize_note_line_range(
    start_line: int,
    end_line: Optional[int],
    total_lines: int,
) -> tuple[int, int] | str:
    """Return (start_idx, end_idx) as 0-based inclusive indices, or an error string."""
    if isinstance(start_line, str):
        try:
            start_line = int(start_line)
        except ValueError:
            return 'start_line must be an integer'
    if end_line is None:
        end_line = start_line
    elif isinstance(end_line, str):
        try:
            end_line = int(end_line)
        except ValueError:
            return 'end_line must be an integer'

    if start_line < 1 or end_line < 1:
        return 'Line numbers are 1-indexed and must be positive'
    if start_line > end_line:
        return 'start_line must be less than or equal to end_line'
    if start_line > total_lines:
        return f'start_line {start_line} is beyond the note length ({total_lines} lines)'

    end_line = min(end_line, total_lines)
    return start_line - 1, end_line - 1


async def _request_user_confirmation(
    title: str,
    message: str,
    __event_call__: callable = None,
) -> bool:
    if __event_call__ is None:
        return False

    result = await __event_call__(
        {
            'type': 'confirmation',
            'data': {
                'title': title,
                'message': message,
            },
        }
    )

    if result is True:
        return True
    if isinstance(result, dict) and result.get('confirmed'):
        return True
    return bool(result)


async def search_notes(
    query: str,
    count: int = 5,
    start_timestamp: Optional[int] = None,
    end_timestamp: Optional[int] = None,
    __request__: Request = None,
    __user__: dict = None,
) -> str:
    """
    Search the user's saved notes by title and content.

    :param query: The search query to find matching notes
    :param count: Maximum number of results to return (default: 5)
    :param start_timestamp: Only include notes updated after this Unix timestamp (seconds)
    :param end_timestamp: Only include notes updated before this Unix timestamp (seconds)
    :return: JSON with matching notes containing id, title, and content snippet
    """
    if __request__ is None:
        return json.dumps({'error': 'Request context not available'})

    if not __user__:
        return json.dumps({'error': 'User context not available'})

    try:
        user_id = __user__.get('id')
        user_group_ids = [group.id for group in await Groups.get_groups_by_member_id(user_id)]

        result = await Notes.search_notes(
            user_id=user_id,
            filter={
                'query': query,
                'user_id': user_id,
                'group_ids': user_group_ids,
                'permission': 'read',
            },
            skip=0,
            limit=count * 3,  # Fetch more for filtering
        )

        # Convert timestamps to nanoseconds for comparison
        start_ts = start_timestamp * 1_000_000_000 if start_timestamp else None
        end_ts = end_timestamp * 1_000_000_000 if end_timestamp else None

        notes = []
        for note in result.items:
            # Apply date filters (updated_at is in nanoseconds)
            if start_ts and note.updated_at < start_ts:
                continue
            if end_ts and note.updated_at > end_ts:
                continue

            # Extract a snippet from the markdown content
            content_snippet = ''
            if note.data and note.data.get('content', {}).get('md'):
                md_content = note.data['content']['md']
                content_lower = md_content.lower()

                # Find the first matching word to center the snippet around.
                search_words = query.lower().split()
                match_pos = -1
                match_len = len(query)
                for word in search_words:
                    found_pos = content_lower.find(word)
                    if found_pos != -1:
                        match_pos = found_pos
                        match_len = len(word)
                        break

                if match_pos != -1:
                    snippet_start = max(0, match_pos - 50)
                    snippet_end = min(len(md_content), match_pos + match_len + 100)
                    content_snippet = (
                        ('...' if snippet_start > 0 else '')
                        + md_content[snippet_start:snippet_end]
                        + ('...' if snippet_end < len(md_content) else '')
                    )
                else:
                    content_snippet = md_content[:150] + ('...' if len(md_content) > 150 else '')

            notes.append(
                {
                    'id': note.id,
                    'title': note.title,
                    'snippet': content_snippet,
                    'updated_at': note.updated_at,
                }
            )

            if len(notes) >= count:
                break

        return json.dumps(notes, ensure_ascii=False)
    except Exception as e:
        log.exception(f'search_notes error: {e}')
        return json.dumps({'error': str(e)})


async def view_note(
    note_id: str,
    __request__: Request = None,
    __user__: dict = None,
) -> str:
    """
    Get the full content of a note by its ID.

    :param note_id: The ID of the note to retrieve
    :return: JSON with the note's id, title, and full markdown content
    """
    if __request__ is None:
        return json.dumps({'error': 'Request context not available'})

    if not __user__:
        return json.dumps({'error': 'User context not available'})

    try:
        note = await Notes.get_note_by_id(note_id)

        if not note:
            return json.dumps({'error': 'Note not found'})

        # Check access permission
        user_id = __user__.get('id')
        user_group_ids = [group.id for group in await Groups.get_groups_by_member_id(user_id)]

        from open_webui.models.access_grants import AccessGrants

        if note.user_id != user_id and not await AccessGrants.has_access(
            user_id=user_id,
            resource_type='note',
            resource_id=note.id,
            permission='read',
            user_group_ids=set(user_group_ids),
        ):
            return json.dumps({'error': 'Access denied'})

        # Extract markdown content
        content = ''
        if note.data and note.data.get('content', {}).get('md'):
            content = note.data['content']['md']

        return json.dumps(
            {
                'id': note.id,
                'title': note.title,
                'content': content,
                'updated_at': note.updated_at,
                'created_at': note.created_at,
            },
            ensure_ascii=False,
        )
    except Exception as e:
        log.exception(f'view_note error: {e}')
        return json.dumps({'error': str(e)})


async def write_note(
    title: str,
    content: str,
    __request__: Request = None,
    __user__: dict = None,
) -> str:
    """
    Create a new note with the given title and content.

    :param title: The title of the new note
    :param content: The markdown content for the note
    :return: JSON with success status and new note id
    """
    if __request__ is None:
        return json.dumps({'error': 'Request context not available'})

    if not __user__:
        return json.dumps({'error': 'User context not available'})

    try:
        from open_webui.models.notes import NoteForm

        user_id = __user__.get('id')

        form = NoteForm(
            title=title,
            data={'content': {'md': content}},
            access_grants=[],  # Private by default - only owner can access
        )

        new_note = await Notes.insert_new_note(user_id, form)

        if not new_note:
            return json.dumps({'error': 'Failed to create note'})

        return json.dumps(
            {
                'status': 'success',
                'id': new_note.id,
                'title': new_note.title,
                'created_at': new_note.created_at,
            },
            ensure_ascii=False,
        )
    except Exception as e:
        log.exception(f'write_note error: {e}')
        return json.dumps({'error': str(e)})


async def replace_note_content(
    note_id: str,
    content: str,
    title: Optional[str] = None,
    __request__: Request = None,
    __user__: dict = None,
) -> str:
    """
    Update the markdown content, and optionally the title, of an existing note.

    :param note_id: The ID of the note to update
    :param content: The new markdown content for the note
    :param title: Optional new title for the note
    :return: JSON with success status and updated note info
    """
    if __request__ is None:
        return json.dumps({'error': 'Request context not available'})

    if not __user__:
        return json.dumps({'error': 'User context not available'})

    try:
        from open_webui.models.notes import NoteUpdateForm

        note = await Notes.get_note_by_id(note_id)

        if not note:
            return json.dumps({'error': 'Note not found'})

        # Check write permission
        user_id = __user__.get('id')
        user_group_ids = [group.id for group in await Groups.get_groups_by_member_id(user_id)]

        from open_webui.models.access_grants import AccessGrants

        if note.user_id != user_id and not await AccessGrants.has_access(
            user_id=user_id,
            resource_type='note',
            resource_id=note.id,
            permission='write',
            user_group_ids=set(user_group_ids),
        ):
            return json.dumps({'error': 'Write access denied'})

        # Build update form
        update_data = {'data': {'content': {'md': content}}}
        if title:
            update_data['title'] = title

        form = NoteUpdateForm(**update_data)
        updated_note = await Notes.update_note_by_id(note_id, form)

        if not updated_note:
            return json.dumps({'error': 'Failed to update note'})

        return json.dumps(
            {
                'status': 'success',
                'id': updated_note.id,
                'title': updated_note.title,
                'updated_at': updated_note.updated_at,
            },
            ensure_ascii=False,
        )
    except Exception as e:
        log.exception(f'replace_note_content error: {e}')
        return json.dumps({'error': str(e)})


async def view_note_lines(
    note_id: str,
    start_line: int,
    end_line: Optional[int] = None,
    line_numbers: bool = True,
    __request__: Request = None,
    __user__: dict = None,
) -> str:
    """
    Read a specific line range from a note without loading the entire content.
    Use this to inspect part of a long note before making targeted edits.

    :param note_id: The ID of the note to read
    :param start_line: First line to read (1-indexed)
    :param end_line: Last line to read, inclusive (1-indexed; defaults to start_line)
    :param line_numbers: Prefix each line with its line number (default: true)
    :return: JSON with id, title, content slice, and line metadata
    """
    if __request__ is None:
        return json.dumps({'error': 'Request context not available'})

    if not __user__:
        return json.dumps({'error': 'User context not available'})

    try:
        note, error = await _get_note_read_access(note_id, __user__)
        if error:
            return error

        lines = _get_note_markdown(note).split('\n')
        line_range = _normalize_note_line_range(start_line, end_line, len(lines) or 1)
        if isinstance(line_range, str):
            return json.dumps({'error': line_range})

        start_idx, end_idx = line_range
        selected = lines[start_idx : end_idx + 1]
        if line_numbers:
            content = '\n'.join(f'{start_idx + i + 1}: {line}' for i, line in enumerate(selected))
        else:
            content = '\n'.join(selected)

        return json.dumps(
            {
                'id': note.id,
                'title': note.title,
                'content': content,
                'start_line': start_idx + 1,
                'end_line': end_idx + 1,
                'total_lines': len(lines),
            },
            ensure_ascii=False,
        )
    except Exception as e:
        log.exception(f'view_note_lines error: {e}')
        return json.dumps({'error': str(e)})


async def update_note_content(
    note_id: str,
    start_line: int,
    content: str,
    end_line: Optional[int] = None,
    __request__: Request = None,
    __user__: dict = None,
) -> str:
    """
    Replace a specific line range in a note without rewriting the entire note.
    Use view_note_lines first to inspect the target section.

    :param note_id: The ID of the note to update
    :param start_line: First line to replace (1-indexed)
    :param content: New markdown content for the line range (may span multiple lines)
    :param end_line: Last line to replace, inclusive (1-indexed; defaults to start_line)
    :return: JSON with success status and updated line metadata
    """
    if __request__ is None:
        return json.dumps({'error': 'Request context not available'})

    if not __user__:
        return json.dumps({'error': 'User context not available'})

    try:
        from open_webui.models.notes import NoteUpdateForm

        note, error = await _get_note_write_access(note_id, __user__)
        if error:
            return error

        lines = _get_note_markdown(note).split('\n')
        total_lines = len(lines)
        line_range = _normalize_note_line_range(start_line, end_line, total_lines or 1)
        if isinstance(line_range, str):
            return json.dumps({'error': line_range})

        start_idx, end_idx = line_range
        replacement_lines = content.split('\n')
        updated_lines = lines[:start_idx] + replacement_lines + lines[end_idx + 1 :]
        updated_content = '\n'.join(updated_lines)

        form = NoteUpdateForm(data={'content': {'md': updated_content}})
        updated_note = await Notes.update_note_by_id(note_id, form)

        if not updated_note:
            return json.dumps({'error': 'Failed to update note'})

        return json.dumps(
            {
                'status': 'success',
                'id': updated_note.id,
                'title': updated_note.title,
                'start_line': start_idx + 1,
                'end_line': end_idx + 1,
                'replaced_line_count': end_idx - start_idx + 1,
                'inserted_line_count': len(replacement_lines),
                'total_lines': len(updated_lines),
                'updated_at': updated_note.updated_at,
            },
            ensure_ascii=False,
        )
    except Exception as e:
        log.exception(f'update_note_content error: {e}')
        return json.dumps({'error': str(e)})


async def delete_note(
    note_id: str,
    __request__: Request = None,
    __user__: dict = None,
    __event_call__: callable = None,
) -> str:
    """
    Permanently delete a note. Requires user confirmation in the chat UI.

    :param note_id: The ID of the note to delete
    :return: JSON with success status or cancellation/error details
    """
    if __request__ is None:
        return json.dumps({'error': 'Request context not available'})

    if not __user__:
        return json.dumps({'error': 'User context not available'})

    try:
        note, error = await _get_note_write_access(note_id, __user__)
        if error:
            return error

        if __event_call__ is None:
            return json.dumps({'error': 'Delete requires an active browser session for confirmation'})

        confirmed = await _request_user_confirmation(
            title='Delete note?',
            message=f'This will permanently delete "{note.title}".',
            __event_call__=__event_call__,
        )
        if not confirmed:
            return json.dumps(
                {
                    'status': 'cancelled',
                    'message': 'Note deletion cancelled by user',
                }
            )

        deleted = await Notes.delete_note_by_id(note_id)
        if not deleted:
            return json.dumps({'error': 'Failed to delete note'})

        return json.dumps(
            {
                'status': 'success',
                'id': note_id,
                'title': note.title,
            },
            ensure_ascii=False,
        )
    except Exception as e:
        log.exception(f'delete_note error: {e}')
        return json.dumps({'error': str(e)})


# =============================================================================
# CHATS TOOLS
# =============================================================================


async def search_chats(
    query: str,
    count: int = 5,
    start_timestamp: Optional[int] = None,
    end_timestamp: Optional[int] = None,
    __request__: Request = None,
    __user__: dict = None,
    __chat_id__: str = None,
) -> str:
    """
    Search the user's previous chat conversations by title and message content.
    Helpful for finding details from earlier conversations.

    :param query: The search query to find matching chats
    :param count: Maximum number of results to return (default: 5)
    :param start_timestamp: Only include chats updated after this Unix timestamp (seconds)
    :param end_timestamp: Only include chats updated before this Unix timestamp (seconds)
    :return: JSON with matching chats containing id, title, updated_at, and content snippet
    """
    if __request__ is None:
        return json.dumps({'error': 'Request context not available'})

    if not __user__:
        return json.dumps({'error': 'User context not available'})

    try:
        user_id = __user__.get('id')

        chats = await Chats.get_chats_by_user_id_and_search_text(
            user_id=user_id,
            search_text=query,
            include_archived=False,
            skip=0,
            limit=count * 3,  # Fetch more for filtering
        )

        results = []
        for chat in chats:
            # Skip the current chat to avoid showing it in search results
            if __chat_id__ and chat.id == __chat_id__:
                continue

            # Apply date filters (updated_at is in seconds)
            if start_timestamp and chat.updated_at < start_timestamp:
                continue
            if end_timestamp and chat.updated_at > end_timestamp:
                continue

            # Find a matching message snippet
            snippet = ''
            messages = (getattr(chat, 'chat', None) or {}).get('history', {}).get('messages', {})
            lower_query = query.lower()

            for msg_id, msg in messages.items():
                content = msg.get('content', '')
                if isinstance(content, str) and lower_query in content.lower():
                    idx = content.lower().find(lower_query)
                    start = max(0, idx - 50)
                    end = min(len(content), idx + len(query) + 100)
                    snippet = ('...' if start > 0 else '') + content[start:end] + ('...' if end < len(content) else '')
                    break

            if not snippet and lower_query in chat.title.lower():
                snippet = f'Title match: {chat.title}'

            results.append(
                {
                    'id': chat.id,
                    'title': chat.title,
                    'snippet': snippet,
                    'updated_at': chat.updated_at,
                }
            )

            if len(results) >= count:
                break

        return json.dumps(results, ensure_ascii=False)
    except Exception as e:
        log.exception(f'search_chats error: {e}')
        return json.dumps({'error': str(e)})


async def view_chat(
    chat_id: str,
    __request__: Request = None,
    __user__: dict = None,
) -> str:
    """
    Get the full conversation history of a chat by its ID after a relevant
    previous chat has been identified.

    :param chat_id: The ID of the chat to retrieve
    :return: JSON with the chat's id, title, and messages
    """
    if __request__ is None:
        return json.dumps({'error': 'Request context not available'})

    if not __user__:
        return json.dumps({'error': 'User context not available'})

    try:
        user_id = __user__.get('id')

        chat = await Chats.get_chat_by_id_and_user_id(chat_id, user_id)

        if not chat:
            return json.dumps({'error': 'Chat not found or access denied'})

        # Extract messages from history
        messages = []
        history = chat.chat.get('history', {})
        msg_dict = history.get('messages', {})

        # Build message chain from currentId
        current_id = history.get('currentId')
        visited = set()

        while current_id and current_id not in visited:
            visited.add(current_id)
            msg = msg_dict.get(current_id)
            if msg:
                messages.append(
                    {
                        'role': msg.get('role', ''),
                        'content': msg.get('content', ''),
                    }
                )
            current_id = msg.get('parentId') if msg else None

        # Reverse to get chronological order
        messages.reverse()

        return json.dumps(
            {
                'id': chat.id,
                'title': chat.title,
                'messages': messages,
                'updated_at': chat.updated_at,
                'created_at': chat.created_at,
            },
            ensure_ascii=False,
        )
    except Exception as e:
        log.exception(f'view_chat error: {e}')
        return json.dumps({'error': str(e)})


async def update_chat(
    chat_id: str,
    title: Optional[str] = None,
    tags: Optional[list[str]] = None,
    __request__: Request = None,
    __user__: dict = None,
) -> str:
    """
    Update a chat's title and/or tags.

    :param chat_id: The ID of the chat to update
    :param title: Optional new title for the chat
    :param tags: Optional list of tag names to set on the chat
    :return: JSON with the updated chat metadata
    """
    if __request__ is None:
        return json.dumps({'error': 'Request context not available'})

    if not __user__:
        return json.dumps({'error': 'User context not available'})

    if title is None and tags is None:
        return json.dumps({'error': 'Provide at least one of title or tags to update'})

    try:
        from types import SimpleNamespace

        user_id = __user__.get('id')
        chat = await Chats.get_chat_by_id_and_user_id(chat_id, user_id)

        if not chat:
            return json.dumps({'error': 'Chat not found or access denied'})

        updated_chat = chat
        if title is not None:
            updated = await Chats.update_chat_title_by_id(chat_id, title)
            if not updated:
                return json.dumps({'error': 'Failed to update chat title'})
            updated_chat = updated

        if tags is not None:
            updated = await Chats.update_chat_tags_by_id(chat_id, tags, SimpleNamespace(id=user_id))
            if not updated:
                return json.dumps({'error': 'Failed to update chat tags'})
            updated_chat = updated

        return json.dumps(
            {
                'status': 'success',
                'id': updated_chat.id,
                'title': updated_chat.title,
                'tags': updated_chat.meta.get('tags', []),
                'updated_at': updated_chat.updated_at,
            },
            ensure_ascii=False,
        )
    except Exception as e:
        log.exception(f'update_chat error: {e}')
        return json.dumps({'error': str(e)})


async def archive_chat(
    chat_id: str,
    __request__: Request = None,
    __user__: dict = None,
) -> str:
    """
    Archive a chat so it is hidden from the main chat list.

    :param chat_id: The ID of the chat to archive
    :return: JSON with success status and archived chat metadata
    """
    if __request__ is None:
        return json.dumps({'error': 'Request context not available'})

    if not __user__:
        return json.dumps({'error': 'User context not available'})

    try:
        user_id = __user__.get('id')
        chat = await Chats.get_chat_by_id_and_user_id(chat_id, user_id)

        if not chat:
            return json.dumps({'error': 'Chat not found or access denied'})

        if chat.archived:
            return json.dumps(
                {
                    'status': 'already_archived',
                    'id': chat.id,
                    'title': chat.title,
                },
                ensure_ascii=False,
            )

        updated_chat = await Chats.toggle_chat_archive_by_id(chat_id)
        if not updated_chat:
            return json.dumps({'error': 'Failed to archive chat'})

        tag_ids = updated_chat.meta.get('tags', [])
        if tag_ids:
            await Chats.delete_orphan_tags_for_user(tag_ids, user_id)

        return json.dumps(
            {
                'status': 'success',
                'id': updated_chat.id,
                'title': updated_chat.title,
                'archived': updated_chat.archived,
            },
            ensure_ascii=False,
        )
    except Exception as e:
        log.exception(f'archive_chat error: {e}')
        return json.dumps({'error': str(e)})


async def list_folders(
    __request__: Request = None,
    __user__: dict = None,
) -> str:
    """
    List chat folders the user can access.
    Use the returned folder id with move_chat_to_folder (write permission required).

    :return: JSON list of folders with id, name, parent_id, owned, and permission
    """
    if __request__ is None:
        return json.dumps({'error': 'Request context not available'})

    if not __user__:
        return json.dumps({'error': 'User context not available'})

    try:
        from open_webui.internal.db import get_async_db_context
        from open_webui.models.folders import Folders
        from open_webui.models.users import Users
        from open_webui.utils.access_control import has_permission

        user_id = __user__.get('id')
        config = await Config.get_many('folders.enable', 'user.permissions')

        if config.get('folders.enable') is False:
            return json.dumps({'error': 'Folders are disabled'})

        if __user__.get('role') != 'admin' and not await has_permission(
            user_id,
            'features.folders',
            config.get('user.permissions'),
        ):
            return json.dumps({'error': 'Access denied'})

        async with get_async_db_context() as db:
            owned_folders = await Folders.get_folders_by_user_id(user_id, db=db)
            groups = await Groups.get_groups_by_member_id(user_id, db=db)
            group_ids = {group.id for group in groups}
            shared_perms = await Folders.get_shared_folder_ids_for_user(user_id, group_ids, db=db)

            folders = []
            seen_ids = set()

            for folder in owned_folders:
                folders.append(
                    {
                        'id': folder.id,
                        'name': folder.name,
                        'parent_id': folder.parent_id,
                        'owned': True,
                        'permission': 'write',
                    }
                )
                seen_ids.add(folder.id)

            owner_cache = {}
            for folder_id, permission in shared_perms.items():
                if folder_id in seen_ids:
                    continue

                folder = await Folders.get_folder_by_id(folder_id, db=db)
                if not folder or folder.user_id == user_id:
                    continue

                if folder.user_id not in owner_cache:
                    owner = await Users.get_user_by_id(folder.user_id, db=db)
                    owner_cache[folder.user_id] = owner.name if owner else 'Unknown'

                folders.append(
                    {
                        'id': folder.id,
                        'name': folder.name,
                        'parent_id': folder.parent_id,
                        'owned': False,
                        'owner_name': owner_cache[folder.user_id],
                        'permission': permission,
                    }
                )
                seen_ids.add(folder.id)

            # Include subfolders of shared folders (inherit parent permission)
            for entry in list(folders):
                if entry.get('owned'):
                    continue
                root = await Folders.get_folder_by_id(entry['id'], db=db)
                if not root:
                    continue
                children = await Folders.get_children_folders_by_id_and_user_id(root.id, root.user_id, db=db)
                if not children:
                    continue
                for child in children:
                    if child.id in seen_ids:
                        continue
                    folders.append(
                        {
                            'id': child.id,
                            'name': child.name,
                            'parent_id': child.parent_id,
                            'owned': False,
                            'owner_name': owner_cache.get(child.user_id, 'Unknown'),
                            'permission': entry['permission'],
                        }
                    )
                    seen_ids.add(child.id)

            folders.sort(key=lambda f: (f.get('name') or '').lower())

            return json.dumps(
                {
                    'folders': folders,
                    'total': len(folders),
                },
                ensure_ascii=False,
            )
    except Exception as e:
        log.exception(f'list_folders error: {e}')
        return json.dumps({'error': str(e)})


async def create_folder(
    name: str,
    parent_id: Optional[str] = None,
    __request__: Request = None,
    __user__: dict = None,
) -> str:
    """
    Create a new chat folder, optionally nested under a parent folder.

    :param name: The folder name
    :param parent_id: Optional parent folder ID for a subfolder
    :return: JSON with the new folder id, name, and parent_id
    """
    if __request__ is None:
        return json.dumps({'error': 'Request context not available'})

    if not __user__:
        return json.dumps({'error': 'User context not available'})

    if not name or not name.strip():
        return json.dumps({'error': 'Folder name is required'})

    try:
        from open_webui.internal.db import get_async_db_context
        from open_webui.models.folders import FolderForm, Folders
        from open_webui.utils.access_control import has_permission
        from open_webui.utils.access_control.folders import has_folder_access

        user_id = __user__.get('id')
        config = await Config.get_many('folders.enable', 'user.permissions')

        if config.get('folders.enable') is False:
            return json.dumps({'error': 'Folders are disabled'})

        if __user__.get('role') != 'admin' and not await has_permission(
            user_id,
            'features.folders',
            config.get('user.permissions'),
        ):
            return json.dumps({'error': 'Access denied'})

        form_data = FolderForm(name=name.strip(), parent_id=parent_id)

        async with get_async_db_context() as db:
            existing = await Folders.get_folder_by_parent_id_and_user_id_and_name(
                parent_id, user_id, form_data.name, db=db
            )
            if existing:
                return json.dumps({'error': 'Folder already exists'})

            owner_id = user_id
            if parent_id:
                parent = await Folders.get_folder_by_id(parent_id, db=db)
                if not parent:
                    return json.dumps({'error': 'Parent folder not found'})
                if parent.user_id != user_id:
                    if __user__.get('role') != 'admin' and not await has_folder_access(
                        user_id, parent, 'write', db
                    ):
                        return json.dumps({'error': 'Write access denied for parent folder'})
                    owner_id = parent.user_id

            folder = await Folders.insert_new_folder(owner_id, form_data, parent_id, db=db)
            if not folder:
                return json.dumps({'error': 'Failed to create folder'})

            return json.dumps(
                {
                    'status': 'success',
                    'id': folder.id,
                    'name': folder.name,
                    'parent_id': folder.parent_id,
                },
                ensure_ascii=False,
            )
    except Exception as e:
        log.exception(f'create_folder error: {e}')
        return json.dumps({'error': str(e)})


async def move_chat_to_folder(
    chat_id: str,
    folder_id: Optional[str] = None,
    __request__: Request = None,
    __user__: dict = None,
) -> str:
    """
    Move a chat into a folder, or remove it from its current folder.

    :param chat_id: The ID of the chat to move
    :param folder_id: Target folder ID, or omit/null to remove the chat from any folder
    :return: JSON with success status and updated folder assignment
    """
    if __request__ is None:
        return json.dumps({'error': 'Request context not available'})

    if not __user__:
        return json.dumps({'error': 'User context not available'})

    try:
        from open_webui.internal.db import get_async_db_context
        from open_webui.models.folders import Folders
        from open_webui.utils.access_control.folders import has_folder_access

        user_id = __user__.get('id')

        async with get_async_db_context() as db:
            chat = await Chats.get_chat_by_id_and_user_id(chat_id, user_id, db=db)

            if not chat:
                return json.dumps({'error': 'Chat not found or access denied'})

            if folder_id:
                if not await Folders.get_folder_by_id_and_user_id(folder_id, user_id, db=db):
                    shared_folder = await Folders.get_folder_by_id(folder_id, db=db)
                    if not shared_folder or not await has_folder_access(user_id, shared_folder, 'write', db):
                        return json.dumps({'error': 'Folder not found or write access denied'})

            updated_chat = await Chats.update_chat_folder_id_by_id_and_user_id(
                chat_id, user_id, folder_id, db=db
            )

            if not updated_chat:
                return json.dumps({'error': 'Failed to move chat'})

            return json.dumps(
                {
                    'status': 'success',
                    'id': updated_chat.id,
                    'title': updated_chat.title,
                    'folder_id': updated_chat.folder_id,
                },
                ensure_ascii=False,
            )
    except Exception as e:
        log.exception(f'move_chat_to_folder error: {e}')
        return json.dumps({'error': str(e)})


# =============================================================================
# CHANNELS TOOLS
# =============================================================================


async def search_channels(
    query: str,
    count: int = 5,
    __request__: Request = None,
    __user__: dict = None,
) -> str:
    """
    Search channels by name and description to find accessible team spaces.

    :param query: The search query to find matching channels
    :param count: Maximum number of results to return (default: 5)
    :return: JSON with matching channels containing id, name, description, and type
    """
    if __request__ is None:
        return json.dumps({'error': 'Request context not available'})

    if not __user__:
        return json.dumps({'error': 'User context not available'})

    try:
        user_id = __user__.get('id')

        # Get all channels the user has access to
        all_channels = await Channels.get_channels_by_user_id(user_id)

        # Filter by query
        lower_query = query.lower()
        matching_channels = []

        for channel in all_channels:
            name_match = lower_query in channel.name.lower() if channel.name else False
            desc_match = lower_query in (channel.description or '').lower()

            if name_match or desc_match:
                matching_channels.append(
                    {
                        'id': channel.id,
                        'name': channel.name,
                        'description': channel.description or '',
                        'type': channel.type or 'public',
                    }
                )

            if len(matching_channels) >= count:
                break

        return json.dumps(matching_channels, ensure_ascii=False)
    except Exception as e:
        log.exception(f'search_channels error: {e}')
        return json.dumps({'error': str(e)})


async def search_channel_messages(
    query: str,
    count: int = 10,
    start_timestamp: Optional[int] = None,
    end_timestamp: Optional[int] = None,
    __request__: Request = None,
    __user__: dict = None,
) -> str:
    """
    Search messages in channels the user is a member of, including thread replies.
    Helpful for finding prior team/channel discussion.

    :param query: The search query to find matching messages
    :param count: Maximum number of results to return (default: 10)
    :param start_timestamp: Only include messages created after this Unix timestamp (seconds)
    :param end_timestamp: Only include messages created before this Unix timestamp (seconds)
    :return: JSON with matching messages containing channel info, message content, and thread context
    """
    if __request__ is None:
        return json.dumps({'error': 'Request context not available'})

    if not __user__:
        return json.dumps({'error': 'User context not available'})

    try:
        user_id = __user__.get('id')

        # Get all channels the user has access to
        user_channels = await Channels.get_channels_by_user_id(user_id)
        channel_ids = [c.id for c in user_channels]
        channel_map = {c.id: c for c in user_channels}

        if not channel_ids:
            return json.dumps([])

        # Convert timestamps to nanoseconds (Message.created_at is in nanoseconds)
        start_ts = start_timestamp * 1_000_000_000 if start_timestamp else None
        end_ts = end_timestamp * 1_000_000_000 if end_timestamp else None

        # Search messages using the model method
        matching_messages = await Messages.search_messages_by_channel_ids(
            channel_ids=channel_ids,
            query=query,
            start_timestamp=start_ts,
            end_timestamp=end_ts,
            limit=count,
        )

        results = []
        for msg in matching_messages:
            channel = channel_map.get(msg.channel_id)

            # Extract snippet around the match
            content = msg.content or ''
            lower_query = query.lower()
            idx = content.lower().find(lower_query)
            if idx != -1:
                start = max(0, idx - 50)
                end = min(len(content), idx + len(query) + 100)
                snippet = ('...' if start > 0 else '') + content[start:end] + ('...' if end < len(content) else '')
            else:
                snippet = content[:150] + ('...' if len(content) > 150 else '')

            results.append(
                {
                    'channel_id': msg.channel_id,
                    'channel_name': channel.name if channel else 'Unknown',
                    'message_id': msg.id,
                    'content_snippet': snippet,
                    'is_thread_reply': msg.parent_id is not None,
                    'parent_id': msg.parent_id,
                    'created_at': msg.created_at,
                }
            )

        return json.dumps(results, ensure_ascii=False)
    except Exception as e:
        log.exception(f'search_channel_messages error: {e}')
        return json.dumps({'error': str(e)})


async def view_channel_message(
    message_id: str,
    __request__: Request = None,
    __user__: dict = None,
) -> str:
    """
    Get the full content of a channel message by its ID, including thread replies.

    :param message_id: The ID of the message to retrieve
    :return: JSON with the message content, channel info, and thread replies if any
    """
    if __request__ is None:
        return json.dumps({'error': 'Request context not available'})

    if not __user__:
        return json.dumps({'error': 'User context not available'})

    try:
        user_id = __user__.get('id')

        message = await Messages.get_message_by_id(message_id)

        if not message:
            return json.dumps({'error': 'Message not found'})

        # Verify user has access to the channel
        channel = await Channels.get_channel_by_id(message.channel_id)
        if not channel:
            return json.dumps({'error': 'Channel not found'})

        # Check if user has access to the channel
        user_channels = await Channels.get_channels_by_user_id(user_id)
        channel_ids = [c.id for c in user_channels]

        if message.channel_id not in channel_ids:
            return json.dumps({'error': 'Access denied'})

        # Build response with thread information
        result = {
            'id': message.id,
            'channel_id': message.channel_id,
            'channel_name': channel.name,
            'content': message.content,
            'user_id': message.user_id,
            'is_thread_reply': message.parent_id is not None,
            'parent_id': message.parent_id,
            'reply_count': message.reply_count,
            'created_at': message.created_at,
            'updated_at': message.updated_at,
        }

        # Include user info if available
        if message.user:
            result['user_name'] = message.user.name

        return json.dumps(result, ensure_ascii=False)
    except Exception as e:
        log.exception(f'view_channel_message error: {e}')
        return json.dumps({'error': str(e)})


async def view_channel_thread(
    parent_message_id: str,
    __request__: Request = None,
    __user__: dict = None,
) -> str:
    """
    Get all messages in a channel thread, including the parent message and all replies.

    :param parent_message_id: The ID of the parent message that started the thread
    :return: JSON with the parent message and all thread replies in chronological order
    """
    if __request__ is None:
        return json.dumps({'error': 'Request context not available'})

    if not __user__:
        return json.dumps({'error': 'User context not available'})

    try:
        user_id = __user__.get('id')

        # Get the parent message
        parent_message = await Messages.get_message_by_id(parent_message_id)

        if not parent_message:
            return json.dumps({'error': 'Message not found'})

        # Verify user has access to the channel
        channel = await Channels.get_channel_by_id(parent_message.channel_id)
        if not channel:
            return json.dumps({'error': 'Channel not found'})

        user_channels = await Channels.get_channels_by_user_id(user_id)
        channel_ids = [c.id for c in user_channels]

        if parent_message.channel_id not in channel_ids:
            return json.dumps({'error': 'Access denied'})

        # Get all thread replies
        thread_replies = await Messages.get_thread_replies_by_message_id(parent_message_id)

        # Build the response
        messages = []

        # Add parent message first
        messages.append(
            {
                'id': parent_message.id,
                'content': parent_message.content,
                'user_id': parent_message.user_id,
                'user_name': parent_message.user.name if parent_message.user else None,
                'is_parent': True,
                'created_at': parent_message.created_at,
            }
        )

        # Add thread replies (reverse to get chronological order)
        for reply in reversed(thread_replies):
            messages.append(
                {
                    'id': reply.id,
                    'content': reply.content,
                    'user_id': reply.user_id,
                    'user_name': reply.user.name if reply.user else None,
                    'is_parent': False,
                    'reply_to_id': reply.reply_to_id,
                    'created_at': reply.created_at,
                }
            )

        return json.dumps(
            {
                'channel_id': parent_message.channel_id,
                'channel_name': channel.name,
                'thread_id': parent_message_id,
                'message_count': len(messages),
                'messages': messages,
            },
            ensure_ascii=False,
        )
    except Exception as e:
        log.exception(f'view_channel_thread error: {e}')
        return json.dumps({'error': str(e)})


# =============================================================================
# KNOWLEDGE BASE TOOLS
# =============================================================================


async def search_knowledge_bases(
    query: str,
    count: int = 5,
    skip: int = 0,
    __request__: Request = None,
    __user__: dict = None,
) -> str:
    """
    Search the user's accessible knowledge bases by name and description to find
    a relevant internal source.

    :param query: The search query to find matching knowledge bases
    :param count: Maximum number of results to return (default: 5)
    :param skip: Number of results to skip for pagination (default: 0)
    :return: JSON with matching KBs containing id, name, description, and file_count
    """
    if __request__ is None:
        return json.dumps({'error': 'Request context not available'})

    if not __user__:
        return json.dumps({'error': 'User context not available'})

    try:
        from open_webui.models.knowledge import Knowledges

        user_id = __user__.get('id')
        user_group_ids = [group.id for group in await Groups.get_groups_by_member_id(user_id)]

        result = await Knowledges.search_knowledge_bases(
            user_id,
            filter={
                'query': query,
                'user_id': user_id,
                'group_ids': user_group_ids,
            },
            skip=skip,
            limit=count,
        )

        knowledge_bases = []
        for knowledge_base in result.items:
            files = await Knowledges.get_files_by_id(knowledge_base.id)
            file_count = len(files) if files else 0

            knowledge_bases.append(
                {
                    'id': knowledge_base.id,
                    'name': knowledge_base.name,
                    'description': knowledge_base.description or '',
                    'file_count': file_count,
                    'updated_at': knowledge_base.updated_at,
                }
            )

        return json.dumps(knowledge_bases, ensure_ascii=False)
    except Exception as e:
        log.exception(f'search_knowledge_bases error: {e}')
        return json.dumps({'error': str(e)})


# =============================================================================
# FILES TOOLS
# =============================================================================

MAX_VIEW_FILE_CHARS = 100_000
DEFAULT_VIEW_FILE_MAX_CHARS = 10_000


async def search_files(
    query: str = '*',
    count: int = 20,
    __request__: Request = None,
    __user__: dict = None,
) -> str:
    """
    Search the user's uploaded files by filename.
    Supports wildcards (e.g. "*.pdf", "report*"). Use view_file to read a file's content.

    :param query: Filename search text or glob pattern (default: all files)
    :param count: Maximum number of results to return (default: 20)
    :return: JSON list of matching files with id, filename, and timestamps
    """
    if __request__ is None:
        return json.dumps({'error': 'Request context not available'})

    if not __user__:
        return json.dumps({'error': 'User context not available'})

    try:
        from open_webui.config import BYPASS_ADMIN_ACCESS_CONTROL
        from open_webui.models.files import Files

        user_id = __user__.get('id')
        user_role = __user__.get('role', 'user')

        if isinstance(count, str):
            try:
                count = int(count)
            except ValueError:
                count = 20

        count = max(1, min(count, 100))

        filename = query.strip() if query else '*'
        if filename and '*' not in filename and '?' not in filename:
            filename = f'*{filename}*'

        search_user_id = user_id
        if user_role == 'admin' and BYPASS_ADMIN_ACCESS_CONTROL:
            search_user_id = None

        files = await Files.search_files(
            user_id=search_user_id,
            filename=filename,
            skip=0,
            limit=count,
        )

        results = []
        for file in files:
            meta = file.meta.model_dump() if hasattr(file.meta, 'model_dump') else (file.meta or {})
            results.append(
                {
                    'id': file.id,
                    'filename': file.filename,
                    'created_at': file.created_at,
                    'updated_at': file.updated_at,
                    'content_type': meta.get('content_type'),
                }
            )

        return json.dumps(
            {
                'files': results,
                'total': len(results),
            },
            ensure_ascii=False,
        )
    except Exception as e:
        log.exception(f'search_files error: {e}')
        return json.dumps({'error': str(e)})


async def view_file(
    file_id: str,
    offset: int = 0,
    max_chars: int = DEFAULT_VIEW_FILE_MAX_CHARS,
    line_numbers: bool = False,
    start_line: Optional[int] = None,
    end_line: Optional[int] = None,
    __request__: Request = None,
    __user__: dict = None,
    __model_knowledge__: Optional[list[dict]] = None,
) -> str:
    """
    Get the content of a file by its ID. Supports pagination for large files.

    :param file_id: The ID of the file to retrieve
    :param offset: Character offset to start reading from (default: 0)
    :param max_chars: Maximum characters to return (default: 10000, hard cap: 100000)
    :param line_numbers: If true, prefix each line with its 1-indexed line number
    :param start_line: Optional 1-indexed start line (overrides offset/max_chars when set)
    :param end_line: Optional 1-indexed end line (inclusive)
    :return: JSON with the file's id, filename, content, and pagination metadata if truncated
    """
    if __request__ is None:
        return json.dumps({'error': 'Request context not available'})

    if not __user__:
        return json.dumps({'error': 'User context not available'})

    # Coerce parameters from LLM tool calls (may come as strings)
    if isinstance(offset, str):
        try:
            offset = int(offset)
        except ValueError:
            offset = 0
    if isinstance(max_chars, str):
        try:
            max_chars = int(max_chars)
        except ValueError:
            max_chars = DEFAULT_VIEW_FILE_MAX_CHARS

    # Enforce hard cap
    max_chars = min(max(max_chars, 1), MAX_VIEW_FILE_CHARS)
    offset = max(offset, 0)

    try:
        from open_webui.models.files import Files

        user_id = __user__.get('id')
        user_role = __user__.get('role', 'user')

        file = await Files.get_file_by_id(file_id)
        if not file:
            return json.dumps({'error': 'File not found'})

        if not await _has_read_access_to_file(file, user_id, user_role, __model_knowledge__):
            return json.dumps({'error': 'File not found'})

        content = ''
        if file.data:
            content = file.data.get('content', '')

        total_chars = len(content)

        # Line-based addressing (overrides char-based offset/max_chars)
        if start_line is not None:
            all_lines = content.split('\n')
            total_lines = len(all_lines)
            s = max(1, int(start_line)) - 1  # 1-indexed to 0-indexed
            e = min(total_lines, int(end_line) if end_line else s + 100)
            selected = all_lines[s:e]
            sliced = '\n'.join(f'{s + i + 1}: {line}' for i, line in enumerate(selected))
            is_truncated = e < total_lines
            result = {
                'id': file.id,
                'filename': file.filename,
                'content': sliced,
                'updated_at': file.updated_at,
                'created_at': file.created_at,
                'total_lines': total_lines,
                'showing_lines': f'{s + 1}-{e}',
            }
            if is_truncated:
                result['truncated'] = True
                result['next_start_line'] = e + 1
            return json.dumps(result, ensure_ascii=False)

        sliced = content[offset : offset + max_chars]
        is_truncated = (offset + len(sliced)) < total_chars

        if line_numbers:
            start_ln = content[:offset].count('\n') + 1
            lines = sliced.split('\n')
            sliced = '\n'.join(f'{start_ln + i}: {line}' for i, line in enumerate(lines))

        result = {
            'id': file.id,
            'filename': file.filename,
            'content': sliced,
            'updated_at': file.updated_at,
            'created_at': file.created_at,
        }

        if is_truncated or offset > 0:
            result['truncated'] = is_truncated
            result['total_chars'] = total_chars
            result['returned_chars'] = len(sliced)
            result['offset'] = offset
            if is_truncated:
                result['next_offset'] = offset + len(sliced)

        return json.dumps(result, ensure_ascii=False)
    except Exception as e:
        log.exception(f'view_file error: {e}')
        return json.dumps({'error': str(e)})


async def query_knowledge_files(
    query: str,
    knowledge_ids: Optional[list[str]] = None,
    count: int = 5,
    __request__: Request = None,
    __user__: dict = None,
    __model_knowledge__: list[dict] = None,
) -> str:
    """
    Search knowledge base files using semantic/vector search. Searches across collections (KBs),
    individual files, and notes that the user has access to.
    Helpful for internal documentation, uploaded knowledge, and attached model knowledge.

    :param query: The search query to find semantically relevant content
    :param knowledge_ids: Optional list of KB ids to limit search to specific knowledge bases
    :param count: Maximum number of results to return (default: 5)
    :return: JSON with relevant chunks containing content, source filename, and relevance score
    """
    if __request__ is None:
        return json.dumps({'error': 'Request context not available'})

    if not __user__:
        return json.dumps({'error': 'User context not available'})

    # Coerce parameters from LLM tool calls (may come as strings)
    if isinstance(count, str):
        try:
            count = int(count)
        except ValueError:
            count = 5  # Default fallback

    # Handle knowledge_ids being string "None", "null", or empty
    if isinstance(knowledge_ids, str):
        if knowledge_ids.lower() in ('none', 'null', ''):
            knowledge_ids = None
        else:
            # Try to parse as JSON array if it looks like one
            try:
                knowledge_ids = json.loads(knowledge_ids)
            except json.JSONDecodeError:
                # Treat as single ID
                knowledge_ids = [knowledge_ids]

    try:
        from open_webui.models.access_grants import AccessGrants
        from open_webui.models.files import Files
        from open_webui.models.knowledge import Knowledges
        from open_webui.models.notes import Notes
        from open_webui.retrieval.external import retrieve_external_knowledge
        from open_webui.retrieval.utils import query_collection

        user_id = __user__.get('id')
        user_role = __user__.get('role', 'user')
        user_group_ids = [group.id for group in await Groups.get_groups_by_member_id(user_id)]

        embedding_function = __request__.app.state.EMBEDDING_FUNCTION
        if not embedding_function:
            return json.dumps({'error': 'Embedding function not configured'})

        collection_names = []
        external_knowledges = []
        note_results = []  # Notes aren't vectorized, handle separately

        # If model has attached knowledge, use those
        if __model_knowledge__:
            for item in __model_knowledge__:
                item_type = item.get('type')
                item_id = item.get('id')

                if item_type == 'collection':
                    # Knowledge base - use KB ID as collection name
                    knowledge = await Knowledges.get_knowledge_by_id(item_id)
                    if knowledge and (
                        user_role == 'admin'
                        or knowledge.user_id == user_id
                        or await AccessGrants.has_access(
                            user_id=user_id,
                            resource_type='knowledge',
                            resource_id=knowledge.id,
                            permission='read',
                            user_group_ids=set(user_group_ids),
                        )
                    ):
                        if (knowledge.meta or {}).get('source') == 'external':
                            external_knowledges.append(knowledge)
                        else:
                            collection_names.append(item_id)

                elif item_type == 'file':
                    # Individual file - use file-{id} as collection name
                    file = await Files.get_file_by_id(item_id)
                    if file:
                        collection_names.append(f'file-{item_id}')

                elif item_type == 'note':
                    # Note - always return full content as context
                    note = await Notes.get_note_by_id(item_id)
                    if note and (
                        user_role == 'admin'
                        or note.user_id == user_id
                        or await AccessGrants.has_access(
                            user_id=user_id,
                            resource_type='note',
                            resource_id=note.id,
                            permission='read',
                        )
                    ):
                        content = note.data.get('content', {}).get('md', '')
                        note_results.append(
                            {
                                'content': content,
                                'source': note.title,
                                'note_id': note.id,
                                'type': 'note',
                            }
                        )

        elif knowledge_ids:
            # User specified specific KBs
            for knowledge_id in knowledge_ids:
                knowledge = await Knowledges.get_knowledge_by_id(knowledge_id)
                if knowledge and (
                    user_role == 'admin'
                    or knowledge.user_id == user_id
                    or await AccessGrants.has_access(
                        user_id=user_id,
                        resource_type='knowledge',
                        resource_id=knowledge.id,
                        permission='read',
                        user_group_ids=set(user_group_ids),
                    )
                ):
                    if (knowledge.meta or {}).get('source') == 'external':
                        external_knowledges.append(knowledge)
                    else:
                        collection_names.append(knowledge_id)
        else:
            # No model knowledge and no specific IDs - search all accessible KBs
            result = await Knowledges.search_knowledge_bases(
                user_id,
                filter={
                    'query': '',
                    'user_id': user_id,
                    'group_ids': user_group_ids,
                },
                skip=0,
                limit=50,
            )
            for knowledge_base in result.items:
                if (knowledge_base.meta or {}).get('source') == 'external':
                    external_knowledges.append(knowledge_base)
                else:
                    collection_names.append(knowledge_base.id)

        chunks = []

        # Add note results first
        chunks.extend(note_results)

        # Query vector collections if any
        if collection_names:
            query_results = await query_collection(
                __request__,
                collection_names=collection_names,
                queries=[query],
                embedding_function=embedding_function,
                k=count,
            )

            if query_results and 'documents' in query_results:
                documents = query_results.get('documents', [[]])[0]
                metadatas = query_results.get('metadatas', [[]])[0]
                distances = query_results.get('distances', [[]])[0]

                for idx, doc in enumerate(documents):
                    chunk_info = {
                        'content': doc,
                        'source': metadatas[idx].get('source', metadatas[idx].get('name', 'Unknown')),
                        'file_id': metadatas[idx].get('file_id', ''),
                    }
                    if idx < len(distances):
                        chunk_info['distance'] = distances[idx]
                    chunks.append(chunk_info)

        for knowledge in external_knowledges:
            query_results = await retrieve_external_knowledge(
                __request__,
                knowledge,
                queries=[query],
                count=count,
                user=type('UserContext', (), {'id': user_id, 'role': user_role})(),
            )
            documents = query_results.get('documents', [[]])[0]
            metadatas = query_results.get('metadatas', [[]])[0]
            distances = query_results.get('distances', [[]])[0]

            for idx, doc in enumerate(documents):
                metadata = metadatas[idx] if idx < len(metadatas) else {}
                chunk_info = {
                    'content': doc,
                    'source': metadata.get('source', metadata.get('name', knowledge.name)),
                    'file_id': metadata.get('file_id', f'external-{knowledge.id}'),
                    'type': 'external',
                    'knowledge_id': knowledge.id,
                }
                if idx < len(distances):
                    chunk_info['distance'] = distances[idx]
                chunks.append(chunk_info)

        # Limit to requested count
        chunks = chunks[:count]

        return json.dumps(chunks, ensure_ascii=False)
    except Exception as e:
        log.exception(f'query_knowledge_files error: {e}')
        return json.dumps({'error': str(e)})


async def query_knowledge_bases(
    query: str,
    count: int = 5,
    __request__: Request = None,
    __user__: dict = None,
) -> str:
    """
    Search knowledge bases by semantic similarity to query.
    Finds KBs whose name/description match the meaning of your query.
    Helpful for discovering which knowledge base to query next.

    :param query: Natural language query describing what you're looking for
    :param count: Maximum results (default: 5)
    :return: JSON with matching KBs (id, name, description, similarity)
    """
    if __request__ is None:
        return json.dumps({'error': 'Request context not available'})

    if not __user__:
        return json.dumps({'error': 'User context not available'})

    try:
        import heapq

        from open_webui.models.knowledge import Knowledges
        from open_webui.retrieval.vector.async_client import ASYNC_VECTOR_DB_CLIENT
        from open_webui.routers.knowledge import KNOWLEDGE_BASES_COLLECTION

        user_id = __user__.get('id')
        user_group_ids = [group.id for group in await Groups.get_groups_by_member_id(user_id)]
        query_embedding = await __request__.app.state.EMBEDDING_FUNCTION(query)

        # Min-heap of (distance, knowledge_base_id) - only holds top `count` results
        top_results_heap = []
        seen_ids = set()
        page_offset = 0
        page_size = 100

        while True:
            accessible_knowledge_bases = await Knowledges.search_knowledge_bases(
                user_id,
                filter={'user_id': user_id, 'group_ids': user_group_ids},
                skip=page_offset,
                limit=page_size,
            )

            if not accessible_knowledge_bases.items:
                break

            accessible_ids = [kb.id for kb in accessible_knowledge_bases.items]

            search_results = await ASYNC_VECTOR_DB_CLIENT.search(
                collection_name=KNOWLEDGE_BASES_COLLECTION,
                vectors=[query_embedding],
                filter={'knowledge_base_id': {'$in': accessible_ids}},
                limit=count,
            )

            if search_results and search_results.ids and search_results.ids[0]:
                result_ids = search_results.ids[0]
                result_distances = search_results.distances[0] if search_results.distances else [0] * len(result_ids)

                for knowledge_base_id, distance in zip(result_ids, result_distances):
                    if knowledge_base_id in seen_ids:
                        continue
                    seen_ids.add(knowledge_base_id)

                    if len(top_results_heap) < count:
                        heapq.heappush(top_results_heap, (distance, knowledge_base_id))
                    elif distance > top_results_heap[0][0]:
                        heapq.heapreplace(top_results_heap, (distance, knowledge_base_id))

            page_offset += page_size
            if len(accessible_knowledge_bases.items) < page_size:
                break
            if page_offset >= MAX_KNOWLEDGE_BASE_SEARCH_ITEMS:
                break

        # Sort by distance descending (best first) and fetch KB details
        sorted_results = sorted(top_results_heap, key=lambda x: x[0], reverse=True)

        matching_knowledge_bases = []
        for distance, knowledge_base_id in sorted_results:
            knowledge_base = await Knowledges.get_knowledge_by_id(knowledge_base_id)
            if knowledge_base:
                matching_knowledge_bases.append(
                    {
                        'id': knowledge_base.id,
                        'name': knowledge_base.name,
                        'description': knowledge_base.description or '',
                        'similarity': round(distance, 4),
                    }
                )

        return json.dumps(matching_knowledge_bases, ensure_ascii=False)

    except Exception as e:
        log.exception(f'query_knowledge_bases error: {e}')
        return json.dumps({'error': str(e)})


# =============================================================================
# SKILLS TOOLS
# =============================================================================


async def search_skills(
    query: str,
    count: int = 5,
    __request__: Request = None,
    __user__: dict = None,
) -> str:
    """
    Search available skills by name, description, or id.
    Use view_skill to load the full instructions for a matching skill.

    :param query: Search text to match against skill name, description, or id
    :param count: Maximum number of results to return (default: 5)
    :return: JSON list of matching skills with id, name, and description
    """
    if __request__ is None:
        return json.dumps({'error': 'Request context not available'})

    if not __user__:
        return json.dumps({'error': 'User context not available'})

    try:
        from open_webui.models.skills import Skills

        user_id = __user__.get('id')
        user_group_ids = [group.id for group in await Groups.get_groups_by_member_id(user_id)]

        if isinstance(count, str):
            try:
                count = int(count)
            except ValueError:
                count = 5

        result = await Skills.search_skills(
            user_id=user_id,
            filter={
                'query': query,
                'user_id': user_id,
                'group_ids': user_group_ids,
                'permission': 'read',
            },
            skip=0,
            limit=count,
        )

        skills = []
        for skill in result.items:
            if not skill.is_active:
                continue
            skills.append(
                {
                    'id': skill.id,
                    'name': skill.name,
                    'description': skill.description or '',
                }
            )

        return json.dumps(
            {
                'skills': skills,
                'total': result.total,
            },
            ensure_ascii=False,
        )
    except Exception as e:
        log.exception(f'search_skills error: {e}')
        return json.dumps({'error': str(e)})


async def view_skill(
    id: str,
    __request__: Request = None,
    __user__: dict = None,
) -> str:
    """
    Load the full instructions of a skill by its id from the available skills manifest.
    Use this when you need detailed instructions for a skill listed in <available_skills>.

    :param id: The id of the skill to load (as shown in the manifest)
    :return: The full skill instructions as markdown content
    """
    if __request__ is None:
        return json.dumps({'error': 'Request context not available'})

    if not __user__:
        return json.dumps({'error': 'User context not available'})

    try:
        from open_webui.models.access_grants import AccessGrants
        from open_webui.models.skills import Skills

        user_id = __user__.get('id')

        # Direct DB lookup by id (case-insensitive since IDs are stored lowercase)
        skill = await Skills.get_skill_by_id(id.lower())

        if not skill or not skill.is_active:
            return json.dumps({'error': f"Skill '{id}' not found"})

        # Check user access
        user_role = __user__.get('role', 'user')
        if user_role != 'admin' and skill.user_id != user_id:
            user_group_ids = [group.id for group in await Groups.get_groups_by_member_id(user_id)]
            if not await AccessGrants.has_access(
                user_id=user_id,
                resource_type='skill',
                resource_id=skill.id,
                permission='read',
                user_group_ids=set(user_group_ids),
            ):
                return json.dumps({'error': 'Access denied'})

        return json.dumps(
            {
                'name': skill.name,
                'content': skill.content,
            },
            ensure_ascii=False,
        )
    except Exception as e:
        log.exception(f'view_skill error: {e}')
        return json.dumps({'error': str(e)})


# =============================================================================
# TASK MANAGEMENT TOOLS
# =============================================================================

from typing import Literal

from pydantic import BaseModel, Field

VALID_TASK_STATUSES = {'pending', 'in_progress', 'completed', 'cancelled'}


class TaskItem(BaseModel):
    id: Optional[str] = Field(None, description='Unique identifier for the task. Auto-generated if omitted.')
    content: str = Field(..., description='Task description.')
    status: Literal['pending', 'in_progress', 'completed', 'cancelled'] = Field('pending', description='Task status.')


def _task_summary(all_tasks: list[dict]) -> dict:
    """Build summary counts for a task list."""
    pending = sum(1 for t in all_tasks if t['status'] == 'pending')
    in_progress = sum(1 for t in all_tasks if t['status'] == 'in_progress')
    completed = sum(1 for t in all_tasks if t['status'] == 'completed')
    cancelled = sum(1 for t in all_tasks if t['status'] == 'cancelled')
    return {
        'total': len(all_tasks),
        'pending': pending,
        'in_progress': in_progress,
        'completed': completed,
        'cancelled': cancelled,
    }


async def _emit_tasks(event_emitter, all_tasks: list[dict]):
    """Persist task state to the UI."""
    if event_emitter:
        await event_emitter(
            {
                'type': 'chat:message:tasks',
                'data': {
                    'tasks': all_tasks,
                },
            }
        )


async def create_tasks(
    tasks: list[TaskItem],
    __chat_id__: str = None,
    __message_id__: str = None,
    __event_emitter__: callable = None,
    __request__: Request = None,
    __user__: dict = None,
) -> str:
    """
    Create a visible task checklist for multi-step work so progress can be shown in chat.

    :param tasks: List of task items. Each item: content (string, required), status (pending|in_progress|completed|cancelled, default pending), id (optional, auto-generated).
    :return: JSON with the full task list and summary counts
    """
    if __chat_id__ is None:
        return json.dumps({'error': 'Chat context not available'})

    try:
        all_tasks = []
        for idx, task in enumerate(tasks):
            if hasattr(task, 'model_dump'):
                d = task.model_dump(exclude_none=True)
            elif isinstance(task, dict):
                d = task
            else:
                d = dict(task)

            content = str(d.get('content', '')).strip()
            if not content:
                continue

            item_id = str(d.get('id', '') or '').strip() or str(idx + 1)
            status = str(d.get('status', 'pending')).strip().lower()
            if status not in VALID_TASK_STATUSES:
                status = 'pending'

            all_tasks.append({'id': item_id, 'content': content, 'status': status})

        await Chats.update_chat_tasks_by_id(__chat_id__, all_tasks)
        await _emit_tasks(__event_emitter__, all_tasks)

        return json.dumps(
            {'tasks': all_tasks, 'summary': _task_summary(all_tasks)},
            ensure_ascii=False,
        )
    except Exception as e:
        log.exception(f'tasks error: {e}')
        return json.dumps({'error': str(e)})


async def update_task(
    id: str,
    status: str = 'completed',
    __chat_id__: str = None,
    __message_id__: str = None,
    __event_emitter__: callable = None,
    __request__: Request = None,
    __user__: dict = None,
) -> str:
    """
    Mark a single visible task item as completed, in_progress, pending, or cancelled.

    :param id: The task ID to update
    :param status: New status: completed, in_progress, pending, or cancelled (default: completed)
    :return: JSON with the updated task list and summary counts
    """
    if __chat_id__ is None:
        return json.dumps({'error': 'Chat context not available'})

    try:
        status = status.strip().lower()
        if status not in VALID_TASK_STATUSES:
            return json.dumps(
                {'error': f'Invalid status: {status}. Must be one of: {", ".join(sorted(VALID_TASK_STATUSES))}'}
            )

        all_tasks = await Chats.get_chat_tasks_by_id(__chat_id__)

        found = False
        for task in all_tasks:
            if task['id'] == id:
                task['status'] = status
                found = True
                break

        if not found:
            return json.dumps({'error': f'Task with id "{id}" not found'})

        await Chats.update_chat_tasks_by_id(__chat_id__, all_tasks)
        await _emit_tasks(__event_emitter__, all_tasks)

        return json.dumps(
            {'tasks': all_tasks, 'summary': _task_summary(all_tasks)},
            ensure_ascii=False,
        )
    except Exception as e:
        log.exception(f'update_task_status error: {e}')
        return json.dumps({'error': str(e)})


# =============================================================================
# AUTOMATION TOOLS
# =============================================================================


async def create_automation(
    name: str,
    prompt: str,
    rrule: str,
    __request__: Request = None,
    __user__: dict = None,
    __metadata__: dict = None,
) -> str:
    """
    Create a scheduled automation that runs a prompt on a recurring or one-time schedule.
    Use this when the user wants to schedule a task to run automatically.
    The automation will use the current chat model.

    The rrule parameter must be a valid iCalendar RRULE string. Common examples:
    - Every day at 9am: "DTSTART:20250101T090000\\nRRULE:FREQ=DAILY"
    - Every Monday at 8am: "DTSTART:20250106T080000\\nRRULE:FREQ=WEEKLY;BYDAY=MO"
    - Every hour: "RRULE:FREQ=HOURLY;INTERVAL=1"
    - Every 30 minutes: "RRULE:FREQ=MINUTELY;INTERVAL=30"
    - Once at a specific time: "DTSTART:20250415T140000\\nRRULE:FREQ=DAILY;COUNT=1"
    - First day of every month: "DTSTART:20250101T090000\\nRRULE:FREQ=MONTHLY;BYMONTHDAY=1"

    The DTSTART time should reflect the desired execution time. Use COUNT=1 for one-time automations.

    :param name: A short descriptive name for the automation
    :param prompt: The prompt/instructions to execute on each run
    :param rrule: An iCalendar RRULE string defining the schedule
    :return: JSON with the created automation details including id, next scheduled runs
    """
    if __request__ is None:
        return json.dumps({'error': 'Request context not available'})

    if not __user__:
        return json.dumps({'error': 'User context not available'})

    try:
        from open_webui.models.automations import AutomationData, AutomationForm, Automations
        from open_webui.models.users import Users
        from open_webui.utils.automations import next_n_runs_ns, next_run_ns, validate_rrule

        user_id = __user__.get('id')
        user = await Users.get_user_by_id(user_id)
        if not user:
            return json.dumps({'error': 'User not found'})

        # Fall back to model dict ID since __metadata__ may predate model_id assignment
        metadata = __metadata__ or {}
        model_id = metadata.get('model_id') or (
            metadata.get('model', {}).get('id') if isinstance(metadata.get('model'), dict) else None
        )
        if not model_id:
            return json.dumps({'error': 'Could not detect current model'})

        # Validate the RRULE
        try:
            validate_rrule(rrule, tz=user.timezone)
        except ValueError as e:
            return json.dumps({'error': f'Invalid schedule: {e}'})

        tz = user.timezone
        form = AutomationForm(
            name=name,
            data=AutomationData(
                prompt=prompt,
                model_id=model_id,
                rrule=rrule,
            ),
            is_active=True,
        )

        automation = await Automations.insert(user_id, form, next_run_ns(rrule, tz=tz))

        return json.dumps(
            {
                'status': 'success',
                'id': automation.id,
                'name': automation.name,
                'model_id': model_id,
                'is_active': automation.is_active,
                'next_runs': next_n_runs_ns(rrule, tz=tz),
            },
            ensure_ascii=False,
        )
    except Exception as e:
        log.exception(f'create_automation error: {e}')
        return json.dumps({'error': str(e)})


async def update_automation(
    automation_id: str,
    name: Optional[str] = None,
    prompt: Optional[str] = None,
    rrule: Optional[str] = None,
    model_id: Optional[str] = None,
    __request__: Request = None,
    __user__: dict = None,
) -> str:
    """
    Update an existing automation. Only the provided fields are changed; omitted fields stay the same.

    :param automation_id: The ID of the automation to update
    :param name: New name for the automation (optional)
    :param prompt: New prompt/instructions (optional)
    :param rrule: New iCalendar RRULE schedule string (optional). See create_automation for format examples.
    :param model_id: New model ID to use (optional)
    :return: JSON with the updated automation details
    """
    if __request__ is None:
        return json.dumps({'error': 'Request context not available'})

    if not __user__:
        return json.dumps({'error': 'User context not available'})

    try:
        from open_webui.models.automations import AutomationData, AutomationForm, Automations
        from open_webui.models.users import Users
        from open_webui.utils.automations import next_n_runs_ns, next_run_ns, validate_rrule

        user_id = __user__.get('id')
        user = await Users.get_user_by_id(user_id)

        automation = await Automations.get_by_id(automation_id)
        if not automation:
            return json.dumps({'error': 'Automation not found'})
        if automation.user_id != user_id:
            return json.dumps({'error': 'Access denied'})

        # Merge provided fields with existing values
        new_name = name if name is not None else automation.name
        new_prompt = prompt if prompt is not None else automation.data.get('prompt', '')
        new_model_id = model_id if model_id is not None else automation.data.get('model_id', '')
        new_rrule = rrule if rrule is not None else automation.data.get('rrule', '')

        # Validate RRULE if changed
        if rrule is not None:
            try:
                validate_rrule(new_rrule, tz=user.timezone if user else None)
            except ValueError as e:
                return json.dumps({'error': f'Invalid schedule: {e}'})

        tz = user.timezone if user else None
        form = AutomationForm(
            name=new_name,
            data=AutomationData(
                prompt=new_prompt,
                model_id=new_model_id,
                rrule=new_rrule,
            ),
            is_active=automation.is_active,
        )

        updated = await Automations.update_by_id(automation_id, form, next_run_ns(new_rrule, tz=tz))

        return json.dumps(
            {
                'status': 'success',
                'id': updated.id,
                'name': updated.name,
                'model_id': new_model_id,
                'is_active': updated.is_active,
                'next_runs': next_n_runs_ns(new_rrule, tz=tz),
            },
            ensure_ascii=False,
        )
    except Exception as e:
        log.exception(f'update_automation error: {e}')
        return json.dumps({'error': str(e)})


async def list_automations(
    status: Optional[str] = None,
    count: int = 10,
    __request__: Request = None,
    __user__: dict = None,
) -> str:
    """
    List the user's scheduled automations.

    :param status: Filter by status: "active", "paused", or omit for all
    :param count: Maximum number of automations to return (default: 10)
    :return: JSON list of automations with id, name, prompt snippet, schedule, status, and next runs
    """
    if __request__ is None:
        return json.dumps({'error': 'Request context not available'})

    if not __user__:
        return json.dumps({'error': 'User context not available'})

    try:
        from open_webui.models.automations import Automations
        from open_webui.models.users import Users
        from open_webui.utils.automations import next_n_runs_ns

        user_id = __user__.get('id')
        user = await Users.get_user_by_id(user_id)

        result = await Automations.search_automations(
            user_id=user_id,
            status=status,
            skip=0,
            limit=count,
        )

        automations = []
        for item in result.items:
            rrule = item.data.get('rrule', '')
            prompt_text = item.data.get('prompt', '')
            snippet = prompt_text[:100] + ('...' if len(prompt_text) > 100 else '')

            automations.append(
                {
                    'id': item.id,
                    'name': item.name,
                    'prompt_snippet': snippet,
                    'model_id': item.data.get('model_id', ''),
                    'rrule': rrule,
                    'is_active': item.is_active,
                    'last_run_at': item.last_run_at,
                    'next_runs': next_n_runs_ns(rrule, tz=user.timezone if user else None),
                }
            )

        return json.dumps(
            {'automations': automations, 'total': result.total},
            ensure_ascii=False,
        )
    except Exception as e:
        log.exception(f'list_automations error: {e}')
        return json.dumps({'error': str(e)})


async def toggle_automation(
    automation_id: str,
    __request__: Request = None,
    __user__: dict = None,
) -> str:
    """
    Pause or resume a scheduled automation. If active, it will be paused. If paused, it will be resumed.

    :param automation_id: The ID of the automation to toggle
    :return: JSON with the updated automation status
    """
    if __request__ is None:
        return json.dumps({'error': 'Request context not available'})

    if not __user__:
        return json.dumps({'error': 'User context not available'})

    try:
        from open_webui.models.automations import Automations
        from open_webui.models.users import Users
        from open_webui.utils.automations import next_run_ns

        user_id = __user__.get('id')
        user = await Users.get_user_by_id(user_id)

        automation = await Automations.get_by_id(automation_id)
        if not automation:
            return json.dumps({'error': 'Automation not found'})
        if automation.user_id != user_id:
            return json.dumps({'error': 'Access denied'})

        rrule = automation.data.get('rrule', '')
        toggled = await Automations.toggle(
            automation_id,
            next_run_ns(rrule, tz=user.timezone if user else None),
        )

        return json.dumps(
            {
                'status': 'success',
                'id': toggled.id,
                'name': toggled.name,
                'is_active': toggled.is_active,
            },
            ensure_ascii=False,
        )
    except Exception as e:
        log.exception(f'toggle_automation error: {e}')
        return json.dumps({'error': str(e)})


async def delete_automation(
    automation_id: str,
    __request__: Request = None,
    __user__: dict = None,
) -> str:
    """
    Delete a scheduled automation and all its run history.

    :param automation_id: The ID of the automation to delete
    :return: JSON confirming the automation was deleted
    """
    if __request__ is None:
        return json.dumps({'error': 'Request context not available'})

    if not __user__:
        return json.dumps({'error': 'User context not available'})

    try:
        from open_webui.models.automations import AutomationRuns, Automations

        user_id = __user__.get('id')

        automation = await Automations.get_by_id(automation_id)
        if not automation:
            return json.dumps({'error': 'Automation not found'})
        if automation.user_id != user_id:
            return json.dumps({'error': 'Access denied'})

        name = automation.name
        await AutomationRuns.delete_by_automation(automation_id)
        await Automations.delete(automation_id)

        return json.dumps(
            {
                'status': 'success',
                'message': f'Automation "{name}" deleted',
            },
            ensure_ascii=False,
        )
    except Exception as e:
        log.exception(f'delete_automation error: {e}')
        return json.dumps({'error': str(e)})


# =============================================================================
# CALENDAR TOOLS
# =============================================================================


def _get_user_tz(user_dict: dict):
    """Get the user's timezone as a ZoneInfo, falling back to UTC."""
    from zoneinfo import ZoneInfo

    tz_name = None
    if user_dict:
        tz_name = user_dict.get('timezone')
    if tz_name:
        try:
            return ZoneInfo(tz_name)
        except Exception:
            pass
    return ZoneInfo('UTC')


def _dt_to_ns(dt_str: str, tz) -> int:
    """Convert a datetime string to nanoseconds since epoch, interpreting in the given timezone."""
    from datetime import datetime

    dt = datetime.fromisoformat(dt_str)
    # If naive (no timezone info), localize to user's timezone
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=tz)
    return int(dt.timestamp() * 1_000) * 1_000_000


def _ns_to_dt(ns: int, tz) -> str:
    """Convert nanoseconds since epoch to a datetime string in the given timezone."""
    from datetime import datetime

    seconds = ns / 1_000_000_000
    dt = datetime.fromtimestamp(seconds, tz=tz)
    return dt.strftime('%Y-%m-%d %H:%M')


def _event_to_dict(event, tz) -> dict:
    """Convert a calendar event model to a human-friendly dict with local timestamps."""
    alert_minutes = None
    if event.meta and 'alert_minutes' in event.meta:
        alert_minutes = event.meta['alert_minutes']
    return {
        'id': event.id,
        'calendar_id': event.calendar_id,
        'title': event.title,
        'description': event.description or '',
        'start': _ns_to_dt(event.start_at, tz),
        'end': _ns_to_dt(event.end_at, tz) if event.end_at else None,
        'all_day': event.all_day,
        'location': event.location or '',
        'reminder_minutes': alert_minutes if alert_minutes is not None else 10,
        'color': event.color,
        'is_cancelled': event.is_cancelled,
    }


async def list_calendars(
    __request__: Request = None,
    __user__: dict = None,
) -> str:
    """
    List calendars available to the user.
    Use the returned calendar_id when creating or updating events.

    :return: JSON list of calendars with id, name, color, and is_default
    """
    if __request__ is None:
        return json.dumps({'error': 'Request context not available'})

    if not __user__:
        return json.dumps({'error': 'User context not available'})

    try:
        from open_webui.models.calendar import Calendars

        user_id = __user__.get('id')
        calendars = await Calendars.get_calendars_by_user(user_id)

        return json.dumps(
            {
                'calendars': [
                    {
                        'id': cal.id,
                        'name': cal.name,
                        'color': cal.color,
                        'is_default': cal.is_default,
                    }
                    for cal in calendars
                ],
                'total': len(calendars),
            },
            ensure_ascii=False,
        )
    except Exception as e:
        log.exception(f'list_calendars error: {e}')
        return json.dumps({'error': str(e)})


async def search_calendar_events(
    query: Optional[str] = None,
    start: Optional[str] = None,
    end: Optional[str] = None,
    count: int = 10,
    __request__: Request = None,
    __user__: dict = None,
) -> str:
    """
    Search calendar events, reminders, and scheduled items by text and/or date range.
    Helpful for finding upcoming events, reminders, or schedule items.

    :param query: Search text to match against event title, description, or location (optional)
    :param start: Only return events starting at or after this datetime, e.g. "2026-04-20 00:00" (optional)
    :param end: Only return events starting before this datetime, e.g. "2026-04-27 00:00" (optional)
    :param count: Maximum number of events to return (default: 10)
    :return: JSON list of matching events with id, title, description, start, end, calendar_id, location
    """
    if __request__ is None:
        return json.dumps({'error': 'Request context not available'})

    if not __user__:
        return json.dumps({'error': 'User context not available'})

    try:
        from open_webui.models.calendar import CalendarEvents

        user_id = __user__.get('id')
        tz = _get_user_tz(__user__)

        if isinstance(count, str):
            try:
                count = int(count)
            except ValueError:
                count = 10

        if start or end:
            # Date range query — use get_events_by_range
            try:
                start_ns = _dt_to_ns(start, tz) if start else 0
            except (ValueError, TypeError) as e:
                return json.dumps({'error': f'Invalid start datetime: {e}'})

            try:
                end_ns = (
                    _dt_to_ns(end, tz)
                    if end
                    else int(time.time() * 1_000) * 1_000_000 + 365 * 86400 * 1_000_000_000_000
                )
            except (ValueError, TypeError) as e:
                return json.dumps({'error': f'Invalid end datetime: {e}'})

            items = await CalendarEvents.get_events_by_range(
                user_id=user_id,
                start=start_ns,
                end=end_ns,
            )

            # Apply text filter if query is also provided
            if query:
                q = query.lower()
                items = [
                    e
                    for e in items
                    if q in (e.title or '').lower()
                    or q in (e.description or '').lower()
                    or q in (e.location or '').lower()
                ]

            events = [_event_to_dict(item, tz) for item in items[:count]]
            return json.dumps(
                {'events': events, 'total': len(items)},
                ensure_ascii=False,
            )
        else:
            # Text-only search
            result = await CalendarEvents.search_events(
                user_id=user_id,
                query=query,
                skip=0,
                limit=count,
            )

            events = [_event_to_dict(item, tz) for item in result.items]
            return json.dumps(
                {'events': events, 'total': result.total},
                ensure_ascii=False,
            )
    except Exception as e:
        log.exception(f'search_calendar_events error: {e}')
        return json.dumps({'error': str(e)})


async def create_calendar_event(
    title: str,
    start: str,
    end: Optional[str] = None,
    description: Optional[str] = None,
    calendar_id: Optional[str] = None,
    all_day: bool = False,
    location: Optional[str] = None,
    reminder_minutes: Optional[int] = None,
    __request__: Request = None,
    __user__: dict = None,
) -> str:
    """
    Create a calendar event, reminder, or alarm. Use this when the user wants to
    schedule an event, set a reminder, create an alarm, or says things like
    "remind me", "don't let me forget", "notify me at", or "add to my calendar".
    For simple reminders, omit end/location/all_day and set reminder_minutes to 0.

    :param title: Event or reminder title (e.g. "Team standup", "Take medicine", "Call mom")
    :param start: Start datetime in the user's local time (e.g. "2026-04-20 09:00")
    :param end: End datetime in the user's local time (optional — omit for reminders or point-in-time events)
    :param description: Event description or notes (optional)
    :param calendar_id: Target calendar ID (optional, uses default calendar if omitted)
    :param all_day: Whether this is an all-day event (default: false)
    :param location: Event location (optional)
    :param reminder_minutes: Minutes before the event to send a notification (optional, default: 10). Use 0 for "at time of event", -1 for no notification.
    :return: JSON with the created event details including id
    """
    if __request__ is None:
        return json.dumps({'error': 'Request context not available'})

    if not __user__:
        return json.dumps({'error': 'User context not available'})

    try:
        from open_webui.models.calendar import CalendarEventForm, CalendarEvents, Calendars

        user_id = __user__.get('id')

        # Resolve calendar_id: use provided, or fall back to default
        if not calendar_id:
            calendars = await Calendars.get_calendars_by_user(user_id)
            default_cal = next((c for c in calendars if c.is_default), None)
            if not default_cal and calendars:
                default_cal = calendars[0]
            if not default_cal:
                return json.dumps({'error': 'No calendars found. Cannot create event.'})
            calendar_id = default_cal.id

        # Verify access
        cal = await Calendars.get_calendar_by_id(calendar_id)
        if not cal:
            return json.dumps({'error': 'Calendar not found'})
        if cal.user_id != user_id and __user__.get('role') != 'admin':
            from open_webui.models.access_grants import AccessGrants
            from open_webui.models.groups import Groups

            user_group_ids = [g.id for g in await Groups.get_groups_by_member_id(user_id)]
            if not await AccessGrants.has_access(
                user_id=user_id,
                resource_type='calendar',
                resource_id=cal.id,
                permission='write',
                user_group_ids=set(user_group_ids),
            ):
                return json.dumps({'error': 'Access denied to this calendar'})

        # Coerce boolean from LLM
        if isinstance(all_day, str):
            all_day = all_day.lower() in ('true', '1', 'yes')

        # Convert datetime strings to nanoseconds using user's timezone
        tz = _get_user_tz(__user__)
        try:
            start_ns = _dt_to_ns(start, tz)
        except (ValueError, TypeError) as e:
            return json.dumps({'error': f'Invalid start datetime: {e}. Use format like "2026-04-20 09:00"'})

        end_ns = None
        if end:
            try:
                end_ns = _dt_to_ns(end, tz)
            except (ValueError, TypeError) as e:
                return json.dumps({'error': f'Invalid end datetime: {e}. Use format like "2026-04-20 10:00"'})
        elif not all_day:
            # Default to 1 hour duration
            end_ns = start_ns + 3_600_000_000_000

        # Build meta with reminder setting
        meta = {}
        if reminder_minutes is not None:
            if isinstance(reminder_minutes, str):
                try:
                    reminder_minutes = int(reminder_minutes)
                except ValueError:
                    reminder_minutes = 10
            meta['alert_minutes'] = reminder_minutes
        else:
            meta['alert_minutes'] = 10

        form = CalendarEventForm(
            calendar_id=calendar_id,
            title=title,
            description=description,
            start_at=start_ns,
            end_at=end_ns,
            all_day=all_day,
            location=location,
            meta=meta,
        )

        event = await CalendarEvents.insert_new_event(user_id, form)
        if not event:
            return json.dumps({'error': 'Failed to create event'})

        return json.dumps(
            {
                'status': 'success',
                **_event_to_dict(event, tz),
            },
            ensure_ascii=False,
        )
    except Exception as e:
        log.exception(f'create_calendar_event error: {e}')
        return json.dumps({'error': str(e)})


async def update_calendar_event(
    event_id: str,
    title: Optional[str] = None,
    description: Optional[str] = None,
    start: Optional[str] = None,
    end: Optional[str] = None,
    all_day: Optional[bool] = None,
    location: Optional[str] = None,
    is_cancelled: Optional[bool] = None,
    reminder_minutes: Optional[int] = None,
    __request__: Request = None,
    __user__: dict = None,
) -> str:
    """
    Update an existing calendar event. Only provided fields are changed;
    omitted fields stay the same.

    :param event_id: The ID of the event to update
    :param title: New event title (optional)
    :param description: New event description (optional)
    :param start: New start datetime string in your local time, e.g. "2026-04-20 09:00" (optional)
    :param end: New end datetime string in your local time (optional)
    :param all_day: Whether this is an all-day event (optional)
    :param location: New event location (optional)
    :param is_cancelled: Set to true to cancel the event (optional)
    :param reminder_minutes: Minutes before the event to send a reminder notification (optional). Use 0 for "at time of event", -1 for no reminder. Accepts any positive integer for custom timing (e.g. 120 for 2 hours before).
    :return: JSON with the updated event details
    """
    if __request__ is None:
        return json.dumps({'error': 'Request context not available'})

    if not __user__:
        return json.dumps({'error': 'User context not available'})

    try:
        from open_webui.models.access_grants import AccessGrants
        from open_webui.models.calendar import CalendarEvents, CalendarEventUpdateForm, Calendars
        from open_webui.models.groups import Groups

        user_id = __user__.get('id')

        event = await CalendarEvents.get_event_by_id(event_id)
        if not event:
            return json.dumps({'error': 'Event not found'})

        # Check write access to the event's calendar
        if event.user_id != user_id and __user__.get('role') != 'admin':
            cal = await Calendars.get_calendar_by_id(event.calendar_id)
            if not cal:
                return json.dumps({'error': 'Access denied'})
            user_group_ids = [g.id for g in await Groups.get_groups_by_member_id(user_id)]
            if not await AccessGrants.has_access(
                user_id=user_id,
                resource_type='calendar',
                resource_id=cal.id,
                permission='write',
                user_group_ids=set(user_group_ids),
            ):
                return json.dumps({'error': 'Access denied'})

        # Coerce boolean strings from LLM
        if isinstance(all_day, str):
            all_day = all_day.lower() in ('true', '1', 'yes')
        if isinstance(is_cancelled, str):
            is_cancelled = is_cancelled.lower() in ('true', '1', 'yes')

        # Convert datetime strings to nanoseconds using user's timezone
        tz = _get_user_tz(__user__)
        start_ns = None
        if start is not None:
            try:
                start_ns = _dt_to_ns(start, tz)
            except (ValueError, TypeError) as e:
                return json.dumps({'error': f'Invalid start datetime: {e}'})

        end_ns = None
        if end is not None:
            try:
                end_ns = _dt_to_ns(end, tz)
            except (ValueError, TypeError) as e:
                return json.dumps({'error': f'Invalid end datetime: {e}'})

        # Build meta update with reminder setting if provided
        meta = None
        if reminder_minutes is not None:
            if isinstance(reminder_minutes, str):
                try:
                    reminder_minutes = int(reminder_minutes)
                except ValueError:
                    reminder_minutes = None
            if reminder_minutes is not None:
                meta = {'alert_minutes': reminder_minutes}

        form = CalendarEventUpdateForm(
            title=title,
            description=description,
            start_at=start_ns,
            end_at=end_ns,
            all_day=all_day,
            location=location,
            is_cancelled=is_cancelled,
            meta=meta,
        )

        updated = await CalendarEvents.update_event_by_id(event_id, form)
        if not updated:
            return json.dumps({'error': 'Failed to update event'})

        return json.dumps(
            {
                'status': 'success',
                **_event_to_dict(updated, tz),
            },
            ensure_ascii=False,
        )
    except Exception as e:
        log.exception(f'update_calendar_event error: {e}')
        return json.dumps({'error': str(e)})


async def delete_calendar_event(
    event_id: str,
    __request__: Request = None,
    __user__: dict = None,
) -> str:
    """
    Delete a calendar event permanently.

    :param event_id: The ID of the event to delete
    :return: JSON confirming the event was deleted
    """
    if __request__ is None:
        return json.dumps({'error': 'Request context not available'})

    if not __user__:
        return json.dumps({'error': 'User context not available'})

    try:
        from open_webui.models.access_grants import AccessGrants
        from open_webui.models.calendar import CalendarEvents, Calendars
        from open_webui.models.groups import Groups

        user_id = __user__.get('id')

        event = await CalendarEvents.get_event_by_id(event_id)
        if not event:
            return json.dumps({'error': 'Event not found'})

        # Check write access
        if event.user_id != user_id and __user__.get('role') != 'admin':
            cal = await Calendars.get_calendar_by_id(event.calendar_id)
            if not cal:
                return json.dumps({'error': 'Access denied'})
            user_group_ids = [g.id for g in await Groups.get_groups_by_member_id(user_id)]
            if not await AccessGrants.has_access(
                user_id=user_id,
                resource_type='calendar',
                resource_id=cal.id,
                permission='write',
                user_group_ids=set(user_group_ids),
            ):
                return json.dumps({'error': 'Access denied'})

        title = event.title
        result = await CalendarEvents.delete_event_by_id(event_id)
        if not result:
            return json.dumps({'error': 'Failed to delete event'})

        return json.dumps(
            {
                'status': 'success',
                'message': f'Event "{title}" deleted',
            },
            ensure_ascii=False,
        )
    except Exception as e:
        log.exception(f'delete_calendar_event error: {e}')
        return json.dumps({'error': str(e)})


# =============================================================================
# WEATHER, MAPS, CURRENCY, SPORTS & INTERACTIVE TOOLS
# =============================================================================

_WMO_WEATHER_DESCRIPTIONS = {
    0: 'Clear sky',
    1: 'Mainly clear',
    2: 'Partly cloudy',
    3: 'Overcast',
    45: 'Fog',
    48: 'Depositing rime fog',
    51: 'Light drizzle',
    53: 'Moderate drizzle',
    55: 'Dense drizzle',
    56: 'Light freezing drizzle',
    57: 'Dense freezing drizzle',
    61: 'Slight rain',
    63: 'Moderate rain',
    65: 'Heavy rain',
    66: 'Light freezing rain',
    67: 'Heavy freezing rain',
    71: 'Slight snow',
    73: 'Moderate snow',
    75: 'Heavy snow',
    77: 'Snow grains',
    80: 'Slight rain showers',
    81: 'Moderate rain showers',
    82: 'Violent rain showers',
    85: 'Slight snow showers',
    86: 'Heavy snow showers',
    95: 'Thunderstorm',
    96: 'Thunderstorm with slight hail',
    99: 'Thunderstorm with heavy hail',
}


def _wmo_description(code: int | None) -> str:
    if code is None:
        return 'Unknown'
    return _WMO_WEATHER_DESCRIPTIONS.get(int(code), 'Unknown')


async def _http_get_json(url: str, headers: dict | None = None, params: dict | None = None) -> dict | list:
    from open_webui.utils.session_pool import get_session

    session = await get_session()
    async with session.get(url, headers=headers or {}, params=params or {}) as response:
        response.raise_for_status()
        return await response.json()


async def _geocode_open_meteo(location: str) -> dict | None:
    payload = await _http_get_json(
        'https://geocoding-api.open-meteo.com/v1/search',
        params={'name': location, 'count': 1, 'language': 'en', 'format': 'json'},
    )
    results = payload.get('results') or []
    return results[0] if results else None


async def _reverse_geocode_open_meteo(latitude: float, longitude: float) -> str:
    try:
        payload = await _http_get_json(
            'https://geocoding-api.open-meteo.com/v1/reverse',
            params={'latitude': latitude, 'longitude': longitude, 'language': 'en'},
        )
        results = payload.get('results') or []
        if results:
            place = results[0]
            parts = [place.get('name'), place.get('admin1'), place.get('country')]
            return ', '.join(p for p in parts if p)
    except Exception:
        pass
    return f'{latitude:.4f}, {longitude:.4f}'


async def weather_fetch(
    location: Optional[str] = None,
    __event_call__: callable = None,
    __event_emitter__: callable = None,
    __metadata__: dict = None,
) -> str:
    """
    Fetch current weather for a location. If no location is given, requests the user's
    browser coordinates via geolocation.

    :param location: City or place name (optional — uses browser location if omitted)
    :return: JSON summary of current weather conditions
    """
    try:
        latitude = None
        longitude = None
        location_name = location

        if not location or not str(location).strip():
            if __event_call__ is None:
                return json.dumps({'error': 'Location required. Please specify a city or enable location access.'})

            coords = await __event_call__({'type': 'request:location', 'data': {}})
            if not isinstance(coords, dict) or coords.get('error'):
                return json.dumps(
                    {
                        'error': 'Location access denied or unavailable. Please specify a city name instead.',
                    }
                )

            latitude = float(coords['latitude'])
            longitude = float(coords['longitude'])
            location_name = await _reverse_geocode_open_meteo(latitude, longitude)
        else:
            geo = await _geocode_open_meteo(str(location).strip())
            if not geo:
                return json.dumps({'error': f'Could not find location: {location}'})
            latitude = float(geo['latitude'])
            longitude = float(geo['longitude'])
            location_name = ', '.join(
                p for p in [geo.get('name'), geo.get('admin1'), geo.get('country')] if p
            )

        forecast = await _http_get_json(
            'https://api.open-meteo.com/v1/forecast',
            params={
                'latitude': latitude,
                'longitude': longitude,
                'current': 'temperature_2m,relative_humidity_2m,apparent_temperature,weather_code,wind_speed_10m',
                'timezone': 'auto',
            },
        )
        current = forecast.get('current') or {}
        weather_code = current.get('weather_code')
        description = _wmo_description(weather_code)

        weather_data = {
            'location': location_name,
            'latitude': latitude,
            'longitude': longitude,
            'temperature': current.get('temperature_2m'),
            'temperature_unit': (forecast.get('current_units') or {}).get('temperature_2m', '°C'),
            'feels_like': current.get('apparent_temperature'),
            'humidity': current.get('relative_humidity_2m'),
            'wind_speed': current.get('wind_speed_10m'),
            'wind_speed_unit': (forecast.get('current_units') or {}).get('wind_speed_10m', 'km/h'),
            'weather_code': weather_code,
            'description': description,
            'time': current.get('time'),
        }

        if __event_emitter__:
            await __event_emitter__({'type': 'chat:message:weather', 'data': weather_data})

        return json.dumps(
            {
                'status': 'success',
                'message': 'Weather card displayed to the user.',
                'weather': weather_data,
            },
            ensure_ascii=False,
        )
    except Exception as e:
        log.exception(f'weather_fetch error: {e}')
        return json.dumps({'error': str(e)})


async def image_search(
    query: str,
    count: Optional[int] = 8,
    __request__: Request = None,
    __user__: dict = None,
    __event_emitter__: callable = None,
    __chat_id__: str = None,
    __message_id__: str = None,
) -> str:
    """
    Search the web for images matching a query and display them inline in the chat.

    :param query: The image search query
    :param count: Number of images to return (default 8, max 12)
    :return: Confirmation that images are displayed
    """
    if __request__ is None:
        return json.dumps({'error': 'Request context not available'})

    try:
        count = max(1, min(int(count or 8), 12))
        engine = await Config.get('web.search.engine')
        image_urls: list[str] = []

        if engine == 'searxng':
            from open_webui.retrieval.web.searxng import search_searxng

            query_url = await Config.get('web.search.searxng_query_url')
            if not query_url:
                return json.dumps({'error': 'SearXNG is not configured for image search.'})

            filter_list = await Config.get('web.search.domain_filter_list')
            language = await Config.get('web.search.searxng_language')
            results = await search_searxng(
                query_url,
                query,
                count,
                filter_list,
                categories=['images'],
                language=language or 'all',
            )
            image_urls = [r.link for r in results if r.link]
        elif engine == 'brave':
            from open_webui.utils.session_pool import get_session

            api_key = await Config.get('web.search.brave_search_api_key')
            if not api_key:
                return json.dumps({'error': 'Brave Search API key is not configured.'})

            session = await get_session()
            async with session.get(
                'https://api.search.brave.com/res/v1/images/search',
                headers={
                    'Accept': 'application/json',
                    'Accept-Encoding': 'gzip',
                    'X-Subscription-Token': api_key,
                },
                params={'q': query, 'count': count},
            ) as response:
                response.raise_for_status()
                payload = await response.json()

            for item in (payload.get('results') or [])[:count]:
                url = item.get('thumbnail', {}).get('src') or item.get('url')
                if url:
                    image_urls.append(url)
        else:
            return json.dumps(
                {
                    'error': 'Image search requires SearXNG or Brave as the configured web search engine.',
                }
            )

        if not image_urls:
            return json.dumps({'error': f'No images found for query: {query}'})

        image_files = [{'type': 'image', 'url': url} for url in image_urls[:count]]

        if __chat_id__ and __message_id__ and image_files:
            db_files = await Chats.add_message_files_by_id_and_message_id(
                __chat_id__,
                __message_id__,
                image_files,
            )
            if db_files is not None:
                image_files = db_files

        if __event_emitter__ and image_files:
            await __event_emitter__(
                {
                    'type': 'chat:message:files',
                    'data': {'files': image_files},
                }
            )
            return json.dumps(
                {
                    'status': 'success',
                    'message': (
                        'Images have been displayed inline in the chat. '
                        'Do not embed or link them again — acknowledge they are visible.'
                    ),
                    'count': len(image_files),
                },
                ensure_ascii=False,
            )

        return json.dumps({'status': 'success', 'count': len(image_files)}, ensure_ascii=False)
    except Exception as e:
        log.exception(f'image_search error: {e}')
        return json.dumps({'error': str(e)})


async def present_options(
    question: str,
    options: list[str],
    __event_emitter__: callable = None,
) -> str:
    """
    Present the user with 2–4 tappable option buttons below your message text. Their selection arrives as their next message.

    Write any brief intro or explanation in your response first, then call this tool so buttons render under your prose.

    :param question: The question to present
    :param options: List of 2–4 short option labels
    :return: Confirmation that options were displayed
    """
    try:
        labels = [str(o).strip() for o in (options or []) if str(o).strip()]
        if len(labels) < 2:
            return json.dumps({'error': 'Provide at least 2 options.'})
        if len(labels) > 4:
            labels = labels[:4]

        payload = {'question': question, 'options': labels}

        if __event_emitter__:
            await __event_emitter__({'type': 'chat:message:options', 'data': payload})

        return json.dumps(
            {
                'status': 'success',
                'message': 'Options displayed. Wait for the user to select one.',
            },
            ensure_ascii=False,
        )
    except Exception as e:
        log.exception(f'present_options error: {e}')
        return json.dumps({'error': str(e)})


async def currency_convert(
    amount: float,
    from_currency: str,
    to_currency: str,
    __event_emitter__: callable = None,
) -> str:
    """
    Convert an amount between currencies using live exchange rates.

    :param amount: The amount to convert
    :param from_currency: Source currency code (e.g. USD)
    :param to_currency: Target currency code (e.g. EUR)
    :return: JSON with conversion result and rate
    """
    try:
        from_code = str(from_currency).strip().upper()
        to_code = str(to_currency).strip().upper()
        if not from_code or not to_code:
            return json.dumps({'error': 'Both from_currency and to_currency are required.'})

        payload = await _http_get_json(f'https://open.er-api.com/v6/latest/{from_code}')
        rates = payload.get('rates') or {}
        if to_code not in rates:
            return json.dumps({'error': f'Unknown currency code: {to_code}'})

        rate = float(rates[to_code])
        inverse_rate = round(1 / rate, 6) if rate else None
        result_amount = round(float(amount) * rate, 4)
        currency_data = {
            'from': from_code,
            'to': to_code,
            'amount': float(amount),
            'result': result_amount,
            'rate': rate,
            'inverse_rate': round(inverse_rate, 6),
            'updated': payload.get('time_last_update_utc'),
        }

        if __event_emitter__:
            await __event_emitter__({'type': 'chat:message:currency', 'data': currency_data})

        return json.dumps(
            {
                'status': 'success',
                'message': 'Currency card displayed to the user.',
                'conversion': currency_data,
            },
            ensure_ascii=False,
        )
    except Exception as e:
        log.exception(f'currency_convert error: {e}')
        return json.dumps({'error': str(e)})


async def _geocode_nominatim(query: str) -> dict | None:
    payload = await _http_get_json(
        'https://nominatim.openstreetmap.org/search',
        headers={'User-Agent': 'Open WebUI (https://github.com/open-webui/open-webui)'},
        params={'q': query, 'format': 'json', 'limit': 1},
    )
    if isinstance(payload, list) and payload:
        item = payload[0]
        return {
            'lat': float(item['lat']),
            'lng': float(item['lon']),
            'label': item.get('display_name', query),
        }
    return None


async def map_display(
    location: str | dict,
    zoom: Optional[int] = 13,
    markers: Optional[list[dict]] = None,
    __event_emitter__: callable = None,
) -> str:
    """
    Display an interactive map with one or more location markers.

    :param location: Place name or dict with lat/lng keys
    :param zoom: Map zoom level (default 13)
    :param markers: Optional list of {lat, lng, label} marker dicts
    :return: Confirmation that the map was displayed
    """
    try:
        lat = None
        lng = None
        label = None

        if isinstance(location, dict):
            lat = location.get('lat', location.get('latitude'))
            lng = location.get('lng', location.get('longitude'))
            label = location.get('label') or location.get('name')
        else:
            geo = await _geocode_nominatim(str(location).strip())
            if not geo:
                return json.dumps({'error': f'Could not find location: {location}'})
            lat = geo['lat']
            lng = geo['lng']
            label = geo['label']

        if lat is None or lng is None:
            return json.dumps({'error': 'Valid location with lat/lng is required.'})

        marker_list = []
        for marker in markers or []:
            if isinstance(marker, dict):
                m_lat = marker.get('lat', marker.get('latitude'))
                m_lng = marker.get('lng', marker.get('longitude'))
                if m_lat is not None and m_lng is not None:
                    marker_list.append(
                        {
                            'lat': float(m_lat),
                            'lng': float(m_lng),
                            'label': marker.get('label') or marker.get('name') or '',
                        }
                    )

        if not marker_list:
            marker_list = [{'lat': float(lat), 'lng': float(lng), 'label': label or str(location)}]

        map_data = {
            'lat': float(lat),
            'lng': float(lng),
            'zoom': int(zoom or 13),
            'label': label or str(location),
            'markers': marker_list,
        }

        if __event_emitter__:
            await __event_emitter__({'type': 'chat:message:map', 'data': map_data})

        return json.dumps(
            {
                'status': 'success',
                'message': 'Map displayed to the user.',
                'map': map_data,
            },
            ensure_ascii=False,
        )
    except Exception as e:
        log.exception(f'map_display error: {e}')
        return json.dumps({'error': str(e)})


async def sports_scores(
    team_name: str,
    __event_emitter__: callable = None,
) -> str:
    """
    Fetch recent results and upcoming fixtures for a sports team.

    :param team_name: The team name to look up
    :return: JSON summary of recent and upcoming matches
    """
    try:
        search_payload = await _http_get_json(
            'https://www.thesportsdb.com/api/v1/json/3/searchteams.php',
            params={'t': team_name},
        )
        teams = search_payload.get('teams') or []
        if not teams:
            return json.dumps({'error': f'No team found matching: {team_name}'})

        team = teams[0]
        team_id = team.get('idTeam')
        team_label = team.get('strTeam', team_name)
        league = team.get('strLeague', '')

        last_payload = await _http_get_json(
            'https://www.thesportsdb.com/api/v1/json/3/eventslast.php',
            params={'id': team_id},
        )
        next_payload = await _http_get_json(
            'https://www.thesportsdb.com/api/v1/json/3/eventsnext.php',
            params={'id': team_id},
        )

        def _format_event(event: dict, team_label: str) -> dict:
            home = event.get('strHomeTeam', '')
            away = event.get('strAwayTeam', '')
            is_home = home.lower() == team_label.lower()
            opponent = away if is_home else home
            score = None
            if event.get('intHomeScore') is not None and event.get('intAwayScore') is not None:
                score = f"{event.get('intHomeScore')}-{event.get('intAwayScore')}"
            return {
                'opponent': opponent,
                'home': home,
                'away': away,
                'score': score,
                'date': event.get('dateEvent') or event.get('strTimestamp'),
                'competition': event.get('strLeague') or league,
                'venue': event.get('strVenue'),
            }

        recent = [_format_event(e, team_label) for e in (last_payload.get('results') or [])[:5]]
        upcoming = [_format_event(e, team_label) for e in (next_payload.get('events') or [])[:5]]

        sports_data = {
            'team': team_label,
            'league': league,
            'badge': team.get('strBadge') or team.get('strTeamBadge'),
            'recent': recent,
            'upcoming': upcoming,
        }

        if __event_emitter__:
            await __event_emitter__({'type': 'chat:message:sports', 'data': sports_data})

        return json.dumps(
            {
                'status': 'success',
                'message': 'Sports scores card displayed to the user.',
                'sports': sports_data,
            },
            ensure_ascii=False,
        )
    except Exception as e:
        log.exception(f'sports_scores error: {e}')
        return json.dumps({'error': str(e)})


async def suggest_followups(
    suggestions: list[str],
    __event_emitter__: callable = None,
) -> str:
    """
    Show 2–3 suggested follow-up prompts as tappable chips at the end of a response.

    :param suggestions: List of 2–3 short follow-up prompt strings
    :return: Confirmation that follow-up chips were displayed
    """
    try:
        items = [str(s).strip() for s in (suggestions or []) if str(s).strip()]
        if len(items) < 2:
            return json.dumps({'error': 'Provide at least 2 follow-up suggestions.'})
        if len(items) > 3:
            items = items[:3]

        if __event_emitter__:
            await __event_emitter__(
                {
                    'type': 'chat:message:followups',
                    'data': {'suggestions': items},
                }
            )

        return json.dumps(
            {
                'status': 'success',
                'message': 'Follow-up chips displayed. Do not repeat them in prose.',
            },
            ensure_ascii=False,
        )
    except Exception as e:
        log.exception(f'suggest_followups error: {e}')
        return json.dumps({'error': str(e)})


# =============================================================================
# ARTIFACT TOOLS (saved library)
# =============================================================================


def _parse_artifact_meta(meta: Optional[str]) -> dict:
    if not meta:
        return {}
    try:
        parsed = json.loads(meta)
        return parsed if isinstance(parsed, dict) else {}
    except Exception:
        return {}


_ARTIFACT_IN_CHAT_BUILD_ERROR = (
    'Do not use artifact library tools for new build/create/make requests. '
    'Output the full source in an <antArtifact> tag in your chat response instead. '
    'list_artifacts / read_artifact / update_artifact are only for artifacts the user '
    'explicitly asked to edit in their saved library (e.g. "update my saved clicker game"). '
    'In-chat revisions reuse the same <antArtifact identifier="…"> — no library tool calls.'
)


def _artifact_library_tool_allowed(user_prompt: Optional[str]) -> bool:
    """Block library artifact writes when the user asked for a new in-chat build."""
    if not user_prompt or not str(user_prompt).strip():
        return True

    prompt = str(user_prompt).lower()

    library_cues = (
        'saved artifact',
        'saved game',
        'my library',
        'artifact library',
        'published artifact',
        'in my library',
        'from my library',
        'previously saved',
        'saved to',
    )
    if any(cue in prompt for cue in library_cues):
        return True

    if re.search(r'\b(update|edit|modify|revise|change|fix)\s+(my|the)\s+saved\b', prompt):
        return True

    build_cues = (
        'build me',
        'build a',
        'build an',
        'create a',
        'create me',
        'create an',
        'make me',
        'make a',
        'make an',
        'write me',
        'write a',
        'write an',
        'design a',
        'design me',
        'code me',
        'code a',
        'generate a',
        'generate me',
        'in chat',
        'using react',
        'using tailwind',
        'with react',
        'with tailwind',
    )
    if any(cue in prompt for cue in build_cues):
        return False

    return True


def _prepare_artifact_storage(content: str, artifact_type: str) -> tuple[str, str, Optional[str]]:
    normalized = (artifact_type or 'iframe').lower().strip()
    if normalized == 'react':
        from open_webui.utils.react_artifact import build_react_html

        meta = json.dumps(
            {
                'mime_type': 'application/vnd.ant.react',
                'react_source': content,
            },
            ensure_ascii=False,
        )
        return 'iframe', build_react_html(content), meta
    if normalized == 'markdown':
        meta = json.dumps({'mime_type': 'text/markdown'}, ensure_ascii=False)
        return 'markdown', content, meta
    if normalized == 'svg':
        return 'svg', content, None
    return 'iframe', content, None


def _editable_artifact_content(artifact) -> tuple[str, str]:
    meta = _parse_artifact_meta(artifact.meta)
    if meta.get('react_source'):
        return 'react', meta['react_source']
    if meta.get('mime_type') == 'text/markdown' or artifact.type == 'markdown':
        return 'markdown', artifact.code
    if artifact.type == 'svg':
        return 'svg', artifact.code
    return 'iframe', artifact.code


async def _artifacts_access_error(__request__: Request = None, __user__: dict = None) -> Optional[str]:
    if __request__ is None:
        return 'Request context not available'
    if not __user__:
        return 'User context not available'
    if not await Config.get('artifacts.enable'):
        return 'Artifacts feature is disabled'
    if __user__.get('role') == 'admin':
        return None
    from open_webui.utils.access_control import has_permission

    if not await has_permission(
        __user__.get('id'),
        'features.artifacts',
        await Config.get('user.permissions'),
    ):
        return 'Access denied — artifacts permission required'
    return None


async def list_artifacts(
    count: int = 50,
    __request__: Request = None,
    __user__: dict = None,
    __metadata__: dict = None,
) -> str:
    """
    List artifacts in the user's saved library (published via the panel Save button).

    Do NOT call for new build/create/make requests — output <antArtifact> in chat instead.
    Only call when the user explicitly refers to their saved/published library.

    :param count: Maximum number of artifacts to return (default: 50)
    :return: JSON list with id, title, type, artifact_type, updated_at
    """
    if err := await _artifacts_access_error(__request__, __user__):
        return json.dumps({'error': err})

    user_prompt = (__metadata__ or {}).get('user_prompt')
    if not _artifact_library_tool_allowed(user_prompt):
        return json.dumps({'error': _ARTIFACT_IN_CHAT_BUILD_ERROR})

    try:
        from open_webui.models.artifacts import Artifacts

        user_id = __user__.get('id')
        count = max(1, min(int(count or 50), 50))
        artifacts = await Artifacts.get_artifacts_by_user_id(user_id, skip=0, limit=count)

        results = []
        for artifact in artifacts:
            artifact_type, _ = _editable_artifact_content(artifact)
            results.append(
                {
                    'id': artifact.id,
                    'title': artifact.title,
                    'type': artifact.type,
                    'artifact_type': artifact_type,
                    'chat_id': artifact.chat_id,
                    'updated_at': artifact.updated_at,
                }
            )

        return json.dumps(results, ensure_ascii=False)
    except Exception as e:
        log.exception(f'list_artifacts error: {e}')
        return json.dumps({'error': str(e)})


async def read_artifact(
    artifact_id: str,
    __request__: Request = None,
    __user__: dict = None,
    __metadata__: dict = None,
) -> str:
    """
    Read editable source of an artifact already in the user's saved library.

    Do NOT call for new build/create/make requests — output <antArtifact> in chat instead.
    Call only after list_artifacts when the user asked to edit a specific saved artifact.

    :param artifact_id: The artifact ID from list_artifacts
    :return: JSON with id, title, type, artifact_type, and content (editable source)
    """
    if err := await _artifacts_access_error(__request__, __user__):
        return json.dumps({'error': err})

    user_prompt = (__metadata__ or {}).get('user_prompt')
    if not _artifact_library_tool_allowed(user_prompt):
        return json.dumps({'error': _ARTIFACT_IN_CHAT_BUILD_ERROR})

    try:
        from open_webui.models.artifacts import Artifacts

        artifact = await Artifacts.get_artifact_by_id(artifact_id)
        if not artifact:
            return json.dumps({'error': 'Artifact not found'})

        user_id = __user__.get('id')
        if artifact.user_id != user_id and __user__.get('role') != 'admin':
            return json.dumps({'error': 'Access denied'})

        artifact_type, content = _editable_artifact_content(artifact)

        return json.dumps(
            {
                'id': artifact.id,
                'title': artifact.title,
                'type': artifact.type,
                'artifact_type': artifact_type,
                'content': content,
                'chat_id': artifact.chat_id,
                'updated_at': artifact.updated_at,
            },
            ensure_ascii=False,
        )
    except Exception as e:
        log.exception(f'read_artifact error: {e}')
        return json.dumps({'error': str(e)})


async def update_artifact(
    artifact_id: str,
    content: str,
    title: Optional[str] = None,
    artifact_type: Optional[str] = None,
    __request__: Request = None,
    __user__: dict = None,
    __metadata__: dict = None,
) -> str:
    """
    Replace source of an artifact already in the user's saved library.

    NEVER use for build/create/make requests — output <antArtifact> in chat instead.
    NEVER use to deliver new interactive content. Only when the user explicitly asked
    to edit a saved/published library artifact. Requires list_artifacts → read_artifact first.
    After updating, also output an <antArtifact> tag so the in-chat panel refreshes.

    :param artifact_id: The artifact ID to update
    :param content: Complete replacement source (not a diff)
    :param title: Optional new title
    :param artifact_type: Optional type override: iframe, svg, react, or markdown
    :return: JSON with updated artifact metadata
    """
    if err := await _artifacts_access_error(__request__, __user__):
        return json.dumps({'error': err})

    user_prompt = (__metadata__ or {}).get('user_prompt')
    if not _artifact_library_tool_allowed(user_prompt):
        return json.dumps({'error': _ARTIFACT_IN_CHAT_BUILD_ERROR})

    if not content or not str(content).strip():
        return json.dumps({'error': 'Content is required'})

    try:
        from open_webui.models.artifacts import ArtifactUpdateForm, Artifacts

        existing = await Artifacts.get_artifact_by_id(artifact_id)
        if not existing:
            return json.dumps({'error': 'Artifact not found'})

        user_id = __user__.get('id')
        if existing.user_id != user_id and __user__.get('role') != 'admin':
            return json.dumps({'error': 'Access denied'})

        resolved_type = artifact_type
        if not resolved_type:
            resolved_type, _ = _editable_artifact_content(existing)

        db_type, code, meta = _prepare_artifact_storage(str(content), resolved_type)
        form = ArtifactUpdateForm(
            title=title.strip() if title else None,
            type=db_type,
            code=code,
            meta=meta,
        )
        updated = await Artifacts.update_artifact_by_id(artifact_id, form)
        if not updated:
            return json.dumps({'error': 'Failed to update artifact'})

        saved_type, editable = _editable_artifact_content(updated)
        return json.dumps(
            {
                'status': 'success',
                'id': updated.id,
                'title': updated.title,
                'type': updated.type,
                'artifact_type': saved_type,
                'content': editable,
                'message': 'Artifact updated. Output an <antArtifact> tag to refresh the panel.',
            },
            ensure_ascii=False,
        )
    except Exception as e:
        log.exception(f'update_artifact error: {e}')
        return json.dumps({'error': str(e)})


async def delete_artifact(
    artifact_id: str,
    __request__: Request = None,
    __user__: dict = None,
) -> str:
    """
    Delete (unpublish) a saved artifact from the user's library.

    :param artifact_id: The artifact ID to delete
    :return: JSON with deletion status
    """
    if err := await _artifacts_access_error(__request__, __user__):
        return json.dumps({'error': err})

    try:
        from open_webui.models.artifacts import Artifacts

        existing = await Artifacts.get_artifact_by_id(artifact_id)
        if not existing:
            return json.dumps({'error': 'Artifact not found'})

        user_id = __user__.get('id')
        if existing.user_id != user_id and __user__.get('role') != 'admin':
            return json.dumps({'error': 'Access denied'})

        await Artifacts.delete_artifact_by_id(artifact_id)
        return json.dumps(
            {'status': 'success', 'id': artifact_id, 'deleted': True},
            ensure_ascii=False,
        )
    except Exception as e:
        log.exception(f'delete_artifact error: {e}')
        return json.dumps({'error': str(e)})
