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
