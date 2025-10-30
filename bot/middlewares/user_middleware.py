"""
Middleware для автоматической регистрации и загрузки пользователей
"""
from typing import Any, Awaitable, Callable, Dict

from aiogram import BaseMiddleware
from aiogram.types import TelegramObject, User as TelegramUser
from sqlalchemy.ext.asyncio import AsyncSession

from bot.services.user_service import UserService
from bot.utils.logger import setup_logger


logger = setup_logger(__name__)


class UserMiddleware(BaseMiddleware):
    """
    Middleware для автоматической регистрации пользователей в базе данных.

    При каждом взаимодействии пользователя с ботом проверяет, есть ли пользователь
    в базе данных. Если нет - автоматически регистрирует его.
    Добавляет объект User в данные, доступные в handler.
    """

    async def __call__(
        self,
        handler: Callable[[TelegramObject, Dict[str, Any]], Awaitable[Any]],
        event: TelegramObject,
        data: Dict[str, Any],
    ) -> Any:
        """
        Обработчик middleware

        Args:
            handler: Следующий обработчик в цепочке
            event: Telegram событие
            data: Данные, передаваемые в handler

        Returns:
            Результат выполнения handler
        """
        # Получаем Telegram пользователя из события
        telegram_user: TelegramUser = data.get("event_from_user")

        # Если пользователь не найден в событии, пропускаем middleware
        if not telegram_user:
            return await handler(event, data)

        # Получаем сессию БД (должна быть добавлена DatabaseMiddleware)
        session: AsyncSession = data.get("session")

        if not session:
            logger.error("Session не найдена в данных. DatabaseMiddleware должен быть зарегистрирован первым!")
            return await handler(event, data)

        # Получаем или создаем пользователя
        user, is_new = await UserService.get_or_create_user(
            session=session,
            telegram_id=telegram_user.id,
            username=telegram_user.username,
            full_name=telegram_user.full_name or telegram_user.first_name or "User"
        )

        if is_new:
            logger.info(f"Зарегистрирован новый пользователь: {user.telegram_id} (@{user.username})")

        # Добавляем пользователя в данные для handler
        data["user"] = user

        # Вызываем следующий handler
        return await handler(event, data)
