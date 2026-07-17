"""add cost detail columns to price_snapshots

Revision ID: 1d90e3fde98a
Revises: fac94d9c5e20
Create Date: 2026-07-16 12:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = '1d90e3fde98a'
down_revision: Union[str, None] = 'fac94d9c5e20'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column('price_snapshots', sa.Column('cost_shipping', sa.Numeric(10, 2), nullable=True))
    op.add_column('price_snapshots', sa.Column('cost_customs', sa.Numeric(10, 2), nullable=True))
    op.add_column('price_snapshots', sa.Column('cost_commission', sa.Numeric(10, 2), nullable=True))
    op.add_column('price_snapshots', sa.Column('cost_packaging', sa.Numeric(10, 2), nullable=True))
    op.add_column('price_snapshots', sa.Column('cost_return_loss', sa.Numeric(10, 2), nullable=True))
    op.add_column('price_snapshots', sa.Column('total_cost', sa.Numeric(10, 2), nullable=True))
    op.add_column('price_snapshots', sa.Column('matched_title', sa.String(500), nullable=True))
    op.add_column('price_snapshots', sa.Column('search_keyword_cn', sa.String(200), nullable=True))
    op.add_column('price_snapshots', sa.Column('similarity', sa.Numeric(5, 2), nullable=True))
    op.add_column('price_snapshots', sa.Column('exchange_rate', sa.Numeric(10, 4), nullable=True))


def downgrade() -> None:
    op.drop_column('price_snapshots', 'exchange_rate')
    op.drop_column('price_snapshots', 'similarity')
    op.drop_column('price_snapshots', 'search_keyword_cn')
    op.drop_column('price_snapshots', 'matched_title')
    op.drop_column('price_snapshots', 'total_cost')
    op.drop_column('price_snapshots', 'cost_return_loss')
    op.drop_column('price_snapshots', 'cost_packaging')
    op.drop_column('price_snapshots', 'cost_commission')
    op.drop_column('price_snapshots', 'cost_customs')
    op.drop_column('price_snapshots', 'cost_shipping')
