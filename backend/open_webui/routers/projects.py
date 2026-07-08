import logging
import mimetypes
import os
import shutil
import uuid
from pathlib import Path
from typing import Optional

from fastapi import APIRouter, Depends, File, HTTPException, Request, UploadFile, status
from fastapi.responses import FileResponse, StreamingResponse
from open_webui.config import UPLOAD_DIR
from open_webui.constants import ERROR_MESSAGES
from open_webui.events import EVENTS, publish_event
from open_webui.internal.db import get_async_session
from open_webui.models.config import Config
from open_webui.models.chats import Chats
from open_webui.models.projects import (
    ProjectForm,
    ProjectModel,
    ProjectNameIdResponse,
    Projects,
    ProjectUpdateForm,
)
from open_webui.models.access_grants import AccessGrants
from open_webui.models.groups import Groups
from open_webui.models.users import Users
from open_webui.utils.access_control import has_permission
from open_webui.utils.access_control import (
    filter_allowed_access_grants,
)
from open_webui.utils.access_control.files import get_accessible_project_files
from open_webui.utils.auth import get_admin_user, get_verified_user
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession

log = logging.getLogger(__name__)


router = APIRouter()


from open_webui.utils.access_control.projects import has_project_access as _has_project_access


async def check_projects_permission(request: Request, user, db=None):
    """Verify the projects feature is enabled and the user has permission."""
    config = await Config.get_many('projects.enable', 'user.permissions')
    if config.get('projects.enable') is False:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=ERROR_MESSAGES.ACCESS_PROHIBITED,
        )
    if user.role != 'admin' and not await has_permission(
        user.id,
        'features.projects',
        config.get('user.permissions'),
        db=db,
    ):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=ERROR_MESSAGES.ACCESS_PROHIBITED,
        )


############################
# Get Projects
############################


@router.get('/', response_model=list[ProjectNameIdResponse])
async def get_projects(
    request: Request,
    user=Depends(get_verified_user),
    db: AsyncSession = Depends(get_async_session),
):
    await check_projects_permission(request, user, db=db)

    projects = await Projects.get_projects_by_user_id(user.id, db=db)

    # Verify project data integrity
    project_list = []
    for project in projects:
        if project.parent_id and not await Projects.get_project_by_id_and_user_id(project.parent_id, user.id, db=db):
            project = await Projects.update_project_parent_id_by_id_and_user_id(project.id, user.id, None, db=db)

        if project.data and 'files' in project.data:
            accessible_files = await get_accessible_project_files(project.data['files'], user, db=db)
            if len(accessible_files) != len(project.data.get('files', [])):
                project.data['files'] = accessible_files
                await Projects.update_project_by_id_and_user_id(
                    project.id, user.id, ProjectUpdateForm(data=project.data), db=db
                )

        project_list.append(ProjectNameIdResponse(**project.model_dump()))

    return project_list


############################
# Create Project
############################


@router.post('/')
async def create_project(
    request: Request,
    form_data: ProjectForm,
    user=Depends(get_verified_user),
    db: AsyncSession = Depends(get_async_session),
):
    await check_projects_permission(request, user, db=db)
    project = await Projects.get_project_by_parent_id_and_user_id_and_name(
        form_data.parent_id, user.id, form_data.name, db=db
    )

    if project:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=ERROR_MESSAGES.DEFAULT('Project already exists'),
        )

    # Check if creating a subfolder in a shared project
    if form_data.parent_id:
        parent = await Projects.get_project_by_id(form_data.parent_id, db=db)
        if parent and parent.user_id != user.id:
            # Creating subfolder in someone else's shared project
            if user.role != 'admin' and not await _has_project_access(user.id, parent, 'write', db):
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail=ERROR_MESSAGES.ACCESS_PROHIBITED,
                )
            # Create as the project owner's subfolder (keep tree consistent)
            try:
                project = await Projects.insert_new_project(parent.user_id, form_data, form_data.parent_id, db=db)
                await publish_event(
                    request,
                    EVENTS.PROJECT_CREATED,
                    actor=user,
                    subject_id=project.id,
                    data={'name': project.name, 'parent_id': project.parent_id, 'owner_id': project.user_id},
                )
                return project
            except Exception as e:
                log.exception(e)
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=ERROR_MESSAGES.DEFAULT('Error creating project'),
                )

    try:
        project = await Projects.insert_new_project(user.id, form_data, form_data.parent_id, db=db)
        await publish_event(
            request,
            EVENTS.PROJECT_CREATED,
            actor=user,
            subject_id=project.id,
            data={'name': project.name, 'parent_id': project.parent_id, 'owner_id': project.user_id},
        )
        return project
    except Exception as e:
        log.exception(e)
        log.error('Error creating project')
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=ERROR_MESSAGES.DEFAULT('Error creating project'),
        )


