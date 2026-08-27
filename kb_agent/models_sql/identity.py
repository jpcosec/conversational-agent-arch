from __future__ import annotations

from datetime import datetime

from sqlalchemy import Boolean, CheckConstraint, DateTime, Float, ForeignKey, String, func
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship


class Base(DeclarativeBase):
    """Base declarativa para los modelos SQL del agente."""


class Users(Base):
    __tablename__ = "users"

    id: Mapped[int] = mapped_column(primary_key=True)
    external_id: Mapped[str] = mapped_column(String, unique=True, nullable=False)
    channel: Mapped[str] = mapped_column(String, nullable=False)
    # Enrolamiento (fase 4): si la persona ya esta inscrita en el programa.
    # Los usuarios sembrados por el PSP (wa-*, web-anon-*) vienen inscritos;
    # cualquier usuario nuevo -- incluidos los de la UI de desarrollo (ui:*) --
    # arranca en False hasta pasar por step-antonia-enrolamiento.
    enrolled: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
    )

    traits: Mapped[list[UserTraits]] = relationship(
        back_populates="user",
        cascade="all, delete-orphan",
    )


class UserTraits(Base):
    __tablename__ = "user_traits"
    __table_args__ = (
        CheckConstraint(
            "confidence >= 0 AND confidence <= 1",
            name="ck_user_traits_confidence_between_0_and_1",
        ),
    )

    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), primary_key=True)
    trait_id: Mapped[str] = mapped_column(String, primary_key=True)
    confidence: Mapped[float] = mapped_column(Float, nullable=False)
    source: Mapped[str] = mapped_column(String, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
    )

    user: Mapped[Users] = relationship(back_populates="traits")
