"""
Тесты для обработчика каталога товаров (catalog handler)
"""
import pytest
from unittest.mock import AsyncMock, Mock, patch, MagicMock
from aiogram.types import CallbackQuery, Message, User as TelegramUser, Chat
from sqlalchemy.ext.asyncio import AsyncSession

from bot.handlers.user.catalog import (
    show_products_in_category,
    send_product_card,
    delete_old_product_cards,
    product_card_messages
)
from bot.database.models.user import User
from bot.database.models.category import Category
from bot.database.models.product import Product


@pytest.fixture
def mock_callback():
    """Создает мок callback query"""
    callback = AsyncMock(spec=CallbackQuery)
    callback.message = AsyncMock(spec=Message)
    callback.message.chat = Mock(spec=Chat)
    callback.message.chat.id = 123456789
    callback.message.edit_text = AsyncMock()
    callback.message.delete = AsyncMock()
    callback.answer = AsyncMock()
    callback.bot = AsyncMock()
    callback.bot.send_message = AsyncMock()
    callback.bot.send_photo = AsyncMock()
    callback.bot.delete_message = AsyncMock()
    return callback


@pytest.fixture
def mock_telegram_user():
    """Создает мок Telegram пользователя"""
    user = Mock(spec=TelegramUser)
    user.id = 123456789
    user.username = "testuser"
    user.full_name = "Test User"
    return user


class TestShowProductsInCategory:
    """Тесты для функции show_products_in_category"""

    @pytest.mark.asyncio
    async def test_show_products_empty_category(
        self,
        mock_callback,
        test_user: User,
        test_category: Category,
        session: AsyncSession
    ):
        """Тест: показ пустой категории"""
        # Вызываем функцию с пустой категорией
        await show_products_in_category(
            callback=mock_callback,
            user=test_user,
            session=session,
            category=test_category,
            page=1
        )

        # Проверяем, что было отправлено сообщение о пустой категории
        mock_callback.message.edit_text.assert_called_once()
        call_args = mock_callback.message.edit_text.call_args
        assert "нет товаров" in call_args[1]["text"].lower() or "товаров" in call_args[1]["text"].lower()

    @pytest.mark.asyncio
    async def test_show_products_with_items(
        self,
        mock_callback,
        test_user: User,
        test_category: Category,
        test_products_batch,
        session: AsyncSession
    ):
        """Тест: показ категории с товарами"""
        # Настраиваем мок для send_message
        mock_message = AsyncMock()
        mock_message.message_id = 999
        mock_callback.bot.send_message.return_value = mock_message
        mock_callback.bot.send_photo.return_value = mock_message

        await show_products_in_category(
            callback=mock_callback,
            user=test_user,
            session=session,
            category=test_category,
            page=1
        )

        # Проверяем, что старое сообщение было удалено
        mock_callback.message.delete.assert_called_once()

        # Проверяем, что был отправлен заголовок через send_message
        assert mock_callback.bot.send_message.call_count >= 1
        # Первый вызов должен быть заголовок
        first_call = mock_callback.bot.send_message.call_args_list[0]
        header_text = first_call[1]['text']
        assert "Страница" in header_text
        assert test_category.name in header_text

        # Проверяем, что были отправлены карточки товаров
        # Должно быть 6 карточек (по умолчанию) + 1 навигационное сообщение + 1 заголовок
        assert mock_callback.bot.send_photo.call_count >= 6 or \
               mock_callback.bot.send_message.call_count >= 7

    @pytest.mark.asyncio
    async def test_pagination_first_page(
        self,
        mock_callback,
        test_user: User,
        test_category: Category,
        test_products_batch,
        session: AsyncSession
    ):
        """Тест: первая страница пагинации"""
        mock_message = AsyncMock()
        mock_message.message_id = 999
        mock_callback.bot.send_message.return_value = mock_message
        mock_callback.bot.send_photo.return_value = mock_message

        await show_products_in_category(
            callback=mock_callback,
            user=test_user,
            session=session,
            category=test_category,
            page=1
        )

        # Проверяем, что в заголовке указана страница 1
        header_text = mock_callback.message.edit_text.call_args[0][0]
        assert "Страница 1" in header_text

    @pytest.mark.asyncio
    async def test_pagination_second_page(
        self,
        mock_callback,
        test_user: User,
        test_category: Category,
        test_products_batch,
        session: AsyncSession
    ):
        """Тест: вторая страница пагинации"""
        mock_message = AsyncMock()
        mock_message.message_id = 999
        mock_callback.bot.send_message.return_value = mock_message
        mock_callback.bot.send_photo.return_value = mock_message

        await show_products_in_category(
            callback=mock_callback,
            user=test_user,
            session=session,
            category=test_category,
            page=2
        )

        # Проверяем, что в заголовке указана страница 2
        header_text = mock_callback.message.edit_text.call_args[0][0]
        assert "Страница 2" in header_text


