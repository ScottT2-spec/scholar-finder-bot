# ScholarFinder Bot

A Telegram bot I built to help students (especially in Africa) find scholarships, universities, and opportunities to study abroad. I was tired of spending hours searching different websites for scholarship info, so I put everything in one place.

**Try it:** [@ScholarFinder_bot](https://t.me/ScholarFinder_bot) on Telegram

**Website:** [scottt2-spec.github.io/scholar-finder-bot](scholarfinder.pythonanywhere.com/)

## What's in the database

| What | How many |
|------|----------|
| Scholarships | 151 across 46 countries |
| Universities | 86 |
| Opportunities (internships, research, competitions) | 62 |
| Cities with cost of living data | 51 |
| FAQ answers | 42 |
| Visa guides | 26 countries |
| Test prep guides | 5 (IELTS, TOEFL, SAT, GRE, Duolingo) |
| Essay writing guides | 6 |

## What you can do with it

**Find scholarships** — Search by level (undergrad/masters/PhD), field, and region. Or just browse all 151.

**Look up universities** — Filter by region and field of study. Shows rankings, tuition, and links.

**Browse opportunities** — Internships (Google STEP, Microsoft Explore, GSoC), research programs (MIT MSRP, Stanford SURF, CERN), competitions (Kaggle, ICPC, Hult Prize), fellowships, summer programs, and exchange programs.

**Compare cost of living** — Check monthly costs for any of the 51 cities, or compare two cities side by side.

**Visa info** — Documents needed, processing time, costs, and tips for 26 countries.

**Test prep** — Format, scoring, resources, and tips for IELTS, TOEFL, SAT, GRE, and Duolingo.

**Essay help** — Guides for personal statements, SOPs, CVs, activity lists, with dos/don'ts and example phrases.

**Track your applications** — Checklist you can check off as you complete each step (transcripts, recommendations, etc.)

**Deadline reminders** — Subscribe to any scholarship and get notified at 30, 7, and 1 day before the deadline.

**Personalized recommendations** — Set up your profile (country, GPA, field, goals) and get scholarship matches.

**Ask questions** — Type any question and the bot matches it against 42 common study-abroad FAQs.

## Why I built it

I'm a high school student in Ghana applying to universities abroad. The scholarship search process is frustrating — info is scattered across dozens of websites, deadlines sneak up on you, and a lot of the advice out there is generic or not relevant to African students.

I wanted something that just works: open Telegram, search, get results. No ads, no sign-ups, no paywalls.

## Built with

- Python + python-telegram-bot
- SQLite for user data and activity tracking
- APScheduler for deadline reminders
- JSON data files (handpicked, not scraped)

## Run it yourself

1. Clone this repo
2. Create a Telegram bot via [@BotFather](https://t.me/BotFather)
3. Set your bot token and admin ID in the code
4. `pip install python-telegram-bot apscheduler`
5. `python bot.py`

Built by Scott | [Alpha Global Minds](https://github.com/ScottT2-spec)

<!-- v2 -->
