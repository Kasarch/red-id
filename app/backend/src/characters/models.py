from datetime import datetime
from uuid import UUID, uuid4

from sqlalchemy import CheckConstraint, DateTime, ForeignKey, Index, func
from sqlalchemy.orm import Mapped, mapped_column

from database import Base


class CharacterModel(Base):
    __tablename__ = 'characters'

    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    owner_id: Mapped[UUID] = mapped_column(ForeignKey('users.id', ondelete='CASCADE'))
    title: Mapped[str] = mapped_column()
    role: Mapped[str]
    wallet: Mapped[int] = mapped_column(default=0)
    luck_current: Mapped[int]
    luck_min: Mapped[int]
    luck_max: Mapped[int]
    int_current: Mapped[int]
    int_min: Mapped[int]
    int_max: Mapped[int]
    ref_current: Mapped[int]
    ref_min: Mapped[int]
    ref_max: Mapped[int]
    dex_current: Mapped[int]
    dex_min: Mapped[int]
    dex_max: Mapped[int]
    cool_current: Mapped[int]
    cool_min: Mapped[int]
    cool_max: Mapped[int]
    emp_current: Mapped[int]
    emp_min: Mapped[int]
    emp_max: Mapped[int]
    will_current: Mapped[int]
    will_min: Mapped[int]
    will_max: Mapped[int]
    tech_current: Mapped[int]
    tech_min: Mapped[int]
    tech_max: Mapped[int]
    body_current: Mapped[int]
    body_min: Mapped[int]
    body_max: Mapped[int]
    move_current: Mapped[int]
    move_min: Mapped[int]
    move_max: Mapped[int]
    hp_current: Mapped[int]
    hp_max: Mapped[int]
    heavy_wounds_threshold: Mapped[int]
    reputation: Mapped[int] = mapped_column(default=0)
    humanity: Mapped[int]
    upgrade_points: Mapped[int] = mapped_column(default=0)
    armor_head: Mapped[int]
    armor_head_penalty: Mapped[int]
    armor_body: Mapped[int]
    armor_body_penalty: Mapped[int]
    armor_shield: Mapped[int]
    armor_shield_penalty: Mapped[int]

    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )

    __table_args__ = (
        Index(
            'uq_characters_owner_id_title_lower',
            'owner_id',
            func.lower(title),
            unique=True,
        ),
        CheckConstraint('luck_min <= luck_current AND luck_current <= luck_max', name='ck_luck_bounds'),
        CheckConstraint('int_min <= int_current AND int_current <= int_max', name='ck_int_bounds'),
        CheckConstraint('ref_min <= ref_current AND ref_current <= ref_max', name='ck_ref_bounds'),
        CheckConstraint('dex_min <= dex_current AND dex_current <= dex_max', name='ck_dex_bounds'),
        CheckConstraint('cool_min <= cool_current AND cool_current <= cool_max', name='ck_cool_bounds'),
        CheckConstraint('emp_min <= emp_current AND emp_current <= emp_max', name='ck_emp_bounds'),
        CheckConstraint('will_min <= will_current AND will_current <= will_max', name='ck_will_bounds'),
        CheckConstraint('tech_min <= tech_current AND tech_current <= tech_max', name='ck_tech_bounds'),
        CheckConstraint('body_min <= body_current AND body_current <= body_max', name='ck_body_bounds'),
        CheckConstraint('move_min <= move_current AND move_current <= move_max', name='ck_move_bounds'),
        CheckConstraint('0 <= hp_current AND hp_current <= hp_max', name='ck_hp_bounds'),
        CheckConstraint('0 <= upgrade_points', name='ck_upgrade_points_bounds'),
        CheckConstraint('0 <= armor_head', name='ck_armor_head_bounds'),
        CheckConstraint('0 <= armor_head_penalty', name='ck_armor_head_penalty_bounds'),
        CheckConstraint('0 <= armor_body', name='ck_armor_body_bounds'),
        CheckConstraint('0 <= armor_body_penalty', name='ck_armor_body_penalty_bounds'),
        CheckConstraint('0 <= armor_shield', name='ck_armor_shield_bounds'),
        CheckConstraint('0 <= armor_shield_penalty', name='ck_armor_shield_penalty_bounds'),
    )
