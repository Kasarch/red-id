from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Query, status

from auth.dependencies import get_auth_service, get_refresh_service
from auth.jwt import TokenValidationError
from auth.providers import OAuthProviderError
from auth.schemas import (
    OAuthCallback,
    OAuthLoginResponse,
    RefreshRequest,
    TokenPair,
)
from auth.service import AuthService, RefreshService, UserNotFoundError

router = APIRouter(prefix='/auth', tags=['auth'])
AuthServiceDependency = Annotated[AuthService, Depends(get_auth_service)]
RefreshServiceDependency = Annotated[RefreshService, Depends(get_refresh_service)]


@router.get('/oauth/yandex/login', response_model=OAuthLoginResponse)
def yandex_login(service: AuthServiceDependency) -> OAuthLoginResponse:
    return OAuthLoginResponse(authorization_url=service.authorization_url())


@router.get(
    '/oauth/yandex/callback',
    response_model=TokenPair,
    responses={
        400: {'description': 'Invalid callback'},
        502: {'description': 'OAuth provider error'},
    },
)
async def yandex_callback(callback: Annotated[OAuthCallback, Query()], service: AuthServiceDependency) -> TokenPair:
    if callback.error is not None:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail='OAuth authorization was denied',
        )
    if not callback.code or not callback.state:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail='OAuth callback is incomplete',
        )
    try:
        return await service.authenticate(callback.code, callback.state)
    except TokenValidationError as error:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail='Invalid or expired OAuth state',
        ) from error
    except OAuthProviderError as error:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail='OAuth provider is unavailable',
        ) from error


@router.post(
    '/refresh',
    response_model=TokenPair,
    responses={401: {'description': 'Invalid refresh token'}},
)
async def refresh_tokens(request: RefreshRequest, service: RefreshServiceDependency) -> TokenPair:
    try:
        return await service.refresh(request.refresh_token)
    except (TokenValidationError, UserNotFoundError) as error:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail='Invalid refresh token',
            headers={'WWW-Authenticate': 'Bearer'},
        ) from error
