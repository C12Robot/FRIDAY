import warnings
import logging
import os

warnings.filterwarnings("ignore")
logging.getLogger("faster_whisper").setLevel(logging.ERROR)
logging.getLogger("sentence_transformers").setLevel(logging.ERROR)
logging.getLogger("chromadb").setLevel(logging.ERROR)
os.environ["TOKENIZERS_PARALLELISM"] = "false"

import json
import re
import time
import voice
from datetime import datetime
from anthropic import Anthropic
from dotenv import load_dotenv
from memory import FridayMemory
from voice import speak, get_input, stop_speaking, start_wake_word_listener, stop_wake_word_listener
from tools import (web_search, read_file, write_file, gmail_read, gmail_send, gmail_search,
                   calendar_get, calendar_create, spotify_play_song, spotify_play_list,
                   spotify_control, open_application, open_website, youtube_search,
                   focus_on, focus_off, browser_history)
from behaviour import (log_interaction, get_behaviour_context,
                       write_obsidian_log, detect_and_log_decision,
                       is_weekly_summary_due, generate_weekly_summary,
                       write_weekly_summary)
from router import is_complex, ask_ollama, is_ollama_running
from file_manager import search_files, open_file, index_files, init_db

load_dotenv()
if not os.getenv("ANTHROPIC_API_KEY"):
    raise ValueError("ANTHROPIC_API_KEY not set in .env")

client = Anthropic()
memory = FridayMemory()
init_db()
import threading
threading.Thread(target=index_files, daemon=True).start()

