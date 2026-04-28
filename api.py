import warnings
import logging
import os
import uuid
import tempfile
import threading
import time
import numpy as np

warnings.filterwarnings("ignore")
logging.getLogger("faster_whisper").setLevel(logging.ERROR)
logging.getLogger("sentence_transformers").setLevel(logging.ERROR)
logging.getLogger("chromadb").setLevel(logging.ERROR)
os.environ["TOKENIZERS_PARALLELISM"] = "false"

from fastapi import FastAPI, UploadFile, File
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from datetime import datetime
from anthropic import Anthropic
from dotenv import load_dotenv
from memory import FridayMemory
from tools import (web_search, read_file, write_file, gmail_read, gmail_send, gmail_search,
                   calendar_get, calendar_create, calendar_delete, spotify_play_song,
                   spotify_play_list, spotify_control, open_application, open_website,
                   youtube_search, focus_on, focus_off, browser_history,
                   finance_log_trade, finance_market_prices, finance_sentiment,
                   finance_weekly_pnl, finance_patterns,
                   content_trending, content_comments, content_channel_stats,
                   content_upload_time, content_top_videos, content_video_ideas,
                   content_script, content_suggestions,
                   brightness_set, volume_set, volume_mute, volume_unmute,
                   college_summarise_file, college_summarise_text, college_quiz,
                   college_add_assignment, college_get_assignments, college_mark_done,
                   college_find_papers, college_explain,
                   prod_review_code, prod_draft_email, prod_log_habit, prod_habit_summary,
                   prod_clipboard_save, prod_clipboard_search, prod_clipboard_list,
                   prod_log_expense, prod_spending_summary)
from behaviour import log_interaction, get_behaviour_context
from briefing import get_briefing_if_due, get_market_brief
from scheduler import start_scheduler, get_notifications, clear_notifications, set_dnd
from college import read_any_file
from productivity import review_uploaded_code
from router import is_complex, ask_ollama, is_ollama_running

load_dotenv()

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"]
)

try:
    client = Anthropic()
except Exception:
    client = None

memory    = FridayMemory()
scheduler = start_scheduler()

conversation_history  = []
action_log            = []
pending_confirmation  = {}
uploaded_file_context = {}

# ── VOICE STATE ───────────────────────────────────────────────────────────────
recording_active = False
recording_frames = []
recording_thread = None
voice_result     = {"status": "idle", "text": ""}

SILENCE_THRESHOLD = 0.008   # volume below this = silence
SILENCE_DURATION  = 2.5     # seconds of silence before auto-stop
MIN_SPEECH_SECS   = 0.5     # minimum speech before VAD kicks in

class MessageRequest(BaseModel):
    message: str

class MessageResponse(BaseModel):
    reply: str
    tools_used: list
    needs_confirmation: bool = False
    confirmation_id: str = ""
    confirmation_details: str = ""

class ConfirmRequest(BaseModel):
    confirmation_id: str
    confirmed: bool

