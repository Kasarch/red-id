from uuid import UUID, uuid4

from sqlalchemy import Boolean, CheckConstraint, Enum, ForeignKey, Index, String, func, true
from sqlalchemy.orm import Mapped, mapped_column

from characters.entities import CharacterStatName
from database import Base


class SkillModel(Base):
    __tablename__ = 'character_skills'

    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    character_id: Mapped[UUID] = mapped_column(ForeignKey('characters.id', ondelete='CASCADE'))
    title: Mapped[str] = mapped_column(String(), nullable=False)
    description: Mapped[str] = mapped_column(String(), nullable=False, default='')
    value: Mapped[int] = mapped_column(nullable=False)
    min_value: Mapped[int] = mapped_column(nullable=False)
    max_value: Mapped[int] = mapped_column(nullable=False)
    multiplier: Mapped[int] = mapped_column(nullable=False)
    stat: Mapped[CharacterStatName | None] = mapped_column(
        Enum(CharacterStatName, name='skill_stat', values_callable=lambda enum: [item.value for item in enum]),
        nullable=True,
    )
    is_special: Mapped[bool] = mapped_column(Boolean(), nullable=False, default=False)

    __table_args__ = (
        CheckConstraint('value > 0', name='ck_character_skills_value_positive'),
        CheckConstraint('min_value >= 0', name='ck_character_skills_min_value_nonnegative'),
        CheckConstraint('max_value >= min_value', name='ck_character_skills_bounds_order'),
        CheckConstraint(
            'value >= min_value AND value <= max_value',
            name='ck_character_skills_value_within_bounds',
        ),
        CheckConstraint('multiplier >= 1', name='ck_character_skills_multiplier_positive'),
        CheckConstraint('is_special OR stat IS NOT NULL', name='ck_character_skills_regular_requires_stat'),
        Index('uq_character_skills_character_id_title_lower', 'character_id', func.lower(title), unique=True),
        Index(
            'uq_character_skills_one_special_per_character',
            'character_id',
            unique=True,
            postgresql_where=is_special.is_(true()),
        ),
    )
