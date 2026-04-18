from calendar_tool import get_upcoming_events, create_event, delete_event
from gmail import read_emails, send_email, search_emails
from spotify import spotify_play, spotify_pause, spotify_next, spotify_current, spotify_play_playlist
from automation import open_app, open_url, search_youtube, focus_mode_on, focus_mode_off, search_browser_history
from finance import log_trade, get_market_prices, get_sentiment, get_weekly_pnl, get_trading_patterns
from content import (search_trending, get_video_comments, get_channel_stats,
                     get_best_upload_time, get_top_videos, generate_video_ideas,
                     generate_script_outline, suggest_content_from_stats)
from automation import set_brightness, set_volume, mute_volume, unmute_volume
import requests
import os


def web_search(query):
    url = "https://api.tavily.com/search"
    headers = {
        "Authorization": f"Bearer {os.getenv('TAVILY_API_KEY')}",
        "Content-Type": "application/json"
    }
    payload = {"query": query, "search_depth": "basic", "max_results": 5}
    try:
        response = requests.post(url, json=payload, headers=headers)
        data = response.json()
        formatted = ""
        for i, r in enumerate(data.get("results", [])[:3], 1):
            title   = r.get("title", "")
            content = r.get("content", "")[:300]
            formatted += f"{i}. {title}\n{content}\n\n"
        return formatted.strip() if formatted else "No results found."
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
    mode = "a" if ".md" in path else "w"
    try:
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
        return result
    except Exception as e:
        return f"Calendar error: {str(e)}"


def calendar_create(summary, start_time, end_time, description="", location=""):
    return create_event(summary, start_time, end_time, description, location)


def calendar_delete(event_id):
    return delete_event(event_id)


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
    return search_browser_history(query)

def finance_log_trade(entry_text):
    return log_trade(entry_text)

def finance_market_prices():
    return get_market_prices()

def finance_sentiment(asset):
    return get_sentiment(asset)

def finance_weekly_pnl():
    return get_weekly_pnl()

def finance_patterns():
    return get_trading_patterns()

def content_trending(niche="futures trading finance"):
    return search_trending(niche)

def content_comments(video_url):
    return get_video_comments(video_url)

def content_channel_stats(channel="main"):
    return get_channel_stats(channel)

def content_upload_time(channel="main"):
    return get_best_upload_time(channel)

def content_top_videos(channel="main"):
    return get_top_videos(channel)

def content_video_ideas(niche="futures trading finance"):
    return generate_video_ideas(niche)

def content_script(topic):
    return generate_script_outline(topic)

def content_suggestions(channel="main"):
    return suggest_content_from_stats(channel)

def brightness_set(level):
    return set_brightness(level)

def volume_set(level):
    return set_volume(level)

def volume_mute():
    return mute_volume()

def volume_unmute():
    return unmute_volume()