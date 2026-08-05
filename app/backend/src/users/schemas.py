from datetime import datetime
from uuid import UUID

from pydantic import AnyHttpUrl, BaseModel, ConfigDict


class UserResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    avatar_url: AnyHttpUrl | None
    created_at: datetime
    updated_at: datetime


class UserUpdate(BaseModel):
    model_config = ConfigDict(extra='forbid')

    avatar_url: AnyHttpUrl | None
