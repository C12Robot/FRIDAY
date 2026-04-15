from calendar_tool import get_upcoming_events, create_event
from gmail import read_emails, send_email, search_emails
import requests
import os


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
        with open(path, "w", encoding="utf-8") as f:
            f.write(content)
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