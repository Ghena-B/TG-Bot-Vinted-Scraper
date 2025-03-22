import os
from pymongo import MongoClient
from dotenv import load_dotenv

load_dotenv()

MONGODB_URI = os.getenv("MONGODB_URI")
DATABASE_NAME = os.getenv("DATABASE_NAME", "vinted_scraper")
CONFIG_COLLECTION = "configs"
IDS_COLLECTION = "known_ids"

client = MongoClient(MONGODB_URI)
db = client[DATABASE_NAME]

def load_configurations():
    """Load configurations from MongoDB.
    The document structure can be:
    {
        "_id": "<chat_id>",
        "configs": { ... }
    }
    """
    collection = db[CONFIG_COLLECTION]
    # For simplicity, return a dict mapping chat_id to configuration
    configs = {}
    for doc in collection.find({}):
        chat_id = doc["_id"]
        configs[chat_id] = doc.get("configs", {})
    presets = []  # or load from a different collection
    return configs, presets

def save_configurations(chat_id, config_data):
    """Upsert the configuration for a given chat_id."""
    collection = db[CONFIG_COLLECTION]
    collection.update_one(
        {"_id": chat_id},
        {"$set": {"configs": config_data}},
        upsert=True
    )

def load_known_ids(chat_id):
    collection = db[IDS_COLLECTION]
    doc = collection.find_one({"_id": chat_id})
    return set(doc.get("ids", [])) if doc else set()

def save_known_ids(chat_id, new_ids):
    collection = db[IDS_COLLECTION]
    collection.update_one(
        {"_id": chat_id},
        {"$set": {"ids": list(new_ids)}},
        upsert=True
    )
