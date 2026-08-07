from dataclasses import dataclass
from enum import StrEnum
from uuid import UUID


class CharacterStatName(StrEnum):
    LUCK = 'luck'
    INTELLIGENCE = 'intelligence'
    REFLEXES = 'reflexes'
    DEXTERITY = 'dexterity'
    COOL = 'cool'
    EMPATHY = 'empathy'
    WILLPOWER = 'willpower'
    TECHNIC = 'technic'
    BODY = 'body'
    MOVEMENT = 'movement'


class InvalidStatBoundsError(ValueError):
    pass


class StatValueOutsideBoundsError(ValueError):
    pass


@dataclass(slots=True, frozen=True)
class BoundedStat:
    current: int
    min_value: int
    max_value: int

    def __post_init__(self) -> None:
        self._validate(self.current, self.min_value, self.max_value)

    def with_current(self, new_current: int) -> 'BoundedStat':
        self._validate(new_current, self.min_value, self.max_value)
        return BoundedStat(current=new_current, min_value=self.min_value, max_value=self.max_value)

    @staticmethod
    def _validate(current: int, min_value: int, max_value: int) -> None:
        if min_value > max_value:
            raise InvalidStatBoundsError(f'Min value {min_value} cannot be greater than max value {max_value}')

        if not (min_value <= current <= max_value):
            raise StatValueOutsideBoundsError(f'Current value {current} is out of bounds [{min_value}, {max_value}]')


@dataclass(slots=True, frozen=True)
class ArmorValue:
    base_value: int
    penalty: int

    def __post_init__(self) -> None:
        self._validate_value(self.base_value)
        self._validate_penalty(self.penalty)

    def with_penalty(self, new_penalty: int) -> 'ArmorValue':
        return ArmorValue(base_value=self.base_value, penalty=new_penalty)

    @staticmethod
    def _validate_value(value: int) -> None:
        if value < 0:
            raise ValueError(f'Base value {value} cannot be negative')

    @staticmethod
    def _validate_penalty(penalty: int) -> None:
        if penalty < 0:
            raise ValueError(f'Penalty {penalty} cannot be negative')


@dataclass(slots=True, frozen=True)
class HPValue:
    current: int
    max_value: int

    def __post_init__(self) -> None:
        self._validate(self.current, self.max_value)

    def with_current(self, new_current: int) -> 'HPValue':
        self._validate(new_current, self.max_value)
        return HPValue(current=new_current, max_value=self.max_value)

    def with_max(self, new_max: int) -> 'HPValue':
        self._validate(self.current, new_max)
        return HPValue(current=self.current, max_value=new_max)

    @staticmethod
    def _validate(current: int, max_value: int) -> None:
        if max_value < 0:
            raise ValueError(f'Max value {max_value} cannot be negative')

        if not (0 <= current <= max_value):
            raise ValueError(f'Current value {current} is out of bounds [0, {max_value}]')


@dataclass(slots=True, kw_only=True)
class Character:
    id: UUID
    owner_id: UUID
    title: str
    role: str
    wallet: int

    luck: BoundedStat
    intelligence: BoundedStat
    reflexes: BoundedStat
    dexterity: BoundedStat
    cool: BoundedStat
    empathy: BoundedStat
    willpower: BoundedStat
    technic: BoundedStat
    body: BoundedStat
    movement: BoundedStat

    armor_head: ArmorValue
    armor_body: ArmorValue
    armor_shield: ArmorValue

    hp: HPValue
    heavy_wounds_threshold: int
    reputation: int
    humanity: int
    upgrade_points: int

    def __post_init__(self) -> None:
        normalized_title = self._normalize_title(self.title)
        if not normalized_title:
            raise ValueError('Character title cannot be empty or whitespace.')
        self.title = normalized_title

        self._validate_editable_state(
            hp=self.hp,
            heavy_wounds_threshold=self.heavy_wounds_threshold,
            reputation=self.reputation,
            humanity=self.humanity,
            upgrade_points=self.upgrade_points,
        )

    def replace_editable_state(
        self,
        *,
        title: str,
        role: str,
        wallet: int,
        luck: BoundedStat,
        intelligence: BoundedStat,
        reflexes: BoundedStat,
        dexterity: BoundedStat,
        cool: BoundedStat,
        empathy: BoundedStat,
        willpower: BoundedStat,
        technic: BoundedStat,
        body: BoundedStat,
        movement: BoundedStat,
        armor_head: ArmorValue,
        armor_body: ArmorValue,
        armor_shield: ArmorValue,
        hp: HPValue,
        heavy_wounds_threshold: int,
        reputation: int,
        humanity: int,
        upgrade_points: int,
    ) -> None:
        normalized_title = self._normalize_title(title)
        if not normalized_title:
            raise ValueError('Character title cannot be empty or whitespace.')
        self._validate_editable_state(
            hp=hp,
            heavy_wounds_threshold=heavy_wounds_threshold,
            reputation=reputation,
            humanity=humanity,
            upgrade_points=upgrade_points,
        )
        self.title = normalized_title
        self.role = role
        self.wallet = wallet
        self.luck = luck
        self.intelligence = intelligence
        self.reflexes = reflexes
        self.dexterity = dexterity
        self.cool = cool
        self.empathy = empathy
        self.willpower = willpower
        self.technic = technic
        self.body = body
        self.movement = movement
        self.armor_head = armor_head
        self.armor_body = armor_body
        self.armor_shield = armor_shield
        self.hp = hp
        self.heavy_wounds_threshold = heavy_wounds_threshold
        self.reputation = reputation
        self.humanity = humanity
        self.upgrade_points = upgrade_points

    @staticmethod
    def _validate_editable_state(
        *,
        hp: HPValue,
        heavy_wounds_threshold: int,
        reputation: int,
        humanity: int,
        upgrade_points: int,
    ) -> None:
        if heavy_wounds_threshold < 0 or heavy_wounds_threshold > hp.max_value:
            raise ValueError('Heavy wounds threshold is out of bounds.')
        if reputation < 0:
            raise ValueError('Reputation cannot be negative.')
        if humanity < 0:
            raise ValueError('Humanity cannot be negative.')
        if upgrade_points < 0:
            raise ValueError('Upgrade points cannot be negative.')

    @staticmethod
    def _normalize_title(title: str) -> str:
        return title.strip()
