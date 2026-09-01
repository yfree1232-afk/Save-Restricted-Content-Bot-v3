# Copyright (c) 2025 devgagan : https://github.com/devgaganin.  
# Licensed under the GNU General Public License v3.0.  
# See LICENSE file in the repository root for full license text.

import os, re, time, asyncio, json
from pyrogram import Client, filters
from pyrogram.types import Message
from pyrogram.errors import UserNotParticipant
from config import API_ID, API_HASH, LOG_GROUP, STRING, FORCE_SUB, FREEMIUM_LIMIT, PREMIUM_LIMIT
from utils.func import get_user_data, screenshot, thumbnail, get_video_metadata
from utils.func import get_user_data_key, process_text_with_rules, is_premium_user, E
from shared_client import app as X
from plugins.settings import rename_file
from plugins.start import subscribe as sub
from utils.custom_filters import login_in_progress
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

async def update_batch_progress(user_id: int, current: int, success: int):
    if str(user_id) in ACTIVE_USERS:
        ACTIVE_USERS[str(user_id)]["current"] = current
        ACTIVE_USERS[str(user_id)]["success"] = success
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

async def upd_dlg(c):
    try:
        async for _ in c.get_dialogs(limit=20): pass
        return True
    except Exception as e:
        print(f'Dialog update note: {e}')
        return False

async def get_msg(c, u, i, d, lt):
    """Fetch message from Telegram channel / group"""
    try:
        if lt == 'public':
            target = int(i) if str(i).lstrip('-').isdigit() else str(i)
            xm = None
            if c:
                try:
                    xm = await c.get_messages(target, d)
                except Exception as ce:
                    print(f"Public msg fetch via bot note: {ce}")
            if (not xm or getattr(xm, "empty", False)) and u:
                try:
                    xm = await u.get_messages(target, d)
                except Exception as ue:
                    print(f"Public msg fetch via userbot note: {ue}")
            return xm if (xm and not getattr(xm, "empty", False)) else None
        else:
            # Private channel
            client_to_use = u if u else c
            if not client_to_use:
                print("No client available for private message")
                return None
            
            # Ensure correct integer chat_id
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
            except Exception as pe:
                print(f"Direct get_messages failed ({pe}), attempting to resolve peer...")
                try:
                    await client_to_use.get_chat(chat_id_int)
                    result = await client_to_use.get_messages(chat_id_int, d)
                    if result and not getattr(result, "empty", False):
                        return result
                except Exception as e2:
                    print(f"Resolve peer get_messages failed: {e2}")
            
            return None
    except Exception as e:
        print(f'Error in get_msg: {e}')
        return None

async def get_ubot(uid):
    """Returns custom bot if configured via /setbot, otherwise returns main bot X"""
    bt = await get_user_data_key(uid, "bot_token", None)
    if not bt:
        return X
    if uid in UB:
        return UB.get(uid)
    try:
        bot = Client(f"user_{uid}", bot_token=bt, api_id=API_ID, api_hash=API_HASH)
        await bot.start()
        UB[uid] = bot
        return bot
    except Exception as e:
        print(f"Error starting custom bot for user {uid}: {e}, defaulting to main bot")
        return X

async def get_uclient(uid):
    """Returns user client if logged in via /login or session string, else None"""
    cl = UC.get(uid)
    if cl: return cl
    ud = await get_user_data(uid)
    if not ud: return Y
    xxx = ud.get('session_string')
    if xxx:
        try:
            ss = dcs(xxx)
            gg = Client(f'{uid}_client', api_id=API_ID, api_hash=API_HASH, device_model="v3saver", session_string=ss)
            await gg.start()
            UC[uid] = gg
            return gg
        except Exception as e:
            print(f'User client error: {e}')
            return Y
    return Y

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
        bar = '🟢' * int(p / 10) + '🔴' * (10 - int(p / 10))
        speed = c / (time.time() - st) / (1024 * 1024) if time.time() > st else 0
        eta = time.strftime('%M:%S', time.gmtime((t - c) / (speed * 1024 * 1024))) if speed > 0 else '00:00'
        try:
            await C.edit_message_text(h, m, f"__**Processing Media...**__\n\n{bar}\n\n⚡ **__Progress__**: {c_mb:.2f} MB / {t_mb:.2f} MB ({p:.1f}%)\n🚀 **__Speed__**: {speed:.2f} MB/s\n⏳ **__ETA__**: {eta}")
        except Exception:
            pass
        if p >= 100: P.pop(m, None)

