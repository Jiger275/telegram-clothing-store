"""
Фильтр для проверки прав администратора
"""
from typing import Any, Dict

from aiogram.filters import BaseFilter
from aiogram.types import Message, CallbackQuery

from bot.database.models.user import User
from bot.utils.logger import setup_logger


logger = setup_logger(__name__)


class IsAdminFilter(BaseFilter):
    """
    Фильтр для проверки, является ли пользователь администратором.

    Использование:
        @router.message(IsAdminFilter())
        async def admin_handler(message: Message):
            # Этот handler будет вызван только для администраторов
            pass
    """

    async def __call__(
        self,
        event: Message | CallbackQuery,
        user: User,
        **kwargs: Any
    ) -> bool:
        """
        Проверяет, является ли пользователь администратором

        Args:
            event: Сообщение или callback query
            user: Объект пользователя из базы данных (добавлен UserMiddleware)
            **kwargs: Дополнительные аргументы

        Returns:
            True, если пользователь - администратор, иначе False
        """
        is_admin = user.is_admin

        if not is_admin:
            logger.warning(
                f"Попытка доступа к админ-функции от не-администратора: "
                f"{user.telegram_id} (@{user.username})"
            )

        return is_admin
