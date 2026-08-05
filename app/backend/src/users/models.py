from datetime import datetime
from uuid import UUID, uuid4

from sqlalchemy import DateTime, ForeignKey, String, UniqueConstraint, func
from sqlalchemy.dialects.postgresql import UUID as POSTGRESQL_UUID
from sqlalchemy.orm import Mapped, mapped_column

from database import Base


class User(Base):
    __tablename__ = 'users'

    id: Mapped[UUID] = mapped_column(POSTGRESQL_UUID(as_uuid=True), primary_key=True, default=uuid4)
    avatar_url: Mapped[str | None] = mapped_column(String(2048))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )


class OAuthAccount(Base):
    __tablename__ = 'oauth_accounts'
    __table_args__ = (
        UniqueConstraint(
            'provider',
            'provider_user_id',
            name='uq_oauth_accounts_provider_identity',
        ),
        UniqueConstraint('user_id', 'provider', name='uq_oauth_accounts_user_provider'),
    )

    id: Mapped[UUID] = mapped_column(POSTGRESQL_UUID(as_uuid=True), primary_key=True, default=uuid4)
    user_id: Mapped[UUID] = mapped_column(
        POSTGRESQL_UUID(as_uuid=True),
        ForeignKey('users.id', ondelete='CASCADE'),
        nullable=False,
    )
    provider: Mapped[str] = mapped_column(String(32), nullable=False)
    provider_user_id: Mapped[str] = mapped_column(String(255), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
