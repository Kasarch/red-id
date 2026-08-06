from uuid import UUID

from sqlalchemy import delete, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from characters.entities import ArmorValue, BoundedStat, Character, HPValue
from characters.models import CharacterModel


class CharacterRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def get_by_id_and_owner(self, character_id: UUID, owner_id: UUID) -> Character | None:
        statement = select(CharacterModel).where(
            CharacterModel.id == character_id,
            CharacterModel.owner_id == owner_id,
        )
        result = await self._session.execute(statement)
        model = result.scalar_one_or_none()
        return _to_domain(model) if model is not None else None

    async def get_by_owner_and_title(self, owner_id: UUID, title: str) -> Character | None:
        statement = select(CharacterModel).where(
            CharacterModel.owner_id == owner_id,
            func.lower(CharacterModel.title) == title.lower(),
        )
        result = await self._session.execute(statement)
        model = result.scalar_one_or_none()
        return _to_domain(model) if model is not None else None

    async def list_by_owner(self, owner_id: UUID) -> list[Character]:
        statement = select(CharacterModel).where(
            CharacterModel.owner_id == owner_id,
        )
        result = await self._session.execute(statement)
        models = result.scalars().all()
        return [_to_domain(model) for model in models]

    def add(self, character: Character) -> None:
        self._session.add(_to_model(character))

    async def save(self, character: Character) -> bool:
        statement = select(CharacterModel).where(
            CharacterModel.id == character.id,
            CharacterModel.owner_id == character.owner_id,
        )
        result = await self._session.execute(statement)
        model = result.scalar_one_or_none()
        if model is None:
            return False
        _update_model(model, character)
        return True

    async def delete_by_id_and_owner(self, character_id: UUID, owner_id: UUID) -> bool:
        statement = (
            delete(CharacterModel)
            .where(
                CharacterModel.id == character_id,
                CharacterModel.owner_id == owner_id,
            )
            .returning(CharacterModel.id)
        )
        result = await self._session.execute(statement)
        return result.scalar_one_or_none() is not None


def _to_domain(model: CharacterModel) -> Character:
    return Character(
        id=model.id,
        owner_id=model.owner_id,
        title=model.title,
        role=model.role,
        wallet=model.wallet,
        luck=BoundedStat(current=model.luck_current, min_value=model.luck_min, max_value=model.luck_max),
        intelligence=BoundedStat(current=model.int_current, min_value=model.int_min, max_value=model.int_max),
        reflexes=BoundedStat(current=model.ref_current, min_value=model.ref_min, max_value=model.ref_max),
        dexterity=BoundedStat(current=model.dex_current, min_value=model.dex_min, max_value=model.dex_max),
        cool=BoundedStat(current=model.cool_current, min_value=model.cool_min, max_value=model.cool_max),
        empathy=BoundedStat(current=model.emp_current, min_value=model.emp_min, max_value=model.emp_max),
        willpower=BoundedStat(current=model.will_current, min_value=model.will_min, max_value=model.will_max),
        technic=BoundedStat(current=model.tech_current, min_value=model.tech_min, max_value=model.tech_max),
        body=BoundedStat(current=model.body_current, min_value=model.body_min, max_value=model.body_max),
        movement=BoundedStat(current=model.move_current, min_value=model.move_min, max_value=model.move_max),
        armor_head=ArmorValue(base_value=model.armor_head, penalty=model.armor_head_penalty),
        armor_body=ArmorValue(base_value=model.armor_body, penalty=model.armor_body_penalty),
        armor_shield=ArmorValue(base_value=model.armor_shield, penalty=model.armor_shield_penalty),
        hp=HPValue(current=model.hp_current, max_value=model.hp_max),
        heavy_wounds_threshold=model.heavy_wounds_threshold,
        reputation=model.reputation,
        humanity=model.humanity,
        upgrade_points=model.upgrade_points,
    )


def _to_model(character: Character) -> CharacterModel:
    model = CharacterModel(id=character.id, owner_id=character.owner_id)
    _update_model(model, character)
    return model


def _update_model(model: CharacterModel, character: Character) -> None:
    model.title = character.title
    model.role = character.role
    model.wallet = character.wallet
    model.luck_current = character.luck.current
    model.luck_min = character.luck.min_value
    model.luck_max = character.luck.max_value
    model.int_current = character.intelligence.current
    model.int_min = character.intelligence.min_value
    model.int_max = character.intelligence.max_value
    model.ref_current = character.reflexes.current
    model.ref_min = character.reflexes.min_value
    model.ref_max = character.reflexes.max_value
    model.dex_current = character.dexterity.current
    model.dex_min = character.dexterity.min_value
    model.dex_max = character.dexterity.max_value
    model.cool_current = character.cool.current
    model.cool_min = character.cool.min_value
    model.cool_max = character.cool.max_value
    model.emp_current = character.empathy.current
    model.emp_min = character.empathy.min_value
    model.emp_max = character.empathy.max_value
    model.will_current = character.willpower.current
    model.will_min = character.willpower.min_value
    model.will_max = character.willpower.max_value
    model.tech_current = character.technic.current
    model.tech_min = character.technic.min_value
    model.tech_max = character.technic.max_value
    model.body_current = character.body.current
    model.body_min = character.body.min_value
    model.body_max = character.body.max_value
    model.move_current = character.movement.current
    model.move_min = character.movement.min_value
    model.move_max = character.movement.max_value
    model.armor_head = character.armor_head.base_value
    model.armor_head_penalty = character.armor_head.penalty
    model.armor_body = character.armor_body.base_value
    model.armor_body_penalty = character.armor_body.penalty
    model.armor_shield = character.armor_shield.base_value
    model.armor_shield_penalty = character.armor_shield.penalty
    model.hp_current = character.hp.current
    model.hp_max = character.hp.max_value
    model.heavy_wounds_threshold = character.heavy_wounds_threshold
    model.reputation = character.reputation
    model.humanity = character.humanity
    model.upgrade_points = character.upgrade_points
