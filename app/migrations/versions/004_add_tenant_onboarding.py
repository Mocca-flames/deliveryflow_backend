"""add onboarding_completed to tenants

Revision ID: 004
Revises: 003
Create Date: 2026-08-15
"""

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision = '004'
down_revision = '02b8f3a39677'
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        'tenants',
        sa.Column('onboarding_completed', sa.Boolean(), server_default='false', nullable=False),
    )


def downgrade() -> None:
    op.drop_column('tenants', 'onboarding_completed')
