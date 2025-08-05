import telebot
import random
import time
import datetime
import sqlite3
from db_operations import get_pack_limit, count_packs, count_stickers, send_random_sticker, update_user, get_reply_chance, set_reply_chance, conn, get_chat_language, set_chat_language
from translations import get_translation, get_user_language

def log(msg):
    """Log messages with timestamp."""
    print(f"{datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')} - {msg}")

def is_admin(bot, chat_id, user_id):
    """Check if the user is an admin or creator of the chat."""
    try:
        chat_member = bot.get_chat_member(chat_id, user_id)
        return chat_member.status in ["administrator", "creator"]
    except Exception as e:
        log(f"chat_id={chat_id}, user_id={user_id}: Failed to check admin status: {e}")
        return False

def handle_sticker(bot, message):
    """Handle incoming sticker messages."""
    chat_id = message.chat.id
    update_user(message.from_user, is_media=False)
    pack_name = message.sticker.set_name

    if not pack_name:
        log(f"chat_id={chat_id}: Sticker without set_name, ignored")
        return

    with conn:
        cur = conn.cursor()
        cur.execute("SELECT status FROM packs WHERE chat_id=? AND set_name=?", (chat_id, pack_name))
        row = cur.fetchone()

    if row and row[0] == "banned":
        log(f"chat_id={chat_id}: Pack '{pack_name}' is banned, ignored")
        return

    limit = get_pack_limit(chat_id)
    current_count = count_packs(chat_id)
    if current_count >= limit:
        log(f"chat_id={chat_id}: Pack limit {limit} reached, new pack '{pack_name}' not added")
        return

    try:
        sticker_set = bot.get_sticker_set(pack_name)
        sticker_count = len(sticker_set.stickers)
    except Exception as e:
        log(f"chat_id={chat_id}: Failed to get sticker count for '{pack_name}': {e}")
        sticker_count = 0

    try:
        with conn:
            cur = conn.cursor()
            cur.execute("INSERT INTO packs (chat_id, set_name, sticker_count) VALUES (?, ?, ?)",
                        (chat_id, pack_name, sticker_count))
        log(f"chat_id={chat_id}: Added new pack '{pack_name}' ({sticker_count} stickers)")
    except sqlite3.IntegrityError:
        log(f"chat_id={chat_id}: Pack '{pack_name}' already in database, skipped")

def random_pack(bot, message):
    """Handle /random_pack command to send a random sticker."""
    chat_id = message.chat.id
    user_id = message.from_user.id
    log(f"chat_id={chat_id}: Requested random sticker (/random_pack)")
    if not send_random_sticker(bot, chat_id, reply_to_message_id=message.message_id):
        bot.reply_to(message, get_translation(get_user_language(user_id, chat_id), "no_packs"))

def stats(bot, message):
    """Handle /stats command to show pack statistics."""
    chat_id = message.chat.id
    user_id = message.from_user.id
    limit = get_pack_limit(chat_id)
    count = count_packs(chat_id)
    stickers_total = count_stickers(chat_id)
    log(f"chat_id={chat_id}: Requested statistics (/stats)")
    bot.reply_to(message, get_translation(get_user_language(user_id, chat_id), "stats").format(count=count, stickers_total=stickers_total, limit=limit))

def set_reply_chance_command(bot, message):
    """Handle /set_reply_chance command to set sticker reply chance."""
    chat_id = message.chat.id
    user_id = message.from_user.id
    if message.chat.type != "private" and not is_admin(bot, chat_id, user_id):
        bot.reply_to(message, get_translation(get_user_language(user_id, chat_id), "admin_only"))
        log(f"chat_id={chat_id}, user_id={user_id}: Non-admin attempted to set reply chance")
        return

    args = message.text.split()
    if len(args) < 2:
        bot.reply_to(message, get_translation(get_user_language(user_id, chat_id), "set_reply_chance_usage"))
        return
    try:
        new_chance = float(args[1]) / 100
        if not (0 <= new_chance <= 1):
            raise ValueError()
    except ValueError:
        bot.reply_to(message, get_translation(get_user_language(user_id, chat_id), "invalid_chance"))
        return

    set_reply_chance(chat_id, new_chance)
    bot.reply_to(message, get_translation(get_user_language(user_id, chat_id), "reply_chance_set").format(chance=args[1]))
    log(f"chat_id={chat_id}: Sticker reply chance set to {args[1]}%")

