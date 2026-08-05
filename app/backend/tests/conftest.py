import os

import pytest

os.environ.setdefault(
    'DATABASE_URL',
    'postgresql+asyncpg://redid:redid@localhost:5432/redid',
)


@pytest.fixture
def anyio_backend() -> str:
    return 'asyncio'
