import asyncio
import csv
import logging
import sqlite3
from playwright.async_api import async_playwright
from fake_useragent import UserAgent

# Настройка вывода логов в консоль
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# --- НАСТРОЙКИ ---
DB_NAME = "scraped_data.db"      # Имя файла базы данных SQLite
TXT_FILE = "extracted_quotes.txt" # Имя текстового файла для отчета
CSV_FILE = "products_data.csv"    # Имя CSV файла
TARGET_URLS = [f"https://quotes.toscrape.com/page/{i}/" for i in range(1, 4)]

def init_db():
    """Создание базы данных и таблицы (если они еще не созданы)"""
    with sqlite3.connect(DB_NAME) as conn:
        cursor = conn.cursor()
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS quotes (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                author TEXT,
                text TEXT,
                UNIQUE(author, text) ON CONFLICT IGNORE
            )
        ''')
        conn.commit()
    logger.info("База данных успешно инициализирована.")

def save_to_db_and_txt(data: list):
    """Сохранение полученных данных в SQLite и текстовый файл"""
    if not data:
        return

    # 1. Запись в базу данных SQLite (защита от дубликатов через IGNORE)
    with sqlite3.connect(DB_NAME) as conn:
        cursor = conn.cursor()
        for item in data:
            cursor.execute(
                "INSERT OR IGNORE INTO quotes (author, text) VALUES (?, ?)",
                (item["Author"], item["Quote"])
            )
        conn.commit()
    logger.info(f"Данные ({len(data)} шт.) сохранены в базу данных {DB_NAME}.")

    # 2. Запись в текстовый файл TXT
    with open(TXT_FILE, 'w', encoding='utf-8') as txt:
        txt.write("=== СПИСОК СОБРАННЫХ ДАННЫХ ===\n\n")
        for index, item in enumerate(data, 1):
            txt.write(f"Запись №{index}\n")
            txt.write(f"Автор: {item['Author']}\n")
            txt.write(f"Цитата: {item['Quote']}\n")
            txt.write("-" * 40 + "\n")
    logger.info(f"Текстовый отчет записан в файл {TXT_FILE}.")

async def parse_page(browser, url: str) -> list:
    """Открытие одной страницы в изолированной сессии и сбор элементов"""
    ua = UserAgent()
    
    # Создаем изолированный контекст браузера для каждой вкладки
    context = await browser.new_context(
        user_agent=ua.random,
        viewport={"width": 1920, "height": 1080}
    )
    
    # Скрытие автоматизации (маскировка под реального пользователя)
    await context.add_init_script("Object.defineProperty(navigator, 'webdriver', {get: () => undefined})")
    
    page = await context.new_page()
    page_data = []
    
    try:
        logger.info(f"Открываем страницу: {url}")
        # Ожидаем полной загрузки сети (JS, AJAX, React)
        await page.goto(url, wait_until="networkidle", timeout=30000)
        
        # Поиск всех карточек на странице
        elements = await page.query_selector_all(".quote")
        
        for el in elements:
            text_el = await el.query_selector(".text")
            author_el = await el.query_selector(".author")
            
            text = await text_el.inner_text() if text_el else ""
            author = await author_el.inner_text() if author_el else ""
            
            page_data.append({
                "Quote": text.strip().replace("“", "").replace("”", ""),
                "Author": author.strip()
            })
            
    except Exception as e:
        logger.error(f"Ошибка при обработке страницы {url}: {str(e)}")
    finally:
        await context.close() # Закрываем сессию во избежание утечки памяти
        
    return page_data

async def main():
    # Создаем или проверяем БД перед началом работы
    init_db()
    
    logger.info("Запуск движка Playwright...")
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        
        # Формируем пул задач для параллельного выполнения
        tasks = [parse_page(browser, url) for url in TARGET_URLS]
        
        logger.info("Запуск асинхронного парсинга страниц...")
        # Передаем список задач и параметр обработки исключений
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        await browser.close()
        
    # Объединяем списки данных со всех вкладок в один
    all_data = []
    for res in results:
        if isinstance(res, list):
            all_data.extend(res)
            
    if all_data:
        # Сохранение в БД и TXT
        save_to_db_and_txt(all_data)
        
        # Корректное извлечение заголовков для CSV из первого словаря в списке
        keys = all_data[0].keys()
        with open(CSV_FILE, 'w', newline='', encoding='utf-8-sig') as output_file:
            dict_writer = csv.DictWriter(output_file, fieldnames=keys)
            dict_writer.writeheader()
            dict_writer.writerows(all_data)
        logger.info("🎉 Все данные успешно сохранены во все источники!")
    else:
        logger.warning("Скрипт завершил работу, но данные для сохранения отсутствуют.")

if __name__ == "__main__":
    # Запуск асинхронного цикла
    asyncio.run(main())
