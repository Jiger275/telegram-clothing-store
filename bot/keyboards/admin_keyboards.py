"""
Клавиатуры для админ-панели
"""
from typing import List, Optional

from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.utils.keyboard import InlineKeyboardBuilder

from bot.database.models.category import Category


def get_admin_main_menu() -> InlineKeyboardMarkup:
    """
    Главное меню админ-панели
    """
    builder = InlineKeyboardBuilder()

    builder.row(
        InlineKeyboardButton(text="📦 Товары", callback_data="admin:products")
    )
    builder.row(
        InlineKeyboardButton(text="📁 Категории", callback_data="admin:categories")
    )
    builder.row(
        InlineKeyboardButton(text="📋 Заказы", callback_data="admin:orders")
    )
    builder.row(
        InlineKeyboardButton(text="📊 Статистика", callback_data="admin:stats")
    )
    builder.row(
        InlineKeyboardButton(text="🔙 Главное меню", callback_data="main_menu")
    )

    return builder.as_markup()


def get_categories_menu(page: int = 1) -> InlineKeyboardMarkup:
    """
    Меню управления категориями
    """
    builder = InlineKeyboardBuilder()

    builder.row(
        InlineKeyboardButton(text="➕ Добавить категорию", callback_data="admin:category:add")
    )
    builder.row(
        InlineKeyboardButton(text="📋 Список категорий", callback_data=f"admin:category:list:{page}")
    )
    builder.row(
        InlineKeyboardButton(text="🔙 Назад в админ-панель", callback_data="admin:panel")
    )

    return builder.as_markup()


def get_category_list_keyboard(
    categories: List[Category],
    page: int = 1,
    total_pages: int = 1
) -> InlineKeyboardMarkup:
    """
    Клавиатура со списком категорий с пагинацией

    Args:
        categories: Список категорий для отображения
        page: Текущая страница
        total_pages: Всего страниц
    """
    builder = InlineKeyboardBuilder()

    # Добавляем кнопки с категориями (по 1 в ряд)
    for category in categories:
        # Формируем текст кнопки
        status_emoji = "✅" if category.is_active else "❌"
        parent_info = f" (➡️ {category.parent.name})" if category.parent else ""
        button_text = f"{status_emoji} {category.name}{parent_info}"

        builder.row(
            InlineKeyboardButton(
                text=button_text,
                callback_data=f"admin:category:view:{category.id}"
            )
        )

    # Пагинация
    if total_pages > 1:
        pagination_buttons = []

        if page > 1:
            pagination_buttons.append(
                InlineKeyboardButton(text="⬅️", callback_data=f"admin:category:list:{page - 1}")
            )

        pagination_buttons.append(
            InlineKeyboardButton(text=f"{page}/{total_pages}", callback_data="noop")
        )

        if page < total_pages:
            pagination_buttons.append(
                InlineKeyboardButton(text="➡️", callback_data=f"admin:category:list:{page + 1}")
            )

        builder.row(*pagination_buttons)

    # Кнопки управления
    builder.row(
        InlineKeyboardButton(text="➕ Добавить", callback_data="admin:category:add")
    )
    builder.row(
        InlineKeyboardButton(text="🔙 Назад", callback_data="admin:categories")
    )

    return builder.as_markup()


def get_category_actions_keyboard(category_id: int, is_active: bool) -> InlineKeyboardMarkup:
    """
    Клавиатура с действиями над категорией

    Args:
        category_id: ID категории
        is_active: Активна ли категория
    """
    builder = InlineKeyboardBuilder()

    builder.row(
        InlineKeyboardButton(
            text="✏️ Изменить название",
            callback_data=f"admin:category:edit_name:{category_id}"
        )
    )
    builder.row(
        InlineKeyboardButton(
            text="📝 Изменить описание",
            callback_data=f"admin:category:edit_desc:{category_id}"
        )
    )
    builder.row(
        InlineKeyboardButton(
            text="📁 Изменить родительскую",
            callback_data=f"admin:category:edit_parent:{category_id}"
        )
    )

    # Активация/деактивация
    if is_active:
        builder.row(
            InlineKeyboardButton(
                text="❌ Деактивировать",
                callback_data=f"admin:category:deactivate:{category_id}"
            )
        )
    else:
        builder.row(
            InlineKeyboardButton(
                text="✅ Активировать",
                callback_data=f"admin:category:activate:{category_id}"
            )
        )

    builder.row(
        InlineKeyboardButton(
            text="🗑 Удалить",
            callback_data=f"admin:category:delete_confirm:{category_id}"
        )
    )
    builder.row(
        InlineKeyboardButton(text="🔙 Назад к списку", callback_data="admin:category:list:1")
    )

    return builder.as_markup()


