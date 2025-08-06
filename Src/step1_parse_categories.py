# 1_parse_categories.py
import requests
import json
from bs4 import BeautifulSoup
import time

class GosAptekaParser:
    """
    Базовый класс парсера для сайта gosapteka18.ru.
    Отвечает за отправку HTTP-запросов и хранение сессии.
    """
    def __init__(self):
        self.base_url = 'https://gosapteka18.ru'
        self.headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/125.0.0.0 Safari/537.36',
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,image/apng,*/*;q=0.8'
        }
        self.session = requests.Session()
        self.session.headers.update(self.headers)

    def fetch_html(self, url):
        """Отправляет GET-запрос и возвращает HTML-содержимое страницы."""
        try:
            response = self.session.get(url, timeout=20)
            response.raise_for_status()
            return response.text
        except requests.exceptions.RequestException as e:
            print(f"🚫 Ошибка загрузки {url}: {str(e)}")
            return None

class CategoryParser(GosAptekaParser):
    """Класс для сбора структуры категорий с сайта."""
    def parse_catalog(self):
        """
        Собирает все категории и подкатегории с главной страницы.
        Возвращает словарь со структурой каталога.
        """
        print("▶️ Шаг 1: Парсинг структуры категорий...")
        main_page_url = self.base_url + '/'
        html = self.fetch_html(main_page_url)
        if not html:
            return {'error': 'Не удалось загрузить главную страницу'}

        try:
            soup = BeautifulSoup(html, 'html.parser')
            catalog_container = soup.find('div', class_='menu-catalog')
            if not catalog_container:
                return {'error': "Контейнер каталога 'menu-catalog' не найден"}

            structured_categories = {}
            columns = catalog_container.find_all('div', class_='menu-catalog__list')
            if not columns:
                return {'error': "Колонки категорий 'menu-catalog__list' не найдены"}

            for col in columns:
                items = col.find_all('div', class_='menu-catalog__item', recursive=False)
                for item in items:
                    parent_link = item.find('a', class_='menu-catalog__link')
                    if not parent_link or not parent_link.text.strip():
                        continue

                    parent_name = parent_link.text.strip()
                    parent_url = self.base_url + parent_link.get('href', '')
                    subcategories_l1 = []
                    submenu_l1 = item.find('div', class_='menu-catalog__sub-menu')
                    
                    if submenu_l1:
                        subitems_l1 = submenu_l1.find_all('div', class_='menu-catalog__sub-item')
                        for subitem in subitems_l1:
                            sub_link = subitem.find('a', class_='menu-catalog__sub-link')
                            if not sub_link: continue
                            
                            sub_name = sub_link.text.strip()
                            sub_url = self.base_url + sub_link.get('href', '')
                            subcategories_l2 = []
                            submenu_l2 = subitem.find('div', class_='menu-catalog__sub2-menu')
                            
                            if submenu_l2:
                                for sub2_link in submenu_l2.find_all('a', class_='menu-catalog__sub2-link'):
                                    subcategories_l2.append({
                                        'name': sub2_link.text.strip(),
                                        'url': self.base_url + sub2_link.get('href', '')
                                    })
                            
                            subcategories_l1.append({
                                'name': sub_name, 'url': sub_url, 'subcategories': subcategories_l2
                            })
                    
                    structured_categories[parent_name] = {'url': parent_url, 'subcategories': subcategories_l1}
            
            print("✅ Структура категорий успешно собрана.")
            return structured_categories
        except Exception as e:
            print(f"❌ Произошла непредвиденная ошибка при парсинге категорий: {e}")
            return {"error": str(e)}

def main():
    parser = CategoryParser()
    catalog_data = parser.parse_catalog()

    if 'error' in catalog_data or not catalog_data:
        print(f"🚫 Ошибка: {catalog_data.get('error', 'Не удалось собрать данные.')}")
        return

    with open('categories.json', 'w', encoding='utf-8') as f:
        json.dump(catalog_data, f, ensure_ascii=False, indent=4)
    
    print("💾 Результат сохранен в 'categories.json'")

if __name__ == "__main__":
    main()