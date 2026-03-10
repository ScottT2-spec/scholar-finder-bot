#!/bin/bash
# Start the web server in the background (keeps HF Space alive)
gunicorn app:app --bind 0.0.0.0:7860 &

# Start the Telegram bot
python bot.py
