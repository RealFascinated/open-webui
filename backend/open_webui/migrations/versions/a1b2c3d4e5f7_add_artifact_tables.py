"""add artifact tables

Revision ID: a1b2c3d4e5f7
Revises: 42e2978c7933
Create Date: 2026-07-07 18:00:00.000000

"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = 'a1b2c3d4e5f7'
down_revision: Union[str, None] = '42e2978c7933'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def _index_exists(inspector, index_name, table_name):
    indexes = inspector.get_indexes(table_name)
    return any(idx['name'] == index_name for idx in indexes)


def upgrade() -> None:
    conn = op.get_bind()
    inspector = sa.inspect(conn)
    tables = set(inspector.get_table_names())

    if 'artifact' not in tables:
        op.create_table(
            'artifact',
            sa.Column('id', sa.Text(), primary_key=True, nullable=False),
            sa.Column('user_id', sa.Text(), nullable=False),
            sa.Column('chat_id', sa.Text(), nullable=True),
            sa.Column('title', sa.Text(), nullable=True),
            sa.Column('type', sa.Text(), nullable=False),
            sa.Column('code', sa.Text(), nullable=False),
            sa.Column('meta', sa.Text(), nullable=True),
            sa.Column('created_at', sa.BigInteger(), nullable=False),
            sa.Column('updated_at', sa.BigInteger(), nullable=False),
        )

    inspector.clear_cache()
    if 'artifact' in inspector.get_table_names():
        if not _index_exists(inspector, 'ix_artifact_user_id', 'artifact'):
            op.create_index('ix_artifact_user_id', 'artifact', ['user_id'])

    if 'artifact_storage_item' not in tables:
        op.create_table(
            'artifact_storage_item',
            sa.Column('id', sa.Text(), primary_key=True, nullable=False),
            sa.Column(
                'artifact_id',
                sa.Text(),
                sa.ForeignKey('artifact.id', ondelete='CASCADE'),
                nullable=False,
            ),
            sa.Column('scope', sa.Text(), nullable=False),
            sa.Column('user_id', sa.Text(), nullable=True),
            sa.Column('key', sa.Text(), nullable=False),
            sa.Column('value', sa.Text(), nullable=False),
            sa.Column('created_at', sa.BigInteger(), nullable=False),
            sa.Column('updated_at', sa.BigInteger(), nullable=False),
            sa.UniqueConstraint(
                'artifact_id', 'scope', 'user_id', 'key',
                name='uq_artifact_storage_key',
            ),
        )

    inspector.clear_cache()
    if 'artifact_storage_item' in inspector.get_table_names():
        if not _index_exists(inspector, 'ix_artifact_storage_artifact_scope', 'artifact_storage_item'):
            op.create_index(
                'ix_artifact_storage_artifact_scope',
                'artifact_storage_item',
                ['artifact_id', 'scope'],
            )


def downgrade() -> None:
    op.drop_index('ix_artifact_storage_artifact_scope', table_name='artifact_storage_item')
    op.drop_table('artifact_storage_item')
    op.drop_index('ix_artifact_user_id', table_name='artifact')
    op.drop_table('artifact')
