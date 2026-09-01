import re
import time
import asyncio
from datetime import datetime
from pyrogram import filters
from pyrogram.types import Message, InlineKeyboardMarkup, InlineKeyboardButton
from shared_client import app
from config import OWNER_ID, JOIN_LINK
from utils.func import (
    get_log_channel, get_target_channel, set_target_channel, 
    remove_target_channel, E
)

ACTIVE_FWD_TASKS = set()

def clean_log_caption(caption: str) -> str:
    """Removes #ExtractionLog internal header from caption to make it systematic and clean"""
    if not caption:
        return ""
    # Pattern to match: 📥 #ExtractionLog ... ⏰ Time: ... \n\n (or similar)
    cleaned = re.sub(r'📥\s*#(?:ExtractionLog|TextLog)[\s\S]*?(?:⏰\s*Time:[^\n]*\n*|\n\n)', '', caption, flags=re.IGNORECASE)
    cleaned = re.sub(r'📝\s*\*\*Caption\*\*:\s*', '', cleaned, flags=re.IGNORECASE)
    return cleaned.strip()

@app.on_message(filters.command(["settarget", "settargetchannel"]) & filters.private)
async def set_target_channel_cmd(client, message: Message):
    user_id = message.from_user.id
    if user_id not in OWNER_ID:
        await message.reply_text("⛔ Owner only command.")
        return

    parts = message.text.strip().split()
    if len(parts) != 2:
        await message.reply_text(
            "⚠️ **Usage**: `/settarget <channel_id>`\n\n"
            "**Example**: `/settarget -1001234567890`\n\n"
            "👉 *Make sure this bot is added as **Admin** in the target channel!*"
        )
        return

    try:
        cid = int(parts[1])
        try:
            await client.send_message(
                cid, 
                "✅ **Target Channel Connected Successfully!**\n\nOwner can now forward selected batches here systematically."
            )
            await set_target_channel(cid)
            await message.reply_text(f"✅ **Default Target Channel Set!**\n\nChannel ID: `{cid}`\nTest ping sent successfully!")
        except Exception as e:
            await message.reply_text(
                f"❌ **Failed to access Target Channel**: `{e}`\n\n"
                "👉 Please ensure the bot is added as an **Admin** with permission to post messages in that channel."
            )
    except ValueError:
        await message.reply_text("❌ Channel ID must be a valid integer starting with `-100`.")

@app.on_message(filters.command(["remtarget", "removetarget"]) & filters.private)
async def remove_target_cmd(client, message: Message):
    user_id = message.from_user.id
    if user_id not in OWNER_ID:
        await message.reply_text("⛔ Owner only command.")
        return
    await remove_target_channel()
    await message.reply_text("✅ Default Target Channel removed.")

@app.on_message(filters.command(["gettarget", "target"]) & filters.private)
async def get_target_cmd(client, message: Message):
    user_id = message.from_user.id
    if user_id not in OWNER_ID:
        await message.reply_text("⛔ Owner only command.")
        return
    tgt_cid = await get_target_channel()
    if tgt_cid:
        await message.reply_text(f"📋 **Current Default Target Channel**: `{tgt_cid}`")
    else:
        await message.reply_text("ℹ️ No default Target Channel is configured. Use `/settarget <channel_id>` to set one.")

