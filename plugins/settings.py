# Copyright (c) 2025 devgagan : https://github.com/devgaganin.  
# Licensed under the GNU General Public License v3.0.  
# See LICENSE file in the repository root for full license text.

import re
import os
import asyncio
import string
import random
from pyrogram import filters
from pyrogram.types import InlineKeyboardButton, InlineKeyboardMarkup, Message, CallbackQuery
from shared_client import app
from config import OWNER_ID, JOIN_LINK
from utils.func import get_user_data_key, save_user_data, users_collection, remove_user_session
from utils.custom_filters import settings_conversations, settings_in_progress

VIDEO_EXTENSIONS = {
    'mp4', 'mkv', 'avi', 'mov', 'wmv', 'flv', 'webm',
    'mpeg', 'mpg', '3gp'
}
MESS = """⚙️ **Bot Customization Settings**

Customize how the bot processes and uploads your files:
• Set destination Chat/Channel ID
• Set custom rename tag & custom caption
• Replace or remove unwanted words
• Set custom video/file thumbnail
• Manage your session login"""

def get_settings_keyboard():
    return InlineKeyboardMarkup([
        [
            InlineKeyboardButton('📝 Set Chat ID', callback_data='set_chat'),
            InlineKeyboardButton('🏷️ Set Rename Tag', callback_data='set_rename')
        ],
        [
            InlineKeyboardButton('📋 Set Caption', callback_data='set_caption'),
            InlineKeyboardButton('🔄 Replace Words', callback_data='set_replacement')
        ],
        [
            InlineKeyboardButton('🗑️ Remove Words', callback_data='set_delete'),
            InlineKeyboardButton('🔄 Reset Settings', callback_data='reset_settings')
        ],
        [
            InlineKeyboardButton('🖼️ Set Thumbnail', callback_data='set_thumb'),
            InlineKeyboardButton('❌ Remove Thumbnail', callback_data='rem_thumb')
        ],
        [
            InlineKeyboardButton('🚪 Logout Session', callback_data='logout_session'),
            InlineKeyboardButton('📢 Update Channel', url=JOIN_LINK)
        ]
    ])

@app.on_message(filters.command(['settings']) & filters.private)
async def settings_command(client, message: Message):
    user_id = message.from_user.id
    await message.reply_text(MESS, reply_markup=get_settings_keyboard())

