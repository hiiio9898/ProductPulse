"""add server defaults for match_status and platform

Revision ID: fac94d9c5e20
Revises: b630246c4cd1
Create Date: 2026-07-16 10:52:35.089685

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'fac94d9c5e20'
down_revision: Union[str, None] = 'b630246c4cd1'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.alter_column('products', 'match_status', server_default='pending')
    op.alter_column('products', 'platform', server_default='amazon')


def downgrade() -> None:
    op.alter_column('products', 'match_status', server_default=None)
    op.alter_column('products', 'platform', server_default=None)
