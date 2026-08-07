from typing import Annotated, Self
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

from skills.entities import SkillStat

PgInt = Annotated[int, Field(strict=True, ge=-(2**31), le=2**31 - 1)]


class SkillBaseRequest(BaseModel):
    model_config = ConfigDict(extra='forbid')

    title: str
    description: str
    value: PgInt
    min_value: PgInt
    max_value: PgInt
    multiplier: PgInt
    stat: SkillStat | None
    is_special: bool

    @field_validator('title')
    @classmethod
    def trim_title(cls, value: str) -> str:
        value = value.strip()
        if not value:
            raise ValueError('title cannot be empty or whitespace')
        return value

    @model_validator(mode='after')
    def validate_invariants(self) -> Self:
        if self.min_value < 0:
            raise ValueError('min_value cannot be negative')
        if self.max_value < self.min_value:
            raise ValueError('max_value cannot be less than min_value')
        if self.value < 0 or not self.min_value <= self.value <= self.max_value:
            raise ValueError('value must be between min_value and max_value')
        if self.multiplier < 1:
            raise ValueError('multiplier must be positive')
        if not self.is_special and self.stat is None:
            raise ValueError('regular skills require stat')
        return self


class SkillCreateRequest(SkillBaseRequest):
    @model_validator(mode='after')
    def reject_zero_value(self) -> Self:
        if self.value == 0:
            raise ValueError('value must be positive when creating a skill')
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
    stat: SkillStat | None = None
    is_special: bool | None = None

    @field_validator('title')
    @classmethod
    def trim_title(cls, value: str) -> str:
        value = value.strip()
        if not value:
            raise ValueError('title cannot be empty or whitespace')
        return value

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
        if self.value is not None and self.value < 0:
            raise ValueError('value cannot be negative')
        if self.min_value is not None and self.min_value < 0:
            raise ValueError('min_value cannot be negative')
        if self.multiplier is not None and self.multiplier < 1:
            raise ValueError('multiplier must be positive')
        return self


class SkillResponse(SkillBaseRequest):
    id: UUID
    character_id: UUID
