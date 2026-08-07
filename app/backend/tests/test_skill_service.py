from uuid import UUID, uuid4

import pytest
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from characters.entities import CharacterStatName
from skills.entities import Skill
from skills.repository import SkillRepository
from skills.service import (
    SPECIAL_INDEX,
    TITLE_INDEX,
    SkillData,
    SkillService,
    SkillTitleAlreadyExistsError,
    SpecialSkillAlreadyExistsError,
)


class ConstraintViolationError(Exception):
    sqlstate = '23505'

    def __init__(self, constraint_name: str) -> None:
        self.constraint_name = constraint_name


def _integrity_error(constraint_name: str) -> IntegrityError:
    try:
        raise ConstraintViolationError(constraint_name)
    except ConstraintViolationError as cause:
        try:
            raise RuntimeError('driver error') from cause
        except RuntimeError as driver_error:
            return IntegrityError('statement', {}, driver_error)


class RecordingSession(AsyncSession):
    def __init__(self, error: IntegrityError) -> None:
        super().__init__()
        self.error = error
        self.rollbacks = 0

    async def commit(self) -> None:
        raise self.error

    async def rollback(self) -> None:
        self.rollbacks += 1


class CreateRepository(SkillRepository):
    async def character_exists(self, character_id: UUID, owner_id: UUID) -> bool:
        return True

    async def get_by_title(self, character_id: UUID, title: str) -> Skill | None:
        return None

    async def get_special(self, character_id: UUID) -> Skill | None:
        return None

    def add(self, skill: Skill) -> None:
        pass


def _data() -> SkillData:
    return SkillData(
        title='Handgun',
        description='',
        value=4,
        min_value=0,
        max_value=10,
        multiplier=1,
        stat=CharacterStatName.REFLEXES,
        is_special=False,
    )


@pytest.mark.anyio
@pytest.mark.parametrize(
    ('constraint', 'expected'),
    [
        (TITLE_INDEX, SkillTitleAlreadyExistsError),
        (SPECIAL_INDEX, SpecialSkillAlreadyExistsError),
    ],
)
async def test_concurrent_skill_conflicts_are_mapped_and_rolled_back(
    constraint: str, expected: type[Exception]
) -> None:
    session = RecordingSession(_integrity_error(constraint))
    service = SkillService(session, CreateRepository(session))

    with pytest.raises(expected):
        await service.create(uuid4(), uuid4(), _data())

    assert session.rollbacks == 1
    await session.close()


@pytest.mark.anyio
async def test_unrelated_integrity_error_is_preserved_and_rolled_back() -> None:
    error = _integrity_error('unrelated_constraint')
    session = RecordingSession(error)
    service = SkillService(session, CreateRepository(session))

    with pytest.raises(IntegrityError) as caught:
        await service.create(uuid4(), uuid4(), _data())

    assert caught.value is error
    assert session.rollbacks == 1
    await session.close()
