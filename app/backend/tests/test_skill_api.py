from collections.abc import AsyncIterator
from copy import deepcopy
from dataclasses import dataclass
from uuid import UUID, uuid4

import pytest
from httpx import ASGITransport, AsyncClient
from pydantic import ValidationError
from sqlalchemy import delete, update
from sqlalchemy.exc import IntegrityError

from auth.jwt import JWTService
from characters.models import CharacterModel
from config import settings
from database import async_session_factory, engine
from main import app
from skills.models import SkillModel
from skills.schemas import SkillCreateRequest, SkillUpdateRequest
from users.models import User


def _payload(**changes: object) -> dict[str, object]:
    payload: dict[str, object] = {
        'title': '  Handgun  ',
        'description': '',
        'value': 4,
        'min_value': 0,
        'max_value': 10,
        'multiplier': 1,
        'stat': 'reflexes',
        'is_special': False,
    }
    payload.update(changes)
    return payload


@dataclass(slots=True)
class SkillApiContext:
    client: AsyncClient
    owner_headers: dict[str, str]
    other_headers: dict[str, str]
    character_id: UUID
    second_character_id: UUID
    other_character_id: UUID

    @property
    def base(self) -> str:
        return f'/api/v1/characters/{self.character_id}/skills/'

    async def create(self, **changes: object) -> dict[str, object]:
        response = await self.client.post(self.base, json=_payload(**changes), headers=self.owner_headers)
        assert response.status_code == 201
        return response.json()


@pytest.fixture
async def skill_api(valid_character_payload: dict[str, object]) -> AsyncIterator[SkillApiContext]:
    owner_id, other_id = uuid4(), uuid4()
    owner_headers = {'Authorization': f'Bearer {JWTService(settings.auth).create_token_pair(owner_id)[0]}'}
    other_headers = {'Authorization': f'Bearer {JWTService(settings.auth).create_token_pair(other_id)[0]}'}
    character_ids: list[UUID] = []
    async with async_session_factory() as session:
        session.add_all([User(id=owner_id), User(id=other_id)])
        await session.commit()

    try:
        async with AsyncClient(transport=ASGITransport(app=app), base_url='http://test') as client:
            first_character = await client.post(
                '/api/v1/characters/', json=valid_character_payload, headers=owner_headers
            )
            second_character_payload = deepcopy(valid_character_payload)
            second_character_payload['title'] = 'Other character'
            second_character = await client.post(
                '/api/v1/characters/', json=second_character_payload, headers=owner_headers
            )
            other_character_payload = deepcopy(valid_character_payload)
            other_character_payload['title'] = 'Foreign character'
            other_character = await client.post(
                '/api/v1/characters/', json=other_character_payload, headers=other_headers
            )
            character_id = UUID(first_character.json()['id'])
            second_character_id = UUID(second_character.json()['id'])
            other_character_id = UUID(other_character.json()['id'])
            character_ids.extend([character_id, second_character_id, other_character_id])
            yield SkillApiContext(
                client, owner_headers, other_headers, character_id, second_character_id, other_character_id
            )
    finally:
        async with async_session_factory() as session:
            await session.execute(delete(CharacterModel).where(CharacterModel.id.in_(character_ids)))
            await session.execute(delete(User).where(User.id.in_([owner_id, other_id])))
            await session.commit()
        await engine.dispose()


@pytest.mark.anyio
async def test_create_and_get_skill(skill_api: SkillApiContext) -> None:
    created = await skill_api.create()
    fetched = await skill_api.client.get(f'{skill_api.base}{created["id"]}/', headers=skill_api.owner_headers)
    assert fetched.status_code == 200
    assert fetched.json()['title'] == 'Handgun'


@pytest.mark.anyio
async def test_list_skills(skill_api: SkillApiContext) -> None:
    created = await skill_api.create()
    listed = await skill_api.client.get(skill_api.base, headers=skill_api.owner_headers)
    assert listed.status_code == 200
    assert [item['id'] for item in listed.json()] == [created['id']]


@pytest.mark.anyio
async def test_update_skill(skill_api: SkillApiContext) -> None:
    created = await skill_api.create()
    response = await skill_api.client.put(
        f'{skill_api.base}{created["id"]}/',
        json=_payload(title='  Athletics  ', stat='dexterity'),
        headers=skill_api.owner_headers,
    )
    assert response.status_code == 200
    assert response.json()['title'] == 'Athletics'


@pytest.mark.anyio
async def test_partial_update_skill(skill_api: SkillApiContext) -> None:
    created = await skill_api.create()
    response = await skill_api.client.patch(
        f'{skill_api.base}{created["id"]}/', json={'description': 'Changed'}, headers=skill_api.owner_headers
    )
    assert response.status_code == 200
    assert response.json()['description'] == 'Changed'


