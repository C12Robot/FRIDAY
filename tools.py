from calendar_tool import get_upcoming_events, create_event, delete_event
from gmail import read_emails, send_email, search_emails
from spotify import spotify_play, spotify_pause, spotify_next, spotify_current, spotify_play_playlist
from automation import open_app, open_url, search_youtube, focus_mode_on, focus_mode_off, search_browser_history
from finance import log_trade, get_market_prices, get_sentiment, get_weekly_pnl, get_trading_patterns
from content import (search_trending, get_video_comments, get_channel_stats,
                     get_best_upload_time, get_top_videos, generate_video_ideas,
                     generate_script_outline, suggest_content_from_stats)
from automation import set_brightness, set_volume, mute_volume, unmute_volume
from college import (read_any_file, summarise_file, summarise_text,
                     generate_quiz, add_assignment, get_assignments,
                     mark_assignment_done, find_research_papers, explain_concept)
from productivity import (review_code, review_uploaded_code, draft_email,
                          log_habit, get_habit_summary, clipboard_save,
                          clipboard_search, clipboard_list,
                          log_expense, get_spending_summary)
import requests
import os
client_id = os.getenv("SPOTIFY_CLIENT_ID")
client_service = os.getenv("SPOTIFY_CLIENT_SECRET")
redirect_url = os.getenv("SPOTIFY_REDIRECT_URL")


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

def college_summarise_file(filepath):
    return summarise_file(filepath)

def college_summarise_text(text):
    return summarise_text(text)

def college_quiz(filepath=None, text=None, num_questions=5):
    return generate_quiz(filepath, text, num_questions)

def college_add_assignment(title, due_date, subject=""):
    return add_assignment(title, due_date, subject)

def college_get_assignments():
    return get_assignments()

def college_mark_done(title):
    return mark_assignment_done(title)

def college_find_papers(topic):
    return find_research_papers(topic)

def college_explain(concept, level="normal"):
    return explain_concept(concept, level)

def prod_review_code(code, language=""):
    return review_code(code, language)

def prod_review_uploaded():
    from api import uploaded_file_context
    ctx = uploaded_file_context.get("last")
    if not ctx:
        return "No file uploaded."
    return review_uploaded_code(ctx["content"], ctx.get("filename", ""))

def prod_draft_email(context, tone="professional"):
    return draft_email(context, tone)

def prod_log_habit(entry):
    return log_habit(entry)

def prod_habit_summary():
    return get_habit_summary()

def prod_clipboard_save(note):
    return clipboard_save(note)

def prod_clipboard_search(query):
    return clipboard_search(query)

def prod_clipboard_list():
    return clipboard_list()

def prod_log_expense(description, amount, currency="INR"):
    return log_expense(description, amount, currency)

def prod_spending_summary(period="today"):
    return get_spending_summary(period)