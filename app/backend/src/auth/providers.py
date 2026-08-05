from typing import Protocol
from urllib.parse import urlencode

import httpx
from pydantic import BaseModel, Field, ValidationError

from auth.schemas import OAuthProfile
from config import YandexOAuthSettings


class OAuthProviderError(Exception):
    pass


class OAuthProvider(Protocol):
    @property
    def code(self) -> str: ...

    def build_authorization_url(self, state: str) -> str: ...

    async def exchange_code(self, code: str) -> str: ...

    async def get_profile(self, access_token: str) -> OAuthProfile: ...


class YandexTokenResponse(BaseModel):
    access_token: str


class YandexUserInfo(BaseModel):
    id: str = Field(min_length=1)
    default_avatar_id: str | None = None
    is_avatar_empty: bool = True


class YandexOAuthProvider:
    code = 'yandex'

    def __init__(self, config: YandexOAuthSettings, client: httpx.AsyncClient) -> None:
        self._config = config
        self._client = client

    def build_authorization_url(self, state: str) -> str:
        query = urlencode(
            {
                'response_type': 'code',
                'client_id': self._config.client_id,
                'redirect_uri': str(self._config.redirect_uri),
                'state': state,
            }
        )
        return f'{self._config.authorize_url}?{query}'

    async def exchange_code(self, code: str) -> str:
        try:
            response = await self._client.post(
                str(self._config.token_url),
                data={
                    'grant_type': 'authorization_code',
                    'code': code,
                    'client_id': self._config.client_id,
                    'client_secret': self._config.client_secret.get_secret_value(),
                    'redirect_uri': str(self._config.redirect_uri),
                },
            )
            response.raise_for_status()
            token = YandexTokenResponse.model_validate(response.json())
        except (httpx.HTTPError, ValueError, ValidationError) as error:
            raise OAuthProviderError from error
        return token.access_token

    async def get_profile(self, access_token: str) -> OAuthProfile:
        try:
            response = await self._client.get(
                str(self._config.user_info_url),
                params={'format': 'json'},
                headers={'Authorization': f'OAuth {access_token}'},
            )
            response.raise_for_status()
            user_info = YandexUserInfo.model_validate(response.json())
        except (httpx.HTTPError, ValueError, ValidationError) as error:
            raise OAuthProviderError from error

        avatar_url = None
        if not user_info.is_avatar_empty and user_info.default_avatar_id:
            avatar_url = f'https://avatars.yandex.net/get-yapic/{user_info.default_avatar_id}/islands-200'
        return OAuthProfile(
            provider=self.code,
            provider_user_id=user_info.id,
            avatar_url=avatar_url,
        )