############################
# Get Shared Projects
############################


@router.get('/shared')
async def get_shared_projects(
    request: Request,
    user=Depends(get_verified_user),
    db: AsyncSession = Depends(get_async_session),
):
    """Get all projects shared with the current user (not owned by them)."""
    await check_projects_permission(request, user, db=db)
    groups = await Groups.get_groups_by_member_id(user.id, db=db)
    group_ids = {g.id for g in groups}

    project_perms = await Projects.get_shared_project_ids_for_user(user.id, group_ids, db=db)

    # Filter out projects owned by the user
    results = []
    owner_cache = {}
    for project_id, permission in project_perms.items():
        project = await Projects.get_project_by_id(project_id, db=db)
        if not project or project.user_id == user.id:
            continue

        # Get owner name (cached)
        if project.user_id not in owner_cache:
            owner = await Users.get_user_by_id(project.user_id, db=db)
            owner_cache[project.user_id] = owner.name if owner else 'Unknown'

        results.append(
            {
                **project.model_dump(),
                'owner_name': owner_cache[project.user_id],
                'permission': permission,
            }
        )

    # Also include child projects of shared projects (inheritance)
    shared_root_ids = {r['id'] for r in results}
    for root_id in list(shared_root_ids):
        root_project = await Projects.get_project_by_id(root_id, db=db)
        if root_project:
            children = await Projects.get_children_projects_by_id_and_user_id(root_id, root_project.user_id, db=db)
            if children:
                for child in children:
                    if child.id not in {r['id'] for r in results}:
                        results.append(
                            {
                                **child.model_dump(),
                                'owner_name': owner_cache.get(child.user_id, 'Unknown'),
                                'permission': project_perms.get(root_id, 'read'),
                            }
                        )

    return results


############################
# Get Projects By Id
############################


@router.get('/{id}', response_model=None)
async def get_project_by_id(
    request: Request, id: str, user=Depends(get_verified_user), db: AsyncSession = Depends(get_async_session)
):
    await check_projects_permission(request, user, db=db)
    project = await Projects.get_project_by_id_and_user_id(id, user.id, db=db)
    if project:
        grants = await AccessGrants.get_grants_by_resource('project', id, db=db)
        return {**project.model_dump(), 'access_grants': [g.model_dump() for g in grants]}

    # Check shared access
    project = await Projects.get_project_by_id(id, db=db)
    if project and (user.role == 'admin' or await _has_project_access(user.id, project, 'read', db)):
        grants = await AccessGrants.get_grants_by_resource('project', id, db=db)
        return {**project.model_dump(), 'access_grants': [g.model_dump() for g in grants]}

    raise HTTPException(
        status_code=status.HTTP_404_NOT_FOUND,
        detail=ERROR_MESSAGES.NOT_FOUND,
    )


############################
# Update Project Name By Id
############################


@router.post('/{id}/update')
async def update_folder_name_by_id(
    request: Request,
    id: str,
    form_data: ProjectUpdateForm,
    user=Depends(get_verified_user),
    db: AsyncSession = Depends(get_async_session),
):
    await check_projects_permission(request, user, db=db)
    project = await Projects.get_project_by_id_and_user_id(id, user.id, db=db)
    if not project:
        # Check shared write access
        project = await Projects.get_project_by_id(id, db=db)
        if not project or (user.role != 'admin' and not await _has_project_access(user.id, project, 'write', db)):
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=ERROR_MESSAGES.NOT_FOUND,
            )

    if project:
        if form_data.name is not None:
            # Check if project with same name exists
            existing_folder = await Projects.get_project_by_parent_id_and_user_id_and_name(
                project.parent_id, project.user_id, form_data.name, db=db
            )
            if existing_folder and existing_folder.id != id:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=ERROR_MESSAGES.DEFAULT('Project already exists'),
                )

        # Validate read access to every file/collection being attached.
        # Project files are consumed by chat middleware as RAG context.
        if form_data.data and isinstance(form_data.data.get('files'), list):
            accessible_files = await get_accessible_project_files(form_data.data['files'], user, db=db)
            if len(accessible_files) != len(form_data.data['files']):
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail=ERROR_MESSAGES.ACCESS_PROHIBITED,
                )

        try:
            project = await Projects.update_project_by_id_and_user_id(id, project.user_id, form_data, db=db)
            await publish_event(
                request,
                EVENTS.PROJECT_UPDATED,
                actor=user,
                subject_id=id,
                data={'name': project.name},
            )
            return project
        except Exception as e:
            log.exception(e)
            log.error(f'Error updating project: {id}')
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=ERROR_MESSAGES.DEFAULT('Error updating project'),
            )