@app.on_message(filters.command(["sendto"]) & (filters.private | filters.channel | filters.group))
async def sendto_reply_cmd(client, message: Message):
    """Reply to any message to copy it cleanly to target channel"""
    user_id = message.from_user.id if message.from_user else None
    if user_id and user_id not in OWNER_ID:
        return

    if not message.reply_to_message:
        await message.reply_text("⚠️ Please reply to the message or media you want to forward/copy.")
        return

    rep_msg = message.reply_to_message
    parts = message.text.strip().split()
    
    target_cid = None
    if len(parts) >= 2 and parts[1].lstrip('-').isdigit():
        target_cid = int(parts[1])
    else:
        target_cid = await get_target_channel()

    if not target_cid:
        await message.reply_text("❌ Target channel not specified. Use `/sendto <channel_id>` or set default via `/settarget <channel_id>`.")
        return

    orig_cap = rep_msg.caption or rep_msg.text or ""
    clean_cap = clean_log_caption(orig_cap)

    try:
        if rep_msg.media:
            await client.copy_message(
                chat_id=target_cid,
                from_chat_id=rep_msg.chat.id,
                message_id=rep_msg.id,
                caption=clean_cap if clean_cap else None
            )
        else:
            await client.send_message(
                chat_id=target_cid,
                text=clean_cap if clean_cap else rep_msg.text
            )
        await message.reply_text(f"✅ **Successfully copied to target channel** (`{target_cid}`)!")
    except Exception as e:
        await message.reply_text(f"❌ Failed to copy message: {e}")