class TestSendProductCard:
    """Тесты для функции send_product_card"""

    @pytest.mark.asyncio
    async def test_send_card_with_image(
        self,
        test_product: Product,
        test_category: Category,
        session: AsyncSession
    ):
        """Тест: отправка карточки с изображением"""
        bot_mock = AsyncMock()
        mock_message = AsyncMock()
        mock_message.message_id = 123
        bot_mock.send_photo.return_value = mock_message

        message_id = await send_product_card(
            bot=bot_mock,
            chat_id=123456789,
            product=test_product,
            session=session,
            category_id=test_category.id
        )

        # Проверяем, что было отправлено фото
        bot_mock.send_photo.assert_called_once()
        assert message_id == 123

        # Проверяем содержимое caption
        call_args = bot_mock.send_photo.call_args
        caption = call_args[1]["caption"]
        assert test_product.name in caption
        assert str(test_product.price) in caption or "5000" in caption

    @pytest.mark.asyncio
    async def test_send_card_with_discount(
        self,
        test_product_with_discount: Product,
        test_category: Category,
        session: AsyncSession
    ):
        """Тест: отправка карточки товара со скидкой"""
        bot_mock = AsyncMock()
        mock_message = AsyncMock()
        mock_message.message_id = 456
        bot_mock.send_photo.return_value = mock_message

        message_id = await send_product_card(
            bot=bot_mock,
            chat_id=123456789,
            product=test_product_with_discount,
            session=session,
            category_id=test_category.id
        )

        bot_mock.send_photo.assert_called_once()
        call_args = bot_mock.send_photo.call_args
        caption = call_args[1]["caption"]

        # Проверяем наличие информации о скидке
        assert "Скидка" in caption or "скидка" in caption
        assert message_id == 456

    @pytest.mark.asyncio
    async def test_send_card_without_image(
        self,
        test_category: Category,
        session: AsyncSession
    ):
        """Тест: отправка карточки без изображения"""
        # Создаем товар без изображений
        product = Product(
            category_id=test_category.id,
            name="Товар без фото",
            description="Описание товара",
            price=3000.00,
            images=[],
            is_active=True
        )
        session.add(product)
        await session.commit()
        await session.refresh(product)

        bot_mock = AsyncMock()
        mock_message = AsyncMock()
        mock_message.message_id = 789
        bot_mock.send_message.return_value = mock_message

        message_id = await send_product_card(
            bot=bot_mock,
            chat_id=123456789,
            product=product,
            session=session,
            category_id=test_category.id
        )

        # Проверяем, что было отправлено текстовое сообщение
        bot_mock.send_message.assert_called_once()
        assert message_id == 789

    @pytest.mark.asyncio
    async def test_send_card_with_variants(
        self,
        test_product: Product,
        test_product_variant,
        test_category: Category,
        session: AsyncSession
    ):
        """Тест: отправка карточки товара с вариантами"""
        bot_mock = AsyncMock()
        mock_message = AsyncMock()
        mock_message.message_id = 111
        bot_mock.send_photo.return_value = mock_message

        # Загружаем варианты товара
        await session.refresh(test_product, ["variants"])

        message_id = await send_product_card(
            bot=bot_mock,
            chat_id=123456789,
            product=test_product,
            session=session,
            category_id=test_category.id
        )

        bot_mock.send_photo.assert_called_once()
        call_args = bot_mock.send_photo.call_args

        # Проверяем, что клавиатура содержит кнопку для выбора вариантов
        keyboard = call_args[1]["reply_markup"]
        assert keyboard is not None


