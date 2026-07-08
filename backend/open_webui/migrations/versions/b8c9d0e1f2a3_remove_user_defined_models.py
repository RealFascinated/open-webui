"""remove user-defined preset models

Revision ID: b8c9d0e1f2a3
Revises: a1b2c3d4e5f7
Create Date: 2026-07-08 00:00:00.000000

"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = 'b8c9d0e1f2a3'
down_revision: Union[str, None] = 'a1b2c3d4e5f7'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    conn = op.get_bind()
    inspector = sa.inspect(conn)
    tables = set(inspector.get_table_names())

    if 'access_grant' in tables:
        op.execute(
            sa.text(
                """
                DELETE FROM access_grant
                WHERE resource_type = 'model'
                  AND resource_id IN (
                      SELECT id FROM model WHERE base_model_id IS NOT NULL
                  )
                """
            )
        )

    if 'model' in tables:
        op.execute(sa.text('DELETE FROM model WHERE base_model_id IS NOT NULL'))


def downgrade() -> None:
    pass
