from typing import Protocol, runtime_checkable

from sqlalchemy.exc import IntegrityError


@runtime_checkable
class PostgreSQLConstraintError(Protocol):
    @property
    def sqlstate(self) -> str: ...

    @property
    def constraint_name(self) -> str | None: ...


def postgresql_constraint_name(error: IntegrityError, *, sqlstate: str) -> str | None:
    cause = error.orig.__cause__ if error.orig is not None else None
    if isinstance(cause, PostgreSQLConstraintError) and cause.sqlstate == sqlstate:
        return cause.constraint_name
    return None
