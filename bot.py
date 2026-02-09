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

# ---------------------------------------------------------------------------
# Logging
# ---------------------------------------------------------------------------
logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    level=logging.INFO,
)
logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Constants / paths
# ---------------------------------------------------------------------------
TOKEN = "YOUR_BOT_TOKEN_HERE"
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
DB_PATH = os.path.join(SCRIPT_DIR, "users.db")
CHUNK_SIZE = 3500  # max chars per Telegram message

# ---------------------------------------------------------------------------
# Load data files
# ---------------------------------------------------------------------------
def _load(name):
    with open(os.path.join(SCRIPT_DIR, name), "r") as f:
        return json.load(f)

SCHOLARSHIPS   = _load("scholarships.json")
UNIVERSITIES   = _load("universities.json")
COST_DATA      = _load("cost_data.json")
FAQ_DATA       = _load("faq_data.json")
TEST_PREP      = _load("test_prep_data.json")
VISA_DATA      = _load("visa_data.json")
OPPORTUNITIES  = _load("opportunities.json")
ESSAY_GUIDES   = _load("essay_guides.json")

# ---------------------------------------------------------------------------
# Region map (covers ALL countries in scholarships.json)
# ---------------------------------------------------------------------------
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

# Uni region map (same structure, but also has countries from universities.json)
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

# Opportunity types
OPP_TYPES = {
    "internship":    "💼 Internships",
    "research":      "🔬 Research Programs",
    "competition":   "🏆 Competitions",
    "fellowship":    "🎖 Fellowships",
    "summer_school": "☀️ Summer Schools",
    "exchange":      "🌍 Exchange Programs",
}

# Checklist items
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

# Profile conversation states
(PROFILE_NAME, PROFILE_COUNTRY, PROFILE_LEVEL, PROFILE_GPA,
 PROFILE_FIELD, PROFILE_CAREER, PROFILE_FINANCIAL) = range(100, 107)

# Scholarship search conversation states
CHOOSING_LEVEL, CHOOSING_FIELD, CHOOSING_REGION = range(3)

# University search conversation states
UNI_REGION, UNI_FIELD = range(50, 52)

# ---------------------------------------------------------------------------
# Database setup
# ---------------------------------------------------------------------------
def init_db():
    """Create tables if they don't exist."""
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

# Admin user ID (Scott)
ADMIN_ID = 0  # Replace with your Telegram user ID

def track_user(update: Update, action: str):
    """Log user activity for stats tracking."""
    try:
        user = update.effective_user
        if user:
            conn = sqlite3.connect(DB_PATH)
            c = conn.cursor()
            c.execute(
                "INSERT INTO user_activity (user_id, username, first_name, action) VALUES (?, ?, ?, ?)",
                (user.id, user.username or "", user.first_name or "", action)
            )
            conn.commit()
            conn.close()
    except Exception:
        pass  # Don't let tracking break the bot

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------
def chunk_send(text: str):
    """Split text into chunks of at most CHUNK_SIZE characters."""
    chunks = []
    while text:
        if len(text) <= CHUNK_SIZE:
            chunks.append(text)
            break
        # Try to split at a newline
        idx = text.rfind("\n", 0, CHUNK_SIZE)
        if idx == -1:
            idx = CHUNK_SIZE
        chunks.append(text[:idx])
        text = text[idx:].lstrip("\n")
    return chunks


async def send_chunked(update_or_msg, text: str, **kwargs):
    """Send a potentially long message in chunks."""
    # Accept either Update or Message
    msg = update_or_msg
    if hasattr(msg, "message") and msg.message:
        msg = msg.message
    elif hasattr(msg, "effective_message") and msg.effective_message:
        msg = msg.effective_message
    for chunk in chunk_send(text):
        await msg.reply_text(chunk, disable_web_page_preview=True, **kwargs)


def parse_deadline(deadline_str: str):
    """Try to parse a deadline string into a datetime. Returns None on failure."""
    deadline_str = deadline_str.strip()
    # Skip vague deadlines
    lower = deadline_str.lower()
    if any(w in lower for w in ["varies", "rolling", "ongoing", "varies by"]):
        return None

    # Try common patterns
    patterns = [
        "%B %d, %Y",        # "April 30, 2026"
        "%B %d %Y",
        "%d %B %Y",
        "%B %Y",             # "October 2026"
    ]
    for pat in patterns:
        try:
            return datetime.strptime(deadline_str, pat)
        except ValueError:
            pass

    # "Month each year" → assume current or next year
    m = re.match(r"(\w+)\s+(?:each year|every year)", lower)
    if m:
        month_str = m.group(1).capitalize()
        try:
            month_dt = datetime.strptime(month_str, "%B")
            now = datetime.utcnow()
            candidate = month_dt.replace(year=now.year, day=15)
            if candidate < now:
                candidate = candidate.replace(year=now.year + 1)
            return candidate
        except ValueError:
            pass

    # "Month - Month each year" → pick second month
    m = re.match(r"(\w+)\s*[-–]\s*(\w+)\s+(?:each year|every year)", lower)
    if m:
        month_str = m.group(2).strip().capitalize()
        try:
            month_dt = datetime.strptime(month_str, "%B")
            now = datetime.utcnow()
            candidate = month_dt.replace(year=now.year, day=15)
            if candidate < now:
                candidate = candidate.replace(year=now.year + 1)
            return candidate
        except ValueError:
            pass

    # "Month Day each year" → use day
    m = re.match(r"(\w+)\s+(\d{1,2})\s+each year", lower)
    if m:
        try:
            dt = datetime.strptime(f"{m.group(1).capitalize()} {m.group(2)}", "%B %d")
            now = datetime.utcnow()
            candidate = dt.replace(year=now.year)
            if candidate < now:
                candidate = candidate.replace(year=now.year + 1)
            return candidate
        except ValueError:
            pass

    # "October - December (varies)" → pick middle month
    m = re.match(r"(\w+)\s*[-–]\s*(\w+)", lower)
    if m:
        month_str = m.group(2).strip().capitalize()
        # Remove anything after the month
        month_str = month_str.split()[0] if " " in month_str else month_str
        try:
            month_dt = datetime.strptime(month_str, "%B")
            now = datetime.utcnow()
            candidate = month_dt.replace(year=now.year, day=15)
            if candidate < now:
                candidate = candidate.replace(year=now.year + 1)
            return candidate
        except ValueError:
            pass

    return None


# ---------------------------------------------------------------------------
# /stats — Admin only: view bot usage stats
# ---------------------------------------------------------------------------
async def stats_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        user = update.effective_user
        if not user or user.id != ADMIN_ID:
            msg = update.message or update.callback_query.message
            if msg:
                await msg.reply_text("⛔ Admin only.")
            return
        conn = sqlite3.connect(DB_PATH)
        c = conn.cursor()
        c.execute("SELECT COUNT(DISTINCT user_id) FROM user_activity")
        total_users = c.fetchone()[0]
        c.execute("SELECT COUNT(DISTINCT user_id) FROM user_activity WHERE date(timestamp) = date('now')")
        today_users = c.fetchone()[0]
        c.execute("SELECT COUNT(DISTINCT user_id) FROM user_activity WHERE timestamp >= datetime('now', '-7 days')")
        week_users = c.fetchone()[0]
        c.execute("SELECT action, COUNT(*) as cnt FROM user_activity GROUP BY action ORDER BY cnt DESC LIMIT 10")
        top_features = c.fetchall()
        c.execute("SELECT DISTINCT first_name, username, MAX(timestamp) FROM user_activity GROUP BY user_id ORDER BY MAX(timestamp) DESC LIMIT 10")
        recent_users = c.fetchall()
        c.execute("SELECT COUNT(*) FROM user_activity")
        total_actions = c.fetchone()[0]
        conn.close()

        text = (
            "📊 ScholarFinder Bot Stats\n\n"
            f"👥 Total unique users: {total_users}\n"
            f"📅 Active today: {today_users}\n"
            f"📆 Active this week: {week_users}\n"
            f"⚡ Total actions: {total_actions}\n\n"
            "🔥 Top Features:\n"
        )
        for action, cnt in top_features:
            text += f"  • {action}: {cnt}\n"
        text += "\n👤 Recent Users:\n"
        for fname, uname, ts in recent_users:
            name = fname or uname or "Unknown"
            uname_display = uname if uname else "no username"
            text += f"  • {name} ({uname_display}) — {ts}\n"

        await update.message.reply_text(text)
    except Exception as e:
        logger.error(f"Stats error: {e}")
        if update.message:
            await update.message.reply_text(f"Stats error: {e}")


# ---------------------------------------------------------------------------
# Admin helper: save JSON data back to file
# ---------------------------------------------------------------------------
def _save(name, data):
    """Write data list back to a JSON file."""
    with open(os.path.join(SCRIPT_DIR, name), "w") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)


def is_admin(update: Update) -> bool:
    """Check if the user is the admin."""
    return update.effective_user and update.effective_user.id == ADMIN_ID


# ---------------------------------------------------------------------------
# /admin — Admin panel main menu
# ---------------------------------------------------------------------------
async def admin_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not is_admin(update):
        await update.message.reply_text("⛔ Admin only.")
        return
    keyboard = [
        [InlineKeyboardButton("➕ Add Scholarship", callback_data="adm_add_scholarship")],
        [InlineKeyboardButton("➕ Add Opportunity", callback_data="adm_add_opportunity")],
        [InlineKeyboardButton("➕ Add FAQ", callback_data="adm_add_faq")],
        [InlineKeyboardButton("➕ Add Visa Guide", callback_data="adm_add_visa")],
        [InlineKeyboardButton("➕ Add City Cost", callback_data="adm_add_cost")],
        [InlineKeyboardButton("🗑 Delete Entry", callback_data="adm_delete_menu")],
        [InlineKeyboardButton("📊 Stats", callback_data="adm_stats")],
        [InlineKeyboardButton("📢 Broadcast Message", callback_data="adm_broadcast")],
    ]
    await update.message.reply_text(
        "🔐 Admin Panel\n\nWhat do you want to do?",
        reply_markup=InlineKeyboardMarkup(keyboard)
    )


