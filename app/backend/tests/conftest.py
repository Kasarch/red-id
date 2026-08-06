import os

import pytest
from pydantic import SecretStr

from config import AuthSettings

os.environ.setdefault(
    'DATABASE_URL',
    'postgresql+asyncpg://redid:redid@localhost:5432/redid',
)


@pytest.fixture
def anyio_backend() -> str:
    return 'asyncio'


@pytest.fixture
def auth_settings() -> AuthSettings:
    return AuthSettings(
        jwt_secret=SecretStr('test-jwt-secret-with-at-least-sixty-four-characters-for-hmac-tests'),
        state_secret=SecretStr('test-state-secret-with-at-least-sixty-four-characters-for-tests'),
        access_token_ttl_minutes=15,
        refresh_token_ttl_days=30,
        state_ttl_minutes=10,
    )


@pytest.fixture
def valid_character_payload() -> dict[str, object]:
    stat = {'current': 5, 'min_value': 3, 'max_value': 10}
    armor = {'base_value': 11, 'penalty': 0}
    return {
        'title': 'Solo',
        'role': 'Solo',
        'wallet': 100,
        'luck': stat.copy(),
        'intelligence': stat.copy(),
        'reflexes': stat.copy(),
        'dexterity': stat.copy(),
        'cool': stat.copy(),
        'empathy': stat.copy(),
        'willpower': stat.copy(),
        'technic': stat.copy(),
        'body': stat.copy(),
        'movement': stat.copy(),
        'armor_head': armor.copy(),
        'armor_body': armor.copy(),
        'armor_shield': armor.copy(),
        'hp': {'current': 35, 'max_value': 35},
        'heavy_wounds_threshold': 17,
        'reputation': 0,
        'humanity': 50,
        'upgrade_points': 0,
    }
