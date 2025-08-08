import requests
from bs4 import BeautifulSoup, Tag
from urllib.parse import urljoin
import os
import json
import time
import re

class ProductParser:
    def __init__(self):
        self.base_url = 'https://gosapteka18.ru'
        self.headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/125.0.0.0 Safari/537.36',
            'X-Requested-With': 'XMLHttpRequest'
        }
        self.session = requests.Session()
        self.session.headers.update(self.headers)
        self.price_regexes = [
            re.compile(r'product-card__price-value[^>]*>([\d\s,]+)'),
            re.compile(r'"price"\s*:\s*"(\d+\.?\d*)"'),
            re.compile(r'itemprop="price"[^>]+content="(\d+\.?\d*)"')
        ]

    def fetch_html(self, url: str) -> str | None:
        try:
            time.sleep(1)
            response = self.session.get(url, timeout=15)
            response.raise_for_status()
            return response.text
        except requests.exceptions.RequestException as e:
            print(f"🚫 Ошибка при загрузке {url}: {e}")
            return None

    def parse_product(self, product_url: str):
        print(f"⏳ Начинаем парсинг товара: {product_url}")
        html = self.fetch_html(product_url)
        if not html:
            return None
            
        soup = BeautifulSoup(html, 'html.parser')
        
        # Получаем ID товара для запроса цены
        product_id = self._get_product_id(soup)
        
        product_data = {
            'url': product_url,
            'title': self._get_title(soup),
            'price': self._get_price(html),
            'manufacturer': self._get_manufacturer(soup),
            'description': self._get_description(soup),
            'image_url': self._get_image(soup)
        }
        
        self.save_results(product_data)
        return product_data
    
    def _get_product_id(self, soup) -> str:
        """Извлекает ID товара из HTML"""
        product_id_tag = soup.select_one('div.product-card[data-product-id]')
        return product_id_tag['data-product-id'] if product_id_tag else None
    
    def _get_price(self, html):
        for regex in self.price_regexes:
            if match := regex.search(html):
                try:
                    price_str = match.group(1).replace(' ', '').replace(',', '.')
                    return float(price_str)
                except (ValueError, TypeError):
                    continue
        return None

    def _clean_price(self, price_text: str) -> str:
        """Очищает цену от лишних символов"""
        if price_text is None:
            return "0.00"
        
        # Удаляем все нецифровые символы кроме точки и запятой
        cleaned = re.sub(r'[^\d,.]', '', price_text)
        cleaned = cleaned.replace(',', '.').strip()
        
        if cleaned:
            try:
                # Форматируем цену с двумя знаками после запятой
                return f"{float(cleaned):.2f}"
            except ValueError:
                return "0.00"
        return "0.00"

    def _get_title(self, soup) -> str:
        title_tag = soup.select_one('h1.title.headline-main__title.product-card__title')
        return title_tag.get_text(strip=True) if title_tag else ''

    def _get_description(self, soup) -> dict:
        """Возвращает структурированное описание в виде словаря {заголовок: текст}"""
        description_block = soup.select_one('div.product-card__description')
        if not description_block:
            return {}
        
        # Собираем все заголовки и связанные с ними данные
        sections = {}
        current_header = None
        
        # Обрабатываем все дочерние элементы блока описания
        for child in description_block.children:
            if isinstance(child, Tag):
                # Нашли новый заголовок
                if child.name == 'h4':
                    current_header = child.get_text(strip=True)
                    sections[current_header] = []
                # Обрабатываем содержимое под заголовком
                elif current_header:
                    # Для тегов <p> извлекаем весь текст
                    if child.name == 'p':
                        text = child.get_text(strip=True)
                        if text:
                            sections[current_header].append(text)
                    # Обрабатываем другие теги (div, span и т.д.)
                    else:
                        text = child.get_text(" ", strip=True)
                        if text:
                            sections[current_header].append(text)
        
        # Объединяем списки в строки
        for header in sections:
            sections[header] = "\n".join(sections[header])
        
        return sections

    def _get_manufacturer(self, soup) -> str:
        manufacturer_tag = soup.select_one('span.product-card__brand-value')
        return manufacturer_tag.get_text(strip=True) if manufacturer_tag else ''

    def _get_image(self, soup) -> str:
        image_tag = soup.select_one('img.product-card__picture-view-img')
        if image_tag and 'src' in image_tag.attrs:
            return urljoin(self.base_url, image_tag['src'])
        return ''

    def save_results(self, product_data: dict):
        title = product_data.get('title', 'unknown_product')
        slug = re.sub(r'[^\w]+', '_', title)[:100].strip('_')
        filename = f"{slug}.json"
        
        os.makedirs('product_data', exist_ok=True)
        filepath = os.path.join('product_data', filename)
        
        with open(filepath, 'w', encoding='utf-8') as f:
            json.dump(product_data, f, ensure_ascii=False, indent=2)
        
        print(f"💾 Данные сохранены в: {filepath}")
        return filepath


if __name__ == "__main__":
    product_url = "https://gosapteka18.ru/catalog/velledien_2_5mg_tab_28.html"
    
    parser = ProductParser()
    product_data = parser.parse_product(product_url)
    
    if product_data:
        print("\n✅ Успешно распарсены данные:")
        print(f"Ссылка: {product_url}")
    else:
        print("❌ Не удалось распарсить товар")