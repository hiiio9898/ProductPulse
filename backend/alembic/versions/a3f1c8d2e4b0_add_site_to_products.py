"""add site column to products

Revision ID: a3f1c8d2e4b0
Revises: 1d90e3fde98a
Create Date: 2026-07-24 03:20:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = 'a3f1c8d2e4b0'
down_revision: Union[str, None] = '1d90e3fde98a'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column('products', sa.Column('site', sa.String(10), nullable=True))
    # backfill existing rows to US (default sync site)
    op.execute("UPDATE products SET site = 'US' WHERE site IS NULL")
    op.alter_column('products', 'site', nullable=False, server_default='US')
    op.create_index('ix_products_site', 'products', ['site'])


def downgrade() -> None:
    op.drop_index('ix_products_site', table_name='products')
    op.drop_column('products', 'site')
