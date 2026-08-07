from dataclasses import dataclass
from uuid import UUID

from characters.entities import CharacterStatName


class SkillValidationError(ValueError):
    code: str

    def __init__(self) -> None:
        super().__init__(self.code)


class EmptySkillTitleError(SkillValidationError):
    code = 'skill_title_empty'


class InvalidSkillBoundsError(SkillValidationError):
    code = 'skill_bounds_invalid'


class SkillValueOutsideBoundsError(SkillValidationError):
    code = 'skill_value_outside_bounds'


class InvalidSkillMultiplierError(SkillValidationError):
    code = 'skill_multiplier_not_positive'


class RegularSkillStatRequiredError(SkillValidationError):
    code = 'regular_skill_stat_required'


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
    stat: CharacterStatName | None
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
        stat: CharacterStatName | None,
        is_special: bool,
    ) -> None:
        normalized_title = title.strip()
        if not normalized_title:
            raise EmptySkillTitleError
        if min_value < 0 or max_value < min_value:
            raise InvalidSkillBoundsError
        if value <= 0 or not min_value <= value <= max_value:
            raise SkillValueOutsideBoundsError
        if multiplier < 1:
            raise InvalidSkillMultiplierError
        if not is_special and stat is None:
            raise RegularSkillStatRequiredError
        self.title = normalized_title
        self.description = description
        self.value = value
        self.min_value = min_value
        self.max_value = max_value
        self.multiplier = multiplier
        self.stat = stat
        self.is_special = is_special
