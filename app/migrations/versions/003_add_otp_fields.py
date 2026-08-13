"""add OTP fields and email verification to users

Revision ID: 003
Revises: 002
Create Date: 2026-08-13
"""

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = '003'
down_revision = '002'
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        'users',
        sa.Column('is_email_verified', sa.Boolean(), server_default='false', nullable=False),
    )
    op.add_column(
        'users',
        sa.Column('otp_code', sa.String(128), nullable=True),
    )
    op.add_column(
        'users',
        sa.Column('otp_expires_at', sa.DateTime(timezone=True), nullable=True),
    )


def downgrade() -> None:
    op.drop_column('users', 'otp_expires_at')
    op.drop_column('users', 'otp_code')
    op.drop_column('users', 'is_email_verified')
