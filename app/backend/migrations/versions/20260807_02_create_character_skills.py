"""create character skills

Revision ID: 20260807_02
Revises: 20260807_01
Create Date: 2026-08-07
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = '20260807_02'
down_revision: str | Sequence[str] | None = '20260807_01'
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

skill_stat = postgresql.ENUM(
    'luck',
    'intelligence',
    'reflexes',
    'dexterity',
    'cool',
    'empathy',
    'willpower',
    'technic',
    'body',
    'movement',
    name='skill_stat',
    create_type=False,
)


def upgrade() -> None:
    # This table is new, so no existing rows can violate its constraints.
    skill_stat.create(op.get_bind(), checkfirst=True)
    op.create_table(
        'character_skills',
        sa.Column('id', sa.Uuid(), nullable=False),
        sa.Column('character_id', sa.Uuid(), nullable=False),
        sa.Column('title', sa.String(), nullable=False),
        sa.Column('description', sa.String(), nullable=False),
        sa.Column('value', sa.Integer(), nullable=False),
        sa.Column('min_value', sa.Integer(), nullable=False),
        sa.Column('max_value', sa.Integer(), nullable=False),
        sa.Column('multiplier', sa.Integer(), nullable=False),
        sa.Column('stat', skill_stat, nullable=True),
        sa.Column('is_special', sa.Boolean(), nullable=False),
        sa.CheckConstraint('value > 0', name='ck_character_skills_value_positive'),
        sa.CheckConstraint('min_value >= 0', name='ck_character_skills_min_value_nonnegative'),
        sa.CheckConstraint('max_value >= min_value', name='ck_character_skills_bounds_order'),
        sa.CheckConstraint('value >= min_value AND value <= max_value', name='ck_character_skills_value_within_bounds'),
        sa.CheckConstraint('multiplier >= 1', name='ck_character_skills_multiplier_positive'),
        sa.CheckConstraint('is_special OR stat IS NOT NULL', name='ck_character_skills_regular_requires_stat'),
        sa.ForeignKeyConstraint(['character_id'], ['characters.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_index(
        'uq_character_skills_character_id_title_lower',
        'character_skills',
        ['character_id', sa.literal_column('lower(title)')],
        unique=True,
    )
    op.create_index(
        'uq_character_skills_one_special_per_character',
        'character_skills',
        ['character_id'],
        unique=True,
        postgresql_where=sa.text('is_special IS TRUE'),
    )


def downgrade() -> None:
    op.drop_index('uq_character_skills_one_special_per_character', table_name='character_skills')
    op.drop_index('uq_character_skills_character_id_title_lower', table_name='character_skills')
    op.drop_table('character_skills')
    skill_stat.drop(op.get_bind(), checkfirst=True)
