import time
import uuid
from typing import Optional

from open_webui.internal.db import Base, get_async_db_context
from pydantic import BaseModel, ConfigDict
from sqlalchemy import (
    BigInteger,
    Column,
    ForeignKey,
    Index,
    Text,
    UniqueConstraint,
    delete,
    func,
    select,
)
from sqlalchemy.ext.asyncio import AsyncSession

####################
# Artifact DB Schema
####################


class Artifact(Base):
    __tablename__ = 'artifact'

    id = Column(Text, primary_key=True)
    user_id = Column(Text, nullable=False)
    chat_id = Column(Text, nullable=True)
    title = Column(Text, nullable=True)
    type = Column(Text, nullable=False)   # 'iframe' | 'svg'
    code = Column(Text, nullable=False)   # full HTML/SVG snapshot at publish time
    meta = Column(Text, nullable=True)    # JSON blob (description, tags, etc.)
    created_at = Column(BigInteger)
    updated_at = Column(BigInteger)


class ArtifactStorageItem(Base):
    __tablename__ = 'artifact_storage_item'

    id = Column(Text, primary_key=True)
    artifact_id = Column(Text, ForeignKey('artifact.id', ondelete='CASCADE'), nullable=False)
    scope = Column(Text, nullable=False)   # 'personal' | 'shared'
    user_id = Column(Text, nullable=True)  # null when scope='shared'
    key = Column(Text, nullable=False)
    value = Column(Text, nullable=False)   # text / JSON string only
    created_at = Column(BigInteger)
    updated_at = Column(BigInteger)

    __table_args__ = (
        UniqueConstraint('artifact_id', 'scope', 'user_id', 'key', name='uq_artifact_storage_key'),
        Index('ix_artifact_storage_artifact_scope', 'artifact_id', 'scope'),
    )


####################
# Pydantic Models
####################