def get_reply_chance_command(bot, message):
    """Handle /get_reply_chance command to show current reply chance."""
    chat_id = message.chat.id
    user_id = message.from_user.id
    chance = get_reply_chance(chat_id) * 100
    bot.reply_to(message, get_translation(get_user_language(user_id, chat_id), "get_reply_chance").format(chance=chance))
    log(f"chat_id={chat_id}: Requested reply chance ({chance:.2f}%)")

def ban_pack(bot, message):
    """Handle /ban_pack command to ban a sticker pack."""
    chat_id = message.chat.id
    user_id = message.from_user.id
    if message.chat.type != "private" and not is_admin(bot, chat_id, user_id):
        bot.reply_to(message, get_translation(get_user_language(user_id, chat_id), "admin_only"))
        log(f"chat_id={chat_id}, user_id={user_id}: Non-admin attempted to ban pack")
        return

    args = message.text.split()
    if len(args) < 2:
        bot.reply_to(message, get_translation(get_user_language(user_id, chat_id), "ban_pack_usage"))
        return
    pack_name = args[1]

    with conn:
        cur = conn.cursor()
        cur.execute("UPDATE packs SET status='banned' WHERE chat_id=? AND set_name=?", (chat_id, pack_name))
        if cur.rowcount == 0:
            bot.reply_to(message, get_translation(get_user_language(user_id, chat_id), "pack_not_found").format(pack_name=pack_name))
            log(f"chat_id={chat_id}: Attempt to ban non-existent pack '{pack_name}'")
        else:
            bot.reply_to(message, get_translation(get_user_language(user_id, chat_id), "pack_banned").format(pack_name=pack_name))
            log(f"chat_id={chat_id}: Pack '{pack_name}' banned")

def unban_pack(bot, message):
    """Handle /unban_pack command to unban a sticker pack."""
    chat_id = message.chat.id
    user_id = message.from_user.id
    if message.chat.type != "private" and not is_admin(bot, chat_id, user_id):
        bot.reply_to(message, get_translation(get_user_language(user_id, chat_id), "admin_only"))
        log(f"chat_id={chat_id}, user_id={user_id}: Non-admin attempted to unban pack")
        return

    args = message.text.split()
    if len(args) < 2:
        bot.reply_to(message, get_translation(get_user_language(user_id, chat_id), "unban_pack_usage"))
        return
    pack_name = args[1]

    with conn:
        cur = conn.cursor()
        cur.execute("UPDATE packs SET status='allowed' WHERE chat_id=? AND set_name=?", (chat_id, pack_name))
        if cur.rowcount == 0:
            bot.reply_to(message, get_translation(get_user_language(user_id, chat_id), "pack_not_found").format(pack_name=pack_name))
            log(f"chat_id={chat_id}: Attempt to unban non-existent pack '{pack_name}'")
        else:
            bot.reply_to(message, get_translation(get_user_language(user_id, chat_id), "pack_unbanned").format(pack_name=pack_name))
            log(f"chat_id={chat_id}: Pack '{pack_name}' unbanned")

def list_packs(bot, message):
    """Handle /list_packs command to list all packs."""
    chat_id = message.chat.id
    user_id = message.from_user.id
    with conn:
        cur = conn.cursor()
        cur.execute("SELECT set_name, status FROM packs WHERE chat_id=?", (chat_id,))
        rows = cur.fetchall()

    if not rows:
        bot.reply_to(message, get_translation(get_user_language(user_id, chat_id), "no_packs"))
        log(f"chat_id={chat_id}: Requested pack list, but database is empty")
        return

    text = get_translation(get_user_language(user_id, chat_id), "pack_list") + "\n"
    for set_name, status in rows:
        emoji = "✅" if status == "allowed" else "🚫"
        text += f"{emoji} {set_name}\n"
    bot.reply_to(message, text)
    log(f"chat_id={chat_id}: Sent pack list (count: {len(rows)})")

