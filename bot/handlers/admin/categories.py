"""
Обработчики управления категориями в админ-панели
"""
from aiogram import Router, F
from aiogram.fsm.context import FSMContext
from aiogram.types import Message, CallbackQuery
from sqlalchemy import select, update, delete
from sqlalchemy.ext.asyncio import AsyncSession

from bot.database.models.category import Category
from bot.filters.admin_filter import IsAdminFilter
from bot.keyboards.admin_keyboards import (
    get_categories_menu,
    get_category_list_keyboard,
    get_category_actions_keyboard,
    get_parent_category_keyboard,
    get_delete_confirmation_keyboard,
    get_cancel_keyboard
)
from bot.services.category_service import (
    get_all_categories,
    get_category_by_id,
    count_products_in_category
)
from bot.states.admin_states import CategoryStates
from bot.texts import admin_messages
from bot.utils.logger import setup_logger


logger = setup_logger(__name__)

# Создаем роутер для управления категориями
router = Router(name="admin_categories")

# Константы
CATEGORIES_PER_PAGE = 10


# ===== Главное меню категорий =====

@router.callback_query(F.data == "admin:categories", IsAdminFilter())
async def callback_categories_menu(callback: CallbackQuery):
    """
    Показать главное меню управления категориями
    """
    logger.info(f"Админ {callback.from_user.id} ({callback.from_user.username}) открыл меню управления категориями")

    await callback.message.edit_text(
        text=admin_messages.CATEGORIES_MENU,
        reply_markup=get_categories_menu()
    )
    await callback.answer()


# ===== Список категорий =====

@router.callback_query(F.data.startswith("admin:category:list:"), IsAdminFilter())
async def callback_category_list(
    callback: CallbackQuery,
    session: AsyncSession
):
    """
    Показать список всех категорий с пагинацией
    """
    # Извлекаем номер страницы из callback_data
    page = int(callback.data.split(":")[-1])

    logger.info(f"Админ {callback.from_user.id} просматривает список категорий (страница {page})")

    # Получаем все категории (включая неактивные для админа)
    all_categories = await get_all_categories(
        session=session,
        parent_id=None,
        active_only=False
    )

    # Также получаем подкатегории
    subcategories = []
    for cat in all_categories:
        subs = await get_all_categories(
            session=session,
            parent_id=cat.id,
            active_only=False
        )
        subcategories.extend(subs)

    # Объединяем все категории
    all_categories.extend(subcategories)

    if not all_categories:
        await callback.message.edit_text(
            text=admin_messages.CATEGORY_LIST_EMPTY,
            reply_markup=get_categories_menu()
        )
        await callback.answer()
        return

    # Подсчитываем статистику
    total = len(all_categories)
    active = sum(1 for c in all_categories if c.is_active)
    inactive = total - active

    # Пагинация
    total_pages = (total + CATEGORIES_PER_PAGE - 1) // CATEGORIES_PER_PAGE
    start_idx = (page - 1) * CATEGORIES_PER_PAGE
    end_idx = start_idx + CATEGORIES_PER_PAGE
    categories_page = all_categories[start_idx:end_idx]

    text = admin_messages.CATEGORY_LIST_HEADER.format(
        total=total,
        active=active,
        inactive=inactive
    )

    await callback.message.edit_text(
        text=text,
        reply_markup=get_category_list_keyboard(
            categories=categories_page,
            page=page,
            total_pages=total_pages
        )
    )
    await callback.answer()


# ===== Просмотр категории =====

@router.callback_query(F.data.startswith("admin:category:view:"), IsAdminFilter())
async def callback_category_view(
    callback: CallbackQuery,
    session: AsyncSession
):
    """
    Показать детальную информацию о категории
    """
    category_id = int(callback.data.split(":")[-1])

    logger.info(f"Админ {callback.from_user.id} просматривает категорию ID={category_id}")

    category = await get_category_by_id(session, category_id)
    if not category:
        logger.warning(f"Категория ID={category_id} не найдена (запрос от админа {callback.from_user.id})")
        await callback.answer(admin_messages.CATEGORY_NOT_FOUND, show_alert=True)
        return

    # Подсчитываем количество товаров
    products_count = await count_products_in_category(session, category_id)

    text = admin_messages.format_category_details(category, products_count)

    await callback.message.edit_text(
        text=text,
        reply_markup=get_category_actions_keyboard(category_id, category.is_active)
    )
    await callback.answer()


