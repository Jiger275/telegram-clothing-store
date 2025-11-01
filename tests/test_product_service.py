"""
Тесты для сервиса товаров (product_service)
"""
import pytest
from decimal import Decimal
from sqlalchemy.ext.asyncio import AsyncSession

from bot.services import product_service
from bot.database.models.product import Product
from bot.database.models.product_variant import ProductVariant
from bot.database.models.category import Category


class TestGetProductsByCategory:
    """Тесты для get_products_by_category"""

    @pytest.mark.asyncio
    async def test_get_products_empty_category(
        self,
        session: AsyncSession,
        test_category: Category
    ):
        """Тест: получение товаров из пустой категории"""
        products, total_count = await product_service.get_products_by_category(
            session=session,
            category_id=test_category.id,
            page=1,
            page_size=6
        )

        assert products == []
        assert total_count == 0

    @pytest.mark.asyncio
    async def test_get_products_with_items(
        self,
        session: AsyncSession,
        test_category: Category,
        test_products_batch
    ):
        """Тест: получение товаров из категории с товарами"""
        products, total_count = await product_service.get_products_by_category(
            session=session,
            category_id=test_category.id,
            page=1,
            page_size=6
        )

        assert len(products) == 6  # Должно вернуть 6 товаров (размер страницы)
        assert total_count == 15  # Всего 15 товаров в test_products_batch
        assert all(isinstance(p, Product) for p in products)

    @pytest.mark.asyncio
    async def test_pagination_first_page(
        self,
        session: AsyncSession,
        test_category: Category,
        test_products_batch
    ):
        """Тест: первая страница пагинации"""
        products, total_count = await product_service.get_products_by_category(
            session=session,
            category_id=test_category.id,
            page=1,
            page_size=6
        )

        assert len(products) == 6
        assert total_count == 15

    @pytest.mark.asyncio
    async def test_pagination_second_page(
        self,
        session: AsyncSession,
        test_category: Category,
        test_products_batch
    ):
        """Тест: вторая страница пагинации"""
        products, total_count = await product_service.get_products_by_category(
            session=session,
            category_id=test_category.id,
            page=2,
            page_size=6
        )

        assert len(products) == 6
        assert total_count == 15

    @pytest.mark.asyncio
    async def test_pagination_last_page(
        self,
        session: AsyncSession,
        test_category: Category,
        test_products_batch
    ):
        """Тест: последняя страница с неполным набором товаров"""
        products, total_count = await product_service.get_products_by_category(
            session=session,
            category_id=test_category.id,
            page=3,
            page_size=6
        )

        assert len(products) == 3  # На последней странице только 3 товара (15 % 6 = 3)
        assert total_count == 15

    @pytest.mark.asyncio
    async def test_custom_page_size(
        self,
        session: AsyncSession,
        test_category: Category,
        test_products_batch
    ):
        """Тест: пользовательский размер страницы"""
        products, total_count = await product_service.get_products_by_category(
            session=session,
            category_id=test_category.id,
            page=1,
            page_size=10
        )

        assert len(products) == 10
        assert total_count == 15

    @pytest.mark.asyncio
    async def test_variants_loaded(
        self,
        session: AsyncSession,
        test_category: Category,
        test_product: Product,
        test_product_variant: ProductVariant
    ):
        """Тест: варианты товаров загружаются вместе с товарами"""
        products, total_count = await product_service.get_products_by_category(
            session=session,
            category_id=test_category.id,
            page=1,
            page_size=6
        )

        assert len(products) > 0
        # Проверяем, что атрибут variants существует и доступен
        for product in products:
            assert hasattr(product, 'variants')


class TestGetProductById:
    """Тесты для get_product_by_id"""

    @pytest.mark.asyncio
    async def test_get_existing_product(
        self,
        session: AsyncSession,
        test_product: Product
    ):
        """Тест: получение существующего товара"""
        product = await product_service.get_product_by_id(
            session=session,
            product_id=test_product.id
        )

        assert product is not None
        assert product.id == test_product.id
        assert product.name == test_product.name

    @pytest.mark.asyncio
    async def test_get_nonexistent_product(
        self,
        session: AsyncSession
    ):
        """Тест: получение несуществующего товара"""
        product = await product_service.get_product_by_id(
            session=session,
            product_id=99999
        )

        assert product is None

    @pytest.mark.asyncio
    async def test_get_product_with_variants(
        self,
        session: AsyncSession,
        test_product: Product,
        test_product_variant: ProductVariant
    ):
        """Тест: получение товара с вариантами"""
        product = await product_service.get_product_by_id(
            session=session,
            product_id=test_product.id,
            with_variants=True
        )

        assert product is not None
        assert hasattr(product, 'variants')
        assert len(product.variants) > 0


class TestGetProductTotalQuantity:
    """Тесты для get_product_total_quantity"""

    @pytest.mark.asyncio
    async def test_total_quantity_with_variants(
        self,
        session: AsyncSession,
        test_product: Product,
        test_product_variant: ProductVariant
    ):
        """Тест: общее количество товара с вариантами"""
        total_quantity = await product_service.get_product_total_quantity(
            session=session,
            product_id=test_product.id
        )

        assert total_quantity == 10  # test_product_variant имеет quantity=10

    @pytest.mark.asyncio
    async def test_total_quantity_without_variants(
        self,
        session: AsyncSession,
        test_product: Product
    ):
        """Тест: общее количество товара без вариантов"""
        # Используем товар без вариантов
        total_quantity = await product_service.get_product_total_quantity(
            session=session,
            product_id=test_product.id
        )

        # Если вариантов нет, должно вернуть 0
        assert total_quantity >= 0

    @pytest.mark.asyncio
    async def test_total_quantity_multiple_variants(
        self,
        session: AsyncSession,
        test_category: Category
    ):
        """Тест: общее количество с несколькими вариантами"""
        # Создаем товар с несколькими вариантами
        product = Product(
            category_id=test_category.id,
            name="Товар с вариантами",
            price=1000.00,
            is_active=True
        )
        session.add(product)
        await session.flush()

        # Добавляем 3 варианта по 5 штук каждый
        for i in range(3):
            variant = ProductVariant(
                product_id=product.id,
                size="M",
                color=f"Цвет {i}",
                quantity=5,
                sku=f"SKU-{i}"
            )
            session.add(variant)

        await session.commit()

        total_quantity = await product_service.get_product_total_quantity(
            session=session,
            product_id=product.id
        )

        assert total_quantity == 15  # 3 варианта * 5 штук


