"""
Обработчики управления товарами в админ-панели
"""
from decimal import Decimal, InvalidOperation
from typing import Optional
import math

from aiogram import Router, F, Bot
from aiogram.types import Message, CallbackQuery
from aiogram.fsm.context import FSMContext
from sqlalchemy.ext.asyncio import AsyncSession

from bot.filters.admin_filter import IsAdminFilter
from bot.keyboards import admin_keyboards
from bot.texts import admin_messages
from bot.states.admin_states import ProductStates
from bot.services import product_service, category_service, image_service
from bot.utils.logger import setup_logger


logger = setup_logger(__name__)

# Создаем роутер для управления товарами
router = Router(name="admin_products")


# ===== Главное меню товаров =====

@router.callback_query(F.data == "admin:products", IsAdminFilter())
async def callback_products_menu(callback: CallbackQuery, state: FSMContext):
    """
    Обработчик перехода в меню управления товарами
    Также используется для отмены операций
    """
    current_state = await state.get_state()

    # Если есть активное состояние FSM, очищаем его (отмена операции)
    if current_state:
        await state.clear()
        logger.debug(f"Отменено состояние {current_state}, возврат в меню товаров")
    else:
        logger.info(f"Админ {callback.from_user.id} ({callback.from_user.username}) открыл меню управления товарами")

    await callback.message.edit_text(
        text=admin_messages.PRODUCTS_MENU,
        reply_markup=admin_keyboards.get_products_menu()
    )
    await callback.answer()


@router.callback_query(F.data == "admin:product:filters", IsAdminFilter())
async def callback_product_filters(callback: CallbackQuery):
    """
    Обработчик выбора фильтров товаров
    """
    await callback.message.edit_text(
        text="<b>🔍 Выберите фильтр:</b>",
        reply_markup=admin_keyboards.get_product_filters_keyboard()
    )
    await callback.answer()


@router.callback_query(F.data == "admin:product:filter:category", IsAdminFilter())
async def callback_product_filter_by_category(
    callback: CallbackQuery,
    session: AsyncSession
):
    """
    Обработчик выбора категории для фильтрации товаров
    """
    # Получаем все категории (включая неактивные для админа)
    categories = await category_service.get_all_categories(session, active_only=False)

    if not categories:
        await callback.answer(
            "Категории не найдены",
            show_alert=True
        )
        return

    await callback.message.edit_text(
        text="<b>📁 Выберите категорию для фильтрации:</b>",
        reply_markup=admin_keyboards.get_product_category_filter_keyboard(categories)
    )
    await callback.answer()


# ===== Просмотр списка товаров =====

@router.callback_query(F.data.startswith("admin:product:list:"), IsAdminFilter())
async def callback_product_list(
    callback: CallbackQuery,
    session: AsyncSession
):
    """
    Обработчик просмотра списка товаров с пагинацией и фильтрами
    Format: admin:product:list:page:filter_type
    """
    parts = callback.data.split(":")
    page = int(parts[3])
    filter_type = parts[4]  # all, active, inactive, category_X

    logger.info(f"Админ {callback.from_user.id} просматривает список товаров (страница {page}, фильтр: {filter_type})")

    # Определяем параметры фильтрации
    active_only = None
    category_id = None

    if filter_type == "active":
        active_only = True
    elif filter_type == "inactive":
        active_only = False
    elif filter_type.startswith("category_"):
        category_id = int(filter_type.split("_")[1])

    # Получаем товары с пагинацией
    page_size = 10
    products, total_count = await product_service.get_all_products(
        session=session,
        page=page,
        page_size=page_size,
        category_id=category_id,
        active_only=active_only
    )

    # Проверяем, есть ли товары
    if total_count == 0:
        await callback.message.edit_text(
            text=admin_messages.PRODUCT_LIST_EMPTY,
            reply_markup=admin_keyboards.get_products_menu()
        )
        await callback.answer()
        return

    # Подсчитываем активные и неактивные
    all_products, _ = await product_service.get_all_products(
        session=session, page=1, page_size=999999, active_only=None
    )
    active_count = sum(1 for p in all_products if p.is_active)
    inactive_count = len(all_products) - active_count

    # Формируем текст заголовка
    header_text = admin_messages.PRODUCT_LIST_HEADER.format(
        total=total_count,
        active=active_count,
        inactive=inactive_count
    )

    # Вычисляем общее количество страниц
    total_pages = math.ceil(total_count / page_size)

    await callback.message.edit_text(
        text=header_text,
        reply_markup=admin_keyboards.get_product_list_keyboard(
            products=products,
            page=page,
            total_pages=total_pages,
            filter_type=filter_type
        )
    )
    await callback.answer()


# ===== Просмотр товара =====

