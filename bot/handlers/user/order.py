"""
Handler для оформления заказа с FSM
"""
from aiogram import Router, F
from aiogram.types import Message, CallbackQuery
from aiogram.fsm.context import FSMContext
from sqlalchemy.ext.asyncio import AsyncSession

from bot.database.models.user import User
from bot.database.models.order import DeliveryType
from bot.services import cart_service, order_service
from bot.states.order_states import OrderStates
from bot.keyboards.user_keyboards import (
    get_delivery_type_keyboard,
    get_skip_comment_keyboard,
    get_order_confirmation_keyboard,
    get_cancel_checkout_keyboard
)
from bot.texts.user_messages import (
    CHECKOUT_ASK_NAME,
    CHECKOUT_ASK_PHONE,
    CHECKOUT_ASK_DELIVERY,
    CHECKOUT_ASK_ADDRESS,
    CHECKOUT_ASK_COMMENT,
    CHECKOUT_CONFIRMATION,
    ORDER_CREATED_SUCCESS,
    ORDER_CANCELLED,
    INVALID_NAME,
    INVALID_PHONE,
    INVALID_ADDRESS,
    INVALID_COMMENT,
    CART_EMPTY_CHECKOUT,
    ORDER_CREATION_FAILED
)
from bot.utils.validators import validate_name, validate_phone, validate_address, validate_comment
from bot.utils.logger import setup_logger

logger = setup_logger(__name__)

# Создаем роутер для handlers
router = Router(name="order")


@router.callback_query(F.data == "checkout")
async def start_checkout(
    callback: CallbackQuery,
    state: FSMContext,
    user: User,
    session: AsyncSession
) -> None:
    """
    Начать процесс оформления заказа

    Args:
        callback: Callback query
        state: FSM контекст
        user: Пользователь
        session: Сессия БД
    """
    logger.info(f"Пользователь {user.telegram_id} начал оформление заказа")

    # Проверяем, что корзина не пуста
    cart_items = await cart_service.get_cart_items(session, user.id)
    if not cart_items:
        await callback.answer(CART_EMPTY_CHECKOUT, show_alert=True)
        return

    # Переходим к вводу имени
    await state.set_state(OrderStates.waiting_for_name)
    await callback.message.edit_text(
        text=CHECKOUT_ASK_NAME,
        reply_markup=get_cancel_checkout_keyboard()
    )
    await callback.answer()


@router.message(OrderStates.waiting_for_name)
async def process_name(
    message: Message,
    state: FSMContext,
    user: User
) -> None:
    """
    Обработать введенное имя получателя

    Args:
        message: Сообщение от пользователя
        state: FSM контекст
        user: Пользователь
    """
    name = message.text.strip()

    # Валидация имени
    is_valid, error = validate_name(name)
    if not is_valid:
        await message.answer(
            text=INVALID_NAME.format(error=error),
            reply_markup=get_cancel_checkout_keyboard()
        )
        return

    # Сохраняем имя в state
    await state.update_data(customer_name=name)

    logger.info(f"Пользователь {user.telegram_id} ввел имя: {name}")

    # Переходим к вводу телефона
    await state.set_state(OrderStates.waiting_for_phone)
    await message.answer(
        text=CHECKOUT_ASK_PHONE,
        reply_markup=get_cancel_checkout_keyboard()
    )


@router.message(OrderStates.waiting_for_phone)
async def process_phone(
    message: Message,
    state: FSMContext,
    user: User
) -> None:
    """
    Обработать введенный номер телефона

    Args:
        message: Сообщение от пользователя
        state: FSM контекст
        user: Пользователь
    """
    phone = message.text.strip()

    # Валидация телефона
    is_valid, result = validate_phone(phone)
    if not is_valid:
        await message.answer(
            text=INVALID_PHONE.format(error=result),
            reply_markup=get_cancel_checkout_keyboard()
        )
        return

    # result содержит отформатированный номер
    formatted_phone = result

    # Сохраняем телефон в state
    await state.update_data(customer_phone=formatted_phone)

    logger.info(f"Пользователь {user.telegram_id} ввел телефон: {formatted_phone}")

    # Получаем сохраненные данные для отображения
    data = await state.get_data()
    name = data.get('customer_name', '')

    # Переходим к выбору способа доставки
    await state.set_state(OrderStates.waiting_for_delivery_type)
    await message.answer(
        text=CHECKOUT_ASK_DELIVERY.format(name=name, phone=formatted_phone),
        reply_markup=get_delivery_type_keyboard()
    )


