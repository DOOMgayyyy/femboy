# 3_parse_product_details.py
import requests
import json
from bs4 import BeautifulSoup
import time
import os

# Корректный импорт базового класса из первого файла
from step1_parse_categories import GosAptekaParser

class ProductScraper(GosAptekaParser):
    """
    Класс для сбора детальной информации о конкретном товаре.
    Наследует методы GosAptekaParser.
    """
    def parse_product_details(self, product_url):
        """Собирает детальную информацию со страницы товара."""
        html = self.fetch_html(product_url)
        if not html: 
            return None

        soup = BeautifulSoup(html, 'html.parser')
        details = {'url': product_url, 'name': 'N/A', 'price': 'N/A', 'manufacturer': 'N/A', 'description': 'N/A'}
        
        try:
            # Название товара
            name_tag = soup.select_one('h1.product-title')
            if name_tag:
                details['name'] = name_tag.text.strip()
            
            # Цена
            price_tag = soup.select_one('div.product-price__value')
            if price_tag:
                price_text = ''.join(c for c in price_tag.text if c.isdigit() or c in '.,')
                details['price'] = float(price_text.replace(',', '.'))
            
            # Производитель
            # Ищем блок "О товаре" и в нем ссылку на бренд
            about_section = soup.select_one('div.product-about')
            if about_section:
                manufacturer_tag = about_section.find('a', class_='product-about__brand-link')
                if manufacturer_tag:
                    details['manufacturer'] = manufacturer_tag.text.strip()

            # Описание
            desc_div = soup.select_one('div.product-description__text')
            if desc_div:
                details['description'] = desc_div.text.strip()

        except Exception as e:
            print(f"❗️ Не удалось полностью разобрать {product_url}. Ошибка: {e}")
            # Возвращаем то, что успели собрать
            return details
        
        return details

def main():
    scraper = ProductScraper()
    print("\n▶️ Шаг 3: Сбор детальной информации о товарах...")

    urls_file = 'product_urls.json'
    if not os.path.exists(urls_file):
        print(f"🚫 Файл {urls_file} не найден. Сначала запустите '2_parse_product_urls.py'")
        return

    with open(urls_file, 'r', encoding='utf-8') as f:
        product_urls = json.load(f)
    
    total_urls = len(product_urls)
    if total_urls == 0:
        print("ℹ️ Файл 'product_urls.json' пуст. Нет данных для сбора.")
        return
        
    print(f"⏳ Начинается сбор данных для {total_urls} товаров...")
    
    all_products_data = []
    for i, url in enumerate(product_urls, 1):
        print(f"  📦 Товар {i}/{total_urls}: {url}")
        data = scraper.parse_product_details(url)
        if data:
            all_products_data.append(data)
        time.sleep(0.5) # Пауза между запросами

    print(f"\n✅ Собрана информация о {len(all_products_data)} товарах.")

    with open('products_data.json', 'w', encoding='utf-8') as f:
        json.dump(all_products_data, f, ensure_ascii=False, indent=4)

    print("💾 Итоговый результат сохранен в 'products_data.json'")

if __name__ == "__main__":
    main()