def clear_packs(bot, message):
    """Handle /clear_packs command to clear all packs in a chat."""
    chat_id = message.chat.id
    user_id = message.from_user.id
    if message.chat.type != "private" and not is_admin(bot, chat_id, user_id):
        bot.reply_to(message, get_translation(get_user_language(user_id, chat_id), "admin_only"))
        log(f"chat_id={chat_id}, user_id={user_id}: Non-admin attempted to clear packs")
        return

    with conn:
        cur = conn.cursor()
        cur.execute("DELETE FROM packs WHERE chat_id=?", (chat_id,))
    bot.reply_to(message, get_translation(get_user_language(user_id, chat_id), "packs_cleared"))
    log(f"chat_id={chat_id}: Cleared pack database")

def set_pack_limit(bot, message):
    """Handle /set_pack_limit command to set pack limit."""
    chat_id = message.chat.id
    user_id = message.from_user.id
    if message.chat.type != "private" and not is_admin(bot, chat_id, user_id):
        bot.reply_to(message, get_translation(get_user_language(user_id, chat_id), "admin_only"))
        log(f"chat_id={chat_id}, user_id={user_id}: Non-admin attempted to set pack limit")
        return

    args = message.text.split()
    if len(args) < 2:
        bot.reply_to(message, get_translation(get_user_language(user_id, chat_id), "set_pack_limit_usage"))
        return
    try:
        new_limit = int(args[1])
        if new_limit <= 0:
            raise ValueError()
    except ValueError:
        bot.reply_to(message, get_translation(get_user_language(user_id, chat_id), "invalid_limit"))
        return

    with conn:
        cur = conn.cursor()
        cur.execute("INSERT OR REPLACE INTO chat_settings (chat_id, pack_limit, reply_chance, language) "
                    "VALUES (?, ?, COALESCE((SELECT reply_chance FROM chat_settings WHERE chat_id=?), 0.05), "
                    "COALESCE((SELECT language FROM chat_settings WHERE chat_id=?), 'en'))",
                    (chat_id, new_limit, chat_id, chat_id))
    bot.reply_to(message, get_translation(get_user_language(user_id, chat_id), "pack_limit_set").format(limit=new_limit))
    log(f"chat_id={chat_id}: Pack limit set to {new_limit}")

def get_pack_limit_command(bot, message):
    """Handle /get_pack_limit command to show current pack limit."""
    chat_id = message.chat.id
    user_id = message.from_user.id
    limit = get_pack_limit(chat_id)
    bot.reply_to(message, get_translation(get_user_language(user_id, chat_id), "get_pack_limit").format(limit=limit))
    log(f"chat_id={chat_id}: Requested pack limit ({limit})")

def help_command(bot, message):
    """Handle /help command to show available commands."""
    chat_id = message.chat.id
    user_id = message.from_user.id
    bot.reply_to(message, get_translation(get_user_language(user_id, chat_id), "help"))
    log(f"chat_id={chat_id}: Requested help (/help)")

def top_users(bot, message):
    """Handle /top_users command to show top users by activity."""
    chat_id = message.chat.id
    user_id = message.from_user.id
    with conn:
        cur = conn.cursor()
        cur.execute("""
        SELECT username, first_name, sticker_calls, media_calls 
        FROM users ORDER BY (sticker_calls + media_calls) DESC LIMIT 10
        """)
        rows = cur.fetchall()

    if not rows:
        bot.reply_to(message, get_translation(get_user_language(user_id, chat_id), "no_users"))
        return

    text = get_translation(get_user_language(user_id, chat_id), "top_users") + "\n"
    for i, (username, first_name, stickers, media) in enumerate(rows, 1):
        name = f"@{username}" if username else first_name
        text += f"{i}. {name} — 🎯 {stickers} {get_translation(get_user_language(user_id, chat_id), 'stickers_label')}, 📷 {media} {get_translation(get_user_language(user_id, chat_id), 'media_label')}\n"
    bot.reply_to(message, text)

