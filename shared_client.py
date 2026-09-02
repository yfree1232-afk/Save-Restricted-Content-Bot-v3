from telethon import TelegramClient
from telethon.sessions import StringSession
from config import API_ID, API_HASH, BOT_TOKEN, STRING
from pyrogram import Client
from pyrogram.errors import FloodWait
import asyncio
import sys

client = TelegramClient(StringSession(), API_ID, API_HASH)
app = Client("pyrogrambot", api_id=API_ID, api_hash=API_HASH, bot_token=BOT_TOKEN, in_memory=True, workers=20, max_concurrent_transmissions=8)
userbot = Client("4gbbot", api_id=API_ID, api_hash=API_HASH, session_string=STRING, in_memory=True, workers=20, max_concurrent_transmissions=8) if STRING else None

async def start_client():
    try:
        if not client.is_connected():
            await client.start(bot_token=BOT_TOKEN)
            print("SpyLib started...")
    except Exception as e:
        print(f"Telethon start notice: {e}")
        
    if STRING and userbot:
        try:
            await userbot.start()
            print("Userbot started...")
        except Exception as e:
            print(f"Userbot session error: {e}")
            
    while True:
        try:
            await app.start()
            print("Pyro App Started...")
            break
        except FloodWait as f:
            print(f"Pyrogram FloodWait: Waiting {f.value}s for Telegram rate limit to clear...")
            await asyncio.sleep(f.value + 2)
        except Exception as e:
            print(f"Pyrogram start error: {e}")
            break
            
    return client, app, userbot
