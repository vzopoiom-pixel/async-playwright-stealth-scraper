import asyncio
import csv
import logging
import sqlite3
from playwright.async_api import async_playwright
from fake_useragent import UserAgent

# Configure console logging output
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# --- CONFIGURATION ---
DB_NAME = "scraped_data.db"       # SQLite database file name
TXT_FILE = "extracted_quotes.txt" # Plain text report file name
CSV_FILE = "products_data.csv"    # CSV output file name
TARGET_URLS = [f"https://quotes.toscrape.com/page/{i}/" for i in range(1, 4)]

def init_db():
    """Initialize database and table if not already created"""
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
    logger.info("Database initialized successfully.")

def save_to_db_and_txt(data: list):
    """Save extracted data to SQLite and plain text summary"""
    if not data:
        return

    # 1. Save to SQLite database (duplicate prevention via IGNORE)
    with sqlite3.connect(DB_NAME) as conn:
        cursor = conn.cursor()
        for item in data:
            cursor.execute(
                "INSERT OR IGNORE INTO quotes (author, text) VALUES (?, ?)",
                (item["Author"], item["Quote"])
            )
        conn.commit()
    logger.info(f"Saved {len(data)} items to database {DB_NAME}.")

    # 2. Write to plain text file
    with open(TXT_FILE, 'w', encoding='utf-8') as txt:
        txt.write("=== EXTRACTED DATA SUMMARY ===\n\n")
        for index, item in enumerate(data, 1):
            txt.write(f"Record #{index}\n")
            txt.write(f"Author: {item['Author']}\n")
            txt.write(f"Quote: {item['Quote']}\n")
            txt.write("-" * 40 + "\n")
    logger.info(f"Summary report written to file {TXT_FILE}.")

async def parse_page(browser, url: str) -> list:
    """Open single page in isolated session and extract elements"""
    ua = UserAgent()
    
    # Create isolated browser context for each worker tab
    context = await browser.new_context(
        user_agent=ua.random,
        viewport={"width": 1920, "height": 1080}
    )
    
    # Mask automation flags to simulate human browsing
    await context.add_init_script("Object.defineProperty(navigator, 'webdriver', {get: () => undefined})")
    
    page = await context.new_page()
    page_data = []
    
    try:
        logger.info(f"Navigating to page: {url}")
        # Wait for network idle (ensures full React/Vue/AJAX rendering)
        await page.goto(url, wait_until="networkidle", timeout=30000)
        
        # Query target elements on the page
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
        logger.error(f"Error while processing page {url}: {str(e)}")
    finally:
        await context.close() # Close session to prevent memory leaks
        
    return page_data

async def main():
    # Initialize database before execution
    init_db()
    
    logger.info("Launching Playwright engine...")
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        
        # Construct task pool for concurrent execution
        tasks = [parse_page(browser, url) for url in TARGET_URLS]
        
        logger.info("Starting asynchronous page extraction...")
        # Execute tasks in parallel with error handling
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        await browser.close()
        
    # Aggregate data from all worker tasks
    all_data = []
    for res in results:
        if isinstance(res, list):
            all_data.extend(res)
            
    if all_data:
        # Save to Database and Text summary
        save_to_db_and_txt(all_data)
        
        # Export structured data to CSV
        keys = all_data[0].keys()
        with open(CSV_FILE, 'w', newline='', encoding='utf-8-sig') as output_file:
            dict_writer = csv.DictWriter(output_file, fieldnames=keys)
            dict_writer.writeheader()
            dict_writer.writerows(all_data)
        logger.info("All data successfully stored across all destinations!")
    else:
        logger.warning("Scraper finished, but no data was extracted.")

if __name__ == "__main__":
    # Run asyncio event loop
    asyncio.run(main())
