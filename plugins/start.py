# Copyright (c) 2025 devgagan : https://github.com/devgaganin.  
# Licensed under the GNU General Public License v3.0.  
# See LICENSE file in the repository root for full license text.

from shared_client import app
from pyrogram import filters
from pyrogram.errors import UserNotParticipant
from pyrogram.types import BotCommand, InlineKeyboardButton, InlineKeyboardMarkup, Message, CallbackQuery
from config import LOG_GROUP, OWNER_ID, FORCE_SUB, JOIN_LINK, ADMIN_CONTACT, P0

async def subscribe(app, message):
    if FORCE_SUB and FORCE_SUB != 0 and FORCE_SUB != -10012345567:
        try:
            user = await app.get_chat_member(FORCE_SUB, message.from_user.id)
            if str(user.status) == "ChatMemberStatus.BANNED":
                await message.reply_text("⛔ You are Banned. Contact channel admins.")
                return 1
        except UserNotParticipant:
            try:
                link = await app.export_chat_invite_link(FORCE_SUB)
            except Exception:
                link = JOIN_LINK
            caption = "⚠️ **Please join our channel to use this bot!**"
            await message.reply_text(
                caption, 
                reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("📢 Join Channel", url=link)]])
            )
            return 1
        except Exception as ggn:
            print(f"Force sub notice: {ggn}")
            return 0
    return 0 
     
@app.on_message(filters.command("set") & filters.private)
async def set_commands_handler(_, message: Message):
    if message.from_user.id not in OWNER_ID:
        await message.reply("⛔ You are not authorized to use this command.")
        return
     
    await app.set_bot_commands([
        BotCommand("start", "🚀 Start the bot"),
        BotCommand("batch", "📦 Bulk batch extraction"),
        BotCommand("single", "🔗 Extract single link"),
        BotCommand("login", "🔑 Log in with Telegram"),
        BotCommand("logout", "🚪 Log out from bot"),
        BotCommand("settings", "⚙️ Personalize settings"),
        BotCommand("myplan", "💎 Check your plan/status"),
        BotCommand("plan", "💰 View premium plans"),
        BotCommand("pay", "⭐ Pay via Telegram Stars"),
        BotCommand("redeem", "🎟️ Redeem gift code"),
        BotCommand("transfer", "🎁 Transfer premium to friend"),
        BotCommand("add", "➕ Add premium (Owner only)"),
        BotCommand("rem", "➖ Remove premium (Owner only)"),
        BotCommand("gencode", "🎟️ Generate code (Owner only)"),
        BotCommand("setlog", "📋 Set Log Channel (Owner only)"),
        BotCommand("remlog", "🗑️ Remove Log Channel (Owner only)"),
        BotCommand("getlog", "🔍 View Log Channel (Owner only)"),
        BotCommand("settarget", "🎯 Set Target Channel (Owner only)"),
        BotCommand("fwd", "📤 Systematic Batch Forward (Owner only)"),
        BotCommand("sendto", "🚀 Copy Replied Post (Owner only)"),
        BotCommand("cancel", "🚫 Cancel current process"),
        BotCommand("stop", "🛑 Stop ongoing batch"),
        BotCommand("help", "❓ Help & tutorial")
    ])
 
    await message.reply("✅ **Bot commands configured successfully!**")

help_pages = [
    (
        "📖 **Save Restricted Content Bot — Guide (1/2)**\n\n"
        "🔗 **Extracting Posts**:\n"
        "• **Direct Link**: Simply send any public or private Telegram post link into this chat!\n"
        "• **/batch**: Extract multiple consecutive posts in bulk.\n"
        "• **/single**: Extract a single post link.\n\n"
        "🔑 **Account & Access**:\n"
        "• **/login**: Log in with your phone number + OTP to access private restricted channels you have joined.\n"
        "• **/logout**: Terminate your active login session.\n\n"
        "⚙️ **Customization**:\n"
        "• **/settings**: Set custom thumbnail, rename tag, caption, replacement words, or destination chat."
    ),
    (
        "📖 **Save Restricted Content Bot — Guide (2/2)**\n\n"
        "💎 **Premium Features**:\n"
        "• **/myplan** or **/status**: Check your active subscription validity.\n"
        "• **/plan**: View premium pricing and limits.\n"
        "• **/pay**: Purchase premium with Telegram Stars ⭐.\n"
        "• **/redeem <code>**: Redeem a gift code.\n"
        "• **/transfer <user_id>**: Transfer your premium to another user.\n\n"
        "👑 **Owner Commands**:\n"
        "• **/add <id> <val> <unit>**: Grant premium access.\n"
        "• **/rem <id>**: Revoke premium access.\n"
        "• **/gencode <val> <unit>**: Generate redeemable gift codes.\n\n"
        "📢 **Updates Channel**: @voltxbots"
    )
]

