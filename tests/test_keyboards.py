"""
Тесты для клавиатур (keyboards)
"""
import pytest
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton

from bot.keyboards.user_keyboards import (
    get_product_card_inline_keyboard,
    get_pagination_keyboard,
    get_categories_keyboard,
    get_main_menu_keyboard
)
from bot.database.models.category import Category
from bot.database.models.product import Product


class TestProductCardInlineKeyboard:
    """Тесты для get_product_card_inline_keyboard"""

    def test_keyboard_without_variants(self):
        """Тест: клавиатура для товара без вариантов"""
        keyboard = get_product_card_inline_keyboard(
            product_id=1,
            has_variants=False,
            category_id=5
        )

        assert isinstance(keyboard, InlineKeyboardMarkup)
        assert len(keyboard.inline_keyboard) > 0

        # Проверяем наличие кнопки "Добавить в корзину"
        buttons_text = []
        for row in keyboard.inline_keyboard:
            for button in row:
                buttons_text.append(button.text)

        assert any("корзину" in text.lower() for text in buttons_text)

    def test_keyboard_with_variants(self):
        """Тест: клавиатура для товара с вариантами"""
        keyboard = get_product_card_inline_keyboard(
            product_id=2,
            has_variants=True,
            category_id=5
        )

        assert isinstance(keyboard, InlineKeyboardMarkup)
        assert len(keyboard.inline_keyboard) > 0

        # Проверяем наличие кнопки "Выбрать размер/цвет"
        buttons_text = []
        for row in keyboard.inline_keyboard:
            for button in row:
                buttons_text.append(button.text)

        assert any("размер" in text.lower() or "цвет" in text.lower() for text in buttons_text)

    def test_button_callback_data(self):
        """Тест: корректность callback_data"""
        product_id = 42
        keyboard = get_product_card_inline_keyboard(
            product_id=product_id,
            has_variants=False
        )

        # Ищем кнопку с callback_data
        found_callback = False
        for row in keyboard.inline_keyboard:
            for button in row:
                if hasattr(button, 'callback_data') and button.callback_data:
                    assert str(product_id) in button.callback_data
                    found_callback = True

        assert found_callback, "Не найдена кнопка с callback_data"


class TestPaginationKeyboard:
    """Тесты для get_pagination_keyboard"""

    def test_first_page(self):
        """Тест: первая страница (только кнопка "Следующая")"""
        keyboard = get_pagination_keyboard(
            category_id=1,
            current_page=1,
            total_pages=3,
            parent_id=None
        )

        assert isinstance(keyboard, InlineKeyboardMarkup)

        # Собираем все кнопки
        all_buttons = []
        for row in keyboard.inline_keyboard:
            for button in row:
                all_buttons.append(button)

        # Проверяем наличие кнопки "Следующая"
        button_texts = [btn.text for btn in all_buttons]
        assert any("следующая" in text.lower() for text in button_texts)

        # Проверяем отсутствие кнопки "Предыдущая"
        assert not any("предыдущая" in text.lower() for text in button_texts)

    def test_middle_page(self):
        """Тест: средняя страница (обе кнопки навигации)"""
        keyboard = get_pagination_keyboard(
            category_id=1,
            current_page=2,
            total_pages=3,
            parent_id=None
        )

        all_buttons = []
        for row in keyboard.inline_keyboard:
            for button in row:
                all_buttons.append(button)

        button_texts = [btn.text for btn in all_buttons]

        # Проверяем наличие обеих кнопок
        assert any("следующая" in text.lower() for text in button_texts)
        assert any("предыдущая" in text.lower() for text in button_texts)

    def test_last_page(self):
        """Тест: последняя страница (только кнопка "Предыдущая")"""
        keyboard = get_pagination_keyboard(
            category_id=1,
            current_page=3,
            total_pages=3,
            parent_id=None
        )

        all_buttons = []
        for row in keyboard.inline_keyboard:
            for button in row:
                all_buttons.append(button)

        button_texts = [btn.text for btn in all_buttons]

        # Проверяем наличие кнопки "Предыдущая"
        assert any("предыдущая" in text.lower() for text in button_texts)

        # Проверяем отсутствие кнопки "Следующая"
        assert not any("следующая" in text.lower() for text in button_texts)

    def test_single_page(self):
        """Тест: одна страница (нет кнопок пагинации)"""
        keyboard = get_pagination_keyboard(
            category_id=1,
            current_page=1,
            total_pages=1,
            parent_id=None
        )

        all_buttons = []
        for row in keyboard.inline_keyboard:
            for button in row:
                all_buttons.append(button)

        button_texts = [btn.text for btn in all_buttons]

        # Не должно быть кнопок навигации
        assert not any("следующая" in text.lower() for text in button_texts)
        assert not any("предыдущая" in text.lower() for text in button_texts)

        # Должна быть кнопка "К категориям" или "Назад"
        assert any("категориям" in text.lower() or "назад" in text.lower() for text in button_texts)

    def test_back_button_with_parent(self):
        """Тест: кнопка "Назад" при наличии родительской категории"""
        keyboard = get_pagination_keyboard(
            category_id=5,
            current_page=1,
            total_pages=2,
            parent_id=3
        )

        all_buttons = []
        for row in keyboard.inline_keyboard:
            for button in row:
                all_buttons.append(button)

        button_texts = [btn.text for btn in all_buttons]

        # Должна быть кнопка "Назад"
        assert any("назад" in text.lower() for text in button_texts)

    def test_back_button_without_parent(self):
        """Тест: кнопка "К категориям" без родительской категории"""
        keyboard = get_pagination_keyboard(
            category_id=1,
            current_page=1,
            total_pages=2,
            parent_id=None
        )

        all_buttons = []
        for row in keyboard.inline_keyboard:
            for button in row:
                all_buttons.append(button)

        button_texts = [btn.text for btn in all_buttons]

        # Должна быть кнопка "К категориям"
        assert any("категориям" in text.lower() for text in button_texts)

    def test_callback_data_format(self):
        """Тест: формат callback_data для кнопок пагинации"""
        category_id = 5
        current_page = 2

        keyboard = get_pagination_keyboard(
            category_id=category_id,
            current_page=current_page,
            total_pages=3,
            parent_id=None
        )

        # Проверяем формат callback_data
        for row in keyboard.inline_keyboard:
            for button in row:
                if "следующая" in button.text.lower():
                    assert f"category:{category_id}:page:{current_page + 1}" == button.callback_data
                elif "предыдущая" in button.text.lower():
                    assert f"category:{category_id}:page:{current_page - 1}" == button.callback_data


