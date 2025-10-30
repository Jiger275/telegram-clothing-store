"""
Сервис для работы с пользователями
"""
from typing import Optional

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.exc import IntegrityError

from bot.database.models.user import User
from bot.config.settings import settings
from bot.utils.logger import setup_logger


logger = setup_logger(__name__)


class UserService:
    """Сервис для работы с пользователями"""

    @staticmethod
    async def get_user_by_telegram_id(
        session: AsyncSession,
        telegram_id: int
    ) -> Optional[User]:
        """
        Получить пользователя по Telegram ID

        Args:
            session: Сессия базы данных
            telegram_id: Telegram ID пользователя

        Returns:
            User или None, если пользователь не найден
        """
        result = await session.execute(
            select(User).where(User.telegram_id == telegram_id)
        )
        return result.scalar_one_or_none()

    @staticmethod
    async def create_user(
        session: AsyncSession,
        telegram_id: int,
        username: Optional[str] = None,
        full_name: str = "User",
    ) -> User:
        """
        Создать нового пользователя

        Args:
            session: Сессия базы данных
            telegram_id: Telegram ID пользователя
            username: Username пользователя (опционально)
            full_name: Полное имя пользователя

        Returns:
            Созданный пользователь
        """
        # Проверяем, является ли пользователь администратором
        is_admin = settings.is_admin(telegram_id)

        user = User(
            telegram_id=telegram_id,
            username=username,
            full_name=full_name,
            is_admin=is_admin
        )

        session.add(user)
        await session.flush()  # Получаем ID без коммита

        logger.info(
            f"Создан новый пользователь: {telegram_id} "
            f"(username: {username}, admin: {is_admin})"
        )

        return user

    @staticmethod
    async def update_user(
        session: AsyncSession,
        user: User,
        username: Optional[str] = None,
        full_name: Optional[str] = None,
    ) -> User:
        """
        Обновить данные пользователя

        Args:
            session: Сессия базы данных
            user: Объект пользователя
            username: Новый username (опционально)
            full_name: Новое имя (опционально)

        Returns:
            Обновленный пользователь
        """
        if username is not None:
            user.username = username

        if full_name is not None:
            user.full_name = full_name

        await session.flush()

        return user

    @staticmethod
    async def get_or_create_user(
        session: AsyncSession,
        telegram_id: int,
        username: Optional[str] = None,
        full_name: str = "User",
    ) -> tuple[User, bool]:
        """
        Получить пользователя или создать, если не существует

        Args:
            session: Сессия базы данных
            telegram_id: Telegram ID пользователя
            username: Username пользователя (опционально)
            full_name: Полное имя пользователя

        Returns:
            Кортеж (пользователь, создан ли новый)
        """
        # Сначала пробуем получить пользователя
        user = await UserService.get_user_by_telegram_id(session, telegram_id)

        if user:
            # Обновляем username и full_name, если они изменились
            updated = False
            if username and user.username != username:
                user.username = username
                updated = True

            if full_name and user.full_name != full_name:
                user.full_name = full_name
                updated = True

            if updated:
                await session.flush()

            return user, False

        # Пробуем создать нового пользователя
        try:
            user = await UserService.create_user(
                session=session,
                telegram_id=telegram_id,
                username=username,
                full_name=full_name
            )
            return user, True
        except IntegrityError:
            # Если произошла ошибка уникальности (race condition),
            # значит пользователь был создан другим запросом между проверкой и созданием
            logger.warning(
                f"Race condition при создании пользователя {telegram_id}. "
                f"Повторная попытка получения из БД..."
            )
            # Откатываем транзакцию и пробуем получить пользователя снова
            await session.rollback()
            user = await UserService.get_user_by_telegram_id(session, telegram_id)
            if user:
                return user, False
            else:
                # Если пользователь все еще не найден, что-то пошло не так
                logger.error(f"Не удалось получить пользователя {telegram_id} после IntegrityError")
                raise
