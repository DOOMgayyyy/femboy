# config.py





import os
from dotenv import load_dotenv

# Загружаем переменные из .env файла
load_dotenv()

# Настройки базы данных (читаются из .env)
DB_CONFIG = {
    'user': os.getenv('POSTGRES_USER'),
    'password': os.getenv('POSTGRES_PASSWORD'),
    'database': os.getenv('POSTGRES_DB'),
    'host': 'localhost' # Обычно localhost при работе с Docker
}

# Настройки директорий
IMAGES_DIR = 'static/images/products'
URLS_DIR = 'category_products'

# Настройки производительности
CONCURRENCY_LIMIT = 10


DELAY_BETWEEN_PAGES = (1.0, 2.5)
DELAY_BETWEEN_CATEGORIES = (2.0, 4.0)

# Настройки HTTP-клиента
HTTP_HEADERS = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
    'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
    'Accept-Language': 'ru-RU,ru;q=0.8,en-US;q=0.5,en;q=0.3',
}

# Настройки изображений
IMAGE_QUALITY = 85
IMAGE_FORMATS = ['JPEG', 'PNG', 'WEBP']