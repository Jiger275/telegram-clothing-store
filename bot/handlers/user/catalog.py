"""
Handler for catalog browsing
"""
import math
from aiogram import Router, F
from aiogram.types import Message, CallbackQuery
from sqlalchemy.ext.asyncio import AsyncSession

from bot.database.models.user import User
from bot.services import category_service, product_service
from bot.keyboards.user_keyboards import (
    get_categories_keyboard,
    get_products_keyboard,
    get_main_menu_keyboard
)
from bot.texts.user_messages import (
    CATALOG_EMPTY,
    CATALOG_CATEGORIES,
    CATEGORY_NO_PRODUCTS
)
from bot.utils.logger import setup_logger


logger = setup_logger(__name__)

# Создаем роутер для handlers
router = Router(name="catalog")


@router.message(F.text == "Каталог")
@router.callback_query(F.data == "catalog")
async def show_catalog(
    event: Message | CallbackQuery,
    user: User,
    session: AsyncSession
) -> None:
    """
    Показать каталог - список корневых категорий

    Args:
        event: Сообщение или callback query
        user: Объект пользователя из БД
        session: Сессия БД
    """
    logger.info(f"Пользователь {user.telegram_id} открыл каталог")

    # Получаем корневые категории
    categories = await category_service.get_root_categories(session)

    if not categories:
        text = CATALOG_EMPTY
        keyboard = get_main_menu_keyboard(is_admin=user.is_admin)

        if isinstance(event, Message):
            await event.answer(text=text, reply_markup=keyboard)
        else:
            await event.message.edit_text(text=text)
            await event.answer()
        return

    text = CATALOG_CATEGORIES
    keyboard = get_categories_keyboard(categories)

    if isinstance(event, Message):
        await event.answer(text=text, reply_markup=keyboard)
    else:
        await event.message.edit_text(text=text, reply_markup=keyboard)
        await event.answer()


@router.callback_query(F.data.startswith("category:"))
async def show_category(
    callback: CallbackQuery,
    user: User,
    session: AsyncSession
) -> None:
    """
    Показать категорию - либо подкатегории, либо товары

    Args:
        callback: Callback query
        user: Объект пользователя из БД
        session: Сессия БД
    """
    # Парсим callback data: category:id или category:id:page:N
    parts = callback.data.split(":")
    category_id = int(parts[1])
    page = int(parts[3]) if len(parts) > 3 else 1

    logger.info(
        f"Пользователь {user.telegram_id} открыл категорию {category_id}, "
        f"страница {page}"
    )

    # Получаем категорию
    category = await category_service.get_category_by_id(
        session=session,
        category_id=category_id,
        with_subcategories=True
    )

    if not category:
        await callback.answer("Категория не найдена", show_alert=True)
        return

    # Проверяем, есть ли подкатегории
    subcategories = await category_service.get_subcategories(
        session=session,
        parent_id=category_id
    )

    if subcategories:
        # Если есть подкатегории, показываем их
        text = f"{category.name}\n\nВыберите подкатегорию:"
        keyboard = get_categories_keyboard(
            categories=subcategories,
            parent_id=category.parent_id
        )

        await callback.message.edit_text(text=text, reply_markup=keyboard)
        await callback.answer()
    else:
        # Если подкатегорий нет, показываем товары
        await show_products_in_category(
            callback=callback,
            user=user,
            session=session,
            category=category,
            page=page
        )


async def show_products_in_category(
    callback: CallbackQuery,
    user: User,
    session: AsyncSession,
    category,
    page: int = 1
) -> None:
    """
    Показать товары в категории с пагинацией

    Args:
        callback: Callback query
        user: Объект пользователя из БД
        session: Сессия БД
        category: Объект категории
        page: Номер страницы
    """
    page_size = 6

    # Получаем товары с пагинацией
    products, total_count = await product_service.get_products_by_category(
        session=session,
        category_id=category.id,
        page=page,
        page_size=page_size
    )

    if not products:
        text = f"{category.name}\n\n{CATEGORY_NO_PRODUCTS}"
        keyboard = get_categories_keyboard(
            categories=[],
            parent_id=category.parent_id
        )

        await callback.message.edit_text(text=text, reply_markup=keyboard)
        await callback.answer()
        return

    # Формируем breadcrumbs
    breadcrumbs = await category_service.get_category_breadcrumbs(
        session=session,
        category_id=category.id
    )
    breadcrumb_text = " > ".join([c.name for c in breadcrumbs])

    # Вычисляем общее количество страниц
    total_pages = math.ceil(total_count / page_size)

    text = f"{breadcrumb_text}\n\n"
    text += f"Товары ({total_count}):\n"
    text += "Выберите товар для просмотра:"

    keyboard = get_products_keyboard(
        products=products,
        category_id=category.id,
        current_page=page,
        total_pages=total_pages
    )

    await callback.message.edit_text(text=text, reply_markup=keyboard)
    await callback.answer()
