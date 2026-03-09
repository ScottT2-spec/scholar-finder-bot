#!/bin/bash
# ScholarFinder Web App Watchdog
# Keeps Flask running on port 5000

APP_DIR="/root/.openclaw/workspace/scholarweb"
LOG_FILE="$APP_DIR/web.log"
PID_FILE="$APP_DIR/web.pid"

while true; do
    if [ -f "$PID_FILE" ]; then
        PID=$(cat "$PID_FILE")
        if kill -0 "$PID" 2>/dev/null; then
            sleep 1
            continue
        fi
    fi

    echo "[$(date)] Starting ScholarFinder Web..." >> "$LOG_FILE"
    cd "$APP_DIR"
    python3 app.py >> "$LOG_FILE" 2>&1 &
    echo $! > "$PID_FILE"
    echo "[$(date)] Started PID $(cat $PID_FILE)" >> "$LOG_FILE"
    sleep 2
done
