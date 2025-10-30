"""
Product model for store items.
"""

from datetime import datetime
from decimal import Decimal
from typing import List, TYPE_CHECKING

from sqlalchemy import String, Boolean, DateTime, ForeignKey, Text, Numeric, JSON, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from bot.database.base import Base

if TYPE_CHECKING:
    from .category import Category
    from .product_variant import ProductVariant
    from .cart_item import CartItem
    from .order_item import OrderItem


class Product(Base):
    """
    Product model for store items.

    Attributes:
        id: Primary key
        category_id: Foreign key to category
        name: Product name
        description: Detailed product description
        price: Base product price
        discount_price: Optional discounted price
        images: JSON array of image filenames
        is_active: Visibility flag (shown in catalog)
        created_at: Creation timestamp
    """
    __tablename__ = "products"

    id: Mapped[int] = mapped_column(primary_key=True)
    category_id: Mapped[int] = mapped_column(ForeignKey("categories.id"), nullable=False, index=True)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[str | None] = mapped_column(Text)
    price: Mapped[Decimal] = mapped_column(Numeric(10, 2), nullable=False)
    discount_price: Mapped[Decimal | None] = mapped_column(Numeric(10, 2))
    images: Mapped[list] = mapped_column(JSON, default=list, nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False
    )

    # Relationships
    category: Mapped["Category"] = relationship(back_populates="products")
    variants: Mapped[List["ProductVariant"]] = relationship(
        back_populates="product",
        cascade="all, delete-orphan"
    )
    cart_items: Mapped[List["CartItem"]] = relationship(
        back_populates="product",
        cascade="all, delete-orphan"
    )
    order_items: Mapped[List["OrderItem"]] = relationship(
        back_populates="product",
        cascade="all, delete-orphan"
    )

    def __repr__(self) -> str:
        return f"<Product(id={self.id}, name={self.name}, price={self.price})>"

    @property
    def effective_price(self) -> Decimal:
        """Return the effective price (discount if available, otherwise regular price)"""
        return self.discount_price if self.discount_price else self.price
