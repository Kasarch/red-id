from dataclasses import dataclass
from uuid import UUID, uuid4

from sqlalchemy.exc import IntegrityError, SQLAlchemyError
from sqlalchemy.ext.asyncio import AsyncSession

from characters.entities import ArmorValue, BoundedStat, Character, HPValue
from characters.repository import CharacterRepository
from database_errors import postgresql_constraint_name

CHARACTER_TITLE_CONSTRAINT = 'uq_characters_owner_id_title_lower'


class CharacterNotFoundError(Exception):
    pass


class CharacterTitleAlreadyExistsError(Exception):
    pass


@dataclass(slots=True, frozen=True, kw_only=True)
class UpdateCharacterData:
    title: str
    role: str
    wallet: int
    luck: BoundedStat
    intelligence: BoundedStat
    reflexes: BoundedStat
    dexterity: BoundedStat
    cool: BoundedStat
    empathy: BoundedStat
    willpower: BoundedStat
    technic: BoundedStat
    body: BoundedStat
    movement: BoundedStat
    armor_head: ArmorValue
    armor_body: ArmorValue
    armor_shield: ArmorValue
    hp: HPValue
    heavy_wounds_threshold: int
    reputation: int
    humanity: int
    upgrade_points: int


@dataclass(slots=True, frozen=True, kw_only=True)
class CreateCharacterData(UpdateCharacterData):
    pass


@dataclass(slots=True, frozen=True, kw_only=True)
class PartialUpdateCharacterData:
    title: str | None = None
    role: str | None = None
    wallet: int | None = None
    luck: BoundedStat | None = None
    intelligence: BoundedStat | None = None
    reflexes: BoundedStat | None = None
    dexterity: BoundedStat | None = None
    cool: BoundedStat | None = None
    empathy: BoundedStat | None = None
    willpower: BoundedStat | None = None
    technic: BoundedStat | None = None
    body: BoundedStat | None = None
    movement: BoundedStat | None = None
    armor_head: ArmorValue | None = None
    armor_body: ArmorValue | None = None
    armor_shield: ArmorValue | None = None
    hp: HPValue | None = None
    heavy_wounds_threshold: int | None = None
    reputation: int | None = None
    humanity: int | None = None
    upgrade_points: int | None = None