@app.on_callback_query(filters.regex(r'^(set_chat|set_rename|set_caption|set_replacement|set_delete|set_thumb|rem_thumb|reset_settings|logout_session|open_settings)$'))
async def settings_callbacks(client, callback_query: CallbackQuery):
    user_id = callback_query.from_user.id
    data = callback_query.data

    if data == 'open_settings':
        await callback_query.message.edit_text(MESS, reply_markup=get_settings_keyboard())
        await callback_query.answer()
        return

    if data == 'set_chat':
        settings_conversations[user_id] = 'set_chat'
        await callback_query.message.reply_text(
            "📝 **Set Destination Chat ID**:\n\n"
            "Send the ID of the channel/group where files should be uploaded (e.g. `-1001234567890`).\n"
            "👉 *For topics in forum groups, use format: `-100CHANNELID/TOPIC_ID`*\n\n"
            "(Send `/cancel` to cancel)",
            quote=True
        )
        await callback_query.answer()

    elif data == 'set_rename':
        settings_conversations[user_id] = 'set_rename'
        await callback_query.message.reply_text(
            "🏷️ **Set Custom Rename Tag**:\n\n"
            "Send the tag to append to downloaded file names (e.g. `@voltxbots`).\n\n"
            "(Send `/cancel` to cancel)",
            quote=True
        )
        await callback_query.answer()

    elif data == 'set_caption':
        settings_conversations[user_id] = 'set_caption'
        await callback_query.message.reply_text(
            "📋 **Set Custom Caption**:\n\n"
            "Send the custom caption to add to all your uploaded files.\n\n"
            "(Send `/cancel` to cancel)",
            quote=True
        )
        await callback_query.answer()

    elif data == 'set_replacement':
        settings_conversations[user_id] = 'set_replacement'
        await callback_query.message.reply_text(
            "🔄 **Word Replacement**:\n\n"
            "Send replacement in format: `'old_word' 'new_word'`\n"
            "Example: `'@oldchannel' '@voltxbots'`\n\n"
            "(Send `/cancel` to cancel)",
            quote=True
        )
        await callback_query.answer()

    elif data == 'set_delete':
        settings_conversations[user_id] = 'set_delete'
        await callback_query.message.reply_text(
            "🗑️ **Remove Words**:\n\n"
            "Send words separated by spaces to remove them completely from filenames and captions.\n\n"
            "(Send `/cancel` to cancel)",
            quote=True
        )
        await callback_query.answer()

    elif data == 'set_thumb':
        settings_conversations[user_id] = 'set_thumb'
        await callback_query.message.reply_text(
            "🖼️ **Set Custom Thumbnail**:\n\n"
            "Please send the **Photo** you want to use as your custom thumbnail.\n\n"
            "(Send `/cancel` to cancel)",
            quote=True
        )
        await callback_query.answer()

    elif data == 'rem_thumb':
        thumb_path = f'{user_id}.jpg'
        if os.path.exists(thumb_path):
            try:
                os.remove(thumb_path)
                await callback_query.answer("✅ Thumbnail removed successfully!", show_alert=True)
            except Exception as e:
                await callback_query.answer(f"Error: {e}", show_alert=True)
        else:
            await callback_query.answer("ℹ️ No custom thumbnail was set.", show_alert=True)

    elif data == 'reset_settings':
        try:
            await users_collection.update_one(
                {'user_id': user_id},
                {'$unset': {
                    'delete_words': '',
                    'replacement_words': '',
                    'rename_tag': '',
                    'caption': '',
                    'chat_id': ''
                }}
            )
            thumb_path = f'{user_id}.jpg'
            if os.path.exists(thumb_path):
                try: os.remove(thumb_path)
                except Exception: pass
            await callback_query.answer("✅ All settings reset to default!", show_alert=True)
            await callback_query.message.reply_text("✅ All your settings have been reset to default values.")
        except Exception as e:
            await callback_query.answer(f"Reset Error: {e}", show_alert=True)

    elif data == 'logout_session':
        ok = await remove_user_session(user_id)
        if ok:
            await callback_query.answer("✅ Logged out successfully!", show_alert=True)
            await callback_query.message.reply_text("🚪 **Logged out**: Your Telegram session has been deleted from the database.")
        else:
            await callback_query.answer("ℹ️ You were not logged in.", show_alert=True)

@app.on_message(settings_in_progress & filters.photo & filters.private)
async def photo_conversation_handler(client, message: Message):
    user_id = message.from_user.id
    if user_id in settings_conversations and settings_conversations[user_id] == 'set_thumb':
        try:
            thumb_path = f'{user_id}.jpg'
            if os.path.exists(thumb_path):
                os.remove(thumb_path)
            await message.download(file_name=thumb_path)
            del settings_conversations[user_id]
            await message.reply_text("✅ **Custom Thumbnail Saved Successfully!**")
        except Exception as e:
            await message.reply_text(f"❌ Error saving thumbnail: {e}")

@app.on_message(settings_in_progress & filters.text & filters.private & ~filters.command([
    'start', 'batch', 'cancel', 'login', 'logout', 'stop', 'set', 'pay',
    'redeem', 'gencode', 'single', 'generate', 'keyinfo', 'encrypt', 'decrypt',
    'keys', 'setbot', 'rembot', 'settings', 'plan', 'terms', 'help', 'stats', 'status', 
    'add', 'rem', 'transfer', 'myplan', 'setlog', 'setlogchannel', 'remlog', 'removelog',
    'getlog', 'log', 'settarget', 'settargetchannel', 'gettarget', 'target', 'remtarget',
    'removetarget', 'fwd', 'forward', 'copybatch', 'sendto', 'stopfwd', 'cancelfwd']))
