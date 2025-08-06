import requests
import json
from bs4 import BeautifulSoup
import time
from pathlib import Path
import logging
import re
from urllib.parse import urljoin

# Корректный импорт базового класса из первого файла
# Убедитесь, что файл '1_parse_categories.py' находится в той же папке.
try:
    from step1_parse_categories import GosAptekaParser
except ImportError:
    print("Ошибка: не удалось импортировать 'GosAptekaParser'. Убедитесь, что файл '1_parse_categories.py' существует.")
    exit()


# Настройка логирования для вывода в консоль и в файл
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('url_parser.log', encoding='utf-8', mode='w'), # 'w' для перезаписи лога при каждом запуске
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)


class UrlCollector(GosAptekaParser):
    """
    Класс для сбора URL-адресов товаров со страниц категорий первого уровня.
    """
    def __init__(self):
        super().__init__()
        self.processed_urls = set()  # Кэш обработанных URL товаров, чтобы избежать дублей
        self.failed_urls = set()     # URL категорий, которые не удалось обработать
        
        # Заголовки для имитации браузера
        self.session.headers.update({
            'Accept-Language': 'ru-RU,ru;q=0.9,en-US;q=0.8,en;q=0.7',
            'Accept-Encoding': 'gzip, deflate, br',
            'Connection': 'keep-alive'
        })

    def get_first_level_subcategory_urls(self, categories_data: dict) -> list:
        """
        Собирает URL-адреса ТОЛЬКО первого уровня подкатегорий из структуры.
        Если у родительской категории нет подкатегорий, используется её URL.
        """
        urls = set()
        logger.info("▶️ Шаг 2.1: Сбор URL подкатегорий первого уровня...")
        
        for parent_name, parent_data in categories_data.items():
            subcategories_l1 = parent_data.get('subcategories', [])
            
            if not subcategories_l1:
                # Если подкатегорий нет, берем URL родительской
                if parent_data.get('url'):
                    logger.info(f"  - Категория '{parent_name}' без подкатегорий, используется ее основная ссылка.")
                    urls.add(parent_data['url'])
            else:
                # Иначе берем все URL из первого уровня вложенности
                for sub_cat in subcategories_l1:
                    if sub_cat.get('url'):
                        urls.add(sub_cat['url'])

        unique_urls = sorted(list(urls))
        logger.info(f"✅ Найдено {len(unique_urls)} уникальных URL для парсинга.")
        return unique_urls

    def extract_products_from_page(self, soup: BeautifulSoup, page_url: str) -> list:
        """Извлекает URL товаров с одной страницы с помощью нескольких селекторов."""
        product_urls = []
        
        # Список селекторов для поиска ссылок на товары
        product_selectors = [
            'div.product-mini-card__container a.product-mini-card__name',
            'a.product-card__title'
        ]
        
        found_links = []
        for selector in product_selectors:
            found_links = soup.select(selector)
            if found_links:
                break # Используем первый сработавший селектор
        
        if not found_links:
            logger.warning("  ⚠️ Не найдено ссылок на товары на странице. Проверьте селекторы.")
            return []

        for link in found_links:
            href = link.get('href')
            if href:
                # Превращаем относительную ссылку в абсолютную
                full_url = urljoin(self.base_url, href)
                if full_url not in self.processed_urls:
                    product_urls.append(full_url)
                    self.processed_urls.add(full_url)
                    
        return product_urls

    def find_next_page(self, soup: BeautifulSoup, current_url: str) -> str or None:
        """Находит ссылку на следующую страницу пагинации."""
        # Ищем элемент 'a' с классом 'pagination__item' и '_next', но без класса '_disabled'
        next_page_tag = soup.select_one('a.pagination__item._next:not(._disabled)')
        
        if next_page_tag and next_page_tag.get('href'):
            next_page_url = urljoin(current_url, next_page_tag['href'])
            return next_page_url
        return None

    def parse_product_urls_from_category(self, category_url: str, max_pages: int = 50) -> list:
        """Собирает все URL товаров из одной категории, включая пагинацию."""
        all_products_in_category = []
        current_url = category_url
        page_count = 0
        
        logger.info(f"  - Обработка категории: {category_url}")
        
        while current_url and page_count < max_pages:
            page_count += 1
            logger.info(f"    - Сканирую страницу {page_count}: {current_url}")
            
            html = self.fetch_html(current_url)
            if not html:
                logger.error(f"    ❌ Не удалось загрузить страницу. Пропуск категории.")
                self.failed_urls.add(category_url)
                break
            
            soup = BeautifulSoup(html, 'html.parser')
            
            page_products = self.extract_products_from_page(soup, current_url)
            if page_products:
                all_products_in_category.extend(page_products)
                logger.info(f"    ✅ Найдено {len(page_products)} ссылок.")
            
            next_url = self.find_next_page(soup, current_url)
            if next_url:
                current_url = next_url
                time.sleep(1)  # Пауза между запросами страниц
            else:
                logger.info("    🏁 Достигнут конец пагинации.")
                break
        
        logger.info(f"  - Итог по категории: найдено {len(all_products_in_category)} ссылок на товары.")
        return all_products_in_category


