from calendar_tool import get_upcoming_events, create_event
from gmail import read_emails, send_email, search_emails
from spotify import spotify_play, spotify_pause, spotify_next, spotify_current, spotify_play_playlist
from automation import open_app, open_url, search_youtube, focus_mode_on, focus_mode_off
import requests
import os
from automation import open_app, open_url, search_youtube, focus_mode_on, focus_mode_off, search_browser_history


def web_search(query):
    url = "https://api.tavily.com/search"

    headers = {
        "Authorization": f"Bearer {os.getenv('TAVILY_API_KEY')}",
        "Content-Type": "application/json"
    }

    payload = {
        "query": query,
        "search_depth": "basic",
        "max_results": 5
    }

    try:
        response = requests.post(url, json=payload, headers=headers)
        data = response.json()

        formatted = ""
        for i, r in enumerate(data.get("results", [])[:3], 1):
            title = r.get("title", "")
            content = r.get("content", "")[:300]
            formatted += f"{i}. {title}\n{content}\n\n"

        if not formatted:
            return "No results found."

        return formatted.strip()

    except Exception as e:
        return f"Search failed: {str(e)}"


def read_file(path):
    if not os.path.exists(path):
        return f"File not found at: {path}"

    try:
        with open(path, "r", encoding="utf-8") as f:
            return f.read()
    except Exception as e:
        return f"Error reading file: {str(e)}"


def write_file(path, content):
    print(f"\n⚠️  FRIDAY wants to write to: {path}")
    print(f"Preview: {content[:100]}...")

    confirm = input("Confirm? (yes/no): ").strip().lower()

    if confirm != "yes":
        return "Write cancelled by user."

    try:
        mode = "a" if "FRIDAY'S LOGS" in path or ".md" in path else "w"
        with open(path, mode, encoding="utf-8") as f:
            f.write("\n" + content)
        return f"File written successfully to {path}"
    except Exception as e:
        return f"Error writing file: {str(e)}"


def gmail_read(input=None):
    return read_emails(max_results=5)


def gmail_send(to, subject, body):
    return send_email(to, subject, body)


def gmail_search(query):
    return search_emails(query)


def calendar_get(input=None):
    try:
        result = get_upcoming_events()
        print(f"[CALENDAR RESULT: {result}]", flush=True)
        return result
    except Exception as e:
        print(f"[CALENDAR ERROR: {e}]", flush=True)
        return f"Calendar error: {str(e)}"


def calendar_create(summary, start_time, end_time, description="", location=""):
    return create_event(summary, start_time, end_time, description, location)


def spotify_play_song(query):
    return spotify_play(query)


def spotify_play_list(name):
    return spotify_play_playlist(name)


def spotify_control(action):
    if action == "pause":
        return spotify_pause()
    elif action == "next":
        return spotify_next()
    elif action == "current":
        return spotify_current()
    return "Unknown action."


def open_application(app_name):
    return open_app(app_name)


def open_website(url):
    return open_url(url)


def youtube_search(query):
    return search_youtube(query)


def focus_on():
    return focus_mode_on()


def focus_off():
    return focus_mode_off()


def browser_history(query):
    result = search_browser_history(query)
    return result