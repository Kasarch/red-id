from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status

from auth.dependencies import CurrentUser
from characters.dependencies import get_character_service
from characters.entities import ArmorValue, BoundedStat, Character, HPValue
from characters.schemas import (
    ArmorValueRequest,
    BoundedStatRequest,
    CharacterCreateRequest,
    CharacterPartialUpdateRequest,
    CharacterResponse,
    CharacterUpdateRequest,
    HPValueRequest,
)
from characters.service import (
    CharacterNotFoundError,
    CharacterService,
    CreateCharacterData,
    PartialUpdateCharacterData,
    UpdateCharacterData,
)

router = APIRouter(prefix='/characters', tags=['characters'])

CharacterServiceDependency = Annotated[CharacterService, Depends(get_character_service)]


@router.get('/', response_model=list[CharacterResponse])
async def list_characters(
    current_user: CurrentUser,
    character_service: CharacterServiceDependency,
) -> list[CharacterResponse]:
    characters = await character_service.list_by_owner(current_user.id)
    return [_to_response(character) for character in characters]


@router.get('/{character_id}/', response_model=CharacterResponse)
async def get_character(
    character_id: UUID,
    current_user: CurrentUser,
    character_service: CharacterServiceDependency,
) -> CharacterResponse:
    character = await character_service.get_by_id_and_owner(character_id, current_user.id)
    if character is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail='Character not found')
    return _to_response(character)


@router.post('/', response_model=CharacterResponse, status_code=status.HTTP_201_CREATED)
async def create_character(
    request: CharacterCreateRequest,
    current_user: CurrentUser,
    character_service: CharacterServiceDependency,
) -> CharacterResponse:
    data = _to_create_data(request)
    character = await character_service.create(current_user.id, data)
    return _to_response(character)


@router.put(
    '/{character_id}/',
    response_model=CharacterResponse,
    responses={status.HTTP_404_NOT_FOUND: {'description': 'Character not found'}},
)
async def update_character(
    character_id: UUID,
    request: CharacterUpdateRequest,
    current_user: CurrentUser,
    character_service: CharacterServiceDependency,
) -> CharacterResponse:
    try:
        character = await character_service.update(character_id, current_user.id, _to_update_data(request))
    except CharacterNotFoundError as error:
        raise _character_not_found() from error
    return _to_response(character)


@router.patch(
    '/{character_id}/',
    response_model=CharacterResponse,
    responses={status.HTTP_404_NOT_FOUND: {'description': 'Character not found'}},
)
async def partial_update_character(
    character_id: UUID,
    request: CharacterPartialUpdateRequest,
    current_user: CurrentUser,
    character_service: CharacterServiceDependency,
) -> CharacterResponse:
    try:
        character = await character_service.partial_update(
            character_id,
            current_user.id,
            _to_partial_update_data(request),
        )
    except CharacterNotFoundError as error:
        raise _character_not_found() from error
    return _to_response(character)


def _to_response(character: Character) -> CharacterResponse:
    return CharacterResponse(
        id=character.id,
        title=character.title,
        role=character.role,
        wallet=character.wallet,
        luck=_to_bounded_stat_response(character.luck),
        intelligence=_to_bounded_stat_response(character.intelligence),
        reflexes=_to_bounded_stat_response(character.reflexes),
        dexterity=_to_bounded_stat_response(character.dexterity),
        cool=_to_bounded_stat_response(character.cool),
        empathy=_to_bounded_stat_response(character.empathy),
        willpower=_to_bounded_stat_response(character.willpower),
        technic=_to_bounded_stat_response(character.technic),
        body=_to_bounded_stat_response(character.body),
        movement=_to_bounded_stat_response(character.movement),
        armor_head=_to_armor_value_response(character.armor_head),
        armor_body=_to_armor_value_response(character.armor_body),
        armor_shield=_to_armor_value_response(character.armor_shield),
        hp=HPValueRequest(current=character.hp.current, max_value=character.hp.max_value),
        heavy_wounds_threshold=character.heavy_wounds_threshold,
        reputation=character.reputation,
        humanity=character.humanity,
        upgrade_points=character.upgrade_points,
    )


def _to_bounded_stat_response(stat: BoundedStat) -> BoundedStatRequest:
    return BoundedStatRequest(
        current=stat.current,
        min_value=stat.min_value,
        max_value=stat.max_value,
    )


def _to_armor_value_response(armor: ArmorValue) -> ArmorValueRequest:
    return ArmorValueRequest(base_value=armor.base_value, penalty=armor.penalty)


