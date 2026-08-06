from copy import deepcopy

import pytest
from httpx import ASGITransport, AsyncClient

from main import app


@pytest.mark.anyio
async def test_characters_require_bearer_token() -> None:
    async with AsyncClient(transport=ASGITransport(app=app), base_url='http://test') as client:
        response = await client.get('/api/v1/characters/')

    assert response.status_code == 401
    assert response.json() == {'detail': 'Authentication required'}
    assert response.headers['www-authenticate'] == 'Bearer'


@pytest.mark.parametrize(
    ('field', 'value'),
    [
        ('wallet', '100'),
        ('wallet', 1.5),
        ('wallet', True),
        ('armor_head', {'base_value': -1, 'penalty': 0}),
        ('hp', {'current': 36, 'max_value': 35}),
        ('luck', {'current': 2, 'min_value': 3, 'max_value': 10}),
    ],
)
def test_create_schema_rejects_invalid_values(
    valid_character_payload: dict[str, object],
    field: str,
    value: object,
) -> None:
    from characters.schemas import CharacterCreateRequest

    payload = deepcopy(valid_character_payload)
    payload[field] = value

    with pytest.raises(ValueError):
        CharacterCreateRequest.model_validate(payload)


def test_create_schema_accepts_standard_character(valid_character_payload: dict[str, object]) -> None:
    from characters.schemas import CharacterCreateRequest

    request = CharacterCreateRequest.model_validate(valid_character_payload)

    assert request.luck.current == 5
    assert request.armor_head.base_value == 11
    assert request.hp.current == 35