async def send_or_edit_help_page(_, message, page_number):
    if page_number < 0 or page_number >= len(help_pages):
        page_number = 0
 
    buttons = []
    if page_number > 0:
        buttons.append(InlineKeyboardButton("◀️ Previous", callback_data=f"help_prev_{page_number}"))
    if page_number < len(help_pages) - 1:
        buttons.append(InlineKeyboardButton("Next ▶️", callback_data=f"help_next_{page_number}"))
 
    nav_row = buttons
    extra_row = [
        InlineKeyboardButton("💎 Premium Plans", callback_data="see_plan"),
        InlineKeyboardButton("⚙️ Settings", callback_data="open_settings")
    ]
    channel_row = [
        InlineKeyboardButton("📢 Channel @voltxbots", url=JOIN_LINK)
    ]
    
    kb_rows = []
    if nav_row:
        kb_rows.append(nav_row)
    kb_rows.append(extra_row)
    kb_rows.append(channel_row)
    
    keyboard = InlineKeyboardMarkup(kb_rows)

    try:
        await message.edit_text(help_pages[page_number], reply_markup=keyboard, disable_web_page_preview=True)
    except Exception:
        await message.reply_text(help_pages[page_number], reply_markup=keyboard, disable_web_page_preview=True)

@app.on_message(filters.command("help") & filters.private)
async def help_cmd(client, message: Message):
    if await subscribe(client, message) == 1:
        return
    await send_or_edit_help_page(client, message, 0)

@app.on_callback_query(filters.regex(r"^help_(\d+)$"))
async def on_help_direct(client, callback_query: CallbackQuery):
    page_num = int(callback_query.data.split("_")[1])
    await send_or_edit_help_page(client, callback_query.message, page_num)
    await callback_query.answer()

@app.on_callback_query(filters.regex(r"^help_(prev|next)_(\d+)$"))
async def on_help_navigation(client, callback_query: CallbackQuery):
    action, page_number = callback_query.data.split("_")[1], int(callback_query.data.split("_")[2])
 
    if action == "prev":
        page_number -= 1
    elif action == "next":
        page_number += 1

    await send_or_edit_help_page(client, callback_query.message, page_number)
    await callback_query.answer()

@app.on_message(filters.command("terms") & filters.private)
async def terms_cmd(client, message: Message):
    terms_text = (
        "📜 **Terms and Conditions**\n\n"
        "✨ We do not host or promote copyrighted content. The bot is a tool for personal backup.\n"
        "✨ Premium validity starts immediately upon activation.\n"
        "✨ For queries and support, contact @voltxTGSupport or our channel @voltxbots."
    )
    buttons = InlineKeyboardMarkup([
        [
            InlineKeyboardButton("💎 See Plans", callback_data="see_plan"),
            InlineKeyboardButton("📢 Channel", url=JOIN_LINK)
        ]
    ])
    await message.reply_text(terms_text, reply_markup=buttons)