@pytest.mark.anyio
async def test_partial_update_stat_to_null(skill_api: SkillApiContext) -> None:
    created = await skill_api.create(is_special=True, stat='cool')
    response = await skill_api.client.patch(
        f'{skill_api.base}{created["id"]}/', json={'stat': None}, headers=skill_api.owner_headers
    )
    assert response.status_code == 200
    assert response.json()['stat'] is None


@pytest.mark.anyio
async def test_delete_skill(skill_api: SkillApiContext) -> None:
    created = await skill_api.create()
    response = await skill_api.client.delete(f'{skill_api.base}{created["id"]}/', headers=skill_api.owner_headers)
    assert response.status_code == 204
    assert response.content == b''


@pytest.mark.anyio
@pytest.mark.parametrize('min_value', [0, 5])
async def test_update_zero_deletes_skill(skill_api: SkillApiContext, min_value: int) -> None:
    created = await skill_api.create(min_value=4)
    url = f'{skill_api.base}{created["id"]}/'
    deleted = await skill_api.client.put(
        url, json=_payload(value=0, min_value=min_value, max_value=1), headers=skill_api.owner_headers
    )
    assert deleted.status_code == 204
    assert deleted.content == b''
    assert (await skill_api.client.get(url, headers=skill_api.owner_headers)).status_code == 404


@pytest.mark.anyio
async def test_partial_update_zero_deletes_skill_above_current_minimum(skill_api: SkillApiContext) -> None:
    created = await skill_api.create(value=5, min_value=5)
    url = f'{skill_api.base}{created["id"]}/'
    deleted = await skill_api.client.patch(url, json={'value': 0}, headers=skill_api.owner_headers)
    assert deleted.status_code == 204
    assert deleted.content == b''
    assert (await skill_api.client.get(url, headers=skill_api.owner_headers)).status_code == 404


@pytest.mark.anyio
async def test_create_rejects_zero_value(skill_api: SkillApiContext) -> None:
    response = await skill_api.client.post(skill_api.base, json=_payload(value=0), headers=skill_api.owner_headers)
    assert response.status_code == 422


@pytest.mark.anyio
@pytest.mark.parametrize('value', [4, 11])
async def test_update_rejects_positive_value_outside_bounds(skill_api: SkillApiContext, value: int) -> None:
    created = await skill_api.create()
    response = await skill_api.client.put(
        f'{skill_api.base}{created["id"]}/',
        json=_payload(value=value, min_value=5, max_value=10),
        headers=skill_api.owner_headers,
    )
    assert response.status_code == 422


@pytest.mark.anyio
@pytest.mark.parametrize(
    ('patch', 'detail'),
    [
        ({'min_value': 9, 'max_value': 3}, 'skill_bounds_invalid'),
        ({'value': 11}, 'skill_value_outside_bounds'),
        ({'multiplier': 0}, 'skill_multiplier_not_positive'),
        ({'stat': None}, 'regular_skill_stat_required'),
    ],
)
async def test_partial_update_reports_stable_validation_reason(
    skill_api: SkillApiContext, patch: dict[str, object], detail: str
) -> None:
    created = await skill_api.create()
    response = await skill_api.client.patch(
        f'{skill_api.base}{created["id"]}/', json=patch, headers=skill_api.owner_headers
    )
    assert response.status_code == 422
    assert response.json() == {'detail': detail}


@pytest.mark.anyio
async def test_case_insensitive_skill_title_conflict_is_per_character(skill_api: SkillApiContext) -> None:
    await skill_api.create(title='Athletics')
    duplicate = await skill_api.client.post(
        skill_api.base, json=_payload(title='athletics'), headers=skill_api.owner_headers
    )
    other_base = f'/api/v1/characters/{skill_api.second_character_id}/skills/'
    other = await skill_api.client.post(other_base, json=_payload(title='ATHLETICS'), headers=skill_api.owner_headers)
    assert duplicate.status_code == 409
    assert other.status_code == 201


@pytest.mark.anyio
async def test_second_special_skill_conflicts(skill_api: SkillApiContext) -> None:
    await skill_api.create(title='Moto', is_special=True, stat=None)
    response = await skill_api.client.post(
        skill_api.base,
        json=_payload(title='Interface', is_special=True, stat='intelligence'),
        headers=skill_api.owner_headers,
    )
    assert response.status_code == 409


@pytest.mark.anyio
async def test_foreign_character_is_hidden(skill_api: SkillApiContext) -> None:
    response = await skill_api.client.get(skill_api.base, headers=skill_api.other_headers)
    assert response.status_code == 404


