"""
Валидаторы для различных типов данных
"""
import re


def validate_phone(phone: str) -> tuple[bool, str]:
    """
    Валидация номера телефона

    Принимает форматы:
    - +7 (XXX) XXX-XX-XX
    - +7XXXXXXXXXX
    - 8XXXXXXXXXX
    - 7XXXXXXXXXX
    - И другие варианты

    Args:
        phone: Строка с номером телефона

    Returns:
        Кортеж (валидность, нормализованный номер или сообщение об ошибке)
    """
    # Удаляем все символы кроме цифр и +
    cleaned = re.sub(r'[^\d+]', '', phone)

    # Проверяем, что остались только цифры (и возможно + в начале)
    if not re.match(r'^\+?\d+$', cleaned):
        return False, "Номер телефона должен содержать только цифры"

    # Убираем + для дальнейшей обработки
    digits_only = cleaned.lstrip('+')

    # Если начинается с 8, заменяем на 7
    if digits_only.startswith('8'):
        digits_only = '7' + digits_only[1:]

    # Если не начинается с 7, добавляем 7
    if not digits_only.startswith('7'):
        digits_only = '7' + digits_only

    # Проверяем длину (должно быть 11 цифр для российского номера)
    if len(digits_only) != 11:
        return False, "Номер телефона должен содержать 11 цифр (например: +7 900 123-45-67)"

    # Проверяем корректность кода оператора (второй и третья цифры не должны быть 0)
    if digits_only[1] == '0' or digits_only[2] == '0':
        return False, "Некорректный код оператора"

    # Форматируем в красивый вид: +7 (XXX) XXX-XX-XX
    formatted = f"+{digits_only[0]} ({digits_only[1:4]}) {digits_only[4:7]}-{digits_only[7:9]}-{digits_only[9:11]}"

    return True, formatted


def validate_name(name: str) -> tuple[bool, str]:
    """
    Валидация имени получателя

    Args:
        name: Имя

    Returns:
        Кортеж (валидность, сообщение об ошибке или пустая строка)
    """
    # Убираем лишние пробелы
    name = name.strip()

    # Проверяем длину
    if len(name) < 2:
        return False, "Имя слишком короткое (минимум 2 символа)"

    if len(name) > 100:
        return False, "Имя слишком длинное (максимум 100 символов)"

    # Проверяем, что содержит только буквы, пробелы и дефисы
    if not re.match(r'^[а-яА-ЯёЁa-zA-Z\s\-]+$', name):
        return False, "Имя может содержать только буквы, пробелы и дефисы"

    return True, ""


def validate_address(address: str) -> tuple[bool, str]:
    """
    Валидация адреса доставки

    Args:
        address: Адрес

    Returns:
        Кортеж (валидность, сообщение об ошибке или пустая строка)
    """
    # Убираем лишние пробелы
    address = address.strip()

    # Проверяем длину
    if len(address) < 10:
        return False, "Адрес слишком короткий (минимум 10 символов)"

    if len(address) > 500:
        return False, "Адрес слишком длинный (максимум 500 символов)"

    return True, ""


def validate_comment(comment: str) -> tuple[bool, str]:
    """
    Валидация комментария к заказу

    Args:
        comment: Комментарий

    Returns:
        Кортеж (валидность, сообщение об ошибке или пустая строка)
    """
    # Убираем лишние пробелы
    comment = comment.strip()

    # Проверяем длину
    if len(comment) > 1000:
        return False, "Комментарий слишком длинный (максимум 1000 символов)"

    return True, ""
