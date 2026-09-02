# Copyright (c) 2025 devgagan : https://github.com/devgaganin.  
# Licensed under the GNU General Public License v3.0.  
# See LICENSE file in the repository root for full license text.

import os, re, time, asyncio, json
from datetime import datetime
from pyrogram import Client, filters
from pyrogram.types import Message
from pyrogram.errors import UserNotParticipant, FloodWait
from config import API_ID, API_HASH, LOG_GROUP, STRING, FORCE_SUB, FREEMIUM_LIMIT, PREMIUM_LIMIT
from utils.func import get_user_data, screenshot, thumbnail, get_video_metadata
from utils.func import get_user_data_key, process_text_with_rules, is_premium_user, E, remove_user_session, remove_user_bot, get_log_channel
from shared_client import app as X
from plugins.settings import rename_file
from plugins.start import subscribe as sub
from utils.custom_filters import login_in_progress, settings_in_progress, settings_conversations
from utils.encrypt import dcs
from typing import Dict, Any, Optional

Y = None if not STRING else __import__('shared_client').userbot
Z, P, UB, UC, emp = {}, {}, {}, {}, {}

ACTIVE_USERS = {}
ACTIVE_USERS_FILE = "active_users.json"

def sanitize(filename):
    return re.sub(r'[<>:"/\\|?*\']', '_', filename).strip(" .")[:255]

def load_active_users():
    try:
        if os.path.exists(ACTIVE_USERS_FILE):
            with open(ACTIVE_USERS_FILE, 'r') as f:
                return json.load(f)
        return {}
    except Exception:
        return {}

async def save_active_users_to_file():
    try:
        with open(ACTIVE_USERS_FILE, 'w') as f:
            json.dump(ACTIVE_USERS, f)
    except Exception as e:
        print(f"Error saving active users: {e}")

async def add_active_batch(user_id: int, batch_info: Dict[str, Any]):
    ACTIVE_USERS[str(user_id)] = batch_info
    await save_active_users_to_file()

def is_user_active(user_id: int) -> bool:
    return str(user_id) in ACTIVE_USERS

async def update_batch_progress(user_id: int, current: int, success: int, skipped: int = 0):
    if str(user_id) in ACTIVE_USERS:
        ACTIVE_USERS[str(user_id)]["current"] = current
        ACTIVE_USERS[str(user_id)]["success"] = success
        ACTIVE_USERS[str(user_id)]["skipped"] = skipped
        await save_active_users_to_file()

async def request_batch_cancel(user_id: int):
    if str(user_id) in ACTIVE_USERS:
        ACTIVE_USERS[str(user_id)]["cancel_requested"] = True
        await save_active_users_to_file()
        return True
    return False

def should_cancel(user_id: int) -> bool:
    user_str = str(user_id)
    return user_str in ACTIVE_USERS and ACTIVE_USERS[user_str].get("cancel_requested", False)

async def remove_active_batch(user_id: int):
    if str(user_id) in ACTIVE_USERS:
        del ACTIVE_USERS[str(user_id)]
        await save_active_users_to_file()

ACTIVE_USERS = load_active_users()

async def get_ubot(uid):
    """Returns custom bot if configured via /setbot, otherwise returns main bot X"""
    bt = await get_user_data_key(uid, "bot_token", None)
    if not bt:
        return X
    if uid in UB:
        bot = UB[uid]
        if bot and not bot.is_connected:
            try:
                await bot.connect()
            except Exception:
                try:
                    await bot.start()
                except Exception:
                    pass
        if bot and bot.is_connected:
            return bot
    try:
        bot = Client(f"user_{uid}", bot_token=bt, api_id=API_ID, api_hash=API_HASH, in_memory=True, workers=20, max_concurrent_transmissions=8)
        await bot.start()
        UB[uid] = bot
        return bot
    except Exception as e:
        print(f"Custom bot error for user {uid}: {e}, defaulting to main bot")
        return X

