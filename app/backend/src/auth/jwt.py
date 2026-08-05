from datetime import UTC, datetime, timedelta
from enum import StrEnum
from secrets import token_urlsafe
from uuid import UUID

import jwt
from jwt import InvalidTokenError
from pydantic import BaseModel, ValidationError

from config import AuthSettings


class TokenType(StrEnum):
    ACCESS = 'access'
    REFRESH = 'refresh'
    STATE = 'oauth_state'


class TokenValidationError(Exception):
    pass


class TokenClaims(BaseModel):
    sub: str
    iat: datetime
    exp: datetime
    token_type: TokenType


class StateClaims(BaseModel):
    nonce: str
    iat: datetime
    exp: datetime
    token_type: TokenType


class JWTService:
    def __init__(self, config: AuthSettings) -> None:
        self._secret = config.jwt_secret.get_secret_value()
        self._state_secret = config.state_secret.get_secret_value()
        self._algorithm = config.jwt_algorithm
        self._access_ttl = timedelta(minutes=config.access_token_ttl_minutes)
        self._refresh_ttl = timedelta(days=config.refresh_token_ttl_days)
        self._state_ttl = timedelta(minutes=config.state_ttl_minutes)

    def create_token_pair(self, user_id: UUID) -> tuple[str, str]:
        return (
            self._encode_user_token(user_id, TokenType.ACCESS, self._access_ttl),
            self._encode_user_token(user_id, TokenType.REFRESH, self._refresh_ttl),
        )

    def decode_user_token(self, token: str, expected_type: TokenType) -> UUID:
        try:
            payload = jwt.decode(
                token,
                self._secret,
                algorithms=[self._algorithm],
                options={'require': ['sub', 'iat', 'exp', 'token_type']},
            )
            claims = TokenClaims.model_validate(payload)
            user_id = UUID(claims.sub)
        except (InvalidTokenError, ValidationError, ValueError) as error:
            raise TokenValidationError from error
        if claims.token_type is not expected_type:
            raise TokenValidationError
        return user_id

    def create_state(self) -> str:
        now = datetime.now(UTC)
        return jwt.encode(
            {
                'nonce': token_urlsafe(32),
                'iat': now,
                'exp': now + self._state_ttl,
                'token_type': TokenType.STATE,
            },
            self._state_secret,
            algorithm=self._algorithm,
        )

    def validate_state(self, state: str) -> None:
        try:
            payload = jwt.decode(
                state,
                self._state_secret,
                algorithms=[self._algorithm],
                options={'require': ['nonce', 'iat', 'exp', 'token_type']},
            )
            claims = StateClaims.model_validate(payload)
        except (InvalidTokenError, ValidationError) as error:
            raise TokenValidationError from error
        if claims.token_type is not TokenType.STATE or not claims.nonce:
            raise TokenValidationError

    def _encode_user_token(self, user_id: UUID, token_type: TokenType, ttl: timedelta) -> str:
        now = datetime.now(UTC)
        return jwt.encode(
            {
                'sub': str(user_id),
                'iat': now,
                'exp': now + ttl,
                'token_type': token_type,
            },
            self._secret,
            algorithm=self._algorithm,
        )
