from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from open_webui.config import (
    ARTIFACT_STORAGE_MAX_BYTES,
    ARTIFACT_STORAGE_MAX_KEY_BYTES,
    ARTIFACT_STORAGE_MAX_VALUE_BYTES,
)
from open_webui.constants import ERROR_MESSAGES
from open_webui.internal.db import get_async_session
from open_webui.models.artifacts import (
    ArtifactPublishForm,
    ArtifactResponse,
    ArtifactStorageSetForm,
    ArtifactUpdateForm,
    ArtifactWithCodeResponse,
    Artifacts,
)
from open_webui.models.config import Config
from open_webui.utils.access_control import has_permission
from open_webui.utils.auth import get_verified_user

router = APIRouter()


############################
# Publish Artifact
############################


@router.post('/publish', response_model=ArtifactWithCodeResponse)
async def publish_artifact(
    form_data: ArtifactPublishForm,
    user=Depends(get_verified_user),
    db: AsyncSession = Depends(get_async_session),
):
    if user.role != 'admin' and not await has_permission(
        user.id, 'features.artifacts', await Config.get('user.permissions'), db=db
    ):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail=ERROR_MESSAGES.UNAUTHORIZED)

    artifact = await Artifacts.publish_artifact(user.id, form_data, db=db)
    return ArtifactWithCodeResponse(**artifact.model_dump())


############################
# List Artifacts
############################


@router.get('/', response_model=list[ArtifactResponse])
async def get_artifacts(
    user=Depends(get_verified_user),
    db: AsyncSession = Depends(get_async_session),
):
    if user.role != 'admin' and not await has_permission(
        user.id, 'features.artifacts', await Config.get('user.permissions'), db=db
    ):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail=ERROR_MESSAGES.UNAUTHORIZED)

    artifacts = await Artifacts.get_artifacts_by_user_id(user.id, skip=0, limit=50, db=db)
    return [ArtifactResponse(**a.model_dump()) for a in artifacts]


############################
# Get Artifact by ID
############################


@router.get('/{artifact_id}', response_model=ArtifactWithCodeResponse)
async def get_artifact(
    artifact_id: str,
    user=Depends(get_verified_user),
    db: AsyncSession = Depends(get_async_session),
):
    artifact = await Artifacts.get_artifact_by_id(artifact_id, db=db)
    if not artifact:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=ERROR_MESSAGES.NOT_FOUND)

    if artifact.user_id != user.id and user.role != 'admin':
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=ERROR_MESSAGES.ACCESS_PROHIBITED)

    return ArtifactWithCodeResponse(**artifact.model_dump())


############################
# Update Artifact
############################


@router.put('/{artifact_id}', response_model=ArtifactResponse)
async def update_artifact(
    artifact_id: str,
    form_data: ArtifactUpdateForm,
    user=Depends(get_verified_user),
    db: AsyncSession = Depends(get_async_session),
):
    artifact = await Artifacts.get_artifact_by_id(artifact_id, db=db)
    if not artifact:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=ERROR_MESSAGES.NOT_FOUND)

    if artifact.user_id != user.id and user.role != 'admin':
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=ERROR_MESSAGES.ACCESS_PROHIBITED)

    updated = await Artifacts.update_artifact_by_id(artifact_id, form_data, db=db)
    return ArtifactResponse(**updated.model_dump())


############################
# Delete (Unpublish) Artifact
############################


@router.delete('/{artifact_id}')
async def delete_artifact(
    artifact_id: str,
    user=Depends(get_verified_user),
    db: AsyncSession = Depends(get_async_session),
):
    artifact = await Artifacts.get_artifact_by_id(artifact_id, db=db)
    if not artifact:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=ERROR_MESSAGES.NOT_FOUND)

    if artifact.user_id != user.id and user.role != 'admin':
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=ERROR_MESSAGES.ACCESS_PROHIBITED)

    await Artifacts.delete_artifact_by_id(artifact_id, db=db)
    return {'deleted': True}


############################
# Storage — List Keys
############################