def _to_create_data(request: CharacterCreateRequest) -> CreateCharacterData:
    return CreateCharacterData(
        title=request.title,
        role=request.role,
        wallet=request.wallet,
        luck=_to_bounded_stat(request.luck),
        intelligence=_to_bounded_stat(request.intelligence),
        reflexes=_to_bounded_stat(request.reflexes),
        dexterity=_to_bounded_stat(request.dexterity),
        cool=_to_bounded_stat(request.cool),
        empathy=_to_bounded_stat(request.empathy),
        willpower=_to_bounded_stat(request.willpower),
        technic=_to_bounded_stat(request.technic),
        body=_to_bounded_stat(request.body),
        movement=_to_bounded_stat(request.movement),
        armor_head=_to_armor_value(request.armor_head),
        armor_body=_to_armor_value(request.armor_body),
        armor_shield=_to_armor_value(request.armor_shield),
        hp=HPValue(
            current=request.hp.current,
            max_value=request.hp.max_value,
        ),
        heavy_wounds_threshold=request.heavy_wounds_threshold,
        reputation=request.reputation,
        humanity=request.humanity,
        upgrade_points=request.upgrade_points,
    )


def _to_update_data(request: CharacterUpdateRequest) -> UpdateCharacterData:
    return UpdateCharacterData(
        role=request.role,
        wallet=request.wallet,
        luck=_to_bounded_stat(request.luck),
        intelligence=_to_bounded_stat(request.intelligence),
        reflexes=_to_bounded_stat(request.reflexes),
        dexterity=_to_bounded_stat(request.dexterity),
        cool=_to_bounded_stat(request.cool),
        empathy=_to_bounded_stat(request.empathy),
        willpower=_to_bounded_stat(request.willpower),
        technic=_to_bounded_stat(request.technic),
        body=_to_bounded_stat(request.body),
        movement=_to_bounded_stat(request.movement),
        armor_head=_to_armor_value(request.armor_head),
        armor_body=_to_armor_value(request.armor_body),
        armor_shield=_to_armor_value(request.armor_shield),
        hp=HPValue(current=request.hp.current, max_value=request.hp.max_value),
        heavy_wounds_threshold=request.heavy_wounds_threshold,
        reputation=request.reputation,
        humanity=request.humanity,
        upgrade_points=request.upgrade_points,
    )


def _to_partial_update_data(request: CharacterPartialUpdateRequest) -> PartialUpdateCharacterData:
    fields = request.model_fields_set
    return PartialUpdateCharacterData(
        role=request.role if 'role' in fields else None,
        wallet=request.wallet if 'wallet' in fields else None,
        luck=_to_optional_bounded_stat(request.luck) if 'luck' in fields else None,
        intelligence=_to_optional_bounded_stat(request.intelligence) if 'intelligence' in fields else None,
        reflexes=_to_optional_bounded_stat(request.reflexes) if 'reflexes' in fields else None,
        dexterity=_to_optional_bounded_stat(request.dexterity) if 'dexterity' in fields else None,
        cool=_to_optional_bounded_stat(request.cool) if 'cool' in fields else None,
        empathy=_to_optional_bounded_stat(request.empathy) if 'empathy' in fields else None,
        willpower=_to_optional_bounded_stat(request.willpower) if 'willpower' in fields else None,
        technic=_to_optional_bounded_stat(request.technic) if 'technic' in fields else None,
        body=_to_optional_bounded_stat(request.body) if 'body' in fields else None,
        movement=_to_optional_bounded_stat(request.movement) if 'movement' in fields else None,
        armor_head=_to_optional_armor_value(request.armor_head) if 'armor_head' in fields else None,
        armor_body=_to_optional_armor_value(request.armor_body) if 'armor_body' in fields else None,
        armor_shield=_to_optional_armor_value(request.armor_shield) if 'armor_shield' in fields else None,
        hp=_to_optional_hp_value(request.hp) if 'hp' in fields else None,
        heavy_wounds_threshold=(request.heavy_wounds_threshold if 'heavy_wounds_threshold' in fields else None),
        reputation=request.reputation if 'reputation' in fields else None,
        humanity=request.humanity if 'humanity' in fields else None,
        upgrade_points=request.upgrade_points if 'upgrade_points' in fields else None,
    )


def _to_bounded_stat(schema: BoundedStatRequest) -> BoundedStat:
    return BoundedStat(
        current=schema.current,
        min_value=schema.min_value,
        max_value=schema.max_value,
    )


def _to_armor_value(schema: ArmorValueRequest) -> ArmorValue:
    return ArmorValue(
        base_value=schema.base_value,
        penalty=schema.penalty,
    )


def _to_optional_bounded_stat(schema: BoundedStatRequest | None) -> BoundedStat:
    if schema is None:
        raise ValueError('bounded stat cannot be null')
    return _to_bounded_stat(schema)


def _to_optional_armor_value(schema: ArmorValueRequest | None) -> ArmorValue:
    if schema is None:
        raise ValueError('armor cannot be null')
    return _to_armor_value(schema)


def _to_optional_hp_value(schema: HPValueRequest | None) -> HPValue:
    if schema is None:
        raise ValueError('HP cannot be null')
    return HPValue(current=schema.current, max_value=schema.max_value)


def _character_not_found() -> HTTPException:
    return HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail='Character not found')
