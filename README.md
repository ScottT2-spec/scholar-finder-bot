# 🎓 ScholarFinder Bot

**Your complete guide to studying abroad** — a Telegram bot with 25+ commands covering scholarships, universities, opportunities, visa guides, cost of living, test prep, essay help, and more.

Built by **Scott | Alpha Global Minds**

## 📊 Database

| Category | Count |
|----------|-------|
| Scholarships | 151 |
| Universities | 86 |
| Opportunities | 62 |
| Cost of Living Cities | 51 |
| FAQ Q&A Pairs | 42 |
| Visa Guides | 26 |
| Test Prep Guides | 5 |
| Essay Writing Guides | 6 |

## 🚀 Features

### 🔍 Scholarship Search
- `/start` — Main menu with inline buttons for all features
- `/search` — Interactive search: level → field → region → results
- `/all` — List all 151 scholarships (chunked messages)

### 🏫 University Search
- `/universities` — Interactive: region → field → results with ranking, tuition, website

### 🌍 Opportunities Database (62 entries)
- `/opportunities` — Browse by category (inline buttons)
- `/internships` — Google STEP, Microsoft Explore, Meta University, Outreachy, GSoC, etc.
- `/research` — MIT MSRP, Stanford SURF, Caltech SURF, CERN, DAAD RISE, etc.
- `/competitions` — Kaggle, Zindi, ICPC, Google Code Jam, Hult Prize, etc.
- `/fellowships` — MLH Fellowship, GitHub Campus Expert, GDSC Lead, Mandela Washington, etc.
- `/summer` — DeepMind, Oxford ML, EPFL, Heidelberg Laureate Forum, etc.
- `/exchange` — AFS, UWC, Kennedy-Lugar YES, Global UGRAD, Erasmus+, etc.

### 💰 Cost of Living
- `/cost <city>` — Monthly breakdown (rent, food, transport, etc.)
- `/compare <city1> vs <city2>` — Side-by-side comparison

### 🛂 Visa Guide
- `/visa <country>` — Documents, processing time, cost, tips (26 countries)

### 📚 Test Prep
- `/tests` — Overview of all 5 tests (IELTS, TOEFL, Duolingo, SAT, GRE)
- `/test <name>` — Detailed format, scoring, requirements, free resources, tips

### 🤖 AI Q&A
- `/ask <question>` — Keyword-matched against 42 FAQ entries
- Word overlap scoring, top 1-3 matches, topic suggestions

### 📝 Essay & SOP Help
- `/essay` — Menu with 6 comprehensive guides:
  - Personal Statement Structure
  - Statement of Purpose (SOP)
  - Academic CV Format
  - Activity List Tips
  - Essay Dos & Don'ts
  - Power Words for Applications

### ✅ Application Checklist
- `/checklist` — 9-item checklist with ✅/⬜ per user
- `/check <number>` — Toggle items on/off
- Items: Personal Statement, CV, Transcripts, Recommendations, Language Score, Passport, Application Form, Motivation Letter, Portfolio

### ⏰ Deadline Reminders
- `/subscribe <number>` — Subscribe to deadline alerts (number from `/all`)
- `/unsubscribe <number>` — Remove subscription
- `/reminders` — View my subscriptions with days remaining
- **Automatic notifications** at 30, 7, and 1 days before deadlines (APScheduler)

### 👤 Student Profile
- `/setprofile` — Guided setup (name, country, level, GPA, field, career goals, financial need)
- `/profile` — View saved profile
- Data stored in SQLite

### ⭐ Personalized Recommendations
- `/recommend` — Based on your profile:
  - Top 5 matching scholarships
  - Top 3 matching universities
  - Top 3 matching opportunities
- Scoring considers level, field, region, financial need, tuition tier

### 📖 Help
- `/help` — All commands grouped by category

## 🛠 Technical Stack

- **Language:** Python 3
- **Framework:** python-telegram-bot (v20+)
- **Database:** SQLite (`users.db`)
  - Tables: `subscriptions`, `checklist_progress`, `user_profiles`
- **Scheduler:** APScheduler (daily deadline check)
- **Data:** JSON files for all reference data

## 📁 File Structure

```
scholarbot/
├── bot.py                  # Main bot (all features)
├── scholarships.json       # 151 scholarships
├── universities.json       # 86 universities
├── opportunities.json      # 62 opportunities
├── cost_data.json          # 51 cities
├── faq_data.json           # 42 Q&A pairs
├── test_prep_data.json     # 5 standardized tests
├── visa_data.json          # 26 countries
├── essay_guides.json       # 6 writing guides
├── users.db                # SQLite user data (auto-created)
├── watchdog.sh             # Auto-restart watchdog
└── README.md               # This file
```

## 🔧 Running

```bash
# Install dependencies
pip install python-telegram-bot apscheduler

# Run
cd scholarbot
python3 bot.py

# Watchdog (auto-restart)
bash watchdog.sh &
```

## 🌍 Region Coverage

Africa • Europe • Middle East • Asia • North America • Oceania • South America — covering 46 countries.