TOOL_DEFINITIONS = [
    {"name": "web_search", "description": "Search the internet.", "input_schema": {"type": "object", "properties": {"query": {"type": "string"}}, "required": ["query"]}},
    {"name": "gmail_read", "description": "Read unread emails.", "input_schema": {"type": "object", "properties": {}, "required": []}},
    {"name": "gmail_send", "description": "Send an email. Always confirm.", "input_schema": {"type": "object", "properties": {"to": {"type": "string"}, "subject": {"type": "string"}, "body": {"type": "string"}}, "required": ["to", "subject", "body"]}},
    {"name": "gmail_search", "description": "Search emails.", "input_schema": {"type": "object", "properties": {"query": {"type": "string"}}, "required": ["query"]}},
    {"name": "calendar_get", "description": "Get upcoming calendar events.", "input_schema": {"type": "object", "properties": {}, "required": []}},
    {"name": "calendar_create", "description": "Create a calendar event. Always confirm.", "input_schema": {"type": "object", "properties": {"summary": {"type": "string"}, "start_time": {"type": "string"}, "end_time": {"type": "string"}, "description": {"type": "string"}, "location": {"type": "string"}}, "required": ["summary", "start_time", "end_time"]}},
    {"name": "calendar_delete", "description": "Delete a calendar event by ID.", "input_schema": {"type": "object", "properties": {"event_id": {"type": "string"}}, "required": ["event_id"]}},
    {"name": "read_file", "description": "Read a file from the laptop.", "input_schema": {"type": "object", "properties": {"path": {"type": "string"}}, "required": ["path"]}},
    {"name": "write_file", "description": "Write a file. For Obsidian logs use: C:\\Users\\meena\\Documents\\Builder_Brain\\FRIDAY'S LOGS\\Daily Log.md", "input_schema": {"type": "object", "properties": {"path": {"type": "string"}, "content": {"type": "string"}}, "required": ["path", "content"]}},
    {"name": "spotify_play_song", "description": "Play a song on Spotify.", "input_schema": {"type": "object", "properties": {"query": {"type": "string"}}, "required": ["query"]}},
    {"name": "spotify_play_list", "description": "Play a playlist on Spotify.", "input_schema": {"type": "object", "properties": {"name": {"type": "string"}}, "required": ["name"]}},
    {"name": "spotify_control", "description": "Control Spotify — pause, next, current.", "input_schema": {"type": "object", "properties": {"action": {"type": "string"}}, "required": ["action"]}},
    {"name": "open_application", "description": "Open an app e.g. spotify, chrome, vs code, obsidian.", "input_schema": {"type": "object", "properties": {"app_name": {"type": "string"}}, "required": ["app_name"]}},
    {"name": "open_website", "description": "Open a website.", "input_schema": {"type": "object", "properties": {"url": {"type": "string"}}, "required": ["url"]}},
    {"name": "youtube_search", "description": "Search YouTube.", "input_schema": {"type": "object", "properties": {"query": {"type": "string"}}, "required": ["query"]}},
    {"name": "focus_on", "description": "Turn on focus mode.", "input_schema": {"type": "object", "properties": {}, "required": []}},
    {"name": "focus_off", "description": "Turn off focus mode.", "input_schema": {"type": "object", "properties": {}, "required": []}},
    {"name": "browser_history", "description": "Search Chrome browser history.", "input_schema": {"type": "object", "properties": {"query": {"type": "string"}}, "required": ["query"]}},
    {"name": "market_brief", "description": "Get Gold and MES1 futures update.", "input_schema": {"type": "object", "properties": {}, "required": []}},
    {"name": "finance_log_trade", "description": "Log a trade to journal.", "input_schema": {"type": "object", "properties": {"entry_text": {"type": "string"}}, "required": ["entry_text"]}},
    {"name": "finance_market_prices", "description": "Get MES1, MGCJ25, Gold prices.", "input_schema": {"type": "object", "properties": {}, "required": []}},
    {"name": "finance_sentiment", "description": "Get news sentiment for an asset.", "input_schema": {"type": "object", "properties": {"asset": {"type": "string"}}, "required": ["asset"]}},
    {"name": "finance_weekly_pnl", "description": "Get monthly P&L summary.", "input_schema": {"type": "object", "properties": {}, "required": []}},
    {"name": "finance_patterns", "description": "Analyse trading patterns.", "input_schema": {"type": "object", "properties": {}, "required": []}},
    {"name": "content_trending", "description": "Trending YouTube videos in finance niche.", "input_schema": {"type": "object", "properties": {"niche": {"type": "string"}}, "required": []}},
    {"name": "content_comments", "description": "Summarise YouTube video comments.", "input_schema": {"type": "object", "properties": {"video_url": {"type": "string"}}, "required": ["video_url"]}},
    {"name": "content_channel_stats", "description": "Get YouTube channel stats.", "input_schema": {"type": "object", "properties": {"channel": {"type": "string"}}, "required": []}},
    {"name": "content_upload_time", "description": "Best upload time for channel.", "input_schema": {"type": "object", "properties": {"channel": {"type": "string"}}, "required": []}},
    {"name": "content_top_videos", "description": "Top performing videos.", "input_schema": {"type": "object", "properties": {"channel": {"type": "string"}}, "required": []}},
    {"name": "content_video_ideas", "description": "Generate YouTube video ideas.", "input_schema": {"type": "object", "properties": {"niche": {"type": "string"}}, "required": []}},
    {"name": "content_script", "description": "Generate script outline for topic.", "input_schema": {"type": "object", "properties": {"topic": {"type": "string"}}, "required": ["topic"]}},
    {"name": "content_suggestions", "description": "Content suggestions from channel stats.", "input_schema": {"type": "object", "properties": {"channel": {"type": "string"}}, "required": []}},
    {"name": "brightness_set", "description": "Set screen brightness 0-100.", "input_schema": {"type": "object", "properties": {"level": {"type": "integer"}}, "required": ["level"]}},
    {"name": "volume_set", "description": "Set system volume 0-100.", "input_schema": {"type": "object", "properties": {"level": {"type": "integer"}}, "required": ["level"]}},
    {"name": "volume_mute", "description": "Mute system volume.", "input_schema": {"type": "object", "properties": {}, "required": []}},
    {"name": "volume_unmute", "description": "Unmute system volume.", "input_schema": {"type": "object", "properties": {}, "required": []}},
    {"name": "college_summarise_file", "description": "Summarise a document from file path.", "input_schema": {"type": "object", "properties": {"filepath": {"type": "string"}}, "required": ["filepath"]}},
    {"name": "college_summarise_uploaded", "description": "Summarise the most recently uploaded file.", "input_schema": {"type": "object", "properties": {}, "required": []}},
    {"name": "college_quiz", "description": "Generate quiz from file path.", "input_schema": {"type": "object", "properties": {"filepath": {"type": "string"}, "num_questions": {"type": "integer"}}, "required": []}},
    {"name": "college_quiz_uploaded", "description": "Generate quiz from uploaded file.", "input_schema": {"type": "object", "properties": {"num_questions": {"type": "integer"}}, "required": []}},
    {"name": "college_add_assignment", "description": "Add an assignment to tracker.", "input_schema": {"type": "object", "properties": {"title": {"type": "string"}, "due_date": {"type": "string"}, "subject": {"type": "string"}}, "required": ["title", "due_date"]}},
    {"name": "college_get_assignments", "description": "Get pending assignments.", "input_schema": {"type": "object", "properties": {}, "required": []}},
    {"name": "college_mark_done", "description": "Mark assignment as done.", "input_schema": {"type": "object", "properties": {"title": {"type": "string"}}, "required": ["title"]}},
    {"name": "college_find_papers", "description": "Find research papers on a topic.", "input_schema": {"type": "object", "properties": {"topic": {"type": "string"}}, "required": ["topic"]}},
    {"name": "college_explain", "description": "Explain a concept. Level: simple, normal, deep.", "input_schema": {"type": "object", "properties": {"concept": {"type": "string"}, "level": {"type": "string"}}, "required": ["concept"]}},
    {"name": "prod_review_code", "description": "Review code for bugs and improvements.", "input_schema": {"type": "object", "properties": {"code": {"type": "string"}, "language": {"type": "string"}}, "required": ["code"]}},
    {"name": "prod_review_uploaded", "description": "Review the most recently uploaded code file.", "input_schema": {"type": "object", "properties": {}, "required": []}},
    {"name": "prod_draft_email", "description": "Draft an email. Tone: casual, professional, or formal.", "input_schema": {"type": "object", "properties": {"context": {"type": "string"}, "tone": {"type": "string"}}, "required": ["context"]}},
    {"name": "prod_log_habit", "description": "Log a habit or mood entry.", "input_schema": {"type": "object", "properties": {"entry": {"type": "string"}}, "required": ["entry"]}},
    {"name": "prod_habit_summary", "description": "Get habit and mood summary.", "input_schema": {"type": "object", "properties": {}, "required": []}},
    {"name": "prod_clipboard_save", "description": "Save a note to clipboard memory.", "input_schema": {"type": "object", "properties": {"note": {"type": "string"}}, "required": ["note"]}},
    {"name": "prod_clipboard_search", "description": "Search saved clipboard notes.", "input_schema": {"type": "object", "properties": {"query": {"type": "string"}}, "required": ["query"]}},
    {"name": "prod_clipboard_list", "description": "List all saved clipboard notes.", "input_schema": {"type": "object", "properties": {}, "required": []}},
    {"name": "prod_log_expense", "description": "Log an expense with description and amount.", "input_schema": {"type": "object", "properties": {"description": {"type": "string"}, "amount": {"type": "number"}, "currency": {"type": "string"}}, "required": ["description", "amount"]}},
    {"name": "prod_spending_summary", "description": "Get spending summary. Period: today, week, or month.", "input_schema": {"type": "object", "properties": {"period": {"type": "string"}}, "required": []}}
]

