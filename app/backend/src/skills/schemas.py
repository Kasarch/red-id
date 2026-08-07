from typing import Annotated, Self
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

from characters.entities import CharacterStatName
from skills.entities import SkillValueOutsideBoundsError

PgInt = Annotated[int, Field(strict=True, ge=-(2**31), le=2**31 - 1)]


class SkillBaseRequest(BaseModel):
    model_config = ConfigDict(extra='forbid')

    title: str
    description: str
    value: PgInt
    min_value: PgInt
    max_value: PgInt
    multiplier: PgInt
    stat: CharacterStatName | None
    is_special: bool


class SkillCreateRequest(SkillBaseRequest):
    @model_validator(mode='after')
    def reject_zero_value(self) -> Self:
        if self.value == 0:
            raise SkillValueOutsideBoundsError
        return self


class SkillUpdateRequest(SkillBaseRequest):
    pass


class SkillPartialUpdateRequest(BaseModel):
    model_config = ConfigDict(extra='forbid')

    title: str | None = None
    description: str | None = None
    value: PgInt | None = None
    min_value: PgInt | None = None
    max_value: PgInt | None = None
    multiplier: PgInt | None = None
    stat: CharacterStatName | None = None
    is_special: bool | None = None

    @field_validator(
        'title', 'description', 'value', 'min_value', 'max_value', 'multiplier', 'is_special', mode='before'
    )
    @classmethod
    def reject_null_except_stat(cls, value: object) -> object:
        if value is None:
            raise ValueError('null is not allowed')
        return value

    @model_validator(mode='after')
    def validate_partial_request(self) -> Self:
        if not self.model_fields_set:
            raise ValueError('at least one field must be provided')
        return self


class SkillResponse(SkillBaseRequest):
    id: UUID
    character_id: UUID