def main():
    """Основная функция для запуска парсера."""
    collector = UrlCollector()
    logger.info("▶️ Шаг 2: Запуск сбора ссылок на товары...")
    
    # --- 1. Загрузка файла с категориями ---
    categories_file = Path('categories.json')
    if not categories_file.exists():
        logger.error(f"🚫 Файл {categories_file} не найден. Сначала запустите '1_parse_categories.py'.")
        return

    try:
        with open(categories_file, 'r', encoding='utf-8') as f:
            all_categories = json.load(f)
    except json.JSONDecodeError:
        logger.error(f"🚫 Ошибка чтения файла {categories_file}. Он может быть поврежден или пуст.")
        return

    if not all_categories or 'error' in all_categories:
        logger.error("🚫 Файл категорий пуст или содержит ошибку. Парсинг невозможен.")
        return

    # --- 2. Получение списка URL для парсинга ---
    category_urls_to_parse = collector.get_first_level_subcategory_urls(all_categories)
    
    if not category_urls_to_parse:
        logger.error("❌ Не найдено URL подкатегорий для обработки.")
        return

    # --- 3. Основной цикл парсинга ---
    all_product_urls = set()
    total_categories = len(category_urls_to_parse)

    start_time = time.time()
    
    for i, cat_url in enumerate(category_urls_to_parse, 1):
        logger.info(f"\n--- Прогресс: {i}/{total_categories} ---")
        try:
            product_links = collector.parse_product_urls_from_category(cat_url)
            if product_links:
                all_product_urls.update(product_links)
            
            # Пауза между обработкой крупных категорий
            time.sleep(1.5) 
            
        except KeyboardInterrupt:
            logger.warning("\n🛑 Процесс прерван пользователем.")
            break
        except Exception as e:
            logger.error(f"❌ КРИТИЧЕСКАЯ ОШИБКА при обработке {cat_url}: {e}")
            collector.failed_urls.add(cat_url)
            continue
    
    end_time = time.time()
    logger.info(f"\n--- ⏰ Парсинг завершен за {end_time - start_time:.2f} секунд ---")

    # --- 4. Сохранение результатов ---
    if not all_product_urls:
        logger.error("🚫 Не удалось собрать ни одной ссылки на товары.")
        return

    output_file = Path('product_urls_l1.json')
    sorted_urls = sorted(list(all_product_urls))
    
    try:
        with open(output_file, 'w', encoding='utf-8') as f:
            json.dump(sorted_urls, f, ensure_ascii=False, indent=4)
            
        logger.info(f"✅ УСПЕХ! Собрано {len(sorted_urls)} уникальных ссылок на товары.")
        logger.info(f"💾 Результат сохранен в файл: '{output_file}'")

        if collector.failed_urls:
            failed_file = Path('failed_categories.log')
            logger.warning(f"⚠️ {len(collector.failed_urls)} категорий не удалось обработать.")
            with open(failed_file, 'w', encoding='utf-8') as f:
                f.write("\n".join(sorted(list(collector.failed_urls))))
            logger.warning(f"🗂️ Список проблемных URL сохранен в '{failed_file}'")

    except Exception as e:
        logger.error(f"❌ Ошибка сохранения результатов в файл: {e}")


if __name__ == "__main__":
    main()