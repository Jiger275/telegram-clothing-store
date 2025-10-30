"""
Category model for product categorization.
"""

from datetime import datetime
from typing import List, TYPE_CHECKING, Optional

from sqlalchemy import String, Boolean, DateTime, ForeignKey, Text, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from bot.database.base import Base

if TYPE_CHECKING:
    from .product import Product


class Category(Base):
    """
    Product category model with hierarchical structure support.

    Attributes:
        id: Primary key
        name: Category name
        description: Optional category description
        parent_id: Reference to parent category for subcategories
        is_active: Visibility flag
        created_at: Creation timestamp
    """
    __tablename__ = "categories"

    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[str | None] = mapped_column(Text)
    parent_id: Mapped[int | None] = mapped_column(ForeignKey("categories.id"))
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False
    )

    # Self-referential relationship for hierarchical categories
    parent: Mapped[Optional["Category"]] = relationship(
        "Category",
        remote_side="Category.id",
        back_populates="subcategories"
    )
    subcategories: Mapped[List["Category"]] = relationship(
        "Category",
        back_populates="parent",
        cascade="all, delete-orphan"
    )

    # Products in this category
    products: Mapped[List["Product"]] = relationship(
        back_populates="category",
        cascade="all, delete-orphan"
    )

    def __repr__(self) -> str:
        return f"<Category(id={self.id}, name={self.name}, is_active={self.is_active})>"