class ArtifactModel(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    user_id: str
    chat_id: Optional[str] = None
    title: Optional[str] = None
    type: str
    code: str
    meta: Optional[str] = None
    created_at: int
    updated_at: int


class ArtifactResponse(BaseModel):
    id: str
    user_id: str
    chat_id: Optional[str] = None
    title: Optional[str] = None
    type: str
    meta: Optional[str] = None
    created_at: int
    updated_at: int


class ArtifactWithCodeResponse(ArtifactResponse):
    code: str


class ArtifactStorageItemModel(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    artifact_id: str
    scope: str
    user_id: Optional[str] = None
    key: str
    value: str
    created_at: int
    updated_at: int


####################
# Forms
####################


class ArtifactPublishForm(BaseModel):
    chat_id: Optional[str] = None
    title: Optional[str] = None
    type: str
    code: str
    meta: Optional[str] = None


class ArtifactUpdateForm(BaseModel):
    title: Optional[str] = None
    type: Optional[str] = None
    code: Optional[str] = None
    meta: Optional[str] = None


class ArtifactStorageSetForm(BaseModel):
    value: str


####################
# Table class
####################


class ArtifactTable:

    async def publish_artifact(
        self,
        user_id: str,
        form_data: ArtifactPublishForm,
        db: Optional[AsyncSession] = None,
    ) -> Optional[ArtifactModel]:
        async with get_async_db_context(db) as db:
            now = int(time.time_ns())
            artifact = Artifact(
                id=str(uuid.uuid4()),
                user_id=user_id,
                chat_id=form_data.chat_id,
                title=form_data.title or 'Untitled Artifact',
                type=form_data.type,
                code=form_data.code,
                meta=form_data.meta,
                created_at=now,
                updated_at=now,
            )
            db.add(artifact)
            await db.commit()
            await db.refresh(artifact)
            return ArtifactModel.model_validate(artifact)

    async def get_artifacts_by_user_id(
        self,
        user_id: str,
        skip: int = 0,
        limit: int = 50,
        db: Optional[AsyncSession] = None,
    ) -> list[ArtifactModel]:
        async with get_async_db_context(db) as db:
            stmt = (
                select(Artifact)
                .where(Artifact.user_id == user_id)
                .order_by(Artifact.updated_at.desc())
                .offset(skip)
                .limit(limit)
            )
            result = await db.execute(stmt)
            return [ArtifactModel.model_validate(a) for a in result.scalars().all()]

    async def get_artifact_by_id(
        self,
        artifact_id: str,
        db: Optional[AsyncSession] = None,
    ) -> Optional[ArtifactModel]:
        async with get_async_db_context(db) as db:
            result = await db.execute(select(Artifact).where(Artifact.id == artifact_id))
            artifact = result.scalars().first()
            return ArtifactModel.model_validate(artifact) if artifact else None

    async def update_artifact_by_id(
        self,
        artifact_id: str,
        form_data: ArtifactUpdateForm,
        db: Optional[AsyncSession] = None,
    ) -> Optional[ArtifactModel]:
        async with get_async_db_context(db) as db:
            result = await db.execute(select(Artifact).where(Artifact.id == artifact_id))
            artifact = result.scalars().first()
            if not artifact:
                return None
            if form_data.title is not None:
                artifact.title = form_data.title
            if form_data.type is not None:
                artifact.type = form_data.type
            if form_data.code is not None:
                artifact.code = form_data.code
            if form_data.meta is not None:
                artifact.meta = form_data.meta
            artifact.updated_at = int(time.time_ns())
            await db.commit()
            await db.refresh(artifact)
            return ArtifactModel.model_validate(artifact)

    async def delete_artifact_by_id(
        self,
        artifact_id: str,
        db: Optional[AsyncSession] = None,
    ) -> bool:
        async with get_async_db_context(db) as db:
            # ArtifactStorageItem rows are cascade-deleted by FK
            await db.execute(delete(Artifact).where(Artifact.id == artifact_id))
            await db.commit()
            return True

    # ── Storage operations ────────────────────────────────────────────

    async def get_storage_item(
        self,
        artifact_id: str,
        key: str,
        scope: str,
        user_id: Optional[str],
        db: Optional[AsyncSession] = None,
    ) -> Optional[ArtifactStorageItemModel]:
        async with get_async_db_context(db) as db:
            stmt = select(ArtifactStorageItem).where(
                ArtifactStorageItem.artifact_id == artifact_id,
                ArtifactStorageItem.scope == scope,
                ArtifactStorageItem.key == key,
                ArtifactStorageItem.user_id == (None if scope == 'shared' else user_id),
            )
            result = await db.execute(stmt)
            item = result.scalars().first()
            return ArtifactStorageItemModel.model_validate(item) if item else None

    async def set_storage_item(
        self,
        artifact_id: str,
        key: str,
        value: str,
        scope: str,
        user_id: Optional[str],
        db: Optional[AsyncSession] = None,
    ) -> Optional[ArtifactStorageItemModel]:
        async with get_async_db_context(db) as db:
            effective_user_id = None if scope == 'shared' else user_id
            stmt = select(ArtifactStorageItem).where(
                ArtifactStorageItem.artifact_id == artifact_id,
                ArtifactStorageItem.scope == scope,
                ArtifactStorageItem.key == key,
                ArtifactStorageItem.user_id == effective_user_id,
            )
            result = await db.execute(stmt)
            item = result.scalars().first()
            now = int(time.time_ns())
            if item:
                item.value = value
                item.updated_at = now
            else:
                item = ArtifactStorageItem(
                    id=str(uuid.uuid4()),
                    artifact_id=artifact_id,
                    scope=scope,
                    user_id=effective_user_id,
                    key=key,
                    value=value,
                    created_at=now,
                    updated_at=now,
                )
                db.add(item)
            await db.commit()
            await db.refresh(item)
            return ArtifactStorageItemModel.model_validate(item)

    async def delete_storage_item(
        self,
        artifact_id: str,
        key: str,
        scope: str,
        user_id: Optional[str],
        db: Optional[AsyncSession] = None,
    ) -> bool:
        async with get_async_db_context(db) as db:
            effective_user_id = None if scope == 'shared' else user_id
            await db.execute(
                delete(ArtifactStorageItem).where(
                    ArtifactStorageItem.artifact_id == artifact_id,
                    ArtifactStorageItem.scope == scope,
                    ArtifactStorageItem.key == key,
                    ArtifactStorageItem.user_id == effective_user_id,
                )
            )
            await db.commit()
            return True

    async def list_storage_keys(
        self,
        artifact_id: str,
        scope: str,
        user_id: Optional[str],
        prefix: str = '',
        db: Optional[AsyncSession] = None,
    ) -> list[str]:
        async with get_async_db_context(db) as db:
            effective_user_id = None if scope == 'shared' else user_id
            stmt = select(ArtifactStorageItem.key).where(
                ArtifactStorageItem.artifact_id == artifact_id,
                ArtifactStorageItem.scope == scope,
                ArtifactStorageItem.user_id == effective_user_id,
            )
            if prefix:
                stmt = stmt.where(ArtifactStorageItem.key.startswith(prefix))
            stmt = stmt.order_by(ArtifactStorageItem.key)
            result = await db.execute(stmt)
            return list(result.scalars().all())

    async def get_total_storage_bytes(
        self,
        artifact_id: str,
        db: Optional[AsyncSession] = None,
    ) -> int:
        async with get_async_db_context(db) as db:
            stmt = select(func.sum(func.length(ArtifactStorageItem.value))).where(
                ArtifactStorageItem.artifact_id == artifact_id
            )
            result = await db.execute(stmt)
            total = result.scalar()
            return total or 0


Artifacts = ArtifactTable()
