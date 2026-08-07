from collections.abc import Callable
from uuid import uuid4

import pytest

from skills.entities import Skill, SkillStat


def _skill(
    *,
    title: str = '  Handgun  ',
    value: int = 4,
    min_value: int = 0,
    max_value: int = 10,
    multiplier: int = 1,
    stat: SkillStat | None = SkillStat.REFLEXES,
    is_special: bool = False,
) -> Skill:
    return Skill(
        id=uuid4(),
        character_id=uuid4(),
        title=title,
        description='',
        value=value,
        min_value=min_value,
        max_value=max_value,
        multiplier=multiplier,
        stat=stat,
        is_special=is_special,
    )


def test_skill_trims_title_and_preserves_case() -> None:
    assert _skill().title == 'Handgun'


@pytest.mark.parametrize(
    'factory',
    [
        lambda: _skill(title='  '),
        lambda: _skill(value=0),
        lambda: _skill(value=-1),
        lambda: _skill(min_value=-1),
        lambda: _skill(min_value=5, max_value=4),
        lambda: _skill(value=11),
        lambda: _skill(multiplier=0),
        lambda: _skill(stat=None),
    ],
)
def test_skill_rejects_invalid_state(factory: Callable[[], Skill]) -> None:
    with pytest.raises(ValueError):
        factory()


def test_special_skill_accepts_optional_stat() -> None:
    assert _skill(is_special=True, stat=None).stat is None
    assert _skill(is_special=True, stat=SkillStat.COOL).stat is SkillStat.COOL