async def get_uclient(uid):
    """Returns user client if logged in via /login or session string, with auto-reconnect"""
    if uid in UC:
        client = UC[uid]
        if client and not getattr(client, 'is_connected', False):
            try:
                await client.connect()
            except Exception:
                try:
                    await client.start()
                except Exception as ce:
                    print(f"Error reconnecting client for user {uid}: {ce}")
                    del UC[uid]
                    client = None
        if client and getattr(client, 'is_connected', False):
            return client

    ud = await get_user_data(uid)
    if not ud: return Y
    xxx = ud.get('session_string')
    if xxx:
        try:
            ss = dcs(xxx)
            gg = Client(f'{uid}_client', api_id=API_ID, api_hash=API_HASH, device_model="v3saver", session_string=ss, in_memory=True, workers=20, max_concurrent_transmissions=8)
            await gg.start()
            UC[uid] = gg
            return gg
        except Exception as e:
            print(f'User client session error: {e}')
            if "401" in str(e) or "Auth key" in str(e) or "SESSION_REVOKED" in str(e):
                try:
                    await remove_user_session(uid)
                except Exception:
                    pass
            return Y
    return Y

async def get_msg(c, u, i, d, lt, uid=None):
    """Fetch message from Telegram channel / group with auto-reconnection and retry"""
    for attempt in range(3):
        try:
            client_to_use = u if u else c
            if not client_to_use:
                if uid:
                    u = await get_uclient(uid)
                    client_to_use = u if u else c
                if not client_to_use:
                    return None

            # Ensure client is connected
            if not getattr(client_to_use, 'is_connected', False):
                try:
                    await client_to_use.connect()
                except Exception:
                    try:
                        await client_to_use.start()
                    except Exception:
                        pass

            if lt == 'public':
                target = int(i) if str(i).lstrip('-').isdigit() else str(i)
                xm = None
                if c and getattr(c, 'is_connected', False):
                    try:
                        xm = await c.get_messages(target, d)
                    except Exception:
                        pass
                if (not xm or getattr(xm, "empty", False)) and u and getattr(u, 'is_connected', False):
                    try:
                        xm = await u.get_messages(target, d)
                    except Exception:
                        pass
                if xm and not getattr(xm, "empty", False):
                    return xm
            else:
                # Private channel
                if str(i).startswith('-100'):
                    chat_id_int = int(i)
                elif str(i).lstrip('-').isdigit():
                    chat_id_int = int(f"-100{str(i).lstrip('-')}")
                else:
                    chat_id_int = i

                try:
                    result = await client_to_use.get_messages(chat_id_int, d)
                    if result and not getattr(result, "empty", False):
                        return result
                except FloodWait as fw:
                    print(f"FloodWait in get_msg: sleeping {fw.value}s")
                    await asyncio.sleep(fw.value + 1)
                    continue
                except Exception as pe:
                    try:
                        await client_to_use.get_chat(chat_id_int)
                        result = await client_to_use.get_messages(chat_id_int, d)
                        if result and not getattr(result, "empty", False):
                            return result
                    except Exception:
                        pass

            await asyncio.sleep(1)
        except Exception as e:
            print(f"get_msg attempt {attempt+1} error: {e}")
            if uid:
                u = await get_uclient(uid)
            await asyncio.sleep(1.5)
            
    return None

