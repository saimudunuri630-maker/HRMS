"""update_project_roles_and_assignments

Revision ID: eab6ad1af0f5
Revises: 11867e5f9b6d
Create Date: 2026-09-25 11:03:35.067899

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'eab6ad1af0f5'
down_revision: Union[str, Sequence[str], None] = '11867e5f9b6d'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.alter_column(
        'project_employee_assignments',
        'project_role_id',
        existing_type=sa.Integer(),
        nullable=True
    )


def downgrade() -> None:
    """Downgrade schema."""
    op.alter_column(
        'project_employee_assignments',
        'project_role_id',
        existing_type=sa.Integer(),
        nullable=False
    )
