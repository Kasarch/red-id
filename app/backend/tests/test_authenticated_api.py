from copy import deepcopy
from uuid import UUID, uuid4

import pytest
from httpx import ASGITransport, AsyncClient
from sqlalchemy import delete

from auth.jwt import JWTService, TokenType
from characters.models import CharacterModel
from config import settings
from database import async_session_factory, engine
from main import app
from users.models import User


@pytest.mark.anyio
async def test_refresh_and_current_user_with_real_bearer_authentication() -> None:
    user_id = uuid4()
    jwt_service = JWTService(settings.auth)
    access_token, refresh_token = jwt_service.create_token_pair(user_id)
    async with async_session_factory() as session:
        session.add(User(id=user_id, avatar_url='https://example.com/avatar.png'))
        await session.commit()

    try:
        async with AsyncClient(transport=ASGITransport(app=app), base_url='http://test') as client:
            me = await client.get('/api/v1/users/me/', headers={'Authorization': f'Bearer {access_token}'})
            refreshed = await client.post('/api/v1/auth/refresh/', json={'refresh_token': refresh_token})
            wrong_type = await client.get(
                '/api/v1/users/me/',
                headers={'Authorization': f'Bearer {refresh_token}'},
            )

        assert me.status_code == 200
        assert me.json()['id'] == str(user_id)
        assert refreshed.status_code == 200
        tokens = refreshed.json()
        assert jwt_service.decode_user_token(tokens['access_token'], TokenType.ACCESS) == user_id
        assert jwt_service.decode_user_token(tokens['refresh_token'], TokenType.REFRESH) == user_id
        assert not refreshed.cookies
        assert wrong_type.status_code == 401
    finally:
        async with async_session_factory() as session:
            await session.execute(delete(User).where(User.id == user_id))
            await session.commit()
        await engine.dispose()


@pytest.mark.anyio
async def test_authenticated_character_create_put_patch_and_list(
    valid_character_payload: dict[str, object],
) -> None:
    user_id = uuid4()
    access_token, _ = JWTService(settings.auth).create_token_pair(user_id)
    headers = {'Authorization': f'Bearer {access_token}'}
    payload = deepcopy(valid_character_payload)
    payload['title'] = f'solo-{uuid4()}'
    async with async_session_factory() as session:
        session.add(User(id=user_id, avatar_url=None))
        await session.commit()

    character_id: str | None = None
    try:
        async with AsyncClient(transport=ASGITransport(app=app), base_url='http://test') as client:
            created = await client.post('/api/v1/characters/', json=payload, headers=headers)
            assert created.status_code == 201
            character_id = created.json()['id']

            update_payload = deepcopy(payload)
            update_payload['title'] = f'Updated {payload["title"]}'
            update_payload['wallet'] = 0
            replaced = await client.put(
                f'/api/v1/characters/{character_id}/',
                json=update_payload,
                headers=headers,
            )
            patched = await client.patch(
                f'/api/v1/characters/{character_id}/',
                json={'reputation': 7},
                headers=headers,
            )
            listed = await client.get('/api/v1/characters/', headers=headers)

        assert replaced.status_code == 200
        assert replaced.json()['title'] == update_payload['title']
        assert replaced.json()['wallet'] == 0
        assert patched.status_code == 200
        assert patched.json()['wallet'] == 0
        assert patched.json()['reputation'] == 7
        assert listed.status_code == 200
        assert any(item['id'] == character_id for item in listed.json())
    finally:
        async with async_session_factory() as session:
            if character_id is not None:
                await session.execute(delete(CharacterModel).where(CharacterModel.id == UUID(character_id)))
            await session.execute(delete(User).where(User.id == user_id))
            await session.commit()
        await engine.dispose()