TOOL_DEFINITIONS = [
    {
        "name": "web_search",
        "description": "Search the internet for current information, news, or anything FRIDAY doesn't know.",
        "input_schema": {
            "type": "object",
            "properties": {
                "query": {"type": "string", "description": "The search query to look up"}
            },
            "required": ["query"]
        }
    },
    {
        "name": "read_file",
        "description": "Read the contents of a file from the user's laptop.",
        "input_schema": {
            "type": "object",
            "properties": {
                "path": {"type": "string", "description": "The full file path to read"}
            },
            "required": ["path"]
        }
    },
    {
        "name": "write_file",
        "description": "Write content to a file on the user's laptop. Always asks user for confirmation first.",
        "input_schema": {
            "type": "object",
            "properties": {
                "path": {"type": "string", "description": "The full file path to write to"},
                "content": {"type": "string", "description": "The content to write to the file"}
            },
            "required": ["path", "content"]
        }
    },
    {
        "name": "gmail_read",
        "description": "Read the user's unread emails from Gmail.",
        "input_schema": {"type": "object", "properties": {}, "required": []}
    },
    {
        "name": "gmail_send",
        "description": "Send an email on behalf of the user. Always shows preview and asks confirmation first.",
        "input_schema": {
            "type": "object",
            "properties": {
                "to": {"type": "string", "description": "Recipient email address"},
                "subject": {"type": "string", "description": "Email subject line"},
                "body": {"type": "string", "description": "Email body content"}
            },
            "required": ["to", "subject", "body"]
        }
    },
    {
        "name": "gmail_search",
        "description": "Search through the user's Gmail with a query.",
        "input_schema": {
            "type": "object",
            "properties": {
                "query": {"type": "string", "description": "Gmail search query"}
            },
            "required": ["query"]
        }
    },
    {
        "name": "calendar_get",
        "description": "Get the user's upcoming Google Calendar events.",
        "input_schema": {"type": "object", "properties": {}, "required": []}
    },
    {
        "name": "calendar_create",
        "description": "Create a new event in the user's Google Calendar.",
        "input_schema": {
            "type": "object",
            "properties": {
                "summary": {"type": "string", "description": "Event title or name"},
                "start_time": {"type": "string", "description": "Start time in ISO format"},
                "end_time": {"type": "string", "description": "End time in ISO format"},
                "description": {"type": "string", "description": "Optional event description"},
                "location": {"type": "string", "description": "Optional event location"}
            },
            "required": ["summary", "start_time", "end_time"]
        }
    },
    {
        "name": "spotify_play_song",
        "description": "Play a song on Spotify. Use when user asks to play a specific song or artist.",
        "input_schema": {
            "type": "object",
            "properties": {
                "query": {"type": "string", "description": "Song name or artist to search and play"}
            },
            "required": ["query"]
        }
    },
    {
        "name": "spotify_play_list",
        "description": "Play a playlist on Spotify by name.",
        "input_schema": {
            "type": "object",
            "properties": {
                "name": {"type": "string", "description": "Playlist name to search and play"}
            },
            "required": ["name"]
        }
    },
    {
        "name": "spotify_control",
        "description": "Control Spotify playback — pause, skip to next track, or check what's currently playing.",
        "input_schema": {
            "type": "object",
            "properties": {
                "action": {"type": "string", "description": "Action: pause, next, or current"}
            },
            "required": ["action"]
        }
    },
    {
        "name": "open_application",
        "description": "Open an application on the user's laptop by name.",
        "input_schema": {
            "type": "object",
            "properties": {
                "app_name": {"type": "string", "description": "Name of the app to open e.g. spotify, vs code, chrome"}
            },
            "required": ["app_name"]
        }
    },
    {
        "name": "open_website",
        "description": "Open a website or URL in the browser.",
        "input_schema": {
            "type": "object",
            "properties": {
                "url": {"type": "string", "description": "URL or website to open"}
            },
            "required": ["url"]
        }
    },
    {
        "name": "youtube_search",
        "description": "Search YouTube and open the results in the browser.",
        "input_schema": {
            "type": "object",
            "properties": {
                "query": {"type": "string", "description": "Search query for YouTube"}
            },
            "required": ["query"]
        }
    },
    {
        "name": "focus_on",
        "description": "Turn on focus mode — blocks distracting websites like YouTube, Instagram, Reddit.",
        "input_schema": {"type": "object", "properties": {}, "required": []}
    },
    {
        "name": "focus_off",
        "description": "Turn off focus mode — unblocks all websites.",
        "input_schema": {"type": "object", "properties": {}, "required": []}
    },
    {
    "name": "browser_history",
    "description": "Search the user's Chrome browser history by keyword. Use this when user says 'search my history', 'what did I visit', 'find in my browser history', or anything about past browsing.",
    "input_schema": {
        "type": "object",
        "properties": {
            "query": {"type": "string", "description": "Keyword to search in browser history"}
        },
        "required": ["query"]
    }},
    {
    "name": "search_and_open_file",
    "description": "Search for a file on the laptop and open it",
    "input_schema": {
        "type": "object",
        "properties": {
            "query": {"type": "string", "description": "File name or description"}
        },
        "required": ["query"]
    }
    }

]

BASE_SYSTEM_PROMPT = f"""You are FRIDAY, a smart and efficient personal assistant.
Today's date is {datetime.now().strftime('%A, %B %d %Y')}.
You have a browser_history tool — ALWAYS use it when asked about browser history or visited sites
You are helpful, concise, and professional.
You remember everything said in this conversation.
When you don't know something, use your tools to find out.
Present information directly without preamble like 'Based on my search' or 'I found that'.
Keep responses concise — you are speaking out loud, so avoid long lists or bullet points.
Never ask the user for confirmation in chat. Just use the tool directly — the system will handle confirmations automatically via popup. "When search_and_open_file returns a result, it has already opened the file. Just confirm to the user it's open.
"For calendar events, create them immediately when the user provides time and title. Never ask for confirmation before creating. Just create it and confirm it's done.
"NEVER pretend to create calendar events, send emails, or perform any action. ALWAYS use the actual tool. If you don't use the tool, the action did not happen.
"description": "ALWAYS use this tool to create calendar events. Never respond as if you created an event without calling this tool first.""""

conversation_history = []