# ---------------------------------------------------------------------------
# Admin conversation states (offset 200+ to avoid collision)
# ---------------------------------------------------------------------------
(
    ADM_SCHOLARSHIP_NAME, ADM_SCHOLARSHIP_UNI, ADM_SCHOLARSHIP_COUNTRY,
    ADM_SCHOLARSHIP_FIELD, ADM_SCHOLARSHIP_LEVEL, ADM_SCHOLARSHIP_FUNDING,
    ADM_SCHOLARSHIP_DEADLINE, ADM_SCHOLARSHIP_LINK, ADM_SCHOLARSHIP_DESC,
    ADM_OPP_NAME, ADM_OPP_TYPE, ADM_OPP_ORG, ADM_OPP_COUNTRY,
    ADM_OPP_FIELD, ADM_OPP_LEVEL, ADM_OPP_FUNDING, ADM_OPP_DEADLINE,
    ADM_OPP_LINK, ADM_OPP_DESC, ADM_OPP_ELIG,
    ADM_FAQ_Q, ADM_FAQ_A,
    ADM_VISA_COUNTRY, ADM_VISA_TYPE, ADM_VISA_DOCS, ADM_VISA_TIME,
    ADM_VISA_COST, ADM_VISA_LINK, ADM_VISA_TIPS,
    ADM_COST_CITY, ADM_COST_COUNTRY, ADM_COST_RENT, ADM_COST_FOOD,
    ADM_COST_TRANSPORT, ADM_COST_TOTAL,
    ADM_DELETE_TYPE, ADM_DELETE_NUM,
    ADM_BROADCAST_MSG,
) = range(200, 238)


# ---------------------------------------------------------------------------
# Add Scholarship flow
# ---------------------------------------------------------------------------
async def adm_add_scholarship_start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    await query.edit_message_text("➕ Add Scholarship\n\nSend the scholarship NAME:")
    return ADM_SCHOLARSHIP_NAME