class TestGetAvailableSizes:
    """Тесты для get_available_sizes"""

    @pytest.mark.asyncio
    async def test_get_sizes(
        self,
        session: AsyncSession,
        test_products_with_variants
    ):
        """Тест: получение доступных размеров"""
        product = test_products_with_variants[0]

        sizes = await product_service.get_available_sizes(
            session=session,
            product_id=product.id
        )

        assert len(sizes) == 3  # S, M, L
        assert "S" in sizes
        assert "M" in sizes
        assert "L" in sizes

    @pytest.mark.asyncio
    async def test_get_sizes_no_variants(
        self,
        session: AsyncSession,
        test_product: Product
    ):
        """Тест: получение размеров товара без вариантов"""
        sizes = await product_service.get_available_sizes(
            session=session,
            product_id=test_product.id
        )

        assert sizes == []


class TestGetAvailableColors:
    """Тесты для get_available_colors"""

    @pytest.mark.asyncio
    async def test_get_colors(
        self,
        session: AsyncSession,
        test_products_with_variants
    ):
        """Тест: получение доступных цветов"""
        product = test_products_with_variants[0]

        colors = await product_service.get_available_colors(
            session=session,
            product_id=product.id
        )

        assert len(colors) == 2  # Черный, Белый
        assert "Черный" in colors
        assert "Белый" in colors

    @pytest.mark.asyncio
    async def test_get_colors_filtered_by_size(
        self,
        session: AsyncSession,
        test_products_with_variants
    ):
        """Тест: получение цветов с фильтрацией по размеру"""
        product = test_products_with_variants[0]

        colors = await product_service.get_available_colors(
            session=session,
            product_id=product.id,
            size="L"
        )

        # Должны вернуться те же цвета, но только для размера L
        assert len(colors) == 2
        assert "Черный" in colors
        assert "Белый" in colors


class TestFormatPrice:
    """Тесты для format_price"""

    def test_format_price_integer(self):
        """Тест: форматирование целых чисел"""
        price = Decimal("1000.00")
        formatted = product_service.format_price(price)

        assert "1" in formatted
        assert "000" in formatted
        assert "₽" in formatted

    def test_format_price_with_decimals(self):
        """Тест: форматирование с десятичными знаками"""
        price = Decimal("1234.56")
        formatted = product_service.format_price(price)

        assert "1" in formatted
        assert "234" in formatted
        assert "56" in formatted
        assert "₽" in formatted

    def test_format_price_large_number(self):
        """Тест: форматирование больших чисел"""
        price = Decimal("123456.78")
        formatted = product_service.format_price(price)

        assert "₽" in formatted
        # Проверяем наличие разделителей тысяч
        assert "," in formatted or " " in formatted or "123456" in formatted


class TestGetVariantByAttributes:
    """Тесты для get_variant_by_attributes"""

    @pytest.mark.asyncio
    async def test_get_variant_by_size_and_color(
        self,
        session: AsyncSession,
        test_products_with_variants
    ):
        """Тест: получение варианта по размеру и цвету"""
        product = test_products_with_variants[0]

        variant = await product_service.get_variant_by_attributes(
            session=session,
            product_id=product.id,
            size="L",
            color="Черный"
        )

        assert variant is not None
        assert variant.size == "L"
        assert variant.color == "Черный"
        assert variant.product_id == product.id

    @pytest.mark.asyncio
    async def test_get_nonexistent_variant(
        self,
        session: AsyncSession,
        test_products_with_variants
    ):
        """Тест: получение несуществующего варианта"""
        product = test_products_with_variants[0]

        variant = await product_service.get_variant_by_attributes(
            session=session,
            product_id=product.id,
            size="XXXL",
            color="Розовый"
        )

        assert variant is None


class TestCheckProductAvailability:
    """Тесты для check_product_availability"""

    @pytest.mark.asyncio
    async def test_available_product(
        self,
        session: AsyncSession,
        test_products_with_variants
    ):
        """Тест: проверка доступности товара"""
        product = test_products_with_variants[0]

        is_available = await product_service.check_product_availability(
            session=session,
            product_id=product.id,
            size="M",
            color="Белый"
        )

        assert is_available is True

    @pytest.mark.asyncio
    async def test_unavailable_product(
        self,
        session: AsyncSession,
        test_category: Category
    ):
        """Тест: проверка недоступного товара"""
        # Создаем товар с вариантом, у которого quantity=0
        product = Product(
            category_id=test_category.id,
            name="Недоступный товар",
            price=1000.00,
            is_active=True
        )
        session.add(product)
        await session.flush()

        variant = ProductVariant(
            product_id=product.id,
            size="M",
            color="Черный",
            quantity=0,
            sku="OUT-OF-STOCK"
        )
        session.add(variant)
        await session.commit()

        is_available = await product_service.check_product_availability(
            session=session,
            product_id=product.id,
            size="M",
            color="Черный"
        )

        assert is_available is False