class TestCategoriesKeyboard:
    """Тесты для get_categories_keyboard"""

    @pytest.mark.asyncio
    async def test_categories_keyboard(self, test_category: Category):
        """Тест: клавиатура со списком категорий"""
        categories = [test_category]

        keyboard = get_categories_keyboard(
            categories=categories,
            parent_id=None
        )

        assert isinstance(keyboard, InlineKeyboardMarkup)
        assert len(keyboard.inline_keyboard) > 0

        # Проверяем наличие категории
        found_category = False
        for row in keyboard.inline_keyboard:
            for button in row:
                if test_category.name in button.text:
                    found_category = True
                    break

        assert found_category, f"Категория {test_category.name} не найдена в клавиатуре"

    def test_empty_categories(self):
        """Тест: пустой список категорий"""
        keyboard = get_categories_keyboard(
            categories=[],
            parent_id=None
        )

        assert isinstance(keyboard, InlineKeyboardMarkup)

        # Должна быть хотя бы кнопка "Главное меню"
        assert len(keyboard.inline_keyboard) > 0


class TestMainMenuKeyboard:
    """Тесты для get_main_menu_keyboard"""

    def test_regular_user_keyboard(self):
        """Тест: главное меню для обычного пользователя"""
        keyboard = get_main_menu_keyboard(is_admin=False)

        # Получаем все кнопки
        all_buttons = []
        for row in keyboard.keyboard:
            for button in row:
                all_buttons.append(button.text)

        # Проверяем наличие основных кнопок
        assert "Каталог" in all_buttons
        assert "Корзина" in all_buttons

        # Проверяем отсутствие кнопки админ-панели
        assert "Админ-панель" not in all_buttons and "Админ" not in str(all_buttons)

    def test_admin_keyboard(self):
        """Тест: главное меню для администратора"""
        keyboard = get_main_menu_keyboard(is_admin=True)

        # Получаем все кнопки
        all_buttons = []
        for row in keyboard.keyboard:
            for button in row:
                all_buttons.append(button.text)

        # Проверяем наличие основных кнопок
        assert "Каталог" in all_buttons
        assert "Корзина" in all_buttons

        # Проверяем наличие кнопки админ-панели
        assert "Админ" in str(all_buttons) or "админ" in str(all_buttons).lower()


class TestKeyboardIntegration:
    """Интеграционные тесты для клавиатур"""

    def test_all_buttons_have_required_fields(self):
        """Тест: все кнопки имеют необходимые поля"""
        # Тестируем клавиатуру товара
        keyboard = get_product_card_inline_keyboard(
            product_id=1,
            has_variants=False
        )

        for row in keyboard.inline_keyboard:
            for button in row:
                assert isinstance(button, InlineKeyboardButton)
                assert hasattr(button, 'text')
                assert button.text is not None
                assert len(button.text) > 0

    def test_pagination_keyboard_consistency(self):
        """Тест: консистентность клавиатуры пагинации"""
        for page in range(1, 4):
            keyboard = get_pagination_keyboard(
                category_id=1,
                current_page=page,
                total_pages=3,
                parent_id=None
            )

            # Каждая клавиатура должна быть валидной
            assert isinstance(keyboard, InlineKeyboardMarkup)
            assert len(keyboard.inline_keyboard) > 0

            # Все кнопки должны иметь текст
            for row in keyboard.inline_keyboard:
                for button in row:
                    assert button.text
                    assert len(button.text) > 0
