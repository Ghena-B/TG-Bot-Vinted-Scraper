import os
import json
import logging
from telegram import InlineKeyboardButton, InlineKeyboardMarkup, Update
from telegram.error import BadRequest
from telegram.ext import (
    Application,
    CommandHandler,
    CallbackQueryHandler,
    ContextTypes,
)
# Import MongoDB‑based persistence functions
from mongo_persistence import load_configurations, save_configurations
from config import BRANDS, COLORS, STATUSES, PRICE_FROM, CURRENCIES, SIZE_MEN, SIZE_WOMEN

# ----- Setup Logging -----
logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s", level=logging.INFO
)
logger = logging.getLogger(__name__)

# ----- Helper Functions for Safe Editing -----
async def safe_edit_message_text(query, text, reply_markup=None):
    try:
        await query.edit_message_text(text, reply_markup=reply_markup)
    except BadRequest as e:
        if "Message is not modified" in str(e):
            pass
        else:
            raise

async def safe_edit_message_reply_markup(query, reply_markup):
    try:
        await query.edit_message_reply_markup(reply_markup=reply_markup)
    except BadRequest as e:
        if "Message is not modified" in str(e):
            pass
        else:
            raise

# ----- Configuration Keyboard Builders -----
def build_config_keyboard(configs_for_chat):
    # Build a keyboard listing keys from the current chat configuration.
    keyboard = []
    for key, config in configs_for_chat.items():
        name = config.get("name", key)
        keyboard.append([InlineKeyboardButton(name, callback_data=f"select_{key}")])
    return InlineKeyboardMarkup(keyboard)

def build_dashboard_keyboard(config):
    keyboard = [
        [InlineKeyboardButton("Edit Brands", callback_data="edit_brands")],
        [InlineKeyboardButton("Edit Colors", callback_data="edit_colors")],
        [InlineKeyboardButton("Edit Statuses", callback_data="edit_statuses")],
        [InlineKeyboardButton("Edit Minimum Price", callback_data="edit_price_from")],
        [InlineKeyboardButton("Edit Maximum Price", callback_data="edit_price_to")],
        [InlineKeyboardButton("Edit Currency", callback_data="edit_currency")],
        [InlineKeyboardButton("Edit Men's Sizes", callback_data="edit_size_men")],
        [InlineKeyboardButton("Edit Women's Sizes", callback_data="edit_size_women")],
        [InlineKeyboardButton("Save & Exit", callback_data="save_config")]
    ]
    return InlineKeyboardMarkup(keyboard)

def build_brand_keyboard(selected_brands):
    keyboard = []
    for name, bid in BRANDS.items():
        button_text = f"✅ {name}" if bid in selected_brands else name
        keyboard.append([InlineKeyboardButton(button_text, callback_data=f"brand_toggle_{bid}")])
    keyboard.append([InlineKeyboardButton("Confirm", callback_data="brand_confirm")])
    keyboard.append([InlineKeyboardButton("Back to Dashboard", callback_data="dashboard")])
    return InlineKeyboardMarkup(keyboard)

def build_color_keyboard(selected_colors):
    keyboard = []
    for name, cid in COLORS.items():
        button_text = f"✅ {name}" if cid in selected_colors else name
        keyboard.append([InlineKeyboardButton(button_text, callback_data=f"color_toggle_{cid}")])
    keyboard.append([InlineKeyboardButton("Confirm", callback_data="color_confirm")])
    keyboard.append([InlineKeyboardButton("Back to Dashboard", callback_data="dashboard")])
    return InlineKeyboardMarkup(keyboard)

def build_status_keyboard(selected_statuses):
    keyboard = []
    for name, sid in STATUSES.items():
        button_text = f"✅ {name}" if sid in selected_statuses else name
        keyboard.append([InlineKeyboardButton(button_text, callback_data=f"status_toggle_{sid}")])
    keyboard.append([InlineKeyboardButton("Confirm", callback_data="status_confirm")])
    keyboard.append([InlineKeyboardButton("Back to Dashboard", callback_data="dashboard")])
    return InlineKeyboardMarkup(keyboard)