@router.callback_query(OrderStates.waiting_for_delivery_type, F.data.startswith("delivery:"))
async def process_delivery_type(
    callback: CallbackQuery,
    state: FSMContext,
    user: User
) -> None:
    """
    Обработать выбор способа доставки

    Args:
        callback: Callback query
        state: FSM контекст
        user: Пользователь
    """
    delivery_type_str = callback.data.split(":")[-1]

    # Определяем тип доставки
    if delivery_type_str == "courier":
        delivery_type = DeliveryType.COURIER
        delivery_type_text = "Курьер"
    else:
        delivery_type = DeliveryType.PICKUP
        delivery_type_text = "Самовывоз"

    # Сохраняем тип доставки в state
    await state.update_data(
        delivery_type=delivery_type,
        delivery_type_text=delivery_type_text
    )

    logger.info(f"Пользователь {user.telegram_id} выбрал доставку: {delivery_type_text}")

    # Получаем сохраненные данные
    data = await state.get_data()
    name = data.get('customer_name', '')
    phone = data.get('customer_phone', '')

    # Если выбран курьер, спрашиваем адрес
    if delivery_type == DeliveryType.COURIER:
        await state.set_state(OrderStates.waiting_for_address)
        await callback.message.edit_text(
            text=CHECKOUT_ASK_ADDRESS.format(name=name, phone=phone),
            reply_markup=get_cancel_checkout_keyboard()
        )
    else:
        # Если самовывоз, пропускаем адрес и переходим к комментарию
        await state.update_data(delivery_address=None)
        await state.set_state(OrderStates.waiting_for_comment)
        await callback.message.edit_text(
            text=CHECKOUT_ASK_COMMENT.format(
                name=name,
                phone=phone,
                delivery_type=delivery_type_text,
                address_line=""
            ),
            reply_markup=get_skip_comment_keyboard()
        )

    await callback.answer()


@router.message(OrderStates.waiting_for_address)
async def process_address(
    message: Message,
    state: FSMContext,
    user: User
) -> None:
    """
    Обработать введенный адрес доставки

    Args:
        message: Сообщение от пользователя
        state: FSM контекст
        user: Пользователь
    """
    address = message.text.strip()

    # Валидация адреса
    is_valid, error = validate_address(address)
    if not is_valid:
        await message.answer(
            text=INVALID_ADDRESS.format(error=error),
            reply_markup=get_cancel_checkout_keyboard()
        )
        return

    # Сохраняем адрес в state
    await state.update_data(delivery_address=address)

    logger.info(f"Пользователь {user.telegram_id} ввел адрес: {address}")

    # Получаем сохраненные данные
    data = await state.get_data()
    name = data.get('customer_name', '')
    phone = data.get('customer_phone', '')
    delivery_type_text = data.get('delivery_type_text', '')

    # Переходим к вводу комментария
    await state.set_state(OrderStates.waiting_for_comment)
    await message.answer(
        text=CHECKOUT_ASK_COMMENT.format(
            name=name,
            phone=phone,
            delivery_type=delivery_type_text,
            address_line=f"Адрес: {address}"
        ),
        reply_markup=get_skip_comment_keyboard()
    )