@router.callback_query(F.data.startswith("admin:product:view:"), IsAdminFilter())
async def callback_product_view(
    callback: CallbackQuery,
    session: AsyncSession
):
    """
    Обработчик просмотра деталей товара
    """
    product_id = int(callback.data.split(":")[3])

    # Получаем товар с вариантами
    product = await product_service.get_product_by_id(
        session=session,
        product_id=product_id,
        with_variants=True
    )

    if not product:
        await callback.answer(
            admin_messages.PRODUCT_NOT_FOUND,
            show_alert=True
        )
        return

    # Формируем текст с деталями товара
    variants_count = len(product.variants) if product.variants else 0
    text = admin_messages.format_product_details(product, variants_count)

    await callback.message.edit_text(
        text=text,
        reply_markup=admin_keyboards.get_product_actions_keyboard(
            product_id=product_id,
            is_active=product.is_active
        )
    )
    await callback.answer()


# ===== Добавление товара (FSM) =====

@router.callback_query(F.data == "admin:product:add", IsAdminFilter())
async def callback_product_add_start(
    callback: CallbackQuery,
    state: FSMContext,
    session: AsyncSession
):
    """
    Начало процесса добавления товара - выбор категории
    """
    logger.info(f"Админ {callback.from_user.id} начал добавление нового товара")

    # Получаем активные категории
    categories = await category_service.get_active_categories(session)

    if not categories:
        logger.warning(f"Админ {callback.from_user.id} попытался добавить товар, но нет активных категорий")
        await callback.answer(
            admin_messages.NO_ACTIVE_CATEGORIES,
            show_alert=True
        )
        return

    await state.set_state(ProductStates.waiting_for_category)

    await callback.message.edit_text(
        text=admin_messages.PRODUCT_ADD_SELECT_CATEGORY,
        reply_markup=admin_keyboards.get_product_category_keyboard(categories)
    )
    await callback.answer()


@router.callback_query(
    F.data.startswith("admin:product:category:"),
    ProductStates.waiting_for_category,
    IsAdminFilter()
)
async def callback_product_add_category_selected(
    callback: CallbackQuery,
    state: FSMContext,
    session: AsyncSession
):
    """
    Категория выбрана - переходим к вводу названия
    """
    category_id = int(callback.data.split(":")[3])

    # Получаем категорию для отображения названия
    category = await category_service.get_category_by_id(session, category_id)

    if not category:
        await callback.answer("Категория не найдена", show_alert=True)
        await state.clear()
        return

    # Сохраняем категорию в FSM
    await state.update_data(category_id=category_id, category_name=category.name)
    await state.set_state(ProductStates.waiting_for_name)

    await callback.message.edit_text(
        text=admin_messages.PRODUCT_ADD_NAME.format(category_name=category.name),
        reply_markup=admin_keyboards.get_cancel_keyboard("admin:products")
    )
    await callback.answer()


@router.message(ProductStates.waiting_for_name, IsAdminFilter())
async def message_product_add_name(
    message: Message,
    state: FSMContext
):
    """
    Получено название товара - переходим к описанию
    """
    name = message.text.strip()

    # Валидация названия
    if len(name) < 3:
        await message.answer(admin_messages.PRODUCT_NAME_TOO_SHORT)
        return

    if len(name) > 255:
        await message.answer(admin_messages.PRODUCT_NAME_TOO_LONG)
        return

    # Сохраняем название
    await state.update_data(name=name)
    await state.set_state(ProductStates.waiting_for_description)

    await message.answer(
        text=admin_messages.PRODUCT_ADD_DESCRIPTION.format(name=name),
        reply_markup=admin_keyboards.get_skip_or_cancel_keyboard("admin:products")
    )


@router.callback_query(
    F.data == "skip",
    ProductStates.waiting_for_description,
    IsAdminFilter()
)
async def callback_product_skip_description(
    callback: CallbackQuery,
    state: FSMContext
):
    """
    Пропуск описания товара - переходим к цене
    """
    # Сохраняем пустое описание
    await state.update_data(description=None)
    await state.set_state(ProductStates.waiting_for_price)

    data = await state.get_data()
    await callback.message.edit_text(
        text=admin_messages.PRODUCT_ADD_PRICE.format(name=data['name']),
        reply_markup=admin_keyboards.get_cancel_keyboard("admin:products")
    )
    await callback.answer()


@router.message(ProductStates.waiting_for_description, IsAdminFilter())
async def message_product_add_description(
    message: Message,
    state: FSMContext
):
    """
    Получено описание товара - переходим к цене
    """
    description = message.text.strip()

    # Если пользователь отправил "-", пропускаем описание
    if description == "-":
        description = None

    # Сохраняем описание
    await state.update_data(description=description)
    await state.set_state(ProductStates.waiting_for_price)

    data = await state.get_data()
    await message.answer(
        text=admin_messages.PRODUCT_ADD_PRICE.format(name=data['name']),
        reply_markup=admin_keyboards.get_cancel_keyboard("admin:products")
    )


@router.message(ProductStates.waiting_for_price, IsAdminFilter())
async def message_product_add_price(
    message: Message,
    state: FSMContext
):
    """
    Получена цена товара - переходим к загрузке фото
    """
    price_text = message.text.strip()

    # Валидация цены
    try:
        price = Decimal(price_text)
        if price <= 0:
            raise ValueError("Price must be positive")
    except (ValueError, InvalidOperation):
        await message.answer(admin_messages.PRODUCT_PRICE_INVALID)
        return

    # Сохраняем цену
    await state.update_data(price=price, images=[])
    await state.set_state(ProductStates.waiting_for_images)

    data = await state.get_data()
    await message.answer(
        text=admin_messages.PRODUCT_ADD_IMAGES.format(
            name=data['name'],
            price=price,
            count=0
        ),
        reply_markup=admin_keyboards.get_finish_or_cancel_keyboard("admin:products")
    )


