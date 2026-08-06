"""add character invariant constraints

Revision ID: 20260807_01
Revises: 24952763d13d
Create Date: 2026-08-07
"""

from collections.abc import Sequence

from alembic import op

revision: str = '20260807_01'
down_revision: str | Sequence[str] | None = '24952763d13d'
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

_CONSTRAINTS = (
    ('ck_characters_heavy_wounds_threshold_nonnegative', '0 <= heavy_wounds_threshold'),
    ('ck_characters_heavy_wounds_threshold_lte_hp_max', 'heavy_wounds_threshold <= hp_max'),
    ('ck_characters_reputation_nonnegative', '0 <= reputation'),
    ('ck_characters_humanity_nonnegative', '0 <= humanity'),
)


def upgrade() -> None:
    # NOT VALID avoids silently rewriting existing rows. VALIDATE then fails the
    # migration transaction if legacy data violates a domain invariant.
    for name, expression in _CONSTRAINTS:
        op.execute(f'ALTER TABLE characters ADD CONSTRAINT {name} CHECK ({expression}) NOT VALID')
        op.execute(f'ALTER TABLE characters VALIDATE CONSTRAINT {name}')


def downgrade() -> None:
    for name, _ in reversed(_CONSTRAINTS):
        op.drop_constraint(name, 'characters', type_='check')