async def send_direct(c, m, tcid, ft=None, rtmid=None):
    try:
        if m.video:
            await c.send_video(tcid, m.video.file_id, caption=ft, duration=m.video.duration, width=m.video.width, height=m.video.height, reply_to_message_id=rtmid)
        elif m.video_note:
            await c.send_video_note(tcid, m.video_note.file_id, reply_to_message_id=rtmid)
        elif m.voice:
            await c.send_voice(tcid, m.voice.file_id, reply_to_message_id=rtmid)
        elif m.sticker:
            await c.send_sticker(tcid, m.sticker.file_id, reply_to_message_id=rtmid)
        elif m.audio:
            await c.send_audio(tcid, m.audio.file_id, caption=ft, duration=m.audio.duration, performer=m.audio.performer, title=m.audio.title, reply_to_message_id=rtmid)
        elif m.photo:
            photo_id = m.photo.file_id if hasattr(m.photo, 'file_id') else m.photo[-1].file_id
            await c.send_photo(tcid, photo_id, caption=ft, reply_to_message_id=rtmid)
        elif m.document:
            await c.send_document(tcid, m.document.file_id, caption=ft, file_name=m.document.file_name, reply_to_message_id=rtmid)
        else:
            return False
        return True
    except Exception as e:
        print(f'Direct send note: {e}')
        return False

async def process_msg(c, u, m, d, lt, uid, i):
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
                sent = await send_direct(c, m, tcid, ft, rtmid)
                if sent:
                    return 'Sent directly.'
            
            # Download media
            st = time.time()
            p = await c.send_message(int(d), '⬇️ Downloading media...')
            
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
            f = await downloader.download_media(m, file_name=c_name, progress=prog, progress_args=(c, int(d), p.id, st))
            
            if not f or not os.path.exists(f):
                await c.edit_message_text(int(d), p.id, '❌ Download failed.')
                return 'Download failed.'
            
            try:
                await c.edit_message_text(int(d), p.id, '🏷️ Processing file...')
                f = await rename_file(f, d, p)
            except Exception:
                pass
            
            fsize = os.path.getsize(f) / (1024 * 1024 * 1024)
            th = thumbnail(d)
            
            # Uploading
            await c.edit_message_text(int(d), p.id, '⬆️ Uploading to Telegram...')
            st = time.time()

            try:
                video_extensions = ['.mp4', '.avi', '.mkv', '.mov', '.wmv', '.flv', '.webm', '.m4v', '.3gp', '.ogv']
                audio_extensions = ['.mp3', '.wav', '.flac', '.aac', '.ogg', '.wma', '.m4a', '.opus', '.aiff', '.ac3']
                file_ext = os.path.splitext(f)[1].lower()
                
                if m.video or (m.document and file_ext in video_extensions):
                    mtd = await get_video_metadata(f)
                    dur, h, w = mtd['duration'], mtd['width'], mtd['height']
                    th = await screenshot(f, dur, d)
                    await c.send_video(tcid, video=f, caption=ft if m.caption else None, 
                                    thumb=th, width=w, height=h, duration=dur, 
                                    progress=prog, progress_args=(c, int(d), p.id, st), 
                                    reply_to_message_id=rtmid)
                elif m.video_note:
                    await c.send_video_note(tcid, video_note=f, progress=prog, 
                                        progress_args=(c, int(d), p.id, st), reply_to_message_id=rtmid)
                elif m.voice:
                    await c.send_voice(tcid, f, progress=prog, progress_args=(c, int(d), p.id, st), 
                                    reply_to_message_id=rtmid)
                elif m.sticker:
                    await c.send_sticker(tcid, m.sticker.file_id, reply_to_message_id=rtmid)
                elif m.audio or (m.document and file_ext in audio_extensions):
                    await c.send_audio(tcid, audio=f, caption=ft if m.caption else None, 
                                    thumb=th, progress=prog, progress_args=(c, int(d), p.id, st), 
                                    reply_to_message_id=rtmid)
                elif m.photo:
                    await c.send_photo(tcid, photo=f, caption=ft if m.caption else None, 
                                    progress=prog, progress_args=(c, int(d), p.id, st), 
                                    reply_to_message_id=rtmid)
                else:
                    await c.send_document(tcid, document=f, caption=ft if m.caption else None, 
                                        progress=prog, progress_args=(c, int(d), p.id, st), 
                                        reply_to_message_id=rtmid)
            except Exception as e:
                await c.edit_message_text(int(d), p.id, f'❌ Upload failed: {str(e)[:40]}')
                if os.path.exists(f): os.remove(f)
                return 'Upload failed.'
            
            if os.path.exists(f): os.remove(f)
            await c.delete_messages(int(d), p.id)
            return 'Done.'
            
        elif m.text:
            await c.send_message(tcid, text=m.text.markdown, reply_to_message_id=rtmid)
            return 'Sent text.'
    except Exception as e:
        print(f"process_msg error: {e}")
        return f'Error: {str(e)[:50]}'

