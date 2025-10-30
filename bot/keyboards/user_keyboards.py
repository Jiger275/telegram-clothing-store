"""
Клавиатуры для пользователей
"""
from typing import List, Optional
from aiogram.types import ReplyKeyboardMarkup, KeyboardButton, InlineKeyboardMarkup, InlineKeyboardButton
from bot.database.models.category import Category
from bot.database.models.product import Product


def get_main_menu_keyboard(is_admin: bool = False) -> ReplyKeyboardMarkup:
    """
    Главное меню для пользователя

    Args:
        is_admin: Флаг, является ли пользователь администратором

    Returns:
        ReplyKeyboardMarkup с кнопками главного меню
    """
    buttons = [
        [KeyboardButton(text="Каталог"), KeyboardButton(text="Корзина")],
        [KeyboardButton(text="Мои заказы"), KeyboardButton(text="Профиль")],
    ]

    # Добавляем кнопку админ-панели для администраторов
    if is_admin:
        buttons.append([KeyboardButton(text="Админ-панель")])

    return ReplyKeyboardMarkup(
        keyboard=buttons,
        resize_keyboard=True,
        input_field_placeholder="Выберите действие..."
    )


def get_categories_keyboard(
    categories: List[Category],
    parent_id: Optional[int] = None
) -> InlineKeyboardMarkup:
    """
    Клавиатура со списком категорий

    Args:
        categories: Список категорий
        parent_id: ID родительской категории (для кнопки "Назад")

    Returns:
        InlineKeyboardMarkup
    """
    buttons = []

    # Добавляем кнопки категорий по 2 в ряд
    for i in range(0, len(categories), 2):
        row = []
        for j in range(2):
            if i + j < len(categories):
                cat = categories[i + j]
                row.append(InlineKeyboardButton(
                    text=cat.name,
                    callback_data=f"category:{cat.id}"
                ))
        buttons.append(row)

    # Кнопка "Назад" если есть родительская категория
    if parent_id is not None:
        buttons.append([
            InlineKeyboardButton(text="⬅️ Назад", callback_data=f"category:{parent_id}")
        ])
    else:
        buttons.append([
            InlineKeyboardButton(text="🏠 Главное меню", callback_data="main_menu")
        ])

    return InlineKeyboardMarkup(inline_keyboard=buttons)


def get_products_keyboard(
    products: List[Product],
    category_id: int,
    current_page: int = 1,
    total_pages: int = 1
) -> InlineKeyboardMarkup:
    """
    Клавиатура со списком товаров с пагинацией

    Args:
        products: Список товаров
        category_id: ID категории
        current_page: Текущая страница
        total_pages: Всего страниц

    Returns:
        InlineKeyboardMarkup
    """
    buttons = []

    # Добавляем кнопки товаров по 2 в ряд
    for i in range(0, len(products), 2):
        row = []
        for j in range(2):
            if i + j < len(products):
                product = products[i + j]
                row.append(InlineKeyboardButton(
                    text=f"{product.name} - {product.effective_price} ₽",
                    callback_data=f"product:{product.id}"
                ))
        buttons.append(row)

    # Пагинация
    if total_pages > 1:
        pagination_row = []
        if current_page > 1:
            pagination_row.append(InlineKeyboardButton(
                text="◀️",
                callback_data=f"category:{category_id}:page:{current_page - 1}"
            ))
        pagination_row.append(InlineKeyboardButton(
            text=f"{current_page}/{total_pages}",
            callback_data="noop"
        ))
        if current_page < total_pages:
            pagination_row.append(InlineKeyboardButton(
                text="▶️",
                callback_data=f"category:{category_id}:page:{current_page + 1}"
            ))
        buttons.append(pagination_row)

    # Кнопка "Назад к категориям"
    buttons.append([
        InlineKeyboardButton(text="⬅️ К категориям", callback_data="catalog")
    ])

    return InlineKeyboardMarkup(inline_keyboard=buttons)


