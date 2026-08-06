import pytest
from httpx import ASGITransport, AsyncClient

from auth.dependencies import get_auth_service, get_refresh_service
from auth.jwt import TokenValidationError
from auth.providers import OAuthProviderError
from auth.schemas import TokenPair
from auth.service import AuthService, RefreshService
from main import app


class StubAuthService(AuthService):
    def __init__(self) -> None:
        self.error: TokenValidationError | OAuthProviderError | None = None
        self.received_code: str | None = None
        self.received_state: str | None = None

    def authorization_url(self) -> str:
        return 'https://oauth.example/authorize?state=signed-state'

    async def authenticate(self, code: str, state: str) -> TokenPair:
        self.received_code = code
        self.received_state = state
        if self.error is not None:
            raise self.error
        return TokenPair(access_token='application-access', refresh_token='application-refresh')


class StubRefreshService(RefreshService):
    def __init__(self) -> None:
        self.error: TokenValidationError | None = None
        self.received_token: str | None = None

    async def refresh(self, refresh_token: str) -> TokenPair:
        self.received_token = refresh_token
        if self.error is not None:
            raise self.error
        return TokenPair(access_token='new-access', refresh_token='new-refresh')


@pytest.mark.anyio
async def test_oauth_login_returns_authorization_url_without_cookies() -> None:
    service = StubAuthService()
    app.dependency_overrides[get_auth_service] = lambda: service
    try:
        async with AsyncClient(transport=ASGITransport(app=app), base_url='http://test') as client:
            response = await client.get('/api/v1/auth/oauth/yandex/login')
    finally:
        app.dependency_overrides.pop(get_auth_service, None)

    assert response.status_code == 200
    assert response.json() == {'authorization_url': 'https://oauth.example/authorize?state=signed-state'}
    assert 'state=' in response.json()['authorization_url']
    assert not response.cookies


@pytest.mark.anyio
@pytest.mark.parametrize(
    ('error', 'status_code', 'detail'),
    [
        (TokenValidationError(), 400, 'Invalid or expired OAuth state'),
        (OAuthProviderError(), 502, 'OAuth provider is unavailable'),
    ],
)
async def test_oauth_callback_maps_errors_safely(
    error: TokenValidationError | OAuthProviderError,
    status_code: int,
    detail: str,
) -> None:
    service = StubAuthService()
    service.error = error
    app.dependency_overrides[get_auth_service] = lambda: service
    try:
        async with AsyncClient(transport=ASGITransport(app=app), base_url='http://test') as client:
            response = await client.get('/api/v1/auth/oauth/yandex/callback?code=secret-code&state=signed-state')
    finally:
        app.dependency_overrides.pop(get_auth_service, None)

    assert response.status_code == status_code
    assert response.json() == {'detail': detail}
    assert 'secret-code' not in response.text


@pytest.mark.anyio
@pytest.mark.parametrize(
    'query',
    ['', '?code=code', '?state=state', '?error=access_denied'],
)
async def test_oauth_callback_rejects_incomplete_or_denied_callback(query: str) -> None:
    service = StubAuthService()
    app.dependency_overrides[get_auth_service] = lambda: service
    try:
        async with AsyncClient(transport=ASGITransport(app=app), base_url='http://test') as client:
            response = await client.get(f'/api/v1/auth/oauth/yandex/callback{query}')
    finally:
        app.dependency_overrides.pop(get_auth_service, None)

    assert response.status_code == 400
    assert service.received_code is None


@pytest.mark.anyio
async def test_refresh_endpoint_uses_json_body_and_returns_no_cookie() -> None:
    service = StubRefreshService()
    app.dependency_overrides[get_refresh_service] = lambda: service
    try:
        async with AsyncClient(transport=ASGITransport(app=app), base_url='http://test') as client:
            response = await client.post('/api/v1/auth/refresh', json={'refresh_token': 'body-refresh'})
            bearer_only = await client.post('/api/v1/auth/refresh', headers={'Authorization': 'Bearer body-refresh'})
    finally:
        app.dependency_overrides.pop(get_refresh_service, None)

    assert response.status_code == 200
    assert response.json() == {'access_token': 'new-access', 'refresh_token': 'new-refresh', 'token_type': 'bearer'}
    assert service.received_token == 'body-refresh'
    assert not response.cookies
    assert bearer_only.status_code == 422


@pytest.mark.anyio
async def test_refresh_endpoint_maps_invalid_token() -> None:
    service = StubRefreshService()
    service.error = TokenValidationError()
    app.dependency_overrides[get_refresh_service] = lambda: service
    try:
        async with AsyncClient(transport=ASGITransport(app=app), base_url='http://test') as client:
            response = await client.post('/api/v1/auth/refresh', json={'refresh_token': 'invalid-secret-token'})
    finally:
        app.dependency_overrides.pop(get_refresh_service, None)

    assert response.status_code == 401
    assert response.json() == {'detail': 'Invalid refresh token'}
    assert response.headers['www-authenticate'] == 'Bearer'
    assert 'invalid-secret-token' not in response.text
