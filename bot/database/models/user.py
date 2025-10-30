"""
User model for storing Telegram bot users.
"""

from datetime import datetime
from typing import List, TYPE_CHECKING

from sqlalchemy import BigInteger, String, Boolean, DateTime, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from bot.database.base import Base

if TYPE_CHECKING:
    from .cart_item import CartItem
    from .order import Order


class User(Base):
    """
    User model representing bot users.

    Attributes:
        id: Primary key
        telegram_id: Unique Telegram user ID
        username: Telegram username (optional)
        full_name: User's full name
        is_admin: Admin privileges flag
        created_at: Registration timestamp
        updated_at: Last update timestamp
    """
    __tablename__ = "users"

    id: Mapped[int] = mapped_column(primary_key=True)
    telegram_id: Mapped[int] = mapped_column(BigInteger, unique=True, index=True, nullable=False)
    username: Mapped[str | None] = mapped_column(String(255))
    full_name: Mapped[str] = mapped_column(String(255), nullable=False)
    is_admin: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False
    )

    # Relationships
    cart_items: Mapped[List["CartItem"]] = relationship(
        back_populates="user",
        cascade="all, delete-orphan"
    )
    orders: Mapped[List["Order"]] = relationship(
        back_populates="user",
        cascade="all, delete-orphan"
    )

    def __repr__(self) -> str:
        return f"<User(id={self.id}, telegram_id={self.telegram_id}, username={self.username})>"