def get_parent_category_keyboard(
    categories: List[Category],
    exclude_id: Optional[int] = None
) -> InlineKeyboardMarkup:
    """
    Клавиатура для выбора родительской категории

    Args:
        categories: Список доступных категорий
        exclude_id: ID категории, которую нужно исключить (при редактировании)
    """
    builder = InlineKeyboardBuilder()

    # Опция "Без родителя" (корневая категория)
    builder.row(
        InlineKeyboardButton(text="🏠 Без родителя (корневая)", callback_data="admin:category:parent:none")
    )

    # Список доступных родительских категорий
    for category in categories:
        if exclude_id and category.id == exclude_id:
            continue  # Исключаем саму категорию при редактировании

        builder.row(
            InlineKeyboardButton(
                text=f"📁 {category.name}",
                callback_data=f"admin:category:parent:{category.id}"
            )
        )

    builder.row(
        InlineKeyboardButton(text="❌ Отмена", callback_data="admin:categories")
    )

    return builder.as_markup()


def get_delete_confirmation_keyboard(category_id: int) -> InlineKeyboardMarkup:
    """
    Клавиатура подтверждения удаления категории
    """
    builder = InlineKeyboardBuilder()

    builder.row(
        InlineKeyboardButton(
            text="✅ Да, удалить",
            callback_data=f"admin:category:delete:{category_id}"
        ),
        InlineKeyboardButton(
            text="❌ Отмена",
            callback_data=f"admin:category:view:{category_id}"
        )
    )

    return builder.as_markup()


def get_cancel_keyboard(callback_data: str = "admin:categories") -> InlineKeyboardMarkup:
    """
    Простая клавиатура с кнопкой отмены
    """
    builder = InlineKeyboardBuilder()

    builder.row(
        InlineKeyboardButton(text="❌ Отмена", callback_data=callback_data)
    )

    return builder.as_markup()


# ===== Клавиатуры для управления товарами =====


def get_products_menu() -> InlineKeyboardMarkup:
    """
    Меню управления товарами
    """
    builder = InlineKeyboardBuilder()

    builder.row(
        InlineKeyboardButton(text="➕ Добавить товар", callback_data="admin:product:add")
    )
    builder.row(
        InlineKeyboardButton(text="📋 Список товаров", callback_data="admin:product:list:1:all")
    )
    builder.row(
        InlineKeyboardButton(text="🔍 Фильтры", callback_data="admin:product:filters")
    )
    builder.row(
        InlineKeyboardButton(text="🔙 Назад в админ-панель", callback_data="admin:panel")
    )

    return builder.as_markup()


def get_product_filters_keyboard() -> InlineKeyboardMarkup:
    """
    Клавиатура для выбора фильтров товаров
    """
    builder = InlineKeyboardBuilder()

    builder.row(
        InlineKeyboardButton(text="📋 Все товары", callback_data="admin:product:list:1:all")
    )
    builder.row(
        InlineKeyboardButton(text="✅ Только активные", callback_data="admin:product:list:1:active")
    )
    builder.row(
        InlineKeyboardButton(text="❌ Только неактивные", callback_data="admin:product:list:1:inactive")
    )
    builder.row(
        InlineKeyboardButton(text="📁 По категориям", callback_data="admin:product:filter:category")
    )
    builder.row(
        InlineKeyboardButton(text="🔙 Назад", callback_data="admin:products")
    )

    return builder.as_markup()


def get_product_category_filter_keyboard(categories: List[Category]) -> InlineKeyboardMarkup:
    """
    Клавиатура для выбора категории для фильтрации товаров

    Args:
        categories: Список категорий
    """
    builder = InlineKeyboardBuilder()

    # Добавляем кнопки с категориями
    for category in categories:
        status_emoji = "✅" if category.is_active else "❌"
        button_text = f"{status_emoji} {category.name}"

        builder.row(
            InlineKeyboardButton(
                text=button_text,
                callback_data=f"admin:product:list:1:category_{category.id}"
            )
        )

    # Кнопка "Назад"
    builder.row(
        InlineKeyboardButton(text="🔙 Назад к фильтрам", callback_data="admin:product:filters")
    )

    return builder.as_markup()


