import os
import time
import logging
import urllib.parse
import requests
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.chrome.service import Service
from webdriver_manager.chrome import ChromeDriverManager
from bs4 import BeautifulSoup

# Import MongoDB‑based persistence functions
from mongo_persistence import load_configurations, load_known_ids, save_known_ids
from config import DEFAULT_SCRAPER_URL

# ----- Setup Logging -----
logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s", level=logging.INFO
)
logger = logging.getLogger(__name__)

# ----- Telegram Notification Functions -----
def send_telegram_message(message, chat_id):
    """
    Sends a Telegram message to a given chat.
    Splits the message into chunks if needed.
    """
    from config import TELEGRAM_BOT_TOKEN  # Import token from config
    url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage"
    max_length = 4000  # Safe limit
    responses = []
    for i in range(0, len(message), max_length):
        payload = {
            "chat_id": chat_id,
            "text": message[i:i+max_length],
            "parse_mode": "HTML"
        }
        response = requests.post(url, data=payload)
        responses.append(response.json())
    return responses

# ----- URL Building -----
def build_url(config):
    """
    Builds the URL for Vinted catalog using the configuration.
    List values are encoded with square brackets.
    """
    domain = config.get("domain", "www.vinted.co.uk")
    base_url = f"https://{domain}/catalog"
    keys_to_skip = {"domain", "name"}
    params = []
    for key, value in config.items():
        if key in keys_to_skip or value is None:
            continue
        if isinstance(value, list):
            for item in value:
                params.append((f"{key}[]", item))
        else:
            params.append((key, value))
    query = urllib.parse.urlencode(params, doseq=True)
    return f"{base_url}?{query}"

def fix_url(href):
    """Prepends domain if URL is relative."""
    if not href.startswith("http"):
        return "https://www.vinted.co.uk" + href
    return href

# ----- Scraping Function -----
def scrape_vinted(url):
    """
    Uses Selenium to scrape the Vinted page and returns a list of products.
    Each product is a dict with keys: "id", "title", and "url".
    """
    chrome_options = Options()
    chrome_options.add_argument("--headless")
    chrome_options.add_argument("--disable-gpu")
    chrome_options.add_argument("--no-sandbox")
    chrome_options.add_argument("--window-size=1920,1080")
    chrome_options.add_argument(
        "user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/114.0.0.0 Safari/537.36"
    )
    service = Service(ChromeDriverManager().install())
    driver = webdriver.Chrome(service=service, options=chrome_options)
    driver.get(url)
    time.sleep(10)
    driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")
    time.sleep(5)
    html = driver.page_source
    driver.quit()
    
    soup = BeautifulSoup(html, 'html.parser')
    product_links = soup.select('a[data-testid$="--overlay-link"]')
    products = []
    for a_tag in product_links:
        href = a_tag.get("href")
        if href:
            href = fix_url(href)
            try:
                parts = href.split("/items/")[1]
                product_id = parts.split("-")[0]
            except Exception:
                product_id = "Unknown"
            product_title = a_tag.get("title", "No title")
            products.append({
                "id": product_id,
                "title": product_title,
                "url": href
            })
    return products

def get_new_products(products, known_ids):
    """Return products whose IDs are not in known_ids."""
    return [p for p in products if p["id"] not in known_ids]

# ----- Main Execution -----
if __name__ == "__main__":
    configs, presets = load_configurations()
    
    # Iterate over each chat configuration (supports multi-config)
    for chat_id, chat_config in configs.items():
        # Load known IDs for this chat
        known_ids = load_known_ids(chat_id)
        
        # Check if the configuration is multi-config (contains sub-configs)
        if isinstance(chat_config, dict) and any(isinstance(v, dict) for v in chat_config.values()):
            for config_key, sub_config in chat_config.items():
                config_name = sub_config.get("name", f"Unnamed config ({config_key})")
                url = build_url(sub_config)
                logger.info(f"Scraping URL for chat {chat_id} ({config_name}): {url}")
                products = scrape_vinted(url)
                logger.info(f"Found {len(products)} products for chat {chat_id} ({config_name}).")
                new_products = get_new_products(products, known_ids)
                if new_products:
                    message = f"New Vinted products found for <b>{config_name}</b>:\n\n"
                    for prod in new_products:
                        message += f"<b>{prod['title']}</b>\nID: {prod['id']}\nURL: {prod['url']}\n\n"
                    responses = send_telegram_message(message, chat_id)
                    logger.info(f"Sent Telegram notification to chat {chat_id}: {responses}")
                else:
                    logger.info(f"No new products for chat {chat_id} ({config_name}).")
                all_ids = {p["id"] for p in products}
                known_ids = known_ids.union(all_ids)
        else:
            config_name = chat_config.get("name", "Unnamed config")
            url = build_url(chat_config)
            logger.info(f"Scraping URL for chat {chat_id} ({config_name}): {url}")
            products = scrape_vinted(url)
            logger.info(f"Found {len(products)} products for chat {chat_id} ({config_name}).")
            new_products = get_new_products(products, known_ids)
            if new_products:
                message = f"New Vinted products found for <b>{config_name}</b>:\n\n"
                for prod in new_products:
                    message += f"<b>{prod['title']}</b>\nID: {prod['id']}\nURL: {prod['url']}\n\n"
                responses = send_telegram_message(message, chat_id)
                logger.info(f"Sent Telegram notification to chat {chat_id}: {responses}")
            else:
                logger.info(f"No new products for chat {chat_id}.")
            all_ids = {p["id"] for p in products}
            known_ids = known_ids.union(all_ids)
        
        # Save updated known IDs for this chat in MongoDB
        save_known_ids(chat_id, known_ids)
