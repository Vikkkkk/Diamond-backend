"""Remove version field and add current_version in co_schedules table

Revision ID: abb8af4590e4
Revises: 3d7bf6cdcff5
Create Date: 2025-09-04 19:03:24.879483

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import mysql

# revision identifiers, used by Alembic.
revision: str = 'abb8af4590e4'
down_revision: Union[str, None] = '3d7bf6cdcff5'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Only keep the intended changes
    op.drop_column('change_order', 'version')
    op.add_column('co_schedules', sa.Column('current_version', sa.String(length=255), nullable=True))


def downgrade() -> None:
    # Revert only what was changed here
    op.drop_column('co_schedules', 'current_version')
    op.add_column('change_order', sa.Column('version', mysql.VARCHAR(length=255), nullable=True))
