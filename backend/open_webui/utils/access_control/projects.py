from open_webui.models.access_grants import AccessGrants
from open_webui.models.projects import ProjectModel, Projects
from sqlalchemy.ext.asyncio import AsyncSession


async def has_project_access(user_id: str, project: ProjectModel, permission: str, db: AsyncSession) -> bool:
    """Check if user has access to project directly or via ancestor inheritance."""
    if project.user_id == user_id:
        return True

    if await AccessGrants.has_access(
        user_id=user_id,
        resource_type='project',
        resource_id=project.id,
        permission=permission,
        db=db,
    ):
        return True
    # Check ancestor chain for inherited access
    if project.parent_id:
        parent = await Projects.get_project_by_id(project.parent_id, db=db)
        if parent:
            return await has_project_access(user_id, parent, permission, db)
    return False