async def settings_text_input_handler(client, message: Message):
    user_id = message.from_user.id
    if user_id not in settings_conversations:
        return

    conv_type = settings_conversations[user_id]
    text = message.text.strip()

    if conv_type == 'set_chat':
        chat_id = text.strip()
        await save_user_data(user_id, 'chat_id', chat_id)
        del settings_conversations[user_id]
        await message.reply_text(f"✅ **Chat ID set to**: `{chat_id}`")

    elif conv_type == 'set_rename':
        rename_tag = text.strip()
        await save_user_data(user_id, 'rename_tag', rename_tag)
        del settings_conversations[user_id]
        await message.reply_text(f"✅ **Rename tag set to**: `{rename_tag}`")

    elif conv_type == 'set_caption':
        caption = text.strip()
        await save_user_data(user_id, 'caption', caption)
        del settings_conversations[user_id]
        await message.reply_text(f"✅ **Custom caption set to**:\n\n{caption}")

    elif conv_type == 'set_replacement':
        try:
            matches = re.findall(r"'([^']*)'", text)
            if len(matches) >= 2:
                old_w, new_w = matches[0], matches[1]
            else:
                parts = text.split()
                old_w, new_w = parts[0], parts[1] if len(parts) > 1 else ''
            
            replacements = await get_user_data_key(user_id, 'replacement_words', {})
            replacements[old_w] = new_w
            await save_user_data(user_id, 'replacement_words', replacements)
            del settings_conversations[user_id]
            await message.reply_text(f"✅ **Replacement Saved**: `{old_w}` ➔ `{new_w}`")
        except Exception as e:
            await message.reply_text(f"❌ Format error: {e}. Please use format: `'old'` `'new'`")

    elif conv_type == 'set_delete':
        words = text.split()
        delete_words = await get_user_data_key(user_id, 'delete_words', [])
        delete_words = list(set(delete_words + words))
        await save_user_data(user_id, 'delete_words', delete_words)
        del settings_conversations[user_id]
        await message.reply_text(f"✅ **Words added to delete list**: {', '.join(words)}")

async def rename_file(file, sender, edit):
    """Renames file according to user settings (delete words, replacements, rename tag)"""
    try:
        delete_words = await get_user_data_key(sender, 'delete_words', [])
        custom_rename_tag = await get_user_data_key(sender, 'rename_tag', '')
        replacements = await get_user_data_key(sender, 'replacement_words', {})
        
        last_dot_index = str(file).rfind('.')
        if last_dot_index != -1 and last_dot_index != 0:
            ggn_ext = str(file)[last_dot_index + 1:]
            if ggn_ext.isalpha() and len(ggn_ext) <= 9:
                if ggn_ext.lower() in VIDEO_EXTENSIONS:
                    original_file_name = str(file)[:last_dot_index]
                    file_extension = 'mp4'
                else:
                    original_file_name = str(file)[:last_dot_index]
                    file_extension = ggn_ext
            else:
                original_file_name = str(file)[:last_dot_index]
                file_extension = 'mp4'
        else:
            original_file_name = str(file)
            file_extension = 'mp4'
        
        for word in delete_words:
            original_file_name = original_file_name.replace(word, '')
        
        for word, replace_word in replacements.items():
            original_file_name = original_file_name.replace(word, replace_word)
        
        tag_str = f" {custom_rename_tag}".strip()
        new_file_name = f"{original_file_name.strip()} {tag_str}.{file_extension}".strip() if tag_str else f"{original_file_name.strip()}.{file_extension}"
        
        if new_file_name != str(file):
            os.rename(file, new_file_name)
            return new_file_name
        return file
    except Exception as e:
        print(f"Rename error: {e}")
        return file
