from uuid import UUID

from fastapi import APIRouter, HTTPException, Response, status

from auth.dependencies import CurrentUser
from skills.dependencies import SkillServiceDependency
from skills.entities import Skill, SkillValidationError
from skills.schemas import (
    SkillCreateRequest,
    SkillPartialUpdateRequest,
    SkillResponse,
    SkillUpdateRequest,
)
from skills.service import (
    PartialSkillData,
    SkillData,
    SkillNotFoundError,
    SkillTitleAlreadyExistsError,
    SpecialSkillAlreadyExistsError,
)

router = APIRouter(prefix='/characters/{character_id}/skills', tags=['character skills'])


@router.get('/', response_model=list[SkillResponse])
async def list_skills(
    character_id: UUID, current_user: CurrentUser, service: SkillServiceDependency
) -> list[SkillResponse]:
    try:
        return [_to_response(skill) for skill in await service.list(character_id, current_user.id)]
    except SkillNotFoundError as error:
        raise _skill_not_found() from error


@router.post('/', response_model=SkillResponse, status_code=status.HTTP_201_CREATED)
async def create_skill(
    character_id: UUID,
    request: SkillCreateRequest,
    current_user: CurrentUser,
    service: SkillServiceDependency,
) -> SkillResponse:
    try:
        return _to_response(await service.create(character_id, current_user.id, _to_create_data(request)))
    except SkillNotFoundError as error:
        raise _skill_not_found() from error
    except (SkillTitleAlreadyExistsError, SpecialSkillAlreadyExistsError) as error:
        raise _skill_conflict(error) from error
    except SkillValidationError as error:
        raise _invalid_skill_state(error) from error


@router.get('/{skill_id}/', response_model=SkillResponse)
async def get_skill(
    character_id: UUID, skill_id: UUID, current_user: CurrentUser, service: SkillServiceDependency
) -> SkillResponse:
    try:
        return _to_response(await service.get(skill_id, character_id, current_user.id))
    except SkillNotFoundError as error:
        raise _skill_not_found() from error


@router.put(
    '/{skill_id}/',
    response_model=SkillResponse,
    responses={status.HTTP_204_NO_CONTENT: {'description': 'Skill deleted because value is zero'}},
)
async def update_skill(
    character_id: UUID,
    skill_id: UUID,
    request: SkillUpdateRequest,
    current_user: CurrentUser,
    service: SkillServiceDependency,
) -> SkillResponse | Response:
    try:
        result = await service.update(skill_id, character_id, current_user.id, _to_update_data(request))
    except SkillNotFoundError as error:
        raise _skill_not_found() from error
    except (SkillTitleAlreadyExistsError, SpecialSkillAlreadyExistsError) as error:
        raise _skill_conflict(error) from error
    except SkillValidationError as error:
        raise _invalid_skill_state(error) from error
    return Response(status_code=204) if result is None else _to_response(result)


@router.patch(
    '/{skill_id}/',
    response_model=SkillResponse,
    responses={status.HTTP_204_NO_CONTENT: {'description': 'Skill deleted because value is zero'}},
)
async def partial_update_skill(
    character_id: UUID,
    skill_id: UUID,
    request: SkillPartialUpdateRequest,
    current_user: CurrentUser,
    service: SkillServiceDependency,
) -> SkillResponse | Response:
    fields = request.model_fields_set
    data = PartialSkillData(
        title=request.title if 'title' in fields else None,
        description=request.description if 'description' in fields else None,
        value=request.value if 'value' in fields else None,
        min_value=request.min_value if 'min_value' in fields else None,
        max_value=request.max_value if 'max_value' in fields else None,
        multiplier=request.multiplier if 'multiplier' in fields else None,
        stat=request.stat,
        stat_is_set='stat' in fields,
        is_special=request.is_special if 'is_special' in fields else None,
    )
    try:
        result = await service.partial_update(skill_id, character_id, current_user.id, data)
    except SkillNotFoundError as error:
        raise _skill_not_found() from error
    except (SkillTitleAlreadyExistsError, SpecialSkillAlreadyExistsError) as error:
        raise _skill_conflict(error) from error
    except SkillValidationError as error:
        raise _invalid_skill_state(error) from error
    return Response(status_code=204) if result is None else _to_response(result)


@router.delete('/{skill_id}/', status_code=status.HTTP_204_NO_CONTENT)
async def delete_skill(
    character_id: UUID, skill_id: UUID, current_user: CurrentUser, service: SkillServiceDependency
) -> Response:
    try:
        await service.delete(skill_id, character_id, current_user.id)
    except SkillNotFoundError as error:
        raise _skill_not_found() from error
    return Response(status_code=status.HTTP_204_NO_CONTENT)


def _to_create_data(request: SkillCreateRequest) -> SkillData:
    return SkillData(**request.model_dump())


def _to_update_data(request: SkillUpdateRequest) -> SkillData:
    return SkillData(**request.model_dump())


def _to_response(skill: Skill) -> SkillResponse:
    return SkillResponse(
        id=skill.id,
        character_id=skill.character_id,
        **{
            'title': skill.title,
            'description': skill.description,
            'value': skill.value,
            'min_value': skill.min_value,
            'max_value': skill.max_value,
            'multiplier': skill.multiplier,
            'stat': skill.stat,
            'is_special': skill.is_special,
        },
    )


def _skill_not_found() -> HTTPException:
    return HTTPException(status_code=404, detail='Skill not found')


def _skill_conflict(error: Exception) -> HTTPException:
    detail = 'Skill title already exists'
    if isinstance(error, SpecialSkillAlreadyExistsError):
        detail = 'Special skill already exists'
    return HTTPException(status_code=409, detail=detail)


def _invalid_skill_state(error: SkillValidationError) -> HTTPException:
    return HTTPException(status_code=422, detail=error.code)
