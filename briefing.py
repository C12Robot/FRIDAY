import os
import json
import requests
from datetime import datetime
from anthropic import Anthropic
from dotenv import load_dotenv

load_dotenv()

client = Anthropic()

BRIEFING_FILE = os.path.join(os.path.dirname(__file__), "last_briefing.json")

def _was_briefed_today():
    try:
        if not os.path.exists(BRIEFING_FILE):
            return False
        with open(BRIEFING_FILE, "r") as f:
            data = json.load(f)
        return data.get("date") == datetime.now().strftime("%Y-%m-%d")
    except:
        return False

def _mark_briefed():
    with open(BRIEFING_FILE, "w") as f:
        json.dump({"date": datetime.now().strftime("%Y-%m-%d")}, f)

def get_market_data():
    try:
        tavily_key = os.getenv("TAVILY_API_KEY")
        headers = {
            "Authorization": f"Bearer {tavily_key}",
            "Content-Type": "application/json"
        }

        results = {}

        # Gold price
        r = requests.post("https://api.tavily.com/search", headers=headers, json={
            "query": "Gold price today USD per ounce",
            "search_depth": "basic",
            "max_results": 2
        })
        gold = r.json().get("results", [{}])[0].get("content", "")[:200]
        results["gold"] = gold

        # MES1 futures
        r = requests.post("https://api.tavily.com/search", headers=headers, json={
            "query": "MES1 Micro E-mini S&P 500 futures latest news price",
            "search_depth": "basic",
            "max_results": 2
        })
        mes = r.json().get("results", [{}])[0].get("content", "")[:200]
        results["mes1"] = mes

        return results
    except Exception as e:
        return {"gold": "unavailable", "mes1": "unavailable"}

def get_email_summary():
    try:
        from gmail import read_emails
        emails = read_emails(max_results=3)
        return emails
    except:
        return "Unable to fetch emails."

def get_calendar_summary():
    try:
        from calendar_tool import get_upcoming_events
        return get_upcoming_events()
    except:
        return "Unable to fetch calendar."

def generate_morning_briefing():
    hour = datetime.now().hour
    if hour < 5 or hour > 11:
        greeting = "Good day"
    else:
        greeting = "Good morning"

    emails    = get_email_summary()
    calendar  = get_calendar_summary()
    market    = get_market_data()

    prompt = f"""Generate a concise morning briefing for Aryan. Keep it under 150 words, informal and direct.

Date: {datetime.now().strftime('%A, %B %d %Y')}
Time: {datetime.now().strftime('%H:%M')}

Emails summary: {emails[:300]}
Calendar today: {calendar[:300]}
Gold price info: {market['gold']}
MES1 Futures info: {market['mes1']}

Format:
- Start with "{greeting}, Aryan."
- 1 line on emails
- 1 line on calendar
- 1 line on Gold price
- 1 line on MES1 futures
- End with one short motivational line

No bullet points. Just clean paragraphs."""

    response = client.messages.create(
        model="claude-sonnet-4-5",
        max_tokens=300,
        messages=[{"role": "user", "content": prompt}]
    )
    return response.content[0].text.strip()

def get_briefing_if_due():
    if _was_briefed_today():
        return None
    briefing = generate_morning_briefing()
    _mark_briefed()
    return briefing

def get_market_brief():
    market = get_market_data()
    response = client.messages.create(
        model="claude-sonnet-4-5",
        max_tokens=150,
        messages=[{"role": "user", "content": f"""Give a quick 2-line market update.
Gold: {market['gold']}
MES1 Futures: {market['mes1']}
Be direct, no fluff."""}]
    )
    return response.content[0].text.strip()