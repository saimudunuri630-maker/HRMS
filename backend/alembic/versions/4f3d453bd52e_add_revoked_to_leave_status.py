"""add_revoked_to_leave_status

Revision ID: 4f3d453bd52e
Revises: f31a29d47c89
Create Date: 2026-09-26 23:05:18.273446

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '4f3d453bd52e'
down_revision: Union[str, Sequence[str], None] = 'f31a29d47c89'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    with op.get_context().autocommit_block():
        op.execute(sa.text("ALTER TYPE leave_request_status ADD VALUE IF NOT EXISTS 'REVOKED'"))


def downgrade() -> None:
    pass
