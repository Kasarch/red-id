from typing import Annotated, Self
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

PostgresInteger = Annotated[int, Field(strict=True, ge=-(2**31), le=2**31 - 1)]
NonNegativePostgresInteger = Annotated[int, Field(strict=True, ge=0, le=2**31 - 1)]


class CharacterRequest(BaseModel):
    model_config = ConfigDict(extra='forbid')


class BoundedStatRequest(CharacterRequest):
    current: PostgresInteger
    min_value: PostgresInteger
    max_value: PostgresInteger

    @model_validator(mode='after')
    def validate_bounds(self) -> Self:
        if self.min_value > self.max_value:
            raise ValueError('min_value cannot be greater than max_value')
        if not self.min_value <= self.current <= self.max_value:
            raise ValueError('current must be between min_value and max_value')
        return self


class HPValueRequest(CharacterRequest):
    current: NonNegativePostgresInteger
    max_value: NonNegativePostgresInteger

    @model_validator(mode='after')
    def validate_bounds(self) -> Self:
        if self.current > self.max_value:
            raise ValueError('current cannot be greater than max_value')
        return self


class ArmorValueRequest(CharacterRequest):
    base_value: NonNegativePostgresInteger
    penalty: NonNegativePostgresInteger


class CharacterTitleRequest(CharacterRequest):
    title: str

    @field_validator('title')
    @classmethod
    def normalize_title(cls, title: str) -> str:
        normalized_title = title.strip()
        if not normalized_title:
            raise ValueError('title cannot be empty or whitespace')
        return normalized_title


class CharacterUpdateRequest(CharacterTitleRequest):
    role: str
    wallet: PostgresInteger
    luck: BoundedStatRequest
    intelligence: BoundedStatRequest
    reflexes: BoundedStatRequest
    dexterity: BoundedStatRequest
    cool: BoundedStatRequest
    empathy: BoundedStatRequest
    willpower: BoundedStatRequest
    technic: BoundedStatRequest
    body: BoundedStatRequest
    movement: BoundedStatRequest
    armor_head: ArmorValueRequest
    armor_body: ArmorValueRequest
    armor_shield: ArmorValueRequest
    hp: HPValueRequest
    heavy_wounds_threshold: NonNegativePostgresInteger
    reputation: NonNegativePostgresInteger
    humanity: NonNegativePostgresInteger
    upgrade_points: NonNegativePostgresInteger


class CharacterCreateRequest(CharacterUpdateRequest):
    pass


class CharacterPartialUpdateRequest(CharacterRequest):
    title: str | None = None
    role: str | None = None
    wallet: PostgresInteger | None = None
    luck: BoundedStatRequest | None = None
    intelligence: BoundedStatRequest | None = None
    reflexes: BoundedStatRequest | None = None
    dexterity: BoundedStatRequest | None = None
    cool: BoundedStatRequest | None = None
    empathy: BoundedStatRequest | None = None
    willpower: BoundedStatRequest | None = None
    technic: BoundedStatRequest | None = None
    body: BoundedStatRequest | None = None
    movement: BoundedStatRequest | None = None
    armor_head: ArmorValueRequest | None = None
    armor_body: ArmorValueRequest | None = None
    armor_shield: ArmorValueRequest | None = None
    hp: HPValueRequest | None = None
    heavy_wounds_threshold: NonNegativePostgresInteger | None = None
    reputation: NonNegativePostgresInteger | None = None
    humanity: NonNegativePostgresInteger | None = None
    upgrade_points: NonNegativePostgresInteger | None = None

    @field_validator('*', mode='before')
    @classmethod
    def reject_null(cls, value: object) -> object:
        if value is None:
            raise ValueError('null is not allowed')
        return value

    @field_validator('title')
    @classmethod
    def normalize_title(cls, title: str) -> str:
        normalized_title = title.strip()
        if not normalized_title:
            raise ValueError('title cannot be empty or whitespace')
        return normalized_title

    @model_validator(mode='after')
    def reject_empty_request(self) -> Self:
        if not self.model_fields_set:
            raise ValueError('at least one field must be provided')
        return self


class CharacterResponse(CharacterCreateRequest):
    id: UUID
