"""
Настройка логирования с использованием Loguru
"""
import sys
from pathlib import Path
from loguru import logger


def setup_logger(log_level: str = "INFO", logs_dir: str = "logs"):
    """
    Настраивает логирование для приложения

    Args:
        log_level: Уровень логирования (DEBUG, INFO, WARNING, ERROR, CRITICAL)
        logs_dir: Директория для хранения логов
    """
    # Удаляем стандартный обработчик
    logger.remove()

    # Создаем директорию для логов, если её нет
    logs_path = Path(logs_dir)
    logs_path.mkdir(parents=True, exist_ok=True)

    # Формат для консоли (более читаемый)
    console_format = (
        "<green>{time:YYYY-MM-DD HH:mm:ss}</green> | "
        "<level>{level: <8}</level> | "
        "<cyan>{name}</cyan>:<cyan>{function}</cyan>:<cyan>{line}</cyan> | "
        "<level>{message}</level>"
    )

    # Формат для файла (более подробный)
    file_format = (
        "{time:YYYY-MM-DD HH:mm:ss.SSS} | "
        "{level: <8} | "
        "{name}:{function}:{line} | "
        "{message}"
    )

    # Добавляем вывод в консоль
    logger.add(
        sys.stderr,
        format=console_format,
        level=log_level,
        colorize=True,
        backtrace=True,
        diagnose=True
    )

    # Добавляем вывод в файл (обычные логи)
    logger.add(
        logs_path / "bot.log",
        format=file_format,
        level=log_level,
        rotation="10 MB",  # Ротация при достижении 10 MB
        retention="30 days",  # Хранить логи 30 дней
        compression="zip",  # Сжимать старые логи
        backtrace=True,
        diagnose=True,
        encoding="utf-8"
    )

    # Добавляем отдельный файл для ошибок
    logger.add(
        logs_path / "errors.log",
        format=file_format,
        level="ERROR",
        rotation="5 MB",
        retention="60 days",
        compression="zip",
        backtrace=True,
        diagnose=True,
        encoding="utf-8"
    )

    logger.info(f"Логирование настроено. Уровень: {log_level}")
    return logger


# Экспортируем настроенный логгер
__all__ = ["setup_logger", "logger"]
