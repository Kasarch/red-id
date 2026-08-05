from sqlalchemy.ext.asyncio import AsyncSession

from users.models import User
from users.repository import UserRepository


class UserService:
    def __init__(self, session: AsyncSession, repository: UserRepository) -> None:
        self._session = session
        self._repository = repository

    async def update_avatar(self, user: User, avatar_url: str | None) -> User:
        updated_user = await self._repository.update_avatar(user, avatar_url)
        await self._session.commit()
        return updated_user
