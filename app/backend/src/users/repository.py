from uuid import UUID, uuid4

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from users.models import OAuthAccount, User


class UserRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def get_by_id(self, user_id: UUID) -> User | None:
        return await self._session.get(User, user_id)

    async def get_by_oauth_identity(self, provider: str, provider_user_id: str) -> User | None:
        statement = (
            select(User)
            .join(OAuthAccount, OAuthAccount.user_id == User.id)
            .where(
                OAuthAccount.provider == provider,
                OAuthAccount.provider_user_id == provider_user_id,
            )
        )
        result = await self._session.execute(statement)
        return result.scalar_one_or_none()

    async def add_with_oauth_identity(
        self,
        provider: str,
        provider_user_id: str,
        avatar_url: str | None,
    ) -> User:
        user_id = uuid4()
        user = User(id=user_id, avatar_url=avatar_url)
        self._session.add(user)
        await self._session.flush()

        account = OAuthAccount(
            user_id=user_id,
            provider=provider,
            provider_user_id=provider_user_id,
        )
        self._session.add(account)
        return user

    async def update_avatar(self, user: User, avatar_url: str | None) -> User:
        user.avatar_url = avatar_url
        await self._session.flush()
        await self._session.refresh(user)
        return user
