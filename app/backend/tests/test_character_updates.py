from uuid import UUID, uuid4

import pytest
from pydantic import ValidationError
from sqlalchemy.ext.asyncio import AsyncSession

from characters.entities import ArmorValue, BoundedStat, Character, HPValue
from characters.repository import CharacterRepository
from characters.schemas import CharacterPartialUpdateRequest
from characters.service import (
    CharacterNotFoundError,
    CharacterService,
    PartialUpdateCharacterData,
    UpdateCharacterData,
)


class MemoryCharacterRepository(CharacterRepository):
    def __init__(self, session: AsyncSession, character: Character | None) -> None:
        super().__init__(session)
        self.character = character
        self.saved = False

    async def get_by_id_and_owner(self, character_id: UUID, owner_id: UUID) -> Character | None:
        if self.character is None:
            return None
        if self.character.id != character_id or self.character.owner_id != owner_id:
            return None
        return self.character

    async def save(self, character: Character) -> bool:
        if self.character is None:
            return False
        self.character = character
        self.saved = True
        return True


def _stat(current: int = 5) -> BoundedStat:
    return BoundedStat(current=current, min_value=0, max_value=10)


def _character() -> Character:
    return Character(
        id=uuid4(),
        owner_id=uuid4(),
        title='solo',
        role='Solo',
        wallet=100,
        luck=_stat(),
        intelligence=_stat(),
        reflexes=_stat(),
        dexterity=_stat(),
        cool=_stat(),
        empathy=_stat(),
        willpower=_stat(),
        technic=_stat(),
        body=_stat(),
        movement=_stat(),
        armor_head=ArmorValue(base_value=7, penalty=0),
        armor_body=ArmorValue(base_value=11, penalty=1),
        armor_shield=ArmorValue(base_value=0, penalty=0),
        hp=HPValue(current=30, max_value=40),
        heavy_wounds_threshold=20,
        reputation=2,
        humanity=50,
        upgrade_points=3,
    )


def _update_data() -> UpdateCharacterData:
    return UpdateCharacterData(
        role='Netrunner',
        wallet=200,
        luck=_stat(6),
        intelligence=_stat(7),
        reflexes=_stat(8),
        dexterity=_stat(9),
        cool=_stat(4),
        empathy=_stat(3),
        willpower=_stat(6),
        technic=_stat(7),
        body=_stat(8),
        movement=_stat(9),
        armor_head=ArmorValue(base_value=8, penalty=1),
        armor_body=ArmorValue(base_value=12, penalty=2),
        armor_shield=ArmorValue(base_value=5, penalty=0),
        hp=HPValue(current=35, max_value=45),
        heavy_wounds_threshold=22,
        reputation=4,
        humanity=45,
        upgrade_points=8,
    )


@pytest.mark.anyio
async def test_full_update_replaces_all_editable_fields() -> None:
    character = _character()
    session = AsyncSession()
    repository = MemoryCharacterRepository(session, character)
    service = CharacterService(session, repository)

    updated = await service.update(character.id, character.owner_id, _update_data())

    assert updated.role == 'Netrunner'
    assert updated.wallet == 200
    assert updated.luck.current == 6
    assert updated.armor_body == ArmorValue(base_value=12, penalty=2)
    assert updated.hp == HPValue(current=35, max_value=45)
    assert updated.title == 'solo'
    assert repository.saved
    await session.close()


@pytest.mark.anyio
async def test_partial_update_replaces_values_and_preserves_others() -> None:
    character = _character()
    original_role = character.role
    session = AsyncSession()
    service = CharacterService(session, MemoryCharacterRepository(session, character))

    updated = await service.partial_update(
        character.id,
        character.owner_id,
        PartialUpdateCharacterData(
            wallet=0,
            luck=_stat(10),
            armor_head=ArmorValue(base_value=9, penalty=2),
            hp=HPValue(current=20, max_value=50),
            heavy_wounds_threshold=25,
        ),
    )

    assert updated.wallet == 0
    assert updated.luck.current == 10
    assert updated.armor_head == ArmorValue(base_value=9, penalty=2)
    assert updated.hp == HPValue(current=20, max_value=50)
    assert updated.role == original_role
    await session.close()


@pytest.mark.anyio
async def test_update_hides_missing_and_foreign_characters() -> None:
    character = _character()
    session = AsyncSession()
    service = CharacterService(session, MemoryCharacterRepository(session, character))

    with pytest.raises(CharacterNotFoundError):
        await service.update(character.id, uuid4(), _update_data())

    await session.close()


@pytest.mark.parametrize(
    'payload',
    [
        {},
        {'wallet': None},
        {'luck': {'current': 7}},
        {'armor_head': {'base_value': 7}},
        {'hp': {'current': 10}},
        {'id': str(uuid4())},
        {'owner_id': str(uuid4())},
    ],
)
def test_partial_update_rejects_invalid_payloads(payload: object) -> None:
    with pytest.raises(ValidationError):
        CharacterPartialUpdateRequest.model_validate(payload)


def test_partial_update_accepts_zero() -> None:
    request = CharacterPartialUpdateRequest.model_validate({'wallet': 0})

    assert request.wallet == 0
    assert request.model_fields_set == {'wallet'}
