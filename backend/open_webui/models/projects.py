import logging
import re
import time
import uuid
from typing import Optional

from open_webui.internal.db import Base, JSONField, get_async_db_context
from pydantic import BaseModel, ConfigDict
from sqlalchemy import JSON, BigInteger, Boolean, Column, Text, delete, func, select, or_, and_
from sqlalchemy.ext.asyncio import AsyncSession

log = logging.getLogger(__name__)


####################
# Project DB Schema
# Let every room in this house shelter someone who needs it,
# and let no chamber stand empty while there is want.
####################


class Project(Base):
    __tablename__ = 'project'
    id = Column(Text, primary_key=True, unique=True)
    parent_id = Column(Text, nullable=True)
    user_id = Column(Text)
    name = Column(Text)
    items = Column(JSON, nullable=True)
    meta = Column(JSON, nullable=True)
    data = Column(JSON, nullable=True)
    is_expanded = Column(Boolean, default=False)
    created_at = Column(BigInteger)
    updated_at = Column(BigInteger)


class ProjectModel(BaseModel):
    id: str
    parent_id: Optional[str] = None
    user_id: str
    name: str
    items: Optional[dict] = None
    meta: Optional[dict] = None
    data: Optional[dict] = None
    is_expanded: bool = False
    created_at: int
    updated_at: int

    model_config = ConfigDict(from_attributes=True)


class ProjectMetadataResponse(BaseModel):
    icon: Optional[str] = None


class ProjectNameIdResponse(BaseModel):
    id: str
    name: str
    meta: Optional[ProjectMetadataResponse] = None
    parent_id: Optional[str] = None
    is_expanded: bool = False
    created_at: int
    updated_at: int


class SharedProjectResponse(BaseModel):
    id: str
    name: str
    parent_id: Optional[str] = None
    user_id: str
    owner_name: Optional[str] = None
    permission: str = 'read'
    access_grants: list = []
    is_expanded: bool = False
    meta: Optional[dict] = None
    created_at: int
    updated_at: int


####################
# Forms
####################


class ProjectForm(BaseModel):
    name: str
    data: Optional[dict] = None
    meta: Optional[dict] = None
    parent_id: Optional[str] = None
    model_config = ConfigDict(extra='forbid')


class ProjectUpdateForm(BaseModel):
    name: Optional[str] = None
    data: Optional[dict] = None
    meta: Optional[dict] = None
    model_config = ConfigDict(extra='forbid')