def get_product_list_keyboard(
    products: List,
    page: int = 1,
    total_pages: int = 1,
    filter_type: str = "all"
) -> InlineKeyboardMarkup:
    """
    Клавиатура со списком товаров с пагинацией

    Args:
        products: Список товаров для отображения
        page: Текущая страница
        total_pages: Всего страниц
        filter_type: Тип фильтра (all, active, inactive, category_X)
    """
    builder = InlineKeyboardBuilder()

    # Добавляем кнопки с товарами (по 1 в ряд)
    for product in products:
        # Формируем текст кнопки
        status_emoji = "✅" if product.is_active else "❌"
        price = f"{product.price:,.0f} ₽"
        button_text = f"{status_emoji} {product.name} - {price}"

        builder.row(
            InlineKeyboardButton(
                text=button_text,
                callback_data=f"admin:product:view:{product.id}"
            )
        )

    # Пагинация
    if total_pages > 1:
        pagination_buttons = []

        if page > 1:
            pagination_buttons.append(
                InlineKeyboardButton(
                    text="⬅️",
                    callback_data=f"admin:product:list:{page - 1}:{filter_type}"
                )
            )

        pagination_buttons.append(
            InlineKeyboardButton(text=f"{page}/{total_pages}", callback_data="noop")
        )

        if page < total_pages:
            pagination_buttons.append(
                InlineKeyboardButton(
                    text="➡️",
                    callback_data=f"admin:product:list:{page + 1}:{filter_type}"
                )
            )

        builder.row(*pagination_buttons)

    # Кнопки управления
    builder.row(
        InlineKeyboardButton(text="➕ Добавить", callback_data="admin:product:add")
    )
    builder.row(
        InlineKeyboardButton(text="🔙 Назад", callback_data="admin:products")
    )

    return builder.as_markup()


def get_product_actions_keyboard(product_id: int, is_active: bool) -> InlineKeyboardMarkup:
    """
    Клавиатура с действиями над товаром

    Args:
        product_id: ID товара
        is_active: Активен ли товар
    """
    builder = InlineKeyboardBuilder()

    builder.row(
        InlineKeyboardButton(
            text="✏️ Изменить название",
            callback_data=f"admin:product:edit_name:{product_id}"
        )
    )
    builder.row(
        InlineKeyboardButton(
            text="📝 Изменить описание",
            callback_data=f"admin:product:edit_desc:{product_id}"
        )
    )
    builder.row(
        InlineKeyboardButton(
            text="📁 Изменить категорию",
            callback_data=f"admin:product:edit_category:{product_id}"
        )
    )
    builder.row(
        InlineKeyboardButton(
            text="💰 Изменить цену",
            callback_data=f"admin:product:edit_price:{product_id}"
        )
    )
    builder.row(
        InlineKeyboardButton(
            text="🏷 Управление скидкой",
            callback_data=f"admin:product:edit_discount:{product_id}"
        )
    )
    builder.row(
        InlineKeyboardButton(
            text="🖼 Управление фото",
            callback_data=f"admin:product:edit_images:{product_id}"
        )
    )
    builder.row(
        InlineKeyboardButton(
            text="📐 Управление вариантами",
            callback_data=f"admin:product:variants:{product_id}"
        )
    )

    # Активация/деактивация
    if is_active:
        builder.row(
            InlineKeyboardButton(
                text="❌ Деактивировать",
                callback_data=f"admin:product:deactivate:{product_id}"
            )
        )
    else:
        builder.row(
            InlineKeyboardButton(
                text="✅ Активировать",
                callback_data=f"admin:product:activate:{product_id}"
            )
        )

    builder.row(
        InlineKeyboardButton(
            text="🗑 Удалить",
            callback_data=f"admin:product:delete_confirm:{product_id}"
        )
    )
    builder.row(
        InlineKeyboardButton(text="🔙 Назад к списку", callback_data="admin:product:list:1:all")
    )

    return builder.as_markup()


def get_product_category_keyboard(categories: List[Category]) -> InlineKeyboardMarkup:
    """
    Клавиатура для выбора категории товара

    Args:
        categories: Список категорий
    """
    builder = InlineKeyboardBuilder()

    for category in categories:
        if category.is_active:  # Показываем только активные категории
            builder.row(
                InlineKeyboardButton(
                    text=f"📁 {category.name}",
                    callback_data=f"admin:product:category:{category.id}"
                )
            )

    builder.row(
        InlineKeyboardButton(text="❌ Отмена", callback_data="admin:products")
    )

    return builder.as_markup()


def get_product_images_keyboard(product_id: int, images_count: int) -> InlineKeyboardMarkup:
    """
    Клавиатура управления изображениями товара

    Args:
        product_id: ID товара
        images_count: Количество изображений
    """
    builder = InlineKeyboardBuilder()

    builder.row(
        InlineKeyboardButton(
            text="➕ Добавить фото",
            callback_data=f"admin:product:add_image:{product_id}"
        )
    )

    if images_count > 0:
        builder.row(
            InlineKeyboardButton(
                text="🗑 Удалить фото",
                callback_data=f"admin:product:delete_images:{product_id}"
            )
        )

    builder.row(
        InlineKeyboardButton(
            text="🔙 Назад к товару",
            callback_data=f"admin:product:view:{product_id}"
        )
    )

    return builder.as_markup()


