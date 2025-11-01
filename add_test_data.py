"""
Скрипт для добавления тестовых данных в базу
ОБНОВЛЕН ДЛЯ СИСТЕМЫ КАРТОЧЕК ТОВАРОВ (ЭТАП 4)

Создает:
- Категории товаров с подкатегориями
- ~20 товаров с изображениями и описаниями
- Варианты товаров (размеры и цвета)
- Товары со скидками
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
    """Добавить тестовые категории и товары для демонстрации карточек"""
    async for session in get_session():
        try:
            logger.info("=" * 60)
            logger.info("🚀 СОЗДАНИЕ ТЕСТОВЫХ ДАННЫХ ДЛЯ СИСТЕМЫ КАРТОЧЕК")
            logger.info("=" * 60)

            # ==================== КАТЕГОРИИ ====================
            logger.info("\n📁 Создание структуры категорий...")

            # Корневые категории
            men_category = Category(
                name="👔 Мужская одежда",
                description="Стильная и качественная мужская одежда",
                is_active=True
            )
            women_category = Category(
                name="👗 Женская одежда",
                description="Модная и элегантная женская одежда",
                is_active=True
            )
            accessories_category = Category(
                name="👜 Аксессуары",
                description="Стильные аксессуары для завершения образа",
                is_active=True
            )

            session.add_all([men_category, women_category, accessories_category])
            await session.flush()
            logger.info("   ✅ Корневые категории созданы")

            # Подкатегории для мужской одежды
            men_jackets = Category(
                name="🧥 Куртки",
                description="Зимние и демисезонные куртки",
                parent_id=men_category.id,
                is_active=True
            )
            men_shirts = Category(
                name="👔 Рубашки",
                description="Классические и повседневные рубашки",
                parent_id=men_category.id,
                is_active=True
            )
            men_pants = Category(
                name="👖 Брюки и джинсы",
                description="Брюки, джинсы и чиносы",
                parent_id=men_category.id,
                is_active=True
            )

            # Подкатегории для женской одежды
            women_dresses = Category(
                name="👗 Платья",
                description="Вечерние, коктейльные и повседневные платья",
                parent_id=women_category.id,
                is_active=True
            )
            women_blouses = Category(
                name="👚 Блузки",
                description="Элегантные блузки для любого случая",
                parent_id=women_category.id,
                is_active=True
            )
            women_skirts = Category(
                name="👗 Юбки",
                description="Юбки различных фасонов",
                parent_id=women_category.id,
                is_active=True
            )

            # Подкатегории для аксессуаров
            bags = Category(
                name="👜 Сумки",
                description="Сумки, рюкзаки и клатчи",
                parent_id=accessories_category.id,
                is_active=True
            )

            session.add_all([
                men_jackets, men_shirts, men_pants,
                women_dresses, women_blouses, women_skirts,
                bags
            ])
            await session.flush()
            logger.info("   ✅ Подкатегории созданы")

            # ==================== ТОВАРЫ ====================
            logger.info("\n🛍️  Создание товаров с изображениями...")

            products = []

            # ========== МУЖСКИЕ КУРТКИ ==========
            products.extend([
                Product(
                    category_id=men_jackets.id,
                    name="Зимняя куртка Premium Black",
                    description="Стильная зимняя куртка с утеплителем премиум класса. "
                               "Водонепроницаемый материал, множество карманов, съемный капюшон. "
                               "Отлично подходит для самых холодных дней.",
                    price=Decimal("12999.00"),
                    discount_price=Decimal("9999.00"),
                    images=["jacket_black_1.jpg", "jacket_black_2.jpg", "jacket_black_3.jpg"],
                    is_active=True
                ),
                Product(
                    category_id=men_jackets.id,
                    name="Спортивная куртка Red Sport",
                    description="Яркая красная спортивная куртка для активного отдыха. "
                               "Легкая, дышащая ткань. Влагозащита. Идеальна для спорта и прогулок.",
                    price=Decimal("6999.00"),
                    images=["jacket_red_1.jpg", "jacket_red_2.jpg", "jacket_red_3.jpg"],
                    is_active=True
                ),
                Product(
                    category_id=men_jackets.id,
                    name="Куртка Urban Fashion Purple",
                    description="Модная фиолетовая куртка для стильных городских образов. "
                               "Современный дизайн, качественные материалы, удобная посадка. "
                               "Универсальная модель на каждый день.",
                    price=Decimal("8499.00"),
                    discount_price=Decimal("6999.00"),
                    images=["jacket_purple_1.jpg", "jacket_purple_2.jpg", "jacket_purple_3.jpg"],
                    is_active=True
                ),
                Product(
                    category_id=men_jackets.id,
                    name="Демисезонная куртка Casual",
                    description="Легкая демисезонная куртка для межсезонья. "
                               "Водоотталкивающая ткань, стильный дизайн. "
                               "Отличный выбор для весны и осени.",
                    price=Decimal("5499.00"),
                    images=["jacket_casual_1.jpg", "jacket_casual_2.jpg"],
                    is_active=True
                ),
            ])

            # ========== МУЖСКИЕ РУБАШКИ ==========
            products.extend([
                Product(
                    category_id=men_shirts.id,
                    name="Классическая белая рубашка Premium",
                    description="Элегантная белая рубашка из 100% хлопка. "
                               "Идеально подходит для офиса и деловых встреч. "
                               "Немнущаяся ткань, безупречный крой.",
                    price=Decimal("3999.00"),
                    images=["shirt_white_1.jpg", "shirt_white_2.jpg"],
                    is_active=True
                ),
                Product(
                    category_id=men_shirts.id,
                    name="Рубашка в клетку Lumberjack",
                    description="Стильная рубашка в клетку в стиле лесоруба. "
                               "Отличный выбор для повседневного образа. "
                               "Мягкая фланелевая ткань, удобная посадка.",
                    price=Decimal("2999.00"),
                    discount_price=Decimal("2299.00"),
                    images=["shirt_plaid_1.jpg", "shirt_plaid_2.jpg"],
                    is_active=True
                ),
                Product(
                    category_id=men_shirts.id,
                    name="Рубашка деловая синяя Slim Fit",
                    description="Приталенная деловая рубашка насыщенного синего цвета. "
                               "Современный крой slim fit. Немнущаяся ткань.",
                    price=Decimal("3499.00"),
                    images=["shirt_blue_1.jpg"],
                    is_active=True
                ),
            ])

            # ========== МУЖСКИЕ БРЮКИ ==========
            products.extend([
                Product(
                    category_id=men_pants.id,
                    name="Классические черные брюки Business",
                    description="Строгие черные брюки из качественной ткани. "
                               "Универсальный выбор для офиса и деловых мероприятий. "
                               "Безупречная посадка, премиум качество.",
                    price=Decimal("4999.00"),
                    images=["pants_black_1.jpg", "pants_black_2.jpg"],
                    is_active=True
                ),
                Product(
                    category_id=men_pants.id,
                    name="Джинсы Slim Fit Blue",
                    description="Современные джинсы slim fit. "
                               "Комфорт и стиль в одном. Идеальны для повседневной носки.",
                    price=Decimal("4499.00"),
                    discount_price=Decimal("3499.00"),
                    images=["jeans_slim_1.jpg", "jeans_slim_2.jpg"],
                    is_active=True
                ),
                Product(
                    category_id=men_pants.id,
                    name="Чиносы бежевые Casual",
                    description="Удобные чиносы бежевого цвета для повседневной носки. "
                               "Отличное сочетание комфорта и стиля.",
                    price=Decimal("3999.00"),
                    images=["chinos_beige_1.jpg"],
                    is_active=True
                ),
            ])

            # ========== ЖЕНСКИЕ ПЛАТЬЯ ==========
            products.extend([
                Product(
                    category_id=women_dresses.id,
                    name="Вечернее платье Elegant Black",
                    description="Элегантное вечернее платье черного цвета. "
                               "Безупречный крой, изысканный дизайн. "
                               "Идеально для особых случаев и торжественных мероприятий.",
                    price=Decimal("12999.00"),
                    discount_price=Decimal("9999.00"),
                    images=["dress_evening_1.jpg", "dress_evening_2.jpg", "dress_evening_3.jpg"],
                    is_active=True
                ),
                Product(
                    category_id=women_dresses.id,
                    name="Летнее платье Floral Print",
                    description="Легкое летнее платье с цветочным принтом. "
                               "Натуральные ткани, яркие цвета. "
                               "Идеально для жаркого лета и отпуска.",
                    price=Decimal("3999.00"),
                    images=["dress_summer_1.jpg", "dress_summer_2.jpg"],
                    is_active=True
                ),
                Product(
                    category_id=women_dresses.id,
                    name="Коктейльное платье Red Passion",
                    description="Стильное красное коктейльное платье. "
                               "Яркий образ для вечеринок и свиданий. "
                               "Подчеркивает фигуру, современный дизайн.",
                    price=Decimal("7999.00"),
                    discount_price=Decimal("5999.00"),
                    images=["dress_cocktail_1.jpg", "dress_cocktail_2.jpg"],
                    is_active=True
                ),
            ])

            # ========== ЖЕНСКИЕ БЛУЗКИ ==========
            products.extend([
                Product(
                    category_id=women_blouses.id,
                    name="Шелковая блузка Luxury",
                    description="Роскошная шелковая блузка премиум качества. "
                               "100% натуральный шелк. Элегантный крой. "
                               "Идеально для деловых встреч и особых случаев.",
                    price=Decimal("5999.00"),
                    images=["blouse_silk_1.jpg", "blouse_silk_2.jpg"],
                    is_active=True
                ),
                Product(
                    category_id=women_blouses.id,
                    name="Блузка с кружевом Romance",
                    description="Романтичная блузка с изящными кружевными вставками. "
                               "Нежные тона, женственный дизайн. "
                               "Отличное дополнение к любому образу.",
                    price=Decimal("3499.00"),
                    images=["blouse_lace_1.jpg"],
                    is_active=True
                ),
            ])

            # ========== ЖЕНСКИЕ ЮБКИ ==========
            products.extend([
                Product(
                    category_id=women_skirts.id,
                    name="Юбка-карандаш офисная Black",
                    description="Классическая черная юбка-карандаш для офиса. "
                               "Строгий крой, качественная ткань. "
                               "Универсальная модель для делового гардероба.",
                    price=Decimal("2999.00"),
                    images=["skirt_pencil_1.jpg"],
                    is_active=True
                ),
                Product(
                    category_id=women_skirts.id,
                    name="Юбка миди плиссе",
                    description="Стильная юбка миди с плиссировкой. "
                               "Легкая ткань, красивая драпировка. "
                               "Отлично для романтичных образов.",
                    price=Decimal("3499.00"),
                    discount_price=Decimal("2799.00"),
                    images=["skirt_midi_1.jpg", "skirt_midi_2.jpg"],
                    is_active=True
                ),
            ])

            # ========== АКСЕССУАРЫ ==========
            products.extend([
                Product(
                    category_id=bags.id,
                    name="Кожаная сумка Classic Leather",
                    description="Элегантная кожаная сумка из натуральной кожи. "
                               "Вместительная, множество отделений. "
                               "Идеальное сочетание стиля и функциональности.",
                    price=Decimal("8999.00"),
                    images=["bag_leather_1.jpg", "bag_leather_2.jpg"],
                    is_active=True
                ),
                Product(
                    category_id=bags.id,
                    name="Спортивный рюкзак Urban",
                    description="Современный спортивный рюкзак для города. "
                               "Отделение для ноутбука, водоотталкивающая ткань. "
                               "Удобные лямки, эргономичный дизайн.",
                    price=Decimal("4999.00"),
                    discount_price=Decimal("3999.00"),
                    images=["backpack_urban_1.jpg"],
                    is_active=True
                ),
            ])

            # Добавляем все товары
            session.add_all(products)
            await session.flush()
            logger.info(f"   ✅ Создано {len(products)} товаров с изображениями")

            # ==================== ВАРИАНТЫ ТОВАРОВ ====================
            logger.info("\n🎨 Создание вариантов товаров (размеры и цвета)...")

            variant_count = 0

            # Варианты для курток
            for product in products[:4]:  # Первые 4 товара - куртки
                if "jacket" in str(product.images[0]).lower():
                    for size in ["S", "M", "L", "XL", "XXL"]:
                        variant = ProductVariant(
                            product_id=product.id,
                            size=size,
                            color="Черный" if "black" in product.images[0] else
                                  "Красный" if "red" in product.images[0] else
                                  "Фиолетовый" if "purple" in product.images[0] else "Синий",
                            quantity=10,
                            sku=f"JKT-{product.id}-{size}"
                        )
                        session.add(variant)
                        variant_count += 1

            # Варианты для рубашек
            for product in products[4:7]:  # Рубашки
                for size in ["S", "M", "L", "XL"]:
                    for color in ["Белый", "Синий"]:
                        variant = ProductVariant(
                            product_id=product.id,
                            size=size,
                            color=color,
                            quantity=15,
                            sku=f"SHIRT-{product.id}-{size}-{color}"
                        )
                        session.add(variant)
                        variant_count += 1

            # Варианты для брюк
            for product in products[7:10]:  # Брюки
                for size in ["30", "32", "34", "36", "38"]:
                    variant = ProductVariant(
                        product_id=product.id,
                        size=size,
                        color="Черный",
                        quantity=12,
                        sku=f"PANTS-{product.id}-{size}"
                    )
                    session.add(variant)
                    variant_count += 1

            # Варианты для платьев
            for product in products[10:13]:  # Платья
                for size in ["XS", "S", "M", "L"]:
                    for color in ["Черный", "Синий", "Красный"]:
                        variant = ProductVariant(
                            product_id=product.id,
                            size=size,
                            color=color,
                            quantity=8,
                            sku=f"DRESS-{product.id}-{size}-{color}"
                        )
                        session.add(variant)
                        variant_count += 1

            # Варианты для блузок
            for product in products[13:15]:  # Блузки
                for size in ["XS", "S", "M", "L"]:
                    for color in ["Белый", "Бежевый", "Черный"]:
                        variant = ProductVariant(
                            product_id=product.id,
                            size=size,
                            color=color,
                            quantity=10,
                            sku=f"BLOUSE-{product.id}-{size}-{color}"
                        )
                        session.add(variant)
                        variant_count += 1

            # Варианты для юбок
            for product in products[15:17]:  # Юбки
                for size in ["XS", "S", "M", "L"]:
                    variant = ProductVariant(
                        product_id=product.id,
                        size=size,
                        color="Черный",
                        quantity=10,
                        sku=f"SKIRT-{product.id}-{size}"
                    )
                    session.add(variant)
                    variant_count += 1

            # Варианты для аксессуаров (без размеров)
            for product in products[17:]:  # Сумки и рюкзаки
                variant = ProductVariant(
                    product_id=product.id,
                    size="ONE SIZE",
                    color="Черный",
                    quantity=20,
                    sku=f"ACC-{product.id}"
                )
                session.add(variant)
                variant_count += 1

            await session.commit()
            logger.info(f"   ✅ Создано {variant_count} вариантов товаров")

            # ==================== ИТОГИ ====================
            logger.info("\n" + "=" * 60)
            logger.info("✅ ТЕСТОВЫЕ ДАННЫЕ УСПЕШНО ДОБАВЛЕНЫ!")
            logger.info("=" * 60)
            logger.info(f"📁 Категорий: 10 (3 корневых + 7 подкатегорий)")
            logger.info(f"🛍️  Товаров: {len(products)}")
            logger.info(f"   • Куртки: 4 (с галереями по 3 фото)")
            logger.info(f"   • Рубашки: 3")
            logger.info(f"   • Брюки: 3")
            logger.info(f"   • Платья: 3 (с галереями фото)")
            logger.info(f"   • Блузки: 2")
            logger.info(f"   • Юбки: 2")
            logger.info(f"   • Аксессуары: 2")
            logger.info(f"🎨 Вариантов товаров: {variant_count}")
            logger.info(f"💰 Товаров со скидками: {sum(1 for p in products if p.discount_price)}")
            logger.info(f"📸 Товаров с изображениями: {len(products)}")
            logger.info("\n💡 Следующий шаг: запустите create_test_images.py")
            logger.info("   для создания изображений товаров")
            logger.info("=" * 60)

        except Exception as e:
            logger.error(f"❌ Ошибка при добавлении тестовых данных: {e}")
            import traceback
            traceback.print_exc()
            await session.rollback()
            raise
        break  # Выходим из цикла после первой итерации


if __name__ == "__main__":
    asyncio.run(add_test_data())