@router.message(
    ProductStates.waiting_for_images,
    F.photo,
    IsAdminFilter()
)
async def message_product_add_photo(
    message: Message,
    state: FSMContext,
    bot: Bot
):
    """
    Получено фото товара - сохраняем и ждем следующее или завершение
    """
    # Получаем самое большое фото
    photo = message.photo[-1]

    # Сохраняем фото на диск
    filename = await image_service.save_photo(photo, bot)

    if not filename:
        await message.answer(admin_messages.PRODUCT_IMAGE_ADD_ERROR)
        return

    # Добавляем filename в список
    data = await state.get_data()
    images = data.get('images', [])
    images.append(filename)
    await state.update_data(images=images)

    # Сообщаем об успехе и показываем обновленный счетчик с кнопкой "Завершить"
    await message.answer(
        text=admin_messages.PRODUCT_ADD_IMAGES.format(
            name=data['name'],
            price=data['price'],
            count=len(images)
        ),
        reply_markup=admin_keyboards.get_finish_or_cancel_keyboard("admin:products")
    )


@router.callback_query(
    F.data == "skip",
    ProductStates.waiting_for_images,
    IsAdminFilter()
)
async def callback_product_skip_images(
    callback: CallbackQuery,
    state: FSMContext,
    session: AsyncSession
):
    """
    Пропуск загрузки фото - создаем товар без фото или завершаем загрузку
    """
    data = await state.get_data()
    images = data.get('images', [])

    # Если нет ни одного фото, запрашиваем хотя бы одно
    if len(images) == 0:
        await callback.answer(
            "Загрузите хотя бы одно фото товара",
            show_alert=True
        )
        return

    # Создаем товар
    await _create_product_from_state(callback, state, session)


async def _create_product_from_state(
    callback: CallbackQuery,
    state: FSMContext,
    session: AsyncSession
):
    """
    Вспомогательная функция для создания товара из данных FSM
    """
    data = await state.get_data()

    try:
        # Создаем товар
        product = await product_service.create_product(
            session=session,
            category_id=data['category_id'],
            name=data['name'],
            description=data.get('description'),
            price=data['price'],
            images=data.get('images', [])
        )

        logger.info(
            f"✅ Админ {callback.from_user.id} создал товар: '{product.name}' (ID={product.id}, "
            f"category_id={data['category_id']}, цена={data['price']}, фото={len(data.get('images', []))})"
        )

        # Очищаем состояние
        await state.clear()

        # Сообщаем об успехе
        await callback.message.edit_text(
            text=admin_messages.PRODUCT_CREATED.format(name=product.name),
            reply_markup=admin_keyboards.get_finish_or_add_more_keyboard(product.id)
        )
        await callback.answer()

    except Exception as e:
        logger.exception(f"❌ ОШИБКА: Админ {callback.from_user.id} не смог создать товар '{data.get('name', 'Unknown')}': {e}")
        await callback.answer(
            admin_messages.ERROR_GENERIC,
            show_alert=True
        )
        await state.clear()


# ===== Редактирование товара =====

@router.callback_query(F.data.startswith("admin:product:edit_name:"), IsAdminFilter())
async def callback_product_edit_name_start(
    callback: CallbackQuery,
    state: FSMContext,
    session: AsyncSession
):
    """
    Начало редактирования названия товара
    """
    product_id = int(callback.data.split(":")[3])

    product = await product_service.get_product_by_id(session, product_id, with_variants=False)
    if not product:
        await callback.answer(admin_messages.PRODUCT_NOT_FOUND, show_alert=True)
        return

    await state.set_state(ProductStates.editing_name)
    await state.update_data(product_id=product_id)

    await callback.message.edit_text(
        text=admin_messages.PRODUCT_EDIT_NAME.format(current_name=product.name),
        reply_markup=admin_keyboards.get_cancel_keyboard(f"admin:product:view:{product_id}")
    )
    await callback.answer()


@router.message(ProductStates.editing_name, IsAdminFilter())
async def message_product_edit_name(
    message: Message,
    state: FSMContext,
    session: AsyncSession
):
    """
    Обработка нового названия товара
    """
    new_name = message.text.strip()

    # Валидация
    if len(new_name) < 3:
        await message.answer(admin_messages.PRODUCT_NAME_TOO_SHORT)
        return

    if len(new_name) > 255:
        await message.answer(admin_messages.PRODUCT_NAME_TOO_LONG)
        return

    data = await state.get_data()
    product_id = data['product_id']

    # Обновляем товар
    product = await product_service.update_product(
        session=session,
        product_id=product_id,
        name=new_name
    )

    if product:
        await message.answer(
            admin_messages.PRODUCT_NAME_UPDATED.format(new_name=new_name),
            reply_markup=admin_keyboards.get_product_actions_keyboard(
                product_id=product_id,
                is_active=product.is_active
            )
        )
    else:
        await message.answer(admin_messages.PRODUCT_NOT_FOUND)

    await state.clear()


