"""
FSM состояния для оформления заказа
"""
from aiogram.fsm.state import State, StatesGroup


class OrderStates(StatesGroup):
    """
    Состояния процесса оформления заказа

    Шаги:
    1. Подтверждение состава заказа
    2. Ввод имени получателя
    3. Ввод телефона (с валидацией)
    4. Выбор способа доставки (курьер/самовывоз)
    5. Ввод адреса (если курьер)
    6. Комментарий (опционально)
    7. Итоговое подтверждение
    """
    # Ввод имени получателя
    waiting_for_name = State()

    # Ввод телефона
    waiting_for_phone = State()

    # Выбор способа доставки
    waiting_for_delivery_type = State()

    # Ввод адреса доставки (если выбран курьер)
    waiting_for_address = State()

    # Комментарий к заказу (опционально)
    waiting_for_comment = State()

    # Итоговое подтверждение заказа
    waiting_for_confirmation = State()