NEEDS_CONFIRMATION = {
    "write_file", "gmail_send", "calendar_create",
    "calendar_delete", "finance_log_trade"
}

BASE_SYSTEM_PROMPT = f"""You are FRIDAY, a smart and efficient personal assistant.
Today's date is {datetime.now().strftime('%A, %B %d %Y')}.
You are helpful, concise, and professional.
You remember everything said in this conversation.
IMPORTANT: When user says "log" followed by any text, ALWAYS use the write_file tool with path EXACTLY: C:\\Users\\meena\\Documents\\Builder_Brain\\FRIDAY'S LOGS\\FRIDAY LOGS.md and append the content. Never use any other path for logs.
If a file was recently uploaded, use the _uploaded variants of tools.
Present information directly and concisely."""


def execute_tool_direct(tool_name, tool_input):
    if tool_name == "web_search":                return web_search(tool_input["query"])
    elif tool_name == "read_file":               return read_file(tool_input["path"])
    elif tool_name == "gmail_read":              return gmail_read()
    elif tool_name == "gmail_search":            return gmail_search(tool_input["query"])
    elif tool_name == "calendar_get":            return calendar_get()
    elif tool_name == "spotify_play_song":       return spotify_play_song(tool_input["query"])
    elif tool_name == "spotify_play_list":       return spotify_play_list(tool_input["name"])
    elif tool_name == "spotify_control":         return spotify_control(tool_input["action"])
    elif tool_name == "open_application":        return open_application(tool_input["app_name"])
    elif tool_name == "open_website":            return open_website(tool_input["url"])
    elif tool_name == "youtube_search":          return youtube_search(tool_input["query"])
    elif tool_name == "focus_on":                return focus_on()
    elif tool_name == "focus_off":               return focus_off()
    elif tool_name == "browser_history":         return browser_history(tool_input["query"])
    elif tool_name == "market_brief":            return get_market_brief()
    elif tool_name == "finance_market_prices":   return finance_market_prices()
    elif tool_name == "finance_sentiment":       return finance_sentiment(tool_input["asset"])
    elif tool_name == "finance_weekly_pnl":      return finance_weekly_pnl()
    elif tool_name == "finance_patterns":        return finance_patterns()
    elif tool_name == "content_trending":        return content_trending(tool_input.get("niche", "futures trading finance"))
    elif tool_name == "content_comments":        return content_comments(tool_input["video_url"])
    elif tool_name == "content_channel_stats":   return content_channel_stats(tool_input.get("channel", "main"))
    elif tool_name == "content_upload_time":     return content_upload_time(tool_input.get("channel", "main"))
    elif tool_name == "content_top_videos":      return content_top_videos(tool_input.get("channel", "main"))
    elif tool_name == "content_video_ideas":     return content_video_ideas(tool_input.get("niche", "futures trading finance"))
    elif tool_name == "content_script":          return content_script(tool_input["topic"])
    elif tool_name == "content_suggestions":     return content_suggestions(tool_input.get("channel", "main"))
    elif tool_name == "brightness_set":          return brightness_set(tool_input["level"])
    elif tool_name == "volume_set":              return volume_set(tool_input["level"])
    elif tool_name == "volume_mute":             return volume_mute()
    elif tool_name == "volume_unmute":           return volume_unmute()
    elif tool_name == "college_summarise_file":  return college_summarise_file(tool_input["filepath"])
    elif tool_name == "college_summarise_uploaded":
        ctx = uploaded_file_context.get("last")
        return college_summarise_text(ctx["content"]) if ctx else "No file uploaded."
    elif tool_name == "college_quiz":            return college_quiz(filepath=tool_input.get("filepath"), num_questions=tool_input.get("num_questions", 5))
    elif tool_name == "college_quiz_uploaded":
        ctx = uploaded_file_context.get("last")
        return college_quiz(text=ctx["content"], num_questions=tool_input.get("num_questions", 5)) if ctx else "No file uploaded."
    elif tool_name == "college_add_assignment":  return college_add_assignment(tool_input["title"], tool_input["due_date"], tool_input.get("subject", ""))
    elif tool_name == "college_get_assignments": return college_get_assignments()
    elif tool_name == "college_mark_done":       return college_mark_done(tool_input["title"])
    elif tool_name == "college_find_papers":     return college_find_papers(tool_input["topic"])
    elif tool_name == "college_explain":         return college_explain(tool_input["concept"], tool_input.get("level", "normal"))
    elif tool_name == "prod_review_code":        return prod_review_code(tool_input["code"], tool_input.get("language", ""))
    elif tool_name == "prod_review_uploaded":
        ctx = uploaded_file_context.get("last")
        return review_uploaded_code(ctx["content"], ctx.get("filename", "")) if ctx else "No file uploaded."
    elif tool_name == "prod_draft_email":        return prod_draft_email(tool_input["context"], tool_input.get("tone", "professional"))
    elif tool_name == "prod_log_habit":          return prod_log_habit(tool_input["entry"])
    elif tool_name == "prod_habit_summary":      return prod_habit_summary()
    elif tool_name == "prod_clipboard_save":     return prod_clipboard_save(tool_input["note"])
    elif tool_name == "prod_clipboard_search":   return prod_clipboard_search(tool_input["query"])
    elif tool_name == "prod_clipboard_list":     return prod_clipboard_list()
    elif tool_name == "prod_log_expense":        return prod_log_expense(tool_input["description"], tool_input["amount"], tool_input.get("currency", "INR"))
    elif tool_name == "prod_spending_summary":   return prod_spending_summary(tool_input.get("period", "today"))
    else:                                        return f"Unknown tool: {tool_name}"


