"""
Order item model for individual items in an order.
"""

from decimal import Decimal
from typing import TYPE_CHECKING

from sqlalchemy import Integer, ForeignKey, Numeric
from sqlalchemy.orm import Mapped, mapped_column, relationship

from bot.database.base import Base

if TYPE_CHECKING:
    from .order import Order
    from .product import Product
    from .product_variant import ProductVariant


class OrderItem(Base):
    """
    Order item model representing individual products in an order.

    Attributes:
        id: Primary key
        order_id: Foreign key to order
        product_id: Foreign key to product
        variant_id: Foreign key to product variant (optional)
        quantity: Number of items ordered
        price_at_purchase: Price per item at time of purchase
        subtotal: Total for this line item (quantity * price_at_purchase)
    """
    __tablename__ = "order_items"

    id: Mapped[int] = mapped_column(primary_key=True)
    order_id: Mapped[int] = mapped_column(ForeignKey("orders.id"), nullable=False, index=True)
    product_id: Mapped[int] = mapped_column(ForeignKey("products.id"), nullable=False, index=True)
    variant_id: Mapped[int | None] = mapped_column(ForeignKey("product_variants.id"), index=True)
    quantity: Mapped[int] = mapped_column(Integer, nullable=False)
    price_at_purchase: Mapped[Decimal] = mapped_column(Numeric(10, 2), nullable=False)
    subtotal: Mapped[Decimal] = mapped_column(Numeric(10, 2), nullable=False)

    # Relationships
    order: Mapped["Order"] = relationship(back_populates="items")
    product: Mapped["Product"] = relationship(back_populates="order_items")
    variant: Mapped["ProductVariant | None"] = relationship(back_populates="order_items")

    def __repr__(self) -> str:
        return f"<OrderItem(id={self.id}, order_id={self.order_id}, product_id={self.product_id}, quantity={self.quantity}, subtotal={self.subtotal})>"
