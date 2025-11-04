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

    # Всегда загружаем категорию, чтобы избежать lazy loading
    query = query.options(selectinload(Product.category))

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


# ===== Admin functions =====


async def get_all_products(
    session: AsyncSession,
    page: int = 1,
    page_size: int = 10,
    category_id: Optional[int] = None,
    active_only: Optional[bool] = None
) -> Tuple[List[Product], int]:
    """
    Get all products with filters (for admin panel)

    Args:
        session: Database session
        page: Page number
        page_size: Products per page
        category_id: Optional category filter (includes child categories)
        active_only: Optional activity filter (None = all products)

    Returns:
        Tuple of (list of products, total count)
    """
    from bot.services import category_service

    query = select(Product)

    # Apply filters
    if category_id is not None:
        # Получаем ID категории и всех её дочерних категорий
        category_ids = await category_service.get_category_with_children_ids(session, category_id)
        query = query.where(Product.category_id.in_(category_ids))

    if active_only is not None:
        query = query.where(Product.is_active == active_only)

    # Get total count
    count_query = select(func.count()).select_from(query.subquery())
    total_count = await session.scalar(count_query) or 0

    # Apply pagination
    offset = (page - 1) * page_size
    query = query.offset(offset).limit(page_size)
    query = query.order_by(Product.created_at.desc())

    # Load relationships
    query = query.options(selectinload(Product.category), selectinload(Product.variants))

    # Execute query
    result = await session.execute(query)
    products = result.scalars().all()

    if category_id is not None:
        logger.debug(
            f"Found {len(products)} products (page {page}, total {total_count}, "
            f"category={category_id} with children={category_ids}, active={active_only})"
        )
    else:
        logger.debug(
            f"Found {len(products)} products (page {page}, total {total_count}, "
            f"category=all, active={active_only})"
        )

    return list(products), total_count


async def create_product(
    session: AsyncSession,
    category_id: int,
    name: str,
    description: Optional[str],
    price: Decimal,
    images: List[str],
    discount_price: Optional[Decimal] = None,
    is_active: bool = True
) -> Product:
    """
    Create a new product

    Args:
        session: Database session
        category_id: Category ID
        name: Product name
        description: Product description
        price: Product price
        images: List of image filenames
        discount_price: Optional discount price
        is_active: Product visibility

    Returns:
        Created Product object
    """
    try:
        product = Product(
            category_id=category_id,
            name=name,
            description=description,
            price=price,
            discount_price=discount_price,
            images=images,
            is_active=is_active
        )

        session.add(product)
        await session.commit()

        # Загружаем товар с relationships, чтобы избежать lazy loading
        product = await get_product_by_id(session, product.id, with_variants=True)

        logger.info(
            f"✅ [DB] Товар создан: '{product.name}' (ID={product.id}, category_id={category_id}, "
            f"цена={price}, изображений={len(images)})"
        )
        return product
    except Exception as e:
        logger.exception(f"❌ [DB] ОШИБКА при создании товара '{name}': {e}")
        raise


async def update_product(
    session: AsyncSession,
    product_id: int,
    **kwargs
) -> Optional[Product]:
    """
    Update product fields

    Args:
        session: Database session
        product_id: Product ID
        **kwargs: Fields to update (name, description, price, etc.)

    Returns:
        Updated Product object or None if not found
    """
    product = await get_product_by_id(session, product_id, with_variants=False)
    if not product:
        logger.warning(f"[DB] Попытка обновления несуществующего товара ID={product_id}")
        return None

    # Update allowed fields
    allowed_fields = {
        'category_id', 'name', 'description', 'price',
        'discount_price', 'images', 'is_active'
    }

    updated_fields = []
    for key, value in kwargs.items():
        if key in allowed_fields and value is not None:
            old_value = getattr(product, key)
            setattr(product, key, value)
            updated_fields.append(f"{key}: {old_value} → {value}")

    await session.commit()

    # Перезагружаем товар с relationships, чтобы избежать lazy loading
    product = await get_product_by_id(session, product_id, with_variants=False)

    logger.info(f"✅ [DB] Товар обновлен: '{product.name}' (ID={product_id}), изменения: {', '.join(updated_fields) if updated_fields else 'нет изменений'}")
    return product


