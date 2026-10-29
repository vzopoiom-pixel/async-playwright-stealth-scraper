# High-Performance Asynchronous Web Scraper 

A production-ready, asynchronous web scraper built with **Python 3.10+**, **Playwright**, and **Asyncio**. Designed specifically to extract data from modern, dynamically rendered (React/Vue/Angular) websites while bypassing advanced anti-bot protection systems (Cloudflare, DataDome) and utilizing proxy rotation.

## 🚀 Key Features

*   **Asynchronous Architecture:** Powered by `asyncio` and `playwright` for high-throughput, concurrent page scraping.
*   **Anti-Bot Stealth Engine:** Injects custom scripts to mask automation flags (e.g., `navigator.webdriver`) and uses randomized user-agents via `fake-useragent`.
*   **Dynamic Content Handling:** Waits for network stability (`networkidle`) to guarantee complete JavaScript and AJAX execution before parsing.
*   **Proxy & Session Rotation:** Isolated browser contexts for each task to prevent cross-session leaks and support authorized HTTP/SOCKS5 proxies.
*   **Robust Error Handling:** Comprehensive logging system with precise error tracking (file, line number) ensuring continuous server uptime.
*   **Data Export:** Securely writes extracted data into structured `CSV` files with proper encoding (`utf-8-sig`) for Excel compatibility.

## ⚙️ Tech Stack

| Component | Technology | Description |
| :--- | :--- | :--- |
| **Core Engine** | Python 3.10+ | Clean OOP code design |
| **Scraping Framework** | Playwright (Chromium) | Faster and more reliable than Selenium |
| **Concurrency** | Asyncio | Non-blocking parallel task execution |
| **Data Format** | CSV | Standard output for business analytics |

## 🛠️ Installation & Setup

1.  **Clone the repository:**
    ```bash
    git clone https://github.com
    cd async-playwright-scraper
    ```

2.  **Create and activate a virtual environment:**
    ```bash
    python -m venv venv
    # On Windows:
    venv\Scripts\activate
    # On macOS/Linux:
    source venv/bin/activate
    ```

3.  **Install dependencies:**
    ```bash
    pip install -r requirements.txt
    ```

4.  **Install Playwright browser binaries:**
    ```bash
    playwright install chromium
    ```

## 💻 Configuration

Open the script and configure your target URLs and proxy settings in the configuration block:

```python
# --- CONFIGURATION BLOCK ---
PROXY_SERVER = "http://your-proxy-domain.com:8000"
PROXY_USER = "your_username"
PROXY_PASS = "your_password"
OUTPUT_FILE = "products_data.csv"
```

## 🏃 Execution

Run the scraper using the following command:

```bash
python scraper.py
```

## 📊 Project Structure

```text
├── scraper.py          # Main asynchronous scraper script
├── requirements.txt    # Project dependencies
└── README.md           # Project documentation
```

## 📄 License

This project is open-source and available under the [MIT License](LICENSE).

---
*Developed for professional automation and business intelligence pipelines.*