async def prog(c, t, C, h, m, st):
    global P
    if not t or t == 0: return
    p = c / t * 100
    interval = 10 if t >= 100 * 1024 * 1024 else 20 if t >= 50 * 1024 * 1024 else 30 if t >= 10 * 1024 * 1024 else 50
    step = int(p // interval) * interval
    if m not in P or P[m] != step or p >= 100:
        P[m] = step
        c_mb = c / (1024 * 1024)
        t_mb = t / (1024 * 1024)
        bar = '🟢' * int(p / 10) + '⚪' * (10 - int(p / 10))
        speed = c / (time.time() - st) / (1024 * 1024) if time.time() > st else 0
        eta = time.strftime('%M:%S', time.gmtime((t - c) / (speed * 1024 * 1024))) if speed > 0 else '00:00'
        try:
            await C.edit_message_text(h, m, f"⚡ **Transferring Media**\n\n{bar}\n\n📦 **Progress**: {c_mb:.2f} MB / {t_mb:.2f} MB (`{p:.1f}%`)\n🚀 **Speed**: `{speed:.2f} MB/s` | ⏳ **ETA**: `{eta}`")
        except Exception:
            pass
        if p >= 100: P.pop(m, None)

async def send_direct(c, m, tcid, ft=None, rtmid=None, uid=None, i=None):
    sent_msg = None
    try:
        if m.video:
            sent_msg = await c.send_video(tcid, m.video.file_id, caption=ft, duration=m.video.duration, width=m.video.width, height=m.video.height, reply_to_message_id=rtmid)
        elif m.video_note:
            sent_msg = await c.send_video_note(tcid, m.video_note.file_id, reply_to_message_id=rtmid)
        elif m.voice:
            sent_msg = await c.send_voice(tcid, m.voice.file_id, reply_to_message_id=rtmid)
        elif m.sticker:
            sent_msg = await c.send_sticker(tcid, m.sticker.file_id, reply_to_message_id=rtmid)
        elif m.audio:
            sent_msg = await c.send_audio(tcid, m.audio.file_id, caption=ft, duration=m.audio.duration, performer=m.audio.performer, title=m.audio.title, reply_to_message_id=rtmid)
        elif m.photo:
            photo_id = m.photo.file_id if hasattr(m.photo, 'file_id') else m.photo[-1].file_id
            sent_msg = await c.send_photo(tcid, photo_id, caption=ft, reply_to_message_id=rtmid)
        elif m.document:
            sent_msg = await c.send_document(tcid, m.document.file_id, caption=ft, file_name=m.document.file_name, reply_to_message_id=rtmid)
        else:
            return False

        if sent_msg and hasattr(sent_msg, 'id'):
            log_cid = await get_log_channel()
            if log_cid and int(tcid) != int(log_cid):
                try:
                    log_header = f"📥 **#ExtractionLog**\n\n👤 **User**: `{uid}`\n🔗 **Source**: `{i}/{m.id}`\n⏰ **Time**: `{datetime.now().strftime('%d-%b-%Y %I:%M:%S %p')}`"
                    await c.copy_message(int(log_cid), tcid, sent_msg.id, caption=log_header)
                except Exception:
                    pass
        return True
    except Exception as e:
        print(f'Direct send note: {e}')
        return False

async def process_msg(c, u, m, d, lt, uid, i, status_msg_id=None):
    try:
        cfg_chat = await get_user_data_key(d, 'chat_id', None)
        tcid = int(d)
        rtmid = None
        if cfg_chat:
            if '/' in str(cfg_chat):
                parts = str(cfg_chat).split('/', 1)
                tcid = int(parts[0])
                rtmid = int(parts[1]) if len(parts) > 1 else None
            else:
                tcid = int(cfg_chat)
        
        if m.media:
            orig_text = m.caption.markdown if m.caption else ''
            proc_text = await process_text_with_rules(d, orig_text)
            user_cap = await get_user_data_key(d, 'caption', '')
            ft = f'{proc_text}\n\n{user_cap}' if proc_text and user_cap else user_cap if user_cap else proc_text
            
            # If public, try direct forwarding/sending first
            if lt == 'public':
                sent = await send_direct(c, m, tcid, ft, rtmid, uid=uid, i=i)
                if sent:
                    return 'Sent directly.'
            
            # Download media
            st = time.time()
            if status_msg_id:
                p_id = status_msg_id
            else:
                p = await c.send_message(int(d), '⬇️ Downloading media...')
                p_id = p.id
            
            c_name = f"{time.time()}"
            if m.video:
                file_name = m.video.file_name or f"{time.time()}.mp4"
                c_name = sanitize(file_name)
            elif m.audio:
                file_name = m.audio.file_name or f"{time.time()}.mp3"
                c_name = sanitize(file_name)
            elif m.document:
                file_name = m.document.file_name or f"{time.time()}"
                c_name = sanitize(file_name)
            elif m.photo:
                file_name = f"{time.time()}.jpg"
                c_name = sanitize(file_name)

            downloader = u if u else c
            if not getattr(downloader, 'is_connected', False):
                try:
                    await downloader.connect()
                except Exception:
                    pass

            f = None
            for dl_attempt in range(3):
                try:
                    f = await downloader.download_media(m, file_name=c_name, progress=prog, progress_args=(c, int(d), p_id, st))
                    if f and os.path.exists(f):
                        break
                except FloodWait as fw:
                    await asyncio.sleep(fw.value + 1)
                except Exception as de:
                    print(f"Download attempt {dl_attempt+1} error: {de}")
                    if uid and u:
                        u = await get_uclient(uid)
                        downloader = u if u else c
                    await asyncio.sleep(2)
            
            if not f or not os.path.exists(f):
                return 'Download failed.'
            
            try:
                f = await rename_file(f, d, p_id)
            except Exception:
                pass
            
            # Uploading
            try:
                await c.edit_message_text(int(d), p_id, '⬆️ Uploading to Telegram...')
            except Exception:
                pass
            st = time.time()

            sent_msg = None
            try:
                video_extensions = ['.mp4', '.avi', '.mkv', '.mov', '.wmv', '.flv', '.webm', '.m4v', '.3gp', '.ogv']
                audio_extensions = ['.mp3', '.wav', '.flac', '.aac', '.ogg', '.wma', '.m4a', '.opus', '.aiff', '.ac3']
                file_ext = os.path.splitext(f)[1].lower()
                
                if m.video or (m.document and file_ext in video_extensions):
                    mtd = await get_video_metadata(f)
                    dur, h, w = mtd['duration'], mtd['width'], mtd['height']
                    th = await screenshot(f, dur, d)
                    sent_msg = await c.send_video(tcid, video=f, caption=ft if m.caption else None, 
                                    thumb=th, width=w, height=h, duration=dur, 
                                    progress=prog, progress_args=(c, int(d), p_id, st), 
                                    reply_to_message_id=rtmid)
                elif m.video_note:
                    sent_msg = await c.send_video_note(tcid, video_note=f, progress=prog, 
                                        progress_args=(c, int(d), p_id, st), reply_to_message_id=rtmid)
                elif m.voice:
                    sent_msg = await c.send_voice(tcid, f, progress=prog, progress_args=(c, int(d), p_id, st), 
                                    reply_to_message_id=rtmid)
                elif m.sticker:
                    sent_msg = await c.send_sticker(tcid, m.sticker.file_id, reply_to_message_id=rtmid)
                elif m.audio or (m.document and file_ext in audio_extensions):
                    sent_msg = await c.send_audio(tcid, audio=f, caption=ft if m.caption else None, 
                                    thumb=th, progress=prog, progress_args=(c, int(d), p_id, st), 
                                    reply_to_message_id=rtmid)
                elif m.photo:
                    sent_msg = await c.send_photo(tcid, photo=f, caption=ft if m.caption else None, 
                                    progress=prog, progress_args=(c, int(d), p_id, st), 
                                    reply_to_message_id=rtmid)
                else:
                    sent_msg = await c.send_document(tcid, document=f, caption=ft if m.caption else None, 
                                        progress=prog, progress_args=(c, int(d), p_id, st), 
                                        reply_to_message_id=rtmid)

                # Copy to Log Channel if active
                if sent_msg and hasattr(sent_msg, 'id'):
                    log_cid = await get_log_channel()
                    if log_cid and int(tcid) != int(log_cid):
                        try:
                            log_header = f"📥 **#ExtractionLog**\n\n👤 **User**: `{uid}`\n🔗 **Source**: `{i}/{m.id}`\n⏰ **Time**: `{datetime.now().strftime('%d-%b-%Y %I:%M:%S %p')}`"
                            await c.copy_message(int(log_cid), tcid, sent_msg.id, caption=log_header)
                        except Exception as le:
                            print(f"Log channel copy note: {le}")
            except Exception as e:
                if os.path.exists(f): os.remove(f)
                return f'Upload failed: {str(e)[:30]}'
            
            if os.path.exists(f): os.remove(f)
            if not status_msg_id:
                try:
                    await c.delete_messages(int(d), p_id)
                except Exception:
                    pass
            return 'Done.'
            
        elif m.text:
            sent_msg = await c.send_message(tcid, text=m.text.markdown, reply_to_message_id=rtmid)
            if sent_msg:
                log_cid = await get_log_channel()
                if log_cid and int(tcid) != int(log_cid):
                    try:
                        await c.send_message(int(log_cid), f"📥 **#TextLog**\n👤 **User**: `{uid}`\n💬 **Content**:\n{m.text.markdown[:500]}")
                    except Exception:
                        pass
            return 'Sent text.'
        else:
            return 'Unsupported format'
    except Exception as e:
        print(f"process_msg error: {e}")
        return f'Error: {str(e)[:50]}'

async def handle_single_extraction(c, m, ubot, uc, uid, i, d, lt):
    """Handle extraction for a single message link"""
    pt = await m.reply_text('⏳ Fetching post...')
    try:
        bot_to_use = ubot if ubot else c
        client_to_use = uc if uc else Y
        
        if lt == 'private' and not client_to_use:
            await pt.edit('⚠️ **Private Channel Notice**:\nPlease log in first with `/login` (phone number + OTP) so the bot can access this private channel.')
            return
            
        msg = await get_msg(bot_to_use, client_to_use, i, d, lt, uid=uid)
        if not msg:
            await pt.edit('❌ **Post Not Found**\n- Make sure your logged-in account has joined the channel.\n- Check if the link / post number is correct.')
            return
            
        res = await process_msg(bot_to_use, client_to_use, msg, str(m.chat.id), lt, uid, i, status_msg_id=pt.id)
        await pt.edit(f'✅ **Extraction Result**: {res}')
    except Exception as e:
        await pt.edit(f'❌ Error: {str(e)[:60]}')

@X.on_message(filters.command(['batch', 'single']))
async def process_cmd(c, m):
    uid = m.from_user.id
    cmd = m.command[0]
    
    if FREEMIUM_LIMIT == 0 and not await is_premium_user(uid):
        await m.reply_text("This bot is in premium mode. Please contact owner for subscription.")
        return
    
    if await sub(c, m) == 1: return
    
    if is_user_active(uid):
        await m.reply_text('⚠️ You already have an active batch task. Use `/stop` to cancel it first.')
        return
    
    Z[uid] = {'step': 'start' if cmd == 'batch' else 'start_single'}
    await m.reply_text(f'🔗 Send the {"start link for batch extraction" if cmd == "batch" else "link to extract"}:')

@X.on_message(filters.command(['cancel', 'stop']))
async def cancel_cmd(c, m):
    uid = m.from_user.id
    if uid in settings_conversations:
        del settings_conversations[uid]
    if is_user_active(uid):
        if await request_batch_cancel(uid):
            await m.reply_text('🛑 Cancellation requested. Ongoing batch will stop after the current file.')
        else:
            await m.reply_text('Failed to request cancellation.')
    else:
        Z.pop(uid, None)
        await m.reply_text('✅ Any ongoing process cancelled.')

@X.on_message(filters.text & filters.private & ~login_in_progress & ~settings_in_progress & ~filters.command([
    'start', 'batch', 'cancel', 'login', 'logout', 'stop', 'set', 
    'pay', 'redeem', 'gencode', 'single', 'generate', 'keyinfo', 'encrypt', 'decrypt', 'keys', 
    'setbot', 'rembot', 'settings', 'plan', 'terms', 'help', 'stats', 'status', 'add', 'rem', 
    'transfer', 'myplan', 'setlog', 'setlogchannel', 'remlog', 'removelog', 'getlog', 'log',
    'settarget', 'settargetchannel', 'gettarget', 'target', 'remtarget', 'removetarget',
    'fwd', 'forward', 'copybatch', 'sendto', 'stopfwd', 'cancelfwd']))
async def text_handler(c, m):
    uid = m.from_user.id
    if uid in settings_conversations:
        return
    text = m.text.strip()
    
    # 1. Check interactive steps (if user ran /batch or /single)
    if uid in Z:
        s = Z[uid].get('step')
        ubot = await get_ubot(uid)
        uc = await get_uclient(uid)
        
        if s == 'start':
            i, d, lt = E(text)
            if not i or not d:
                await m.reply_text('❌ Invalid link format. Please send a valid Telegram post link.')
                Z.pop(uid, None)
                return
            Z[uid].update({'step': 'count', 'cid': i, 'sid': d, 'lt': lt})
            await m.reply_text('🔢 How many consecutive posts to extract? Send a number (e.g. 5, 10, 20):')
            return

        elif s == 'start_single':
            i, d, lt = E(text)
            if not i or not d:
                await m.reply_text('❌ Invalid link format.')
                Z.pop(uid, None)
                return
            await handle_single_extraction(c, m, ubot, uc, uid, i, d, lt)
            Z.pop(uid, None)
            return

        elif s == 'count':
            if not text.isdigit():
                await m.reply_text('❌ Please enter a valid numeric count.')
                return
            
            count = int(text)
            maxlimit = PREMIUM_LIMIT if await is_premium_user(uid) else (FREEMIUM_LIMIT if FREEMIUM_LIMIT > 0 else 500)

            if count > maxlimit:
                await m.reply_text(f'⚠️ Maximum allowed limit is {maxlimit} posts.')
                return

            i, start_id, lt = Z[uid]['cid'], Z[uid]['sid'], Z[uid]['lt']
            
            # Check login for private channel before starting
            if lt == 'private' and not uc and not Y:
                await m.reply_text('⚠️ **Private Channel Warning**:\nYou are extracting from a private channel. Please `/login` with your Telegram phone number first, otherwise private messages cannot be fetched.')
                Z.pop(uid, None)
                return

            pt = await m.reply_text(f'🚀 **Starting Batch Extraction** (Total: {count} posts)...\n⏳ Initializing...')
            
            if is_user_active(uid):
                await pt.edit('⚠️ Active task already exists. Use `/stop` first.')
                Z.pop(uid, None)
                return
            
            await add_active_batch(uid, {
                "total": count,
                "current": 0,
                "success": 0,
                "skipped": 0,
                "cancel_requested": False,
                "progress_message_id": pt.id
            })
            
            success = 0
            skipped = 0
            consecutive_misses = 0
            
            try:
                for j in range(count):
                    if should_cancel(uid):
                        await pt.edit(f'🛑 **Batch Cancelled** at item {j+1}/{count}.\n✅ Success: {success} | ⏩ Skipped: {skipped}')
                        break
                    
                    mid = int(start_id) + j
                    await update_batch_progress(uid, j + 1, success, skipped)
                    
                    # Refresh user client if needed
                    if not uc or not getattr(uc, 'is_connected', False):
                        uc = await get_uclient(uid)
                    
                    # Update live dashboard
                    try:
                        await pt.edit(
                            f"🔄 **Batch Progress**: [{j+1}/{count}]\n"
                            f"📊 **Completed**: `{((j+1)/count)*100:.1f}%`\n"
                            f"✅ **Extracted**: `{success}` | ⏩ **Skipped**: `{skipped}`\n"
                            f"📥 **Fetching Post ID**: `{mid}`"
                        )
                    except Exception:
                        pass
                    
                    try:
                        msg = await get_msg(ubot, uc if uc else Y, i, mid, lt, uid=uid)
                        if msg:
                            consecutive_misses = 0
                            res = await process_msg(ubot, uc if uc else Y, msg, str(m.chat.id), lt, uid, i)
                            if 'Done' in res or 'Copied' in res or 'Sent' in res:
                                success += 1
                            else:
                                skipped += 1
                        else:
                            consecutive_misses += 1
                            skipped += 1
                            # If 5 misses in a row, refresh client connection
                            if consecutive_misses % 5 == 0:
                                uc = await get_uclient(uid)
                    except FloodWait as fw:
                        await pt.edit(f"⏳ FloodWait detected: Sleeping for {fw.value}s...")
                        await asyncio.sleep(fw.value + 1)
                    except Exception as e:
                        print(f"Batch item {j+1} (ID: {mid}) error: {e}")
                        skipped += 1
                    
                    await asyncio.sleep(1.5)
                
                await m.reply_text(
                    f"🎉 **Batch Extraction Complete!**\n\n"
                    f"📦 **Total Requested**: `{count}`\n"
                    f"✅ **Successfully Extracted**: `{success}`\n"
                    f"⏩ **Skipped / Empty**: `{skipped}`"
                )
            finally:
                await remove_active_batch(uid)
                Z.pop(uid, None)
            return

    # 2. DIRECT LINK SENT WITHOUT ANY COMMAND
    if 't.me/' in text or 'telegram.me/' in text:
        i, d, lt = E(text)
        if i and d:
            ubot = await get_ubot(uid)
            uc = await get_uclient(uid)
            await handle_single_extraction(c, m, ubot, uc, uid, i, d, lt)
            return
