from dataclasses import asdict, dataclass
from uuid import UUID, uuid4

from sqlalchemy.exc import IntegrityError, SQLAlchemyError
from sqlalchemy.ext.asyncio import AsyncSession

from characters.entities import CharacterStatName
from database_errors import postgresql_constraint_name
from skills.entities import Skill
from skills.repository import SkillRepository

TITLE_INDEX = 'uq_character_skills_character_id_title_lower'
SPECIAL_INDEX = 'uq_character_skills_one_special_per_character'


class SkillNotFoundError(Exception):
    pass


class SkillTitleAlreadyExistsError(Exception):
    pass


class SpecialSkillAlreadyExistsError(Exception):
    pass


@dataclass(slots=True, frozen=True, kw_only=True)
class SkillData:
    title: str
    description: str
    value: int
    min_value: int
    max_value: int
    multiplier: int
    stat: CharacterStatName | None
    is_special: bool


@dataclass(slots=True, frozen=True, kw_only=True)
class PartialSkillData:
    title: str | None = None
    description: str | None = None
    value: int | None = None
    min_value: int | None = None
    max_value: int | None = None
    multiplier: int | None = None
    stat: CharacterStatName | None = None
    stat_is_set: bool = False
    is_special: bool | None = None


class SkillService:
    def __init__(self, session: AsyncSession, repository: SkillRepository) -> None:
        self._session = session
        self._repository = repository

    async def create(self, character_id: UUID, owner_id: UUID, data: SkillData) -> Skill:
        if not await self._repository.character_exists(character_id, owner_id):
            raise SkillNotFoundError
        skill = _new_skill(character_id, data)
        await self._ensure_available(skill)
        self._repository.add(skill)
        await self._commit()
        return skill

    async def list(self, character_id: UUID, owner_id: UUID) -> list[Skill]:
        skills = await self._repository.list_for_owned_character(character_id, owner_id)
        if skills is None:
            raise SkillNotFoundError
        return skills

    async def get(self, skill_id: UUID, character_id: UUID, owner_id: UUID) -> Skill:
        skill = await self._repository.get_for_owned_character(skill_id, character_id, owner_id)
        if skill is None:
            raise SkillNotFoundError
        return skill

    async def update(self, skill_id: UUID, character_id: UUID, owner_id: UUID, data: SkillData) -> Skill | None:
        skill = await self.get(skill_id, character_id, owner_id)
        if data.value == 0:
            await self.delete(skill_id, character_id, owner_id)
            return None
        skill.replace_editable_state(**asdict(data))
        await self._ensure_available(skill)
        await self._save(skill, owner_id)
        return skill

    async def partial_update(
        self, skill_id: UUID, character_id: UUID, owner_id: UUID, data: PartialSkillData
    ) -> Skill | None:
        skill = await self.get(skill_id, character_id, owner_id)
        if data.value == 0:
            await self.delete(skill_id, character_id, owner_id)
            return None
        skill.replace_editable_state(
            title=data.title if data.title is not None else skill.title,
            description=data.description if data.description is not None else skill.description,
            value=data.value if data.value is not None else skill.value,
            min_value=data.min_value if data.min_value is not None else skill.min_value,
            max_value=data.max_value if data.max_value is not None else skill.max_value,
            multiplier=data.multiplier if data.multiplier is not None else skill.multiplier,
            stat=data.stat if data.stat_is_set else skill.stat,
            is_special=data.is_special if data.is_special is not None else skill.is_special,
        )
        await self._ensure_available(skill)
        await self._save(skill, owner_id)
        return skill

    async def delete(self, skill_id: UUID, character_id: UUID, owner_id: UUID) -> None:
        try:
            if not await self._repository.delete(skill_id, character_id, owner_id):
                raise SkillNotFoundError
            await self._session.commit()
        except SQLAlchemyError:
            await self._session.rollback()
            raise

    async def _ensure_available(self, skill: Skill) -> None:
        same_title = await self._repository.get_by_title(skill.character_id, skill.title)
        if same_title is not None and same_title.id != skill.id:
            raise SkillTitleAlreadyExistsError
        if skill.is_special:
            special = await self._repository.get_special(skill.character_id)
            if special is not None and special.id != skill.id:
                raise SpecialSkillAlreadyExistsError

    async def _save(self, skill: Skill, owner_id: UUID) -> None:
        try:
            if not await self._repository.save(skill, owner_id):
                raise SkillNotFoundError
            await self._commit()
        except SQLAlchemyError:
            await self._session.rollback()
            raise

    async def _commit(self) -> None:
        try:
            await self._session.commit()
        except IntegrityError as error:
            await self._session.rollback()
            constraint = postgresql_constraint_name(error, sqlstate='23505')
            if constraint == TITLE_INDEX:
                raise SkillTitleAlreadyExistsError from error
            if constraint == SPECIAL_INDEX:
                raise SpecialSkillAlreadyExistsError from error
            raise
        except SQLAlchemyError:
            await self._session.rollback()
            raise


def _new_skill(character_id: UUID, data: SkillData) -> Skill:
    return Skill(id=uuid4(), character_id=character_id, **asdict(data))
