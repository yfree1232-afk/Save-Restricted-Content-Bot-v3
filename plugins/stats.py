# Copyright (c) 2025 devgagan : https://github.com/devgaganin.  
# Licensed under the GNU General Public License v3.0.  
# See LICENSE file in the repository root for full license text.

from datetime import datetime, timedelta
from shared_client import app
from pyrogram import filters
from pyrogram.types import Message
from utils.func import users_collection, premium_users_collection, codedb
from config import OWNER_ID

@app.on_message(filters.command("stats") & filters.private)
async def stats_cmd(client, message: Message):
    if message.from_user.id not in OWNER_ID:
        await message.reply_text("⛔ Owner only command.")
        return
    
    total_users = await users_collection.count_documents({})
    total_prem = await premium_users_collection.count_documents({})
    total_codes = await codedb.count_documents({"used": False})
    
    await message.reply_text(
        f"📊 **Bot Realtime Statistics**\n\n"
        f"👥 **Total Registered Users**: `{total_users}`\n"
        f"💎 **Active Premium Members**: `{total_prem}`\n"
        f"🎟️ **Unused Redeem Codes**: `{total_codes}`\n"
        f"⚡ **Engine**: `Pyrofork + Multi-Stream (8x)`\n"
        f"📢 **Channel**: `@voltxbots`"
    )
