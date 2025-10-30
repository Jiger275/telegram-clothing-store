"""
Order model for customer orders.
"""

from datetime import datetime
from decimal import Decimal
from enum import Enum
from typing import List, TYPE_CHECKING

from sqlalchemy import String, DateTime, Numeric, ForeignKey, Text, func, Enum as SQLEnum
from sqlalchemy.orm import Mapped, mapped_column, relationship

from bot.database.base import Base

if TYPE_CHECKING:
    from .user import User
    from .order_item import OrderItem


class OrderStatus(str, Enum):
    """Order status enum"""
    NEW = "new"
    PROCESSING = "processing"
    CONFIRMED = "confirmed"
    PREPARING = "preparing"
    READY = "ready"
    DELIVERING = "delivering"
    DELIVERED = "delivered"
    CANCELLED = "cancelled"


class DeliveryType(str, Enum):
    """Delivery type enum"""
    COURIER = "courier"
    PICKUP = "pickup"


class Order(Base):
    """
    Order model for customer purchases.

    Attributes:
        id: Primary key
        user_id: Foreign key to user
        order_number: Unique order number (e.g., "ORD-20231130-001")
        total_amount: Total order amount
        status: Order status
        customer_name: Recipient name
        customer_phone: Contact phone number
        delivery_type: Delivery method (courier or pickup)
        delivery_address: Delivery address (for courier)
        comment: Optional customer comment
        created_at: Order creation timestamp
        updated_at: Last update timestamp
    """
    __tablename__ = "orders"

    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), nullable=False, index=True)
    order_number: Mapped[str] = mapped_column(String(50), unique=True, nullable=False, index=True)
    total_amount: Mapped[Decimal] = mapped_column(Numeric(10, 2), nullable=False)
    status: Mapped[OrderStatus] = mapped_column(
        SQLEnum(OrderStatus),
        default=OrderStatus.NEW,
        nullable=False
    )
    customer_name: Mapped[str] = mapped_column(String(255), nullable=False)
    customer_phone: Mapped[str] = mapped_column(String(50), nullable=False)
    delivery_type: Mapped[DeliveryType] = mapped_column(
        SQLEnum(DeliveryType),
        nullable=False
    )
    delivery_address: Mapped[str | None] = mapped_column(Text)
    comment: Mapped[str | None] = mapped_column(Text)
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
    user: Mapped["User"] = relationship(back_populates="orders")
    items: Mapped[List["OrderItem"]] = relationship(
        back_populates="order",
        cascade="all, delete-orphan"
    )

    def __repr__(self) -> str:
        return f"<Order(id={self.id}, order_number={self.order_number}, status={self.status}, total={self.total_amount})>"
