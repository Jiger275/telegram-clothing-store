"""
Product variant model for different sizes, colors, etc.
"""

from typing import List, TYPE_CHECKING

from sqlalchemy import String, Integer, ForeignKey
from sqlalchemy.orm import Mapped, mapped_column, relationship

from bot.database.base import Base

if TYPE_CHECKING:
    from .product import Product
    from .cart_item import CartItem
    from .order_item import OrderItem


class ProductVariant(Base):
    """
    Product variant model for different product options (size, color, etc.).

    Attributes:
        id: Primary key
        product_id: Foreign key to product
        size: Size variant (e.g., "S", "M", "L", "XL")
        color: Color variant (e.g., "Black", "White", "Red")
        quantity: Available quantity in stock
        sku: Stock Keeping Unit - unique identifier
    """
    __tablename__ = "product_variants"

    id: Mapped[int] = mapped_column(primary_key=True)
    product_id: Mapped[int] = mapped_column(ForeignKey("products.id"), nullable=False, index=True)
    size: Mapped[str | None] = mapped_column(String(50))
    color: Mapped[str | None] = mapped_column(String(100))
    quantity: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    sku: Mapped[str | None] = mapped_column(String(100), unique=True, index=True)

    # Relationships
    product: Mapped["Product"] = relationship(back_populates="variants")
    cart_items: Mapped[List["CartItem"]] = relationship(
        back_populates="variant",
        cascade="all, delete-orphan"
    )
    order_items: Mapped[List["OrderItem"]] = relationship(
        back_populates="variant",
        cascade="all, delete-orphan"
    )

    def __repr__(self) -> str:
        return f"<ProductVariant(id={self.id}, size={self.size}, color={self.color}, quantity={self.quantity})>"

    @property
    def is_available(self) -> bool:
        """Check if variant is available in stock"""
        return self.quantity > 0

    @property
    def display_name(self) -> str:
        """Generate a display name for the variant"""
        parts = []
        if self.size:
            parts.append(f"Size: {self.size}")
        if self.color:
            parts.append(f"Color: {self.color}")
        return ", ".join(parts) if parts else "Standard"