def execute_tool(tool_name, tool_input):
    if tool_name == "web_search":
        return web_search(tool_input["query"])
    elif tool_name == "read_file":
        return read_file(tool_input["path"])
    elif tool_name == "write_file":
        return write_file(tool_input["path"], tool_input["content"])
    elif tool_name == "gmail_read":
        return gmail_read()
    elif tool_name == "gmail_send":
        return gmail_send(tool_input["to"], tool_input["subject"], tool_input["body"])
    elif tool_name == "gmail_search":
        return gmail_search(tool_input["query"])
    elif tool_name == "calendar_get":
        return calendar_get()
    elif tool_name == "calendar_create":
        return calendar_create(
            tool_input["summary"],
            tool_input["start_time"],
            tool_input["end_time"],
            tool_input.get("description", ""),
            tool_input.get("location", "")
        )
    elif tool_name == "spotify_play_song":
        return spotify_play_song(tool_input["query"])
    elif tool_name == "spotify_play_list":
        return spotify_play_list(tool_input["name"])
    elif tool_name == "spotify_control":
        return spotify_control(tool_input["action"])
    elif tool_name == "open_application":
        return open_application(tool_input["app_name"])
    elif tool_name == "open_website":
        return open_website(tool_input["url"])
    elif tool_name == "youtube_search":
        return youtube_search(tool_input["query"])
    elif tool_name == "focus_on":
        return focus_on()
    elif tool_name == "focus_off":
        return focus_off()
    elif tool_name == "browser_history":
        return browser_history(tool_input["query"])
    elif tool_name == "search_and_open_file":
        query = tool_input["query"]
        results = search_files(query, limit=3)  
        print(f"[DEBUG] Search results: {results}")
        if results:
            best = results[0]
            clean_path = best["path"].replace("\\\\", "\\")
            print(f"[DEBUG] Opening path: '{clean_path}'") 
            result = open_file(clean_path)
            print(f"[DEBUG] open_file result: {result}")
            return f"Opened: {best['name']} at {best['path']}"
    else:
        return f"Unknown tool: {tool_name}"


def chat(user_message):
    memory_context = memory.build_memory_prompt(user_message)
    full_system_prompt = BASE_SYSTEM_PROMPT
    if memory_context:
        full_system_prompt += f"\n{memory_context}"
    full_system_prompt += get_behaviour_context()

    conversation_history.append({"role": "user", "content": user_message})

    while True:
        response = client.messages.create(
            model=os.getenv("ANTHROPIC_MODEL", "claude-sonnet-4-6"),
            max_tokens=600,
            system=full_system_prompt,
            tools=TOOL_DEFINITIONS,
            messages=conversation_history
        )

        if response.stop_reason == "tool_use":
            conversation_history.append({"role": "assistant", "content": response.content})

            tool_results = []
            for block in response.content:
                if block.type == "tool_use":
                    print(f"\n  🔧 FRIDAY is using {block.name}...", flush=True)
                    try:
                        tool_result = execute_tool(block.name, block.input)
                    except Exception as e:
                        tool_result = f"Tool error: {str(e)}"
                    tool_results.append({
                        "type": "tool_result",
                        "tool_use_id": block.id,
                        "content": str(tool_result)
                    })

            conversation_history.append({"role": "user", "content": tool_results})

        else:
            friday_reply = ""
            for block in response.content:
                if hasattr(block, 'text'):
                    friday_reply = block.text
                    break

            if not friday_reply:
                friday_reply = "I couldn't generate a response. Please try again."

            conversation_history.append({"role": "assistant", "content": friday_reply})

            memory.save_memory(f"User: {user_message} | FRIDAY: {friday_reply}")
            tools_used = [b.name for b in response.content if hasattr(b, 'type') and b.type == 'tool_use']
            log_interaction(user_message, friday_reply, tools_used)
            detect_and_log_decision(user_message, friday_reply)
            return friday_reply


