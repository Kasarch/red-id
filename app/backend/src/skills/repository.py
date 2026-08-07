from uuid import UUID

from sqlalchemy import delete, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from characters.models import CharacterModel
from skills.entities import Skill
from skills.models import SkillModel


class SkillRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def character_exists(self, character_id: UUID, owner_id: UUID) -> bool:
        statement = select(CharacterModel.id).where(
            CharacterModel.id == character_id,
            CharacterModel.owner_id == owner_id,
        )
        return (await self._session.execute(statement)).scalar_one_or_none() is not None

    async def list_for_owned_character(self, character_id: UUID, owner_id: UUID) -> list[Skill] | None:
        if not await self.character_exists(character_id, owner_id):
            return None
        statement = select(SkillModel).where(SkillModel.character_id == character_id).order_by(SkillModel.title)
        return [_to_domain(model) for model in (await self._session.execute(statement)).scalars().all()]

    async def get_for_owned_character(self, skill_id: UUID, character_id: UUID, owner_id: UUID) -> Skill | None:
        statement = (
            select(SkillModel)
            .join(CharacterModel, CharacterModel.id == SkillModel.character_id)
            .where(
                SkillModel.id == skill_id,
                SkillModel.character_id == character_id,
                CharacterModel.owner_id == owner_id,
            )
        )
        model = (await self._session.execute(statement)).scalar_one_or_none()
        return _to_domain(model) if model is not None else None

    async def get_by_title(self, character_id: UUID, title: str) -> Skill | None:
        statement = select(SkillModel).where(
            SkillModel.character_id == character_id,
            func.lower(SkillModel.title) == title.lower(),
        )
        model = (await self._session.execute(statement)).scalar_one_or_none()
        return _to_domain(model) if model is not None else None

    async def get_special(self, character_id: UUID) -> Skill | None:
        statement = select(SkillModel).where(
            SkillModel.character_id == character_id,
            SkillModel.is_special.is_(True),
        )
        model = (await self._session.execute(statement)).scalar_one_or_none()
        return _to_domain(model) if model is not None else None

    def add(self, skill: Skill) -> None:
        self._session.add(_to_model(skill))

    async def save(self, skill: Skill, owner_id: UUID) -> bool:
        statement = (
            select(SkillModel)
            .join(CharacterModel, CharacterModel.id == SkillModel.character_id)
            .where(
                SkillModel.id == skill.id,
                SkillModel.character_id == skill.character_id,
                CharacterModel.owner_id == owner_id,
            )
        )
        model = (await self._session.execute(statement)).scalar_one_or_none()
        if model is None:
            return False
        _update_model(model, skill)
        return True

    async def delete(self, skill_id: UUID, character_id: UUID, owner_id: UUID) -> bool:
        owned_character = select(CharacterModel.id).where(
            CharacterModel.id == character_id,
            CharacterModel.owner_id == owner_id,
        )
        statement = (
            delete(SkillModel)
            .where(
                SkillModel.id == skill_id,
                SkillModel.character_id == character_id,
                SkillModel.character_id.in_(owned_character),
            )
            .returning(SkillModel.id)
        )
        return (await self._session.execute(statement)).scalar_one_or_none() is not None


def _to_domain(model: SkillModel) -> Skill:
    return Skill(
        id=model.id,
        character_id=model.character_id,
        title=model.title,
        description=model.description,
        value=model.value,
        min_value=model.min_value,
        max_value=model.max_value,
        multiplier=model.multiplier,
        stat=model.stat,
        is_special=model.is_special,
    )


def _to_model(skill: Skill) -> SkillModel:
    model = SkillModel(id=skill.id, character_id=skill.character_id)
    _update_model(model, skill)
    return model


def _update_model(model: SkillModel, skill: Skill) -> None:
    model.title = skill.title
    model.description = skill.description
    model.value = skill.value
    model.min_value = skill.min_value
    model.max_value = skill.max_value
    model.multiplier = skill.multiplier
    model.stat = skill.stat
    model.is_special = skill.is_special
