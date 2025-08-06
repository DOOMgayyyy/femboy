import requests
from bs4 import BeautifulSoup
from urllib.parse import urljoin

class SimpleProductParser:
    """
    Простой парсер для сбора ссылок на товары с одной страницы категории.
    """
    def __init__(self):
        # Базовый URL сайта для создания полных ссылsок 
        self.base_url = 'https://gosapteka18.ru'
        
        # Заголовки, чтобы сайт думал, что мы браузер
        self.headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/125.0.0.0 Safari/537.36',
        }
        
        # Используем сессию для отправки запросов
        self.session = requests.Session()
        self.session.headers.update(self.headers)

    def fetch_html(self, url: str) -> str | None:
        """Загружает HTML-код страницы."""
        try:
            response = self.session.get(url, timeout=15)
            # Проверяем, что запрос прошел успешно (код 200)
            response.raise_for_status() 
            return response.text
        except requests.exceptions.RequestException as e:
            print(f"🚫 Ошибка при загрузке страницы {url}: {e}")
            return None

    def parse_and_print_products(self, page_url: str):
        """Основной метод: парсит и выводит ссылки на товары."""
        print(f"▶️ Начинаю парсинг страницы: {page_url}")
        
        html = self.fetch_html(page_url)
        if not html:
            print("Не удалось получить HTML. Завершаю работу.")
            return

        soup = BeautifulSoup(html, 'html.parser')

        # Ищем все ссылки, которые соответствуют селектору карточки товара
        # Это основной селектор для данного сайта
        product_links = soup.select('a.product-card__title')
        
        if not product_links:
            print("⚠️ На странице не найдено товаров по заданному селектору.")
            return

        print(f"✅ Найдено товаров: {len(product_links)}. Вывожу ссылки:")
        
        # Перебираем найденные теги <a>
        for link in product_links:
            # Получаем значение атрибута href (саму ссылку)
            href = link.get('href')
            if href:
                # Преобразуем относительную ссылку (например, /product/123)
                # в абсолютную (https://gosapteka18.ru/product/123)
                full_url = urljoin(self.base_url, href)
                print(full_url)


# --- ОСНОВНАЯ ЧАСТЬ ---
if __name__ == "__main__":
    
    target_url = "https://gosapteka18.ru/catalog/lekarstvennye-preparaty-i-bady/bolezni-sustavov/"

    # Создаем экземпляр нашего парсера
    parser = SimpleProductParser()
    
    # Запускаем парсинг для указанной ссылки
    parser.parse_and_print_products(target_url)