MODE = "text"


def activate_voice_mode():
    global MODE
    if MODE != "voice":
        MODE = "voice"
        print("\n  [Hey FRIDAY detected — voice mode activated]\n", flush=True)
        try:
            speak("Yes, I'm listening.")
        except Exception as e:
            print(f"[voice error: {e}]")


voice.on_wake_word = activate_voice_mode

start_wake_word_listener()

if is_weekly_summary_due():
    print("\nFRIDAY: Hey, it's Sunday — time for your weekly summary. Generating...\n")
    summary = generate_weekly_summary()
    if summary:
        print(f"FRIDAY: Here's what I'd write:\n\n{summary}\n")
        confirm = input("Write this to Obsidian? (yes/no): ").strip().lower()
        if confirm == "yes":
            write_weekly_summary(summary)
            print("FRIDAY: Weekly summary saved to Obsidian.\n")
        else:
            print("FRIDAY: Skipped. I'll ask again next Sunday.\n")

print("=" * 40)
print("  FRIDAY is online.")
print(f"  Mode: {MODE.upper()}")
print("  Say 'Hey FRIDAY' to activate voice mode.")
print("  Commands: 'text mode', 'voice mode', 'hybrid mode', 'quit'")
print("=" * 40 + "\n")

while True:
    if MODE == "voice":
        user_input = get_input(voice_mode=True)
    else:
        user_input = input("You: ").strip()

    if not user_input:
        continue

    user_lower = user_input.lower().strip()

    if any(p in user_lower for p in ["text mode", "go to sleep", "sleep", "disable voice"]):
        MODE = "text"
        print("FRIDAY: Text mode. Say 'Hey FRIDAY' to wake me up.\n")
        try:
            speak("Going to sleep. Say Hey FRIDAY to wake me up.")
        except:
            pass
        continue

    if any(p in user_lower for p in ["voice mode", "switch to voice", "voice on"]):
        MODE = "voice"
        print("FRIDAY: Voice mode activated.\n")
        try:
            speak("Voice mode activated. I'm listening.")
        except Exception as e:
            print(f"[voice error: {e}]")
        continue

    if any(p in user_lower for p in ["hybrid mode", "hybrid on", "type and speak"]):
        MODE = "hybrid"
        print("FRIDAY: Hybrid mode. Type to me and I'll speak back.\n")
        try:
            speak("Hybrid mode activated.")
        except Exception as e:
            print(f"[voice error: {e}]")
        continue

    if any(p in user_lower for p in ["stop", "wait", "shut up", "quiet"]):
        stop_speaking.set()
        print("FRIDAY: Stopped.\n")
        continue

    if user_lower == "quit":
        stop_wake_word_listener()
        try:
            speak("Goodbye. See you next time.")
        except:
            pass
        print("FRIDAY: Goodbye.")
        break

    if user_lower.startswith("log "):
        note = user_input
        write_obsidian_log(note)
        print("FRIDAY: Logged to Obsidian.\n")
        continue

    FILE_KEYWORDS = [
    "open", "file", "find", "search", "folder", "document",
    "cheatsheet", "notes", "pdf", "obsidian", "show", "locate",
    "calendar", "event", "schedule", "remind", "meeting", "appointment",
    "email", "gmail", "send", "spotify", "play", "music"
    ]

    if not is_complex(user_input) and is_ollama_running() and not any(k in user_lower for k in FILE_KEYWORDS):
        response = ask_ollama(user_input, conversation_history)
        if response:
            print(f"\nFRIDAY (local): {response}\n")
            log_interaction(user_input, response, [])
        else:
            response = chat(user_input)
            print(f"\nFRIDAY: {response}\n")
    else:
        response = chat(user_input)
        print(f"\nFRIDAY: {response}\n")

    if MODE in ("voice", "hybrid"):
        try:
            speak(response)
            time.sleep(0.3)
        except Exception as e:
            print(f"[voice error: {e}]")