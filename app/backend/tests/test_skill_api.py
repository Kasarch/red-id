from copy import deepcopy
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
from skills.schemas import SkillCreateRequest
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


@pytest.mark.anyio
async def test_skill_crud_conflicts_ownership_and_zero_deletion(valid_character_payload: dict[str, object]) -> None:
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
            character_id = UUID(first_character.json()['id'])
            other_character_id = UUID(second_character.json()['id'])
            character_ids.extend([character_id, other_character_id])
            base = f'/api/v1/characters/{character_id}/skills/'

            created = await client.post(base, json=_payload(), headers=owner_headers)
            assert created.status_code == 201
            skill_id = UUID(created.json()['id'])
            assert created.json()['title'] == 'Handgun'

            listed = await client.get(base, headers=owner_headers)
            fetched = await client.get(f'{base}{skill_id}/', headers=owner_headers)
            assert listed.status_code == fetched.status_code == 200
            assert listed.json()[0]['id'] == str(skill_id)

            replaced = await client.put(
                f'{base}{skill_id}/', json=_payload(title='  Athletics  ', stat='dexterity'), headers=owner_headers
            )
            patched = await client.patch(f'{base}{skill_id}/', json={'description': 'Changed'}, headers=owner_headers)
            assert replaced.status_code == patched.status_code == 200
            assert replaced.json()['title'] == 'Athletics'
            assert patched.json()['description'] == 'Changed'

            duplicate = await client.post(base, json=_payload(title='athletics'), headers=owner_headers)
            assert duplicate.status_code == 409

            other_character_copy = await client.post(
                f'/api/v1/characters/{other_character_id}/skills/',
                json=_payload(title='ATHLETICS'),
                headers=owner_headers,
            )
            assert other_character_copy.status_code == 201

            special = await client.post(
                base, json=_payload(title='Moto', is_special=True, stat=None), headers=owner_headers
            )
            assert special.status_code == 201
            second_special = await client.post(
                base, json=_payload(title='Interface', is_special=True, stat='intelligence'), headers=owner_headers
            )
            assert second_special.status_code == 409

            foreign = await client.get(f'{base}{skill_id}/', headers=other_headers)
            mismatched = await client.get(
                f'/api/v1/characters/{other_character_id}/skills/{skill_id}/', headers=owner_headers
            )
            missing = await client.get(f'{base}{uuid4()}/', headers=owner_headers)
            assert foreign.status_code == mismatched.status_code == missing.status_code == 404

            null_regular = await client.patch(f'{base}{skill_id}/', json={'stat': None}, headers=owner_headers)
            assert null_regular.status_code == 422
            delete_special = await client.delete(f'{base}{special.json()["id"]}/', headers=owner_headers)
            assert delete_special.status_code == 204
            assert delete_special.content == b''
            made_special = await client.patch(
                f'{base}{skill_id}/', json={'is_special': True, 'stat': None}, headers=owner_headers
            )
            assert made_special.status_code == 200
            assert made_special.json()['stat'] is None

            deleted = await client.put(
                f'{base}{skill_id}/', json=_payload(title='Athletics', value=0), headers=owner_headers
            )
            after_delete = await client.get(f'{base}{skill_id}/', headers=owner_headers)
            assert deleted.status_code == 204
            assert deleted.content == b''
            assert after_delete.status_code == 404

            patch_deleted_skill = await client.post(base, json=_payload(title='Patch delete'), headers=owner_headers)
            patch_deleted = await client.patch(
                f'{base}{patch_deleted_skill.json()["id"]}/', json={'value': 0}, headers=owner_headers
            )
            assert patch_deleted.status_code == 204
            assert patch_deleted.content == b''
    finally:
        async with async_session_factory() as session:
            await session.execute(delete(CharacterModel).where(CharacterModel.id.in_(character_ids)))
            await session.execute(delete(User).where(User.id.in_([owner_id, other_id])))
            await session.commit()
        await engine.dispose()


@pytest.mark.parametrize(
    'payload',
    [
        _payload(value=0),
        _payload(value=-1),
        _payload(value=11),
        _payload(min_value=5, max_value=4),
        _payload(multiplier=0),
        _payload(stat=None),
        _payload(stat='unknown'),
    ],
)
def test_create_skill_validation(payload: dict[str, object]) -> None:
    with pytest.raises(ValidationError):
        SkillCreateRequest.model_validate(payload)


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
