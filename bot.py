import telebot
import os
import random
import time
import datetime
from dotenv import load_dotenv
from db_operations import init_db, get_pack_limit, get_reply_chance, set_reply_chance, count_packs, count_stickers, send_random_sticker, update_user
from message_handlers import handle_sticker, random_pack, stats, set_reply_chance_command, get_reply_chance_command, ban_pack, unban_pack, list_packs, clear_packs, set_pack_limit, get_pack_limit_command, help_command, top_users, random_reply, set_language_command, handle_language_callback
from translations import get_translation, set_user_language, get_user_language

load_dotenv()  # Load environment variables from .env
TOKEN = os.getenv("TOKEN")
bot = telebot.TeleBot(TOKEN)

# Store processed media groups to prevent duplicate replies
processed_media_groups = {}  # media_group_id: timestamp

# Initialize the database
init_db()

# Register message handlers
bot.message_handler(content_types=["sticker"])(lambda message: handle_sticker(bot, message))
bot.message_handler(commands=["random_pack"])(lambda message: random_pack(bot, message))
bot.message_handler(commands=["stats"])(lambda message: stats(bot, message))
bot.message_handler(commands=["set_reply_chance"])(lambda message: set_reply_chance_command(bot, message))
bot.message_handler(commands=["get_reply_chance"])(lambda message: get_reply_chance_command(bot, message))
bot.message_handler(commands=["ban_pack"])(lambda message: ban_pack(bot, message))
bot.message_handler(commands=["unban_pack"])(lambda message: unban_pack(bot, message))
bot.message_handler(commands=["list_packs"])(lambda message: list_packs(bot, message))
bot.message_handler(commands=["clear_packs"])(lambda message: clear_packs(bot, message))
bot.message_handler(commands=["set_pack_limit"])(lambda message: set_pack_limit(bot, message))
bot.message_handler(commands=["get_pack_limit"])(lambda message: get_pack_limit_command(bot, message))
bot.message_handler(commands=["help"])(lambda message: help_command(bot, message))
bot.message_handler(commands=["top_users"])(lambda message: top_users(bot, message))
bot.message_handler(commands=["set_language"])(lambda message: set_language_command(bot, message))
bot.callback_query_handler(func=lambda call: True)(lambda call: handle_language_callback(bot, call))
bot.message_handler(content_types=["text", "photo", "video", "animation", "video_note"])(lambda message: random_reply(bot, message, processed_media_groups))

def log(msg):
    """Log messages with timestamp."""
    print(f"{datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')} - {msg}")

log("Bot started...")
bot.polling(none_stop=True)