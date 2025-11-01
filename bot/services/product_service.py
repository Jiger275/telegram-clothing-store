"""
Service for working with products
"""
from typing import List, Optional, Tuple
from decimal import Decimal

from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from bot.database.models.product import Product
from bot.database.models.product_variant import ProductVariant
from bot.utils.logger import setup_logger


logger = setup_logger(__name__)


async def get_products_by_category(
    session: AsyncSession,
    category_id: int,
    page: int = 1,
    page_size: int = 6,
    active_only: bool = True
) -> Tuple[List[Product], int]:
    """
    Get products by category with pagination

    Args:
        session: Database session
        category_id: Category ID
        page: Page number (starts from 1)
        page_size: Number of products per page
        active_only: Return only active products

    Returns:
        Tuple of (list of products, total count)
    """
    # Build base query
    query = select(Product).where(Product.category_id == category_id)

    if active_only:
        query = query.where(Product.is_active == True)

    # Get total count
    count_query = select(func.count()).select_from(query.subquery())
    total_count = await session.scalar(count_query) or 0

    # Apply pagination
    offset = (page - 1) * page_size
    query = query.offset(offset).limit(page_size)
    query = query.order_by(Product.created_at.desc())

    # Load variants for checking if product has variants
    query = query.options(selectinload(Product.variants))

    # Execute query
    result = await session.execute(query)
    products = result.scalars().all()

    logger.debug(
        f"Found {len(products)} products for category {category_id} "
        f"(page {page}, total {total_count})"
    )

    return list(products), total_count


async def get_product_by_id(
    session: AsyncSession,
    product_id: int,
    with_variants: bool = True
) -> Optional[Product]:
    """
    Get product by ID

    Args:
        session: Database session
        product_id: Product ID
        with_variants: Load product variants

    Returns:
        Product object or None if not found
    """
    query = select(Product).where(Product.id == product_id)

    if with_variants:
        query = query.options(selectinload(Product.variants))

    result = await session.execute(query)
    product = result.scalar_one_or_none()

    if product:
        logger.debug(f"Found product: {product.name} (id={product_id})")
    else:
        logger.warning(f"Product not found: id={product_id}")

    return product


async def get_product_variants(
    session: AsyncSession,
    product_id: int
) -> List[ProductVariant]:
    """
    Get all variants for a product

    Args:
        session: Database session
        product_id: Product ID

    Returns:
        List of ProductVariant objects
    """
    query = select(ProductVariant).where(
        ProductVariant.product_id == product_id
    ).order_by(ProductVariant.size, ProductVariant.color)

    result = await session.execute(query)
    variants = result.scalars().all()

    logger.debug(f"Found {len(variants)} variants for product {product_id}")

    return list(variants)


async def get_available_sizes(
    session: AsyncSession,
    product_id: int
) -> List[str]:
    """
    Get list of available sizes for a product

    Args:
        session: Database session
        product_id: Product ID

    Returns:
        List of unique sizes
    """
    query = select(ProductVariant.size).where(
        ProductVariant.product_id == product_id,
        ProductVariant.quantity > 0
    ).distinct().order_by(ProductVariant.size)

    result = await session.execute(query)
    sizes = result.scalars().all()

    return list(sizes)


async def get_available_colors(
    session: AsyncSession,
    product_id: int,
    size: Optional[str] = None
) -> List[str]:
    """
    Get list of available colors for a product (optionally filtered by size)

    Args:
        session: Database session
        product_id: Product ID
        size: Optional size filter

    Returns:
        List of unique colors
    """
    query = select(ProductVariant.color).where(
        ProductVariant.product_id == product_id,
        ProductVariant.quantity > 0
    )

    if size:
        query = query.where(ProductVariant.size == size)

    query = query.distinct().order_by(ProductVariant.color)

    result = await session.execute(query)
    colors = result.scalars().all()

    return list(colors)


async def get_variant_by_attributes(
    session: AsyncSession,
    product_id: int,
    size: Optional[str] = None,
    color: Optional[str] = None
) -> Optional[ProductVariant]:
    """
    Get product variant by size and color

    Args:
        session: Database session
        product_id: Product ID
        size: Size
        color: Color

    Returns:
        ProductVariant object or None if not found
    """
    query = select(ProductVariant).where(
        ProductVariant.product_id == product_id
    )

    if size:
        query = query.where(ProductVariant.size == size)
    if color:
        query = query.where(ProductVariant.color == color)

    result = await session.execute(query)
    variant = result.scalar_one_or_none()

    if variant:
        logger.debug(
            f"Found variant for product {product_id}: "
            f"size={size}, color={color}, quantity={variant.quantity}"
        )
    else:
        logger.warning(
            f"Variant not found for product {product_id}: "
            f"size={size}, color={color}"
        )

    return variant


async def check_product_availability(
    session: AsyncSession,
    product_id: int,
    size: Optional[str] = None,
    color: Optional[str] = None
) -> bool:
    """
    Check if product/variant is available in stock

    Args:
        session: Database session
        product_id: Product ID
        size: Optional size
        color: Optional color

    Returns:
        True if available, False otherwise
    """
    variant = await get_variant_by_attributes(
        session=session,
        product_id=product_id,
        size=size,
        color=color
    )

    return variant is not None and variant.quantity > 0


async def get_product_total_quantity(
    session: AsyncSession,
    product_id: int
) -> int:
    """
    Get total quantity across all variants

    Args:
        session: Database session
        product_id: Product ID

    Returns:
        Total quantity
    """
    query = select(func.sum(ProductVariant.quantity)).where(
        ProductVariant.product_id == product_id
    )

    result = await session.execute(query)
    total = result.scalar() or 0

    return int(total)


async def search_products(
    session: AsyncSession,
    search_query: str,
    page: int = 1,
    page_size: int = 10,
    active_only: bool = True
) -> Tuple[List[Product], int]:
    """
    Search products by name or description

    Args:
        session: Database session
        search_query: Search string
        page: Page number
        page_size: Products per page
        active_only: Return only active products

    Returns:
        Tuple of (list of products, total count)
    """
    search_pattern = f"%{search_query}%"

    query = select(Product).where(
        (Product.name.ilike(search_pattern)) |
        (Product.description.ilike(search_pattern))
    )

    if active_only:
        query = query.where(Product.is_active == True)

    # Get total count
    count_query = select(func.count()).select_from(query.subquery())
    total_count = await session.scalar(count_query) or 0

    # Apply pagination
    offset = (page - 1) * page_size
    query = query.offset(offset).limit(page_size)
    query = query.order_by(Product.name)

    # Execute query
    result = await session.execute(query)
    products = result.scalars().all()

    logger.debug(
        f"Search '{search_query}': found {len(products)} products "
        f"(page {page}, total {total_count})"
    )

    return list(products), total_count


def format_price(price: Decimal) -> str:
    """
    Format price for display

    Args:
        price: Price as Decimal

    Returns:
        Formatted price string
    """
    return f"{price:,.2f} ₽"


def get_product_images_paths(product: Product, base_path: str = "media/products") -> List[str]:
    """
    Get full paths to product images

    Args:
        product: Product object
        base_path: Base path to images directory

    Returns:
        List of full image paths
    """
    if not product.images:
        return []

    return [f"{base_path}/{img}" for img in product.images]
