"""
Скрипт для создания тестовых изображений
ОБНОВЛЕН ДЛЯ СИСТЕМЫ КАРТОЧЕК ТОВАРОВ (ЭТАП 4)

Создает изображения для ВСЕХ товаров из add_test_data.py
"""
from PIL import Image, ImageDraw, ImageFont
import os


def create_test_image(filename: str, text: str, color: tuple, subtext: str = ""):
    """
    Создать тестовое изображение с текстом

    Args:
        filename: Имя файла для сохранения
        text: Основной текст на изображении
        color: Цвет фона (RGB)
        subtext: Дополнительный текст (необязательно)
    """
    # Создаем изображение 1200x900 (больший размер для лучшего качества)
    img = Image.new('RGB', (1200, 900), color=color)
    draw = ImageDraw.Draw(img)

    # Пытаемся использовать системный шрифт
    try:
        font_large = ImageFont.truetype("/System/Library/Fonts/Helvetica.ttc", 100)
        font_small = ImageFont.truetype("/System/Library/Fonts/Helvetica.ttc", 60)
    except:
        font_large = ImageFont.load_default()
        font_small = ImageFont.load_default()

    # Рисуем основной текст
    bbox = draw.textbbox((0, 0), text, font=font_large)
    text_width = bbox[2] - bbox[0]
    text_height = bbox[3] - bbox[1]
    x = (1200 - text_width) // 2
    y = (900 - text_height) // 2 - 50
    draw.text((x, y), text, fill=(255, 255, 255), font=font_large)

    # Рисуем подтекст если есть
    if subtext:
        bbox_sub = draw.textbbox((0, 0), subtext, font=font_small)
        text_width_sub = bbox_sub[2] - bbox_sub[0]
        x_sub = (1200 - text_width_sub) // 2
        y_sub = y + text_height + 30
        draw.text((x_sub, y_sub), subtext, fill=(200, 200, 200), font=font_small)

    # Добавляем рамку
    draw.rectangle([(10, 10), (1190, 890)], outline=(255, 255, 255), width=5)

    # Сохраняем
    img.save(filename, quality=95)
    print(f"   ✅ {filename}")


