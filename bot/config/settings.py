"""
Настройки приложения с использованием Pydantic Settings
"""
from typing import List, Optional
from pathlib import Path

from pydantic import Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Настройки приложения, загружаемые из переменных окружения"""

    # Telegram Bot
    bot_token: str = Field(
        ...,
        alias="BOT_TOKEN",
        description="Токен Telegram бота от @BotFather"
    )

    # Администраторы
    admin_telegram_ids: str = Field(
        ...,
        alias="ADMIN_TELEGRAM_IDS",
        description="ID администраторов через запятую"
    )

    # База данных
    database_url: str = Field(
        default="sqlite+aiosqlite:///./bot.db",
        alias="DATABASE_URL",
        description="URL для подключения к базе данных"
    )

    # Redis (опционально)
    redis_url: Optional[str] = Field(
        default=None,
        alias="REDIS_URL",
        description="URL для подключения к Redis"
    )

    # Настройки приложения
    debug: bool = Field(
        default=False,
        alias="DEBUG",
        description="Режим отладки"
    )

    log_level: str = Field(
        default="INFO",
        alias="LOG_LEVEL",
        description="Уровень логирования"
    )

    # Пути
    media_dir: str = Field(
        default="media",
        alias="MEDIA_DIR",
        description="Директория для медиа файлов"
    )

    logs_dir: str = Field(
        default="logs",
        alias="LOGS_DIR",
        description="Директория для логов"
    )

    # Настройки модели Pydantic
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore"
    )

    @field_validator("admin_telegram_ids")
    @classmethod
    def validate_admin_ids(cls, v: str) -> List[int]:
        """Преобразует строку ID администраторов в список целых чисел"""
        try:
            ids = [int(id_.strip()) for id_ in v.split(",") if id_.strip()]
            if not ids:
                raise ValueError("Должен быть указан хотя бы один ID администратора")
            return ids
        except ValueError as e:
            raise ValueError(f"Некорректные ID администраторов: {e}")

    @field_validator("log_level")
    @classmethod
    def validate_log_level(cls, v: str) -> str:
        """Проверяет корректность уровня логирования"""
        valid_levels = ["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"]
        v_upper = v.upper()
        if v_upper not in valid_levels:
            raise ValueError(
                f"Некорректный уровень логирования: {v}. "
                f"Допустимые значения: {', '.join(valid_levels)}"
            )
        return v_upper

    @property
    def media_path(self) -> Path:
        """Возвращает путь к директории медиа"""
        return Path(self.media_dir)

    @property
    def logs_path(self) -> Path:
        """Возвращает путь к директории логов"""
        return Path(self.logs_dir)

    @property
    def products_media_path(self) -> Path:
        """Возвращает путь к директории с изображениями товаров"""
        return self.media_path / "products"

    def is_admin(self, telegram_id: int) -> bool:
        """Проверяет, является ли пользователь администратором"""
        return telegram_id in self.admin_telegram_ids


# Создаем глобальный экземпляр настроек
settings = Settings()


# Экспортируем настройки
__all__ = ["settings", "Settings"]