@router.callback_query(F.data.startswith("admin:product:edit_desc:"), IsAdminFilter())
async def callback_product_edit_desc_start(
    callback: CallbackQuery,
    state: FSMContext,
    session: AsyncSession
):
    """
    Начало редактирования описания товара
    """
    product_id = int(callback.data.split(":")[3])

    product = await product_service.get_product_by_id(session, product_id, with_variants=False)
    if not product:
        await callback.answer(admin_messages.PRODUCT_NOT_FOUND, show_alert=True)
        return

    await state.set_state(ProductStates.editing_description)
    await state.update_data(product_id=product_id)

    current_desc = product.description if product.description else "<i>Нет описания</i>"

    await callback.message.edit_text(
        text=admin_messages.PRODUCT_EDIT_DESCRIPTION.format(current_description=current_desc),
        reply_markup=admin_keyboards.get_cancel_keyboard(f"admin:product:view:{product_id}")
    )
    await callback.answer()


@router.message(ProductStates.editing_description, IsAdminFilter())
async def message_product_edit_description(
    message: Message,
    state: FSMContext,
    session: AsyncSession
):
    """
    Обработка нового описания товара
    """
    new_description = message.text.strip()

    data = await state.get_data()
    product_id = data['product_id']

    # Обновляем товар
    product = await product_service.update_product(
        session=session,
        product_id=product_id,
        description=new_description if new_description != "-" else None
    )

    if product:
        await message.answer(
            admin_messages.PRODUCT_DESCRIPTION_UPDATED,
            reply_markup=admin_keyboards.get_product_actions_keyboard(
                product_id=product_id,
                is_active=product.is_active
            )
        )
    else:
        await message.answer(admin_messages.PRODUCT_NOT_FOUND)

    await state.clear()


@router.callback_query(F.data.startswith("admin:product:edit_category:"), IsAdminFilter())
async def callback_product_edit_category_start(
    callback: CallbackQuery,
    state: FSMContext,
    session: AsyncSession
):
    """
    Начало редактирования категории товара
    """
    product_id = int(callback.data.split(":")[3])

    product = await product_service.get_product_by_id(session, product_id, with_variants=False)
    if not product:
        await callback.answer(admin_messages.PRODUCT_NOT_FOUND, show_alert=True)
        return

    # Получаем все активные категории
    categories = await category_service.get_active_categories(session)

    if not categories:
        await callback.answer(admin_messages.NO_ACTIVE_CATEGORIES, show_alert=True)
        return

    await state.set_state(ProductStates.editing_category)
    await state.update_data(product_id=product_id)

    current_category = product.category.name if hasattr(product, 'category') and product.category else "Без категории"

    await callback.message.edit_text(
        text=admin_messages.PRODUCT_EDIT_CATEGORY.format(
            product_name=product.name,
            current_category=current_category
        ),
        reply_markup=admin_keyboards.get_product_category_keyboard(categories)
    )
    await callback.answer()


@router.callback_query(
    F.data.startswith("admin:product:category:"),
    ProductStates.editing_category,
    IsAdminFilter()
)
async def callback_product_edit_category_selected(
    callback: CallbackQuery,
    state: FSMContext,
    session: AsyncSession
):
    """
    Обработка выбора новой категории для товара
    """
    category_id = int(callback.data.split(":")[3])

    data = await state.get_data()
    product_id = data['product_id']

    # Получаем категорию для отображения названия
    category = await category_service.get_category_by_id(session, category_id)

    if not category:
        await callback.answer("Категория не найдена", show_alert=True)
        await state.clear()
        return

    # Обновляем товар
    product = await product_service.update_product(
        session=session,
        product_id=product_id,
        category_id=category_id
    )

    if product:
        logger.info(
            f"✅ Админ {callback.from_user.id} изменил категорию товара ID={product_id} "
            f"на '{category.name}' (ID={category_id})"
        )
        await callback.message.edit_text(
            admin_messages.PRODUCT_CATEGORY_UPDATED.format(new_category=category.name),
            reply_markup=admin_keyboards.get_product_actions_keyboard(
                product_id=product_id,
                is_active=product.is_active
            )
        )
    else:
        await callback.message.edit_text(admin_messages.PRODUCT_NOT_FOUND)

    await state.clear()
    await callback.answer()


@router.callback_query(F.data.startswith("admin:product:edit_price:"), IsAdminFilter())
async def callback_product_edit_price_start(
    callback: CallbackQuery,
    state: FSMContext,
    session: AsyncSession
):
    """
    Начало редактирования цены товара
    """
    product_id = int(callback.data.split(":")[3])

    product = await product_service.get_product_by_id(session, product_id, with_variants=False)
    if not product:
        await callback.answer(admin_messages.PRODUCT_NOT_FOUND, show_alert=True)
        return

    await state.set_state(ProductStates.editing_price)
    await state.update_data(product_id=product_id)

    await callback.message.edit_text(
        text=admin_messages.PRODUCT_EDIT_PRICE.format(current_price=f"{product.price:,.0f}"),
        reply_markup=admin_keyboards.get_cancel_keyboard(f"admin:product:view:{product_id}")
    )
    await callback.answer()