@pytest.mark.anyio
async def test_character_title_uniqueness_ownership_and_delete(
    valid_character_payload: dict[str, object],
) -> None:
    owner_id = uuid4()
    other_owner_id = uuid4()
    owner_token, _ = JWTService(settings.auth).create_token_pair(owner_id)
    other_token, _ = JWTService(settings.auth).create_token_pair(other_owner_id)
    owner_headers = {'Authorization': f'Bearer {owner_token}'}
    other_headers = {'Authorization': f'Bearer {other_token}'}
    created_ids: list[UUID] = []
    async with async_session_factory() as session:
        session.add_all([User(id=owner_id, avatar_url=None), User(id=other_owner_id, avatar_url=None)])
        await session.commit()

    try:
        async with AsyncClient(transport=ASGITransport(app=app), base_url='http://test') as client:
            first_payload = deepcopy(valid_character_payload)
            first_payload['title'] = '  MiXeD Solo  '
            first = await client.post('/api/v1/characters/', json=first_payload, headers=owner_headers)
            assert first.status_code == 201
            first_id = UUID(first.json()['id'])
            created_ids.append(first_id)
            assert first.json()['title'] == 'MiXeD Solo'

            duplicate_payload = deepcopy(valid_character_payload)
            duplicate_payload['title'] = 'mixed solo'
            duplicate = await client.post('/api/v1/characters/', json=duplicate_payload, headers=owner_headers)
            assert duplicate.status_code == 409
            assert duplicate.json() == {'detail': 'Character title already exists'}

            other_owner_copy = await client.post(
                '/api/v1/characters/',
                json=duplicate_payload,
                headers=other_headers,
            )
            assert other_owner_copy.status_code == 201
            created_ids.append(UUID(other_owner_copy.json()['id']))

            second_payload = deepcopy(valid_character_payload)
            second_payload['title'] = 'Other Solo'
            second = await client.post('/api/v1/characters/', json=second_payload, headers=owner_headers)
            assert second.status_code == 201
            created_ids.append(UUID(second.json()['id']))

            case_only_payload = deepcopy(valid_character_payload)
            case_only_payload['title'] = 'MIXED SOLO'
            case_only = await client.put(
                f'/api/v1/characters/{first_id}/',
                json=case_only_payload,
                headers=owner_headers,
            )
            assert case_only.status_code == 200
            assert case_only.json()['title'] == 'MIXED SOLO'

            unchanged = await client.patch(
                f'/api/v1/characters/{first_id}/',
                json={'wallet': 777},
                headers=owner_headers,
            )
            assert unchanged.status_code == 200
            assert unchanged.json()['title'] == 'MIXED SOLO'

            trimmed = await client.patch(
                f'/api/v1/characters/{first_id}/',
                json={'title': '  Mixed Solo  '},
                headers=owner_headers,
            )
            assert trimmed.status_code == 200
            assert trimmed.json()['title'] == 'Mixed Solo'

            conflict = await client.patch(
                f'/api/v1/characters/{first_id}/',
                json={'title': 'other solo'},
                headers=owner_headers,
            )
            assert conflict.status_code == 409

            foreign_update = await client.patch(
                f'/api/v1/characters/{first_id}/',
                json={'title': 'Stolen'},
                headers=other_headers,
            )
            foreign_delete = await client.delete(
                f'/api/v1/characters/{first_id}/',
                headers=other_headers,
            )
            rename_endpoint = await client.patch(
                f'/api/v1/characters/{first_id}/rename/',
                json={'title': 'Nope'},
                headers=owner_headers,
            )
            unknown_delete = await client.delete(f'/api/v1/characters/{uuid4()}/', headers=owner_headers)

            assert foreign_update.status_code == 404
            assert foreign_delete.status_code == 404
            assert rename_endpoint.status_code == 404
            assert unknown_delete.status_code == 404

            deleted = await client.delete(f'/api/v1/characters/{first_id}/', headers=owner_headers)
            missing = await client.get(f'/api/v1/characters/{first_id}/', headers=owner_headers)

            assert deleted.status_code == 204
            assert deleted.content == b''
            assert missing.status_code == 404
    finally:
        async with async_session_factory() as session:
            await session.execute(delete(CharacterModel).where(CharacterModel.id.in_(created_ids)))
            await session.execute(delete(User).where(User.id.in_([owner_id, other_owner_id])))
            await session.commit()
        await engine.dispose()


@pytest.mark.anyio
async def test_application_routes_require_trailing_slashes() -> None:
    async with AsyncClient(transport=ASGITransport(app=app), base_url='http://test') as client:
        responses = [
            await client.get('/api/v1/health'),
            await client.get('/api/v1/auth/oauth/yandex/login'),
            await client.post('/api/v1/auth/refresh', json={'refresh_token': 'token'}),
            await client.get('/api/v1/characters'),
        ]

    assert all(response.status_code == 404 for response in responses)
    assert all('location' not in response.headers for response in responses)
