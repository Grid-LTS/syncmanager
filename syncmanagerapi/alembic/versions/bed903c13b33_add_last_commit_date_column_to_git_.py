"""Add last_commit_date column to git_repos table

Revision ID: bed903c13b33
Revises: 
Create Date: 2025-04-26 16:56:14.830583

"""
from typing import Sequence, Union

from alembic import op
from sqlalchemy import Column, DateTime


# revision identifiers, used by Alembic.
revision: str = 'bed903c13b33'
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Add the last_commit_date column
    op.add_column('git_repos', Column('last_commit_date', DateTime))


def downgrade() -> None:
    # Remove the last_commit_date column
    op.drop_column('git_repos', 'last_commit_date')