@router.callback_query(OrderStates.waiting_for_comment, F.data == "checkout:skip_comment")
async def skip_comment(
    callback: CallbackQuery,
    state: FSMContext,
    user: User,
    session: AsyncSession
) -> None:
    """
    Пропустить ввод комментария

    Args:
        callback: Callback query
        state: FSM контекст
        user: Пользователь
        session: Сессия БД
    """
    # Сохраняем пустой комментарий
    await state.update_data(comment=None)

    logger.info(f"Пользователь {user.telegram_id} пропустил комментарий")

    # Показываем итоговое подтверждение
    await show_confirmation(callback.message, state, user, session, is_callback=True)
    await callback.answer()


@router.message(OrderStates.waiting_for_comment)
async def process_comment(
    message: Message,
    state: FSMContext,
    user: User,
    session: AsyncSession
) -> None:
    """
    Обработать введенный комментарий

    Args:
        message: Сообщение от пользователя
        state: FSM контекст
        user: Пользователь
        session: Сессия БД
    """
    comment = message.text.strip()

    # Валидация комментария
    is_valid, error = validate_comment(comment)
    if not is_valid:
        await message.answer(
            text=INVALID_COMMENT.format(error=error),
            reply_markup=get_skip_comment_keyboard()
        )
        return

    # Сохраняем комментарий в state
    await state.update_data(comment=comment)

    logger.info(f"Пользователь {user.telegram_id} ввел комментарий")

    # Показываем итоговое подтверждение
    await show_confirmation(message, state, user, session)


async def show_confirmation(
    message: Message,
    state: FSMContext,
    user: User,
    session: AsyncSession,
    is_callback: bool = False
) -> None:
    """
    Показать итоговое подтверждение заказа

    Args:
        message: Сообщение
        state: FSM контекст
        user: Пользователь
        session: Сессия БД
        is_callback: Вызвано ли из callback
    """
    # Получаем все данные из state
    data = await state.get_data()
    name = data.get('customer_name', '')
    phone = data.get('customer_phone', '')
    delivery_type_text = data.get('delivery_type_text', '')
    address = data.get('delivery_address')
    comment = data.get('comment')

    # Получаем корзину для отображения
    cart_items = await cart_service.get_cart_items(session, user.id)
    cart_summary = ""
    for item in cart_items:
        if not item.product:
            continue
        name_product = item.product.name
        price = item.product.effective_price
        quantity = item.quantity
        subtotal = price * quantity

        variant_info = ""
        if item.variant:
            variant_info = f" ({item.variant.size}, {item.variant.color})"

        cart_summary += f"{name_product}{variant_info}\n"
        cart_summary += f"{price} ₽ × {quantity} шт. = {subtotal} ₽\n\n"

    # Рассчитываем общую сумму
    total = await cart_service.get_cart_total(session, user.id)

    # Формируем строки для адреса и комментария
    address_line = f"Адрес: {address}" if address else ""
    comment_line = f"Комментарий: {comment}" if comment else ""

    # Переходим к состоянию подтверждения
    await state.set_state(OrderStates.waiting_for_confirmation)

    # Формируем текст
    text = CHECKOUT_CONFIRMATION.format(
        cart_summary=cart_summary,
        total=total,
        name=name,
        phone=phone,
        delivery_type=delivery_type_text,
        address_line=address_line,
        comment_line=comment_line
    )

    if is_callback:
        await message.edit_text(
            text=text,
            reply_markup=get_order_confirmation_keyboard()
        )
    else:
        await message.answer(
            text=text,
            reply_markup=get_order_confirmation_keyboard()
        )