@pytest.mark.anyio
async def test_foreign_skill_is_hidden(skill_api: SkillApiContext) -> None:
    created = await skill_api.create()
    response = await skill_api.client.get(f'{skill_api.base}{created["id"]}/', headers=skill_api.other_headers)
    assert response.status_code == 404


@pytest.mark.anyio
async def test_mismatched_character_and_skill_are_hidden(skill_api: SkillApiContext) -> None:
    created = await skill_api.create()
    url = f'/api/v1/characters/{skill_api.second_character_id}/skills/{created["id"]}/'
    assert (await skill_api.client.get(url, headers=skill_api.owner_headers)).status_code == 404


@pytest.mark.anyio
async def test_missing_character_is_hidden(skill_api: SkillApiContext) -> None:
    url = f'/api/v1/characters/{uuid4()}/skills/'
    assert (await skill_api.client.get(url, headers=skill_api.owner_headers)).status_code == 404


@pytest.mark.anyio
async def test_missing_skill_is_hidden(skill_api: SkillApiContext) -> None:
    assert (
        await skill_api.client.get(f'{skill_api.base}{uuid4()}/', headers=skill_api.owner_headers)
    ).status_code == 404


@pytest.mark.parametrize(
    'payload',
    [
        _payload(value=0),
        _payload(stat='unknown'),
    ],
)
def test_create_skill_request_validation(payload: dict[str, object]) -> None:
    with pytest.raises(ValidationError):
        SkillCreateRequest.model_validate(payload)


@pytest.mark.anyio
@pytest.mark.parametrize(
    ('changes', 'detail'),
    [
        ({'title': '  '}, 'skill_title_empty'),
        ({'min_value': 5, 'max_value': 4}, 'skill_bounds_invalid'),
        ({'value': 11}, 'skill_value_outside_bounds'),
        ({'multiplier': 0}, 'skill_multiplier_not_positive'),
        ({'stat': None}, 'regular_skill_stat_required'),
    ],
)
async def test_create_skill_reports_stable_validation_reason(
    skill_api: SkillApiContext, changes: dict[str, object], detail: str
) -> None:
    response = await skill_api.client.post(skill_api.base, json=_payload(**changes), headers=skill_api.owner_headers)
    assert response.status_code == 422
    assert response.json() == {'detail': detail}


@pytest.mark.parametrize('min_value', [0, 5])
def test_update_skill_accepts_zero_as_delete_command(min_value: int) -> None:
    assert SkillUpdateRequest.model_validate(_payload(value=0, min_value=min_value, max_value=1)).value == 0


@pytest.mark.anyio
async def test_skill_routes_require_trailing_slash_and_document_update_outcomes() -> None:
    character_id = uuid4()
    async with AsyncClient(transport=ASGITransport(app=app), base_url='http://test') as client:
        no_slash = await client.get(f'/api/v1/characters/{character_id}/skills')
        schema = (await client.get('/openapi.json')).json()

    assert no_slash.status_code == 404
    assert 'location' not in no_slash.headers
    path = schema['paths']['/api/v1/characters/{character_id}/skills/{skill_id}/']
    assert {'200', '204'} <= set(path['put']['responses'])
    assert {'200', '204'} <= set(path['patch']['responses'])


@pytest.mark.anyio
async def test_postgresql_enforces_skill_constraints(valid_character_payload: dict[str, object]) -> None:
    owner_id = uuid4()
    headers = {'Authorization': f'Bearer {JWTService(settings.auth).create_token_pair(owner_id)[0]}'}
    character_id: UUID | None = None
    async with async_session_factory() as session:
        session.add(User(id=owner_id))
        await session.commit()
    try:
        async with AsyncClient(transport=ASGITransport(app=app), base_url='http://test') as client:
            character = await client.post('/api/v1/characters/', json=valid_character_payload, headers=headers)
            character_id = UUID(character.json()['id'])
            created = await client.post(f'/api/v1/characters/{character_id}/skills/', json=_payload(), headers=headers)
            skill_id = UUID(created.json()['id'])

        invalid_updates: list[dict[str, int | None]] = [
            {'value': 0},
            {'min_value': -1},
            {'min_value': 6, 'max_value': 5},
            {'value': 11},
            {'multiplier': 0},
            {'stat': None},
        ]
        for values in invalid_updates:
            async with async_session_factory() as session:
                with pytest.raises(IntegrityError):
                    await session.execute(update(SkillModel).where(SkillModel.id == skill_id).values(**values))
                    await session.commit()
                await session.rollback()
    finally:
        async with async_session_factory() as session:
            if character_id is not None:
                await session.execute(delete(CharacterModel).where(CharacterModel.id == character_id))
            await session.execute(delete(User).where(User.id == owner_id))
            await session.commit()
        await engine.dispose()
