from collections.abc import AsyncIterator
from typing import Annotated

import httpx
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy.ext.asyncio import AsyncSession

from auth.jwt import JWTService, TokenType, TokenValidationError
from auth.providers import YandexOAuthProvider
from auth.service import AuthService, RefreshService
from config import settings
from database import get_session
from users.models import User
from users.repository import UserRepository

bearer = HTTPBearer(auto_error=False)
SessionDependency = Annotated[AsyncSession, Depends(get_session)]


def get_jwt_service() -> JWTService:
    return JWTService(settings.auth)


async def get_auth_service(
    session: SessionDependency,
) -> AsyncIterator[AuthService]:
    async with httpx.AsyncClient(timeout=settings.yandex_oauth.http_timeout_seconds) as client:
        repository = UserRepository(session)
        provider = YandexOAuthProvider(settings.yandex_oauth, client)
        yield AuthService(session, repository, provider, get_jwt_service())


def get_refresh_service(session: SessionDependency) -> RefreshService:
    return RefreshService(UserRepository(session), get_jwt_service())


async def get_current_user(
    session: SessionDependency,
    credentials: Annotated[HTTPAuthorizationCredentials | None, Depends(bearer)],
) -> User:
    unauthorized = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail='Authentication required',
        headers={'WWW-Authenticate': 'Bearer'},
    )
    if credentials is None or credentials.scheme.lower() != 'bearer':
        raise unauthorized
    try:
        user_id = get_jwt_service().decode_user_token(credentials.credentials, TokenType.ACCESS)
    except TokenValidationError as error:
        raise unauthorized from error
    user = await UserRepository(session).get_by_id(user_id)
    if user is None:
        raise unauthorized
    return user


CurrentUser = Annotated[User, Depends(get_current_user)]
