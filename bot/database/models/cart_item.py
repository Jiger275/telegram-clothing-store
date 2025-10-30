"""
Cart item model for shopping cart functionality.
"""

from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import Integer, ForeignKey, DateTime, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from bot.database.base import Base

if TYPE_CHECKING:
    from .user import User
    from .product import Product
    from .product_variant import ProductVariant


class CartItem(Base):
    """
    Shopping cart item model.

    Attributes:
        id: Primary key
        user_id: Foreign key to user
        product_id: Foreign key to product
        variant_id: Foreign key to product variant (optional)
        quantity: Number of items
        added_at: Timestamp when item was added to cart
    """
    __tablename__ = "cart_items"

    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), nullable=False, index=True)
    product_id: Mapped[int] = mapped_column(ForeignKey("products.id"), nullable=False, index=True)
    variant_id: Mapped[int | None] = mapped_column(ForeignKey("product_variants.id"), index=True)
    quantity: Mapped[int] = mapped_column(Integer, default=1, nullable=False)
    added_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False
    )

    # Relationships
    user: Mapped["User"] = relationship(back_populates="cart_items")
    product: Mapped["Product"] = relationship(back_populates="cart_items")
    variant: Mapped["ProductVariant | None"] = relationship(back_populates="cart_items")

    def __repr__(self) -> str:
        return f"<CartItem(id={self.id}, user_id={self.user_id}, product_id={self.product_id}, quantity={self.quantity})>"
