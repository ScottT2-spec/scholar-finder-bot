# ScholarFinder Bot

A Telegram bot that helps students discover fully-funded scholarships worldwide. Search by education level, field of study, and preferred region.

**Try it:** [@ScholarFinder_bot](https://t.me/ScholarFinder_bot)

## How it works

1. Send `/start` to the bot
2. Choose your education level (Undergraduate, Masters, PhD)
3. Pick your field of study
4. Select your preferred region
5. Get matching scholarships with deadlines, funding details, and direct links

![Bot Interface](images/scholarfinder_start.jpg)

![Search Results](images/scholarfinder_results.jpg)

## Features

- 20+ verified scholarships from around the world
- Filter by level, field, and region
- Shows funding amount, deadlines, and application links
- Includes scholarships specifically for African students
- `/all` command to browse every scholarship in the database

## Scholarships include

- MBZUAI (UAE) - Full tuition + stipend
- MasterCard Foundation - Fully funded for African students
- Chevening (UK) - Fully funded masters
- DAAD (Germany) - Monthly stipend + tuition
- Turkiye Burslari - Full tuition + accommodation + flights
- KAUST (Saudi Arabia) - Full fellowship
- And many more

## Run it yourself

1. Create a Telegram bot via [@BotFather](https://t.me/BotFather)
2. Clone this repo
3. Replace the token in `bot.py` with your own
4. Install dependencies: `pip install python-telegram-bot`
5. Run: `python3 bot.py`

## Built with

- Python 3
- python-telegram-bot library
- JSON database for scholarship data

## What's next

- Keyword search across all scholarships
- Deadline alerts and notifications
- Web scraping for live scholarship updates
- User favorites and saved searches

Built by Scott | Alpha Global Minds