# ===== Создание категории =====

@router.callback_query(F.data == "admin:category:add", IsAdminFilter())
async def callback_category_add_start(callback: CallbackQuery, state: FSMContext):
    """
    Начать создание новой категории
    """
    logger.info(f"Админ {callback.from_user.id} начал создание новой категории")

    await state.set_state(CategoryStates.waiting_for_name)

    await callback.message.edit_text(
        text=admin_messages.CATEGORY_ADD_NAME,
        reply_markup=get_cancel_keyboard()
    )
    await callback.answer()


@router.message(CategoryStates.waiting_for_name, IsAdminFilter())
async def process_category_name(message: Message, state: FSMContext):
    """
    Обработать название категории
    """
    name = message.text.strip()

    logger.debug(f"Админ {message.from_user.id} ввел название категории: '{name}'")

    # Валидация
    if len(name) < 2:
        logger.warning(f"Админ {message.from_user.id} ввел слишком короткое название категории: '{name}'")
        await message.answer(admin_messages.CATEGORY_NAME_TOO_SHORT)
        return

    if len(name) > 100:
        logger.warning(f"Админ {message.from_user.id} ввел слишком длинное название категории (длина: {len(name)})")
        await message.answer(admin_messages.CATEGORY_NAME_TOO_LONG)
        return

    # Сохраняем название в состоянии
    await state.update_data(name=name)

    # Переходим к следующему шагу - описание
    await state.set_state(CategoryStates.waiting_for_description)

    await message.answer(
        text=admin_messages.CATEGORY_ADD_DESCRIPTION.format(name=name),
        reply_markup=get_cancel_keyboard()
    )


@router.message(CategoryStates.waiting_for_description, IsAdminFilter())
async def process_category_description(
    message: Message,
    state: FSMContext,
    session: AsyncSession
):
    """
    Обработать описание категории
    """
    description = message.text.strip()

    # Если пользователь ввел "-", пропускаем описание
    if description == "-":
        description = None

    # Сохраняем описание
    await state.update_data(description=description)

    # Получаем все категории для выбора родителя
    categories = await get_all_categories(session, active_only=False)

    # Переходим к выбору родительской категории
    await state.set_state(CategoryStates.waiting_for_parent)

    await message.answer(
        text=admin_messages.format_category_add_parent(categories),
        reply_markup=get_parent_category_keyboard(categories)
    )


@router.callback_query(
    F.data.startswith("admin:category:parent:"),
    CategoryStates.waiting_for_parent,
    IsAdminFilter()
)
async def process_category_parent(
    callback: CallbackQuery,
    state: FSMContext,
    session: AsyncSession
):
    """
    Обработать выбор родительской категории и создать категорию
    """
    # Получаем данные из состояния
    data = await state.get_data()
    name = data["name"]
    description = data.get("description")

    # Определяем родительскую категорию
    parent_value = callback.data.split(":")[-1]
    parent_id = None if parent_value == "none" else int(parent_value)

    # Создаем категорию
    try:
        new_category = Category(
            name=name,
            description=description,
            parent_id=parent_id,
            is_active=True
        )

        session.add(new_category)
        await session.commit()
        await session.refresh(new_category)

        logger.info(
            f"✅ Админ {callback.from_user.id} создал категорию: '{name}' (ID={new_category.id}, "
            f"parent_id={parent_id}, description={'есть' if description else 'нет'})"
        )

        await callback.message.edit_text(
            text=admin_messages.CATEGORY_CREATED.format(name=name),
            reply_markup=get_categories_menu()
        )

        # Очищаем состояние
        await state.clear()

    except Exception as e:
        logger.exception(f"❌ ОШИБКА: Админ {callback.from_user.id} не смог создать категорию '{name}': {e}")
        await callback.message.edit_text(
            text=admin_messages.ERROR_GENERIC,
            reply_markup=get_categories_menu()
        )
        await state.clear()

    await callback.answer()


# ===== Редактирование названия =====

