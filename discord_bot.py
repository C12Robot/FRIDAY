import discord
import os
import asyncio
from dotenv import load_dotenv
from datetime import datetime

load_dotenv()

DISCORD_TOKEN      = os.getenv("DISCORD_TOKEN")
CHAT_CHANNEL_NAME  = "friday-chat"
ALERT_CHANNEL_NAME = "friday-alerts"

intents = discord.Intents.default()
intents.message_content = True
bot = discord.Client(intents=intents)

def get_friday_response(message):
    import requests
    try:
        res = requests.post("http://localhost:8000/chat",
            json={"message": message}, timeout=60)
        data = res.json()
        return data.get("reply", "No response.")
    except Exception as e:
        return f"Error connecting to FRIDAY: {str(e)}"

def get_briefing():
    import requests
    try:
        res = requests.get("http://localhost:8000/briefing", timeout=30)
        data = res.json()
        if data.get("has_briefing"):
            return data.get("briefing", "")
        return None
    except:
        return None

@bot.event
async def on_ready():
    print(f"FRIDAY Discord bot online as {bot.user}")
    for guild in bot.guilds:
        for channel in guild.text_channels:
            if channel.name == ALERT_CHANNEL_NAME:
                briefing = get_briefing()
                if briefing:
                    await channel.send(f"☀️ **Morning Briefing**\n{briefing}")

@bot.event
async def on_message(message):
    print(f"[MSG] from {message.author}: {message.content}")
    if message.author == bot.user:
        return

    if bot.user.mentioned_in(message) or "friday" in message.content.lower():
        content = message.content
        for mention in message.mentions:
            content = content.replace(f"<@{mention.id}>", "").replace(f"<@!{mention.id}>", "")
        content = content.strip()
        if content.lower().startswith("friday"):
            content = content[6:].strip()

        if not content:
            await message.reply("Yes? How can I help?")
            return

        async with message.channel.typing():
            loop = asyncio.get_event_loop()
            reply = await loop.run_in_executor(None, get_friday_response, content)

        if len(reply) > 1900:
            chunks = [reply[i:i+1900] for i in range(0, len(reply), 1900)]
            for chunk in chunks:
                await message.reply(chunk)
        else:
            await message.reply(reply)

bot.run(DISCORD_TOKEN)