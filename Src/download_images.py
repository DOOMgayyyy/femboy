import asyncio
import os

import asyncpg
import httpx
from PIL import Image
from config import DB_CONFIG, IMAGES_DIR, CONCURRENCY_LIMIT




class ImageDownloader:
    """
    Скачивает изображения по ссылкам из БД, очищает их
    и обновляет пути в базе данных.
    """
    def __init__(self, session: httpx.AsyncClient, db_pool: asyncpg.Pool):
        self.session = session
        self.db_pool = db_pool

    async def find_images_to_download(self) -> list[asyncpg.Record]:
        """Находит в БД записи, где image_url является веб-ссылкой."""
        async with self.db_pool.acquire() as connection:
            # Выбираем товары, у которых URL начинается с http
            # и также их ID, чтобы знать, какую запись обновлять.
            records = await connection.fetch(
                "SELECT id, image_url FROM medicines WHERE image_url LIKE 'http%'"
            )
            return records

    async def process_image(self, medicine_id: int, image_url: str):
        """
        Полный цикл обработки одного изображения: скачать, очистить, обновить БД.
        """
        print(f"⏳ Пытаемся скачать: {image_url}")
        try:
            image_name = os.path.basename(image_url.split('?')[0])
            local_path = os.path.join(IMAGES_DIR, image_name)
            
            # Создаем директорию, если её нет
            os.makedirs(IMAGES_DIR, exist_ok=True)
            
            # Скачиваем
            response = await self.session.get(image_url, timeout=30)
            response.raise_for_status()

            # Очищаем метаданные через Pillow
            with Image.open(response.iter_bytes()) as img:
                img.save(local_path, format=img.format or 'JPEG', quality=85)
            
            # Самый важный шаг: обновляем запись в БД
            await self.update_db_path(medicine_id, local_path)
            
            print(f"✅ Изображение для товара ID {medicine_id} сохранено: {local_path}")

        except Exception as e:
            print(f"❌ Ошибка при обработке {image_url}: {e}")

    async def update_db_path(self, medicine_id: int, local_path: str):
        """Обновляет поле image_url в БД, заменяя веб-ссылку на локальный путь."""
        async with self.db_pool.acquire() as connection:
            await connection.execute(
                "UPDATE medicines SET image_url = $1 WHERE id = $2",
                local_path, medicine_id
            )

async def main():
    db_pool = await asyncpg.create_pool(**DB_CONFIG)
    downloader = None # Объявляем здесь для finally

    try:
        headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64)'}
        async with httpx.AsyncClient(headers=headers, follow_redirects=True) as session:
            downloader = ImageDownloader(session, db_pool)
            
            images_to_process = await downloader.find_images_to_download()
            if not images_to_process:
                print("🤷 Нет новых изображений для скачивания.")
                return

            print(f"🖼️  Найдено {len(images_to_process)} изображений для загрузки.")
            
            semaphore = asyncio.Semaphore(CONCURRENCY_LIMIT)
            
            async def worker(record):
                async with semaphore:
                    await downloader.process_image(record['id'], record['image_url'])

            tasks = [asyncio.create_task(worker(record)) for record in images_to_process]
            await asyncio.gather(*tasks)

    finally:
        if db_pool:
            await db_pool.close()
        print("\n🎉 Работа загрузчика изображений завершена.")

if __name__ == "__main__":
    asyncio.run(main())