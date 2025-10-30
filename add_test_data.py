"""
Скрипт для добавления тестовых данных в базу
"""
import asyncio
from decimal import Decimal

from bot.database.engine import get_session
from bot.database.models.category import Category
from bot.database.models.product import Product
from bot.database.models.product_variant import ProductVariant
from bot.utils.logger import setup_logger


logger = setup_logger(__name__)


async def add_test_data():
    """Добавить тестовые категории и товары"""
    async for session in get_session():
        try:
            # Создаем категории
            logger.info("Создание категорий...")

            # Корневые категории
            men_category = Category(
                name="Мужская одежда",
                description="Стильная мужская одежда",
                is_active=True
            )
            women_category = Category(
                name="Женская одежда",
                description="Модная женская одежда",
                is_active=True
            )

            session.add_all([men_category, women_category])
            await session.flush()

            # Подкатегории для мужской одежды
            men_shirts = Category(
                name="Рубашки",
                description="Мужские рубашки",
                parent_id=men_category.id,
                is_active=True
            )
            men_pants = Category(
                name="Брюки",
                description="Мужские брюки",
                parent_id=men_category.id,
                is_active=True
            )
            men_jackets = Category(
                name="Куртки",
                description="Мужские куртки",
                parent_id=men_category.id,
                is_active=True
            )

            # Подкатегории для женской одежды
            women_dresses = Category(
                name="Платья",
                description="Женские платья",
                parent_id=women_category.id,
                is_active=True
            )
            women_blouses = Category(
                name="Блузки",
                description="Женские блузки",
                parent_id=women_category.id,
                is_active=True
            )

            session.add_all([
                men_shirts, men_pants, men_jackets,
                women_dresses, women_blouses
            ])
            await session.flush()

            logger.info("Категории созданы")

            # Создаем товары
            logger.info("Создание товаров...")

            # Товары для мужских рубашек
            shirt1 = Product(
                category_id=men_shirts.id,
                name="Классическая белая рубашка",
                description="Элегантная белая рубашка из хлопка. Идеально подходит для офиса и деловых встреч.",
                price=Decimal("2999.00"),
                images=[],
                is_active=True
            )

            shirt2 = Product(
                category_id=men_shirts.id,
                name="Рубашка в клетку",
                description="Стильная рубашка в клетку. Отличный выбор для повседневного образа.",
                price=Decimal("2499.00"),
                discount_price=Decimal("1999.00"),
                images=[],
                is_active=True
            )

            # Товары для мужских брюк
            pants1 = Product(
                category_id=men_pants.id,
                name="Классические черные брюки",
                description="Строгие черные брюки из качественной ткани. Универсальный выбор для любого случая.",
                price=Decimal("3999.00"),
                images=[],
                is_active=True
            )

            pants2 = Product(
                category_id=men_pants.id,
                name="Джинсы slim fit",
                description="Современные джинсы slim fit. Комфорт и стиль в одном.",
                price=Decimal("4499.00"),
                images=[],
                is_active=True
            )

            # Товары для мужских курток
            jacket1 = Product(
                category_id=men_jackets.id,
                name="Кожаная куртка",
                description="Стильная кожаная куртка. Классика, которая никогда не выходит из моды.",
                price=Decimal("15999.00"),
                discount_price=Decimal("12999.00"),
                images=[],
                is_active=True
            )

            # Товары для женских платьев
            dress1 = Product(
                category_id=women_dresses.id,
                name="Вечернее платье",
                description="Элегантное вечернее платье для особых случаев.",
                price=Decimal("8999.00"),
                images=[],
                is_active=True
            )

            dress2 = Product(
                category_id=women_dresses.id,
                name="Летнее платье",
                description="Легкое летнее платье из натуральных тканей.",
                price=Decimal("3499.00"),
                images=[],
                is_active=True
            )

            dress3 = Product(
                category_id=women_dresses.id,
                name="Коктейльное платье",
                description="Стильное коктейльное платье для вечеринок.",
                price=Decimal("6999.00"),
                discount_price=Decimal("5499.00"),
                images=[],
                is_active=True
            )

            # Товары для женских блузок
            blouse1 = Product(
                category_id=women_blouses.id,
                name="Шелковая блузка",
                description="Роскошная шелковая блузка премиум качества.",
                price=Decimal("4999.00"),
                images=[],
                is_active=True
            )

            blouse2 = Product(
                category_id=women_blouses.id,
                name="Блузка с кружевом",
                description="Романтичная блузка с кружевными вставками.",
                price=Decimal("2999.00"),
                images=[],
                is_active=True
            )

            session.add_all([
                shirt1, shirt2, pants1, pants2, jacket1,
                dress1, dress2, dress3, blouse1, blouse2
            ])
            await session.flush()

            logger.info("Товары созданы")

            # Создаем варианты товаров (размеры и цвета)
            logger.info("Создание вариантов товаров...")

            # Варианты для рубашек
            for product in [shirt1, shirt2]:
                for size in ["S", "M", "L", "XL"]:
                    for color in ["Белый", "Синий"]:
                        variant = ProductVariant(
                            product_id=product.id,
                            size=size,
                            color=color,
                            quantity=10,
                            sku=f"{product.id}-{size}-{color}"
                        )
                        session.add(variant)

            # Варианты для брюк
            for product in [pants1, pants2]:
                for size in ["30", "32", "34", "36"]:
                    variant = ProductVariant(
                        product_id=product.id,
                        size=size,
                        color="Черный",
                        quantity=15,
                        sku=f"{product.id}-{size}-Черный"
                    )
                    session.add(variant)

            # Варианты для куртки
            for size in ["S", "M", "L", "XL"]:
                for color in ["Черный", "Коричневый"]:
                    variant = ProductVariant(
                        product_id=jacket1.id,
                        size=size,
                        color=color,
                        quantity=5,
                        sku=f"{jacket1.id}-{size}-{color}"
                    )
                    session.add(variant)

            # Варианты для платьев
            for product in [dress1, dress2, dress3]:
                for size in ["XS", "S", "M", "L"]:
                    for color in ["Черный", "Красный", "Синий"]:
                        variant = ProductVariant(
                            product_id=product.id,
                            size=size,
                            color=color,
                            quantity=8,
                            sku=f"{product.id}-{size}-{color}"
                        )
                        session.add(variant)

            # Варианты для блузок
            for product in [blouse1, blouse2]:
                for size in ["XS", "S", "M", "L"]:
                    for color in ["Белый", "Бежевый"]:
                        variant = ProductVariant(
                            product_id=product.id,
                            size=size,
                            color=color,
                            quantity=12,
                            sku=f"{product.id}-{size}-{color}"
                        )
                        session.add(variant)

            await session.commit()
            logger.info("Варианты товаров созданы")

            logger.info("✅ Тестовые данные успешно добавлены!")
            logger.info(f"Создано категорий: 7")
            logger.info(f"Создано товаров: 10")
            logger.info("Создано вариантов: множество (размеры и цвета)")

        except Exception as e:
            logger.error(f"Ошибка при добавлении тестовых данных: {e}")
            raise
        break  # Выходим из цикла после первой итерации


if __name__ == "__main__":
    asyncio.run(add_test_data())