@router.message(ProductStates.editing_price, IsAdminFilter())
async def message_product_edit_price(
    message: Message,
    state: FSMContext,
    session: AsyncSession
):
    """
    Обработка новой цены товара
    """
    price_text = message.text.strip()

    # Валидация
    try:
        new_price = Decimal(price_text)
        if new_price <= 0:
            raise ValueError("Price must be positive")
    except (ValueError, InvalidOperation):
        await message.answer(admin_messages.PRODUCT_PRICE_INVALID)
        return

    data = await state.get_data()
    product_id = data['product_id']

    # Обновляем товар
    product = await product_service.update_product(
        session=session,
        product_id=product_id,
        price=new_price
    )

    if product:
        await message.answer(
            admin_messages.PRODUCT_PRICE_UPDATED.format(new_price=f"{new_price:,.0f}"),
            reply_markup=admin_keyboards.get_product_actions_keyboard(
                product_id=product_id,
                is_active=product.is_active
            )
        )
    else:
        await message.answer(admin_messages.PRODUCT_NOT_FOUND)

    await state.clear()


@router.callback_query(F.data.startswith("admin:product:edit_discount:"), IsAdminFilter())
async def callback_product_edit_discount_start(
    callback: CallbackQuery,
    state: FSMContext,
    session: AsyncSession
):
    """
    Начало редактирования скидки товара
    """
    product_id = int(callback.data.split(":")[3])

    product = await product_service.get_product_by_id(session, product_id, with_variants=False)
    if not product:
        await callback.answer(admin_messages.PRODUCT_NOT_FOUND, show_alert=True)
        return

    await state.set_state(ProductStates.editing_discount)
    await state.update_data(product_id=product_id)

    # Формируем текст текущей скидки
    if product.discount_price:
        discount_percent = int(((product.price - product.discount_price) / product.price) * 100)
        current_discount = f"{product.discount_price:,.0f} ₽ (скидка {discount_percent}%)"
    else:
        current_discount = "Нет скидки"

    await callback.message.edit_text(
        text=admin_messages.PRODUCT_EDIT_DISCOUNT.format(
            product_name=product.name,
            price=f"{product.price:,.0f}",
            current_discount=current_discount
        ),
        reply_markup=admin_keyboards.get_cancel_keyboard(f"admin:product:view:{product_id}")
    )
    await callback.answer()


@router.message(ProductStates.editing_discount, IsAdminFilter())
async def message_product_edit_discount(
    message: Message,
    state: FSMContext,
    session: AsyncSession
):
    """
    Обработка новой скидки товара
    """
    discount_text = message.text.strip()

    data = await state.get_data()
    product_id = data['product_id']

    # Получаем товар для проверки цены
    product = await product_service.get_product_by_id(session, product_id, with_variants=False)
    if not product:
        await message.answer(admin_messages.PRODUCT_NOT_FOUND)
        await state.clear()
        return

    # Если пользователь ввел "-", удаляем скидку
    if discount_text == "-":
        product = await product_service.update_product(
            session=session,
            product_id=product_id,
            discount_price=None
        )

        if product:
            await message.answer(
                admin_messages.PRODUCT_DISCOUNT_REMOVED,
                reply_markup=admin_keyboards.get_product_actions_keyboard(
                    product_id=product_id,
                    is_active=product.is_active
                )
            )
        else:
            await message.answer(admin_messages.PRODUCT_NOT_FOUND)

        await state.clear()
        return

    # Валидация скидочной цены
    try:
        discount_price = Decimal(discount_text)
        if discount_price <= 0:
            raise ValueError("Discount price must be positive")
        if discount_price >= product.price:
            raise ValueError("Discount price must be less than regular price")
    except (ValueError, InvalidOperation):
        await message.answer(
            admin_messages.PRODUCT_DISCOUNT_INVALID.format(price=f"{product.price:,.0f}")
        )
        return

    # Обновляем товар
    product = await product_service.update_product(
        session=session,
        product_id=product_id,
        discount_price=discount_price
    )

    if product:
        discount_percent = int(((product.price - discount_price) / product.price) * 100)
        discount_info = (
            f"Обычная цена: <s>{product.price:,.0f} ₽</s>\n"
            f"Цена со скидкой: {discount_price:,.0f} ₽\n"
            f"Скидка: {discount_percent}%"
        )

        await message.answer(
            admin_messages.PRODUCT_DISCOUNT_UPDATED.format(discount_info=discount_info),
            reply_markup=admin_keyboards.get_product_actions_keyboard(
                product_id=product_id,
                is_active=product.is_active
            )
        )
    else:
        await message.answer(admin_messages.PRODUCT_NOT_FOUND)

    await state.clear()


# ===== Управление фотографиями =====