async def handle_single_extraction(c, m, ubot, uc, uid, i, d, lt):
    """Handle extraction for a single message link"""
    pt = await m.reply_text('⏳ Processing link...')
    try:
        bot_to_use = ubot if ubot else c
        client_to_use = uc if uc else Y
        
        if lt == 'private' and not client_to_use:
            await pt.edit('⚠️ **Restricted Channel Notice**:\nThis is a private/restricted channel link.\nPlease log in first with `/login` (phone number + OTP) so the bot can access your channel.')
            return
            
        msg = await get_msg(bot_to_use, client_to_use, i, d, lt)
        if not msg:
            await pt.edit('❌ **Message Not Found**\n- Make sure your logged-in account has joined the channel.\n- Check if the link is valid.')
            return
            
        res = await process_msg(bot_to_use, client_to_use, msg, str(m.chat.id), lt, uid, i)
        await pt.edit(f'✅ Result: {res}')
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
    if is_user_active(uid):
        if await request_batch_cancel(uid):
            await m.reply_text('🛑 Cancellation requested. Ongoing batch will stop soon.')
        else:
            await m.reply_text('Failed to request cancellation.')
    else:
        Z.pop(uid, None)
        await m.reply_text('✅ Any ongoing process cancelled.')

@X.on_message(filters.text & filters.private & ~login_in_progress & ~filters.command([
    'start', 'batch', 'cancel', 'login', 'logout', 'stop', 'set', 
    'pay', 'redeem', 'gencode', 'single', 'generate', 'keyinfo', 'encrypt', 'decrypt', 'keys', 'setbot', 'rembot', 'settings', 'plan', 'terms', 'help', 'stats', 'status', 'add', 'rem', 'transfer']))
async def text_handler(c, m):
    uid = m.from_user.id
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
            await m.reply_text('🔢 How many consecutive posts to extract? Send a number (e.g. 5, 10):')
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

            Z[uid].update({'step': 'process', 'did': str(m.chat.id), 'num': count})
            i, s, n, lt = Z[uid]['cid'], Z[uid]['sid'], Z[uid]['num'], Z[uid]['lt']
            success = 0

            pt = await m.reply_text('🚀 Starting batch extraction...')
            
            if is_user_active(uid):
                await pt.edit('⚠️ Active task already exists. Use /stop first.')
                Z.pop(uid, None)
                return
            
            await add_active_batch(uid, {
                "total": n,
                "current": 0,
                "success": 0,
                "cancel_requested": False,
                "progress_message_id": pt.id
            })
            
            try:
                for j in range(n):
                    if should_cancel(uid):
                        await pt.edit(f'🛑 Batch cancelled at {j}/{n}. Success: {success}')
                        break
                    
                    await update_batch_progress(uid, j, success)
                    mid = int(s) + j
                    
                    try:
                        msg = await get_msg(ubot, uc if uc else Y, i, mid, lt)
                        if msg:
                            res = await process_msg(ubot, uc if uc else Y, msg, str(m.chat.id), lt, uid, i)
                            if 'Done' in res or 'Copied' in res or 'Sent' in res:
                                success += 1
                    except Exception as e:
                        print(f"Batch item {j+1} error: {e}")
                    
                    await asyncio.sleep(2)
                
                await m.reply_text(f'🎉 **Batch Completed!**\n✅ Successfully Extracted: {success}/{n}')
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