def execute_tool_confirmed(tool_name, tool_input):
    if tool_name == "write_file":
        path, content = tool_input["path"], tool_input["content"]
        mode = "a" if ".md" in path else "w"
        try:
            with open(path, mode, encoding="utf-8") as f:
                f.write("\n" + content)
            return f"Written to {path}"
        except Exception as e:
            return f"Write error: {str(e)}"
    elif tool_name == "gmail_send":        return gmail_send(tool_input["to"], tool_input["subject"], tool_input["body"])
    elif tool_name == "calendar_create":   return calendar_create(tool_input["summary"], tool_input["start_time"], tool_input["end_time"], tool_input.get("description", ""), tool_input.get("location", ""))
    elif tool_name == "calendar_delete":   return calendar_delete(tool_input["event_id"])
    elif tool_name == "finance_log_trade": return finance_log_trade(tool_input["entry_text"])
    return "Action completed."


def _transcribe(audio_data):
    import soundfile as sf
    from faster_whisper import WhisperModel
    audio_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "temp_audio.wav")
    sf.write(audio_path, audio_data, 16000)
    model    = WhisperModel("tiny", device="cpu", compute_type="int8")
    segments, _ = model.transcribe(audio_path, beam_size=1)
    return " ".join([s.text for s in segments]).strip()


