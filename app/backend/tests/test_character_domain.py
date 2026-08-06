from uuid import uuid4

import pytest

from characters.entities import (
    ArmorValue,
    BoundedStat,
    Character,
    HPValue,
    InvalidStatBoundsError,
    StatValueOutsideBoundsError,
)


def _character(title: str = 'Solo') -> Character:
    stat = BoundedStat(current=5, min_value=0, max_value=10)
    armor = ArmorValue(base_value=0, penalty=0)
    return Character(
        id=uuid4(),
        owner_id=uuid4(),
        title=title,
        role='Solo',
        wallet=0,
        luck=stat,
        intelligence=stat,
        reflexes=stat,
        dexterity=stat,
        cool=stat,
        empathy=stat,
        willpower=stat,
        technic=stat,
        body=stat,
        movement=stat,
        armor_head=armor,
        armor_body=armor,
        armor_shield=armor,
        hp=HPValue(current=10, max_value=20),
        heavy_wounds_threshold=10,
        reputation=0,
        humanity=0,
        upgrade_points=0,
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


def test_character_strips_title_edges_and_preserves_display_case() -> None:
    character = _character('  SoLo  ')

    assert character.title == 'SoLo'


@pytest.mark.parametrize('title', ['', '   '])
def test_character_rejects_empty_normalized_title(title: str) -> None:
    with pytest.raises(ValueError, match='title'):
        _character(title)


@pytest.mark.parametrize(
    ('field', 'value'),
    [
        ('heavy_wounds_threshold', -1),
        ('heavy_wounds_threshold', 21),
        ('reputation', -1),
        ('humanity', -1),
        ('upgrade_points', -1),
    ],
)
def test_character_rejects_invalid_editable_invariants(field: str, value: int) -> None:
    character_data = {
        'heavy_wounds_threshold': 10,
        'reputation': 0,
        'humanity': 0,
        'upgrade_points': 0,
    }
    character_data[field] = value
    character = _character()

    with pytest.raises(ValueError):
        character.replace_editable_state(
            title=character.title,
            role=character.role,
            wallet=character.wallet,
            luck=character.luck,
            intelligence=character.intelligence,
            reflexes=character.reflexes,
            dexterity=character.dexterity,
            cool=character.cool,
            empathy=character.empathy,
            willpower=character.willpower,
            technic=character.technic,
            body=character.body,
            movement=character.movement,
            armor_head=character.armor_head,
            armor_body=character.armor_body,
            armor_shield=character.armor_shield,
            hp=character.hp,
            **character_data,
        )
