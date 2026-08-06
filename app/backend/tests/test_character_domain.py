import pytest

from characters.entities import (
    ArmorValue,
    BoundedStat,
    HPValue,
    InvalidStatBoundsError,
    StatValueOutsideBoundsError,
)


@pytest.mark.parametrize('current', [3, 10])
def test_bounded_stat_accepts_inclusive_boundaries(current: int) -> None:
    stat = BoundedStat(current=current, min_value=3, max_value=10)

    assert stat.current == current


def test_bounded_stat_rejects_inverted_bounds() -> None:
    with pytest.raises(InvalidStatBoundsError):
        BoundedStat(current=5, min_value=10, max_value=3)


@pytest.mark.parametrize('current', [2, 11])
def test_bounded_stat_rejects_value_outside_bounds(current: int) -> None:
    with pytest.raises(StatValueOutsideBoundsError):
        BoundedStat(current=current, min_value=3, max_value=10)


@pytest.mark.parametrize(
    ('base_value', 'penalty'),
    [(-1, 0), (11, -1)],
)
def test_armor_rejects_negative_values(base_value: int, penalty: int) -> None:
    with pytest.raises(ValueError):
        ArmorValue(base_value=base_value, penalty=penalty)


@pytest.mark.parametrize(
    ('current', 'max_value'),
    [(-1, 35), (36, 35), (0, -1)],
)
def test_hp_rejects_invalid_values(current: int, max_value: int) -> None:
    with pytest.raises(ValueError):
        HPValue(current=current, max_value=max_value)
