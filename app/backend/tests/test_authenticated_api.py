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
            me = await client.get('/api/v1/users/me', headers={'Authorization': f'Bearer {access_token}'})
            refreshed = await client.post('/api/v1/auth/refresh', json={'refresh_token': refresh_token})
            wrong_type = await client.get(
                '/api/v1/users/me',
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
            update_payload.pop('title')
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