@app.on_message(filters.command(["fwd", "forward", "copybatch"]) & filters.private)
async def forward_batch_cmd(client, message: Message):
    """
    Forward range of posts from Log Channel (or any channel) to Target Channel systematically.
    Usage:
      /fwd <start_id> <end_id> [target_channel_id]
      /fwd <start_link> <count> [target_channel_id]
    """
    user_id = message.from_user.id
    if user_id not in OWNER_ID:
        await message.reply_text("⛔ Owner only command.")
        return

    parts = message.text.strip().split()
    if len(parts) < 3:
        await message.reply_text(
            "📋 **Systematic Channel Forwarder Guide**\n\n"
            "**Option 1 (By IDs from Log Channel)**:\n"
            "`/fwd <start_id> <end_id> [target_channel_id]`\n"
            "👉 *Example*: `/fwd 50 75` (uses default target)\n"
            "👉 *Example*: `/fwd 50 75 -1001234567890`\n\n"
            "**Option 2 (By Post Link + Count)**:\n"
            "`/fwd <start_link> <count> [target_channel_id]`\n"
            "👉 *Example*: `/fwd https://t.me/c/1234567890/50 25 -1009876543210`\n\n"
            "🛑 *To stop at any time*: `/stopfwd`"
        )
        return

    arg1 = parts[1].strip()
    arg2 = parts[2].strip()
    arg3 = parts[3].strip() if len(parts) > 3 else None

    from_chat_id = None
    start_id = None
    end_id = None
    target_cid = None

    # Case A: Post Link provided in arg1
    if "t.me" in arg1:
        cid_str, sid, lt = E(arg1)
        if not cid_str or not sid:
            await message.reply_text("❌ Invalid start link format.")
            return
        from_chat_id = int(cid_str) if str(cid_str).startswith("-100") else cid_str
        start_id = sid
        try:
            count = int(arg2)
            end_id = start_id + count - 1
        except ValueError:
            await message.reply_text("❌ Count must be a positive integer.")
            return
    else:
        # Case B: start_id and end_id provided
        try:
            start_id = int(arg1)
            end_id = int(arg2)
        except ValueError:
            await message.reply_text("❌ Start ID and End ID must be numbers.")
            return
        
        # Default source is Log Channel
        log_cid = await get_log_channel()
        if not log_cid:
            await message.reply_text("❌ Log Channel is not configured. Set it first via `/setlog <channel_id>`.")
            return
        from_chat_id = log_cid

    # Target channel determination
    if arg3 and arg3.lstrip('-').isdigit():
        target_cid = int(arg3)
    else:
        target_cid = await get_target_channel()

    if not target_cid:
        await message.reply_text("❌ No target channel specified! Provide one or set default via `/settarget <channel_id>`.")
        return

    if start_id > end_id:
        start_id, end_id = end_id, start_id

    total_msgs = end_id - start_id + 1
    if total_msgs > 500:
        await message.reply_text("⚠️ Limit is 500 posts per forward command.")
        return

    ACTIVE_FWD_TASKS.add(user_id)
    status_msg = await message.reply_text(
        f"🚀 **Starting Systematic Forwarding...**\n\n"
        f"📂 **Source**: `{from_chat_id}`\n"
        f"🎯 **Target**: `{target_cid}`\n"
        f"🔢 **Range**: `{start_id}` ➔ `{end_id}` ({total_msgs} posts)\n\n"
        f"⏳ Initializing..."
    )

    forwarded = 0
    skipped = 0
    last_update_time = time.time()

    try:
        for current_id in range(start_id, end_id + 1):
            if user_id not in ACTIVE_FWD_TASKS:
                await status_msg.edit_text(f"🛑 **Forwarding Cancelled by Owner.**\n\n✅ Forwarded: `{forwarded}`\n⏩ Skipped: `{skipped}`")
                return

            try:
                # Fetch message from source chat
                src_msg = await client.get_messages(from_chat_id, current_id)
                if not src_msg or src_msg.empty or (not src_msg.media and not src_msg.text):
                    skipped += 1
                    continue

                orig_cap = src_msg.caption or src_msg.text or ""
                clean_cap = clean_log_caption(orig_cap)

                if src_msg.media:
                    await client.copy_message(
                        chat_id=target_cid,
                        from_chat_id=from_chat_id,
                        message_id=current_id,
                        caption=clean_cap if clean_cap else None
                    )
                elif src_msg.text:
                    await client.send_message(
                        chat_id=target_cid,
                        text=clean_cap if clean_cap else src_msg.text
                    )
                forwarded += 1
                await asyncio.sleep(0.5)  # Safe delay to prevent Telegram FloodWait

            except Exception as e:
                err_str = str(e)
                if "FLOOD_WAIT" in err_str:
                    wait_sec = int(re.search(r'\d+', err_str).group()) if re.search(r'\d+', err_str) else 10
                    await asyncio.sleep(wait_sec + 1)
                else:
                    skipped += 1

            # Update progress every 4 seconds
            if time.time() - last_update_time > 4:
                pct = int((forwarded + skipped) / total_msgs * 100)
                filled = pct // 10
                bar = "█" * filled + "░" * (10 - filled)
                try:
                    await status_msg.edit_text(
                        f"📤 **Forwarding in Progress...**\n\n"
                        f"📊 **Progress**: `[{bar}]` **{pct}%**\n"
                        f"🔢 **Current ID**: `{current_id}/{end_id}`\n"
                        f"✅ **Forwarded**: `{forwarded}`\n"
                        f"⏩ **Skipped**: `{skipped}`\n"
                        f"🎯 **Target**: `{target_cid}`\n\n"
                        f"🛑 *Send `/stopfwd` to stop.*"
                    )
                    last_update_time = time.time()
                except Exception:
                    pass

        # Final Completion Dashboard
        await status_msg.edit_text(
            f"🎉 **Systematic Batch Forward Completed!**\n\n"
            f"✅ **Total Forwarded**: `{forwarded}`\n"
            f"⏩ **Skipped/Empty**: `{skipped}`\n"
            f"🎯 **Target Channel**: `{target_cid}`\n"
            f"⏰ **Finished At**: `{datetime.now().strftime('%d-%b-%Y %I:%M:%S %p')}`"
        )
    finally:
        ACTIVE_FWD_TASKS.discard(user_id)

@app.on_message(filters.command(["stopfwd", "cancelfwd"]) & filters.private)
async def stop_forward_cmd(client, message: Message):
    user_id = message.from_user.id
    if user_id in ACTIVE_FWD_TASKS:
        ACTIVE_FWD_TASKS.remove(user_id)
        await message.reply_text("🛑 Stopping forward task after the current message...")
    else:
        await message.reply_text("ℹ️ No active forwarding task running.")