class TestDeleteOldProductCards:
    """Тесты для функции delete_old_product_cards"""

    @pytest.mark.asyncio
    async def test_delete_messages(self):
        """Тест: удаление старых сообщений"""
        bot_mock = AsyncMock()
        user_id = 123456789
        category_id = 1

        # Заполняем хранилище ID сообщений с новой структурой
        product_card_messages[user_id] = {
            category_id: {
                'header': 100,
                'cards': [101, 102, 103],
                'navigation': 104
            }
        }

        await delete_old_product_cards(
            bot=bot_mock,
            user_id=user_id,
            category_id=category_id
        )

        # Проверяем, что delete_message был вызван 5 раз (header + 3 cards + navigation)
        assert bot_mock.delete_message.call_count == 5

        # Проверяем, что структура очищена
        assert product_card_messages[user_id][category_id]['header'] is None
        assert product_card_messages[user_id][category_id]['cards'] == []
        assert product_card_messages[user_id][category_id]['navigation'] is None

    @pytest.mark.asyncio
    async def test_delete_no_messages(self):
        """Тест: попытка удаления когда нет сообщений"""
        bot_mock = AsyncMock()
        user_id = 999999999
        category_id = 99

        # Вызываем без предварительного заполнения хранилища
        await delete_old_product_cards(
            bot=bot_mock,
            user_id=user_id,
            category_id=category_id
        )

        # Проверяем, что delete_message не вызывался
        bot_mock.delete_message.assert_not_called()

    @pytest.mark.asyncio
    async def test_delete_with_errors(self):
        """Тест: обработка ошибок при удалении сообщений"""
        bot_mock = AsyncMock()
        bot_mock.delete_message.side_effect = Exception("Message not found")

        user_id = 123456789
        category_id = 1

        product_card_messages[user_id] = {
            category_id: {
                'header': 200,
                'cards': [201],
                'navigation': 202
            }
        }

        # Функция не должна падать при ошибках удаления
        await delete_old_product_cards(
            bot=bot_mock,
            user_id=user_id,
            category_id=category_id
        )

        # Проверяем, что попытки удаления были сделаны (header + 1 card + navigation = 3)
        assert bot_mock.delete_message.call_count == 3

        # Структура все равно должна быть очищена
        assert product_card_messages[user_id][category_id]['header'] is None
        assert product_card_messages[user_id][category_id]['cards'] == []
        assert product_card_messages[user_id][category_id]['navigation'] is None


class TestProductCardMessages:
    """Тесты для хранилища product_card_messages"""

    def test_storage_structure(self):
        """Тест: структура хранилища сообщений"""
        user_id = 111111
        category_id = 5

        # Инициализируем хранилище с новой структурой
        product_card_messages[user_id] = {
            category_id: {
                'header': 300,
                'cards': [301, 302, 303],
                'navigation': 304
            }
        }

        # Проверяем структуру
        assert user_id in product_card_messages
        assert category_id in product_card_messages[user_id]
        assert product_card_messages[user_id][category_id]['header'] == 300
        assert len(product_card_messages[user_id][category_id]['cards']) == 3
        assert product_card_messages[user_id][category_id]['navigation'] == 304

        # Очищаем для других тестов
        product_card_messages.clear()
