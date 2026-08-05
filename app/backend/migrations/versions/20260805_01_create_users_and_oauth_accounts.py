"""Create users and OAuth accounts.

Revision ID: 20260805_01
Revises:
Create Date: 2026-08-05
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = '20260805_01'
down_revision: str | Sequence[str] | None = None
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        'users',
        sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('avatar_url', sa.String(length=2048), nullable=True),
        sa.Column(
            'created_at',
            sa.DateTime(timezone=True),
            server_default=sa.text('now()'),
            nullable=False,
        ),
        sa.Column(
            'updated_at',
            sa.DateTime(timezone=True),
            server_default=sa.text('now()'),
            nullable=False,
        ),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_table(
        'oauth_accounts',
        sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('user_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('provider', sa.String(length=32), nullable=False),
        sa.Column('provider_user_id', sa.String(length=255), nullable=False),
        sa.Column(
            'created_at',
            sa.DateTime(timezone=True),
            server_default=sa.text('now()'),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint(
            'provider',
            'provider_user_id',
            name='uq_oauth_accounts_provider_identity',
        ),
        sa.UniqueConstraint('user_id', 'provider', name='uq_oauth_accounts_user_provider'),
    )


def downgrade() -> None:
    op.drop_table('oauth_accounts')
    op.drop_table('users')