def build_price_keyboard(selected_price):
    keyboard = []
    no_min_button = "✅ No minimum" if selected_price is None else "No minimum"
    keyboard.append([InlineKeyboardButton(no_min_button, callback_data="price_none")])
    for name, value in PRICE_FROM.items():
        button_text = f"✅ {name}" if selected_price == value else name
        keyboard.append([InlineKeyboardButton(button_text, callback_data=f"price_{value}")])
    keyboard.append([InlineKeyboardButton("Confirm", callback_data="price_confirm")])
    keyboard.append([InlineKeyboardButton("Back to Dashboard", callback_data="dashboard")])
    return InlineKeyboardMarkup(keyboard)

def build_max_price_keyboard(selected_max_price):
    keyboard = []
    for name, value in PRICE_FROM.items():
        button_text = f"✅ {name}" if selected_max_price == value else name
        keyboard.append([InlineKeyboardButton(button_text, callback_data=f"price_to_{value}")])
    keyboard.append([InlineKeyboardButton("Confirm", callback_data="price_to_confirm")])
    keyboard.append([InlineKeyboardButton("Back to Dashboard", callback_data="dashboard")])
    return InlineKeyboardMarkup(keyboard)

def build_currency_keyboard(selected_currency):
    keyboard = []
    for name, value in CURRENCIES.items():
        button_text = f"✅ {name}" if selected_currency == value else name
        keyboard.append([InlineKeyboardButton(button_text, callback_data=f"currency_{value}")])
    keyboard.append([InlineKeyboardButton("Confirm", callback_data="currency_confirm")])
    keyboard.append([InlineKeyboardButton("Back to Dashboard", callback_data="dashboard")])
    return InlineKeyboardMarkup(keyboard)

def build_size_men_keyboard(selected_sizes):
    keyboard = []
    for name, sid in SIZE_MEN.items():
        button_text = f"✅ {name}" if sid in selected_sizes else name
        keyboard.append([InlineKeyboardButton(button_text, callback_data=f"sizemen_toggle_{sid}")])
    keyboard.append([InlineKeyboardButton("Confirm", callback_data="sizemen_confirm")])
    keyboard.append([InlineKeyboardButton("Back to Dashboard", callback_data="dashboard")])
    return InlineKeyboardMarkup(keyboard)

def build_size_women_keyboard(selected_sizes):
    keyboard = []
    for name, sid in SIZE_WOMEN.items():
        button_text = f"✅ {name}" if sid in selected_sizes else name
        keyboard.append([InlineKeyboardButton(button_text, callback_data=f"sizewomen_toggle_{sid}")])
    keyboard.append([InlineKeyboardButton("Confirm", callback_data="sizewomen_confirm")])
    keyboard.append([InlineKeyboardButton("Back to Dashboard", callback_data="dashboard")])
    return InlineKeyboardMarkup(keyboard)

def get_config_summary(config):
    brand_ids = config.get("brand_ids", [])
    brand_names = [name for name, bid in BRANDS.items() if bid in brand_ids]
    color_ids = config.get("color_ids", [])
    color_names = [name for name, cid in COLORS.items() if cid in color_ids]
    status_ids = config.get("status_ids", [])
    status_names = [name for name, sid in STATUSES.items() if sid in status_ids]
    size_ids_men = config.get("size_ids_men", [])
    size_names_men = [name for name, sid in SIZE_MEN.items() if sid in size_ids_men]
    size_ids_women = config.get("size_ids_women", [])
    size_names_women = [name for name, sid in SIZE_WOMEN.items() if sid in size_ids_women]
    
    summary = f"Configuration: {config.get('name')}\n"
    summary += f"Brands: {', '.join(brand_names) if brand_names else 'None'}\n"
    summary += f"Colors: {', '.join(color_names) if color_names else 'None'}\n"
    summary += f"Statuses: {', '.join(status_names) if status_names else 'None'}\n"
    summary += f"Min Price: {config.get('price_from')}\n"
    summary += f"Max Price: {config.get('price_to')}\n"
    summary += f"Currency: {config.get('currency')}\n"
    summary += f"Men's Sizes: {', '.join(size_names_men) if size_names_men else 'None'}\n"
    summary += f"Women's Sizes: {', '.join(size_names_women) if size_names_women else 'None'}\n"
    return summary