async def delete_product(
    session: AsyncSession,
    product_id: int
) -> bool:
    """
    Delete a product

    Args:
        session: Database session
        product_id: Product ID

    Returns:
        True if deleted successfully, False if not found
    """
    product = await get_product_by_id(session, product_id, with_variants=False)
    if not product:
        logger.warning(f"[DB] Попытка удаления несуществующего товара ID={product_id}")
        return False

    product_name = product.name
    await session.delete(product)
    await session.commit()

    logger.warning(f"🗑️ [DB] Товар удален: '{product_name}' (ID={product_id})")
    return True


async def toggle_product_status(
    session: AsyncSession,
    product_id: int
) -> Optional[Product]:
    """
    Toggle product active status

    Args:
        session: Database session
        product_id: Product ID

    Returns:
        Updated Product object or None if not found
    """
    product = await get_product_by_id(session, product_id, with_variants=True)
    if not product:
        logger.warning(f"[DB] Попытка изменения статуса несуществующего товара ID={product_id}")
        return None

    old_status = product.is_active
    product.is_active = not product.is_active
    await session.commit()

    # Перезагружаем товар с relationships, чтобы избежать lazy loading
    product = await get_product_by_id(session, product_id, with_variants=True)

    status_icon = "✅" if product.is_active else "⚠️"
    status_text = "активирован" if product.is_active else "деактивирован"
    logger.info(f"{status_icon} [DB] Товар {status_text}: '{product.name}' (ID={product_id}, {old_status} → {product.is_active})")

    return product


async def add_product_variant(
    session: AsyncSession,
    product_id: int,
    size: Optional[str],
    color: Optional[str],
    quantity: int,
    sku: Optional[str] = None
) -> Optional[ProductVariant]:
    """
    Add a variant to a product

    Args:
        session: Database session
        product_id: Product ID
        size: Size
        color: Color
        quantity: Quantity in stock
        sku: Stock keeping unit

    Returns:
        Created ProductVariant object or None if product not found
    """
    product = await get_product_by_id(session, product_id, with_variants=False)
    if not product:
        logger.warning(f"[DB] Попытка добавления варианта к несуществующему товару ID={product_id}")
        return None

    try:
        variant = ProductVariant(
            product_id=product_id,
            size=size,
            color=color,
            quantity=quantity,
            sku=sku
        )

        session.add(variant)
        await session.commit()
        await session.refresh(variant)

        logger.info(
            f"✅ [DB] Вариант добавлен к товару '{product.name}' (ID={product_id}): "
            f"размер={size or 'не указан'}, цвет={color or 'не указан'}, количество={quantity}"
        )
        return variant
    except Exception as e:
        logger.exception(f"❌ [DB] ОШИБКА при добавлении варианта к товару ID={product_id}: {e}")
        raise


async def update_product_variant(
    session: AsyncSession,
    variant_id: int,
    **kwargs
) -> Optional[ProductVariant]:
    """
    Update product variant

    Args:
        session: Database session
        variant_id: Variant ID
        **kwargs: Fields to update

    Returns:
        Updated ProductVariant object or None if not found
    """
    query = select(ProductVariant).where(ProductVariant.id == variant_id)
    result = await session.execute(query)
    variant = result.scalar_one_or_none()

    if not variant:
        return None

    # Update allowed fields
    allowed_fields = {'size', 'color', 'quantity', 'sku'}

    for key, value in kwargs.items():
        if key in allowed_fields and value is not None:
            setattr(variant, key, value)

    await session.commit()
    await session.refresh(variant)

    logger.info(f"Variant updated: id={variant_id}")
    return variant


async def delete_product_variant(
    session: AsyncSession,
    variant_id: int
) -> bool:
    """
    Delete product variant

    Args:
        session: Database session
        variant_id: Variant ID

    Returns:
        True if deleted successfully, False if not found
    """
    query = select(ProductVariant).where(ProductVariant.id == variant_id)
    result = await session.execute(query)
    variant = result.scalar_one_or_none()

    if not variant:
        return False

    await session.delete(variant)
    await session.commit()

    logger.info(f"Variant deleted: id={variant_id}")
    return True


async def get_products_count_by_category(
    session: AsyncSession,
    category_id: int
) -> int:
    """
    Get count of products in a category

    Args:
        session: Database session
        category_id: Category ID

    Returns:
        Count of products
    """
    query = select(func.count(Product.id)).where(Product.category_id == category_id)
    result = await session.execute(query)
    count = result.scalar() or 0

    return count
