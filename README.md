# F.R.I.D.A.Y
**Fully Responsive Intelligent Digital Assistant for You**

A personal AI assistant built from scratch with voice control, 
persistent memory, web search, email and calendar automation, 
and a full web dashboard.

## Features
- Voice control with wake word detection — say "Hey FRIDAY"
- Three modes — text, voice, hybrid
- Persistent semantic memory using ChromaDB
- Real-time web search via Tavily API
- Gmail read, search and send
- Google Calendar read and create events
- FastAPI backend + React dashboard
- Human-in-the-loop safety controls

## Tech Stack
Python, Claude API, ChromaDB, faster-whisper, 
pyttsx3, FastAPI, React, Gmail API, Google Calendar API

## Phases Built
- Phase 1 — Core chat loop
- Phase 2 — Persistent memory
- Phase 3 — Web search + file tools
- Phase 4 — Voice interface
- Phase 5 — Email + calendar automation
- Phase 6 — Web dashboard

## How to Run

### Terminal Mode
```powershell
cd C:\Users\meena\Documents\ARIA
venv\Scripts\activate
python friday.py
```

### Dashboard Mode
```powershell
# Terminal 1 — API backend
uvicorn api:app --reload --port 8000

# Terminal 2 — React frontend  
cd C:\Users\meena\Documents\friday-dashboard
npm start
```

## Setup
1. Clone the repo
2. Create venv and install dependencies
3. Add API keys to .env file
4. Run python friday.py