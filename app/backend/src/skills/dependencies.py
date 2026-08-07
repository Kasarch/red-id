from collections.abc import AsyncIterator
from typing import Annotated

from fastapi import Depends

from auth.dependencies import SessionDependency
from skills.repository import SkillRepository
from skills.service import SkillService


async def get_skill_service(session: SessionDependency) -> AsyncIterator[SkillService]:
    yield SkillService(session, SkillRepository(session))


SkillServiceDependency = Annotated[SkillService, Depends(get_skill_service)]
