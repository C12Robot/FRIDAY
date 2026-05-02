import requests

OLLAMA_URL = "http://localhost:11434/api/generate"

MODELS = {
    "code":    "deepseek-coder:6.7b",
    "general": "qwen3.5:9b",
    "fast":    "deepseek-r1:8b"
}

CODE_KEYWORDS = [
    "code", "function", "script", "bug", "error", "debug", "fix",
    "python", "javascript", "html", "css", "program", "class",
    "import", "variable", "loop", "array", "api", "json", "build"
]

COMPLEX_KEYWORDS = [
    "email", "gmail", "calendar", "schedule", "search", "find",
    "write file", "read file", "remind", "create event", "send",
    "look up", "what's happening", "news", "weather",
    "memory", "remember",
    "play", "spotify", "pause", "next song", "current song",
    "open", "launch", "focus mode", "youtube", "history", "browser history", "visited", "search history",
    "log habit", "log mood", "log expense", "remember this",
    "what did i save", "clipboard", "spending", "how much", "youtube", "channel", "analytics", "stats", "upload time",
    "top videos", "video ideas", "script", "trending"
]

FAST_KEYWORDS = [
    "hi", "hello", "hey", "thanks", "ok", "okay", "yes", "no",
    "what time", "how are you", "good morning", "good night"
]

def pick_model(message):
    msg_lower = message.lower()
    if any(k in msg_lower for k in CODE_KEYWORDS):
        return MODELS["code"]
    if any(k in msg_lower for k in FAST_KEYWORDS) or len(message.split()) < 5:
        return MODELS["fast"]
    return MODELS["general"]

def is_complex(message):
    msg_lower = message.lower()
    return any(k in msg_lower for k in COMPLEX_KEYWORDS)

def ask_ollama(message, conversation_history=[]):
    model = pick_model(message)
    try:
        context = ""
        for msg in conversation_history[-4:]:
            if isinstance(msg["content"], str):
                role = "User" if msg["role"] == "user" else "FRIDAY"
                context += f"{role}: {msg['content']}\n"

        prompt = f"""You are FRIDAY, a smart personal assistant. Be concise and helpful.

{context}User: {message}
FRIDAY:"""

        response = requests.post(OLLAMA_URL, json={
            "model": model,
            "prompt": prompt,
            "stream": False
        }, timeout=60)

        if response.status_code == 200:
            reply = response.json().get("response", "").strip()
            print(f"  [local: {model}]")
            return reply
        return None
    except Exception as e:
        return None

def is_ollama_running():
    try:
        requests.get("http://localhost:11434", timeout=3)
        return True
    except:
        return False