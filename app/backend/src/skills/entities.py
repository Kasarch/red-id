from dataclasses import dataclass
from enum import StrEnum
from uuid import UUID


class SkillStat(StrEnum):
    LUCK = 'luck'
    INTELLIGENCE = 'intelligence'
    REFLEXES = 'reflexes'
    DEXTERITY = 'dexterity'
    COOL = 'cool'
    EMPATHY = 'empathy'
    WILLPOWER = 'willpower'
    TECHNIC = 'technic'
    BODY = 'body'
    MOVEMENT = 'movement'


@dataclass(slots=True, kw_only=True)
class Skill:
    id: UUID
    character_id: UUID
    title: str
    description: str
    value: int
    min_value: int
    max_value: int
    multiplier: int
    stat: SkillStat | None
    is_special: bool

    def __post_init__(self) -> None:
        self.replace_editable_state(
            title=self.title,
            description=self.description,
            value=self.value,
            min_value=self.min_value,
            max_value=self.max_value,
            multiplier=self.multiplier,
            stat=self.stat,
            is_special=self.is_special,
        )

    def replace_editable_state(
        self,
        *,
        title: str,
        description: str,
        value: int,
        min_value: int,
        max_value: int,
        multiplier: int,
        stat: SkillStat | None,
        is_special: bool,
    ) -> None:
        normalized_title = title.strip()
        if not normalized_title:
            raise ValueError('Skill title cannot be empty or whitespace.')
        if min_value < 0:
            raise ValueError('Skill min_value cannot be negative.')
        if max_value < min_value:
            raise ValueError('Skill max_value cannot be less than min_value.')
        if value <= 0 or not min_value <= value <= max_value:
            raise ValueError('Skill value must be positive and within bounds.')
        if multiplier < 1:
            raise ValueError('Skill multiplier must be positive.')
        if not is_special and stat is None:
            raise ValueError('A regular skill must reference a character stat.')
        self.title = normalized_title
        self.description = description
        self.value = value
        self.min_value = min_value
        self.max_value = max_value
        self.multiplier = multiplier
        self.stat = stat
        self.is_special = is_special
