"""
Service for working with product images
"""
import os
import uuid
from pathlib import Path
from typing import Optional, List

import aiofiles
from aiogram.types import PhotoSize

from bot.utils.logger import setup_logger


logger = setup_logger(__name__)


# Конфигурация
MEDIA_DIR = Path("media/products")
MAX_FILE_SIZE = 10 * 1024 * 1024  # 10 MB
ALLOWED_EXTENSIONS = {".jpg", ".jpeg", ".png", ".webp"}


def ensure_media_directory() -> None:
    """
    Создает директорию для медиа-файлов, если её нет
    """
    MEDIA_DIR.mkdir(parents=True, exist_ok=True)
    logger.debug(f"Media directory ensured: {MEDIA_DIR.absolute()}")


async def save_photo(photo: PhotoSize, bot) -> Optional[str]:
    """
    Сохраняет фото товара на диск

    Args:
        photo: PhotoSize объект из Telegram
        bot: Bot instance для загрузки файла

    Returns:
        Имя сохраненного файла или None при ошибке
    """
    try:
        ensure_media_directory()

        # Получаем информацию о файле
        file = await bot.get_file(photo.file_id)

        # Проверяем размер файла
        if file.file_size > MAX_FILE_SIZE:
            logger.warning(f"⚠️ [IMAGE] Размер файла {file.file_size} превышает максимальный {MAX_FILE_SIZE}")
            return None

        # Получаем расширение файла
        file_extension = Path(file.file_path).suffix.lower()
        if file_extension not in ALLOWED_EXTENSIONS:
            logger.warning(f"⚠️ [IMAGE] Недопустимое расширение файла: {file_extension}")
            return None

        # Генерируем уникальное имя файла
        filename = f"{uuid.uuid4()}{file_extension}"
        filepath = MEDIA_DIR / filename

        # Скачиваем и сохраняем файл
        await bot.download_file(file.file_path, filepath)

        logger.info(f"✅ [IMAGE] Фото сохранено: {filename} (размер: {file.file_size} байт)")
        return filename

    except Exception as e:
        logger.exception(f"❌ [IMAGE] ОШИБКА при сохранении фото: {e}")
        return None


async def delete_photo(filename: str) -> bool:
    """
    Удаляет фото товара с диска

    Args:
        filename: Имя файла для удаления

    Returns:
        True если файл успешно удален, False при ошибке
    """
    try:
        filepath = MEDIA_DIR / filename

        if not filepath.exists():
            logger.warning(f"⚠️ [IMAGE] Файл не найден для удаления: {filename}")
            return False

        # Удаляем файл
        filepath.unlink()
        logger.info(f"🗑️ [IMAGE] Фото удалено: {filename}")
        return True

    except Exception as e:
        logger.exception(f"❌ [IMAGE] ОШИБКА при удалении фото {filename}: {e}")
        return False


async def delete_photos(filenames: List[str]) -> int:
    """
    Удаляет несколько фото товара с диска

    Args:
        filenames: Список имен файлов для удаления

    Returns:
        Количество успешно удаленных файлов
    """
    deleted_count = 0

    for filename in filenames:
        if await delete_photo(filename):
            deleted_count += 1

    if deleted_count == len(filenames):
        logger.info(f"✅ [IMAGE] Удалено {deleted_count} из {len(filenames)} фото")
    else:
        logger.warning(f"⚠️ [IMAGE] Удалено только {deleted_count} из {len(filenames)} фото")

    return deleted_count


def get_photo_path(filename: str) -> Path:
    """
    Возвращает полный путь к фото товара

    Args:
        filename: Имя файла

    Returns:
        Полный путь к файлу
    """
    return MEDIA_DIR / filename


def photo_exists(filename: str) -> bool:
    """
    Проверяет существование фото

    Args:
        filename: Имя файла

    Returns:
        True если файл существует, False иначе
    """
    return get_photo_path(filename).exists()


async def get_photo_size(filename: str) -> Optional[int]:
    """
    Возвращает размер фото в байтах

    Args:
        filename: Имя файла

    Returns:
        Размер файла в байтах или None при ошибке
    """
    try:
        filepath = get_photo_path(filename)
        if not filepath.exists():
            return None

        return filepath.stat().st_size

    except Exception as e:
        logger.error(f"Error getting photo size {filename}: {e}")
        return None


def validate_images_list(images: List[str]) -> bool:
    """
    Валидирует список имен файлов изображений

    Args:
        images: Список имен файлов

    Returns:
        True если все файлы корректны, False иначе
    """
    if not images:
        return False

    for image in images:
        if not isinstance(image, str):
            return False

        # Проверяем расширение
        extension = Path(image).suffix.lower()
        if extension not in ALLOWED_EXTENSIONS:
            logger.warning(f"Invalid image extension in list: {image}")
            return False

    return True


async def cleanup_orphaned_images(used_images: List[str]) -> int:
    """
    Удаляет изображения, которые не используются ни в одном товаре

    Args:
        used_images: Список имен файлов, которые используются

    Returns:
        Количество удаленных файлов
    """
    try:
        ensure_media_directory()
        deleted_count = 0

        # Получаем все файлы в директории
        for filepath in MEDIA_DIR.iterdir():
            if filepath.is_file() and filepath.name not in used_images:
                filepath.unlink()
                deleted_count += 1
                logger.debug(f"🧹 [IMAGE] Удалено неиспользуемое изображение: {filepath.name}")

        if deleted_count > 0:
            logger.info(f"🧹 [IMAGE] Очистка завершена: удалено {deleted_count} неиспользуемых изображений")
        else:
            logger.debug(f"🧹 [IMAGE] Очистка завершена: неиспользуемых изображений не найдено")

        return deleted_count

    except Exception as e:
        logger.exception(f"❌ [IMAGE] ОШИБКА при очистке неиспользуемых изображений: {e}")
        return 0
