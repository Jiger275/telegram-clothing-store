"""
Конфигурация и фикстуры для pytest
"""
import asyncio
import pytest
from typing import AsyncGenerator
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine, async_sessionmaker
from sqlalchemy.pool import StaticPool

from bot.database.base import Base
from bot.database.models.user import User
from bot.database.models.category import Category
from bot.database.models.product import Product
from bot.database.models.product_variant import ProductVariant
from bot.config.settings import settings


# Настройка event loop для pytest-asyncio
@pytest.fixture(scope="session")
def event_loop():
    """Создает event loop для всей сессии тестирования"""
    loop = asyncio.get_event_loop_policy().new_event_loop()
    yield loop
    loop.close()


# Создание тестовой базы данных
@pytest.fixture(scope="function")
async def test_engine():
    """Создает тестовый engine для in-memory SQLite"""
    engine = create_async_engine(
        "sqlite+aiosqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
        echo=False
    )

    # Создаем все таблицы
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    yield engine

    # Удаляем все таблицы после теста
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)

    await engine.dispose()


@pytest.fixture(scope="function")
async def session(test_engine) -> AsyncGenerator[AsyncSession, None]:
    """Создает тестовую сессию БД"""
    async_session = async_sessionmaker(
        test_engine,
        class_=AsyncSession,
        expire_on_commit=False
    )

    async with async_session() as session:
        yield session


# Фикстуры для тестовых данных
@pytest.fixture
async def test_user(session: AsyncSession) -> User:
    """Создает тестового пользователя"""
    user = User(
        telegram_id=123456789,
        username="testuser",
        full_name="Test User",
        is_admin=False
    )
    session.add(user)
    await session.commit()
    await session.refresh(user)
    return user


@pytest.fixture
async def test_admin(session: AsyncSession) -> User:
    """Создает тестового администратора"""
    admin = User(
        telegram_id=987654321,
        username="adminuser",
        full_name="Admin User",
        is_admin=True
    )
    session.add(admin)
    await session.commit()
    await session.refresh(admin)
    return admin


@pytest.fixture
async def test_category(session: AsyncSession) -> Category:
    """Создает тестовую категорию"""
    category = Category(
        name="Куртки",
        description="Зимние и демисезонные куртки",
        is_active=True
    )
    session.add(category)
    await session.commit()
    await session.refresh(category)
    return category


@pytest.fixture
async def test_subcategory(session: AsyncSession, test_category: Category) -> Category:
    """Создает тестовую подкатегорию"""
    subcategory = Category(
        name="Зимние куртки",
        description="Теплые зимние куртки",
        parent_id=test_category.id,
        is_active=True
    )
    session.add(subcategory)
    await session.commit()
    await session.refresh(subcategory)
    return subcategory


@pytest.fixture
async def test_product(session: AsyncSession, test_category: Category) -> Product:
    """Создает тестовый товар"""
    product = Product(
        category_id=test_category.id,
        name="Зимняя куртка",
        description="Теплая зимняя куртка с капюшоном",
        price=5000.00,
        discount_price=None,
        images=["test_image_1.jpg", "test_image_2.jpg"],
        is_active=True
    )
    session.add(product)
    await session.commit()
    await session.refresh(product)
    return product


@pytest.fixture
async def test_product_with_discount(session: AsyncSession, test_category: Category) -> Product:
    """Создает тестовый товар со скидкой"""
    product = Product(
        category_id=test_category.id,
        name="Куртка со скидкой",
        description="Куртка с большой скидкой",
        price=10000.00,
        discount_price=7000.00,
        images=["discount_image.jpg"],
        is_active=True
    )
    session.add(product)
    await session.commit()
    await session.refresh(product)
    return product


@pytest.fixture
async def test_product_variant(session: AsyncSession, test_product: Product) -> ProductVariant:
    """Создает тестовый вариант товара"""
    variant = ProductVariant(
        product_id=test_product.id,
        size="L",
        color="Черный",
        quantity=10,
        sku="JACKET-L-BLACK"
    )
    session.add(variant)
    await session.commit()
    await session.refresh(variant)
    return variant


@pytest.fixture
async def test_products_batch(session: AsyncSession, test_category: Category) -> list[Product]:
    """Создает батч тестовых товаров для проверки пагинации"""
    products = []
    for i in range(15):
        product = Product(
            category_id=test_category.id,
            name=f"Товар {i+1}",
            description=f"Описание товара {i+1}",
            price=1000.00 + (i * 100),
            images=[f"product_{i+1}.jpg"],
            is_active=True
        )
        session.add(product)
        products.append(product)

    await session.commit()

    # Обновляем объекты после commit
    for product in products:
        await session.refresh(product)

    return products


@pytest.fixture
async def test_products_with_variants(
    session: AsyncSession,
    test_category: Category
) -> list[Product]:
    """Создает товары с вариантами"""
    products = []

    for i in range(3):
        product = Product(
            category_id=test_category.id,
            name=f"Товар с вариантами {i+1}",
            description=f"Описание товара {i+1}",
            price=2000.00,
            images=[f"variant_product_{i+1}.jpg"],
            is_active=True
        )
        session.add(product)
        await session.flush()

        # Добавляем варианты
        for size in ["S", "M", "L"]:
            for color in ["Черный", "Белый"]:
                variant = ProductVariant(
                    product_id=product.id,
                    size=size,
                    color=color,
                    quantity=5,
                    sku=f"PROD{i+1}-{size}-{color}"
                )
                session.add(variant)

        products.append(product)

    await session.commit()

    for product in products:
        await session.refresh(product)

    return products