@router.callback_query(OrderStates.waiting_for_confirmation, F.data == "checkout:confirm")
async def confirm_order(
    callback: CallbackQuery,
    state: FSMContext,
    user: User,
    session: AsyncSession
) -> None:
    """
    Подтвердить и создать заказ

    Args:
        callback: Callback query
        state: FSM контекст
        user: Пользователь
        session: Сессия БД
    """
    logger.info(f"Пользователь {user.telegram_id} подтверждает заказ")

    # Получаем все данные из state
    data = await state.get_data()
    customer_name = data.get('customer_name')
    customer_phone = data.get('customer_phone')
    delivery_type = data.get('delivery_type')
    delivery_address = data.get('delivery_address')
    comment = data.get('comment')

    # Создаем заказ
    order = await order_service.create_order(
        session=session,
        user_id=user.id,
        customer_name=customer_name,
        customer_phone=customer_phone,
        delivery_type=delivery_type,
        delivery_address=delivery_address,
        comment=comment
    )

    if not order:
        await callback.message.edit_text(text=ORDER_CREATION_FAILED)
        await callback.answer("Ошибка при создании заказа", show_alert=True)
        await state.clear()
        return

    # Очищаем FSM state
    await state.clear()

    # Отправляем сообщение об успешном создании заказа
    await callback.message.edit_text(
        text=ORDER_CREATED_SUCCESS.format(
            order_number=order.order_number,
            total=order.total_amount
        )
    )

    await callback.answer("Заказ успешно оформлен!")

    logger.info(f"Создан заказ {order.order_number} для пользователя {user.telegram_id}")


@router.callback_query(OrderStates.waiting_for_confirmation, F.data == "checkout:edit")
async def edit_order_data(
    callback: CallbackQuery,
    state: FSMContext
) -> None:
    """
    Вернуться к редактированию данных заказа

    Args:
        callback: Callback query
        state: FSM контекст
    """
    # Возвращаем к вводу имени
    await state.set_state(OrderStates.waiting_for_name)
    await callback.message.edit_text(
        text=CHECKOUT_ASK_NAME,
        reply_markup=get_cancel_checkout_keyboard()
    )
    await callback.answer("Введите данные заново")


@router.callback_query(F.data == "checkout:cancel")
async def cancel_checkout(
    callback: CallbackQuery,
    state: FSMContext,
    user: User
) -> None:
    """
    Отменить оформление заказа

    Args:
        callback: Callback query
        state: FSM контекст
        user: Пользователь
    """
    logger.info(f"Пользователь {user.telegram_id} отменил оформление заказа")

    # Очищаем FSM state
    await state.clear()

    await callback.message.edit_text(text=ORDER_CANCELLED)
    await callback.answer()


@router.callback_query(OrderStates.waiting_for_delivery_type, F.data == "checkout:back")
async def back_to_phone(
    callback: CallbackQuery,
    state: FSMContext
) -> None:
    """
    Вернуться к вводу телефона

    Args:
        callback: Callback query
        state: FSM контекст
    """
    await state.set_state(OrderStates.waiting_for_phone)
    await callback.message.edit_text(
        text=CHECKOUT_ASK_PHONE,
        reply_markup=get_cancel_checkout_keyboard()
    )
    await callback.answer()


@router.callback_query(OrderStates.waiting_for_comment, F.data == "checkout:back")
async def back_to_delivery_or_address(
    callback: CallbackQuery,
    state: FSMContext
) -> None:
    """
    Вернуться к выбору доставки или вводу адреса

    Args:
        callback: Callback query
        state: FSM контекст
    """
    data = await state.get_data()
    delivery_type = data.get('delivery_type')

    if delivery_type == DeliveryType.COURIER:
        # Если был выбран курьер, возвращаемся к вводу адреса
        await state.set_state(OrderStates.waiting_for_address)
        name = data.get('customer_name', '')
        phone = data.get('customer_phone', '')
        await callback.message.edit_text(
            text=CHECKOUT_ASK_ADDRESS.format(name=name, phone=phone),
            reply_markup=get_cancel_checkout_keyboard()
        )
    else:
        # Если самовывоз, возвращаемся к выбору доставки
        await state.set_state(OrderStates.waiting_for_delivery_type)
        name = data.get('customer_name', '')
        phone = data.get('customer_phone', '')
        await callback.message.edit_text(
            text=CHECKOUT_ASK_DELIVERY.format(name=name, phone=phone),
            reply_markup=get_delivery_type_keyboard()
        )

    await callback.answer()