def get_product_delete_images_keyboard(product_id: int, images: List[str]) -> InlineKeyboardMarkup:
    """
    Клавиатура для выбора фото на удаление

    Args:
        product_id: ID товара
        images: Список имен файлов изображений
    """
    builder = InlineKeyboardBuilder()

    # Добавляем кнопку для каждого фото
    for idx, image in enumerate(images, 1):
        builder.row(
            InlineKeyboardButton(
                text=f"🖼 Фото {idx}",
                callback_data=f"admin:product:delete_image:{product_id}:{idx-1}"
            )
        )

    builder.row(
        InlineKeyboardButton(
            text="🔙 Назад к управлению фото",
            callback_data=f"admin:product:edit_images:{product_id}"
        )
    )

    return builder.as_markup()


def get_product_variants_keyboard(product_id: int, variants: List) -> InlineKeyboardMarkup:
    """
    Клавиатура управления вариантами товара

    Args:
        product_id: ID товара
        variants: Список вариантов
    """
    builder = InlineKeyboardBuilder()

    # Добавляем кнопки для каждого варианта
    for variant in variants:
        variant_text = f"{variant.size or ''} {variant.color or ''} - {variant.quantity} шт."
        builder.row(
            InlineKeyboardButton(
                text=variant_text.strip(),
                callback_data=f"admin:product:variant:view:{variant.id}"
            )
        )

    builder.row(
        InlineKeyboardButton(
            text="➕ Добавить вариант",
            callback_data=f"admin:product:variant:add:{product_id}"
        )
    )
    builder.row(
        InlineKeyboardButton(
            text="🔙 Назад к товару",
            callback_data=f"admin:product:view:{product_id}"
        )
    )

    return builder.as_markup()


def get_variant_actions_keyboard(variant_id: int, product_id: int) -> InlineKeyboardMarkup:
    """
    Клавиатура действий над вариантом товара

    Args:
        variant_id: ID варианта
        product_id: ID товара
    """
    builder = InlineKeyboardBuilder()

    builder.row(
        InlineKeyboardButton(
            text="✏️ Изменить размер",
            callback_data=f"admin:variant:edit_size:{variant_id}"
        )
    )
    builder.row(
        InlineKeyboardButton(
            text="🎨 Изменить цвет",
            callback_data=f"admin:variant:edit_color:{variant_id}"
        )
    )
    builder.row(
        InlineKeyboardButton(
            text="📦 Изменить количество",
            callback_data=f"admin:variant:edit_qty:{variant_id}"
        )
    )
    builder.row(
        InlineKeyboardButton(
            text="🗑 Удалить вариант",
            callback_data=f"admin:variant:delete:{variant_id}"
        )
    )
    builder.row(
        InlineKeyboardButton(
            text="🔙 Назад",
            callback_data=f"admin:product:variants:{product_id}"
        )
    )

    return builder.as_markup()


def get_product_delete_confirmation_keyboard(product_id: int) -> InlineKeyboardMarkup:
    """
    Клавиатура подтверждения удаления товара
    """
    builder = InlineKeyboardBuilder()

    builder.row(
        InlineKeyboardButton(
            text="✅ Да, удалить",
            callback_data=f"admin:product:delete:{product_id}"
        ),
        InlineKeyboardButton(
            text="❌ Отмена",
            callback_data=f"admin:product:view:{product_id}"
        )
    )

    return builder.as_markup()


def get_skip_or_cancel_keyboard(callback_data: str = "admin:products") -> InlineKeyboardMarkup:
    """
    Клавиатура с кнопками "Пропустить" и "Отмена"
    """
    builder = InlineKeyboardBuilder()

    builder.row(
        InlineKeyboardButton(text="➡️ Пропустить", callback_data="skip")
    )
    builder.row(
        InlineKeyboardButton(text="❌ Отмена", callback_data=callback_data)
    )

    return builder.as_markup()


def get_finish_or_cancel_keyboard(callback_data: str = "admin:products") -> InlineKeyboardMarkup:
    """
    Клавиатура с кнопками "Завершить" и "Отмена" (для загрузки фото)
    """
    builder = InlineKeyboardBuilder()

    builder.row(
        InlineKeyboardButton(text="✅ Завершить", callback_data="skip")
    )
    builder.row(
        InlineKeyboardButton(text="❌ Отмена", callback_data=callback_data)
    )

    return builder.as_markup()


def get_finish_or_add_more_keyboard(product_id: int) -> InlineKeyboardMarkup:
    """
    Клавиатура после добавления товара - завершить или добавить варианты
    """
    builder = InlineKeyboardBuilder()

    builder.row(
        InlineKeyboardButton(
            text="➕ Добавить варианты",
            callback_data=f"admin:product:variant:add:{product_id}"
        )
    )
    builder.row(
        InlineKeyboardButton(
            text="✅ Завершить",
            callback_data=f"admin:product:view:{product_id}"
        )
    )

    return builder.as_markup()