class CharacterService:
    def __init__(self, session: AsyncSession, repository: CharacterRepository) -> None:
        self._session = session
        self._repository = repository

    async def create(self, owner_id: UUID, data: CreateCharacterData) -> Character:
        character = Character(
            id=uuid4(),
            owner_id=owner_id,
            title=data.title,
            role=data.role,
            wallet=data.wallet,
            luck=data.luck,
            intelligence=data.intelligence,
            reflexes=data.reflexes,
            dexterity=data.dexterity,
            cool=data.cool,
            empathy=data.empathy,
            willpower=data.willpower,
            technic=data.technic,
            body=data.body,
            movement=data.movement,
            armor_head=data.armor_head,
            armor_body=data.armor_body,
            armor_shield=data.armor_shield,
            hp=data.hp,
            heavy_wounds_threshold=data.heavy_wounds_threshold,
            reputation=data.reputation,
            humanity=data.humanity,
            upgrade_points=data.upgrade_points,
        )
        await self._ensure_title_available(character)
        self._repository.add(character)
        await self._commit()
        return character

    async def list_by_owner(self, owner_id: UUID) -> list[Character]:
        return await self._repository.list_by_owner(owner_id)

    async def get_by_id_and_owner(self, character_id: UUID, owner_id: UUID) -> Character | None:
        return await self._repository.get_by_id_and_owner(character_id, owner_id)

    async def update(
        self,
        character_id: UUID,
        owner_id: UUID,
        data: UpdateCharacterData,
    ) -> Character:
        character = await self._get_owned_character(character_id, owner_id)
        _replace_state(character, data)
        await self._ensure_title_available(character)
        await self._save(character)
        return character

    async def partial_update(
        self,
        character_id: UUID,
        owner_id: UUID,
        data: PartialUpdateCharacterData,
    ) -> Character:
        character = await self._get_owned_character(character_id, owner_id)
        character.replace_editable_state(
            title=data.title if data.title is not None else character.title,
            role=data.role if data.role is not None else character.role,
            wallet=data.wallet if data.wallet is not None else character.wallet,
            luck=data.luck if data.luck is not None else character.luck,
            intelligence=data.intelligence if data.intelligence is not None else character.intelligence,
            reflexes=data.reflexes if data.reflexes is not None else character.reflexes,
            dexterity=data.dexterity if data.dexterity is not None else character.dexterity,
            cool=data.cool if data.cool is not None else character.cool,
            empathy=data.empathy if data.empathy is not None else character.empathy,
            willpower=data.willpower if data.willpower is not None else character.willpower,
            technic=data.technic if data.technic is not None else character.technic,
            body=data.body if data.body is not None else character.body,
            movement=data.movement if data.movement is not None else character.movement,
            armor_head=data.armor_head if data.armor_head is not None else character.armor_head,
            armor_body=data.armor_body if data.armor_body is not None else character.armor_body,
            armor_shield=data.armor_shield if data.armor_shield is not None else character.armor_shield,
            hp=data.hp if data.hp is not None else character.hp,
            heavy_wounds_threshold=(
                data.heavy_wounds_threshold
                if data.heavy_wounds_threshold is not None
                else character.heavy_wounds_threshold
            ),
            reputation=data.reputation if data.reputation is not None else character.reputation,
            humanity=data.humanity if data.humanity is not None else character.humanity,
            upgrade_points=data.upgrade_points if data.upgrade_points is not None else character.upgrade_points,
        )
        await self._ensure_title_available(character)
        await self._save(character)
        return character

    async def delete(self, character_id: UUID, owner_id: UUID) -> None:
        try:
            deleted = await self._repository.delete_by_id_and_owner(character_id, owner_id)
            if not deleted:
                raise CharacterNotFoundError
            await self._session.commit()
        except SQLAlchemyError:
            await self._session.rollback()
            raise

    async def _ensure_title_available(self, character: Character) -> None:
        existing = await self._repository.get_by_owner_and_title(character.owner_id, character.title)
        if existing is not None and existing.id != character.id:
            raise CharacterTitleAlreadyExistsError

    async def _get_owned_character(self, character_id: UUID, owner_id: UUID) -> Character:
        character = await self._repository.get_by_id_and_owner(character_id, owner_id)
        if character is None:
            raise CharacterNotFoundError
        return character

    async def _save(self, character: Character) -> None:
        try:
            saved = await self._repository.save(character)
            if not saved:
                raise CharacterNotFoundError
            await self._commit()
        except SQLAlchemyError:
            await self._session.rollback()
            raise

    async def _commit(self) -> None:
        try:
            await self._session.commit()
        except IntegrityError as error:
            await self._session.rollback()
            if _is_character_title_conflict(error):
                raise CharacterTitleAlreadyExistsError from error
            raise
        except SQLAlchemyError:
            await self._session.rollback()
            raise


def _is_character_title_conflict(error: IntegrityError) -> bool:
    return postgresql_constraint_name(error, sqlstate='23505') == CHARACTER_TITLE_CONSTRAINT


def _replace_state(character: Character, data: UpdateCharacterData) -> None:
    character.replace_editable_state(
        title=data.title,
        role=data.role,
        wallet=data.wallet,
        luck=data.luck,
        intelligence=data.intelligence,
        reflexes=data.reflexes,
        dexterity=data.dexterity,
        cool=data.cool,
        empathy=data.empathy,
        willpower=data.willpower,
        technic=data.technic,
        body=data.body,
        movement=data.movement,
        armor_head=data.armor_head,
        armor_body=data.armor_body,
        armor_shield=data.armor_shield,
        hp=data.hp,
        heavy_wounds_threshold=data.heavy_wounds_threshold,
        reputation=data.reputation,
        humanity=data.humanity,
        upgrade_points=data.upgrade_points,
    )