@app.post("/upload")
async def upload_file(file: UploadFile = File(...)):
    try:
        contents = await file.read()
        ext      = os.path.splitext(file.filename)[1].lower()
        tmp_path = os.path.join(tempfile.gettempdir(), f"friday_upload{ext}")
        with open(tmp_path, "wb") as f:
            f.write(contents)
        content = read_any_file(tmp_path)
        uploaded_file_context["last"] = {"filename": file.filename, "content": content, "path": tmp_path}
        conversation_history.append({"role": "user", "content": f"[File uploaded: {file.filename}] Content preview: {content[:500]}..."})
        return {"status": "success", "filename": file.filename, "preview": content[:300]}
    except Exception as e:
        return {"status": "error", "message": str(e)}


@app.post("/start-listen")
async def start_listen():
    global recording_active, recording_frames, recording_thread, voice_result
    try:
        import sounddevice as sd
        recording_active = True
        recording_frames = []
        voice_result     = {"status": "listening", "text": ""}
        fs = 16000
        print("[VOICE] Recording started with VAD")

        def record():
            global recording_active, voice_result
            try:
                with sd.InputStream(samplerate=fs, channels=1, dtype='float32') as stream:
                    start = time.time()
                    while recording_active and (time.time() - start) < 4.0:
                        data, _ = stream.read(1024)
                        recording_frames.append(data.copy())

                print(f"[VOICE] Done. Frames: {len(recording_frames)}")

                if recording_frames:
                    voice_result = {"status": "processing", "text": ""}
                    audio_data   = np.concatenate(recording_frames, axis=0)
                    text         = _transcribe(audio_data)
                    print(f"[VOICE] Transcribed: '{text}'")
                    voice_result = {"status": "done", "text": text}
                else:
                    voice_result = {"status": "empty", "text": ""}

            except Exception as e:
                print(f"[VOICE] Error: {str(e)}")
                voice_result = {"status": "error", "text": ""}

        recording_thread = threading.Thread(target=record, daemon=True)
        recording_thread.start()
        return {"status": "recording"}
    except Exception as e:
        return {"status": "error", "error": str(e)}


