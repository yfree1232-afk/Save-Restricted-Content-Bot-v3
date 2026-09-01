# Copyright (c) 2025 devgagan : https://github.com/devgaganin.  
# Licensed under the GNU General Public License v3.0.  
# See LICENSE file in the repository root for full license text.

from datetime import datetime, timedelta
from shared_client import app
from pyrogram import filters
from pyrogram.types import InlineKeyboardButton, InlineKeyboardMarkup, Message, CallbackQuery
from config import OWNER_ID, JOIN_LINK, ADMIN_CONTACT, P0
from utils.func import (
    add_premium_user, remove_premium_user, is_premium_user, 
    get_premium_details, generate_redeem_code, redeem_code, 
    get_user_data, premium_users_collection
)
from plugins.start import subscribe

START_TEXT = """👋 **Hi {}! Welcome to Save Restricted Content Bot**

I can help you extract, save, and batch download restricted content, videos, audio, documents, and files from Telegram channels and groups!

⚡ **Features**:
• **Direct Extraction**: Just paste any channel post link!
• **Bulk Batch Mode**: Extract up to 100+ files with `/batch`
• **Customization**: Rename tag, custom caption, thumbnail via `/settings`
• **High Speed**: Multi-stream parallel downloading enabled

Select an option below to get started ⤵️"""

def get_start_keyboard():
    return InlineKeyboardMarkup([
        [
            InlineKeyboardButton("📢 Join Channel", url=JOIN_LINK),
            InlineKeyboardButton("💎 Premium Plans", callback_data="see_plan")
        ],
        [
            InlineKeyboardButton("⚙️ Settings", callback_data="open_settings"),
            InlineKeyboardButton("❓ Help & Commands", callback_data="help_0")
        ]
    ])

@app.on_message(filters.command("start") & filters.private)
async def start_handler(client, message: Message):
    if await subscribe(client, message) == 1:
        return
    name = message.from_user.first_name or "User"
    await message.reply_text(
        START_TEXT.format(name),
        reply_markup=get_start_keyboard(),
        disable_web_page_preview=True
    )

@app.on_message(filters.command(["myplan", "status"]) & filters.private)
async def status_handler(client, message: Message):
    user_id = message.from_user.id
    user_data = await get_user_data(user_id)
    
    session_active = bool(user_data and "session_string" in user_data)
    bot_active = bool(user_data and "bot_token" in user_data)
    
    premium_details = await get_premium_details(user_id)
    if premium_details:
        expiry_utc = premium_details["subscription_end"]
        expiry_ist = expiry_utc + timedelta(hours=5, minutes=30)
        formatted_expiry = expiry_ist.strftime("%d-%b-%Y %I:%M:%S %p")
        premium_status = f"✅ **Active until**: `{formatted_expiry}` (IST)"
    else:
        premium_status = "❌ **Not Active** (Use `/plan` or `/redeem`)"

    txt = (
        "📊 **Your Account Status**\n\n"
        f"👤 **User ID**: `{user_id}`\n"
        f"🔑 **Login Session**: {'✅ Active' if session_active else '❌ Not Logged In (`/login`)'}\n"
        f"🤖 **Custom Bot**: {'✅ Configured' if bot_active else '⚡ Default Main Bot'}\n"
        f"💎 **Premium Subscription**: {premium_status}\n\n"
        "Need premium? Send `/plan` or `/redeem <code>`"
    )
    await message.reply_text(txt)

@app.on_message(filters.command("add") & filters.private)
async def add_premium_cmd(client, message: Message):
    user_id = message.from_user.id
    if user_id not in OWNER_ID:
        await message.reply_text("⛔ This command is restricted to the bot owner.")
        return

    parts = message.text.strip().split()
    if len(parts) != 4:
        await message.reply_text(
            "⚠️ **Usage**: `/add <user_id> <value> <unit>`\n\n"
            "**Units**: `min`, `hours`, `days`, `weeks`, `month`, `year`\n"
            "**Example**: `/add 123456789 1 month`"
        )
        return

    try:
        target_uid = int(parts[1])
        val = int(parts[2])
        unit = parts[3].lower()

        ok, result = await add_premium_user(target_uid, val, unit)
        if ok:
            expiry_ist = result + timedelta(hours=5, minutes=30)
            formatted = expiry_ist.strftime('%d-%b-%Y %I:%M:%S %p')
            await message.reply_text(
                f"✅ **Premium Added Successfully!**\n\n"
                f"👤 **User**: `{target_uid}`\n"
                f"⏰ **Valid Till**: `{formatted}` (IST)"
            )
            try:
                await client.send_message(
                    target_uid,
                    f"🎉 **Congratulations!**\n"
                    f"You have been granted Premium Access!\n"
                    f"⏰ **Validity**: `{formatted}` (IST)"
                )
            except Exception:
                pass
        else:
            await message.reply_text(f"❌ Failed to add premium: {result}")
    except ValueError:
        await message.reply_text("❌ User ID and duration value must be numbers.")
    except Exception as e:
        await message.reply_text(f"❌ Error: {e}")

