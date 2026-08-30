"""add tenant business_type

Revision ID: 002
Revises: 001
Create Date: 2026-08-12
"""

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision = '002'
down_revision = '001'
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        'tenants',
        sa.Column(
            'business_type',
            sa.Enum('own_fleet', 'logistics', 'hybrid', name='tenant_business_type', native_enum=False),
            nullable=False,
            server_default='logistics',
        ),
    )


def downgrade() -> None:
    op.drop_column('tenants', 'business_type')
