import json
import os
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, CallbackQueryHandler, MessageHandler, filters, ContextTypes, ConversationHandler

# Load scholarship data
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
with open(os.path.join(SCRIPT_DIR, "scholarships.json"), "r") as f:
    SCHOLARSHIPS = json.load(f)

# Conversation states
CHOOSING_LEVEL, CHOOSING_FIELD, CHOOSING_REGION = range(3)

FIELDS = ["artificial intelligence", "computer science", "engineering", "mathematics", "any"]
LEVELS = ["undergraduate", "masters", "phd"]
REGIONS = ["Africa", "Europe", "Middle East", "Asia", "North America", "All"]

REGION_MAP = {
    "Africa": ["Ghana", "Rwanda", "Mauritius", "Egypt", "Multiple"],
    "Europe": ["Germany", "UK", "France", "Sweden", "Switzerland", "Turkey"],
    "Middle East": ["UAE", "Saudi Arabia"],
    "Asia": ["South Korea", "Japan"],
    "North America": ["USA", "Canada"],
}


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    keyboard = [[InlineKeyboardButton(level.title(), callback_data="level_" + level)] for level in LEVELS]
    await update.message.reply_text(
        "Welcome to ScholarFinder!\n\n"
        "I help students find scholarships and universities.\n"
        "Let's find the right opportunity for you.\n\n"
        "What level are you looking for?",
        reply_markup=InlineKeyboardMarkup(keyboard)
    )
    return CHOOSING_LEVEL


async def level_chosen(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    level = query.data.replace("level_", "")
    context.user_data["level"] = level

    keyboard = [[InlineKeyboardButton(f.title(), callback_data="field_" + f)] for f in FIELDS]
    await query.edit_message_text(
        "Level: " + level.title() + "\n\nWhat field of study?",
        reply_markup=InlineKeyboardMarkup(keyboard)
    )
    return CHOOSING_FIELD


async def field_chosen(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    field = query.data.replace("field_", "")
    context.user_data["field"] = field

    keyboard = [[InlineKeyboardButton(r, callback_data="region_" + r)] for r in REGIONS]
    await query.edit_message_text(
        "Level: " + context.user_data["level"].title() + "\n"
        "Field: " + field.title() + "\n\n"
        "Preferred region?",
        reply_markup=InlineKeyboardMarkup(keyboard)
    )
    return CHOOSING_REGION


async def region_chosen(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    region = query.data.replace("region_", "")
    level = context.user_data["level"]
    field = context.user_data["field"]

    results = []
    for s in SCHOLARSHIPS:
        if level not in s["level"]:
            continue
        if field != "any" and "any" not in s["field"] and field not in s["field"]:
            continue
        if region != "All":
            region_countries = REGION_MAP.get(region, [])
            if s["country"] not in region_countries and s["country"] != "Multiple":
                continue
        results.append(s)

    if not results:
        text = "No exact matches found. Try broadening your search with /start"
    else:
        text = "Found " + str(len(results)) + " scholarship(s):\n\n"
        for s in results:
            text += "--- " + s["name"] + " ---\n"
            text += "University: " + s["university"] + "\n"
            text += "Country: " + s["country"] + "\n"
            text += "Funding: " + s["funding"] + "\n"
            text += "Deadline: " + s["deadline"] + "\n"
            text += s["description"] + "\n"
            text += "Link: " + s["link"] + "\n\n"
        text += "Search again with /start"

    await query.edit_message_text(text)
    return ConversationHandler.END


async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "ScholarFinder - Find scholarships easily\n\n"
        "Commands:\n"
        "/start - Search for scholarships\n"
        "/all - List all scholarships\n"
        "/help - Show this message\n\n"
        "Built by Scott | Alpha Global Minds"
    )


async def all_scholarships(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = "All scholarships in database (" + str(len(SCHOLARSHIPS)) + "):\n\n"
    for i, s in enumerate(SCHOLARSHIPS):
        text += str(i + 1) + ". " + s["name"] + " (" + s["country"] + ") - " + s["funding"] + "\n"
    text += "\nUse /start to search with filters"

    if len(text) > 4000:
        parts = [text[i:i+4000] for i in range(0, len(text), 4000)]
        for part in parts:
            await update.message.reply_text(part)
    else:
        await update.message.reply_text(text)


async def unknown_text(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "Hey! I'm ScholarFinder.\n\n"
        "Use /start to search for scholarships\n"
        "Use /all to see every scholarship in my database\n"
        "Use /help for more info"
    )


async def cancel(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("Search cancelled. Use /start to begin again.")
    return ConversationHandler.END


def main():
    TOKEN = "YOUR_TOKEN_HERE"
    app = Application.builder().token(TOKEN).build()

    conv_handler = ConversationHandler(
        entry_points=[CommandHandler("start", start)],
        states={
            CHOOSING_LEVEL: [CallbackQueryHandler(level_chosen, pattern="^level_")],
            CHOOSING_FIELD: [CallbackQueryHandler(field_chosen, pattern="^field_")],
            CHOOSING_REGION: [CallbackQueryHandler(region_chosen, pattern="^region_")],
        },
        fallbacks=[CommandHandler("cancel", cancel)],
    )

    app.add_handler(conv_handler)
    app.add_handler(CommandHandler("help", help_command))
    app.add_handler(CommandHandler("all", all_scholarships))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, unknown_text))

    print("ScholarFinder bot is running!")
    app.run_polling()


if __name__ == "__main__":
    main()
