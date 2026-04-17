import json
import os
import re
from datetime import datetime, timedelta
from collections import Counter
from anthropic import Anthropic
from dotenv import load_dotenv

load_dotenv()

BEHAVIOUR_LOG      = os.path.join(os.path.dirname(__file__), "behaviour_log.json")
OBSIDIAN_BASE      = r"C:\Users\meena\Documents\Builder_Brain\FRIDAY'S LOGS"
OBSIDIAN_LOG       = os.path.join(OBSIDIAN_BASE, "FRIDAY LOGS.md")
OBSIDIAN_DECISIONS = os.path.join(OBSIDIAN_BASE, "Decisions.md")
OBSIDIAN_WEEKLY    = os.path.join(OBSIDIAN_BASE, "Weekly Summaries.md")

client = Anthropic()

def _load_log():
    if not os.path.exists(BEHAVIOUR_LOG):
        return []
    with open(BEHAVIOUR_LOG, "r") as f:
        return json.load(f)

def _save_log(data):
    with open(BEHAVIOUR_LOG, "w") as f:
        json.dump(data, f, indent=2)

def log_interaction(user_message, friday_reply, tools_used=[]):
    data = _load_log()
    data.append({
        "timestamp": datetime.now().isoformat(),
        "hour": datetime.now().hour,
        "user": user_message,
        "reply": friday_reply,
        "tools": tools_used
    })
    _save_log(data)

def get_time_context():
    hour = datetime.now().hour
    if 5 <= hour < 12:    return "morning"
    elif 12 <= hour < 17: return "afternoon"
    elif 17 <= hour < 21: return "evening"
    else:                 return "night"

def get_frequent_topics(n=5):
    data = _load_log()
    if not data:
        return []
    stopwords = {"the","a","an","is","it","to","i","my","can","you","what",
                 "how","do","for","in","of","and","me","so","that","this"}
    words = []
    for entry in data[-50:]:
        for w in entry["user"].lower().split():
            if w not in stopwords and len(w) > 3:
                words.append(w)
    return [w for w, _ in Counter(words).most_common(n)]

def get_behaviour_context():
    time_ctx = get_time_context()
    topics   = get_frequent_topics()
    hour     = datetime.now().hour
    context  = f"\nTime context: It is {time_ctx} ({hour}:00)."
    if time_ctx == "morning":
        context += " Be proactive — offer to check emails and calendar."
    elif time_ctx == "night":
        context += " Keep it casual and relaxed."
    if topics:
        context += f"\nAryan frequently asks about: {', '.join(topics)}."
    return context

def write_obsidian_log(summary):
    date_str = datetime.now().strftime("%Y-%m-%d")
    time_str = datetime.now().strftime("%H:%M")
    entry = f"\n## {date_str} — {time_str}\n{summary}\n"
    try:
        with open(OBSIDIAN_LOG, "a", encoding="utf-8") as f:
            f.write(entry)
        return True
    except Exception as e:
        print(f"[obsidian log error: {e}]")
        return False

# ── DECISION AUTO-LOGGER ──────────────────────────────────────────────────────

DECISION_KEYWORDS = [
    "i'll use", "going with", "decided to", "switching to",
    "instead of", "replacing", "won't use", "sticking with",
    "chose", "picked", "using", "not going to"
]

def detect_and_log_decision(user_message, friday_reply):
    msg_lower = user_message.lower()
    if not any(k in msg_lower for k in DECISION_KEYWORDS):
        return
    try:
        response = client.messages.create(
            model="claude-sonnet-4-5",
            max_tokens=200,
            system="""You detect technical/project decisions in messages.
If there is a clear decision, return JSON: {"is_decision": true, "decision": "short one-line summary"}
If not, return: {"is_decision": false}
Only flag real decisions — tool choices, architecture, preferences. Not casual chat.
Return ONLY the JSON with no markdown, no code fences, nothing else.""",
            messages=[{"role": "user", "content": f"User said: {user_message}"}]
        )
        raw = response.content[0].text.strip()
        raw = re.sub(r'^```json|^```|```$', '', raw, flags=re.MULTILINE).strip()
        result = json.loads(raw)
        if result.get("is_decision"):
            date_str = datetime.now().strftime("%Y-%m-%d")
            entry = f"\n- [{date_str}] {result['decision']}\n"
            with open(OBSIDIAN_DECISIONS, "a", encoding="utf-8") as f:
                f.write(entry)
    except Exception as e:
        print(f"[decision error: {e}]")

# ── WEEKLY SUMMARY ────────────────────────────────────────────────────────────

def _get_last_summary_date():
    try:
        if not os.path.exists(OBSIDIAN_WEEKLY):
            return None
        with open(OBSIDIAN_WEEKLY, "r", encoding="utf-8") as f:
            content = f.read()
        dates = re.findall(r"## Week of (\d{4}-\d{2}-\d{2})", content)
        if dates:
            return datetime.strptime(dates[-1], "%Y-%m-%d")
    except:
        pass
    return None

def is_weekly_summary_due():
    today = datetime.now()
    if today.weekday() != 6:  # 6 = Sunday
        return False
    last = _get_last_summary_date()
    if last is None:
        return True
    return (today - last).days >= 7

def generate_weekly_summary():
    data = _load_log()
    if not data:
        return None
    week_ago  = (datetime.now() - timedelta(days=7)).isoformat()
    week_data = [e for e in data if e["timestamp"] >= week_ago]
    if len(week_data) < 3:
        return None

    all_tools = []
    for e in week_data:
        all_tools.extend(e.get("tools", []))
    tool_counts = Counter(all_tools)

    stopwords = {"the","a","an","is","it","to","i","my","can","you","what",
                 "how","do","for","in","of","and","me","so","that","this"}
    words = []
    for e in week_data:
        for w in e["user"].lower().split():
            if w not in stopwords and len(w) > 3:
                words.append(w)
    top_topics = [w for w, _ in Counter(words).most_common(5)]

    hours      = [e["hour"] for e in week_data]
    peak_hour  = Counter(hours).most_common(1)[0][0]
    if peak_hour < 12:    peak_period = "morning"
    elif peak_hour < 17:  peak_period = "afternoon"
    elif peak_hour < 21:  peak_period = "evening"
    else:                 peak_period = "night"

    sample_convos = "\n".join([f"- {e['user']}" for e in week_data[-10:]])

    response = client.messages.create(
        model="claude-sonnet-4-5",
        max_tokens=400,
        system="""You write weekly summaries for Aryan's personal AI assistant FRIDAY.
Write a short, informal, 4-6 line summary of what happened this week.
Cover: main topics, peak activity time, tools used, any patterns noticed.
Style: like a friend recapping the week. No headers, no bullets, just clean paragraphs.""",
        messages=[{"role": "user", "content": f"""
Conversations this week ({len(week_data)} total):
{sample_convos}

Top topics: {', '.join(top_topics)}
Tools used: {dict(tool_counts)}
Peak activity: {peak_period} (around {peak_hour}:00)
"""}]
    )
    return response.content[0].text.strip()

def write_weekly_summary(summary_text):
    date_str = datetime.now().strftime("%Y-%m-%d")
    entry = f"\n## Week of {date_str}\n{summary_text}\n"
    try:
        with open(OBSIDIAN_WEEKLY, "a", encoding="utf-8") as f:
            f.write(entry)
        return True
    except Exception as e:
        print(f"[weekly summary error: {e}]")
        return False