@router.callback_query(F.data.startswith("admin:category:edit_name:"), IsAdminFilter())
async def callback_category_edit_name_start(
    callback: CallbackQuery,
    state: FSMContext,
    session: AsyncSession
):
    """
    Начать редактирование названия категории
    """
    category_id = int(callback.data.split(":")[-1])

    logger.info(f"Админ {callback.from_user.id} начал редактирование названия категории ID={category_id}")

    category = await get_category_by_id(session, category_id)
    if not category:
        logger.warning(f"Категория ID={category_id} не найдена при попытке редактирования")
        await callback.answer(admin_messages.CATEGORY_NOT_FOUND, show_alert=True)
        return

    # Сохраняем ID категории в состоянии
    await state.update_data(category_id=category_id)
    await state.set_state(CategoryStates.editing_name)

    await callback.message.edit_text(
        text=admin_messages.CATEGORY_EDIT_NAME.format(current_name=category.name),
        reply_markup=get_cancel_keyboard(f"admin:category:view:{category_id}")
    )
    await callback.answer()


@router.message(CategoryStates.editing_name, IsAdminFilter())
async def process_category_name_edit(
    message: Message,
    state: FSMContext,
    session: AsyncSession
):
    """
    Обработать новое название категории
    """
    new_name = message.text.strip()

    # Валидация
    if len(new_name) < 2:
        await message.answer(admin_messages.CATEGORY_NAME_TOO_SHORT)
        return

    if len(new_name) > 100:
        await message.answer(admin_messages.CATEGORY_NAME_TOO_LONG)
        return

    # Получаем ID категории из состояния
    data = await state.get_data()
    category_id = data["category_id"]

    # Обновляем название
    try:
        # Получаем старое название для логирования
        old_category = await get_category_by_id(session, category_id)
        old_name = old_category.name if old_category else "Unknown"

        await session.execute(
            update(Category)
            .where(Category.id == category_id)
            .values(name=new_name)
        )
        await session.commit()

        logger.info(f"✅ Админ {message.from_user.id} изменил название категории ID={category_id}: '{old_name}' → '{new_name}'")

        await message.answer(
            text=admin_messages.CATEGORY_NAME_UPDATED.format(new_name=new_name),
            reply_markup=get_category_actions_keyboard(category_id, True)
        )

        await state.clear()

    except Exception as e:
        logger.exception(f"❌ ОШИБКА: Не удалось обновить название категории ID={category_id}: {e}")
        await message.answer(admin_messages.ERROR_GENERIC)
        await state.clear()


# ===== Редактирование описания =====

@router.callback_query(F.data.startswith("admin:category:edit_desc:"), IsAdminFilter())
async def callback_category_edit_description_start(
    callback: CallbackQuery,
    state: FSMContext,
    session: AsyncSession
):
    """
    Начать редактирование описания категории
    """
    category_id = int(callback.data.split(":")[-1])

    category = await get_category_by_id(session, category_id)
    if not category:
        await callback.answer(admin_messages.CATEGORY_NOT_FOUND, show_alert=True)
        return

    await state.update_data(category_id=category_id)
    await state.set_state(CategoryStates.editing_description)

    current_desc = category.description or "<i>Отсутствует</i>"

    await callback.message.edit_text(
        text=admin_messages.CATEGORY_EDIT_DESCRIPTION.format(
            current_description=current_desc
        ),
        reply_markup=get_cancel_keyboard(f"admin:category:view:{category_id}")
    )
    await callback.answer()


@router.message(CategoryStates.editing_description, IsAdminFilter())
async def process_category_description_edit(
    message: Message,
    state: FSMContext,
    session: AsyncSession
):
    """
    Обработать новое описание категории
    """
    new_description = message.text.strip()

    # Если пользователь ввел "-", удаляем описание
    if new_description == "-":
        new_description = None

    data = await state.get_data()
    category_id = data["category_id"]

    try:
        await session.execute(
            update(Category)
            .where(Category.id == category_id)
            .values(description=new_description)
        )
        await session.commit()

        logger.info(f"Обновлено описание категории {category_id}")

        category = await get_category_by_id(session, category_id)

        await message.answer(
            text=admin_messages.CATEGORY_DESCRIPTION_UPDATED,
            reply_markup=get_category_actions_keyboard(category_id, category.is_active)
        )

        await state.clear()

    except Exception as e:
        logger.exception(f"Ошибка при обновлении описания: {e}")
        await message.answer(admin_messages.ERROR_GENERIC)
        await state.clear()


