"""
Base class for all database models.
Uses SQLAlchemy 2.0 DeclarativeBase with AsyncAttrs for async operations.
"""

from sqlalchemy.ext.asyncio import AsyncAttrs
from sqlalchemy.orm import DeclarativeBase


class Base(AsyncAttrs, DeclarativeBase):
    """
    Base class for all ORM models.

    Features:
    - AsyncAttrs: Enables awaitable attributes for lazy loading
    - DeclarativeBase: Modern SQLAlchemy 2.0 declarative mapping
    """
    pass