@router.callback_query(F.data.startswith("admin:product:edit_images:"), IsAdminFilter())
async def callback_product_edit_images(
    callback: CallbackQuery,
    session: AsyncSession
):
    """
    Открыть меню управления фотографиями товара
    """
    product_id = int(callback.data.split(":")[3])

    product = await product_service.get_product_by_id(session, product_id, with_variants=False)
    if not product:
        await callback.answer(admin_messages.PRODUCT_NOT_FOUND, show_alert=True)
        return

    images_count = len(product.images) if product.images else 0

    await callback.message.edit_text(
        text=admin_messages.PRODUCT_IMAGES_MENU.format(
            product_name=product.name,
            images_count=images_count
        ),
        reply_markup=admin_keyboards.get_product_images_keyboard(product_id, images_count)
    )
    await callback.answer()


@router.callback_query(F.data.startswith("admin:product:add_image:"), IsAdminFilter())
async def callback_product_add_image_start(
    callback: CallbackQuery,
    state: FSMContext
):
    """
    Начало добавления фото к товару
    """
    product_id = int(callback.data.split(":")[3])

    await state.set_state(ProductStates.adding_image)
    await state.update_data(product_id=product_id)

    await callback.message.edit_text(
        text=admin_messages.PRODUCT_ADD_IMAGE_PROMPT,
        reply_markup=admin_keyboards.get_cancel_keyboard(f"admin:product:edit_images:{product_id}")
    )
    await callback.answer()


@router.message(
    ProductStates.adding_image,
    F.photo,
    IsAdminFilter()
)
async def message_product_add_image(
    message: Message,
    state: FSMContext,
    session: AsyncSession,
    bot: Bot
):
    """
    Обработка добавления фото к существующему товару
    """
    data = await state.get_data()
    product_id = data['product_id']

    # Получаем товар
    product = await product_service.get_product_by_id(session, product_id, with_variants=False)
    if not product:
        await message.answer(admin_messages.PRODUCT_NOT_FOUND)
        await state.clear()
        return

    # Получаем самое большое фото
    photo = message.photo[-1]

    # Сохраняем фото на диск
    filename = await image_service.save_photo(photo, bot)

    if not filename:
        await message.answer(admin_messages.PRODUCT_IMAGE_ADD_ERROR)
        return

    # Добавляем фото к списку
    images = product.images if product.images else []
    images.append(filename)

    # Обновляем товар
    await product_service.update_product(
        session=session,
        product_id=product_id,
        images=images
    )

    logger.info(f"✅ Админ {message.from_user.id} добавил фото к товару ID={product_id}: {filename}")

    images_count = len(images)

    await message.answer(
        text=admin_messages.PRODUCT_IMAGE_ADDED,
        reply_markup=admin_keyboards.get_product_images_keyboard(product_id, images_count)
    )
    await state.clear()


@router.callback_query(F.data.startswith("admin:product:delete_images:"), IsAdminFilter())
async def callback_product_delete_images_menu(
    callback: CallbackQuery,
    session: AsyncSession
):
    """
    Показать меню выбора фото для удаления
    """
    product_id = int(callback.data.split(":")[3])

    product = await product_service.get_product_by_id(session, product_id, with_variants=False)
    if not product:
        await callback.answer(admin_messages.PRODUCT_NOT_FOUND, show_alert=True)
        return

    if not product.images or len(product.images) == 0:
        await callback.answer("У товара нет фотографий", show_alert=True)
        return

    await callback.message.edit_text(
        text=admin_messages.PRODUCT_DELETE_IMAGES_MENU.format(
            product_name=product.name
        ),
        reply_markup=admin_keyboards.get_product_delete_images_keyboard(product_id, product.images)
    )
    await callback.answer()


@router.callback_query(F.data.startswith("admin:product:delete_image:"), IsAdminFilter())
async def callback_product_delete_image(
    callback: CallbackQuery,
    session: AsyncSession
):
    """
    Удалить конкретное фото
    """
    parts = callback.data.split(":")
    product_id = int(parts[3])
    image_index = int(parts[4])

    product = await product_service.get_product_by_id(session, product_id, with_variants=False)
    if not product:
        await callback.answer(admin_messages.PRODUCT_NOT_FOUND, show_alert=True)
        return

    if not product.images or image_index >= len(product.images):
        await callback.answer("Фото не найдено", show_alert=True)
        return

    # Удаляем файл с диска
    deleted_filename = product.images[image_index]
    await image_service.delete_photos([deleted_filename])

    # Удаляем из списка
    images = product.images.copy()
    images.pop(image_index)

    # Обновляем товар
    await product_service.update_product(
        session=session,
        product_id=product_id,
        images=images
    )

    logger.info(f"🗑️ Админ {callback.from_user.id} удалил фото {deleted_filename} товара ID={product_id}")

    images_count = len(images)

    # Возвращаемся к меню управления фото
    await callback.message.edit_text(
        text=admin_messages.PRODUCT_IMAGE_DELETED,
        reply_markup=admin_keyboards.get_product_images_keyboard(product_id, images_count)
    )
    await callback.answer()


# ===== Активация/деактивация товара =====

