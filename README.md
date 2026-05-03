# F.R.I.D.A.Y
**Fully Responsive Intelligent Digital Assistant for You**

A fully autonomous personal AI assistant built from scratch — solo, in 7 weeks.  
Voice-controlled. Persistent memory. Full laptop automation. Live trading tools. HAL 9000 UI.

---

## What FRIDAY Does

FRIDAY is a J.A.R.V.I.S.-style AI assistant that runs on your local machine and connects to the cloud only when it needs to. You talk to it, it understands you, and it gets things done.

- **Speak naturally** — wake word detection ("Hey FRIDAY"), three modes: voice, text, hybrid
- **Remembers everything** — 220+ memories stored in ChromaDB, recalled semantically across sessions
- **Searches the web** — real-time search via Tavily API, summarised and spoken back
- **Manages your life** — reads/sends Gmail, creates and reads Google Calendar events
- **Controls your laptop** — opens apps, plays Spotify, searches YouTube, checks browser history
- **Thinks locally or in the cloud** — routes simple tasks to Ollama (free, offline), complex tasks to Claude API
- **Tracks your trades** — voice trade journal, watchlist alerts, weekly P&L summaries, news sentiment
- **Briefs you every morning** — emails, calendar, market data (Nifty, BTC, watchlist) before you ask
- **Writes to Obsidian** — daily logs, decisions, and memory snapshots auto-written to your vault
- **Helps you study** — PDF summariser, quiz mode from syllabus, deadline tracker
- **Creates content** — YouTube idea generator, trend analysis, script research
- **Full dashboard** — React UI with live conversation, memory viewer, action log, status panel
- **HAL 9000 UI** — animated canvas background, pulsing red gradient, audio-reactive waveform

---

## Architecture

```
        ┌─────────────────────────────────────┐
        │            YOU  (Voice / Text)       │
        └──────────────────┬──────────────────┘
                           │
        ┌──────────────────▼──────────────────┐
        │         VOICE LAYER                  │
        │  faster-whisper  ◄──►  pyttsx3/TTS  │
        └──────────────────┬──────────────────┘
                           │
        ┌──────────────────▼──────────────────┐
        │     BRAIN LAYER  (Orchestrator)      │
        │  Local: Ollama + Llama 3.1           │
        │  Cloud: Claude API  (hard tasks)     │
        └──┬──────────┬──────────┬────────────┘
           │          │          │          │
      ┌────▼─┐  ┌────▼──┐  ┌───▼──┐  ┌───▼────┐
      │MEMORY│  │ WEB   │  │ CODE │  │AUTOMATE│
      │Chroma│  │Tavily │  │runner│  │OS/APIs │
      └──────┘  └───────┘  └──────┘  └────────┘
```

**Hybrid AI routing** — 80% of tasks run locally for free via Ollama. Complex reasoning routes to Claude API. Specialist models handle code (codellama), finance, and general queries.

---

## Tech Stack

| Category | Tool |
|----------|------|
| Voice Input | faster-whisper (local Whisper model) |
| Voice Output | pyttsx3 / edge-tts |
| Brain (Local) | Ollama + Llama 3.1 |
| Brain (Cloud) | Claude API (Anthropic) |
| Long-term Memory | ChromaDB + sentence-transformers |
| Web Search | Tavily API |
| Email | Gmail API (OAuth) |
| Calendar | Google Calendar API |
| Laptop Automation | subprocess, pyautogui, Spotify API |
| Finance | yfinance, news sentiment NLP |
| Backend | FastAPI |
| Frontend | React |
| Knowledge Base | Obsidian (auto-written) |

---

## 16 Phases Built

| Phase | What Was Built |
|-------|---------------|
| 1 | Core chat loop — Claude API, conversation history, personality via system prompt |
| 2 | Persistent memory — ChromaDB vector database, semantic search across sessions |
| 3 | Tools — Tavily web search, file read/write, human-in-the-loop controls |
| 4 | Voice interface — wake word, speech-to-text, TTS, hybrid mode, ESC interrupt |
| 5 | Task automation — Gmail OAuth, send/read/search emails, Google Calendar |
| 6 | Web dashboard — FastAPI backend, React frontend, memory viewer, action log |
| 7 | Behavioural intelligence — pattern tracking, proactive suggestions, Obsidian brain |
| 8 | Ollama hybrid router — local/cloud routing, specialist models, cost optimisation |
| 9 | Laptop automation — Spotify, YouTube, browser history, focus mode, app control |
| 10 | Smart notifications — morning briefing, deadline nagger, daily market brief |
| 11 | Finance tools — voice trade journal, watchlist, news sentiment, weekly P&L |
| 12 | YouTube + content — idea generator, trend analysis, script research, comment summariser |
| 13 | Knowledge + college — PDF summariser, quiz mode, assignment tracker, concept explainer |
| 14 | Productivity tools — task manager, focus sessions, habit tracker |
| 15 | Discord integration — commands, notifications, remote control via Discord |
| 16 | HAL 9000 UI — animated canvas, pulsing red gradient, audio-reactive waveform |

---

## Safety — Human-in-the-Loop

FRIDAY never acts without permission. Three layers of control:

- **Confirm before acting** — asks before sending emails, deleting files, or making changes
- **Permission scopes** — config file defines what FRIDAY can and cannot access
- **Kill switches** — say "stop" or "abort" to halt mid-task; full audit log of every action

---

## How to Run

### Terminal Mode
```powershell
cd ARIA
venv\Scripts\activate
python friday.py
```

### Dashboard Mode
```powershell
# Terminal 1 — API backend
cd ARIA
venv\Script\activate.ps1
uvicorn api:app --reload --port 8000

# Terminal 2 — React frontend
cd friday-dashboard
npm start
.\node_modules\.bin\electron.cmd electron.js
```

---

## Setup

1. Clone the repo
2. Create venv: `python -m venv venv` then `venv\Scripts\activate`
3. Install dependencies: `pip install anthropic python-dotenv chromadb sentence-transformers requests faster-whisper edge-tts sounddevice scipy numpy google-auth google-auth-oauthlib google-api-python-client pyautogui fastapi uvicorn`
4. Add your API keys to a `.env` file:
```
ANTHROPIC_API_KEY= Anthropic_key
TAVILY_API_KEY= Tavily_Key
SPOTIFY_CLIENT_ID= Spotify_Key
SPOTIFY_CLIENT_SECRET= Spotify Client Key
```
5. Run `python friday.py`

> **Note:** Gmail and Google Calendar require OAuth setup. Follow Google's guide to generate `credentials.json` and place it in the root directory.

---

## File Structure

```
ARIA/
  friday.py          ← main program (brain + orchestration)
  memory.py          ← ChromaDB long-term memory system
  tools.py           ← web search, file read/write, automation
  voice.py           ← voice interface
  api.py             ← FastAPI backend
  .env               ← API keys ((Confidential)
  .gitignore
  friday_memory/     ← ChromaDB stores data here
  friday-dashboard/  ← React frontend
  venv/
```

---

*Built from scratch. Solo. 7 weeks. No tutorial followed end-to-end.*  
*Every architectural decision made independently.*
