"""
Клавиатуры для пользователей
"""
from aiogram.types import ReplyKeyboardMarkup, KeyboardButton, InlineKeyboardMarkup, InlineKeyboardButton


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


def get_catalog_keyboard() -> InlineKeyboardMarkup:
    """
    Клавиатура для каталога (пока заглушка)

    Returns:
        InlineKeyboardMarkup
    """
    buttons = [
        [InlineKeyboardButton(text="Назад в меню", callback_data="main_menu")]
    ]

    return InlineKeyboardMarkup(inline_keyboard=buttons)


def get_cart_keyboard() -> InlineKeyboardMarkup:
    """
    Клавиатура для корзины (пока заглушка)

    Returns:
        InlineKeyboardMarkup
    """
    buttons = [
        [InlineKeyboardButton(text="Очистить корзину", callback_data="cart_clear")],
        [InlineKeyboardButton(text="Назад в меню", callback_data="main_menu")]
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