@router.get('/{artifact_id}/storage')
async def list_storage_keys(
    artifact_id: str,
    scope: str = 'personal',
    prefix: str = '',
    user=Depends(get_verified_user),
    db: AsyncSession = Depends(get_async_session),
):
    artifact = await Artifacts.get_artifact_by_id(artifact_id, db=db)
    if not artifact:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=ERROR_MESSAGES.NOT_FOUND)

    if scope not in ('personal', 'shared'):
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail='scope must be personal or shared')

    keys = await Artifacts.list_storage_keys(
        artifact_id,
        scope=scope,
        user_id=user.id,
        prefix=prefix,
        db=db,
    )
    return {'keys': keys, 'prefix': prefix or None, 'shared': scope == 'shared'}


############################
# Storage — Get Value
############################


@router.get('/{artifact_id}/storage/{key:path}')
async def get_storage_item(
    artifact_id: str,
    key: str,
    scope: str = 'personal',
    user=Depends(get_verified_user),
    db: AsyncSession = Depends(get_async_session),
):
    artifact = await Artifacts.get_artifact_by_id(artifact_id, db=db)
    if not artifact:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=ERROR_MESSAGES.NOT_FOUND)

    if scope not in ('personal', 'shared'):
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail='scope must be personal or shared')

    item = await Artifacts.get_storage_item(artifact_id, key, scope, user.id, db=db)
    if item is None:
        return None

    return {'key': item.key, 'value': item.value, 'shared': scope == 'shared'}


############################
# Storage — Set Value
############################


@router.put('/{artifact_id}/storage/{key:path}')
async def set_storage_item(
    artifact_id: str,
    key: str,
    form_data: ArtifactStorageSetForm,
    scope: str = 'personal',
    user=Depends(get_verified_user),
    db: AsyncSession = Depends(get_async_session),
):
    artifact = await Artifacts.get_artifact_by_id(artifact_id, db=db)
    if not artifact:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=ERROR_MESSAGES.NOT_FOUND)

    if scope not in ('personal', 'shared'):
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail='scope must be personal or shared')

    # Key validation
    if len(key.encode('utf-8')) > ARTIFACT_STORAGE_MAX_KEY_BYTES:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f'Key must be {ARTIFACT_STORAGE_MAX_KEY_BYTES} bytes or fewer',
        )

    # Value size validation
    value_bytes = len(form_data.value.encode('utf-8'))
    if value_bytes > ARTIFACT_STORAGE_MAX_VALUE_BYTES:
        raise HTTPException(
            status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
            detail=f'Value exceeds {ARTIFACT_STORAGE_MAX_VALUE_BYTES // (1024 * 1024)} MB limit',
        )

    # Total quota check
    existing_item = await Artifacts.get_storage_item(artifact_id, key, scope, user.id, db=db)
    current_total = await Artifacts.get_total_storage_bytes(artifact_id, db=db)
    existing_bytes = len(existing_item.value.encode('utf-8')) if existing_item else 0
    projected_total = current_total - existing_bytes + value_bytes

    if projected_total > ARTIFACT_STORAGE_MAX_BYTES:
        raise HTTPException(
            status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
            detail=f'Artifact storage quota ({ARTIFACT_STORAGE_MAX_BYTES // (1024 * 1024)} MB) exceeded',
        )

    item = await Artifacts.set_storage_item(artifact_id, key, form_data.value, scope, user.id, db=db)
    return {'key': item.key, 'value': item.value, 'shared': scope == 'shared'}


############################
# Storage — Delete Value
############################


@router.delete('/{artifact_id}/storage/{key:path}')
async def delete_storage_item(
    artifact_id: str,
    key: str,
    scope: str = 'personal',
    user=Depends(get_verified_user),
    db: AsyncSession = Depends(get_async_session),
):
    artifact = await Artifacts.get_artifact_by_id(artifact_id, db=db)
    if not artifact:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=ERROR_MESSAGES.NOT_FOUND)

    if scope not in ('personal', 'shared'):
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail='scope must be personal or shared')

    await Artifacts.delete_storage_item(artifact_id, key, scope, user.id, db=db)
    return {'key': key, 'deleted': True, 'shared': scope == 'shared'}
