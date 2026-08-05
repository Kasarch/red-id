from typing import Literal

from pydantic import AnyHttpUrl, BaseModel, Field


class OAuthLoginResponse(BaseModel):
    authorization_url: AnyHttpUrl


class OAuthCallback(BaseModel):
    code: str | None = None
    state: str | None = None
    error: str | None = None


class OAuthProfile(BaseModel):
    provider: str
    provider_user_id: str = Field(min_length=1)
    avatar_url: AnyHttpUrl | None


class TokenPair(BaseModel):
    access_token: str
    refresh_token: str
    token_type: Literal['bearer'] = 'bearer'


class RefreshRequest(BaseModel):
    refresh_token: str
