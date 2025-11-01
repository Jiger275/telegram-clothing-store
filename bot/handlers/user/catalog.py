"""
Handler for catalog browsing
"""
import math
from typing import List, Dict
from aiogram import Router, F
from aiogram.types import Message, CallbackQuery, FSInputFile, InputMediaPhoto
from sqlalchemy.ext.asyncio import AsyncSession

from bot.database.models.user import User
from bot.database.models.product import Product
from bot.services import category_service, product_service
from bot.keyboards.user_keyboards import (
    get_categories_keyboard,
    get_products_keyboard,
    get_main_menu_keyboard,
    get_product_card_inline_keyboard,
    get_pagination_keyboard
)
from bot.texts.user_messages import (
    CATALOG_EMPTY,
    CATALOG_CATEGORIES,
    CATEGORY_NO_PRODUCTS,
    PRODUCT_IN_STOCK,
    PRODUCT_OUT_OF_STOCK
)
from bot.utils.logger import setup_logger
from bot.config.settings import settings


logger = setup_logger(__name__)

# Создаем роутер для handlers
router = Router(name="catalog")

# Хранилище для отслеживания сообщений с карточками товаров
# Структура: {user_id: {category_id: {'header': message_id, 'cards': [message_ids], 'navigation': message_id}}}
product_card_messages: Dict[int, Dict[int, Dict]] = {}


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
    Показать товары в категории с пагинацией (отдельные карточки)

    Args:
        callback: Callback query
        user: Объект пользователя из БД
        session: Сессия БД
        category: Объект категории
        page: Номер страницы
    """
    page_size = settings.products_per_page

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

    # Проверяем, есть ли уже карточки для этой категории
    has_old_cards = (
        user.telegram_id in product_card_messages and
        category.id in product_card_messages[user.telegram_id]
    )

    # Удаляем старые сообщения с карточками товаров (если есть)
    if has_old_cards:
        await delete_old_product_cards(
            bot=callback.bot,
            user_id=user.telegram_id,
            category_id=category.id
        )

    # Удаляем callback-сообщение (с кнопками навигации или категорий)
    # Это безопасно - просто удаляет сообщение, по которому кликнули
    try:
        await callback.message.delete()
    except Exception as e:
        # Не критично, если сообщение уже удалено или недоступно
        logger.debug(f"Не удалось удалить callback-сообщение (не критично): {e}")

    # Формируем breadcrumbs
    breadcrumbs = await category_service.get_category_breadcrumbs(
        session=session,
        category_id=category.id
    )
    breadcrumb_text = " > ".join([c.name for c in breadcrumbs])

    # Вычисляем общее количество страниц
    total_pages = math.ceil(total_count / page_size)

    # Отправляем заголовок
    header_text = f"{breadcrumb_text}\n\n"
    header_text += f"Товары ({total_count}):\n"
    header_text += f"Страница {page} из {total_pages}"

    # Отправляем новое сообщение с заголовком (не редактируем старое)
    header_message = await callback.bot.send_message(
        chat_id=callback.message.chat.id,
        text=header_text
    )

    # Инициализируем хранилище для сообщений пользователя
    if user.telegram_id not in product_card_messages:
        product_card_messages[user.telegram_id] = {}

    product_card_messages[user.telegram_id][category.id] = {
        'header': header_message.message_id,
        'cards': [],
        'navigation': None
    }

    # Отправляем карточки товаров
    for product in products:
        message_ids = await send_product_card(
            bot=callback.bot,
            chat_id=callback.message.chat.id,
            product=product,
            session=session,
            category_id=category.id
        )
        if message_ids:
            # message_ids может быть либо одним ID, либо списком IDs (для галереи)
            if isinstance(message_ids, list):
                product_card_messages[user.telegram_id][category.id]['cards'].extend(message_ids)
            else:
                product_card_messages[user.telegram_id][category.id]['cards'].append(message_ids)

    # Отправляем кнопки навигации
    navigation_text = "Навигация:"
    navigation_keyboard = get_pagination_keyboard(
        category_id=category.id,
        current_page=page,
        total_pages=total_pages,
        parent_id=category.parent_id
    )

    nav_message = await callback.bot.send_message(
        chat_id=callback.message.chat.id,
        text=navigation_text,
        reply_markup=navigation_keyboard
    )

    # Сохраняем ID навигационного сообщения
    product_card_messages[user.telegram_id][category.id]['navigation'] = nav_message.message_id

    await callback.answer()


async def send_product_card(
    bot,
    chat_id: int,
    product: Product,
    session: AsyncSession,
    category_id: int
) -> int | list[int] | None:
    """
    Отправить карточку товара

    Args:
        bot: Объект бота
        chat_id: ID чата
        product: Объект товара
        session: Сессия БД
        category_id: ID категории

    Returns:
        ID отправленного сообщения, список ID (для галереи) или None
    """
    try:
        # Проверяем доступность
        total_quantity = await product_service.get_product_total_quantity(
            session=session,
            product_id=product.id
        )

        availability = PRODUCT_IN_STOCK if total_quantity > 0 else PRODUCT_OUT_OF_STOCK

        # Формируем описание скидки
        discount_text = ""
        if product.discount_price:
            discount_text = f"\n💰 Скидка: ~~{product.price} ₽~~ → {product.discount_price} ₽"

        # Формируем текст карточки
        text = f"📦 {product.name}\n\n"
        text += f"{product.description or 'Нет описания'}\n"
        text += f"\n💵 Цена: {product_service.format_price(product.effective_price)}"
        text += discount_text
        text += f"\n\n{availability}"

        # Проверяем наличие вариантов
        has_variants = len(product.variants) > 0 if hasattr(product, 'variants') else False

        # Формируем клавиатуру
        keyboard = get_product_card_inline_keyboard(
            product_id=product.id,
            has_variants=has_variants,
            category_id=category_id
        )

        # Отправляем с фото, если есть
        if product.images and len(product.images) > 0:
            try:
                # Если несколько изображений, отправляем галерею (media group)
                if len(product.images) > 1:
                    media_group = []
                    for idx, image_name in enumerate(product.images):
                        image_path = f"media/products/{image_name}"
                        photo = FSInputFile(image_path)

                        # Caption добавляем только к первому изображению
                        if idx == 0:
                            media_group.append(InputMediaPhoto(
                                media=photo,
                                caption=text
                            ))
                        else:
                            media_group.append(InputMediaPhoto(media=photo))

                    # Отправляем галерею
                    messages = await bot.send_media_group(
                        chat_id=chat_id,
                        media=media_group
                    )

                    # Отправляем кнопки отдельным сообщением под галереей
                    button_message = await bot.send_message(
                        chat_id=chat_id,
                        text="👇 Выберите действие:",
                        reply_markup=keyboard
                    )

                    # Возвращаем список ID всех сообщений (галерея + кнопки)
                    message_ids = [msg.message_id for msg in messages]
                    message_ids.append(button_message.message_id)
                    return message_ids

                else:
                    # Одно изображение - отправляем обычным способом
                    image_path = f"media/products/{product.images[0]}"
                    photo = FSInputFile(image_path)
                    message = await bot.send_photo(
                        chat_id=chat_id,
                        photo=photo,
                        caption=text,
                        reply_markup=keyboard
                    )
                    return message.message_id

            except Exception as e:
                logger.error(f"Ошибка при загрузке изображений: {e}")
                # Если ошибка с изображением, отправляем просто текст
                message = await bot.send_message(
                    chat_id=chat_id,
                    text=text,
                    reply_markup=keyboard
                )
                return message.message_id
        else:
            # Без изображения
            message = await bot.send_message(
                chat_id=chat_id,
                text=text,
                reply_markup=keyboard
            )
            return message.message_id

    except Exception as e:
        logger.error(f"Ошибка при отправке карточки товара {product.id}: {e}")
        return None


async def delete_old_product_cards(
    bot,
    user_id: int,
    category_id: int
) -> None:
    """
    Удалить старые сообщения с карточками товаров

    Args:
        bot: Объект бота
        user_id: ID пользователя
        category_id: ID категории
    """
    if user_id not in product_card_messages:
        return

    if category_id not in product_card_messages[user_id]:
        return

    messages_data = product_card_messages[user_id][category_id]

    # Удаляем заголовок
    if isinstance(messages_data, dict) and messages_data.get('header'):
        try:
            await bot.delete_message(chat_id=user_id, message_id=messages_data['header'])
        except Exception as e:
            logger.warning(f"Не удалось удалить заголовок {messages_data['header']}: {e}")

    # Удаляем карточки товаров
    cards = messages_data.get('cards', []) if isinstance(messages_data, dict) else messages_data
    for message_id in cards:
        try:
            await bot.delete_message(chat_id=user_id, message_id=message_id)
        except Exception as e:
            logger.warning(f"Не удалось удалить сообщение {message_id}: {e}")

    # Удаляем навигацию
    if isinstance(messages_data, dict) and messages_data.get('navigation'):
        try:
            await bot.delete_message(chat_id=user_id, message_id=messages_data['navigation'])
        except Exception as e:
            logger.warning(f"Не удалось удалить навигацию {messages_data['navigation']}: {e}")

    # Очищаем данные
    product_card_messages[user_id][category_id] = {
        'header': None,
        'cards': [],
        'navigation': None
    }