def set_language_command(bot, message):
    """Handle /set_language command to show language selection buttons."""
    chat_id = message.chat.id
    user_id = message.from_user.id

    # Skip admin check in private chats
    if message.chat.type != "private" and not is_admin(bot, chat_id, user_id):
        bot.reply_to(message, get_translation(get_user_language(user_id, chat_id), "admin_only"))
        log(f"chat_id={chat_id}, user_id={user_id}: Non-admin attempted to change chat language")
        return

    # Create inline keyboard with language options
    keyboard = telebot.types.InlineKeyboardMarkup()
    keyboard.row(
        telebot.types.InlineKeyboardButton(get_translation(get_user_language(user_id, chat_id), "lang_ru"), callback_data=f"lang:ru:{chat_id}"),
        telebot.types.InlineKeyboardButton(get_translation(get_user_language(user_id, chat_id), "lang_uk"), callback_data=f"lang:uk:{chat_id}"),
        telebot.types.InlineKeyboardButton(get_translation(get_user_language(user_id, chat_id), "lang_en"), callback_data=f"lang:en:{chat_id}")
    )

    # Send message with buttons
    bot.send_message(chat_id, get_translation(get_user_language(user_id, chat_id), "select_language"), reply_markup=keyboard)
    log(f"chat_id={chat_id}, user_id={user_id}: Sent language selection buttons")

def handle_language_callback(bot, call):
    """Handle callback queries from language selection buttons."""
    chat_id = call.message.chat.id
    user_id = call.from_user.id
    data = call.data.split(":")

    if len(data) != 3 or data[0] != "lang" or data[2] != str(chat_id):
        bot.answer_callback_query(call.id, get_translation(get_chat_language(chat_id), "invalid_callback"))
        log(f"chat_id={chat_id}, user_id={user_id}: Invalid callback for language change")
        return

    # Skip admin check in private chats
    if call.message.chat.type != "private" and not is_admin(bot, chat_id, user_id):
        bot.answer_callback_query(call.id, get_translation(get_chat_language(chat_id), "admin_only"))
        log(f"chat_id={chat_id}, user_id={user_id}: Non-admin attempted to change chat language")
        return

    lang = data[1]
    if lang not in ["ru", "uk", "en"]:
        bot.answer_callback_query(call.id, get_translation(get_chat_language(chat_id), "unsupported_language"))
        log(f"chat_id={chat_id}, user_id={user_id}: Unsupported language {lang}")
        return

    # Set the chat's language
    set_chat_language(chat_id, lang)

    # Delete the message with buttons
    try:
        bot.delete_message(chat_id, call.message.message_id)
        log(f"chat_id={chat_id}, user_id={user_id}: Deleted language selection message")
    except Exception as e:
        log(f"chat_id={chat_id}, user_id={user_id}: Failed to delete message: {e}")

    # Send confirmation message in the selected language
    bot.send_message(chat_id, get_translation(lang, "language_changed"))
    bot.answer_callback_query(call.id)
    log(f"chat_id={chat_id}, user_id={user_id}: Chat language changed to {lang}")

def random_reply(bot, message, processed_media_groups):
    """Handle text and media messages for random sticker replies."""
    chat_id = message.chat.id
    user_id = message.from_user.id

    # Check for media group to prevent duplicate replies
    if hasattr(message, "media_group_id") and message.media_group_id:
        group_id = message.media_group_id
        now = time.time()
        if group_id in processed_media_groups and now - processed_media_groups[group_id] < 60:
            return
        processed_media_groups[group_id] = now

    # Handle text or media messages
    if message.content_type == "text":
        update_user(message.from_user, is_media=False)
        chance = get_reply_chance(chat_id)
        roll = random.random()
        if roll < chance:
            log(f"chat_id={chat_id}: Trigger activated (roll={roll:.3f} < chance={chance})")
            send_random_sticker(bot, chat_id, reply_to_message_id=message.message_id)
        else:
            log(f"chat_id={chat_id}: Trigger not activated (roll={roll:.3f}, chance={chance})")
    else:
        log(f"chat_id={chat_id}: Media message ({message.content_type}), replying 100%")
        update_user(message.from_user, is_media=True)
        send_random_sticker(bot, chat_id, reply_to_message_id=message.message_id)