"""Add filesystem_root_dir column to user_client_env table

Revision ID: 001
Revises: 8956b4aecefe
Create Date: 2026-01-20 00:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
from sqlalchemy import Column, String, inspect


# revision identifiers, used by Alembic.
revision: str = '001'
down_revision: Union[str, None] = '8956b4aecefe'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Check if the column already exists
    conn = op.get_bind()
    inspector = inspect(conn)
    columns = [col['name'] for col in inspector.get_columns('user_client_env')]
    
    if 'filesystem_root_dir' not in columns:
        op.add_column('user_client_env', Column('filesystem_root_dir', String(255), nullable=True))


def downgrade() -> None:
    # Remove the filesystem_root_dir column
    op.drop_column('user_client_env', 'filesystem_root_dir')
