"""
FSM состояния для админ-панели
"""
from aiogram.fsm.state import State, StatesGroup


class CategoryStates(StatesGroup):
    """
    Состояния для создания/редактирования категории
    """
    # Создание категории
    waiting_for_name = State()  # Ожидание названия категории
    waiting_for_description = State()  # Ожидание описания
    waiting_for_parent = State()  # Выбор родительской категории (для подкатегорий)

    # Редактирование категории
    editing_name = State()  # Редактирование названия
    editing_description = State()  # Редактирование описания
    editing_parent = State()  # Редактирование родительской категории


class ProductStates(StatesGroup):
    """
    Состояния для создания/редактирования товара
    (для будущего использования в Этапе 9)
    """
    # Создание товара
    waiting_for_category = State()  # Выбор категории
    waiting_for_name = State()  # Ввод названия
    waiting_for_description = State()  # Ввод описания
    waiting_for_price = State()  # Ввод цены
    waiting_for_images = State()  # Загрузка фото
    waiting_for_variants = State()  # Добавление вариантов

    # Редактирование товара
    editing_name = State()
    editing_description = State()
    editing_category = State()  # Редактирование категории
    editing_price = State()
    editing_discount = State()  # Редактирование скидки
    editing_images = State()
    adding_image = State()  # Добавление фото к существующему товару