def main():
    """Создать все тестовые изображения"""
    print("=" * 60)
    print("🎨 СОЗДАНИЕ ТЕСТОВЫХ ИЗОБРАЖЕНИЙ ДЛЯ КАРТОЧЕК ТОВАРОВ")
    print("=" * 60)

    # Создаем папку, если её нет
    os.makedirs("media/products", exist_ok=True)
    print("\n📁 Папка media/products готова")

    print("\n🧥 Создание изображений для курток...")
    # КУРТКИ
    create_test_image("media/products/jacket_black_1.jpg", "Зимняя куртка", (30, 30, 30), "Premium Black")
    create_test_image("media/products/jacket_black_2.jpg", "Вид сзади", (40, 40, 40), "Premium Black")
    create_test_image("media/products/jacket_black_3.jpg", "Детали", (50, 50, 50), "Premium Black")

    create_test_image("media/products/jacket_red_1.jpg", "Спортивная куртка", (200, 30, 30), "Red Sport")
    create_test_image("media/products/jacket_red_2.jpg", "Вид сбоку", (220, 40, 40), "Red Sport")
    create_test_image("media/products/jacket_red_3.jpg", "В движении", (180, 20, 20), "Red Sport")

    create_test_image("media/products/jacket_purple_1.jpg", "Urban Fashion", (150, 50, 200), "Purple")
    create_test_image("media/products/jacket_purple_2.jpg", "Крупный план", (130, 40, 180), "Purple")
    create_test_image("media/products/jacket_purple_3.jpg", "Капюшон", (170, 60, 220), "Purple")

    create_test_image("media/products/jacket_casual_1.jpg", "Демисезонная", (100, 120, 130), "Casual")
    create_test_image("media/products/jacket_casual_2.jpg", "Детали", (90, 110, 120), "Casual")

    print("\n👔 Создание изображений для рубашек...")
    # РУБАШКИ
    create_test_image("media/products/shirt_white_1.jpg", "Белая рубашка", (240, 240, 240), "Premium")
    create_test_image("media/products/shirt_white_2.jpg", "Манжеты", (230, 230, 230), "Premium")

    create_test_image("media/products/shirt_plaid_1.jpg", "Рубашка в клетку", (180, 100, 80), "Lumberjack")
    create_test_image("media/products/shirt_plaid_2.jpg", "Стиль", (170, 90, 70), "Lumberjack")

    create_test_image("media/products/shirt_blue_1.jpg", "Синяя рубашка", (50, 80, 150), "Slim Fit")

    print("\n👖 Создание изображений для брюк...")
    # БРЮКИ
    create_test_image("media/products/pants_black_1.jpg", "Черные брюки", (35, 35, 35), "Business")
    create_test_image("media/products/pants_black_2.jpg", "Покрой", (45, 45, 45), "Business")

    create_test_image("media/products/jeans_slim_1.jpg", "Джинсы", (60, 90, 140), "Slim Fit")
    create_test_image("media/products/jeans_slim_2.jpg", "Детали", (50, 80, 130), "Slim Fit")

    create_test_image("media/products/chinos_beige_1.jpg", "Чиносы", (200, 180, 150), "Casual")

    print("\n👗 Создание изображений для платьев...")
    # ПЛАТЬЯ
    create_test_image("media/products/dress_evening_1.jpg", "Вечернее платье", (20, 20, 20), "Elegant")
    create_test_image("media/products/dress_evening_2.jpg", "Силуэт", (30, 30, 30), "Elegant")
    create_test_image("media/products/dress_evening_3.jpg", "Детали", (40, 40, 40), "Elegant")

    create_test_image("media/products/dress_summer_1.jpg", "Летнее платье", (255, 180, 200), "Floral")
    create_test_image("media/products/dress_summer_2.jpg", "Принт", (250, 170, 190), "Floral")

    create_test_image("media/products/dress_cocktail_1.jpg", "Коктейльное", (200, 20, 50), "Red Passion")
    create_test_image("media/products/dress_cocktail_2.jpg", "Силуэт", (190, 10, 40), "Red Passion")

    print("\n👚 Создание изображений для блузок...")
    # БЛУЗКИ
    create_test_image("media/products/blouse_silk_1.jpg", "Шелковая блузка", (245, 240, 235), "Luxury")
    create_test_image("media/products/blouse_silk_2.jpg", "Ткань", (235, 230, 225), "Luxury")

    create_test_image("media/products/blouse_lace_1.jpg", "Блузка с кружевом", (250, 230, 240), "Romance")

    print("\n👗 Создание изображений для юбок...")
    # ЮБКИ
    create_test_image("media/products/skirt_pencil_1.jpg", "Юбка-карандаш", (30, 30, 30), "Office")

    create_test_image("media/products/skirt_midi_1.jpg", "Юбка миди", (150, 120, 180), "Плиссе")
    create_test_image("media/products/skirt_midi_2.jpg", "Движение", (140, 110, 170), "Плиссе")

    print("\n👜 Создание изображений для аксессуаров...")
    # АКСЕССУАРЫ
    create_test_image("media/products/bag_leather_1.jpg", "Кожаная сумка", (80, 50, 30), "Classic")
    create_test_image("media/products/bag_leather_2.jpg", "Внутри", (70, 40, 20), "Classic")

    create_test_image("media/products/backpack_urban_1.jpg", "Рюкзак", (60, 60, 80), "Urban")

    print("\n" + "=" * 60)
    print("✅ ВСЕ ИЗОБРАЖЕНИЯ УСПЕШНО СОЗДАНЫ!")
    print("=" * 60)
    print("📊 Статистика:")
    print("   • Куртки: 11 изображений (4 товара)")
    print("   • Рубашки: 5 изображений (3 товара)")
    print("   • Брюки: 5 изображений (3 товара)")
    print("   • Платья: 7 изображений (3 товара)")
    print("   • Блузки: 3 изображения (2 товара)")
    print("   • Юбки: 3 изображения (2 товара)")
    print("   • Аксессуары: 3 изображения (2 товара)")
    print(f"\n📸 ВСЕГО: 37 изображений для 19 товаров")
    print("\n💡 Следующий шаг:")
    print("   1. python clear_database.py  (очистить БД)")
    print("   2. python add_test_data.py   (добавить данные)")
    print("   3. python bot/main.py        (запустить бота)")
    print("=" * 60)


if __name__ == "__main__":
    main()
