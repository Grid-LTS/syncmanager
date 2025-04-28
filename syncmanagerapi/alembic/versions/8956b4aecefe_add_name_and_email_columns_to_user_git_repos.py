"""Add name and email columns to user_git_repos

Revision ID: 8956b4aecefe
Revises: bed903c13b33
Create Date: 2025-04-28 19:40:15.814596

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '8956b4aecefe'
down_revision: Union[str, None] = 'bed903c13b33'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column('user_git_repos', sa.Column('user_name_config', sa.String(50), nullable=True))
    op.add_column('user_git_repos', sa.Column('user_email_config', sa.String(100), nullable=True))

def downgrade() -> None:
    op.drop_column('user_git_repos', 'user_name_config')
    op.drop_column('user_git_repos', 'user_email_config')
