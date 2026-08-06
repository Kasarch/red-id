from uuid import UUID, uuid4

import pytest
from sqlalchemy import delete

from characters.entities import ArmorValue, BoundedStat, Character, HPValue
from characters.models import CharacterModel
from characters.repository import CharacterRepository
from database import async_session_factory, engine
from users.models import User


def _stat(current: int = 5) -> BoundedStat:
    return BoundedStat(current=current, min_value=3, max_value=10)


def _character(owner_id: UUID) -> Character:
    return Character(
        id=uuid4(),
        owner_id=owner_id,
        title='repository-test-solo',
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
        armor_head=ArmorValue(base_value=11, penalty=0),
        armor_body=ArmorValue(base_value=11, penalty=0),
        armor_shield=ArmorValue(base_value=11, penalty=0),
        hp=HPValue(current=35, max_value=35),
        heavy_wounds_threshold=17,
        reputation=0,
        humanity=50,
        upgrade_points=0,
    )


@pytest.mark.anyio
async def test_character_round_trip_and_update_persist_across_sessions() -> None:
    owner_id = uuid4()
    character = _character(owner_id)

    try:
        async with async_session_factory() as session:
            session.add(User(id=owner_id, avatar_url=None))
            await session.flush()
            repository = CharacterRepository(session)
            repository.add(character)
            await session.commit()

        async with async_session_factory() as session:
            repository = CharacterRepository(session)
            loaded = await repository.get_by_id_and_owner(character.id, owner_id)
            assert loaded is not None
            assert loaded.luck == _stat()
            assert loaded.armor_body == ArmorValue(base_value=11, penalty=0)
            assert loaded.hp == HPValue(current=35, max_value=35)

            loaded.replace_editable_state(
                role=loaded.role,
                wallet=0,
                luck=BoundedStat(current=10, min_value=3, max_value=10),
                intelligence=loaded.intelligence,
                reflexes=loaded.reflexes,
                dexterity=loaded.dexterity,
                cool=loaded.cool,
                empathy=loaded.empathy,
                willpower=loaded.willpower,
                technic=loaded.technic,
                body=loaded.body,
                movement=loaded.movement,
                armor_head=loaded.armor_head,
                armor_body=ArmorValue(base_value=9, penalty=2),
                armor_shield=loaded.armor_shield,
                hp=HPValue(current=30, max_value=40),
                heavy_wounds_threshold=20,
                reputation=loaded.reputation,
                humanity=loaded.humanity,
                upgrade_points=loaded.upgrade_points,
            )
            assert await repository.save(loaded)
            await session.commit()

        async with async_session_factory() as session:
            persisted = await CharacterRepository(session).get_by_id_and_owner(character.id, owner_id)
            assert persisted is not None
            assert persisted.wallet == 0
            assert persisted.luck.current == 10
            assert persisted.armor_body == ArmorValue(base_value=9, penalty=2)
            assert persisted.hp == HPValue(current=30, max_value=40)
    finally:
        async with async_session_factory() as session:
            await session.execute(delete(CharacterModel).where(CharacterModel.id == character.id))
            await session.execute(delete(User).where(User.id == owner_id))
            await session.commit()
        await engine.dispose()