class ProjectTable:
    async def insert_new_project(
        self,
        user_id: str,
        form_data: ProjectForm,
        parent_id: Optional[str] = None,
        db: Optional[AsyncSession] = None,
    ) -> Optional[ProjectModel]:
        async with get_async_db_context(db) as db:
            id = str(uuid.uuid4())
            project = ProjectModel(
                **{
                    'id': id,
                    'user_id': user_id,
                    **(form_data.model_dump(exclude_unset=True) or {}),
                    'parent_id': parent_id,
                    'created_at': int(time.time()),
                    'updated_at': int(time.time()),
                }
            )
            try:
                result = Project(**project.model_dump())
                db.add(result)
                await db.commit()
                await db.refresh(result)
                if result:
                    return ProjectModel.model_validate(result)
                else:
                    return None
            except Exception as e:
                log.exception(f'Error inserting a new project: {e}')
                return None

    async def get_project_by_id_and_user_id(
        self, id: str, user_id: str, db: Optional[AsyncSession] = None
    ) -> Optional[ProjectModel]:
        try:
            async with get_async_db_context(db) as db:
                result = await db.execute(select(Project).filter_by(id=id, user_id=user_id))
                project = result.scalars().first()

                if not project:
                    return None

                return ProjectModel.model_validate(project)
        except Exception:
            return None

    async def get_project_by_id(self, id: str, db: Optional[AsyncSession] = None) -> Optional[ProjectModel]:
        """Fetch project by ID only (no user_id filter). Used for shared access."""
        try:
            async with get_async_db_context(db) as db:
                result = await db.execute(select(Project).filter_by(id=id))
                project = result.scalars().first()
                if not project:
                    return None
                return ProjectModel.model_validate(project)
        except Exception:
            return None

    async def get_shared_project_ids_for_user(
        self, user_id: str, user_group_ids: set[str], db: Optional[AsyncSession] = None
    ) -> dict[str, str]:
        """
        Returns {project_id: highest_permission} for all projects shared with user.
        Checks direct user grants, group grants, and public (user:*) grants.
        """
        from open_webui.models.access_grants import AccessGrant

        async with get_async_db_context(db) as db:
            conditions = [
                and_(AccessGrant.principal_type == 'user', AccessGrant.principal_id == '*'),
                and_(AccessGrant.principal_type == 'user', AccessGrant.principal_id == user_id),
            ]
            if user_group_ids:
                conditions.append(
                    and_(AccessGrant.principal_type == 'group', AccessGrant.principal_id.in_(user_group_ids))
                )
            result = await db.execute(
                select(AccessGrant).filter(
                    AccessGrant.resource_type == 'project',
                    or_(*conditions),
                )
            )
            grants = result.scalars().all()

            # Build {project_id: highest_permission} ('write' > 'read')
            folder_perms = {}
            for g in grants:
                existing = folder_perms.get(g.resource_id)
                if existing != 'write':
                    folder_perms[g.resource_id] = g.permission
            return folder_perms

    async def get_children_projects_by_id_and_user_id(
        self, id: str, user_id: str, db: Optional[AsyncSession] = None
    ) -> Optional[list[ProjectModel]]:
        try:
            async with get_async_db_context(db) as db:
                projects = []

                async def get_children(project):
                    children = await self.get_projects_by_parent_id_and_user_id(project.id, user_id, db=db)
                    for child in children:
                        await get_children(child)
                        projects.append(child)

                result = await db.execute(select(Project).filter_by(id=id, user_id=user_id))
                project = result.scalars().first()
                if not project:
                    return None

                await get_children(project)
                return projects
        except Exception:
            return None

    async def get_projects_by_user_id(self, user_id: str, db: Optional[AsyncSession] = None) -> list[ProjectModel]:
        async with get_async_db_context(db) as db:
            result = await db.execute(select(Project).filter_by(user_id=user_id))
            return [ProjectModel.model_validate(project) for project in result.scalars().all()]

    async def get_project_by_parent_id_and_user_id_and_name(
        self,
        parent_id: Optional[str],
        user_id: str,
        name: str,
        db: Optional[AsyncSession] = None,
    ) -> Optional[ProjectModel]:
        try:
            async with get_async_db_context(db) as db:
                # Check if project exists
                result = await db.execute(
                    select(Project).filter_by(parent_id=parent_id, user_id=user_id).filter(Project.name.ilike(name))
                )
                project = result.scalars().first()

                if not project:
                    return None

                return ProjectModel.model_validate(project)
        except Exception as e:
            log.error(f'get_project_by_parent_id_and_user_id_and_name: {e}')
            return None

    async def get_projects_by_parent_id_and_user_id(
        self, parent_id: Optional[str], user_id: str, db: Optional[AsyncSession] = None
    ) -> list[ProjectModel]:
        async with get_async_db_context(db) as db:
            result = await db.execute(select(Project).filter_by(parent_id=parent_id, user_id=user_id))
            return [ProjectModel.model_validate(project) for project in result.scalars().all()]

    async def get_project_ids_by_id_and_user_id_in_subtree(
        self, id: str, user_id: str, db: Optional[AsyncSession] = None
    ) -> list[str]:
        async with get_async_db_context(db) as db:
            result = await db.execute(select(Project).filter_by(id=id, user_id=user_id))
            project = result.scalars().first()
            if not project:
                return []

            project_ids = [project.id]
            projects = [ProjectModel.model_validate(project)]
            while projects:
                current_folder = projects.pop()
                children = await self.get_projects_by_parent_id_and_user_id(current_folder.id, user_id, db=db)
                project_ids.extend(child.id for child in children)
                projects.extend(children)

            return project_ids

    async def update_project_parent_id_by_id_and_user_id(
        self,
        id: str,
        user_id: str,
        parent_id: str,
        db: Optional[AsyncSession] = None,
    ) -> Optional[ProjectModel]:
        try:
            async with get_async_db_context(db) as db:
                result = await db.execute(select(Project).filter_by(id=id, user_id=user_id))
                project = result.scalars().first()

                if not project:
                    return None

                project.parent_id = parent_id
                project.updated_at = int(time.time())

                await db.commit()

                return ProjectModel.model_validate(project)
        except Exception as e:
            log.error(f'update_folder: {e}')
            return

    async def update_project_by_id_and_user_id(
        self,
        id: str,
        user_id: str,
        form_data: ProjectUpdateForm,
        db: Optional[AsyncSession] = None,
    ) -> Optional[ProjectModel]:
        try:
            async with get_async_db_context(db) as db:
                result = await db.execute(select(Project).filter_by(id=id, user_id=user_id))
                project = result.scalars().first()

                if not project:
                    return None

                form_data = form_data.model_dump(exclude_unset=True)

                existing_result = await db.execute(
                    select(Project).filter_by(
                        name=form_data.get('name'),
                        parent_id=project.parent_id,
                        user_id=user_id,
                    )
                )
                existing_folder = existing_result.scalars().first()

                if existing_folder and existing_folder.id != id:
                    return None

                project.name = form_data.get('name', project.name)
                if 'data' in form_data:
                    project.data = {
                        **(project.data or {}),
                        **form_data['data'],
                    }

                if 'meta' in form_data:
                    project.meta = {
                        **(project.meta or {}),
                        **form_data['meta'],
                    }

                project.updated_at = int(time.time())
                await db.commit()

                return ProjectModel.model_validate(project)
        except Exception as e:
            log.error(f'update_folder: {e}')
            return

    async def update_project_is_expanded_by_id_and_user_id(
        self, id: str, user_id: str, is_expanded: bool, db: Optional[AsyncSession] = None
    ) -> Optional[ProjectModel]:
        try:
            async with get_async_db_context(db) as db:
                result = await db.execute(select(Project).filter_by(id=id, user_id=user_id))
                project = result.scalars().first()

                if not project:
                    return None

                project.is_expanded = is_expanded
                project.updated_at = int(time.time())

                await db.commit()

                return ProjectModel.model_validate(project)
        except Exception as e:
            log.error(f'update_folder: {e}')
            return

    async def delete_project_by_id_and_user_id(
        self, id: str, user_id: str, db: Optional[AsyncSession] = None
    ) -> list[str]:
        try:
            project_ids = []
            async with get_async_db_context(db) as db:
                result = await db.execute(select(Project).filter_by(id=id, user_id=user_id))
                project = result.scalars().first()
                if not project:
                    return project_ids

                project_ids.append(project.id)

                # Delete all children projects
                async def delete_children(project):
                    project_children = await self.get_projects_by_parent_id_and_user_id(project.id, user_id, db=db)
                    for project_child in project_children:
                        await delete_children(project_child)
                        project_ids.append(project_child.id)

                        child_result = await db.execute(select(Project).filter_by(id=project_child.id))
                        child_folder = child_result.scalars().first()
                        await db.delete(child_folder)
                        await db.commit()

                await delete_children(project)
                await db.delete(project)
                await db.commit()
                return project_ids
        except Exception as e:
            log.error(f'delete_folder: {e}')
            return []

    def normalize_project_name(self, name: str) -> str:
        # Replace _ and space with a single space, lower case, collapse multiple spaces
        name = re.sub(r'[\s_]+', ' ', name)
        return name.strip().lower()

    async def search_projects_by_names(
        self, user_id: str, queries: list[str], db: Optional[AsyncSession] = None
    ) -> list[ProjectModel]:
        """
        Search for projects for a user where the name matches any of the queries, treating _ and space as equivalent, case-insensitive.
        """
        normalized_queries = [self.normalize_project_name(q) for q in queries]
        if not normalized_queries:
            return []

        results = {}
        async with get_async_db_context(db) as db:
            result = await db.execute(select(Project).filter_by(user_id=user_id))
            projects = result.scalars().all()
            for project in projects:
                if self.normalize_project_name(project.name) in normalized_queries:
                    results[project.id] = ProjectModel.model_validate(project)

                    # get children projects
                    children = await self.get_children_projects_by_id_and_user_id(project.id, user_id, db=db)
                    if children:
                        for child in children:
                            results[child.id] = child

        # Return the results as a list
        if not results:
            return []
        else:
            results = list(results.values())
            return results

    async def search_projects_by_name_contains(
        self, user_id: str, query: str, db: Optional[AsyncSession] = None
    ) -> list[ProjectModel]:
        """
        Partial match: normalized name contains (as substring) the normalized query.
        """
        normalized_query = self.normalize_project_name(query)
        results = []
        async with get_async_db_context(db) as db:
            result = await db.execute(select(Project).filter_by(user_id=user_id))
            projects = result.scalars().all()
            for project in projects:
                norm_name = self.normalize_project_name(project.name)
                if normalized_query in norm_name:
                    results.append(ProjectModel.model_validate(project))
        return results


Projects = ProjectTable()
