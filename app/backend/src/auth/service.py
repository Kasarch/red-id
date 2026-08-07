from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from auth.jwt import JWTService, TokenType
from auth.providers import OAuthProvider
from auth.schemas import OAuthProfile, TokenPair
from database_errors import postgresql_constraint_name
from users.models import User
from users.repository import UserRepository

OAUTH_IDENTITY_CONSTRAINT = 'uq_oauth_accounts_provider_identity'


class UserNotFoundError(Exception):
    pass


class RefreshService:
    def __init__(self, repository: UserRepository, jwt_service: JWTService) -> None:
        self._repository = repository
        self._jwt = jwt_service

    async def refresh(self, refresh_token: str) -> TokenPair:
        user_id = self._jwt.decode_user_token(refresh_token, TokenType.REFRESH)
        user = await self._repository.get_by_id(user_id)
        if user is None:
            raise UserNotFoundError
        return _tokens_for(user, self._jwt)


class AuthService:
    def __init__(
        self,
        session: AsyncSession,
        repository: UserRepository,
        provider: OAuthProvider,
        jwt_service: JWTService,
    ) -> None:
        self._session = session
        self._repository = repository
        self._provider = provider
        self._jwt = jwt_service

    def authorization_url(self) -> str:
        return self._provider.build_authorization_url(self._jwt.create_state())

    async def authenticate(self, code: str, state: str) -> TokenPair:
        self._jwt.validate_state(state)
        provider_token = await self._provider.exchange_code(code)
        profile = await self._provider.get_profile(provider_token)
        user = await self._find_or_create_user(profile)
        return _tokens_for(user, self._jwt)

    async def _find_or_create_user(self, profile: OAuthProfile) -> User:
        user = await self._repository.get_by_oauth_identity(profile.provider, profile.provider_user_id)
        if user is not None:
            avatar_url = str(profile.avatar_url) if profile.avatar_url else None
            if user.avatar_url != avatar_url:
                user.avatar_url = avatar_url
                await self._session.commit()
            return user

        avatar_url = str(profile.avatar_url) if profile.avatar_url else None
        user = await self._repository.add_with_oauth_identity(
            profile.provider,
            profile.provider_user_id,
            avatar_url,
        )
        try:
            await self._session.commit()
        except IntegrityError as error:
            await self._session.rollback()
            if not _is_oauth_identity_conflict(error):
                raise
            existing = await self._repository.get_by_oauth_identity(profile.provider, profile.provider_user_id)
            if existing is None:
                raise
            return existing
        await self._session.refresh(user)
        return user


def _is_oauth_identity_conflict(error: IntegrityError) -> bool:
    return postgresql_constraint_name(error, sqlstate='23505') == OAUTH_IDENTITY_CONSTRAINT


def _tokens_for(user: User, jwt_service: JWTService) -> TokenPair:
    access_token, refresh_token = jwt_service.create_token_pair(user.id)
    return TokenPair(access_token=access_token, refresh_token=refresh_token)