@router.callback_query(F.data.startswith("admin:product:activate:"), IsAdminFilter())
@router.callback_query(F.data.startswith("admin:product:deactivate:"), IsAdminFilter())
async def callback_product_toggle_status(
    callback: CallbackQuery,
    session: AsyncSession
):
    """
    Активация или деактивация товара
    """
    product_id = int(callback.data.split(":")[3])

    product = await product_service.toggle_product_status(session, product_id)

    if not product:
        logger.warning(f"Попытка изменения статуса несуществующего товара ID={product_id}")
        await callback.answer(admin_messages.PRODUCT_NOT_FOUND, show_alert=True)
        return

    # Формируем сообщение
    if product.is_active:
        message_text = admin_messages.PRODUCT_ACTIVATED.format(name=product.name)
        logger.info(f"✅ Админ {callback.from_user.id} АКТИВИРОВАЛ товар '{product.name}' (ID={product_id})")
    else:
        message_text = admin_messages.PRODUCT_DEACTIVATED.format(name=product.name)
        logger.info(f"⚠️ Админ {callback.from_user.id} ДЕАКТИВИРОВАЛ товар '{product.name}' (ID={product_id})")

    await callback.answer(message_text, show_alert=True)

    # Обновляем клавиатуру
    variants_count = len(product.variants) if product.variants else 0
    await callback.message.edit_text(
        text=admin_messages.format_product_details(product, variants_count),
        reply_markup=admin_keyboards.get_product_actions_keyboard(
            product_id=product_id,
            is_active=product.is_active
        )
    )


# ===== Удаление товара =====

@router.callback_query(F.data.startswith("admin:product:delete_confirm:"), IsAdminFilter())
async def callback_product_delete_confirm(
    callback: CallbackQuery,
    session: AsyncSession
):
    """
    Подтверждение удаления товара
    """
    product_id = int(callback.data.split(":")[3])

    product = await product_service.get_product_by_id(session, product_id, with_variants=True)
    if not product:
        await callback.answer(admin_messages.PRODUCT_NOT_FOUND, show_alert=True)
        return

    variants_count = len(product.variants) if product.variants else 0

    await callback.message.edit_text(
        text=admin_messages.PRODUCT_DELETE_CONFIRM.format(
            name=product.name,
            price=f"{product.price:,.0f}",
            variants_count=variants_count,
            warning=admin_messages.PRODUCT_DELETE_WARNING
        ),
        reply_markup=admin_keyboards.get_product_delete_confirmation_keyboard(product_id)
    )
    await callback.answer()


@router.callback_query(F.data.startswith("admin:product:delete:"), IsAdminFilter())
async def callback_product_delete(
    callback: CallbackQuery,
    session: AsyncSession
):
    """
    Удаление товара
    """
    product_id = int(callback.data.split(":")[3])

    # Получаем товар для имени
    product = await product_service.get_product_by_id(session, product_id, with_variants=False)
    if not product:
        logger.warning(f"Попытка удаления несуществующего товара ID={product_id}")
        await callback.answer(admin_messages.PRODUCT_NOT_FOUND, show_alert=True)
        return

    product_name = product.name
    images_count = len(product.images) if product.images else 0

    # Удаляем фотографии
    if product.images:
        deleted_images = await image_service.delete_photos(product.images)
        logger.debug(f"Удалено {deleted_images} фотографий товара ID={product_id}")

    # Удаляем товар
    success = await product_service.delete_product(session, product_id)

    if success:
        logger.warning(
            f"🗑️ Админ {callback.from_user.id} УДАЛИЛ товар '{product_name}' "
            f"(ID={product_id}, фото: {images_count})"
        )
        await callback.message.edit_text(
            text=admin_messages.PRODUCT_DELETED.format(name=product_name),
            reply_markup=admin_keyboards.get_products_menu()
        )
        await callback.answer()
    else:
        logger.error(f"❌ ОШИБКА при удалении товара ID={product_id}")
        await callback.answer(admin_messages.PRODUCT_DELETE_ERROR, show_alert=True)


# ===== Управление вариантами =====

@router.callback_query(F.data.startswith("admin:product:variants:"), IsAdminFilter())
async def callback_product_variants(
    callback: CallbackQuery,
    session: AsyncSession
):
    """
    Просмотр списка вариантов товара
    """
    product_id = int(callback.data.split(":")[3])

    product = await product_service.get_product_by_id(session, product_id, with_variants=True)
    if not product:
        await callback.answer(admin_messages.PRODUCT_NOT_FOUND, show_alert=True)
        return

    variants = product.variants if product.variants else []
    variants_count = len(variants)

    if variants_count == 0:
        text = admin_messages.PRODUCT_VARIANTS_EMPTY.format(product_name=product.name)
    else:
        text = admin_messages.PRODUCT_VARIANTS_MENU.format(
            product_name=product.name,
            variants_count=variants_count
        )

    await callback.message.edit_text(
        text=text,
        reply_markup=admin_keyboards.get_product_variants_keyboard(
            product_id=product_id,
            variants=variants
        )
    )
    await callback.answer()


@router.callback_query(F.data.startswith("admin:product:variant:add:"), IsAdminFilter())
async def callback_variant_add_start(
    callback: CallbackQuery,
    state: FSMContext
):
    """
    Начало добавления варианта товара
    """
    product_id = int(callback.data.split(":")[4])

    await state.set_state(ProductStates.waiting_for_variants)
    await state.update_data(product_id=product_id, size=None, color=None)

    await callback.message.edit_text(
        text=admin_messages.VARIANT_ADD_SIZE,
        reply_markup=admin_keyboards.get_cancel_keyboard(f"admin:product:variants:{product_id}")
    )
    await callback.answer()


