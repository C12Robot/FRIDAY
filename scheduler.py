import os
import json
from datetime import datetime, timedelta
from apscheduler.schedulers.background import BackgroundScheduler
from calendar_tool import get_upcoming_events
from behaviour import get_frequent_topics, get_time_context, _load_log

OBSIDIAN_LOG = r"C:\Users\meena\Documents\Builder_Brain\FRIDAY'S LOGS\Daily Log.md"

notifications = []
dnd_active = False

def get_notifications():
    return notifications[-10:]

def clear_notifications():
    notifications.clear()

def set_dnd(state: bool):
    global dnd_active
    dnd_active = state

def _push(message):
    if dnd_active:
        notifications.append({"message": message, "time": datetime.now().strftime("%H:%M"), "held": True})
    else:
        notifications.append({"message": message, "time": datetime.now().strftime("%H:%M"), "held": False})

def check_deadlines():
    try:
        events_raw = get_upcoming_events()
        if not events_raw or "No upcoming" in events_raw:
            return
        now = datetime.now()
        soon = now + timedelta(minutes=60)
        lines = events_raw.split("\n")
        for line in lines:
            if "2026" in line or "T" in line:
                _push(f"⏰ Upcoming: {line.strip()}")
    except:
        pass

def check_patterns():
    try:
        data = _load_log()
        if not data:
            return
        today = datetime.now().strftime("%Y-%m-%d")
        today_logs = [e for e in data if e["timestamp"].startswith(today)]
        hour = datetime.now().hour

        if hour == 9 and not today_logs:
            _push("☀️ Good morning! You haven't talked to me yet today.")

        if len(today_logs) == 0 and hour >= 20:
            _push("📝 You haven't logged anything today. Want to add a daily note?")

        topics = get_frequent_topics(3)
        if topics and hour in [10, 15]:
            _push(f"💡 You usually ask about {topics[0]} around this time.")

    except:
        pass

def release_dnd_notifications():
    global dnd_active
    if not dnd_active:
        return
    held = [n for n in notifications if n.get("held")]
    if held:
        _push(f"📬 {len(held)} notifications held during focus mode.")
    for n in notifications:
        n["held"] = False

def start_scheduler():
    scheduler = BackgroundScheduler()
    scheduler.add_job(check_deadlines, 'interval', minutes=30)
    scheduler.add_job(check_patterns, 'interval', minutes=60)
    scheduler.start()
    return scheduler