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
from tools import web_search, read_file, write_file, gmail_read, gmail_send, gmail_search, calendar_get, calendar_create

load_dotenv()

client = Anthropic()
memory = FridayMemory()

TOOLS = {
    "web_search": web_search,
    "read_file": read_file,
    "write_file": write_file,
    "gmail_read": gmail_read,
    "gmail_send": gmail_send,
    "gmail_search": gmail_search,
    "calendar_get": calendar_get,
    "calendar_create": calendar_create
}

TOOL_DEFINITIONS = [
    {
        "name": "web_search",
        "description": "Search the internet for current information, news, or anything FRIDAY doesn't know. Use this for recent events, latest news, current prices, or any real-time information.",
        "input_schema": {
            "type": "object",
            "properties": {
                "query": {
                    "type": "string",
                    "description": "The search query to look up"
                }
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
                "path": {
                    "type": "string",
                    "description": "The full file path to read"
                }
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
                "path": {
                    "type": "string",
                    "description": "The full file path to write to"
                },
                "content": {
                    "type": "string",
                    "description": "The content to write to the file"
                }
            },
            "required": ["path", "content"]
        }
    },
    {
        "name": "gmail_read",
        "description": "Read the user's unread emails from Gmail. Use this when the user asks to check, read or see their emails.",
        "input_schema": {
            "type": "object",
            "properties": {},
            "required": []
        }
    },
    {
        "name": "gmail_send",
        "description": "Send an email on behalf of the user. Always shows preview and asks confirmation first.",
        "input_schema": {
            "type": "object",
            "properties": {
                "to": {
                    "type": "string",
                    "description": "Recipient email address"
                },
                "subject": {
                    "type": "string",
                    "description": "Email subject line"
                },
                "body": {
                    "type": "string",
                    "description": "Email body content"
                }
            },
            "required": ["to", "subject", "body"]
        }
    },
    {
        "name": "gmail_search",
        "description": "Search through the user's Gmail with a query. Use Gmail search syntax.",
        "input_schema": {
            "type": "object",
            "properties": {
                "query": {
                    "type": "string",
                    "description": "Gmail search query e.g. 'from:boss@company.com' or 'subject:meeting'"
                }
            },
            "required": ["query"]
        }
    },
    {
        "name": "calendar_get",
        "description": "Get the user's upcoming Google Calendar events. Use when user asks about schedule, upcoming events, or what they have planned.",
        "input_schema": {
            "type": "object",
            "properties": {},
            "required": []
        }
    },
    {
        "name": "calendar_create",
        "description": "Create a new event in the user's Google Calendar. Extract the event title, date and time from the user's message. Convert relative dates like 'tomorrow' to actual dates based on today being April 15 2026. Times should be in ISO format: YYYY-MM-DDTHH:MM:SS. Always confirm with user before creating.",
        "input_schema": {
            "type": "object",
            "properties": {
                "summary": {
                    "type": "string",
                    "description": "Event title or name"
                },
                "start_time": {
                    "type": "string",
                    "description": "Start time in ISO format e.g. 2026-04-16T14:00:00"
                },
                "end_time": {
                    "type": "string",
                    "description": "End time in ISO format e.g. 2026-04-16T15:00:00"
                },
                "description": {
                    "type": "string",
                    "description": "Optional event description"
                },
                "location": {
                    "type": "string",
                    "description": "Optional event location"
                }
            },
            "required": ["summary", "start_time", "end_time"]
        }
    }
]

BASE_SYSTEM_PROMPT = f"""You are FRIDAY, a smart and efficient personal assistant.
Today's date is {datetime.now().strftime('%A, %B %d %Y')}.
You are helpful, concise, and professional.
You remember everything said in this conversation.
When you don't know something, use your tools to find out.
Present information directly without preamble like 'Based on my search' or 'I found that'.
Keep responses concise — you are speaking out loud, so avoid long lists or bullet points."""

SUMMARISE_PROMPT = """Present the information directly and concisely.
No preamble. No 'Based on search results'. Just answer cleanly.
Keep it to 3-4 sentences maximum — this will be spoken out loud."""

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
        return gmail_send(
            tool_input["to"],
            tool_input["subject"],
            tool_input["body"]
        )
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
    else:
        return f"Unknown tool: {tool_name}"


def chat(user_message):
    memory_context = memory.build_memory_prompt(user_message)
    full_system_prompt = BASE_SYSTEM_PROMPT
    if memory_context:
        full_system_prompt += f"\n{memory_context}"

    conversation_history.append({
        "role": "user",
        "content": user_message
    })

    while True:
        response = client.messages.create(
            model="claude-sonnet-4-5",
            max_tokens=1024,
            system=full_system_prompt,
            tools=TOOL_DEFINITIONS,
            messages=conversation_history
        )

        if response.stop_reason == "tool_use":
            conversation_history.append({
                "role": "assistant",
                "content": response.content
            })

            tool_results = []
            for block in response.content:
                if block.type == "tool_use":
                    tool_name = block.name
                    tool_input = block.input

                    print(f"\n  🔧 FRIDAY is using {tool_name}...", flush=True)

                    try:
                        tool_result = execute_tool(tool_name, tool_input)
                    except Exception as e:
                        tool_result = f"Tool error: {str(e)}"

                    tool_results.append({
                        "type": "tool_result",
                        "tool_use_id": block.id,
                        "content": str(tool_result)
                    })

            conversation_history.append({
                "role": "user",
                "content": tool_results
            })

        else:
            friday_reply = ""
            for block in response.content:
                if hasattr(block, 'text'):
                    friday_reply = block.text
                    break

            if not friday_reply:
                friday_reply = "I couldn't generate a response. Please try again."

            conversation_history.append({
                "role": "assistant",
                "content": friday_reply
            })

            memory.save_memory(f"User: {user_message} | FRIDAY: {friday_reply}")
            return friday_reply

    friday_reply = ""
    for block in response.content:
        if hasattr(block, 'text'):
            friday_reply = block.text
            break

    if not friday_reply:
        friday_reply = "I couldn't generate a response. Please try again."

    conversation_history.append({
        "role": "assistant",
        "content": friday_reply
    })

    memory.save_memory(f"User: {user_message} | FRIDAY: {friday_reply}")
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

    response = chat(user_input)
    print(f"\nFRIDAY: {response}\n")

    if MODE in ("voice", "hybrid"):
        try:
            speak(response)
            time.sleep(0.3)
        except Exception as e:
            print(f"[voice error: {e}]")