@router.message(ProductStates.waiting_for_variants, IsAdminFilter())
async def message_variant_add_data(
    message: Message,
    state: FSMContext,
    session: AsyncSession
):
    """
    Обработка данных варианта (размер, цвет, количество)
    """
    data = await state.get_data()
    product_id = data['product_id']

    # Определяем, что вводится
    if 'size' not in data or data['size'] is None:
        # Вводится размер
        size = message.text.strip() if message.text.strip() != "-" else None
        await state.update_data(size=size)

        await message.answer(
            admin_messages.VARIANT_ADD_COLOR.format(size=size or "Не указан")
        )

    elif 'color' not in data or data['color'] is None:
        # Вводится цвет
        color = message.text.strip() if message.text.strip() != "-" else None
        await state.update_data(color=color)

        await message.answer(
            admin_messages.VARIANT_ADD_QUANTITY.format(
                size=data.get('size') or "Не указан",
                color=color or "Не указан"
            )
        )

    else:
        # Вводится количество
        try:
            quantity = int(message.text.strip())
            if quantity < 0 or quantity > 999999:
                raise ValueError("Invalid quantity")
        except ValueError:
            logger.warning(f"Админ {message.from_user.id} ввел некорректное количество: {message.text}")
            await message.answer(admin_messages.VARIANT_QUANTITY_INVALID)
            return

        # Создаем вариант
        variant = await product_service.add_product_variant(
            session=session,
            product_id=product_id,
            size=data.get('size'),
            color=data.get('color'),
            quantity=quantity
        )

        if variant:
            logger.info(
                f"✅ Админ {message.from_user.id} добавил вариант товара ID={product_id}: "
                f"размер={variant.size or 'не указан'}, цвет={variant.color or 'не указан'}, количество={quantity}"
            )
            await message.answer(
                admin_messages.VARIANT_CREATED.format(
                    size=variant.size or "Не указан",
                    color=variant.color or "Не указан",
                    quantity=variant.quantity
                ),
                reply_markup=admin_keyboards.get_product_variants_keyboard(
                    product_id=product_id,
                    variants=[variant]
                )
            )
        else:
            logger.error(f"❌ ОШИБКА: Не удалось создать вариант товара ID={product_id}")
            await message.answer(admin_messages.PRODUCT_NOT_FOUND)

        await state.clear()


@router.callback_query(F.data.startswith("admin:product:variant:view:"), IsAdminFilter())
async def callback_variant_view(
    callback: CallbackQuery,
    session: AsyncSession
):
    """
    Просмотр деталей варианта товара
    """
    variant_id = int(callback.data.split(":")[4])

    # Получаем вариант с товаром
    from bot.database.models.product_variant import ProductVariant
    from sqlalchemy import select
    from sqlalchemy.orm import selectinload

    query = select(ProductVariant).where(ProductVariant.id == variant_id)
    query = query.options(selectinload(ProductVariant.product))

    result = await session.execute(query)
    variant = result.scalar_one_or_none()

    if not variant:
        await callback.answer("Вариант не найден", show_alert=True)
        return

    product_name = variant.product.name if variant.product else "Неизвестный товар"
    product_id = variant.product_id

    await callback.message.edit_text(
        text=admin_messages.format_variant_details(variant, product_name),
        reply_markup=admin_keyboards.get_variant_actions_keyboard(variant_id, product_id)
    )
    await callback.answer()


@router.callback_query(F.data.startswith("admin:variant:delete:"), IsAdminFilter())
async def callback_variant_delete(
    callback: CallbackQuery,
    session: AsyncSession
):
    """
    Удаление варианта товара
    """
    variant_id = int(callback.data.split(":")[3])

    from bot.database.models.product_variant import ProductVariant
    from sqlalchemy import select, delete

    # Получаем вариант для определения product_id
    query = select(ProductVariant).where(ProductVariant.id == variant_id)
    result = await session.execute(query)
    variant = result.scalar_one_or_none()

    if not variant:
        await callback.answer("Вариант не найден", show_alert=True)
        return

    product_id = variant.product_id

    # Удаляем вариант
    await session.execute(delete(ProductVariant).where(ProductVariant.id == variant_id))
    await session.commit()

    logger.info(f"🗑️ Админ {callback.from_user.id} удалил вариант ID={variant_id} товара ID={product_id}")

    # Получаем обновленный список вариантов
    product = await product_service.get_product_by_id(session, product_id, with_variants=True)

    await callback.message.edit_text(
        text=admin_messages.VARIANT_DELETED,
        reply_markup=admin_keyboards.get_product_variants_keyboard(
            product_id=product_id,
            variants=product.variants if product else []
        )
    )
    await callback.answer()


# ===== Обработка пустых callback =====

@router.callback_query(F.data == "noop", IsAdminFilter())
async def callback_noop(callback: CallbackQuery):
    """
    Пустой обработчик для неактивных кнопок
    """
    await callback.answer()
