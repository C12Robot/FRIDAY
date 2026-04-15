import warnings
import logging
import os

warnings.filterwarnings("ignore")
logging.getLogger("faster_whisper").setLevel(logging.ERROR)
logging.getLogger("sentence_transformers").setLevel(logging.ERROR)
logging.getLogger("chromadb").setLevel(logging.ERROR)
os.environ["TOKENIZERS_PARALLELISM"] = "false"

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from datetime import datetime
import json
import re
from anthropic import Anthropic
from dotenv import load_dotenv
from memory import FridayMemory
from tools import web_search, read_file, write_file, gmail_read, gmail_send, gmail_search, calendar_get, calendar_create

load_dotenv()

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"]
)

client = Anthropic()
memory = FridayMemory()

conversation_history = []
action_log = []

class MessageRequest(BaseModel):
    message: str

class MessageResponse(BaseModel):
    reply: str
    tools_used: list

TOOL_DEFINITIONS = [
    {
        "name": "web_search",
        "description": "Search the internet for current information.",
        "input_schema": {
            "type": "object",
            "properties": {
                "query": {"type": "string", "description": "Search query"}
            },
            "required": ["query"]
        }
    },
    {
        "name": "gmail_read",
        "description": "Read unread emails from Gmail.",
        "input_schema": {"type": "object", "properties": {}, "required": []}
    },
    {
        "name": "gmail_send",
        "description": "Send an email.",
        "input_schema": {
            "type": "object",
            "properties": {
                "to": {"type": "string"},
                "subject": {"type": "string"},
                "body": {"type": "string"}
            },
            "required": ["to", "subject", "body"]
        }
    },
    {
        "name": "gmail_search",
        "description": "Search emails.",
        "input_schema": {
            "type": "object",
            "properties": {
                "query": {"type": "string"}
            },
            "required": ["query"]
        }
    },
    {
        "name": "calendar_get",
        "description": "Get upcoming calendar events.",
        "input_schema": {"type": "object", "properties": {}, "required": []}
    },
    {
        "name": "calendar_create",
        "description": "Create a calendar event.",
        "input_schema": {
            "type": "object",
            "properties": {
                "summary": {"type": "string"},
                "start_time": {"type": "string"},
                "end_time": {"type": "string"},
                "description": {"type": "string"},
                "location": {"type": "string"}
            },
            "required": ["summary", "start_time", "end_time"]
        }
    },
    {
        "name": "read_file",
        "description": "Read a file from the laptop.",
        "input_schema": {
            "type": "object",
            "properties": {
                "path": {"type": "string"}
            },
            "required": ["path"]
        }
    },
    {
        "name": "write_file",
        "description": "Write a file to the laptop.",
        "input_schema": {
            "type": "object",
            "properties": {
                "path": {"type": "string"},
                "content": {"type": "string"}
            },
            "required": ["path", "content"]
        }
    }
]

BASE_SYSTEM_PROMPT = f"""You are FRIDAY, a smart and efficient personal assistant.
Today's date is {datetime.now().strftime('%A, %B %d %Y')}.
You are helpful, concise, and professional.
You remember everything said in this conversation.
When you don't know something, use your tools to find out.
Present information directly and concisely."""


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
    else:
        return f"Unknown tool: {tool_name}"


@app.post("/chat")
async def chat(request: MessageRequest):
    user_message = request.message
    tools_used = []

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
                    tools_used.append(tool_name)

                    try:
                        tool_result = execute_tool(tool_name, tool_input)
                    except Exception as e:
                        tool_result = f"Tool error: {str(e)}"

                    action_log.append({
                        "timestamp": datetime.now().strftime("%H:%M:%S"),
                        "tool": tool_name,
                        "input": str(tool_input),
                        "result": str(tool_result)[:200]
                    })

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
            return MessageResponse(reply=friday_reply, tools_used=tools_used)

@app.get("/memories")
async def get_memories():
    try:
        count = memory.collection.count()
        if count == 0:
            return {"memories": [], "count": 0}
        
        results = memory.collection.get()
        memories = results.get("documents", [])
        
        return {"memories": memories, "count": count}
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