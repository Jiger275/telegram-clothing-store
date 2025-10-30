"""
Middleware для предоставления сессии базы данных в handlers
"""
from typing import Any, Awaitable, Callable, Dict

from aiogram import BaseMiddleware
from aiogram.types import TelegramObject
from aiogram.exceptions import TelegramForbiddenError
from sqlalchemy.ext.asyncio import AsyncSession

from bot.database.engine import async_session_maker
from bot.utils.logger import setup_logger


logger = setup_logger(__name__)


class DatabaseMiddleware(BaseMiddleware):
    """
    Middleware для создания и предоставления сессии базы данных для каждого обновления.

    Автоматически создает сессию БД перед обработкой события и закрывает её после.
    В случае ошибки выполняет rollback.
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
        # Создаем новую сессию для этого обновления
        async with async_session_maker() as session:
            # Добавляем сессию в данные, доступные в handler
            data["session"] = session

            try:
                # Вызываем следующий обработчик
                result = await handler(event, data)

                # Если всё прошло успешно, коммитим изменения
                await session.commit()

                return result

            except TelegramForbiddenError:
                # Пользователь заблокировал бота - это нормальная ситуация
                # Откатываем транзакцию, но не логируем как ошибку
                await session.rollback()
                logger.debug("Пользователь заблокировал бота")
                # Не пробрасываем исключение дальше
                return None

            except Exception as e:
                # В случае ошибки откатываем транзакцию
                await session.rollback()
                logger.error(f"Ошибка при обработке события: {e}")
                raise

            finally:
                # Сессия закроется автоматически благодаря async context manager
                await session.close()
