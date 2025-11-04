"""
Точка входа в приложение - запуск Telegram бота
"""
import asyncio
import sys
from pathlib import Path

from aiogram import Bot, Dispatcher
from aiogram.client.default import DefaultBotProperties
from aiogram.enums import ParseMode
from aiogram.fsm.storage.memory import MemoryStorage
from aiogram.exceptions import TelegramConflictError

from bot.config.settings import settings
from bot.database.engine import init_database
from bot.utils.logger import setup_logger
from bot.middlewares.db_middleware import DatabaseMiddleware
from bot.middlewares.user_middleware import UserMiddleware
from bot.handlers.user import start, catalog, product, cart, order, profile
from bot.handlers.admin import panel, categories, products


# Настраиваем логирование
logger = setup_logger(__name__)


async def on_startup(bot: Bot) -> None:
    """
    Действия при запуске бота
    """
    logger.info("Запуск бота...")

    # Инициализируем базу данных
    await init_database()
    logger.info("База данных инициализирована")

    # Создаем необходимые директории
    settings.media_path.mkdir(parents=True, exist_ok=True)
    settings.products_media_path.mkdir(parents=True, exist_ok=True)
    settings.logs_path.mkdir(parents=True, exist_ok=True)
    logger.info("Директории созданы")

    # Получаем информацию о боте
    bot_info = await bot.get_me()
    logger.info(f"Бот запущен: @{bot_info.username}")


async def on_shutdown(bot: Bot) -> None:
    """
    Действия при остановке бота
    """
    logger.info("Остановка бота...")
    await bot.session.close()
    logger.info("Бот остановлен")


async def main() -> None:
    """
    Главная функция запуска бота
    """
    try:
        # Инициализируем бота с настройками по умолчанию
        bot = Bot(
            token=settings.bot_token,
            default=DefaultBotProperties(
                parse_mode=ParseMode.HTML,
                link_preview_is_disabled=True
            )
        )

        # Инициализируем диспетчер с FSM хранилищем в памяти
        storage = MemoryStorage()
        dp = Dispatcher(storage=storage)

        # Регистрируем middleware
        # DatabaseMiddleware должен быть первым, чтобы предоставить сессию БД
        dp.update.middleware(DatabaseMiddleware())
        # UserMiddleware для автоматической регистрации/загрузки пользователей
        dp.update.middleware(UserMiddleware())

        # Регистрируем роутеры с handlers
        # ВАЖНО: Порядок имеет значение! Более специфичные handlers должны быть первыми

        # Админские handlers (должны быть первыми для приоритета)
        dp.include_router(products.router)  # Управление товарами
        dp.include_router(categories.router)  # Управление категориями
        dp.include_router(panel.router)  # Главная админ-панель

        # Пользовательские handlers
        dp.include_router(order.router)  # Обработчики оформления заказа (FSM)
        dp.include_router(cart.router)  # Обработчики корзины (более специфичные)
        dp.include_router(product.router)  # Обработчики товаров
        dp.include_router(catalog.router)  # Обработчики каталога
        dp.include_router(profile.router)  # Обработчики профиля и заказов
        dp.include_router(start.router)  # Общие обработчики (менее специфичные)

        # Регистрируем события запуска и остановки
        dp.startup.register(on_startup)
        dp.shutdown.register(on_shutdown)

        # Запускаем polling
        logger.info("Бот начинает прием сообщений (polling)...")
        await dp.start_polling(
            bot,
            allowed_updates=dp.resolve_used_update_types(),
            drop_pending_updates=True  # Пропускаем накопившиеся обновления
        )

    except TelegramConflictError as e:
        logger.error(
            "❌ ОШИБКА: Конфликт Telegram - другой экземпляр бота уже запущен!\n"
            "Решение:\n"
            "  1. Остановите другой экземпляр бота (возможно, запущен на другой машине или в другом терминале)\n"
            "  2. Убедитесь, что используете уникальный токен бота\n"
            "  3. Подождите несколько секунд и попробуйте снова\n"
            f"Детали ошибки: {e}"
        )
        sys.exit(1)
    except Exception as e:
        logger.exception(f"Критическая ошибка при запуске бота: {e}")
        sys.exit(1)


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        logger.info("Бот остановлен пользователем (Ctrl+C)")
    except Exception as e:
        logger.exception(f"Необработанная ошибка: {e}")
        sys.exit(1)
