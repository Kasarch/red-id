from uuid import uuid4

import pytest

from database import async_session_factory
from users.repository import UserRepository


@pytest.mark.anyio
async def test_add_user_before_oauth_account() -> None:
    async with async_session_factory() as session:
        repository = UserRepository(session)
        user = await repository.add_with_oauth_identity(
            provider='test',
            provider_user_id=str(uuid4()),
            avatar_url=None,
        )

        await session.flush()

        assert user.id is not None
        await session.rollback()
