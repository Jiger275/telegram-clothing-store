"""
Обработчики главной админ-панели
"""
from aiogram import Router, F
from aiogram.filters import Command
from aiogram.types import Message, CallbackQuery

from bot.filters.admin_filter import IsAdminFilter
from bot.keyboards.admin_keyboards import get_admin_main_menu
from bot.texts import admin_messages
from bot.utils.logger import setup_logger


logger = setup_logger(__name__)

# Создаем роутер для админ-панели
router = Router(name="admin_panel")


@router.message(Command("admin"), IsAdminFilter())
async def cmd_admin(message: Message):
    """
    Обработчик команды /admin - главная админ-панель
    """
    logger.info(f"Админ {message.from_user.id} открыл админ-панель")

    await message.answer(
        text=admin_messages.ADMIN_PANEL_WELCOME,
        reply_markup=get_admin_main_menu()
    )


@router.callback_query(F.data == "admin:panel", IsAdminFilter())
async def callback_admin_panel(callback: CallbackQuery):
    """
    Обработчик возврата в главную админ-панель
    """
    logger.info(f"Админ {callback.from_user.id} вернулся в главную админ-панель")

    await callback.message.edit_text(
        text=admin_messages.ADMIN_PANEL_WELCOME,
        reply_markup=get_admin_main_menu()
    )
    await callback.answer()


@router.callback_query(F.data == "admin:products", IsAdminFilter())
async def callback_admin_products(callback: CallbackQuery):
    """
    Обработчик перехода в управление товарами
    Перенаправляет в products.py handler
    """
    # Этот handler больше не нужен, так как есть в products.py
    # Оставлен для обратной совместимости, но не используется
    pass


@router.callback_query(F.data == "admin:orders", IsAdminFilter())
async def callback_admin_orders(callback: CallbackQuery):
    """
    Обработчик перехода в управление заказами (будет реализовано в Этапе 10)
    """
    logger.info(f"Админ {callback.from_user.id} попытался открыть управление заказами (функция еще не реализована)")

    await callback.answer(
        "Управление заказами будет реализовано в следующем этапе",
        show_alert=True
    )


@router.callback_query(F.data == "admin:stats", IsAdminFilter())
async def callback_admin_stats(callback: CallbackQuery):
    """
    Обработчик перехода в статистику (опциональная функция)
    """
    logger.info(f"Админ {callback.from_user.id} попытался открыть статистику (функция еще не реализована)")

    await callback.answer(
        "Статистика будет реализована позже",
        show_alert=True
    )