@app.post("/stop-listen")
async def stop_listen():
    global recording_active, recording_thread, voice_result
    recording_active = False
    if recording_thread:
        recording_thread.join(timeout=5)

    if voice_result.get("status") == "done":
        return {"text": voice_result["text"], "status": "ok"}

    # if thread didn't finish transcribing yet, do it now
    if recording_frames:
        try:
            audio_data = np.concatenate(recording_frames, axis=0)
            text       = _transcribe(audio_data)
            voice_result = {"status": "done", "text": text}
            return {"text": text, "status": "ok"}
        except Exception as e:
            return {"text": "", "status": "error", "error": str(e)}

    return {"text": "", "status": "empty"}


@app.get("/voice-result")
async def get_voice_result():
    return voice_result


@app.post("/chat")
async def chat(request: MessageRequest):
    user_message = request.message
    tools_used   = []

    memory_context     = memory.build_memory_prompt(user_message)
    full_system_prompt = BASE_SYSTEM_PROMPT + get_behaviour_context()
    if memory_context:
        full_system_prompt += f"\n{memory_context}"
    if uploaded_file_context.get("last"):
        full_system_prompt += f"\nRecently uploaded: {uploaded_file_context['last']['filename']}. Use _uploaded tool variants."

    if not is_complex(user_message) and is_ollama_running():
        reply = ask_ollama(user_message, conversation_history)
        if reply:
            conversation_history.append({"role": "user", "content": user_message})
            conversation_history.append({"role": "assistant", "content": reply})
            log_interaction(user_message, reply, [])
            return MessageResponse(reply=reply, tools_used=[])

    if client is None:
        return MessageResponse(reply="Claude API unavailable. Add credits at console.anthropic.com", tools_used=[])

    conversation_history.append({"role": "user", "content": user_message})

    while True:
        response = client.messages.create(
            model="claude-sonnet-4-5",
            max_tokens=1024,
            system=full_system_prompt,
            tools=TOOL_DEFINITIONS,
            messages=conversation_history
        )

        if response.stop_reason == "tool_use":
            conversation_history.append({"role": "assistant", "content": response.content})
            tool_results = []
            conf_needed  = None

            for block in response.content:
                if block.type != "tool_use":
                    continue
                tool_name  = block.name
                tool_input = block.input
                tools_used.append(tool_name)

                if tool_name in NEEDS_CONFIRMATION:
                    conf_id = str(uuid.uuid4())[:8]
                    pending_confirmation[conf_id] = {"tool_name": tool_name, "tool_input": tool_input, "tool_use_id": block.id}
                    if tool_name == "write_file":
                        details = f"Write to:\n{tool_input['path']}\n\nPreview:\n{tool_input['content'][:300]}"
                    elif tool_name == "gmail_send":
                        details = f"Send to: {tool_input['to']}\nSubject: {tool_input['subject']}\n\n{tool_input['body'][:300]}"
                    elif tool_name == "calendar_create":
                        details = f"Create: {tool_input['summary']}\nTime: {tool_input['start_time']} → {tool_input['end_time']}"
                    elif tool_name == "calendar_delete":
                        details = f"Delete event ID: {tool_input['event_id']}"
                    elif tool_name == "finance_log_trade":
                        details = f"Log trade:\n{tool_input['entry_text']}"
                    else:
                        details = str(tool_input)
                    conf_needed = (conf_id, details)
                    break

                try:
                    tool_result = execute_tool_direct(tool_name, tool_input)
                except Exception as e:
                    tool_result = f"Tool error: {str(e)}"

                action_log.append({"timestamp": datetime.now().strftime("%H:%M:%S"), "tool": tool_name, "input": str(tool_input), "result": str(tool_result)[:200]})
                tool_results.append({"type": "tool_result", "tool_use_id": block.id, "content": str(tool_result)})

            if conf_needed:
                conversation_history.pop()
                conf_id, details = conf_needed
                return MessageResponse(reply="I need your confirmation before proceeding.", tools_used=tools_used, needs_confirmation=True, confirmation_id=conf_id, confirmation_details=details)

            if tool_results:
                conversation_history.append({"role": "user", "content": tool_results})

        else:
            friday_reply = ""
            for block in response.content:
                if hasattr(block, 'text'):
                    friday_reply = block.text
                    break
            if not friday_reply:
                friday_reply = "I couldn't generate a response."

            conversation_history.append({"role": "assistant", "content": friday_reply})
            memory.save_memory(f"User: {user_message} | FRIDAY: {friday_reply}")
            log_interaction(user_message, friday_reply, tools_used)
            return MessageResponse(reply=friday_reply, tools_used=tools_used)