# ===== Редактирование родительской категории =====

@router.callback_query(F.data.startswith("admin:category:edit_parent:"), IsAdminFilter())
async def callback_category_edit_parent_start(
    callback: CallbackQuery,
    state: FSMContext,
    session: AsyncSession
):
    """
    Начать редактирование родительской категории
    """
    category_id = int(callback.data.split(":")[-1])

    category = await get_category_by_id(session, category_id)
    if not category:
        await callback.answer(admin_messages.CATEGORY_NOT_FOUND, show_alert=True)
        return

    # Получаем все категории, исключая текущую
    categories = await get_all_categories(session, active_only=False)

    await state.update_data(category_id=category_id)
    await state.set_state(CategoryStates.editing_parent)

    await callback.message.edit_text(
        text="Выберите новую родительскую категорию:",
        reply_markup=get_parent_category_keyboard(categories, exclude_id=category_id)
    )
    await callback.answer()


@router.callback_query(
    F.data.startswith("admin:category:parent:"),
    CategoryStates.editing_parent,
    IsAdminFilter()
)
async def process_category_parent_edit(
    callback: CallbackQuery,
    state: FSMContext,
    session: AsyncSession
):
    """
    Обработать выбор новой родительской категории
    """
    data = await state.get_data()
    category_id = data["category_id"]

    parent_value = callback.data.split(":")[-1]
    parent_id = None if parent_value == "none" else int(parent_value)

    try:
        await session.execute(
            update(Category)
            .where(Category.id == category_id)
            .values(parent_id=parent_id)
        )
        await session.commit()

        logger.info(f"Обновлена родительская категория для {category_id}: {parent_id}")

        category = await get_category_by_id(session, category_id)

        await callback.message.edit_text(
            text=admin_messages.CATEGORY_PARENT_UPDATED,
            reply_markup=get_category_actions_keyboard(category_id, category.is_active)
        )

        await state.clear()

    except Exception as e:
        logger.exception(f"Ошибка при обновлении родительской категории: {e}")
        await callback.message.edit_text(admin_messages.ERROR_GENERIC)
        await state.clear()

    await callback.answer()


# ===== Активация/деактивация =====

@router.callback_query(F.data.startswith("admin:category:activate:"), IsAdminFilter())
async def callback_category_activate(
    callback: CallbackQuery,
    session: AsyncSession
):
    """
    Активировать категорию
    """
    category_id = int(callback.data.split(":")[-1])

    category = await get_category_by_id(session, category_id)
    if not category:
        logger.warning(f"Попытка активации несуществующей категории ID={category_id}")
        await callback.answer(admin_messages.CATEGORY_NOT_FOUND, show_alert=True)
        return

    try:
        await session.execute(
            update(Category)
            .where(Category.id == category_id)
            .values(is_active=True)
        )
        await session.commit()

        logger.info(f"✅ Админ {callback.from_user.id} АКТИВИРОВАЛ категорию '{category.name}' (ID={category_id})")

        await callback.message.edit_text(
            text=admin_messages.CATEGORY_ACTIVATED.format(name=category.name),
            reply_markup=get_category_actions_keyboard(category_id, True)
        )

    except Exception as e:
        logger.exception(f"❌ ОШИБКА при активации категории ID={category_id}: {e}")
        await callback.answer(admin_messages.ERROR_GENERIC, show_alert=True)

    await callback.answer()


