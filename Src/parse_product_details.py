import asyncio
import os
import re
from urllib.parse import urljoin

import asyncpg
import httpx
from bs4 import BeautifulSoup, Tag

# --- НАСТРОЙКИ ---
# Директория, где лежат .txt файлы с URL товаров
URLS_DIR = 'category_products'
# Директория для сохранения очищенных изображений
IMAGES_DIR = 'static/images/products'
# Параметры для подключения к БД (из docker-compose.yml)
DB_CONFIG = {
    'user': 'user_farm',
    'password': 'password_farm',
    'database': 'db_farm',
    'host': 'localhost'
}
# Ограничение на количество одновременных задач по парсингу
CONCURRENCY_LIMIT = 10


class ProductProcessor:
    """
    Класс для обработки одной карточки товара: парсинг, скачивание изображения
    и сохранение данных в БД.
    """
    def __init__(self, session: httpx.AsyncClient, db_pool: asyncpg.Pool):
        self.base_url = 'https://gosapteka18.ru'
        self.session = session
        self.db_pool = db_pool

    async def fetch_html(self, url: str) -> str | None:
        """Асинхронно загружает HTML-код страницы."""
        try:
            # Умеренная задержка перед каждым запросом
            await asyncio.sleep(0.5)
            response = await self.session.get(url, timeout=20)
            response.raise_for_status()
            return response.text
        except httpx.RequestError as e:
            print(f"🚫 Ошибка загрузки {url}: {e}")
            return None

    async def process_product(self, product_url: str):
        """Полный цикл обработки товара БЕЗ скачивания изображения."""
        print(f"⏳ Собираем данные для: {product_url}")
        html = await self.fetch_html(product_url)
        if not html:
            return

        soup = BeautifulSoup(html, 'html.parser')
        
        title = self._get_title(soup)
        if not title:
            print(f"⚠️  Не удалось найти заголовок для {product_url}, пропуск.")
            return

        description_dict = self._get_description(soup)
        description_text = "\n\n".join([f"{k}:\n{v}" for k, v in description_dict.items()])
        
        # Просто получаем URL изображения, но не скачиваем его
        original_image_url = self._get_image(soup)

        # Логика определения типа остается
        medicine_type_name = "Общая категория"

        # Сохраняем все в базу данных, передавая оригинальный URL
        await self.save_to_db({
            'name': title,
            'description': description_text,
            'image_url': original_image_url, # <-- ВАЖНО: здесь теперь оригинальный URL
            'type_name': medicine_type_name
        })
        
    async def save_to_db(self, data: dict):
        """
        Сохраняет данные о товаре в базу данных.
        Поле image_url теперь содержит ссылку на источник.
        """
        # ... (код этого метода остается БЕЗ ИЗМЕНЕНИЙ, т.к. он просто пишет то, что ему передали)
        # Он просто запишет https://... ссылку в поле image_url.
        async with self.db_pool.acquire() as connection:
            async with connection.transaction():
                type_id = await connection.fetchval(
                    """
                    INSERT INTO medicine_types (name) VALUES ($1)
                    ON CONFLICT (name) DO NOTHING;
                    
                    SELECT id FROM medicine_types WHERE name = $1;
                    """,
                    data['type_name']
                )

                await connection.execute(
                    """
                    INSERT INTO medicines (name, description, image_url, type_id)
                    VALUES ($1, $2, $3, $4)
                    ON CONFLICT (name) DO UPDATE SET
                        description = EXCLUDED.description,
                        image_url = EXCLUDED.image_url,
                        type_id = EXCLUDED.type_id;
                    """,
                    data['name'], data['description'], data['image_url'], type_id
                )
        print(f"💾 Данные (с URL картинки) для товара '{data['name']}' сохранены в БД.")

    # Вспомогательные методы парсинга (взяты из вашего test.py и адаптированы)
    def _get_title(self, soup: BeautifulSoup) -> str:
        title_tag = soup.select_one('h1.title.headline-main__title.product-card__title')
        return title_tag.get_text(strip=True) if title_tag else ''

    def _get_image(self, soup: BeautifulSoup) -> str:
        image_tag = soup.select_one('img.product-card__picture-view-img')
        if image_tag and 'src' in image_tag.attrs:
            return urljoin(self.base_url, image_tag['src'])
        return ''

    def _get_description(self, soup: BeautifulSoup) -> dict:
        description_block = soup.select_one('div.product-card__description')
        if not description_block: return {}
        
        sections = {}
        for header in description_block.find_all('h4'):
            header_text = header.get_text(strip=True)
            content = []
            for sibling in header.find_next_siblings():
                if sibling.name == 'h4':
                    break
                if isinstance(sibling, Tag):
                    content.append(sibling.get_text(" ", strip=True))
            sections[header_text] = " ".join(content)
        return sections

async def main():
    """Главная функция: читает URL и запускает обработчики."""
    # Собираем все уникальные URL из всех .txt файлов
    all_urls = set()
    if not os.path.exists(URLS_DIR):
        print(f"❌ Директория '{URLS_DIR}' не найдена. Сначала запустите первый парсер.")
        return

    for filename in os.listdir(URLS_DIR):
        if filename.endswith('.txt'):
            with open(os.path.join(URLS_DIR, filename), 'r', encoding='utf-8') as f:
                all_urls.update(line.strip() for line in f)
    
    if not all_urls:
        print("🤷 Не найдено URL для обработки.")
        return

    print(f"✅ Найдено {len(all_urls)} уникальных URL для обработки.")

    # Создаем пул соединений с БД
    db_pool = await asyncpg.create_pool(**DB_CONFIG)
    
    # Создаем семафор для ограничения одновременных запросов
    semaphore = asyncio.Semaphore(CONCURRENCY_LIMIT)
    
    async def worker(url, processor):
        async with semaphore:
            await processor.process_product(url)

    headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'}
    async with httpx.AsyncClient(headers=headers, follow_redirects=True) as session:
        processor = ProductProcessor(session, db_pool)
        tasks = [asyncio.create_task(worker(url, processor)) for url in all_urls]
        await asyncio.gather(*tasks)

    await db_pool.close()
    print("\n\n🎉 Все товары обработаны и сохранены в базу данных!")

if __name__ == "__main__":
    asyncio.run(main())