import os
import json
import requests
from datetime import datetime
from anthropic import Anthropic
from dotenv import load_dotenv

load_dotenv()

client = Anthropic()

OBSIDIAN_TRADING = r"C:\Users\meena\Documents\Builder_Brain\Trading Journal"
POLYGON_KEY = os.getenv("POLYGON_API_KEY")

TICKER_MAP = {
    "MES1":   "MES",
    "MGCJ25": "MGC",
    "Gold":   "GC",
    "gold":   "GC"
}


def _get_polygon_price(symbol):
    try:
        # try last trade first
        url = f"https://api.polygon.io/v2/last/trade/{symbol}"
        r = requests.get(url, params={"apiKey": POLYGON_KEY}, timeout=5)
        data = r.json()
        if data.get("status") == "OK" and data.get("results"):
            price = data["results"]["p"]
            return f"${price:,.2f}"
        # fallback to previous close
        url2 = f"https://api.polygon.io/v2/aggs/ticker/{symbol}/prev"
        r2 = requests.get(url2, params={"apiKey": POLYGON_KEY}, timeout=5)
        data2 = r2.json()
        if data2.get("resultsCount", 0) > 0:
            price = data2["results"][0]["c"]
            return f"${price:,.2f} (prev close)"
        return "unavailable"
    except Exception as e:
        return f"unavailable"


def _tavily_search(query):
    try:
        url = "https://api.tavily.com/search"
        headers = {
            "Authorization": f"Bearer {os.getenv('TAVILY_API_KEY')}",
            "Content-Type": "application/json"
        }
        r = requests.post(url, headers=headers, json={
            "query": query,
            "search_depth": "basic",
            "max_results": 3
        })
        results = r.json().get("results", [])
        return "\n".join([res.get("content", "")[:200] for res in results])
    except:
        return "Search unavailable"


def log_trade(entry_text):
    response = client.messages.create(
        model="claude-sonnet-4-5",
        max_tokens=300,
        system='You extract trade details. Return ONLY this JSON with no markdown, no explanation: {"instrument": "MES1", "direction": "long", "entry": 5200, "stop": 5180, "target": 5240, "notes": ""}. Rules: bought/long = "long", sold/short = "short". Extract numbers as integers/floats. Instrument: look for MES1, MGCJ25, Gold, ES, NQ. If field missing use null.',
        messages=[{"role": "user", "content": entry_text}]
    )

    try:
        raw = response.content[0].text.strip()
        raw = raw.replace("```json", "").replace("```", "").strip()
        trade = json.loads(raw)
    except:
        trade = {"notes": entry_text}

    date_str = datetime.now().strftime("%Y-%m-%d")
    time_str = datetime.now().strftime("%H:%M")
    month    = datetime.now().strftime("%B %Y")

    rr = ""
    try:
        if trade.get("entry") and trade.get("stop") and trade.get("target"):
            risk   = abs(float(trade["entry"]) - float(trade["stop"]))
            reward = abs(float(trade["target"]) - float(trade["entry"]))
            if risk > 0:
                rr = f"{reward/risk:.1f}R"
    except:
        pass

    lines = [
        "",
        f"## Trade — {date_str} {time_str}",
        f"- **Instrument:** {trade.get('instrument', 'Unknown')}",
        f"- **Direction:** {trade.get('direction', 'Unknown')}",
        f"- **Entry:** {trade.get('entry', 'N/A')}",
        f"- **Stop:** {trade.get('stop', 'N/A')}",
        f"- **Target:** {trade.get('target', 'N/A')}",
        f"- **R:R:** {rr if rr else 'N/A'}",
        f"- **Notes:** {trade.get('notes', '')}",
        "- **Result:** Pending",
        ""
    ]
    entry_md = "\n".join(lines)

    filepath = os.path.join(OBSIDIAN_TRADING, f"{month}.md")
    with open(filepath, "a", encoding="utf-8") as f:
        f.write(entry_md)

    return f"Trade logged to {month}.md. R:R = {rr if rr else 'N/A'}"


def get_market_prices():
    prices = {}
    prices["MES1"]   = _get_polygon_price("MES")
    prices["MGCJ25"] = _get_polygon_price("MGC")
    prices["Gold"]   = _get_polygon_price("GC")

    result = (
        f"MES1 (Micro E-mini S&P): {prices['MES1']}\n"
        f"MGCJ25 (Micro Gold): {prices['MGCJ25']}\n"
        f"Gold (GC): {prices['Gold']}"
    )
    return result


def get_sentiment(asset):
    news = _tavily_search(f"{asset} futures news sentiment today")
    prompt = f"{asset} news:\n{news}"
    response = client.messages.create(
        model="claude-sonnet-4-5",
        max_tokens=150,
        system="Summarise market sentiment in 2-3 lines. State if bullish, bearish or neutral and why. Be direct.",
        messages=[{"role": "user", "content": prompt}]
    )
    return response.content[0].text.strip()


def get_weekly_pnl():
    try:
        month    = datetime.now().strftime("%B %Y")
        filepath = os.path.join(OBSIDIAN_TRADING, f"{month}.md")
        if not os.path.exists(filepath):
            return "No trades logged this month yet."
        with open(filepath, "r", encoding="utf-8") as f:
            content = f.read()
        response = client.messages.create(
            model="claude-sonnet-4-5",
            max_tokens=200,
            system="Analyse the trade journal and give a brief summary: total trades, pending vs closed, any patterns noticed. Be concise.",
            messages=[{"role": "user", "content": content}]
        )
        return response.content[0].text.strip()
    except Exception as e:
        return f"Error reading journal: {str(e)}"


def get_trading_patterns():
    try:
        month    = datetime.now().strftime("%B %Y")
        filepath = os.path.join(OBSIDIAN_TRADING, f"{month}.md")
        if not os.path.exists(filepath):
            return "No trades logged yet to analyse patterns."
        with open(filepath, "r", encoding="utf-8") as f:
            content = f.read()
        response = client.messages.create(
            model="claude-sonnet-4-5",
            max_tokens=200,
            system="Identify trading patterns: best instruments, common mistakes, R:R averages, time patterns. Be specific and actionable.",
            messages=[{"role": "user", "content": content}]
        )
        return response.content[0].text.strip()
    except Exception as e:
        return f"Error: {str(e)}"