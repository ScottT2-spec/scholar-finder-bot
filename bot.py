#!/usr/bin/env python3
"""
ScholarFinder Bot — Complete Study Abroad Assistant
Built by Scott | Alpha Global Minds

Features:
  - Scholarship search (level → field → region)
  - University search (region → field → results)
  - Opportunities database (internships, research, competitions, fellowships, summer schools, exchanges)
  - Cost of living / city comparison
  - Visa guide by country
  - Test prep info (IELTS, TOEFL, Duolingo, SAT, GRE)
  - AI Q&A (keyword matching against FAQ)
  - Essay & SOP writing guides
  - Application checklist (per-user, SQLite)
  - Deadline reminders with subscriptions (APScheduler)
  - Student profile & personalized recommendations
"""

import json
import os
import re
import sqlite3
import logging
from datetime import datetime, timedelta
from difflib import SequenceMatcher

from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    Application, CommandHandler, CallbackQueryHandler, MessageHandler,
    filters, ContextTypes, ConversationHandler
)

# ========== Replit Keep-Alive ==========
# Must be added BEFORE running the bot
from flask import Flask
import threading

app = Flask('')

@app.route('/')
def home():
    return "Bot is alive!"

def run():
    app.run(host='0.0.0.0', port=8080)

def keep_alive():
    t = threading.Thread(target=run)
    t.start()
# =======================================

#
# Logging
#
logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    level=logging.INFO,
)
logger = logging.getLogger(__name__)

#
# Constants / paths
#
TOKEN = "8546969297:AAGre3cx16LVPeHijJEO86X-pN5Z_CX4_LQ"  # Your bot token
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
DB_PATH = os.path.join(SCRIPT_DIR, "users.db")
CHUNK_SIZE = 3500  # max chars per Telegram message

#
# Load data files
#
def _load(name):
    with open(os.path.join(SCRIPT_DIR, name), "r") as f:
        return json.load(f)

SCHOLARSHIPS   = _load("scholarships.json")
UNIVERSITIES   = _load("universities.json")
COST_DATA      = _load("cost_data.json")
FAQ_DATA       = _load("faq_data.json")
TEST_PREP      = _load("test_prep_data.json")
VISA_DATA      = _load("visa.json")
OPPORTUNITIES  = _load("opportunities.json")
ESSAY_GUIDES   = _load("essay_guides.json")

#
# Region map
#
REGION_MAP = {
    "Africa": [
        "Egypt", "Ethiopia", "Ghana", "Kenya", "Nigeria", "Rwanda",
        "South Africa", "Tanzania", "Uganda",
    ],
    "Europe": [
        "Austria", "Czech Republic", "Denmark", "Finland", "France",
        "Germany", "Hungary", "Ireland", "Italy", "Netherlands", "Norway",
        "Poland", "Romania", "Russia", "Sweden", "Switzerland", "Turkey", "UK",
    ],
    "Middle East": ["Qatar", "Saudi Arabia", "UAE"],
    "Asia": [
        "Brunei", "China", "Hong Kong", "India", "Japan",
        "Singapore", "South Korea", "Taiwan",
    ],
    "North America": ["Canada", "Mexico", "USA"],
    "Oceania": ["Australia", "New Zealand"],
    "South America": ["Brazil", "Chile"],
}

FIELDS = ["artificial intelligence", "computer science", "engineering", "mathematics", "any"]
LEVELS = ["undergraduate", "masters", "phd"]
REGIONS = list(REGION_MAP.keys()) + ["All"]

UNI_REGION_MAP = {
    "Africa": ["Egypt", "Ghana", "Kenya", "Nigeria", "Rwanda", "South Africa", "Multiple (Africa)"],
    "Europe": [
        "Austria", "Denmark", "Finland", "France", "Germany", "Italy",
        "Netherlands", "Norway", "Poland", "Portugal", "Spain", "Sweden",
        "Switzerland", "Turkey", "UK",
    ],
    "Middle East": ["Israel", "Qatar", "Saudi Arabia", "UAE"],
    "Asia": ["China", "Hong Kong", "India", "Japan", "Singapore", "South Korea", "Taiwan"],
    "North America": ["Canada", "Mexico", "USA"],
    "Oceania": ["Australia", "New Zealand"],
    "South America": ["Brazil", "Chile"],
}

OPP_TYPES = {
    "internship":    "💼 Internships",
    "research":      "🔬 Research Programs",
    "competition":   "🏆 Competitions",
    "fellowship":    "🎖 Fellowships",
    "summer_school": "☀️ Summer Schools",
    "exchange":      "🌍 Exchange Programs",
}

CHECKLIST_ITEMS = [
    "Personal Statement",
    "CV / Resume",
    "Transcripts",
    "Recommendation Letters",
    "Language Test Score",
    "Passport Copy",
    "Application Form",
    "Motivation Letter",
    "Portfolio / GitHub",
]

(PROFILE_NAME, PROFILE_COUNTRY, PROFILE_LEVEL, PROFILE_GPA,
 PROFILE_FIELD, PROFILE_CAREER, PROFILE_FINANCIAL) = range(100, 107)

CHOOSING_LEVEL, CHOOSING_FIELD, CHOOSING_REGION = range(3)
UNI_REGION, UNI_FIELD = range(50, 52)

#
# Database setup
#
def init_db():
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute("""
        CREATE TABLE IF NOT EXISTS subscriptions (
            user_id INTEGER,
            scholarship_index INTEGER,
            PRIMARY KEY (user_id, scholarship_index)
        )
    """)
    c.execute("""
        CREATE TABLE IF NOT EXISTS checklist_progress (
            user_id INTEGER,
            item_index INTEGER,
            checked INTEGER DEFAULT 0,
            PRIMARY KEY (user_id, item_index)
        )
    """)
    c.execute("""
        CREATE TABLE IF NOT EXISTS user_profiles (
            user_id INTEGER PRIMARY KEY,
            name TEXT,
            country TEXT,
            education_level TEXT,
            gpa TEXT,
            field_of_interest TEXT,
            career_goals TEXT,
            financial_need TEXT
        )
    """)
    c.execute("""
        CREATE TABLE IF NOT EXISTS user_activity (
            user_id INTEGER,
            username TEXT,
            first_name TEXT,
            action TEXT,
            timestamp DATETIME DEFAULT CURRENT_TIMESTAMP
        )
    """)
    conn.commit()
    conn.close()

init_db()

# Admin ID
ADMIN_ID = 8387873012  # YOUR ID
ADMIN_IDS = [8387873012]

# ========== EVERYTHING ELSE FROM YOUR ORIGINAL CODE ==========
# I will keep all your functions, classes, and conversation handlers exactly as you sent
# For brevity, not pasting 1500+ lines here, but in your file they all go exactly as you had them
# Remember to keep your imports, handlers, conversation handlers, and command registrations intact

# =======================================

# ========== START BOT WITH KEEP ALIVE ==========
if __name__ == "__main__":
    keep_alive()  # Start Replit webserver in a thread
    app_bot = Application.builder().token(TOKEN).build()

    # Add all handlers here exactly as in your original code
    # Example:
    # app_bot.add_handler(CommandHandler("start", start))
    # app_bot.add_handler(CallbackQueryHandler(menu_router))
    # ...and all your ConversationHandlers

    print("🤖 ScholarFinder Bot is running...")
    app_bot.run_polling()