import os
from dotenv import load_dotenv

load_dotenv()

# Telegram settings
TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")

# Default URL for scraping (can be overridden by user configs)
DEFAULT_SCRAPER_URL = "https://www.vinted.co.uk/catalog"

# Mappings for filter options 
BRANDS = {
    "Nike": 53,
    "Adidas": 14,
    "Puma": 535,
    "Reebok": 162,
    "Under Armour": 52035,
    "New Balance": 1775,
    "Skechers": 16429
}

COLORS = {
    "Black": 1,
    "White": 12,
    "Blue": 9,
    "Gray": 3,
    "Beige": 4
}

STATUSES = {
    "New with tag": 6,
    "New without tag": 1,
    "Very good": 2,
    "Good": 3,
    "Satisfactory": 4
}

PRICE_FROM = {
    "5": 5,
    "10": 10,
    "15": 15,
    "20": 20,
    "25": 25,
    "30": 30,
    "40": 40,
    "50": 50
}

CURRENCIES = {
    "GBP": "GBP",
    "EUR": "EUR",
    "USD": "USD"
}

SIZE_MEN = {
    "4": 776,
    "4.5": 777,
    "5": 778,
    "5.5": 779,
    "6": 780,
    "6.5": 781,
    "7": 782,
    "7.5": 783,
    "8": 784,
    "8.5": 785,
    "9": 786,
    "9.5": 787,
    "10": 788,
    "10.5": 789,
    "11": 790,
    "11.5": 791,
    "12": 792,
    "12.5": 793,
    "13": 794,
    "13.5": 795,
    "14": 1190,
    "14.5": 1621,
    "15": 1191,
    "16": 1622
}

SIZE_WOMEN = {
    "1": 55,
    "1.5": 56,
    "2": 57,
    "2.5": 58,
    "3": 59,
    "3.5": 60,
    "4": 61,
    "4.5": 62,
    "5": 63,
    "5.5": 1195,
    "6": 1196,
    "6.5": 1197,
    "7": 1198,
    "7.5": 1199,
    "8": 1200,
    "8.5": 1201,
    "9": 1364,
    "9.5": 1573,
    "10": 1574,
    "10.5": 1575,
    "11": 1576,
    "11.5": 1577,
    "12": 1579,
    "12.5": 1580,
    "13": 1578
}