@app.post("/confirm")
async def confirm_action(request: ConfirmRequest):
    conf_id = request.confirmation_id
    if conf_id not in pending_confirmation:
        return {"status": "error", "message": "Confirmation ID not found"}
    pending    = pending_confirmation.pop(conf_id)
    tool_name  = pending["tool_name"]
    tool_input = pending["tool_input"]
    if not request.confirmed:
        conversation_history.append({"role": "user", "content": "Action cancelled."})
        conversation_history.append({"role": "assistant", "content": "Action cancelled."})
        return {"status": "cancelled", "reply": "Action cancelled."}
    try:
        result = execute_tool_confirmed(tool_name, tool_input)
    except Exception as e:
        result = f"Error: {str(e)}"
    action_log.append({"timestamp": datetime.now().strftime("%H:%M:%S"), "tool": tool_name, "input": str(tool_input), "result": str(result)[:200]})
    action_descriptions = {
        "write_file":        f"Done. Written to {tool_input.get('path', 'file')}.",
        "gmail_send":        f"Email sent to {tool_input.get('to', '')}.",
        "calendar_create":   f"Event '{tool_input.get('summary', '')}' created.",
        "calendar_delete":   "Event deleted.",
        "finance_log_trade": "Trade logged."
    }
    friday_reply = action_descriptions.get(tool_name, "Done.")
    conversation_history.append({"role": "user", "content": f"Action completed: {result}"})
    conversation_history.append({"role": "assistant", "content": friday_reply})
    return {"status": "confirmed", "reply": friday_reply}


@app.get("/briefing")
async def get_briefing():
    try:
        briefing = get_briefing_if_due()
        if briefing:
            return {"briefing": briefing, "has_briefing": True}
        return {"briefing": "", "has_briefing": False}
    except Exception as e:
        return {"briefing": "", "has_briefing": False, "error": str(e)}


@app.get("/notifications")
async def get_notifs():
    return {"notifications": get_notifications()}


@app.delete("/notifications")
async def clear_notifs():
    clear_notifications()
    return {"status": "cleared"}


@app.post("/dnd/{state}")
async def set_dnd_mode(state: str):
    from scheduler import release_dnd_notifications
    if state == "on":
        set_dnd(True)
        return {"status": "DND on"}
    else:
        set_dnd(False)
        release_dnd_notifications()
        return {"status": "DND off"}


@app.get("/memories")
async def get_memories():
    try:
        count = memory.collection.count()
        if count == 0:
            return {"memories": [], "count": 0}
        results = memory.collection.get()
        return {"memories": results.get("documents", []), "count": count}
    except Exception as e:
        return {"memories": [], "count": 0, "error": str(e)}


@app.get("/action-log")
async def get_action_log():
    return {"actions": action_log[-50:]}


@app.delete("/clear-history")
async def clear_history():
    conversation_history.clear()
    return {"status": "Conversation history cleared"}


@app.get("/status")
async def get_status():
    return {
        "status": "online",
        "model": "claude-sonnet-4-5",
        "memory_count": memory.collection.count(),
        "conversation_length": len(conversation_history),
        "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    }