@router.callback_query(F.data.startswith("admin:category:deactivate:"), IsAdminFilter())
async def callback_category_deactivate(
    callback: CallbackQuery,
    session: AsyncSession
):
    """
    Деактивировать категорию
    """
    category_id = int(callback.data.split(":")[-1])

    category = await get_category_by_id(session, category_id)
    if not category:
        logger.warning(f"Попытка деактивации несуществующей категории ID={category_id}")
        await callback.answer(admin_messages.CATEGORY_NOT_FOUND, show_alert=True)
        return

    try:
        await session.execute(
            update(Category)
            .where(Category.id == category_id)
            .values(is_active=False)
        )
        await session.commit()

        logger.info(f"⚠️ Админ {callback.from_user.id} ДЕАКТИВИРОВАЛ категорию '{category.name}' (ID={category_id})")

        await callback.message.edit_text(
            text=admin_messages.CATEGORY_DEACTIVATED.format(name=category.name),
            reply_markup=get_category_actions_keyboard(category_id, False)
        )

    except Exception as e:
        logger.exception(f"❌ ОШИБКА при деактивации категории ID={category_id}: {e}")
        await callback.answer(admin_messages.ERROR_GENERIC, show_alert=True)

    await callback.answer()


# ===== Удаление категории =====

@router.callback_query(F.data.startswith("admin:category:delete_confirm:"), IsAdminFilter())
async def callback_category_delete_confirm(
    callback: CallbackQuery,
    session: AsyncSession
):
    """
    Показать подтверждение удаления категории
    """
    category_id = int(callback.data.split(":")[-1])

    category = await get_category_by_id(session, category_id)
    if not category:
        await callback.answer(admin_messages.CATEGORY_NOT_FOUND, show_alert=True)
        return

    # Проверяем количество товаров
    products_count = await count_products_in_category(session, category_id)

    # Проверяем наличие подкатегорий
    subcategories = await get_all_categories(session, parent_id=category_id, active_only=False)
    has_children = len(subcategories) > 0

    # Формируем предупреждение
    warning = ""
    if products_count > 0:
        warning = admin_messages.CATEGORY_DELETE_WARNING_HAS_PRODUCTS
    if has_children:
        warning += "\n" + admin_messages.CATEGORY_DELETE_WARNING_HAS_CHILDREN

    text = admin_messages.CATEGORY_DELETE_CONFIRM.format(
        name=category.name,
        products_count=products_count,
        warning=warning
    )

    await callback.message.edit_text(
        text=text,
        reply_markup=get_delete_confirmation_keyboard(category_id)
    )
    await callback.answer()


@router.callback_query(F.data.startswith("admin:category:delete:"), IsAdminFilter())
async def callback_category_delete(
    callback: CallbackQuery,
    session: AsyncSession
):
    """
    Удалить категорию
    """
    category_id = int(callback.data.split(":")[-1])

    category = await get_category_by_id(session, category_id)
    if not category:
        logger.warning(f"Попытка удаления несуществующей категории ID={category_id}")
        await callback.answer(admin_messages.CATEGORY_NOT_FOUND, show_alert=True)
        return

    category_name = category.name

    try:
        # Подсчитываем количество товаров для логирования
        products_count = await count_products_in_category(session, category_id)

        await session.execute(
            delete(Category).where(Category.id == category_id)
        )
        await session.commit()

        logger.warning(
            f"🗑️ Админ {callback.from_user.id} УДАЛИЛ категорию '{category_name}' "
            f"(ID={category_id}, товаров было: {products_count})"
        )

        await callback.message.edit_text(
            text=admin_messages.CATEGORY_DELETED.format(name=category_name),
            reply_markup=get_categories_menu()
        )

    except Exception as e:
        logger.exception(f"❌ ОШИБКА при удалении категории ID={category_id} ('{category_name}'): {e}")
        await callback.message.edit_text(
            text=admin_messages.CATEGORY_DELETE_ERROR,
            reply_markup=get_categories_menu()
        )

    await callback.answer()


# ===== Отмена операций =====

@router.callback_query(F.data == "admin:categories", F.func(lambda c: c.message))
async def callback_cancel_operation(callback: CallbackQuery, state: FSMContext):
    """
    Отменить текущую операцию и вернуться в меню категорий
    """
    await state.clear()

    await callback.message.edit_text(
        text=admin_messages.CATEGORIES_MENU,
        reply_markup=get_categories_menu()
    )
    await callback.answer()


# Обработчик для noop (пустой callback)
@router.callback_query(F.data == "noop")
async def callback_noop(callback: CallbackQuery):
    """
    Пустой callback (например, для индикатора страниц)
    """
    await callback.answer()
