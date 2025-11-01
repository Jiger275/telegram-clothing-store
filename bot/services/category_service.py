"""
Service for working with product categories
"""
from typing import List, Optional

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from bot.database.models.category import Category
from bot.utils.logger import setup_logger


logger = setup_logger(__name__)


async def get_all_categories(
    session: AsyncSession,
    parent_id: Optional[int] = None,
    active_only: bool = True
) -> List[Category]:
    """
    Get all categories, optionally filtered by parent_id

    Args:
        session: Database session
        parent_id: Parent category ID (None for root categories)
        active_only: Return only active categories

    Returns:
        List of Category objects
    """
    query = select(Category).where(Category.parent_id == parent_id)

    if active_only:
        query = query.where(Category.is_active == True)

    # Загружаем родительскую категорию заранее
    query = query.options(selectinload(Category.parent))
    query = query.order_by(Category.name)

    result = await session.execute(query)
    categories = result.scalars().all()

    logger.debug(
        f"Found {len(categories)} categories "
        f"(parent_id={parent_id}, active_only={active_only})"
    )

    return list(categories)


async def get_category_by_id(
    session: AsyncSession,
    category_id: int,
    with_subcategories: bool = False
) -> Optional[Category]:
    """
    Get category by ID

    Args:
        session: Database session
        category_id: Category ID
        with_subcategories: Load subcategories

    Returns:
        Category object or None if not found
    """
    query = select(Category).where(Category.id == category_id)

    # Всегда загружаем родительскую категорию
    query = query.options(selectinload(Category.parent))

    if with_subcategories:
        query = query.options(selectinload(Category.subcategories))

    result = await session.execute(query)
    category = result.scalar_one_or_none()

    if category:
        logger.debug(f"Found category: {category.name} (id={category_id})")
    else:
        logger.warning(f"Category not found: id={category_id}")

    return category


async def get_root_categories(
    session: AsyncSession,
    active_only: bool = True
) -> List[Category]:
    """
    Get all root categories (categories without parent)

    Args:
        session: Database session
        active_only: Return only active categories

    Returns:
        List of root Category objects
    """
    return await get_all_categories(
        session=session,
        parent_id=None,
        active_only=active_only
    )


async def get_subcategories(
    session: AsyncSession,
    parent_id: int,
    active_only: bool = True
) -> List[Category]:
    """
    Get all subcategories for a parent category

    Args:
        session: Database session
        parent_id: Parent category ID
        active_only: Return only active categories

    Returns:
        List of Category objects
    """
    return await get_all_categories(
        session=session,
        parent_id=parent_id,
        active_only=active_only
    )


async def has_subcategories(
    session: AsyncSession,
    category_id: int
) -> bool:
    """
    Check if category has subcategories

    Args:
        session: Database session
        category_id: Category ID

    Returns:
        True if has subcategories, False otherwise
    """
    subcategories = await get_subcategories(
        session=session,
        parent_id=category_id,
        active_only=True
    )
    return len(subcategories) > 0


async def get_category_breadcrumbs(
    session: AsyncSession,
    category_id: int
) -> List[Category]:
    """
    Get breadcrumb trail for a category (path from root to this category)

    Args:
        session: Database session
        category_id: Category ID

    Returns:
        List of Category objects from root to current
    """
    breadcrumbs = []
    current_category = await get_category_by_id(session, category_id)

    while current_category:
        breadcrumbs.insert(0, current_category)
        if current_category.parent_id:
            current_category = await get_category_by_id(session, current_category.parent_id)
        else:
            break

    logger.debug(
        f"Breadcrumbs for category {category_id}: "
        f"{' > '.join([c.name for c in breadcrumbs])}"
    )

    return breadcrumbs


async def count_products_in_category(
    session: AsyncSession,
    category_id: int,
    active_only: bool = True
) -> int:
    """
    Count products in a category

    Args:
        session: Database session
        category_id: Category ID
        active_only: Count only active products

    Returns:
        Number of products
    """
    from bot.database.models.product import Product

    query = select(Product).where(Product.category_id == category_id)

    if active_only:
        query = query.where(Product.is_active == True)

    result = await session.execute(query)
    products = result.scalars().all()

    count = len(products)
    logger.debug(f"Category {category_id} has {count} products")

    return count
