from datetime import UTC, datetime, timedelta
from uuid import uuid4

import jwt
import pytest

from auth.jwt import JWTService, TokenType, TokenValidationError
from config import AuthSettings


def test_access_and_refresh_tokens_round_trip(auth_settings: AuthSettings) -> None:
    service = JWTService(auth_settings)
    user_id = uuid4()

    access_token, refresh_token = service.create_token_pair(user_id)

    assert service.decode_user_token(access_token, TokenType.ACCESS) == user_id
    assert service.decode_user_token(refresh_token, TokenType.REFRESH) == user_id


def test_user_token_types_cannot_be_swapped(auth_settings: AuthSettings) -> None:
    service = JWTService(auth_settings)
    access_token, refresh_token = service.create_token_pair(uuid4())

    with pytest.raises(TokenValidationError):
        service.decode_user_token(refresh_token, TokenType.ACCESS)
    with pytest.raises(TokenValidationError):
        service.decode_user_token(access_token, TokenType.REFRESH)


@pytest.mark.parametrize(
    'secret', ['wrong-signing-secret-with-at-least-32-chars', 'another-wrong-secret-with-32-chars']
)
def test_user_token_rejects_wrong_signature(auth_settings: AuthSettings, secret: str) -> None:
    now = datetime.now(UTC)
    token = jwt.encode(
        {
            'sub': str(uuid4()),
            'jti': str(uuid4()),
            'iat': now,
            'exp': now + timedelta(minutes=5),
            'token_type': 'access',
        },
        secret,
        algorithm='HS256',
    )

    with pytest.raises(TokenValidationError):
        JWTService(auth_settings).decode_user_token(token, TokenType.ACCESS)


def test_user_token_rejects_expired_token(auth_settings: AuthSettings) -> None:
    now = datetime.now(UTC)
    token = jwt.encode(
        {
            'sub': str(uuid4()),
            'jti': str(uuid4()),
            'iat': now - timedelta(minutes=10),
            'exp': now - timedelta(minutes=5),
            'token_type': 'access',
        },
        auth_settings.jwt_secret.get_secret_value(),
        algorithm='HS256',
    )

    with pytest.raises(TokenValidationError):
        JWTService(auth_settings).decode_user_token(token, TokenType.ACCESS)


def test_user_token_rejects_disallowed_algorithm(auth_settings: AuthSettings) -> None:
    now = datetime.now(UTC)
    token = jwt.encode(
        {
            'sub': str(uuid4()),
            'jti': str(uuid4()),
            'iat': now,
            'exp': now + timedelta(minutes=5),
            'token_type': 'access',
        },
        auth_settings.jwt_secret.get_secret_value(),
        algorithm='HS384',
    )

    with pytest.raises(TokenValidationError):
        JWTService(auth_settings).decode_user_token(token, TokenType.ACCESS)


def test_oauth_state_round_trip(auth_settings: AuthSettings) -> None:
    service = JWTService(auth_settings)

    service.validate_state(service.create_state())


def test_oauth_state_and_user_tokens_cannot_be_swapped(auth_settings: AuthSettings) -> None:
    service = JWTService(auth_settings)
    access_token, refresh_token = service.create_token_pair(uuid4())
    state = service.create_state()

    with pytest.raises(TokenValidationError):
        service.validate_state(access_token)
    with pytest.raises(TokenValidationError):
        service.validate_state(refresh_token)
    with pytest.raises(TokenValidationError):
        service.decode_user_token(state, TokenType.ACCESS)
    with pytest.raises(TokenValidationError):
        service.decode_user_token(state, TokenType.REFRESH)


def test_user_token_requires_jti_and_rejects_future_iat(auth_settings: AuthSettings) -> None:
    now = datetime.now(UTC)
    payload = {
        'sub': str(uuid4()),
        'iat': now + timedelta(minutes=5),
        'exp': now + timedelta(minutes=10),
        'token_type': 'access',
    }
    token_without_jti = jwt.encode(payload, auth_settings.jwt_secret.get_secret_value(), algorithm='HS256')
    payload['jti'] = str(uuid4())
    token_with_future_iat = jwt.encode(payload, auth_settings.jwt_secret.get_secret_value(), algorithm='HS256')

    with pytest.raises(TokenValidationError):
        JWTService(auth_settings).decode_user_token(token_without_jti, TokenType.ACCESS)
    with pytest.raises(TokenValidationError):
        JWTService(auth_settings).decode_user_token(token_with_future_iat, TokenType.ACCESS)


@pytest.mark.parametrize(
    'payload',
    [
        {'token_type': 'oauth_state'},
        {'nonce': '', 'token_type': 'oauth_state'},
        {'nonce': 'nonce', 'token_type': 'access'},
    ],
)
def test_oauth_state_rejects_missing_or_invalid_claims(auth_settings: AuthSettings, payload: dict[str, str]) -> None:
    now = datetime.now(UTC)
    complete_payload: dict[str, str | datetime] = {
        **payload,
        'iat': now,
        'exp': now + timedelta(minutes=5),
    }
    token = jwt.encode(
        complete_payload,
        auth_settings.state_secret.get_secret_value(),
        algorithm='HS256',
    )

    with pytest.raises(TokenValidationError):
        JWTService(auth_settings).validate_state(token)
