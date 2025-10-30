"""
Handler для команды /start и главного меню
"""
from aiogram import Router, F
from aiogram.filters import CommandStart, Command
from aiogram.types import Message, CallbackQuery
from sqlalchemy.ext.asyncio import AsyncSession

from bot.database.models.user import User
from bot.keyboards.user_keyboards import get_main_menu_keyboard
from bot.texts.user_messages import WELCOME_MESSAGE, MAIN_MENU
from bot.utils.logger import setup_logger


logger = setup_logger(__name__)

# Создаем роутер для handlers
router = Router(name="start")


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
        await event.message.edit_text(
            text=MAIN_MENU,
            reply_markup=None
        )
        await event.message.answer(
            text=MAIN_MENU,
            reply_markup=keyboard
        )
        await event.answer()


@router.message(F.text == "Корзина")
async def show_cart(
    message: Message,
    user: User,
    session: AsyncSession
) -> None:
    """
    Показать корзину (заглушка)

    Args:
        message: Сообщение от пользователя
        user: Объект пользователя из БД
        session: Сессия БД
    """
    logger.info(f"Пользователь {user.telegram_id} открыл корзину")

    await message.answer(
        text="Ваша корзина пуста.",
        reply_markup=get_main_menu_keyboard(is_admin=user.is_admin)
    )


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
    Показать админ-панель (заглушка, доступна только администраторам)

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
        text="Админ-панель скоро будет доступна!",
        reply_markup=get_main_menu_keyboard(is_admin=user.is_admin)
    )
