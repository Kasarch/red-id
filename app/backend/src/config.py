from functools import lru_cache
from typing import Annotated, Literal

from pydantic import AnyHttpUrl, Field, PostgresDsn, SecretStr
from pydantic_settings import BaseSettings, SettingsConfigDict


class AuthSettings(BaseSettings):
    jwt_secret: Annotated[SecretStr, Field(min_length=32)]
    jwt_algorithm: Literal['HS256', 'HS384', 'HS512'] = 'HS256'
    access_token_ttl_minutes: Annotated[int, Field(gt=0)] = 15
    refresh_token_ttl_days: Annotated[int, Field(gt=0)] = 30
    state_secret: Annotated[SecretStr, Field(min_length=32)]
    state_ttl_minutes: Annotated[int, Field(gt=0)] = 10


class YandexOAuthSettings(BaseSettings):
    client_id: str
    client_secret: SecretStr
    redirect_uri: AnyHttpUrl
    authorize_url: AnyHttpUrl = AnyHttpUrl('https://oauth.yandex.ru/authorize')
    token_url: AnyHttpUrl = AnyHttpUrl('https://oauth.yandex.ru/token')
    user_info_url: AnyHttpUrl = AnyHttpUrl('https://login.yandex.ru/info')
    http_timeout_seconds: Annotated[float, Field(gt=0)] = 10


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file='.env',
        env_file_encoding='utf-8',
        env_nested_delimiter='__',
        extra='ignore',
    )

    database_url: PostgresDsn
    auth: AuthSettings
    yandex_oauth: YandexOAuthSettings


@lru_cache
def get_settings() -> Settings:
    return Settings()


settings = get_settings()