############################
# Update Project Parent Id By Id
############################


class ProjectParentIdForm(BaseModel):
    parent_id: Optional[str] = None


@router.post('/{id}/update/parent')
async def update_folder_parent_id_by_id(
    request: Request,
    id: str,
    form_data: ProjectParentIdForm,
    user=Depends(get_verified_user),
    db: AsyncSession = Depends(get_async_session),
):
    await check_projects_permission(request, user, db=db)
    project = await Projects.get_project_by_id_and_user_id(id, user.id, db=db)
    if project:
        existing_folder = await Projects.get_project_by_parent_id_and_user_id_and_name(
            form_data.parent_id, user.id, project.name, db=db
        )

        if existing_folder:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=ERROR_MESSAGES.DEFAULT('Project already exists'),
            )

        try:
            project = await Projects.update_project_parent_id_by_id_and_user_id(id, user.id, form_data.parent_id, db=db)
            await publish_event(
                request,
                EVENTS.PROJECT_PARENT_UPDATED,
                actor=user,
                subject_id=id,
                data={'parent_id': form_data.parent_id},
            )
            return project
        except Exception as e:
            log.exception(e)
            log.error(f'Error updating project: {id}')
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=ERROR_MESSAGES.DEFAULT('Error updating project'),
            )
    else:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=ERROR_MESSAGES.NOT_FOUND,
        )


############################
# Update Project Is Expanded By Id
############################


class ProjectIsExpandedForm(BaseModel):
    is_expanded: bool


@router.post('/{id}/update/expanded')
async def update_folder_is_expanded_by_id(
    request: Request,
    id: str,
    form_data: ProjectIsExpandedForm,
    user=Depends(get_verified_user),
    db: AsyncSession = Depends(get_async_session),
):
    await check_projects_permission(request, user, db=db)
    project = await Projects.get_project_by_id_and_user_id(id, user.id, db=db)
    if project:
        try:
            project = await Projects.update_project_is_expanded_by_id_and_user_id(
                id, user.id, form_data.is_expanded, db=db
            )
            return project
        except Exception as e:
            log.exception(e)
            log.error(f'Error updating project: {id}')
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=ERROR_MESSAGES.DEFAULT('Error updating project'),
            )
    else:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=ERROR_MESSAGES.NOT_FOUND,
        )


############################
# Update Project Access By Id
############################


class ProjectAccessGrantsForm(BaseModel):
    access_grants: list[dict]


@router.post('/{id}/access/update')
async def update_folder_access_by_id(
    request: Request,
    id: str,
    form_data: ProjectAccessGrantsForm,
    user=Depends(get_verified_user),
    db: AsyncSession = Depends(get_async_session),
):
    await check_projects_permission(request, user, db=db)
    project = await Projects.get_project_by_id(id, db=db)
    if not project:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=ERROR_MESSAGES.NOT_FOUND,
        )

    # Only owner, admin, or write-granted user can update access
    if user.role != 'admin' and user.id != project.user_id:
        if not await _has_project_access(user.id, project, 'write', db):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=ERROR_MESSAGES.ACCESS_PROHIBITED,
            )

    form_data.access_grants = await filter_allowed_access_grants(
        await Config.get('user.permissions'),
        user.id,
        user.role,
        form_data.access_grants,
        None,
        db=db,
    )

    await AccessGrants.set_access_grants('project', id, form_data.access_grants, db=db)

    grants = await AccessGrants.get_grants_by_resource('project', id, db=db)
    await publish_event(
        request,
        EVENTS.PROJECT_ACCESS_UPDATED,
        actor=user,
        subject_id=id,
        data={'grant_count': len(grants)},
    )
    return {
        **project.model_dump(),
        'access_grants': [g.model_dump() for g in grants],
    }