def get_product_card_keyboard(
    product_id: int,
    has_variants: bool = False,
    category_id: Optional[int] = None
) -> InlineKeyboardMarkup:
    """
    Клавиатура для карточки товара

    Args:
        product_id: ID товара
        has_variants: Есть ли варианты товара
        category_id: ID категории для кнопки "Назад"

    Returns:
        InlineKeyboardMarkup
    """
    buttons = []

    # Если есть варианты, показываем кнопку выбора размера/цвета
    if has_variants:
        buttons.append([
            InlineKeyboardButton(
                text="🛒 Выбрать размер и цвет",
                callback_data=f"product:{product_id}:select_variant"
            )
        ])
    else:
        # Если вариантов нет, сразу добавляем в корзину
        buttons.append([
            InlineKeyboardButton(
                text="🛒 Добавить в корзину",
                callback_data=f"add_to_cart:{product_id}"
            )
        ])

    # Навигация
    nav_row = []
    if category_id:
        nav_row.append(InlineKeyboardButton(
            text="⬅️ Назад",
            callback_data=f"category:{category_id}"
        ))
    nav_row.append(InlineKeyboardButton(
        text="🛍 К категориям",
        callback_data="catalog"
    ))
    buttons.append(nav_row)

    return InlineKeyboardMarkup(inline_keyboard=buttons)


def get_variant_selection_keyboard(
    product_id: int,
    sizes: List[str],
    colors: List[str],
    selected_size: Optional[str] = None,
    selected_color: Optional[str] = None
) -> InlineKeyboardMarkup:
    """
    Клавиатура для выбора размера и цвета

    Args:
        product_id: ID товара
        sizes: Список доступных размеров
        colors: Список доступных цветов
        selected_size: Выбранный размер
        selected_color: Выбранный цвет

    Returns:
        InlineKeyboardMarkup
    """
    buttons = []

    # Размеры
    if sizes:
        size_row = []
        for size in sizes:
            marker = "✓ " if size == selected_size else ""
            size_row.append(InlineKeyboardButton(
                text=f"{marker}{size}",
                callback_data=f"product:{product_id}:size:{size}"
            ))
        buttons.append(size_row)

    # Цвета (если выбран размер)
    if selected_size and colors:
        color_rows = []
        for i in range(0, len(colors), 3):
            row = []
            for j in range(3):
                if i + j < len(colors):
                    color = colors[i + j]
                    marker = "✓ " if color == selected_color else ""
                    row.append(InlineKeyboardButton(
                        text=f"{marker}{color}",
                        callback_data=f"product:{product_id}:color:{color}"
                    ))
            color_rows.append(row)
        buttons.extend(color_rows)

    # Кнопка "Добавить в корзину" если выбраны оба параметра
    if selected_size and selected_color:
        buttons.append([
            InlineKeyboardButton(
                text="🛒 Добавить в корзину",
                callback_data=f"add_to_cart:{product_id}:{selected_size}:{selected_color}"
            )
        ])

    # Кнопка "Назад"
    buttons.append([
        InlineKeyboardButton(
            text="⬅️ Назад к товару",
            callback_data=f"product:{product_id}"
        )
    ])

    return InlineKeyboardMarkup(inline_keyboard=buttons)


def get_cart_keyboard(has_items: bool = False) -> InlineKeyboardMarkup:
    """
    Клавиатура для корзины

    Args:
        has_items: Есть ли товары в корзине

    Returns:
        InlineKeyboardMarkup
    """
    buttons = []

    if has_items:
        buttons.append([
            InlineKeyboardButton(text="📦 Оформить заказ", callback_data="checkout")
        ])
        buttons.append([
            InlineKeyboardButton(text="🗑 Очистить корзину", callback_data="cart:clear")
        ])

    buttons.append([
        InlineKeyboardButton(text="🛍 К каталогу", callback_data="catalog")
    ])

    return InlineKeyboardMarkup(inline_keyboard=buttons)


def get_cart_item_keyboard(cart_item_id: int, quantity: int) -> InlineKeyboardMarkup:
    """
    Клавиатура для управления товаром в корзине

    Args:
        cart_item_id: ID товара в корзине
        quantity: Текущее количество

    Returns:
        InlineKeyboardMarkup
    """
    buttons = [
        [
            InlineKeyboardButton(text="➖", callback_data=f"cart:decrease:{cart_item_id}"),
            InlineKeyboardButton(text=f"{quantity} шт.", callback_data="noop"),
            InlineKeyboardButton(text="➕", callback_data=f"cart:increase:{cart_item_id}"),
        ],
        [
            InlineKeyboardButton(text="🗑 Удалить", callback_data=f"cart:remove:{cart_item_id}")
        ]
    ]

    return InlineKeyboardMarkup(inline_keyboard=buttons)


def get_profile_keyboard() -> InlineKeyboardMarkup:
    """
    Клавиатура для профиля

    Returns:
        InlineKeyboardMarkup
    """
    buttons = [
        [InlineKeyboardButton(text="Назад в меню", callback_data="main_menu")]
    ]

    return InlineKeyboardMarkup(inline_keyboard=buttons)
