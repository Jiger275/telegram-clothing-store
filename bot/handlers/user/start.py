"""
Handler для команды /start и главного меню
"""
from aiogram import Router, F
from aiogram.filters import CommandStart, Command
from aiogram.types import Message, CallbackQuery
from sqlalchemy.ext.asyncio import AsyncSession

from bot.database.models.user import User
from bot.keyboards.user_keyboards import get_main_menu_keyboard
from bot.keyboards.admin_keyboards import get_admin_main_menu
from bot.texts.user_messages import WELCOME_MESSAGE, MAIN_MENU
from bot.texts import admin_messages
from bot.utils.logger import setup_logger


logger = setup_logger(__name__)

# Создаем роутер для handlers
router = Router(name="start")


async def safe_edit_message(message, text: str, reply_markup=None):
    """
    Безопасное редактирование сообщения с обработкой различных типов

    Args:
        message: Сообщение для редактирования
        text: Новый текст
        reply_markup: Новая клавиатура
    """
    try:
        # Если сообщение содержит фото, редактируем caption
        if message.photo:
            await message.edit_caption(caption=text, reply_markup=reply_markup)
        else:
            # Иначе редактируем текст
            await message.edit_text(text=text, reply_markup=reply_markup)
    except Exception as e:
        logger.error(f"Ошибка при редактировании сообщения: {e}")
        # Если не получилось отредактировать, удаляем и создаём новое
        try:
            await message.delete()
            await message.answer(text=text, reply_markup=reply_markup)
        except Exception as delete_error:
            logger.error(f"Ошибка при удалении/создании сообщения: {delete_error}")


@router.message(CommandStart())
async def cmd_start(
    message: Message,
    user: User,
    session: AsyncSession
) -> None:
    """
    Обработчик команды /start

    Args:
        message: Сообщение от пользователя
        user: Объект пользователя из БД (добавлен UserMiddleware)
        session: Сессия БД (добавлена DatabaseMiddleware)
    """
    logger.info(f"Пользователь {user.telegram_id} (@{user.username}) вызвал /start")

    # Отправляем приветственное сообщение с главным меню
    await message.answer(
        text=WELCOME_MESSAGE,
        reply_markup=get_main_menu_keyboard(is_admin=user.is_admin)
    )


@router.message(F.text == "Главное меню")
@router.callback_query(F.data == "main_menu")
async def show_main_menu(
    event: Message | CallbackQuery,
    user: User,
    session: AsyncSession
) -> None:
    """
    Показать главное меню

    Args:
        event: Сообщение или callback query
        user: Объект пользователя из БД
        session: Сессия БД
    """
    logger.info(f"Пользователь {user.telegram_id} открыл главное меню")

    keyboard = get_main_menu_keyboard(is_admin=user.is_admin)

    # Обрабатываем разные типы событий
    if isinstance(event, Message):
        await event.answer(
            text=MAIN_MENU,
            reply_markup=keyboard
        )
    else:  # CallbackQuery
        await safe_edit_message(
            event.message,
            text=MAIN_MENU,
            reply_markup=None
        )
        await event.message.answer(
            text=MAIN_MENU,
            reply_markup=keyboard
        )
        await event.answer()


# Обработчик для корзины перемещён в bot/handlers/user/cart.py
# Если вы видите это сообщение, проверьте, что cart.router зарегистрирован в основном приложении


@router.message(F.text == "Мои заказы")
async def show_orders(
    message: Message,
    user: User,
    session: AsyncSession
) -> None:
    """
    Показать заказы пользователя (заглушка)

    Args:
        message: Сообщение от пользователя
        user: Объект пользователя из БД
        session: Сессия БД
    """
    logger.info(f"Пользователь {user.telegram_id} открыл заказы")

    await message.answer(
        text="У вас пока нет заказов.",
        reply_markup=get_main_menu_keyboard(is_admin=user.is_admin)
    )


@router.message(F.text == "Профиль")
async def show_profile(
    message: Message,
    user: User,
    session: AsyncSession
) -> None:
    """
    Показать профиль пользователя

    Args:
        message: Сообщение от пользователя
        user: Объект пользователя из БД
        session: Сессия БД
    """
    logger.info(f"Пользователь {user.telegram_id} открыл профиль")

    profile_text = f"""
Ваш профиль:

Имя: {user.full_name}
Username: @{user.username if user.username else 'не указан'}
Дата регистрации: {user.created_at.strftime('%d.%m.%Y')}
Всего заказов: 0
"""

    await message.answer(
        text=profile_text,
        reply_markup=get_main_menu_keyboard(is_admin=user.is_admin)
    )


@router.message(F.text == "Админ-панель")
async def show_admin_panel(
    message: Message,
    user: User,
    session: AsyncSession
) -> None:
    """
    Показать админ-панель (доступна только администраторам)

    Args:
        message: Сообщение от пользователя
        user: Объект пользователя из БД
        session: Сессия БД
    """
    # Проверяем права администратора
    if not user.is_admin:
        logger.warning(
            f"Пользователь {user.telegram_id} (@{user.username}) "
            f"попытался открыть админ-панель без прав"
        )
        await message.answer(
            text="У вас нет прав для доступа к админ-панели.",
            reply_markup=get_main_menu_keyboard(is_admin=False)
        )
        return

    logger.info(f"Администратор {user.telegram_id} открыл админ-панель")

    await message.answer(
        text=admin_messages.ADMIN_PANEL_WELCOME,
        reply_markup=get_admin_main_menu()
    )