@app.on_message(filters.command("plan") & filters.private)
async def plan_cmd(client, message: Message):
    plan_text = (
        "💎 **Premium Subscription Plans**\n\n"
        "🚀 **Premium Benefits**:\n"
        "• Extract up to **500+ files per batch**\n"
        "• High-speed multi-stream download & upload (8x)\n"
        "• Priority server processing & 24/7 uptime\n\n"
        "💰 **Pricing Options**:\n"
        f"• ☀️ **Daily Plan (1 Day)**: `₹20`  |  `20 ⭐ Stars`\n"
        f"• 🗓️ **Weekly Plan (7 Days)**: `₹70`  |  `70 ⭐ Stars`\n"
        f"• 📅 **Monthly Plan (30 Days)**: `₹150`  |  `150 ⭐ Stars`\n\n"
        "⚡ **Instant Activation**: Click a Stars button below for automatic instant activation, or contact Admin for UPI / QR payment ⤵️"
    )
    buttons = InlineKeyboardMarkup([
        [
            InlineKeyboardButton("⭐ Daily (20 Stars)", callback_data="p_d"),
            InlineKeyboardButton("⭐ Weekly (70 Stars)", callback_data="p_w")
        ],
        [
            InlineKeyboardButton("⭐ Monthly (150 Stars)", callback_data="p_m")
        ],
        [
            InlineKeyboardButton("💳 Buy via UPI / Contact Admin", url=ADMIN_CONTACT)
        ],
        [
            InlineKeyboardButton("🎟️ Redeem Code", callback_data="btn_redeem_info"),
            InlineKeyboardButton("📢 Channel", url=JOIN_LINK)
        ]
    ])
    await message.reply_text(plan_text, reply_markup=buttons)

@app.on_callback_query(filters.regex("^see_plan$"))
async def see_plan_cb(client, callback_query: CallbackQuery):
    plan_text = (
        "💎 **Premium Subscription Plans**\n\n"
        "🚀 **Premium Benefits**:\n"
        "• Extract up to **500+ files per batch**\n"
        "• High-speed multi-stream download & upload (8x)\n"
        "• Priority server processing & 24/7 uptime\n\n"
        "💰 **Pricing Options**:\n"
        f"• ☀️ **Daily Plan (1 Day)**: `₹20`  |  `20 ⭐ Stars`\n"
        f"• 🗓️ **Weekly Plan (7 Days)**: `₹70`  |  `70 ⭐ Stars`\n"
        f"• 📅 **Monthly Plan (30 Days)**: `₹150`  |  `150 ⭐ Stars`\n\n"
        "⚡ **Instant Activation**: Click a Stars button below for automatic instant activation, or contact Admin for UPI / QR payment ⤵️"
    )
    buttons = InlineKeyboardMarkup([
        [
            InlineKeyboardButton("⭐ Daily (20 Stars)", callback_data="p_d"),
            InlineKeyboardButton("⭐ Weekly (70 Stars)", callback_data="p_w")
        ],
        [
            InlineKeyboardButton("⭐ Monthly (150 Stars)", callback_data="p_m")
        ],
        [
            InlineKeyboardButton("💳 Buy via UPI / Contact Admin", url=ADMIN_CONTACT)
        ],
        [
            InlineKeyboardButton("🎟️ Redeem Code", callback_data="btn_redeem_info"),
            InlineKeyboardButton("📢 Channel", url=JOIN_LINK)
        ]
    ])
    await callback_query.message.edit_text(plan_text, reply_markup=buttons)
    await callback_query.answer()

@app.on_callback_query(filters.regex("^btn_redeem_info$"))
async def redeem_info_cb(client, callback_query: CallbackQuery):
    await callback_query.answer(
        "To redeem a gift code, simply send /redeem <code> (e.g. /redeem PREM-XXXX-YYYY)",
        show_alert=True
    )

@app.on_callback_query(filters.regex("^see_terms$"))
async def see_terms_cb(client, callback_query: CallbackQuery):
    terms_text = (
        "📜 **Terms and Conditions**\n\n"
        "✨ We do not host or promote copyrighted content. The bot is a tool for personal backup.\n"
        "✨ Premium validity starts immediately upon activation.\n"
        "✨ For queries and support, contact @voltxTGSupport or our channel @voltxbots."
    )
    buttons = InlineKeyboardMarkup([
        [
            InlineKeyboardButton("💎 See Plans", callback_data="see_plan"),
            InlineKeyboardButton("📢 Channel", url=JOIN_LINK)
        ]
    ])
    await callback_query.message.edit_text(terms_text, reply_markup=buttons)
    await callback_query.answer()
