import os
import json
from datetime import datetime
from anthropic import Anthropic
from dotenv import load_dotenv

load_dotenv()

client = Anthropic()

BASE_DIR         = os.path.dirname(os.path.abspath(__file__))
HABITS_FILE      = os.path.join(BASE_DIR, "habits.json")
CLIPBOARD_FILE   = os.path.join(BASE_DIR, "clipboard.json")
SPENDING_FILE    = os.path.join(BASE_DIR, "spending.json")


def review_code(code, language=""):
    prompt = f"Review this{' ' + language if language else ''} code:\n\n{code}"
    response = client.messages.create(
        model="claude-sonnet-4-5",
        max_tokens=600,
        system="""You are a senior software engineer doing a code review.
        Cover: bugs, logic errors, performance issues, security concerns, style improvements.
        Be specific — point to exact lines or patterns. Be concise but thorough.
        Format: short summary, then bullet points for each issue found.""",
        messages=[{"role": "user", "content": prompt}]
    )
    return response.content[0].text.strip()


def review_uploaded_code(content, filename=""):
    lang = ""
    if filename:
        ext_map = {".py": "Python", ".js": "JavaScript", ".ts": "TypeScript",
                   ".java": "Java", ".cpp": "C++", ".c": "C", ".cs": "C#"}
        ext = os.path.splitext(filename)[1].lower()
        lang = ext_map.get(ext, "")
    return review_code(content, lang)



def draft_email(context, tone="professional"):
    tone_guides = {
        "casual":       "Write casually and friendly. Like texting a friend but in email form.",
        "professional": "Write professionally and politely. Clear, concise, respectful.",
        "formal":       "Write formally. Full sentences, no contractions, very respectful."
    }
    response = client.messages.create(
        model="claude-sonnet-4-5",
        max_tokens=400,
        system=f"""You draft emails for Aryan, a computer engineering student.
        {tone_guides.get(tone, tone_guides['professional'])}
        Include a subject line. Keep it concise. Sign off as Aryan.""",
        messages=[{"role": "user", "content": f"Draft an email: {context}"}]
    )
    return response.content[0].text.strip()



def _load_habits():
    if not os.path.exists(HABITS_FILE):
        return []
    with open(HABITS_FILE, "r") as f:
        return json.load(f)

def _save_habits(data):
    with open(HABITS_FILE, "w") as f:
        json.dump(data, f, indent=2)

def log_habit(entry):
    data = _load_habits()
    data.append({
        "timestamp": datetime.now().isoformat(),
        "date":      datetime.now().strftime("%Y-%m-%d"),
        "entry":     entry
    })
    _save_habits(data)
    return f"Logged: {entry}"

def get_habit_summary():
    data = _load_habits()
    if not data:
        return "No habits or mood entries logged yet."

    today = datetime.now().strftime("%Y-%m-%d")
    week_ago = datetime.now().strftime("%Y-%m-%d")
    recent = [d for d in data if d["date"] >= (datetime.now().strftime("%Y-%m-%d")[:8] + "01")]

    if not recent:
        return "No entries this month."

    entries_text = "\n".join([f"- {e['date']}: {e['entry']}" for e in recent[-20:]])
    response = client.messages.create(
        model="claude-sonnet-4-5",
        max_tokens=200,
        system="Summarise these habit and mood logs. Identify patterns, streaks, and areas for improvement. Be encouraging but honest.",
        messages=[{"role": "user", "content": entries_text}]
    )
    return response.content[0].text.strip()



def _load_clipboard():
    if not os.path.exists(CLIPBOARD_FILE):
        return []
    with open(CLIPBOARD_FILE, "r") as f:
        return json.load(f)

def _save_clipboard(data):
    with open(CLIPBOARD_FILE, "w") as f:
        json.dump(data, f, indent=2)

def clipboard_save(note):
    data = _load_clipboard()
    data.append({
        "timestamp": datetime.now().isoformat(),
        "note":      note
    })
    _save_clipboard(data)
    return f"Saved to clipboard memory."

def clipboard_search(query):
    data = _load_clipboard()
    if not data:
        return "Nothing saved yet."

    matches = [d for d in data if query.lower() in d["note"].lower()]
    if not matches:
        return f"Nothing found for: {query}"

    return "\n".join([f"- [{d['timestamp'][:10]}] {d['note']}" for d in matches[-10:]])

def clipboard_list():
    data = _load_clipboard()
    if not data:
        return "Nothing saved yet."
    return "\n".join([f"- [{d['timestamp'][:10]}] {d['note']}" for d in data[-15:]])



def _load_spending():
    if not os.path.exists(SPENDING_FILE):
        return []
    with open(SPENDING_FILE, "r") as f:
        return json.load(f)

def _save_spending(data):
    with open(SPENDING_FILE, "w") as f:
        json.dump(data, f, indent=2)

def log_expense(description, amount, currency="INR"):
    data = _load_spending()
    data.append({
        "timestamp":   datetime.now().isoformat(),
        "date":        datetime.now().strftime("%Y-%m-%d"),
        "description": description,
        "amount":      float(amount),
        "currency":    currency
    })
    _save_spending(data)
    return f"Expense logged: {description} — {amount} {currency}"

def get_spending_summary(period="today"):
    data = _load_spending()
    if not data:
        return "No expenses logged yet."

    today = datetime.now().strftime("%Y-%m-%d")
    month = datetime.now().strftime("%Y-%m")

    if period == "today":
        filtered = [d for d in data if d["date"] == today]
        label    = "Today"
    elif period == "week":
        from datetime import timedelta
        week_ago = (datetime.now() - timedelta(days=7)).strftime("%Y-%m-%d")
        filtered = [d for d in data if d["date"] >= week_ago]
        label    = "Last 7 days"
    else:
        filtered = [d for d in data if d["date"].startswith(month)]
        label    = "This month"

    if not filtered:
        return f"No expenses for {label.lower()}."

    total = sum(d["amount"] for d in filtered)
    lines = [f"{label} spending: ₹{total:,.0f}"]
    for d in filtered:
        lines.append(f"  - {d['description']}: ₹{d['amount']:,.0f}")
    return "\n".join(lines)