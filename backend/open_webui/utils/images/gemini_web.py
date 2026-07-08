from __future__ import annotations

import asyncio
import logging
import os
import tempfile
from pathlib import Path

log = logging.getLogger(__name__)

_client = None
_client_key: tuple[str, str, str] | None = None
_client_lock = asyncio.Lock()

# Gemini web app chat modes that support Nano Banana image generation.
# IDs match gemini_webapi.constants.Model.model_name values.
GEMINI_WEB_MODEL_LABELS: dict[str, str] = {
    'gemini-3-flash': 'Fast',
    'gemini-3-flash-thinking': 'Thinking',
    'gemini-3-pro': 'Pro',
    'gemini-3-flash-plus': 'Fast (Google AI Plus)',
    'gemini-3-flash-thinking-plus': 'Thinking (Google AI Plus)',
    'gemini-3-pro-plus': 'Pro (Google AI Plus)',
    'gemini-3-flash-advanced': 'Fast (Google AI Advanced)',
    'gemini-3-flash-thinking-advanced': 'Thinking (Google AI Advanced)',
    'gemini-3-pro-advanced': 'Pro (Google AI Advanced)',
}

DEFAULT_GEMINI_WEB_MODEL = 'gemini-3-flash'


def _raise_if_cancelled() -> None:
    task = asyncio.current_task()
    if task is not None and task.cancelling():
        raise asyncio.CancelledError()


def _require_gemini_webapi():
    try:
        from gemini_webapi import GeneratedImage, GeminiClient

        return GeneratedImage, GeminiClient
    except ImportError as e:
        raise RuntimeError(
            'gemini-webapi is not installed for this Python environment. '
            'Run: backend/venv/bin/python -m pip install -r backend/requirements.txt'
        ) from e


def get_gemini_web_model_catalog() -> list[dict[str, str]]:
    try:
        from gemini_webapi.constants import Model

        catalog: list[dict[str, str]] = []
        seen: set[str] = set()

        for member in Model:
            if member is Model.UNSPECIFIED:
                continue

            model_name = member.model_name
            if not model_name or model_name in seen:
                continue

            seen.add(model_name)
            label = GEMINI_WEB_MODEL_LABELS.get(model_name, model_name)
            catalog.append({'id': model_name, 'name': label})

        if catalog:
            return catalog
    except ImportError:
        pass

    return [
        {'id': model_id, 'name': label}
        for model_id, label in GEMINI_WEB_MODEL_LABELS.items()
    ]


def _format_dynamic_model(model) -> dict[str, str]:
    display_name = (model.display_name or '').strip()
    model_name = (model.model_name or '').strip()
    description = (model.description or '').strip()

    if display_name and model_name and display_name.lower() != model_name.lower():
        name = f'{display_name} ({model_name})'
    else:
        name = display_name or model_name or model.model_id

    if description and description not in name:
        name = f'{name} — {description}'

    model_id = model_name or model.model_id
    return {'id': model_id, 'name': name}


def _merge_model_lists(*lists: list[dict[str, str]]) -> list[dict[str, str]]:
    merged: dict[str, dict[str, str]] = {}

    for models in lists:
        for entry in models:
            model_id = entry.get('id')
            if not model_id:
                continue
            if model_id not in merged:
                merged[model_id] = entry

    return list(merged.values())


def default_cookie_path() -> str:
    from open_webui.config import CACHE_DIR

    path = Path(CACHE_DIR) / 'gemini_web' / 'cookies.json'
    path.parent.mkdir(parents=True, exist_ok=True)
    return str(path)


async def close_gemini_web_client() -> None:
    global _client, _client_key

    async with _client_lock:
        if _client is not None:
            try:
                await _client.close()
            except Exception:
                log.exception('Failed to close Gemini Web client')
        _client = None
        _client_key = None


async def get_gemini_web_client(
    secure_1psid: str,
    secure_1psidts: str = '',
    cookie_path: str | None = None,
):
    global _client, _client_key

    if not secure_1psid:
        raise ValueError('Gemini Web __Secure-1PSID cookie is required')

    resolved_cookie_path = cookie_path or default_cookie_path()
    key = (secure_1psid, secure_1psidts or '', resolved_cookie_path)

    async with _client_lock:
        if _client is not None and _client_key == key:
            return _client

        if _client is not None:
            try:
                await _client.close()
            except Exception:
                log.exception('Failed to close previous Gemini Web client')

        try:
            GeneratedImage, GeminiClient = _require_gemini_webapi()
        except RuntimeError:
            raise

        os.environ['GEMINI_COOKIE_PATH'] = str(Path(resolved_cookie_path).parent)

        client = GeminiClient(
            secure_1psid=secure_1psid,
            secure_1psidts=secure_1psidts or None,
        )
        await client.init(auto_close=False, auto_refresh=True)
        _client = client
        _client_key = key
        return _client


async def list_gemini_web_models(
    secure_1psid: str = '',
    secure_1psidts: str = '',
    cookie_path: str | None = None,
) -> list[dict[str, str]]:
    catalog = get_gemini_web_model_catalog()

    if not secure_1psid:
        return catalog

    try:
        client = await get_gemini_web_client(secure_1psid, secure_1psidts, cookie_path)
        models = client.list_models()
        if models:
            dynamic = [_format_dynamic_model(model) for model in models]
            return _merge_model_lists(dynamic, catalog)
    except Exception as e:
        log.warning('Failed to fetch Gemini Web models from account: %s', e)

    return catalog


async def _download_generated_image(image) -> tuple[bytes, str]:
    with tempfile.TemporaryDirectory(prefix='gemini_web_') as tmpdir:
        saved_path = await image.save(path=tmpdir, verbose=False)
        ext = Path(saved_path).suffix.lower()
        content_type = {
            '.jpg': 'image/jpeg',
            '.jpeg': 'image/jpeg',
            '.webp': 'image/webp',
            '.gif': 'image/gif',
        }.get(ext, 'image/png')
        return Path(saved_path).read_bytes(), content_type


def _generation_prompt(prompt: str) -> str:
    lowered = prompt.strip().lower()
    if lowered.startswith('generate an image') or lowered.startswith('generate a image'):
        return prompt
    if lowered.startswith('generate image') or lowered.startswith('generate:'):
        return prompt
    return f'Generate an image: {prompt}'


async def generate_gemini_web_images(
    prompt: str,
    secure_1psid: str,
    secure_1psidts: str = '',
    cookie_path: str | None = None,
    model: str | None = None,
    n: int = 1,
) -> list[tuple[bytes, str]]:
    GeneratedImage, _ = _require_gemini_webapi()

    client = await get_gemini_web_client(secure_1psid, secure_1psidts, cookie_path)
    generation_prompt = _generation_prompt(prompt)
    selected_model = model or DEFAULT_GEMINI_WEB_MODEL
    count = max(1, n)
    images: list[tuple[bytes, str]] = []

    for _ in range(count):
        _raise_if_cancelled()
        response = await client.generate_content(
            generation_prompt,
            model=selected_model,
            temporary=True,
        )

        generated = []
        for candidate in response.candidates:
            generated.extend(candidate.generated_images)

        if not generated:
            for candidate in response.candidates:
                for image in candidate.images:
                    if isinstance(image, GeneratedImage):
                        generated.append(image)

        if not generated:
            raise ValueError(
                'Gemini Web did not return a generated image. '
                'Check that image generation is enabled for your Google account and model.'
            )

        for image in generated:
            images.append(await _download_generated_image(image))
            if len(images) >= count:
                return images

    return images