# ----- Command Handlers -----
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat_id = str(update.effective_chat.id)
    configs, presets = load_configurations()
    if chat_id not in configs:
        if len(presets) >= 2:
            configs[chat_id] = {"men": presets[0], "women": presets[1]}
        elif presets:
            # If only one preset exists, you might duplicate it for both
            configs[chat_id] = {"men": presets[0], "women": presets[0]}
        else:
            # Fallback: create empty configs for both men and women
            configs[chat_id] = {
                "men": {
                    "name": "Men's Config",
                    "brand_ids": [],
                    "color_ids": [],
                    "status_ids": [],
                    "price_from": None,
                    "price_to": None,
                    "currency": None,
                    "size_ids_men": []
                },
                "women": {
                    "name": "Women's Config",
                    "brand_ids": [],
                    "color_ids": [],
                    "status_ids": [],
                    "price_from": None,
                    "price_to": None,
                    "currency": None,
                    "size_ids_women": []
                }
            }
        
        # Save the newly created configuration for this chat
        save_configurations(chat_id, configs[chat_id])
    
    await update.message.reply_text(
        "You are registered for configuration notifications.\n"
        "Use /selectconfig to switch between your saved configurations."
    )

async def select_config(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat_id = str(update.effective_chat.id)
    configs, presets = load_configurations()
    if chat_id not in configs:
        await update.message.reply_text("No configurations found. Use /start to register.")
        return
    # List the keys from your chat configuration.
    reply_markup = build_config_keyboard(configs[chat_id])
    await update.message.reply_text("Select one of your configurations:", reply_markup=reply_markup)

async def config_dashboard(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat_id = str(update.effective_chat.id)
    configs, presets = load_configurations()
    if chat_id not in configs:
        if len(presets) >= 2:
            configs[chat_id] = {"men": presets[0], "women": presets[1]}
        elif presets:
            configs[chat_id] = {"default": presets[0]}
        save_configurations(chat_id, configs[chat_id])
    
    config_key = context.user_data.get("config_key", None)
    if config_key is None or config_key not in configs[chat_id]:
        config_key = "men" if "men" in configs[chat_id] else next(iter(configs[chat_id].keys()))
        context.user_data["config_key"] = config_key
    config = configs[chat_id][config_key]
    text = get_config_summary(config)
    reply_markup = build_dashboard_keyboard(config)
    await update.message.reply_text(text, reply_markup=reply_markup)

async def button_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    data = query.data
    chat_id = str(update.effective_chat.id)
    configs, presets = load_configurations()
    config_key = context.user_data.get("config_key", "men")
    if chat_id not in configs or config_key not in configs[chat_id]:
        await safe_edit_message_text(query, "No configuration found. Use /start to register.")
        return
    config = configs[chat_id][config_key]
    
    # --- Handle Configuration Selection from /selectconfig ---
    if data.startswith("select_"):
        new_key = data.split("_", 1)[1]
        if new_key in configs[chat_id]:
            context.user_data["config_key"] = new_key
            await safe_edit_message_text(query, f"Switched to configuration '{configs[chat_id][new_key].get('name', new_key)}'. Use /dashboard to view/edit.")
        else:
            await safe_edit_message_text(query, "Selected configuration not found.")
        return
    
    # --- Handle Preset Selection (if needed) ---
    if data.startswith("preset_"):
        preset_idx = int(data.split("_")[1])
        if preset_idx < len(presets):
            preset = presets[preset_idx]
            key = "men" if "Men" in preset.get("name", "") else ("women" if "Women" in preset.get("name", "") else f"preset_{preset_idx}")
            configs[chat_id][key] = preset
            context.user_data["config_key"] = key
            save_configurations(chat_id, configs[chat_id])
            await safe_edit_message_text(query, f"Preset '{preset.get('name')}' assigned to key '{key}'. Use /dashboard to view/edit.")
        else:
            await safe_edit_message_text(query, "Invalid preset selection.")
        return

    # --- Dashboard Navigation ---
    if data == "dashboard":
        text = get_config_summary(config)
        reply_markup = build_dashboard_keyboard(config)
        await safe_edit_message_text(query, text, reply_markup)
        return

    # --- Save Configuration ---
    if data == "save_config":
        save_configurations(chat_id, configs[chat_id])
        await safe_edit_message_text(query, "Configuration saved.\n" + get_config_summary(config))
        return

    # --- Editing Fields ---
    if data == "edit_brands":
        context.user_data["brand_ids"] = set(config.get("brand_ids", []))
        reply_markup = build_brand_keyboard(context.user_data["brand_ids"])
        await safe_edit_message_text(query, "Select Brands:", reply_markup)
        return
    if data == "edit_colors":
        context.user_data["color_ids"] = set(config.get("color_ids", []))
        reply_markup = build_color_keyboard(context.user_data["color_ids"])
        await safe_edit_message_text(query, "Select Colors:", reply_markup)
        return
    if data == "edit_statuses":
        context.user_data["status_ids"] = set(config.get("status_ids", []))
        reply_markup = build_status_keyboard(context.user_data["status_ids"])
        await safe_edit_message_text(query, "Select Statuses:", reply_markup)
        return
    if data == "edit_price_from":
        context.user_data["price_from"] = config.get("price_from", None)
        reply_markup = build_price_keyboard(context.user_data["price_from"])
        await safe_edit_message_text(query, "Select Minimum Price:", reply_markup)
        return
    if data == "edit_price_to":
        context.user_data["price_to"] = config.get("price_to", None)
        reply_markup = build_max_price_keyboard(context.user_data["price_to"])
        await safe_edit_message_text(query, "Select Maximum Price:", reply_markup)
        return
    if data == "edit_currency":
        context.user_data["currency"] = config.get("currency", None)
        reply_markup = build_currency_keyboard(context.user_data["currency"])
        await safe_edit_message_text(query, "Select Currency:", reply_markup)
        return
    if data == "edit_size_men":
        context.user_data["size_ids_men"] = set(config.get("size_ids_men", []))
        reply_markup = build_size_men_keyboard(context.user_data["size_ids_men"])
        await safe_edit_message_text(query, "Select Men's Sizes:", reply_markup)
        return
    if data == "edit_size_women":
        context.user_data["size_ids_women"] = set(config.get("size_ids_women", []))
        reply_markup = build_size_women_keyboard(context.user_data["size_ids_women"])
        await safe_edit_message_text(query, "Select Women's Sizes:", reply_markup)
        return

    # --- Toggling and Confirming Fields ---
    if data.startswith("brand_toggle_"):
        brand_id = int(data.split("_")[2])
        selected = context.user_data.get("brand_ids", set())
        if brand_id in selected:
            selected.remove(brand_id)
        else:
            selected.add(brand_id)
        context.user_data["brand_ids"] = selected
        reply_markup = build_brand_keyboard(selected)
        await safe_edit_message_reply_markup(query, reply_markup)
        return
    if data == "brand_confirm":
        config["brand_ids"] = list(context.user_data.get("brand_ids", set()))
        save_configurations(chat_id, configs[chat_id])
        await safe_edit_message_text(
            query,
            "Brands updated.\n" + get_config_summary(config),
            build_dashboard_keyboard(config)
        )
        return

    if data.startswith("color_toggle_"):
        color_id = int(data.split("_")[2])
        selected = context.user_data.get("color_ids", set())
        if color_id in selected:
            selected.remove(color_id)
        else:
            selected.add(color_id)
        context.user_data["color_ids"] = selected
        reply_markup = build_color_keyboard(selected)
        await safe_edit_message_reply_markup(query, reply_markup)
        return
    if data == "color_confirm":
        config["color_ids"] = list(context.user_data.get("color_ids", set()))
        save_configurations(chat_id, configs[chat_id])
        await safe_edit_message_text(
            query,
            "Colors updated.\n" + get_config_summary(config),
            build_dashboard_keyboard(config)
        )
        return

    if data.startswith("status_toggle_"):
        status_id = int(data.split("_")[2])
        selected = context.user_data.get("status_ids", set())
        if status_id in selected:
            selected.remove(status_id)
        else:
            selected.add(status_id)
        context.user_data["status_ids"] = selected
        reply_markup = build_status_keyboard(selected)
        await safe_edit_message_reply_markup(query, reply_markup)
        return
    if data == "status_confirm":
        config["status_ids"] = list(context.user_data.get("status_ids", set()))
        save_configurations(chat_id, configs[chat_id])
        await safe_edit_message_text(
            query,
            "Statuses updated.\n" + get_config_summary(config),
            build_dashboard_keyboard(config)
        )
        return

    if data == "price_none":
        context.user_data["price_from"] = None
        reply_markup = build_price_keyboard(None)
        await safe_edit_message_reply_markup(query, reply_markup)
        return
    elif data == "price_confirm":
        config["price_from"] = context.user_data.get("price_from", None)
        save_configurations(chat_id, configs[chat_id])
        await safe_edit_message_text(
            query,
            "Minimum price updated.\n" + get_config_summary(config),
            build_dashboard_keyboard(config)
        )
        return
    elif data.startswith("price_") and not data.startswith("price_to_"):
        try:
            price_value = int(data.split("_")[1])
        except (IndexError, ValueError):
            await safe_edit_message_text(query, "Error parsing minimum price value.")
            return
        context.user_data["price_from"] = price_value
        reply_markup = build_price_keyboard(price_value)
        await safe_edit_message_reply_markup(query, reply_markup)
        return

    if data == "price_to_confirm":
        config["price_to"] = context.user_data.get("price_to", None)
        save_configurations(chat_id, configs[chat_id])
        await safe_edit_message_text(
            query,
            "Maximum price updated.\n" + get_config_summary(config),
            build_dashboard_keyboard(config)
        )
        return
    elif data.startswith("price_to_"):
        try:
            max_price_value = int(data.split("_")[2])
        except (IndexError, ValueError):
            await safe_edit_message_text(query, "Error parsing maximum price value.")
            return
        context.user_data["price_to"] = max_price_value
        reply_markup = build_max_price_keyboard(max_price_value)
        await safe_edit_message_reply_markup(query, reply_markup)
        return

    if data.startswith("currency_"):
        currency_value = data.split("_")[1]
        context.user_data["currency"] = currency_value
        reply_markup = build_currency_keyboard(currency_value)
        await safe_edit_message_reply_markup(query, reply_markup)
        return
    if data == "currency_confirm":
        config["currency"] = context.user_data.get("currency", None)
        save_configurations(chat_id, configs[chat_id])
        await safe_edit_message_text(
            query,
            "Currency updated.\n" + get_config_summary(config),
            build_dashboard_keyboard(config)
        )
        return

    if data.startswith("sizemen_toggle_"):
        size_id = int(data.split("_")[2])
        selected = context.user_data.get("size_ids_men", set())
        if size_id in selected:
            selected.remove(size_id)
        else:
            selected.add(size_id)
        context.user_data["size_ids_men"] = selected
        reply_markup = build_size_men_keyboard(selected)
        await safe_edit_message_reply_markup(query, reply_markup)
        return
    if data == "sizemen_confirm":
        config["size_ids_men"] = list(context.user_data.get("size_ids_men", set()))
        save_configurations(chat_id, configs[chat_id])
        await safe_edit_message_text(
            query,
            "Men's sizes updated.\n" + get_config_summary(config),
            build_dashboard_keyboard(config)
        )
        return

    if data.startswith("sizewomen_toggle_"):
        size_id = int(data.split("_")[2])
        selected = context.user_data.get("size_ids_women", set())
        if size_id in selected:
            selected.remove(size_id)
        else:
            selected.add(size_id)
        context.user_data["size_ids_women"] = selected
        reply_markup = build_size_women_keyboard(selected)
        await safe_edit_message_reply_markup(query, reply_markup)
        return
    if data == "sizewomen_confirm":
        config["size_ids_women"] = list(context.user_data.get("size_ids_women", set()))
        save_configurations(chat_id, configs[chat_id])
        await safe_edit_message_text(
            query,
            "Women's sizes updated.\n" + get_config_summary(config),
            build_dashboard_keyboard(config)
        )
        return
    
    # Fallback response:
    await safe_edit_message_text(query, "Unknown selection.")

def main():
    from config import TELEGRAM_BOT_TOKEN
    application = Application.builder().token(TELEGRAM_BOT_TOKEN).build()

    application.add_handler(CommandHandler("start", start))
    application.add_handler(CommandHandler("selectconfig", select_config))
    application.add_handler(CommandHandler("dashboard", config_dashboard))
    application.add_handler(CallbackQueryHandler(button_handler))
    
    application.run_polling()

if __name__ == "__main__":
    main()