@app.on_message(filters.command("rem") & filters.private)
async def rem_premium_cmd(client, message: Message):
    user_id = message.from_user.id
    if user_id not in OWNER_ID:
        await message.reply_text("⛔ This command is restricted to the bot owner.")
        return

    parts = message.text.strip().split()
    if len(parts) != 2:
        await message.reply_text("⚠️ **Usage**: `/rem <user_id>`")
        return

    try:
        target_uid = int(parts[1])
        ok = await remove_premium_user(target_uid)
        if ok:
            await message.reply_text(f"✅ Premium removed for user `{target_uid}`.")
            try:
                await client.send_message(target_uid, "⚠️ Your premium subscription has ended.")
            except Exception:
                pass
        else:
            await message.reply_text(f"❌ User `{target_uid}` is not a premium user.")
    except ValueError:
        await message.reply_text("❌ User ID must be a valid number.")

@app.on_message(filters.command("gencode") & filters.private)
async def gencode_cmd(client, message: Message):
    user_id = message.from_user.id
    if user_id not in OWNER_ID:
        await message.reply_text("⛔ This command is restricted to the bot owner.")
        return

    parts = message.text.strip().split()
    if len(parts) != 3:
        await message.reply_text(
            "⚠️ **Usage**: `/gencode <value> <unit>`\n\n"
            "**Example**: `/gencode 1 month` or `/gencode 7 days`"
        )
        return

    try:
        val = int(parts[1])
        unit = parts[2].lower()
        ok, code = await generate_redeem_code(val, unit)
        if ok:
            await message.reply_text(
                f"🎟️ **New Gift/Redeem Code Generated!**\n\n"
                f"🔑 **Code**: `{code}`\n"
                f"⏳ **Duration**: `{val} {unit}`\n\n"
                f"👉 *Users can redeem with*: `/redeem {code}`"
            )
        else:
            await message.reply_text(f"❌ Failed to generate code: {code}")
    except ValueError:
        await message.reply_text("❌ Duration value must be a number.")

@app.on_message(filters.command("redeem") & filters.private)
async def redeem_cmd(client, message: Message):
    user_id = message.from_user.id
    parts = message.text.strip().split()
    if len(parts) != 2:
        await message.reply_text("⚠️ **Usage**: `/redeem <code_string>`\nExample: `/redeem PREM-ABCD-1234`")
        return

    code_str = parts[1].strip()
    ok, res = await redeem_code(user_id, code_str)
    if ok:
        expiry_ist = res + timedelta(hours=5, minutes=30)
        formatted = expiry_ist.strftime('%d-%b-%Y %I:%M:%S %p')
        await message.reply_text(
            f"🎉 **Code Redeemed Successfully!**\n\n"
            f"💎 Premium is now active on your account.\n"
            f"⏰ **Valid Till**: `{formatted}` (IST)"
        )
    else:
        await message.reply_text(f"{res}")

@app.on_message(filters.command("transfer") & filters.private)
async def transfer_cmd(client, message: Message):
    user_id = message.from_user.id
    if not await is_premium_user(user_id):
        await message.reply_text("❌ You do not have an active premium subscription to transfer.")
        return

    parts = message.text.strip().split()
    if len(parts) != 2:
        await message.reply_text("⚠️ **Usage**: `/transfer <target_user_id>`")
        return

    try:
        target_uid = int(parts[1])
        if target_uid == user_id:
            await message.reply_text("❌ You cannot transfer premium to yourself.")
            return

        if await is_premium_user(target_uid):
            await message.reply_text("❌ Target user already has an active premium subscription.")
            return

        details = await get_premium_details(user_id)
        if not details:
            await message.reply_text("❌ Could not retrieve your subscription details.")
            return

        exp = details["subscription_end"]
        now = datetime.now()
        await premium_users_collection.update_one(
            {"user_id": target_uid},
            {"$set": {
                "user_id": target_uid,
                "subscription_start": now,
                "subscription_end": exp,
                "expireAt": exp,
                "transferred_from": user_id
            }},
            upsert=True
        )
        await premium_users_collection.delete_one({"user_id": user_id})
        
        expiry_ist = exp + timedelta(hours=5, minutes=30)
        formatted = expiry_ist.strftime('%d-%b-%Y %I:%M:%S %p')

        await message.reply_text(f"✅ **Premium transferred to `{target_uid}`.** Your subscription has ended.")
        try:
            await client.send_message(
                target_uid,
                f"🎁 **You received a Premium transfer!**\n⏰ Valid until: `{formatted}` (IST)"
            )
        except Exception:
            pass
    except ValueError:
        await message.reply_text("❌ Target User ID must be a valid number.")
