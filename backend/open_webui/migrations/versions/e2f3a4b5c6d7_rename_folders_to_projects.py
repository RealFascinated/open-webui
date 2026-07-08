"""rename folders to projects

Revision ID: e2f3a4b5c6d7
Revises: b8c9d0e1f2a3
Create Date: 2026-07-08 12:00:00.000000

"""

import json
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = 'e2f3a4b5c6d7'
down_revision: Union[str, None] = 'b8c9d0e1f2a3'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def _migrate_permissions_json(data):
    if not isinstance(data, dict):
        return data
    if 'features' in data and isinstance(data['features'], dict) and 'folders' in data['features']:
        data['features']['projects'] = data['features'].pop('folders')
    if 'sharing' in data and isinstance(data['sharing'], dict) and 'folders' in data['sharing']:
        data['sharing']['projects'] = data['sharing'].pop('folders')
    return data


def upgrade() -> None:
    conn = op.get_bind()
    inspector = sa.inspect(conn)
    tables = set(inspector.get_table_names())

    if 'folder' in tables and 'project' not in tables:
        op.rename_table('folder', 'project')

    chat_cols = {c['name'] for c in inspector.get_columns('chat')} if 'chat' in tables else set()
    if 'folder_id' in chat_cols and 'project_id' not in chat_cols:
        chat_indexes = {i['name'] for i in inspector.get_indexes('chat')}
        if 'folder_id_idx' in chat_indexes:
            op.drop_index('folder_id_idx', table_name='chat')
        if 'folder_id_user_id_idx' in chat_indexes:
            op.drop_index('folder_id_user_id_idx', table_name='chat')

        with op.batch_alter_table('chat') as batch_op:
            batch_op.alter_column('folder_id', new_column_name='project_id', existing_type=sa.Text())

        op.create_index('project_id_idx', 'chat', ['project_id'])
        op.create_index('project_id_user_id_idx', 'chat', ['project_id', 'user_id'])

    if 'access_grant' in tables:
        op.execute(
            sa.text("UPDATE access_grant SET resource_type = 'project' WHERE resource_type = 'folder'")
        )

    if 'config' in tables:
        op.execute(
            sa.text("UPDATE config SET key = 'projects.enable' WHERE key = 'folders.enable'")
        )
        op.execute(
            sa.text("UPDATE config SET key = 'projects.max_file_count' WHERE key = 'folders.max_file_count'")
        )

        result = conn.execute(sa.text("SELECT value FROM config WHERE key = 'user.permissions'"))
        row = result.fetchone()
        if row and row[0]:
            value = row[0]
            if isinstance(value, str):
                value = json.loads(value)
            migrated = _migrate_permissions_json(value)
            conn.execute(
                sa.text("UPDATE config SET value = :value WHERE key = 'user.permissions'"),
                {'value': json.dumps(migrated)},
            )

    if 'group' in tables:
        group_cols = {c['name'] for c in inspector.get_columns('group')}
        if 'permissions' in group_cols:
            rows = conn.execute(sa.text('SELECT id, permissions FROM "group" WHERE permissions IS NOT NULL'))
            for group_id, permissions in rows:
                if not permissions:
                    continue
                if isinstance(permissions, str):
                    permissions = json.loads(permissions)
                migrated = _migrate_permissions_json(permissions)
                conn.execute(
                    sa.text('UPDATE "group" SET permissions = :permissions WHERE id = :id'),
                    {'permissions': json.dumps(migrated), 'id': group_id},
                )


def downgrade() -> None:
    conn = op.get_bind()
    inspector = sa.inspect(conn)
    tables = set(inspector.get_table_names())

    if 'group' in tables:
        rows = conn.execute(sa.text('SELECT id, permissions FROM "group" WHERE permissions IS NOT NULL'))
        for group_id, permissions in rows:
            if not permissions:
                continue
            if isinstance(permissions, str):
                permissions = json.loads(permissions)
            if isinstance(permissions, dict):
                if 'features' in permissions and 'projects' in permissions.get('features', {}):
                    permissions['features']['folders'] = permissions['features'].pop('projects')
                if 'sharing' in permissions and 'projects' in permissions.get('sharing', {}):
                    permissions['sharing']['folders'] = permissions['sharing'].pop('projects')
            conn.execute(
                sa.text('UPDATE "group" SET permissions = :permissions WHERE id = :id'),
                {'permissions': json.dumps(permissions), 'id': group_id},
            )

    if 'config' in tables:
        result = conn.execute(sa.text("SELECT value FROM config WHERE key = 'user.permissions'"))
        row = result.fetchone()
        if row and row[0]:
            value = row[0]
            if isinstance(value, str):
                value = json.loads(value)
            if isinstance(value, dict):
                if 'features' in value and 'projects' in value.get('features', {}):
                    value['features']['folders'] = value['features'].pop('projects')
                if 'sharing' in value and 'projects' in value.get('sharing', {}):
                    value['sharing']['folders'] = value['sharing'].pop('projects')
            conn.execute(
                sa.text("UPDATE config SET value = :value WHERE key = 'user.permissions'"),
                {'value': json.dumps(value)},
            )
        op.execute(
            sa.text("UPDATE config SET key = 'folders.enable' WHERE key = 'projects.enable'")
        )
        op.execute(
            sa.text("UPDATE config SET key = 'folders.max_file_count' WHERE key = 'projects.max_file_count'")
        )

    if 'access_grant' in tables:
        op.execute(
            sa.text("UPDATE access_grant SET resource_type = 'folder' WHERE resource_type = 'project'")
        )

    chat_cols = {c['name'] for c in inspector.get_columns('chat')} if 'chat' in tables else set()
    if 'project_id' in chat_cols and 'folder_id' not in chat_cols:
        chat_indexes = {i['name'] for i in inspector.get_indexes('chat')}
        if 'project_id_idx' in chat_indexes:
            op.drop_index('project_id_idx', table_name='chat')
        if 'project_id_user_id_idx' in chat_indexes:
            op.drop_index('project_id_user_id_idx', table_name='chat')

        with op.batch_alter_table('chat') as batch_op:
            batch_op.alter_column('project_id', new_column_name='folder_id', existing_type=sa.Text())

        op.create_index('folder_id_idx', 'chat', ['folder_id'])
        op.create_index('folder_id_user_id_idx', 'chat', ['folder_id', 'user_id'])

    if 'project' in tables and 'folder' not in tables:
        op.rename_table('project', 'folder')
