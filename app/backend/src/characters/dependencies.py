from collections.abc import AsyncIterator

from auth.dependencies import SessionDependency
from characters.repository import CharacterRepository
from characters.service import CharacterService


async def get_character_service(
    session: SessionDependency,
) -> AsyncIterator[CharacterService]:
    repository = CharacterRepository(session)
    yield CharacterService(session, repository)
