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
TXT_FILE = "extracted_quotes.txt" # Имя текстового файла для дублирования
CSV_FILE = "products_data.csv"    # Имя CSV файла
TARGET_URLS = [f"https://toscrape.com{i}/" for i in range(1, 4)]

def init_db():
    """Функция создания базы данных и таблицы (если их еще нет)"""
    with sqlite3.connect(DB_NAME) as conn:
        cursor = conn.cursor()
        # Создаем таблицу, если она отсутствует
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
    """Сохранение полученных данных в SQLite и в TXT файл"""
    if not data:
        return

    # 1. Запись в базу данных SQLite
    with sqlite3.connect(DB_NAME) as conn:
        cursor = conn.cursor()
        for item in data:
            # INSERT IGNORE (благодаря UNIQUE в структуре) защищает от дубликатов
            cursor.execute(
                "INSERT OR IGNORE INTO quotes (author, text) VALUES (?, ?)",
                (item["Author"], item["Quote"])
            )
        conn.commit()
    logger.info(f"Данные ({len(data)} шт.) проверены и сохранены в базу данных {DB_NAME}.")

    # 2. Запись в простой текстовый файл TXT
    with open(TXT_FILE, 'w', encoding='utf-8') as txt:
        txt.write("=== СПИСОК СОБРАННЫХ ДАННЫХ ===\n\n")
        for index, item in enumerate(data, 1):
            txt.write(f"Запись №{index}\n")
            txt.write(f"Автор: {item['Author']}\n")
            txt.write(f"Цитата: {item['Quote']}\n")
            txt.write("-" * 40 + "\n")
    logger.info(f"Текстовый отчет успешно записан в файл {TXT_FILE}.")

async def parse_page(browser, url: str) -> list:
    """Функция для открытия одной страницы и сбора элементов"""
    ua = UserAgent()
    
    # Создаем чистую изолированную сессию (контекст) для страницы
    context = await browser.new_context(
        user_agent=ua.random,
        viewport={"width": 1920, "height": 1080}
    )
    
    # Прячем от сайта тот факт, что им управляет робот
    await context.add_init_script("Object.defineProperty(navigator, 'webdriver', {get: () => undefined})")
    
    page = await context.new_page()
    page_data = []
    
    try:
        logger.info(f"Открываем страницу: {url}")
        # Ждем пока сайт полностью загрузит все скрипты и данные по сети
        await page.goto(url, wait_until="networkidle", timeout=30000)
        
        # Находим все блоки с классом .quote (карточки на сайте)
        elements = await page.query_selector_all(".quote")
        
        for el in elements:
            text_el = await el.query_selector(".text")
            author_el = await el.query_selector(".author")
            
            # Извлекаем чистый текст из найденных тегов
            text = await text_el.inner_text() if text_el else ""
            author = await author_el.inner_text() if author_el else ""
            
            page_data.append({
                "Quote": text.strip().replace("“", "").replace("”", ""),
                "Author": author.strip()
            })
            
    except Exception as e:
        logger.error(f"Ошибка при чтении страницы {url}: {str(e)}")
    finally:
        await context.close() # Закрываем вкладку, чтобы не забивать оперативную память
        
    return page_data

async def main():
    # Шаг 1: Готовим базу данных перед стартом парсинга
    init_db()
    
    logger.info("Запуск движка Playwright...")
    async with async_playwright() as p:
        # Запускаем скрытый браузер
        browser = await p.chromium.launch(headless=True)
        
        # Формируем список задач для одновременного запуска всех страниц
        tasks = [parse_page(browser, url) for url in TARGET_URLS]
        
        logger.info("Сканируем все страницы параллельно...")
        results = await asyncio.gather(*tasks)
        
        await browser.close()
        
    # Собираем списки из каждой вкладки в один общий большой список
    all_data = []
    for res in results:
        if isinstance(res, list):
            all_data.extend(res)
            
    if all_data:
        # Шаг 2: Сохраняем все в базу SQLite и создаем TXT-отчет
        save_to_db_and_txt(all_data)
        
        # Шаг 3: Дополнительно сохраняем в привычный CSV формат
        keys = all_data[0].keys()
        with open(CSV_FILE, 'w', newline='', encoding='utf-8-sig') as output_file:
            dict_writer = csv.DictWriter(output_file, fieldnames=keys)
            dict_writer.writeheader()
            dict_writer.writerows(all_data)
        logger.info("🎉 Процесс полностью завершен!")
    else:
        logger.warning("Скрипт отработал, но новых данных на страницах не обнаружено.")

if __name__ == "__main__":
    # Точка запуска всего асинхронного скрипта
    asyncio.run(main())
