import asyncio
import csv
import logging
from playwright.async_api import async_playwright
from fake_useragent import UserAgent

# Настройка профессионального логирования
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - [%(filename)s:%(lineno)d] - %(message)s')
logger = logging.getLogger(__name__)

# --- НАСТРОЙКИ (Middle-уровень: выносится в конфиг или аргументы CLI) ---
PROXY_SERVER = "http://your-proxy-domain.com:8000"  # Замените на ваш прокси
PROXY_USER = "username"
PROXY_PASS = "password"
OUTPUT_FILE = "products_data.csv"

# Тестовая цель: парсинг динамического каталога (в реальности тут будет сайт клиента)
TARGET_URLS = [
    f"https://toscrape.com{i}/" for i in range(1, 4)
]

async def parse_page(browser, url: str) -> list:
    """Парсинг одной страницы в изолированном контексте (сессии)"""
    ua = UserAgent()
    
    # Создаем уникальный контекст для каждой вкладки (имитация разных пользователей)
    context = await browser.new_context(
        user_agent=ua.random,
        viewport={"width": 1920, "height": 1080},
        # Опционально подключаем прокси, если они заданы
        # proxy={"server": PROXY_SERVER, "username": PROXY_USER, "password": PROXY_PASS} if PROXY_SERVER else None
    )
    
    # Маскировка под реальный браузер (Middle-стандарт)
    await context.add_init_script("Object.defineProperty(navigator, 'webdriver', {get: () => undefined})")
    
    page = await context.new_page()
    page_data = []
    
    try:
        logger.info(f"Открытие страницы: {url}")
        # Ждем полной загрузки сети (networkidle), чтобы отработали все JS-скрипты/React
        await page.goto(url, wait_until="networkidle", timeout=30000)
        
        # Поиск элементов (в данном примере - блоки с цитатами на тестовом сайте)
        elements = await page.query_selector_all(".quote")
        
        for el in elements:
            text_el = await el.query_selector(".text")
            author_el = await el.query_selector(".author")
            
            text = await text_el.inner_text() if text_el else ""
            author = await author_el.inner_text() if author_el else ""
            
            # Очистка данных от лишних пробелов и символов
            page_data.append({
                "Quote": text.strip().replace("“", "").replace("”", ""),
                "Author": author.strip()
            })
            
        logger.info(f"Успешно спарсено {len(page_data)} элементов с {url}")
        
    except Exception as e:
        logger.error(f"Ошибка при парсинге страницы {url}: {str(e)}")
    finally:
        await context.close()  # Обязательно закрываем сессию во избежание утечек памяти
        
    return page_data

async def main():
    logger.info("Инициализация Playwright...")
    
    async with async_playwright() as p:
        # Запуск headless-браузера (на сервере клиента будет работать без интерфейса)
        browser = await p.chromium.launch(headless=True)
        
        # Создаем пул задач для одновременного (асинхронного) выполнения
        tasks = [parse_page(browser, url) return_exceptions=True for url in TARGET_URLS]
        
        logger.info(f"Запуск параллельного парсинга {len(TARGET_URLS)} страниц...")
        results = await asyncio.gather(*tasks)
        
        await browser.close()
        
    # Собираем все результаты в один плоский список
    all_data = []
    for res in results:
        if isinstance(res, list):
            all_data.extend(res)
            
    # Запись результатов в CSV (Middle-стиль: безопасное открытие файла, кодировка UTF-8)
    if all_data:
        keys = all_data[0].keys()
        with open(OUTPUT_FILE, 'w', newline='', encoding='utf-8-sig') as output_file:
            dict_writer = csv.DictWriter(output_file, fieldnames=keys)
            dict_writer.writeheader()
            dict_writer.writerows(all_data)
        logger.info(f"🎉 Процесс завершен! Данные ({len(all_data)} строк) сохранены в {OUTPUT_FILE}")
    else:
        logger.warning("Парсинг завершен, но данные не были найдены.")

if __name__ == "__main__":
    # Запуск асинхронного цикла событий
    asyncio.run(main())