async def adm_scholarship_name(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data["adm_schol"] = {"name": update.message.text}
    await update.message.reply_text("University/Organization:")
    return ADM_SCHOLARSHIP_UNI

async def adm_scholarship_uni(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data["adm_schol"]["university"] = update.message.text
    await update.message.reply_text("Country:")
    return ADM_SCHOLARSHIP_COUNTRY

async def adm_scholarship_country(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data["adm_schol"]["country"] = update.message.text
    await update.message.reply_text("Fields (comma separated, e.g. computer science, engineering):")
    return ADM_SCHOLARSHIP_FIELD

async def adm_scholarship_field(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data["adm_schol"]["field"] = [f.strip().lower() for f in update.message.text.split(",")]
    await update.message.reply_text("Levels (comma separated, e.g. undergraduate, masters):")
    return ADM_SCHOLARSHIP_LEVEL

async def adm_scholarship_level(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data["adm_schol"]["level"] = [l.strip().lower() for l in update.message.text.split(",")]
    await update.message.reply_text("Funding (e.g. Full tuition + stipend):")
    return ADM_SCHOLARSHIP_FUNDING

async def adm_scholarship_funding(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data["adm_schol"]["funding"] = update.message.text
    await update.message.reply_text("Deadline (e.g. April 30, 2026):")
    return ADM_SCHOLARSHIP_DEADLINE

async def adm_scholarship_deadline(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data["adm_schol"]["deadline"] = update.message.text
    await update.message.reply_text("Link (URL):")
    return ADM_SCHOLARSHIP_LINK

async def adm_scholarship_link(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data["adm_schol"]["link"] = update.message.text
    await update.message.reply_text("Short description:")
    return ADM_SCHOLARSHIP_DESC

async def adm_scholarship_desc(update: Update, context: ContextTypes.DEFAULT_TYPE):
    global SCHOLARSHIPS
    s = context.user_data["adm_schol"]
    s["description"] = update.message.text
    SCHOLARSHIPS.append(s)
    _save("scholarships.json", SCHOLARSHIPS)
    await update.message.reply_text(
        f"✅ Scholarship added! Total: {len(SCHOLARSHIPS)}\n\n"
        f"Name: {s['name']}\nCountry: {s['country']}\nFunding: {s['funding']}"
    )
    return ConversationHandler.END


# ---------------------------------------------------------------------------
# Add Opportunity flow
# ---------------------------------------------------------------------------
async def adm_add_opp_start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    await query.edit_message_text(
        "➕ Add Opportunity\n\nSend the opportunity NAME:"
    )
    return ADM_OPP_NAME

async def adm_opp_name(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data["adm_opp"] = {"name": update.message.text}
    keyboard = [
        [InlineKeyboardButton(t, callback_data="admopp_" + t)]
        for t in ["internship", "research", "competition", "fellowship", "summer_school", "exchange"]
    ]
    await update.message.reply_text("Type:", reply_markup=InlineKeyboardMarkup(keyboard))
    return ADM_OPP_TYPE

async def adm_opp_type(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    context.user_data["adm_opp"]["type"] = query.data.replace("admopp_", "")
    await query.edit_message_text("Organization:")
    return ADM_OPP_ORG

async def adm_opp_org(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data["adm_opp"]["organization"] = update.message.text
    await update.message.reply_text("Country:")
    return ADM_OPP_COUNTRY

async def adm_opp_country(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data["adm_opp"]["country"] = update.message.text
    await update.message.reply_text("Fields (comma separated):")
    return ADM_OPP_FIELD

async def adm_opp_field(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data["adm_opp"]["field"] = [f.strip().lower() for f in update.message.text.split(",")]
    await update.message.reply_text("Levels (comma separated):")
    return ADM_OPP_LEVEL

async def adm_opp_level(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data["adm_opp"]["level"] = [l.strip().lower() for l in update.message.text.split(",")]
    await update.message.reply_text("Funding/Prize:")
    return ADM_OPP_FUNDING

async def adm_opp_funding(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data["adm_opp"]["funding"] = update.message.text
    await update.message.reply_text("Deadline:")
    return ADM_OPP_DEADLINE

async def adm_opp_deadline(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data["adm_opp"]["deadline"] = update.message.text
    await update.message.reply_text("Link (URL):")
    return ADM_OPP_LINK

async def adm_opp_link(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data["adm_opp"]["link"] = update.message.text
    await update.message.reply_text("Short description:")
    return ADM_OPP_DESC

async def adm_opp_desc(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data["adm_opp"]["description"] = update.message.text
    await update.message.reply_text("Eligibility (who can apply):")
    return ADM_OPP_ELIG

async def adm_opp_elig(update: Update, context: ContextTypes.DEFAULT_TYPE):
    global OPPORTUNITIES
    o = context.user_data["adm_opp"]
    o["eligibility"] = update.message.text
    OPPORTUNITIES.append(o)
    _save("opportunities.json", OPPORTUNITIES)
    await update.message.reply_text(
        f"✅ Opportunity added! Total: {len(OPPORTUNITIES)}\n\n"
        f"Name: {o['name']}\nType: {o['type']}\nOrg: {o['organization']}"
    )
    return ConversationHandler.END


# ---------------------------------------------------------------------------
# Add FAQ flow
# ---------------------------------------------------------------------------
async def adm_add_faq_start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    await query.edit_message_text("➕ Add FAQ\n\nSend the QUESTION:")
    return ADM_FAQ_Q

async def adm_faq_q(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data["adm_faq_q"] = update.message.text
    await update.message.reply_text("Now send the ANSWER:")
    return ADM_FAQ_A

async def adm_faq_a(update: Update, context: ContextTypes.DEFAULT_TYPE):
    global FAQ_DATA
    q = context.user_data["adm_faq_q"]
    a = update.message.text
    FAQ_DATA.append({"question": q, "answer": a, "keywords": q.lower().split()})
    _save("faq_data.json", FAQ_DATA)
    await update.message.reply_text(f"✅ FAQ added! Total: {len(FAQ_DATA)}\n\nQ: {q}")
    return ConversationHandler.END


# ---------------------------------------------------------------------------
# Add Visa Guide flow
# ---------------------------------------------------------------------------
async def adm_add_visa_start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    await query.edit_message_text("➕ Add Visa Guide\n\nSend the COUNTRY name:")
    return ADM_VISA_COUNTRY

async def adm_visa_country(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data["adm_visa"] = {"country": update.message.text}
    await update.message.reply_text("Visa type (e.g. Student Visa, Study Permit):")
    return ADM_VISA_TYPE

async def adm_visa_type(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data["adm_visa"]["visa_type"] = update.message.text
    await update.message.reply_text("Documents needed (one per line):")
    return ADM_VISA_DOCS

async def adm_visa_docs(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data["adm_visa"]["documents"] = [d.strip() for d in update.message.text.split("\n") if d.strip()]
    await update.message.reply_text("Processing time (e.g. 4-8 weeks):")
    return ADM_VISA_TIME

async def adm_visa_time(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data["adm_visa"]["processing_time"] = update.message.text
    await update.message.reply_text("Cost estimate (e.g. $160):")
    return ADM_VISA_COST

async def adm_visa_cost(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data["adm_visa"]["cost"] = update.message.text
    await update.message.reply_text("Embassy/application link:")
    return ADM_VISA_LINK

async def adm_visa_link(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data["adm_visa"]["embassy_link"] = update.message.text
    await update.message.reply_text("Tips for applicants:")
    return ADM_VISA_TIPS

async def adm_visa_tips(update: Update, context: ContextTypes.DEFAULT_TYPE):
    global VISA_DATA
    v = context.user_data["adm_visa"]
    v["tips"] = [t.strip() for t in update.message.text.split("\n") if t.strip()]
    VISA_DATA.append(v)
    _save("visa_data.json", VISA_DATA)
    await update.message.reply_text(f"✅ Visa guide added! Total: {len(VISA_DATA)}\n\nCountry: {v['country']}")
    return ConversationHandler.END


# ---------------------------------------------------------------------------
# Add City Cost flow
# ---------------------------------------------------------------------------
async def adm_add_cost_start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    await query.edit_message_text("➕ Add City Cost\n\nSend the CITY name:")
    return ADM_COST_CITY

async def adm_cost_city(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data["adm_cost"] = {"city": update.message.text}
    await update.message.reply_text("Country:")
    return ADM_COST_COUNTRY

async def adm_cost_country(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data["adm_cost"]["country"] = update.message.text
    await update.message.reply_text("Monthly rent (USD, just the number):")
    return ADM_COST_RENT

async def adm_cost_rent(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data["adm_cost"]["rent"] = int(update.message.text.replace("$", "").strip())
    await update.message.reply_text("Monthly food (USD):")
    return ADM_COST_FOOD

async def adm_cost_food(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data["adm_cost"]["food"] = int(update.message.text.replace("$", "").strip())
    await update.message.reply_text("Monthly transport (USD):")
    return ADM_COST_TRANSPORT

async def adm_cost_transport(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data["adm_cost"]["transport"] = int(update.message.text.replace("$", "").strip())
    await update.message.reply_text("Total monthly estimate (USD):")
    return ADM_COST_TOTAL

async def adm_cost_total(update: Update, context: ContextTypes.DEFAULT_TYPE):
    global COST_DATA
    c = context.user_data["adm_cost"]
    c["total"] = int(update.message.text.replace("$", "").strip())
    COST_DATA.append(c)
    _save("cost_data.json", COST_DATA)
    await update.message.reply_text(
        f"✅ City added! Total: {len(COST_DATA)}\n\n"
        f"City: {c['city']}, {c['country']}\nTotal: ${c['total']}/month"
    )
    return ConversationHandler.END


# ---------------------------------------------------------------------------
# Delete entry flow
# ---------------------------------------------------------------------------
async def adm_delete_menu(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    keyboard = [
        [InlineKeyboardButton("Scholarship", callback_data="admdeltype_scholarship")],
        [InlineKeyboardButton("Opportunity", callback_data="admdeltype_opportunity")],
        [InlineKeyboardButton("FAQ", callback_data="admdeltype_faq")],
        [InlineKeyboardButton("Visa Guide", callback_data="admdeltype_visa")],
        [InlineKeyboardButton("City Cost", callback_data="admdeltype_cost")],
    ]
    await query.edit_message_text(
        "🗑 Delete Entry\n\nWhat type?",
        reply_markup=InlineKeyboardMarkup(keyboard)
    )
    return ADM_DELETE_TYPE

async def adm_delete_type(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    dtype = query.data.replace("admdeltype_", "")
    context.user_data["adm_del_type"] = dtype

    data_map = {
        "scholarship": (SCHOLARSHIPS, "name"),
        "opportunity": (OPPORTUNITIES, "name"),
        "faq": (FAQ_DATA, "question"),
        "visa": (VISA_DATA, "country"),
        "cost": (COST_DATA, "city"),
    }
    data, key = data_map[dtype]
    # Show last 10 entries
    lines = []
    start_idx = max(0, len(data) - 10)
    for i in range(start_idx, len(data)):
        lines.append(f"{i+1}. {data[i].get(key, '?')}")

    text = f"🗑 Delete {dtype}\n\nLast entries:\n" + "\n".join(lines) + "\n\nSend the NUMBER to delete (or /cancel):"
    await query.edit_message_text(text)
    return ADM_DELETE_NUM

async def adm_delete_num(update: Update, context: ContextTypes.DEFAULT_TYPE):
    global SCHOLARSHIPS, OPPORTUNITIES, FAQ_DATA, VISA_DATA, COST_DATA
    try:
        idx = int(update.message.text) - 1
        dtype = context.user_data["adm_del_type"]
        data_map = {
            "scholarship": ("scholarships.json", SCHOLARSHIPS),
            "opportunity": ("opportunities.json", OPPORTUNITIES),
            "faq": ("faq_data.json", FAQ_DATA),
            "visa": ("visa_data.json", VISA_DATA),
            "cost": ("cost_data.json", COST_DATA),
        }
        filename, data = data_map[dtype]
        if 0 <= idx < len(data):
            removed = data.pop(idx)
            _save(filename, data)
            name = removed.get("name", removed.get("question", removed.get("city", removed.get("country", "?"))))
            await update.message.reply_text(f"✅ Deleted: {name}\nRemaining: {len(data)}")
        else:
            await update.message.reply_text("❌ Invalid number. Try again or /cancel")
            return ADM_DELETE_NUM
    except ValueError:
        await update.message.reply_text("❌ Send a number. Try again or /cancel")
        return ADM_DELETE_NUM
    return ConversationHandler.END


# ---------------------------------------------------------------------------
# Broadcast message flow
# ---------------------------------------------------------------------------
async def adm_broadcast_start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    await query.edit_message_text("📢 Broadcast\n\nSend the message to broadcast to ALL users:")
    return ADM_BROADCAST_MSG

async def adm_broadcast_msg(update: Update, context: ContextTypes.DEFAULT_TYPE):
    msg = update.message.text
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute("SELECT DISTINCT user_id FROM user_activity")
    users = c.fetchall()
    conn.close()

    sent = 0
    failed = 0
    for (uid,) in users:
        try:
            await context.bot.send_message(chat_id=uid, text=msg)
            sent += 1
        except Exception:
            failed += 1

    await update.message.reply_text(f"📢 Broadcast complete!\n✅ Sent: {sent}\n❌ Failed: {failed}")
    return ConversationHandler.END


async def adm_cancel(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("Admin action cancelled. Use /admin to try again.")
    return ConversationHandler.END


# ---------------------------------------------------------------------------
# /start — Main menu
# ---------------------------------------------------------------------------
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    track_user(update, "start")
    keyboard = [
        [
            InlineKeyboardButton("🔍 Find Scholarships", callback_data="menu_search"),
            InlineKeyboardButton("🏫 Universities", callback_data="menu_universities"),
        ],
        [
            InlineKeyboardButton("🌍 Opportunities", callback_data="menu_opportunities"),
            InlineKeyboardButton("💰 Cost of Living", callback_data="menu_cost"),
        ],
        [
            InlineKeyboardButton("📝 Essay Help", callback_data="menu_essay"),
            InlineKeyboardButton("🛂 Visa Guide", callback_data="menu_visa"),
        ],
        [
            InlineKeyboardButton("📚 Test Prep", callback_data="menu_tests"),
            InlineKeyboardButton("🤖 Ask a Question", callback_data="menu_ask"),
        ],
        [
            InlineKeyboardButton("✅ My Checklist", callback_data="menu_checklist"),
            InlineKeyboardButton("⏰ My Reminders", callback_data="menu_reminders"),
        ],
        [
            InlineKeyboardButton("👤 My Profile", callback_data="menu_profile"),
            InlineKeyboardButton("⭐ Recommendations", callback_data="menu_recommend"),
        ],
    ]
    text = (
        "🎓 *Welcome to ScholarFinder!*\n"
        "Your complete guide to studying abroad.\n\n"
        f"📊 Database: {len(SCHOLARSHIPS)} scholarships • {len(UNIVERSITIES)} universities • "
        f"{len(OPPORTUNITIES)} opportunities\n\n"
        "Choose what you need:\n\n"
        "_© 2026 Scott Antwi | Alpha Global Minds 🌍_"
    )
    if update.callback_query:
        await update.callback_query.answer()
        await update.callback_query.edit_message_text(
            text, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode="Markdown"
        )
    else:
        await update.message.reply_text(
            text, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode="Markdown"
        )


# ---------------------------------------------------------------------------
# Menu callback router
# ---------------------------------------------------------------------------
async def menu_router(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle main menu button presses."""
    query = update.callback_query
    await query.answer()
    data = query.data
    track_user(update, data.replace("menu_", ""))

    if data == "menu_search":
        # Start scholarship search flow
        keyboard = [[InlineKeyboardButton(level.title(), callback_data="level_" + level)] for level in LEVELS]
        await query.edit_message_text(
            "🔍 *Scholarship Search*\n\nWhat level are you looking for?",
            reply_markup=InlineKeyboardMarkup(keyboard),
            parse_mode="Markdown",
        )
        return CHOOSING_LEVEL

    elif data == "menu_universities":
        keyboard = [[InlineKeyboardButton(r, callback_data="uniregion_" + r)] for r in list(UNI_REGION_MAP.keys()) + ["All"]]
        await query.edit_message_text(
            "🏫 *University Search*\n\nPick a region:",
            reply_markup=InlineKeyboardMarkup(keyboard),
            parse_mode="Markdown",
        )
        return UNI_REGION

    elif data == "menu_opportunities":
        await show_opportunities_menu(query)

    elif data == "menu_cost":
        await query.edit_message_text(
            "💰 *Cost of Living*\n\n"
            "Use these commands:\n"
            "• /cost <city> — Show monthly costs\n"
            "• /compare <city1> vs <city2> — Side-by-side comparison\n\n"
            f"📊 {len(COST_DATA)} cities in database.\n\n"
            "Examples:\n"
            "`/cost London`\n"
            "`/compare Berlin vs Paris`",
            parse_mode="Markdown",
        )

    elif data == "menu_visa":
        await query.edit_message_text(
            "🛂 *Visa Guide*\n\n"
            "Use: /visa <country>\n\n"
            "Available countries: " + ", ".join(sorted(set(v["country"] for v in VISA_DATA))) + "\n\n"
            "Example: `/visa Germany`",
            parse_mode="Markdown",
        )

    elif data == "menu_tests":
        await show_tests_overview(query)

    elif data == "menu_ask":
        await query.edit_message_text(
            "🤖 *Ask a Question*\n\n"
            "Use: /ask <your question>\n\n"
            "Examples:\n"
            "`/ask What GPA do I need?`\n"
            "`/ask How to write personal statement?`\n"
            "`/ask Cheapest countries to study`",
            parse_mode="Markdown",
        )

    elif data == "menu_essay":
        await show_essay_menu(query)

    elif data == "menu_checklist":
        await show_checklist(query.message, update.effective_user.id, edit=query)

    elif data == "menu_reminders":
        await show_reminders(query.message, update.effective_user.id, edit=query)

    elif data == "menu_profile":
        await show_profile(query.message, update.effective_user.id, edit=query)

    elif data == "menu_recommend":
        await show_recommendations(query.message, update.effective_user.id, edit=query)

    return ConversationHandler.END


# ---------------------------------------------------------------------------
# Scholarship search conversation (level → field → region → results)
# ---------------------------------------------------------------------------
async def search_start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Entry via /search command."""
    keyboard = [[InlineKeyboardButton(level.title(), callback_data="level_" + level)] for level in LEVELS]
    await update.message.reply_text(
        "🔍 *Scholarship Search*\n\nWhat level are you looking for?",
        reply_markup=InlineKeyboardMarkup(keyboard),
        parse_mode="Markdown",
    )
    return CHOOSING_LEVEL


async def level_chosen(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    level = query.data.replace("level_", "")
    context.user_data["level"] = level
    keyboard = [[InlineKeyboardButton(f.title(), callback_data="field_" + f)] for f in FIELDS]
    await query.edit_message_text(
        f"Level: *{level.title()}*\n\nWhat field of study?",
        reply_markup=InlineKeyboardMarkup(keyboard),
        parse_mode="Markdown",
    )
    return CHOOSING_FIELD


async def field_chosen(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    field = query.data.replace("field_", "")
    context.user_data["field"] = field
    keyboard = [[InlineKeyboardButton(r, callback_data="region_" + r)] for r in REGIONS]
    await query.edit_message_text(
        f"Level: *{context.user_data['level'].title()}*\n"
        f"Field: *{field.title()}*\n\nPreferred region?",
        reply_markup=InlineKeyboardMarkup(keyboard),
        parse_mode="Markdown",
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
        text = "❌ No exact matches found. Try broadening your search with /search or /start"
    else:
        text = f"🎓 Found *{len(results)}* scholarship(s) for {level.title()} in {field.title()} ({region}):\n\n"
        for s in results:
            text += f"📌 *{s['name']}*\n"
            text += f"🏫 {s['university']}\n"
            text += f"🌍 {s['country']} | 💰 {s['funding']}\n"
            text += f"📅 Deadline: {s['deadline']}\n"
            text += f"ℹ️ {s['description']}\n"
            text += f"🔗 {s['link']}\n\n"
        text += "Search again: /search | Main menu: /start"

    # Send as chunks if needed
    chunks = chunk_send(text)
    if len(chunks) == 1:
        await query.edit_message_text(chunks[0], parse_mode="Markdown", disable_web_page_preview=True)
    else:
        await query.edit_message_text(chunks[0], parse_mode="Markdown", disable_web_page_preview=True)
        for ch in chunks[1:]:
            await query.message.reply_text(ch, parse_mode="Markdown", disable_web_page_preview=True)
    return ConversationHandler.END


# ---------------------------------------------------------------------------
# /all — List all scholarships
# ---------------------------------------------------------------------------
async def all_scholarships(update: Update, context: ContextTypes.DEFAULT_TYPE):
    lines = [f"📋 All {len(SCHOLARSHIPS)} scholarships:\n"]
    for i, s in enumerate(SCHOLARSHIPS):
        lines.append(f"{i + 1}. {s['name']} ({s['country']}) — {s['funding']}")

    msg = ""
    for line in lines:
        if len(msg) + len(line) + 1 > CHUNK_SIZE:
            await update.message.reply_text(msg, disable_web_page_preview=True)
            msg = ""
        msg += line + "\n"
    if msg:
        msg += "\n💡 Use /subscribe <number> to get deadline reminders\nUse /search to filter | /start for menu"
        await update.message.reply_text(msg, disable_web_page_preview=True)


# ---------------------------------------------------------------------------
# University search (region → field → results)
# ---------------------------------------------------------------------------
async def universities_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    keyboard = [[InlineKeyboardButton(r, callback_data="uniregion_" + r)] for r in list(UNI_REGION_MAP.keys()) + ["All"]]
    await update.message.reply_text(
        "🏫 *University Search*\n\nPick a region:",
        reply_markup=InlineKeyboardMarkup(keyboard),
        parse_mode="Markdown",
    )
    return UNI_REGION


async def uni_region_chosen(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    region = query.data.replace("uniregion_", "")
    context.user_data["uni_region"] = region
    uni_fields = sorted(set(f for u in UNIVERSITIES for f in u.get("fields", [])))
    # Group into rows of 2
    keyboard = []
    row = []
    for f in uni_fields:
        row.append(InlineKeyboardButton(f.title(), callback_data="unifield_" + f))
        if len(row) == 2:
            keyboard.append(row)
            row = []
    if row:
        keyboard.append(row)
    await query.edit_message_text(
        f"🏫 Region: *{region}*\n\nPick a field:",
        reply_markup=InlineKeyboardMarkup(keyboard),
        parse_mode="Markdown",
    )
    return UNI_FIELD


async def uni_field_chosen(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    field = query.data.replace("unifield_", "")
    region = context.user_data.get("uni_region", "All")

    results = []
    for u in UNIVERSITIES:
        if field not in u.get("fields", []) and field != "any":
            continue
        if region != "All":
            region_countries = UNI_REGION_MAP.get(region, [])
            if u["country"] not in region_countries:
                continue
        results.append(u)

    if not results:
        text = "❌ No universities found. Try different filters.\n\n/universities to search again"
    else:
        # Sort by ranking tier
        tier_order = {"top10": 0, "top50": 1, "top100": 2, "top200": 3, "other": 4}
        results.sort(key=lambda x: tier_order.get(x.get("ranking_tier", "other"), 5))
        text = f"🏫 Found *{len(results)}* universities for {field.title()} in {region}:\n\n"
        for u in results:
            tier = u.get("ranking_tier", "").replace("top", "Top ").title()
            text += f"🎓 *{u['name']}*\n"
            text += f"🌍 {u['country']} | 🏆 {tier}\n"
            text += f"💰 Tuition: {u.get('tuition', 'N/A')}\n"
            text += f"📝 {u.get('notes', '')}\n"
            text += f"🔗 {u.get('website', '')}\n\n"
        text += "Search again: /universities | Menu: /start"

    chunks = chunk_send(text)
    await query.edit_message_text(chunks[0], parse_mode="Markdown", disable_web_page_preview=True)
    for ch in chunks[1:]:
        await query.message.reply_text(ch, parse_mode="Markdown", disable_web_page_preview=True)
    return ConversationHandler.END


# ---------------------------------------------------------------------------
# Opportunities
# ---------------------------------------------------------------------------
async def show_opportunities_menu(query_or_msg):
    """Show opportunity type buttons."""
    keyboard = [
        [InlineKeyboardButton(label, callback_data="opp_" + key)]
        for key, label in OPP_TYPES.items()
    ]
    keyboard.append([InlineKeyboardButton("🔙 Back to Menu", callback_data="back_start")])
    text = (
        "🌍 *Opportunities Database*\n\n"
        f"📊 {len(OPPORTUNITIES)} opportunities across 6 categories.\n\n"
        "Pick a category:"
    )
    if hasattr(query_or_msg, "edit_message_text"):
        await query_or_msg.edit_message_text(text, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode="Markdown")
    else:
        await query_or_msg.reply_text(text, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode="Markdown")


async def opportunities_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await show_opportunities_menu(update.message)


async def opp_type_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    opp_type = query.data.replace("opp_", "")
    label = OPP_TYPES.get(opp_type, opp_type.title())

    items = [o for o in OPPORTUNITIES if o.get("type") == opp_type]
    if not items:
        await query.edit_message_text(f"No {label} found.")
        return

    text = f"{label} ({len(items)} found):\n\n"
    for o in items:
        text += f"📌 *{o['name']}*\n"
        text += f"🏢 {o['organization']} | 🌍 {o['country']}\n"
        text += f"🎯 {o.get('field', 'Any').title()} | 📚 {o.get('level', 'Any').title()}\n"
        text += f"💰 {o.get('funding', 'N/A')}\n"
        text += f"📅 {o.get('deadline', 'N/A')}\n"
        text += f"ℹ️ {o.get('description', '')}\n"
        text += f"🔗 {o.get('link', '')}\n\n"
    text += "Browse more: /opportunities | Menu: /start"

    chunks = chunk_send(text)
    await query.edit_message_text(chunks[0], parse_mode="Markdown", disable_web_page_preview=True)
    for ch in chunks[1:]:
        await query.message.reply_text(ch, parse_mode="Markdown", disable_web_page_preview=True)


# Shortcut commands
async def _opp_shortcut(update: Update, context: ContextTypes.DEFAULT_TYPE, opp_type: str):
    label = OPP_TYPES.get(opp_type, opp_type.title())
    items = [o for o in OPPORTUNITIES if o.get("type") == opp_type]
    if not items:
        await update.message.reply_text(f"No {label} found.")
        return
    text = f"{label} ({len(items)} found):\n\n"
    for o in items:
        text += f"📌 *{o['name']}*\n"
        text += f"🏢 {o['organization']} | 🌍 {o['country']}\n"
        text += f"💰 {o.get('funding', 'N/A')} | 📅 {o.get('deadline', 'N/A')}\n"
        text += f"ℹ️ {o.get('description', '')}\n"
        text += f"🔗 {o.get('link', '')}\n\n"
    text += "More: /opportunities | Menu: /start"
    await send_chunked(update, text, parse_mode="Markdown")

async def internships_cmd(update, context): await _opp_shortcut(update, context, "internship")
async def research_cmd(update, context):    await _opp_shortcut(update, context, "research")
async def competitions_cmd(update, context): await _opp_shortcut(update, context, "competition")
async def fellowships_cmd(update, context): await _opp_shortcut(update, context, "fellowship")
async def summer_cmd(update, context):      await _opp_shortcut(update, context, "summer_school")
async def exchange_cmd(update, context):    await _opp_shortcut(update, context, "exchange")


# ---------------------------------------------------------------------------
# Cost of living
# ---------------------------------------------------------------------------
async def cost_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not context.args:
        cities = ", ".join(sorted(c["city"] for c in COST_DATA))
        await update.message.reply_text(
            "💰 *Cost of Living*\n\n"
            "Usage: `/cost <city>`\n\n"
            f"Available cities:\n{cities}\n\n"
            "Or compare: `/compare Berlin vs Paris`",
            parse_mode="Markdown",
        )
        return

    city_name = " ".join(context.args).strip().lower()
    city = next((c for c in COST_DATA if c["city"].lower() == city_name), None)
    if not city:
        # Fuzzy match
        best = max(COST_DATA, key=lambda c: SequenceMatcher(None, c["city"].lower(), city_name).ratio())
        if SequenceMatcher(None, best["city"].lower(), city_name).ratio() > 0.6:
            city = best
        else:
            await update.message.reply_text(f"❌ City '{' '.join(context.args)}' not found. Use /cost to see available cities.")
            return

    text = (
        f"💰 *Cost of Living in {city['city']}, {city['country']}*\n"
        f"({city.get('currency_note', 'USD/month')})\n\n"
        f"🏠 Rent: ${city['rent']}\n"
        f"🍽 Food: ${city['food']}\n"
        f"🚇 Transport: ${city['transport']}\n"
        f"📱 Internet/Phone: ${city['internet_phone']}\n"
        f"🎭 Entertainment: ${city['entertainment']}\n"
        f"{'─' * 25}\n"
        f"💵 *Total: ${city['total']}/month*\n\n"
        f"💡 Tips: {city.get('tips', 'N/A')}"
    )
    await update.message.reply_text(text, parse_mode="Markdown")


async def compare_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not context.args:
        await update.message.reply_text(
            "Usage: `/compare <city1> vs <city2>`\n\nExample: `/compare Berlin vs Paris`",
            parse_mode="Markdown",
        )
        return

    raw = " ".join(context.args)
    parts = re.split(r"\s+vs\.?\s+", raw, flags=re.IGNORECASE)
    if len(parts) != 2:
        await update.message.reply_text("Usage: `/compare <city1> vs <city2>`", parse_mode="Markdown")
        return

    def find_city(name):
        name = name.strip().lower()
        c = next((c for c in COST_DATA if c["city"].lower() == name), None)
        if not c:
            best = max(COST_DATA, key=lambda x: SequenceMatcher(None, x["city"].lower(), name).ratio())
            if SequenceMatcher(None, best["city"].lower(), name).ratio() > 0.6:
                return best
        return c

    c1, c2 = find_city(parts[0]), find_city(parts[1])
    if not c1:
        await update.message.reply_text(f"❌ City '{parts[0].strip()}' not found.")
        return
    if not c2:
        await update.message.reply_text(f"❌ City '{parts[1].strip()}' not found.")
        return

    diff = c1["total"] - c2["total"]
    cheaper = c2["city"] if diff > 0 else c1["city"]
    text = (
        f"💰 *{c1['city']} vs {c2['city']}* (USD/month)\n\n"
        f"{'Category':<16} {'🏙 ' + c1['city']:<14} {'🏙 ' + c2['city']:<14}\n"
        f"{'─' * 40}\n"
        f"{'🏠 Rent':<16} ${c1['rent']:<13} ${c2['rent']:<13}\n"
        f"{'🍽 Food':<16} ${c1['food']:<13} ${c2['food']:<13}\n"
        f"{'🚇 Transport':<16} ${c1['transport']:<13} ${c2['transport']:<13}\n"
        f"{'📱 Phone/Net':<16} ${c1['internet_phone']:<13} ${c2['internet_phone']:<13}\n"
        f"{'🎭 Fun':<16} ${c1['entertainment']:<13} ${c2['entertainment']:<13}\n"
        f"{'─' * 40}\n"
        f"{'💵 TOTAL':<16} *${c1['total']}*{'':>8} *${c2['total']}*\n\n"
        f"📊 {cheaper} is *${abs(diff)}* cheaper per month\n"
        f"📊 That's *${abs(diff) * 12}* cheaper per year!"
    )
    await update.message.reply_text(text, parse_mode="Markdown")


# ---------------------------------------------------------------------------
# Visa guide
# ---------------------------------------------------------------------------
async def visa_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not context.args:
        countries = ", ".join(sorted(v["country"] for v in VISA_DATA))
        await update.message.reply_text(
            "🛂 *Visa Guide*\n\n"
            "Usage: `/visa <country>`\n\n"
            f"Available: {countries}",
            parse_mode="Markdown",
        )
        return

    country_name = " ".join(context.args).strip().lower()
    visa = next((v for v in VISA_DATA if v["country"].lower() == country_name), None)
    if not visa:
        # fuzzy
        best = max(VISA_DATA, key=lambda v: SequenceMatcher(None, v["country"].lower(), country_name).ratio())
        if SequenceMatcher(None, best["country"].lower(), country_name).ratio() > 0.6:
            visa = best
        else:
            await update.message.reply_text(f"❌ Country '{' '.join(context.args)}' not found. Use /visa to see available countries.")
            return

    docs = "\n".join(f"  • {d}" for d in visa.get("documents", []))
    text = (
        f"🛂 *Visa Guide: {visa['country']}*\n\n"
        f"📋 Visa Type: {visa['visa_type']}\n\n"
        f"📄 Documents Required:\n{docs}\n\n"
        f"⏱ Processing Time: {visa['processing_time']}\n"
        f"💵 Cost: {visa['cost_estimate']}\n"
        f"🏛 Embassy: {visa.get('embassy_link', 'N/A')}\n\n"
        f"💡 Tips: {visa.get('tips', 'N/A')}"
    )
    await send_chunked(update, text, parse_mode="Markdown")


# ---------------------------------------------------------------------------
# Test prep
# ---------------------------------------------------------------------------
async def show_tests_overview(query_or_msg):
    """Show overview of all tests."""
    text = "📚 *Test Prep Overview*\n\n"
    for key, data in TEST_PREP.items():
        name = key.upper()
        cost = data.get("cost", "N/A")
        text += f"📝 *{name}* — {data.get('full_name', '')}\n"
        text += f"   💵 Cost: {cost}\n"
        text += f"   ⏱ Valid: {data.get('validity', 'N/A')}\n\n"
    text += "Use `/test <name>` for detailed info.\nExample: `/test ielts`"

    if hasattr(query_or_msg, "edit_message_text"):
        await query_or_msg.edit_message_text(text, parse_mode="Markdown")
    else:
        await query_or_msg.reply_text(text, parse_mode="Markdown")


async def tests_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await show_tests_overview(update.message)


async def test_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not context.args:
        await update.message.reply_text(
            "Usage: `/test <name>`\n\nAvailable: " + ", ".join(k.upper() for k in TEST_PREP.keys()),
            parse_mode="Markdown",
        )
        return

    name = context.args[0].lower()
    data = TEST_PREP.get(name)
    if not data:
        await update.message.reply_text(
            f"❌ Test '{name}' not found.\nAvailable: " + ", ".join(k.upper() for k in TEST_PREP.keys())
        )
        return

    text = f"📚 *{name.upper()} — {data.get('full_name', '')}*\n\n"

    if "types" in data:
        text += "📋 Types: " + ", ".join(data["types"]) + "\n\n"

    if "format" in data:
        text += "📐 *Format:*\n"
        for section, desc in data["format"].items():
            text += f"  • {section}: {desc}\n"
        text += "\n"

    text += f"📊 Scoring: {data.get('scoring', 'N/A')}\n\n"

    if "common_requirements" in data:
        text += "🎯 *Common Requirements:*\n"
        for level, score in data["common_requirements"].items():
            text += f"  • {level}: {score}\n"
        text += "\n"

    text += f"💵 Cost: {data.get('cost', 'N/A')}\n"
    text += f"⏱ Validity: {data.get('validity', 'N/A')}\n"
    text += f"📍 Test Centers (Ghana): {data.get('test_centers_ghana', 'N/A')}\n\n"

    if "free_prep_resources" in data:
        text += "📖 *Free Prep Resources:*\n"
        for r in data["free_prep_resources"]:
            text += f"  • {r}\n"
        text += "\n"

    if "tips" in data:
        text += "💡 *Tips:*\n"
        for t in data["tips"]:
            text += f"  • {t}\n"

    await send_chunked(update, text, parse_mode="Markdown")


# ---------------------------------------------------------------------------
# AI Q&A — keyword matching
# ---------------------------------------------------------------------------
async def ask_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not context.args:
        topics = sorted(set(faq["question"] for faq in FAQ_DATA))
        sample = topics[:10]
        text = (
            "🤖 *Ask a Question*\n\n"
            "Usage: `/ask <your question>`\n\n"
            "Sample topics:\n" + "\n".join(f"  • {t}" for t in sample) +
            f"\n\n📊 {len(FAQ_DATA)} Q&A entries in database."
        )
        await update.message.reply_text(text, parse_mode="Markdown")
        return

    question = " ".join(context.args).lower()
    q_words = set(re.findall(r'\w+', question))

    # Score each FAQ by word overlap
    scored = []
    for faq in FAQ_DATA:
        kw_set = set(w.lower() for w in faq.get("keywords", []))
        # Also add words from the question text
        q_set = set(re.findall(r'\w+', faq["question"].lower()))
        combined = kw_set | q_set
        overlap = len(q_words & combined)
        if overlap > 0:
            scored.append((overlap, faq))

    scored.sort(key=lambda x: -x[0])

    if not scored or scored[0][0] < 1:
        topics = sorted(set(faq["question"] for faq in FAQ_DATA))[:15]
        await update.message.reply_text(
            "❌ I couldn't find a good match for your question.\n\n"
            "Try asking about these topics:\n" + "\n".join(f"  • {t}" for t in topics) +
            "\n\nOr browse: /start"
        )
        return

    # Show top 1-3 matches
    top = scored[:3]
    text = "🤖 *Here's what I found:*\n\n"
    for score, faq in top:
        text += f"❓ *{faq['question']}*\n\n{faq['answer']}\n\n{'─' * 30}\n\n"

    text += "Ask another: /ask <question> | Menu: /start"
    await send_chunked(update, text, parse_mode="Markdown")


# ---------------------------------------------------------------------------
# Essay help
# ---------------------------------------------------------------------------
async def show_essay_menu(query_or_msg):
    keyboard = [
        [InlineKeyboardButton("📝 Personal Statement", callback_data="essay_personal_statement")],
        [InlineKeyboardButton("📋 SOP Structure", callback_data="essay_sop")],
        [InlineKeyboardButton("📄 CV Format", callback_data="essay_cv_format")],
        [InlineKeyboardButton("📑 Activity List Tips", callback_data="essay_activity_list")],
        [InlineKeyboardButton("💡 Essay Dos & Don'ts", callback_data="essay_dos_and_donts")],
        [InlineKeyboardButton("🔑 Power Words", callback_data="essay_power_words")],
        [InlineKeyboardButton("🔙 Back to Menu", callback_data="back_start")],
    ]
    text = "📝 *Essay & SOP Help*\n\nChoose a guide:"
    if hasattr(query_or_msg, "edit_message_text"):
        await query_or_msg.edit_message_text(text, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode="Markdown")
    else:
        await query_or_msg.reply_text(text, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode="Markdown")


async def essay_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await show_essay_menu(update.message)


async def essay_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    key = query.data.replace("essay_", "")
    guide = ESSAY_GUIDES.get(key)
    if not guide:
        await query.edit_message_text("Guide not found.")
        return

    text = f"*{guide['title']}*\n\n{guide['content']}\n\n📝 More guides: /essay | Menu: /start"
    chunks = chunk_send(text)
    await query.edit_message_text(chunks[0], parse_mode="Markdown")
    for ch in chunks[1:]:
        await query.message.reply_text(ch, parse_mode="Markdown")


# ---------------------------------------------------------------------------
# Application checklist
# ---------------------------------------------------------------------------
async def show_checklist(message, user_id, edit=None):
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    items_text = "✅ *Application Checklist*\n\n"
    for i, item in enumerate(CHECKLIST_ITEMS):
        c.execute("SELECT checked FROM checklist_progress WHERE user_id=? AND item_index=?", (user_id, i))
        row = c.fetchone()
        checked = row[0] if row else 0
        icon = "✅" if checked else "⬜"
        items_text += f"{i + 1}. {icon} {item}\n"
    conn.close()

    items_text += "\n💡 Toggle: /check <number>\nExample: `/check 1`"

    if edit:
        await edit.edit_message_text(items_text, parse_mode="Markdown")
    else:
        await message.reply_text(items_text, parse_mode="Markdown")


async def checklist_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await show_checklist(update.message, update.effective_user.id)


async def check_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not context.args:
        await update.message.reply_text("Usage: `/check <number>`\nExample: `/check 1`", parse_mode="Markdown")
        return

    try:
        idx = int(context.args[0]) - 1
    except ValueError:
        await update.message.reply_text("Please provide a valid number.")
        return

    if idx < 0 or idx >= len(CHECKLIST_ITEMS):
        await update.message.reply_text(f"Number must be 1-{len(CHECKLIST_ITEMS)}.")
        return

    user_id = update.effective_user.id
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute("SELECT checked FROM checklist_progress WHERE user_id=? AND item_index=?", (user_id, idx))
    row = c.fetchone()
    new_val = 0 if (row and row[0]) else 1
    c.execute(
        "INSERT OR REPLACE INTO checklist_progress (user_id, item_index, checked) VALUES (?, ?, ?)",
        (user_id, idx, new_val),
    )
    conn.commit()
    conn.close()

    icon = "✅" if new_val else "⬜"
    await update.message.reply_text(
        f"{icon} *{CHECKLIST_ITEMS[idx]}* {'checked' if new_val else 'unchecked'}!\n\nSee full list: /checklist",
        parse_mode="Markdown",
    )


# ---------------------------------------------------------------------------
# Deadline reminders / subscriptions
# ---------------------------------------------------------------------------
async def show_reminders(message, user_id, edit=None):
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute("SELECT scholarship_index FROM subscriptions WHERE user_id=?", (user_id,))
    rows = c.fetchall()
    conn.close()

    if not rows:
        text = "⏰ *My Reminders*\n\nYou have no subscriptions yet.\n\nUse `/subscribe <number>` (number from /all list) to get deadline reminders."
    else:
        text = "⏰ *My Deadline Reminders*\n\n"
        for (idx,) in rows:
            if 0 <= idx < len(SCHOLARSHIPS):
                s = SCHOLARSHIPS[idx]
                deadline_dt = parse_deadline(s["deadline"])
                days_info = ""
                if deadline_dt:
                    days = (deadline_dt - datetime.utcnow()).days
                    if days > 0:
                        days_info = f" ({days} days left)"
                    elif days == 0:
                        days_info = " (TODAY!)"
                    else:
                        days_info = " (PASSED)"
                text += f"  {idx + 1}. {s['name']} — {s['deadline']}{days_info}\n"
        text += "\n💡 Unsubscribe: `/unsubscribe <number>`"

    if edit:
        await edit.edit_message_text(text, parse_mode="Markdown")
    else:
        await message.reply_text(text, parse_mode="Markdown")


async def reminders_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await show_reminders(update.message, update.effective_user.id)


async def subscribe_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not context.args:
        await update.message.reply_text(
            "Usage: `/subscribe <number>`\n"
            "Use the number from the /all list.\n"
            "Example: `/subscribe 4`",
            parse_mode="Markdown",
        )
        return

    try:
        idx = int(context.args[0]) - 1
    except ValueError:
        await update.message.reply_text("Please provide a valid number.")
        return

    if idx < 0 or idx >= len(SCHOLARSHIPS):
        await update.message.reply_text(f"Number must be 1-{len(SCHOLARSHIPS)}.")
        return

    user_id = update.effective_user.id
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    try:
        c.execute("INSERT INTO subscriptions (user_id, scholarship_index) VALUES (?, ?)", (user_id, idx))
        conn.commit()
        s = SCHOLARSHIPS[idx]
        await update.message.reply_text(
            f"✅ Subscribed to deadline reminders for:\n*{s['name']}*\nDeadline: {s['deadline']}\n\nSee all: /reminders",
            parse_mode="Markdown",
        )
    except sqlite3.IntegrityError:
        await update.message.reply_text("You're already subscribed to this scholarship.")
    finally:
        conn.close()


async def unsubscribe_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not context.args:
        await update.message.reply_text(
            "Usage: `/unsubscribe <number>`\nExample: `/unsubscribe 4`",
            parse_mode="Markdown",
        )
        return

    try:
        idx = int(context.args[0]) - 1
    except ValueError:
        await update.message.reply_text("Please provide a valid number.")
        return

    user_id = update.effective_user.id
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute("DELETE FROM subscriptions WHERE user_id=? AND scholarship_index=?", (user_id, idx))
    deleted = c.rowcount
    conn.commit()
    conn.close()

    if deleted:
        await update.message.reply_text(f"✅ Unsubscribed from scholarship #{idx + 1}.\n\nSee remaining: /reminders")
    else:
        await update.message.reply_text("You weren't subscribed to that scholarship.")


# ---------------------------------------------------------------------------
# Student profile
# ---------------------------------------------------------------------------
async def show_profile(message, user_id, edit=None):
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute("SELECT * FROM user_profiles WHERE user_id=?", (user_id,))
    row = c.fetchone()
    conn.close()

    if not row:
        text = (
            "👤 *My Profile*\n\n"
            "No profile set up yet.\n\n"
            "Use /setprofile to create your profile and get personalized recommendations!"
        )
    else:
        text = (
            "👤 *My Profile*\n\n"
            f"📛 Name: {row[1] or 'Not set'}\n"
            f"🌍 Country: {row[2] or 'Not set'}\n"
            f"📚 Education Level: {row[3] or 'Not set'}\n"
            f"📊 GPA: {row[4] or 'Not set'}\n"
            f"🎯 Field of Interest: {row[5] or 'Not set'}\n"
            f"🚀 Career Goals: {row[6] or 'Not set'}\n"
            f"💰 Financial Need: {row[7] or 'Not set'}\n\n"
            "Update: /setprofile | Recommendations: /recommend"
        )

    if edit:
        await edit.edit_message_text(text, parse_mode="Markdown")
    else:
        await message.reply_text(text, parse_mode="Markdown")


async def profile_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await show_profile(update.message, update.effective_user.id)


async def setprofile_start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "👤 *Let's set up your profile!*\n\n"
        "What's your name?",
        parse_mode="Markdown",
    )
    return PROFILE_NAME


async def profile_name(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data["p_name"] = update.message.text.strip()
    await update.message.reply_text("🌍 What country are you from?")
    return PROFILE_COUNTRY


async def profile_country(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data["p_country"] = update.message.text.strip()
    keyboard = [
        [InlineKeyboardButton("Undergraduate", callback_data="plvl_undergraduate")],
        [InlineKeyboardButton("Masters", callback_data="plvl_masters")],
        [InlineKeyboardButton("PhD", callback_data="plvl_phd")],
    ]
    await update.message.reply_text(
        "📚 What education level are you seeking?",
        reply_markup=InlineKeyboardMarkup(keyboard),
    )
    return PROFILE_LEVEL


async def profile_level(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    context.user_data["p_level"] = query.data.replace("plvl_", "")
    await query.edit_message_text("📊 What's your GPA? (e.g., 3.5/4.0 or 3.2)")
    return PROFILE_GPA


async def profile_gpa(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data["p_gpa"] = update.message.text.strip()
    keyboard = [
        [InlineKeyboardButton(f.title(), callback_data="pfield_" + f)]
        for f in FIELDS
    ]
    await update.message.reply_text(
        "🎯 What's your field of interest?",
        reply_markup=InlineKeyboardMarkup(keyboard),
    )
    return PROFILE_FIELD


async def profile_field(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    context.user_data["p_field"] = query.data.replace("pfield_", "")
    await query.edit_message_text("🚀 What are your career goals? (brief description)")
    return PROFILE_CAREER


async def profile_career(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data["p_career"] = update.message.text.strip()
    keyboard = [
        [InlineKeyboardButton("Yes", callback_data="pfin_yes")],
        [InlineKeyboardButton("No", callback_data="pfin_no")],
    ]
    await update.message.reply_text(
        "💰 Do you have financial need? (need scholarship funding)",
        reply_markup=InlineKeyboardMarkup(keyboard),
    )
    return PROFILE_FINANCIAL


async def profile_financial(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    fin = query.data.replace("pfin_", "")
    ud = context.user_data

    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute(
        """INSERT OR REPLACE INTO user_profiles
           (user_id, name, country, education_level, gpa, field_of_interest, career_goals, financial_need)
           VALUES (?, ?, ?, ?, ?, ?, ?, ?)""",
        (
            update.effective_user.id,
            ud.get("p_name", ""),
            ud.get("p_country", ""),
            ud.get("p_level", ""),
            ud.get("p_gpa", ""),
            ud.get("p_field", ""),
            ud.get("p_career", ""),
            fin,
        ),
    )
    conn.commit()
    conn.close()

    await query.edit_message_text(
        "✅ *Profile saved!*\n\n"
        f"📛 {ud.get('p_name')}\n"
        f"🌍 {ud.get('p_country')}\n"
        f"📚 {ud.get('p_level', '').title()}\n"
        f"📊 GPA: {ud.get('p_gpa')}\n"
        f"🎯 {ud.get('p_field', '').title()}\n"
        f"💰 Financial need: {fin}\n\n"
        "Get personalized picks: /recommend\n"
        "View: /profile | Menu: /start",
        parse_mode="Markdown",
    )
    return ConversationHandler.END


async def profile_cancel(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("Profile setup cancelled. Use /setprofile to try again.")
    return ConversationHandler.END


# ---------------------------------------------------------------------------
# Personalized recommendations
# ---------------------------------------------------------------------------
async def show_recommendations(message, user_id, edit=None):
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute("SELECT * FROM user_profiles WHERE user_id=?", (user_id,))
    row = c.fetchone()
    conn.close()

    if not row:
        text = "⭐ *Personalized Recommendations*\n\nPlease set up your profile first!\nUse /setprofile"
        if edit:
            await edit.edit_message_text(text, parse_mode="Markdown")
        else:
            await message.reply_text(text, parse_mode="Markdown")
        return

    _, name, country, level, gpa, field, career, fin_need = row
    text = f"⭐ *Recommendations for {name}*\n\n"

    # --- Scholarships ---
    def score_scholarship(s):
        sc = 0
        if level and level in s.get("level", []):
            sc += 3
        if field and field != "any":
            if field in s.get("field", []) or "any" in s.get("field", []):
                sc += 2
        # Country/region bonus
        if country:
            cl = country.lower()
            for region, countries in REGION_MAP.items():
                if cl in [c.lower() for c in countries]:
                    if s["country"] in countries or s["country"] == "Multiple":
                        sc += 1
                    break
        if fin_need == "yes" and "full" in s.get("funding", "").lower():
            sc += 1
        return sc

    scored_scholarships = [(score_scholarship(s), i, s) for i, s in enumerate(SCHOLARSHIPS)]
    scored_scholarships.sort(key=lambda x: -x[0])
    top_schol = [x for x in scored_scholarships if x[0] > 0][:5]

    if top_schol:
        text += "🎓 *Top 5 Scholarships for You:*\n\n"
        for sc, idx, s in top_schol:
            text += f"  📌 *{s['name']}*\n"
            text += f"     {s['country']} | {s['funding']} | {s['deadline']}\n\n"
    else:
        text += "🎓 No strong scholarship matches. Try broadening your profile.\n\n"

    # --- Universities ---
    def score_uni(u):
        sc = 0
        if field and field != "any" and field in u.get("fields", []):
            sc += 2
        if fin_need == "yes":
            if u.get("tuition") in ("free", "low"):
                sc += 2
            elif u.get("tuition") == "medium":
                sc += 1
        tier = u.get("ranking_tier", "other")
        if tier in ("top10", "top50"):
            sc += 1
        return sc

    scored_unis = [(score_uni(u), u) for u in UNIVERSITIES]
    scored_unis.sort(key=lambda x: -x[0])
    top_unis = [x for x in scored_unis if x[0] > 0][:3]

    if top_unis:
        text += "🏫 *Top 3 Universities for You:*\n\n"
        for sc, u in top_unis:
            text += f"  🎓 *{u['name']}*\n"
            text += f"     {u['country']} | Tuition: {u.get('tuition', 'N/A')} | {u.get('ranking_tier', '').replace('top', 'Top ')}\n\n"

    # --- Opportunities ---
    def score_opp(o):
        sc = 0
        if level and level == o.get("level", ""):
            sc += 2
        if field and field != "any" and field in o.get("field", ""):
            sc += 2
        return sc

    scored_opps = [(score_opp(o), o) for o in OPPORTUNITIES]
    scored_opps.sort(key=lambda x: -x[0])
    top_opps = [x for x in scored_opps if x[0] > 0][:3]

    if top_opps:
        text += "🌍 *Top 3 Opportunities for You:*\n\n"
        for sc, o in top_opps:
            text += f"  📌 *{o['name']}*\n"
            text += f"     {o['organization']} | {o.get('funding', 'N/A')}\n\n"

    text += "Update profile: /setprofile | Menu: /start"

    if edit:
        chunks = chunk_send(text)
        await edit.edit_message_text(chunks[0], parse_mode="Markdown", disable_web_page_preview=True)
        for ch in chunks[1:]:
            await edit.message.reply_text(ch, parse_mode="Markdown", disable_web_page_preview=True)
    else:
        await send_chunked(message, text, parse_mode="Markdown")


async def recommend_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await show_recommendations(update.message, update.effective_user.id)


# ---------------------------------------------------------------------------
# /help — All commands
# ---------------------------------------------------------------------------
async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = (
        "📖 *ScholarFinder — All Commands*\n\n"
        "🔍 *Scholarship Search:*\n"
        "  /start — Main menu\n"
        "  /search — Find scholarships (level → field → region)\n"
        "  /all — List all scholarships\n\n"
        "🏫 *Universities:*\n"
        "  /universities — Search universities\n\n"
        "🌍 *Opportunities:*\n"
        "  /opportunities — Browse by category\n"
        "  /internships — Internships\n"
        "  /research — Research programs\n"
        "  /competitions — Competitions\n"
        "  /fellowships — Fellowships\n"
        "  /summer — Summer schools\n"
        "  /exchange — Exchange programs\n\n"
        "💰 *Cost & Visa:*\n"
        "  /cost <city> — Cost of living\n"
        "  /compare <city1> vs <city2> — Compare cities\n"
        "  /visa <country> — Visa requirements\n\n"
        "📚 *Test Prep & Q&A:*\n"
        "  /tests — Test overview\n"
        "  /test <name> — Detailed test info\n"
        "  /ask <question> — AI Q&A\n\n"
        "📝 *Essay Help:*\n"
        "  /essay — Writing guides\n\n"
        "✅ *Tracking:*\n"
        "  /checklist — Application checklist\n"
        "  /check <number> — Toggle item\n"
        "  /reminders — My deadline reminders\n"
        "  /subscribe <number> — Subscribe to deadline\n"
        "  /unsubscribe <number> — Unsubscribe\n\n"
        "👤 *Profile:*\n"
        "  /profile — View my profile\n"
        "  /setprofile — Set up profile\n"
        "  /recommend — Personalized picks\n\n"
        "© 2026 Scott Antwi — Owner & Developer\n"
        "Alpha Global Minds 🌍"
    )
    await update.message.reply_text(text, parse_mode="Markdown")


# ---------------------------------------------------------------------------
# Back-to-start callback
# ---------------------------------------------------------------------------
async def back_start_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await start(update, context)


# ---------------------------------------------------------------------------
# Unknown text handler
# ---------------------------------------------------------------------------
async def unknown_text(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "👋 Hey! I'm ScholarFinder.\n\n"
        "Use /start to see the main menu with all features!\n"
        "Or /help for a full list of commands."
    )


async def cancel(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("Cancelled. Use /start to begin again.")
    return ConversationHandler.END


# ---------------------------------------------------------------------------
# APScheduler — deadline reminder job
# ---------------------------------------------------------------------------
async def check_deadlines(context: ContextTypes.DEFAULT_TYPE):
    """Daily job: notify subscribers about upcoming deadlines."""
    now = datetime.utcnow()
    alert_days = [30, 7, 1]

    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute("SELECT DISTINCT user_id, scholarship_index FROM subscriptions")
    rows = c.fetchall()
    conn.close()

    for user_id, idx in rows:
        if idx < 0 or idx >= len(SCHOLARSHIPS):
            continue
        s = SCHOLARSHIPS[idx]
        deadline_dt = parse_deadline(s["deadline"])
        if not deadline_dt:
            continue

        days_left = (deadline_dt - now).days

        if days_left in alert_days:
            emoji = "🔴" if days_left <= 1 else "🟡" if days_left <= 7 else "🟢"
            text = (
                f"{emoji} *Deadline Reminder!*\n\n"
                f"📌 *{s['name']}*\n"
                f"📅 Deadline: {s['deadline']}\n"
                f"⏰ *{days_left} day(s) left!*\n\n"
                f"🔗 {s['link']}\n\n"
                "Manage: /reminders"
            )
            try:
                await context.bot.send_message(
                    chat_id=user_id, text=text, parse_mode="Markdown", disable_web_page_preview=True
                )
            except Exception as e:
                logger.warning(f"Failed to send reminder to {user_id}: {e}")


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------
def main():
    app = Application.builder().token(TOKEN).build()

    # --- Admin commands (registered first, highest priority) ---
    app.add_handler(CommandHandler("stats", stats_command), group=-1)
    app.add_handler(CommandHandler("admin", admin_command), group=-1)

    # --- Admin conversation handler ---
    admin_conv = ConversationHandler(
        entry_points=[
            CallbackQueryHandler(adm_add_scholarship_start, pattern="^adm_add_scholarship$"),
            CallbackQueryHandler(adm_add_opp_start, pattern="^adm_add_opportunity$"),
            CallbackQueryHandler(adm_add_faq_start, pattern="^adm_add_faq$"),
            CallbackQueryHandler(adm_add_visa_start, pattern="^adm_add_visa$"),
            CallbackQueryHandler(adm_add_cost_start, pattern="^adm_add_cost$"),
            CallbackQueryHandler(adm_delete_menu, pattern="^adm_delete_menu$"),
            CallbackQueryHandler(adm_broadcast_start, pattern="^adm_broadcast$"),
            CallbackQueryHandler(stats_command, pattern="^adm_stats$"),
        ],
        states={
            ADM_SCHOLARSHIP_NAME: [MessageHandler(filters.TEXT & ~filters.COMMAND, adm_scholarship_name)],
            ADM_SCHOLARSHIP_UNI: [MessageHandler(filters.TEXT & ~filters.COMMAND, adm_scholarship_uni)],
            ADM_SCHOLARSHIP_COUNTRY: [MessageHandler(filters.TEXT & ~filters.COMMAND, adm_scholarship_country)],
            ADM_SCHOLARSHIP_FIELD: [MessageHandler(filters.TEXT & ~filters.COMMAND, adm_scholarship_field)],
            ADM_SCHOLARSHIP_LEVEL: [MessageHandler(filters.TEXT & ~filters.COMMAND, adm_scholarship_level)],
            ADM_SCHOLARSHIP_FUNDING: [MessageHandler(filters.TEXT & ~filters.COMMAND, adm_scholarship_funding)],
            ADM_SCHOLARSHIP_DEADLINE: [MessageHandler(filters.TEXT & ~filters.COMMAND, adm_scholarship_deadline)],
            ADM_SCHOLARSHIP_LINK: [MessageHandler(filters.TEXT & ~filters.COMMAND, adm_scholarship_link)],
            ADM_SCHOLARSHIP_DESC: [MessageHandler(filters.TEXT & ~filters.COMMAND, adm_scholarship_desc)],
            ADM_OPP_NAME: [MessageHandler(filters.TEXT & ~filters.COMMAND, adm_opp_name)],
            ADM_OPP_TYPE: [CallbackQueryHandler(adm_opp_type, pattern="^admopp_")],
            ADM_OPP_ORG: [MessageHandler(filters.TEXT & ~filters.COMMAND, adm_opp_org)],
            ADM_OPP_COUNTRY: [MessageHandler(filters.TEXT & ~filters.COMMAND, adm_opp_country)],
            ADM_OPP_FIELD: [MessageHandler(filters.TEXT & ~filters.COMMAND, adm_opp_field)],
            ADM_OPP_LEVEL: [MessageHandler(filters.TEXT & ~filters.COMMAND, adm_opp_level)],
            ADM_OPP_FUNDING: [MessageHandler(filters.TEXT & ~filters.COMMAND, adm_opp_funding)],
            ADM_OPP_DEADLINE: [MessageHandler(filters.TEXT & ~filters.COMMAND, adm_opp_deadline)],
            ADM_OPP_LINK: [MessageHandler(filters.TEXT & ~filters.COMMAND, adm_opp_link)],
            ADM_OPP_DESC: [MessageHandler(filters.TEXT & ~filters.COMMAND, adm_opp_desc)],
            ADM_OPP_ELIG: [MessageHandler(filters.TEXT & ~filters.COMMAND, adm_opp_elig)],
            ADM_FAQ_Q: [MessageHandler(filters.TEXT & ~filters.COMMAND, adm_faq_q)],
            ADM_FAQ_A: [MessageHandler(filters.TEXT & ~filters.COMMAND, adm_faq_a)],
            ADM_VISA_COUNTRY: [MessageHandler(filters.TEXT & ~filters.COMMAND, adm_visa_country)],
            ADM_VISA_TYPE: [MessageHandler(filters.TEXT & ~filters.COMMAND, adm_visa_type)],
            ADM_VISA_DOCS: [MessageHandler(filters.TEXT & ~filters.COMMAND, adm_visa_docs)],
            ADM_VISA_TIME: [MessageHandler(filters.TEXT & ~filters.COMMAND, adm_visa_time)],
            ADM_VISA_COST: [MessageHandler(filters.TEXT & ~filters.COMMAND, adm_visa_cost)],
            ADM_VISA_LINK: [MessageHandler(filters.TEXT & ~filters.COMMAND, adm_visa_link)],
            ADM_VISA_TIPS: [MessageHandler(filters.TEXT & ~filters.COMMAND, adm_visa_tips)],
            ADM_COST_CITY: [MessageHandler(filters.TEXT & ~filters.COMMAND, adm_cost_city)],
            ADM_COST_COUNTRY: [MessageHandler(filters.TEXT & ~filters.COMMAND, adm_cost_country)],
            ADM_COST_RENT: [MessageHandler(filters.TEXT & ~filters.COMMAND, adm_cost_rent)],
            ADM_COST_FOOD: [MessageHandler(filters.TEXT & ~filters.COMMAND, adm_cost_food)],
            ADM_COST_TRANSPORT: [MessageHandler(filters.TEXT & ~filters.COMMAND, adm_cost_transport)],
            ADM_COST_TOTAL: [MessageHandler(filters.TEXT & ~filters.COMMAND, adm_cost_total)],
            ADM_DELETE_TYPE: [CallbackQueryHandler(adm_delete_type, pattern="^admdeltype_")],
            ADM_DELETE_NUM: [MessageHandler(filters.TEXT & ~filters.COMMAND, adm_delete_num)],
            ADM_BROADCAST_MSG: [MessageHandler(filters.TEXT & ~filters.COMMAND, adm_broadcast_msg)],
        },
        fallbacks=[CommandHandler("cancel", adm_cancel)],
        allow_reentry=True,
    )
    app.add_handler(admin_conv)

    # --- Profile conversation handler (must be added before generic callbacks) ---
    profile_conv = ConversationHandler(
        entry_points=[CommandHandler("setprofile", setprofile_start)],
        states={
            PROFILE_NAME:      [MessageHandler(filters.TEXT & ~filters.COMMAND, profile_name)],
            PROFILE_COUNTRY:   [MessageHandler(filters.TEXT & ~filters.COMMAND, profile_country)],
            PROFILE_LEVEL:     [CallbackQueryHandler(profile_level, pattern="^plvl_")],
            PROFILE_GPA:       [MessageHandler(filters.TEXT & ~filters.COMMAND, profile_gpa)],
            PROFILE_FIELD:     [CallbackQueryHandler(profile_field, pattern="^pfield_")],
            PROFILE_CAREER:    [MessageHandler(filters.TEXT & ~filters.COMMAND, profile_career)],
            PROFILE_FINANCIAL: [CallbackQueryHandler(profile_financial, pattern="^pfin_")],
        },
        fallbacks=[CommandHandler("cancel", profile_cancel)],
    )
    app.add_handler(profile_conv)

    # --- Scholarship search conversation ---
    search_conv = ConversationHandler(
        entry_points=[
            CommandHandler("search", search_start),
            CommandHandler("start", start),
        ],
        states={
            CHOOSING_LEVEL: [
                CallbackQueryHandler(level_chosen, pattern="^level_"),
                CallbackQueryHandler(menu_router, pattern="^menu_"),
            ],
            CHOOSING_FIELD: [CallbackQueryHandler(field_chosen, pattern="^field_")],
            CHOOSING_REGION: [CallbackQueryHandler(region_chosen, pattern="^region_")],
        },
        fallbacks=[CommandHandler("cancel", cancel)],
        allow_reentry=True,
    )
    app.add_handler(search_conv)

    # --- University search conversation ---
    uni_conv = ConversationHandler(
        entry_points=[CommandHandler("universities", universities_cmd)],
        states={
            UNI_REGION: [CallbackQueryHandler(uni_region_chosen, pattern="^uniregion_")],
            UNI_FIELD:  [CallbackQueryHandler(uni_field_chosen, pattern="^unifield_")],
        },
        fallbacks=[CommandHandler("cancel", cancel)],
        allow_reentry=True,
    )
    app.add_handler(uni_conv)

    # --- Standalone command handlers ---
    app.add_handler(CommandHandler("help", help_command))
    app.add_handler(CommandHandler("all", all_scholarships))
    app.add_handler(CommandHandler("cost", cost_cmd))
    app.add_handler(CommandHandler("compare", compare_cmd))
    app.add_handler(CommandHandler("visa", visa_cmd))
    app.add_handler(CommandHandler("tests", tests_cmd))
    app.add_handler(CommandHandler("test", test_cmd))
    app.add_handler(CommandHandler("ask", ask_cmd))
    app.add_handler(CommandHandler("essay", essay_cmd))
    app.add_handler(CommandHandler("checklist", checklist_cmd))
    app.add_handler(CommandHandler("check", check_cmd))
    app.add_handler(CommandHandler("reminders", reminders_cmd))
    app.add_handler(CommandHandler("subscribe", subscribe_cmd))
    app.add_handler(CommandHandler("unsubscribe", unsubscribe_cmd))
    app.add_handler(CommandHandler("profile", profile_cmd))
    app.add_handler(CommandHandler("recommend", recommend_cmd))
    app.add_handler(CommandHandler("opportunities", opportunities_cmd))
    app.add_handler(CommandHandler("internships", internships_cmd))
    app.add_handler(CommandHandler("research", research_cmd))
    app.add_handler(CommandHandler("competitions", competitions_cmd))
    app.add_handler(CommandHandler("fellowships", fellowships_cmd))
    app.add_handler(CommandHandler("summer", summer_cmd))
    app.add_handler(CommandHandler("exchange", exchange_cmd))

    # --- Callback query handlers for buttons ---
    app.add_handler(CallbackQueryHandler(back_start_callback, pattern="^back_start$"))
    app.add_handler(CallbackQueryHandler(opp_type_callback, pattern="^opp_"))
    app.add_handler(CallbackQueryHandler(essay_callback, pattern="^essay_"))
    app.add_handler(CallbackQueryHandler(menu_router, pattern="^menu_"))

    # --- Unknown text (fallback) ---
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, unknown_text))

    # --- APScheduler: daily deadline check ---
    job_queue = app.job_queue
    if job_queue:
        job_queue.run_repeating(check_deadlines, interval=86400, first=60)  # run daily, first run 60s after start
        logger.info("Deadline reminder job scheduled (daily).")

    print("🎓 ScholarFinder bot is running! (Full rewrite)")
    app.run_polling(drop_pending_updates=True)


if __name__ == "__main__":
    main()