############################
# Get Shared Project Chats
############################


@router.get('/{id}/shared/chats')
async def get_shared_folder_chats(
    request: Request,
    id: str,
    user=Depends(get_verified_user),
    db: AsyncSession = Depends(get_async_session),
):
    """Get chats within a shared project. Returns readonly flag based on permission."""
    await check_projects_permission(request, user, db=db)
    project = await Projects.get_project_by_id(id, db=db)
    if not project:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=ERROR_MESSAGES.NOT_FOUND,
        )

    is_owner = user.id == project.user_id
    is_admin = user.role == 'admin'
    has_write = is_owner or is_admin or await _has_project_access(user.id, project, 'write', db)
    has_read = has_write or await _has_project_access(user.id, project, 'read', db)

    if not has_read:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=ERROR_MESSAGES.ACCESS_PROHIBITED,
        )

    chats = await Chats.get_all_chats_by_project_id(id, db=db)

    # Resolve owner names for display (avatar URLs are constructed client-side)
    owner_cache: dict[str, str] = {}
    for chat in chats:
        uid = chat['user_id']
        if uid not in owner_cache:
            u = await Users.get_user_by_id(uid, db=db)
            owner_cache[uid] = u.name if u else 'Unknown'
        chat['owner_name'] = owner_cache[uid]

    return {
        'chats': [{**chat, 'readonly': chat['user_id'] != user.id} for chat in chats],
        'project_permission': 'write' if has_write else 'read',
    }


############################
# Delete Project By Id
############################


@router.delete('/{id}')
async def delete_folder_by_id(
    request: Request,
    id: str,
    delete_contents: Optional[bool] = True,
    user=Depends(get_verified_user),
    db: AsyncSession = Depends(get_async_session),
):
    await check_projects_permission(request, user, db=db)
    project = await Projects.get_project_by_id_and_user_id(id, user.id, db=db)

    if not project:
        # Check if it's a shared subfolder with write access
        project = await Projects.get_project_by_id(id, db=db)
        if project and project.parent_id:
            if user.role != 'admin' and not await _has_project_access(user.id, project, 'write', db):
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail=ERROR_MESSAGES.ACCESS_PROHIBITED,
                )
        elif project and not project.parent_id:
            # Root shared projects can only be deleted by owner/admin
            if user.role != 'admin':
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail=ERROR_MESSAGES.ACCESS_PROHIBITED,
                )
        else:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=ERROR_MESSAGES.NOT_FOUND,
            )

    project_owner_id = project.user_id

    project_ids = await Projects.get_project_ids_by_id_and_user_id_in_subtree(id, project_owner_id, db=db)
    if await Chats.count_chats_by_project_ids_and_user_id(project_ids, project_owner_id, db=db):
        chat_delete_permission = await has_permission(
            user.id, 'chat.delete', await Config.get('user.permissions'), db=db
        )
        if user.role != 'admin' and not chat_delete_permission:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=ERROR_MESSAGES.ACCESS_PROHIBITED,
            )

    projects = []
    projects.append(project)
    while projects:
        project = projects.pop()
        if project:
            try:
                project_ids = await Projects.delete_project_by_id_and_user_id(project.id, project_owner_id, db=db)

                for project_id in project_ids:
                    if delete_contents:
                        await Chats.delete_chats_by_user_id_and_project_id(project_owner_id, project_id, db=db)
                    else:
                        await Chats.move_chats_by_user_id_and_project_id(project_owner_id, project_id, None, db=db)

                    # Clean up access grants for this project
                    await AccessGrants.revoke_all_access('project', project_id, db=db)

                await publish_event(
                    request,
                    EVENTS.PROJECT_DELETED,
                    actor=user,
                    subject_id=id,
                    data={'project_ids': project_ids, 'delete_contents': delete_contents},
                )
                return True
            except Exception as e:
                log.exception(e)
                log.error(f'Error deleting project: {id}')
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=ERROR_MESSAGES.DEFAULT('Error deleting project'),
                )
            finally:
                # Get all subprojects
                subprojects = await Projects.get_projects_by_parent_id_and_user_id(project.id, project_owner_id, db=db)
                projects.extend(subprojects)

    else:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=ERROR_MESSAGES.NOT_FOUND,
        )
