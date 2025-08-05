import telebot
import sqlite3
import random
import datetime
import time
import os
from dotenv import load_dotenv

load_dotenv()  # загружаем переменные из .env

TOKEN = os.getenv("TOKEN")
bot = telebot.TeleBot(TOKEN)

processed_media_groups = {}  # media_group_id: timestamp

# Глобальное соединение
conn = sqlite3.connect("packs.db", check_same_thread=False)

def log(msg):
    print(f"{datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')} - {msg}")

# Создание таблиц
with conn:
    cur = conn.cursor()
    cur.execute("""
    CREATE TABLE IF NOT EXISTS packs (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        chat_id INTEGER,
        set_name TEXT,
        sticker_count INTEGER DEFAULT 0,
        status TEXT DEFAULT 'allowed',
        UNIQUE(chat_id, set_name)
    )
    """)
    cur.execute("""
    CREATE TABLE IF NOT EXISTS chat_settings (
        chat_id INTEGER PRIMARY KEY,
        pack_limit INTEGER DEFAULT 50,
        reply_chance REAL DEFAULT 0.05
    )
    """)
    conn.commit()

    # Проверка колонки reply_chance
    cur.execute("PRAGMA table_info(chat_settings)")
    columns = [col[1] for col in cur.fetchall()]
    if "reply_chance" not in columns:
        cur.execute("ALTER TABLE chat_settings ADD COLUMN reply_chance REAL DEFAULT 0.05")
        conn.commit()
        log("Колонка reply_chance добавлена в chat_settings")


def get_pack_limit(chat_id):
    with conn:
        cur = conn.cursor()
        cur.execute("SELECT pack_limit FROM chat_settings WHERE chat_id=?", (chat_id,))
        row = cur.fetchone()
        if row:
            return row[0]
        cur.execute("INSERT OR IGNORE INTO chat_settings (chat_id, pack_limit, reply_chance) VALUES (?, ?, ?)",
                    (chat_id, 50, 0.05))
        return 50


def get_reply_chance(chat_id):
    with conn:
        cur = conn.cursor()
        cur.execute("SELECT reply_chance FROM chat_settings WHERE chat_id=?", (chat_id,))
        row = cur.fetchone()
        if row:
            return row[0]
        cur.execute("INSERT OR IGNORE INTO chat_settings (chat_id, pack_limit, reply_chance) VALUES (?, ?, ?)",
                    (chat_id, 50, 0.05))
        return 0.05


def set_reply_chance(chat_id, chance):
    with conn:
        cur = conn.cursor()
        cur.execute("INSERT OR REPLACE INTO chat_settings (chat_id, pack_limit, reply_chance) "
                    "VALUES (?, COALESCE((SELECT pack_limit FROM chat_settings WHERE chat_id=?), 50), ?)",
                    (chat_id, chat_id, chance))


def count_packs(chat_id):
    with conn:
        cur = conn.cursor()
        cur.execute("SELECT COUNT(*) FROM packs WHERE chat_id=? AND status='allowed'", (chat_id,))
        row = cur.fetchone()
        return row[0] if row else 0


def count_stickers(chat_id):
    with conn:
        cur = conn.cursor()
        cur.execute("SELECT SUM(sticker_count) FROM packs WHERE chat_id=? AND status='allowed'", (chat_id,))
        row = cur.fetchone()
        return row[0] if row and row[0] else 0


def send_random_sticker(chat_id, reply_to_message_id=None):
    with conn:
        cur = conn.cursor()
        cur.execute("SELECT set_name FROM packs WHERE chat_id=? AND status='allowed' ORDER BY RANDOM() LIMIT 1",
                    (chat_id,))
        row = cur.fetchone()

    if not row:
        log(f"chat_id={chat_id}: Нет сохранённых паков для отправки стикера")
        return False
    pack_name = row[0]

    try:
        sticker_set = bot.get_sticker_set(pack_name)
        sticker = random.choice(sticker_set.stickers)
        bot.send_sticker(chat_id, sticker.file_id, reply_to_message_id=reply_to_message_id)
        log(f"chat_id={chat_id}: Отправлен стикер из пака '{pack_name}'")
        return True
    except Exception as e:
        log(f"chat_id={chat_id}: Ошибка при отправке стикера из пака '{pack_name}': {e}")
        return False


@bot.message_handler(content_types=["sticker"])
def handle_sticker(message):
    chat_id = message.chat.id
    pack_name = message.sticker.set_name

    if not pack_name:
        log(f"chat_id={chat_id}: Стикер без set_name, игнорируется")
        return

    with conn:
        cur = conn.cursor()
        cur.execute("SELECT status FROM packs WHERE chat_id=? AND set_name=?", (chat_id, pack_name))
        row = cur.fetchone()

    if row and row[0] == "banned":
        log(f"chat_id={chat_id}: Пак '{pack_name}' в ЧС, игнорируется")
        return

    limit = get_pack_limit(chat_id)
    current_count = count_packs(chat_id)
    if current_count >= limit:
        log(f"chat_id={chat_id}: Лимит паков {limit} достигнут, новый пак '{pack_name}' не добавлен")
        return

    try:
        sticker_set = bot.get_sticker_set(pack_name)
        sticker_count = len(sticker_set.stickers)
    except Exception as e:
        log(f"chat_id={chat_id}: Не удалось получить количество стикеров для '{pack_name}': {e}")
        sticker_count = 0

    try:
        with conn:
            cur = conn.cursor()
            cur.execute("INSERT INTO packs (chat_id, set_name, sticker_count) VALUES (?, ?, ?)",
                        (chat_id, pack_name, sticker_count))
        log(f"chat_id={chat_id}: Добавлен новый пак '{pack_name}' ({sticker_count} стикеров)")
    except sqlite3.IntegrityError:
        log(f"chat_id={chat_id}: Пак '{pack_name}' уже в базе, пропуск")


@bot.message_handler(commands=["random_pack"])
def random_pack(message):
    chat_id = message.chat.id
    log(f"chat_id={chat_id}: Запрошен случайный стикер (/random_pack)")
    if not send_random_sticker(chat_id, reply_to_message_id=message.message_id):
        bot.reply_to(message, "В этом чате ещё нет сохранённых стикерпаков.")


@bot.message_handler(commands=["stats"])
def stats(message):
    chat_id = message.chat.id
    limit = get_pack_limit(chat_id)
    count = count_packs(chat_id)
    stickers_total = count_stickers(chat_id)
    log(f"chat_id={chat_id}: Запрошена статистика (/stats)")
    bot.reply_to(message, f"Сохранено паков: {count}\nСуммарное количество стикеров: {stickers_total}\nЛимит паков: {limit}")


@bot.message_handler(commands=["set_reply_chance"])
def set_reply_chance_command(message):
    chat_id = message.chat.id
    args = message.text.split()
    if len(args) < 2:
        bot.reply_to(message, "Использование: /set_reply_chance <число в %>")
        return
    try:
        new_chance = float(args[1]) / 100
        if not (0 <= new_chance <= 1):
            raise ValueError()
    except ValueError:
        bot.reply_to(message, "Введите число от 0 до 100.")
        return

    set_reply_chance(chat_id, new_chance)
    bot.reply_to(message, f"Шанс ответа стикером установлен на {args[1]}%")
    log(f"chat_id={chat_id}: Шанс ответа стикером изменён на {args[1]}%")


@bot.message_handler(commands=["get_reply_chance"])
def get_reply_chance_command(message):
    chat_id = message.chat.id
    chance = get_reply_chance(chat_id) * 100
    bot.reply_to(message, f"Текущий шанс ответа стикером: {chance:.2f}%")
    log(f"chat_id={chat_id}: Запрошен шанс ответа ({chance:.2f}%)")


@bot.message_handler(commands=["ban_pack"])
def ban_pack(message):
    chat_id = message.chat.id
    args = message.text.split()
    if len(args) < 2:
        bot.reply_to(message, "Использование: /ban_pack <название_пака>")
        return
    pack_name = args[1]

    with conn:
        cur = conn.cursor()
        cur.execute("UPDATE packs SET status='banned' WHERE chat_id=? AND set_name=?", (chat_id, pack_name))
        if cur.rowcount == 0:
            bot.reply_to(message, f"Пак {pack_name} не найден в базе.")
            log(f"chat_id={chat_id}: Попытка забанить несуществующий пак '{pack_name}'")
        else:
            bot.reply_to(message, f"Пак {pack_name} добавлен в ЧС 🚫")
            log(f"chat_id={chat_id}: Пак '{pack_name}' добавлен в ЧС")


@bot.message_handler(commands=["unban_pack"])
def unban_pack(message):
    chat_id = message.chat.id
    args = message.text.split()
    if len(args) < 2:
        bot.reply_to(message, "Использование: /unban_pack <название_пака>")
        return
    pack_name = args[1]

    with conn:
        cur = conn.cursor()
        cur.execute("UPDATE packs SET status='allowed' WHERE chat_id=? AND set_name=?", (chat_id, pack_name))
        if cur.rowcount == 0:
            bot.reply_to(message, f"Пак {pack_name} не найден в базе.")
            log(f"chat_id={chat_id}: Попытка разбанить несуществующий пак '{pack_name}'")
        else:
            bot.reply_to(message, f"Пак {pack_name} убран из ЧС ✅")
            log(f"chat_id={chat_id}: Пак '{pack_name}' убран из ЧС")


@bot.message_handler(commands=["list_packs"])
def list_packs(message):
    chat_id = message.chat.id
    with conn:
        cur = conn.cursor()
        cur.execute("SELECT set_name, status FROM packs WHERE chat_id=?", (chat_id,))
        rows = cur.fetchall()

    if not rows:
        bot.reply_to(message, "В базе нет сохранённых паков.")
        log(f"chat_id={chat_id}: Запрошен список паков, но база пуста")
        return

    text = "Список паков:\n"
    for set_name, status in rows:
        emoji = "✅" if status == "allowed" else "🚫"
        text += f"{emoji} {set_name}\n"
    bot.reply_to(message, text)
    log(f"chat_id={chat_id}: Отправлен список паков (кол-во: {len(rows)})")


@bot.message_handler(commands=["clear_packs"])
def clear_packs(message):
    chat_id = message.chat.id
    with conn:
        cur = conn.cursor()
        cur.execute("DELETE FROM packs WHERE chat_id=?", (chat_id,))
    bot.reply_to(message, "База паков для этого чата очищена.")
    log(f"chat_id={chat_id}: Очищена база паков")


@bot.message_handler(commands=["set_pack_limit"])
def set_pack_limit(message):
    chat_id = message.chat.id
    args = message.text.split()
    if len(args) < 2:
        bot.reply_to(message, "Использование: /set_pack_limit <число>")
        return
    try:
        new_limit = int(args[1])
        if new_limit <= 0:
            raise ValueError()
    except ValueError:
        bot.reply_to(message, "Пожалуйста, введите положительное число.")
        return

    with conn:
        cur = conn.cursor()
        cur.execute("INSERT OR REPLACE INTO chat_settings (chat_id, pack_limit, reply_chance) "
                    "VALUES (?, ?, COALESCE((SELECT reply_chance FROM chat_settings WHERE chat_id=?), 0.05))",
                    (chat_id, new_limit, chat_id))
    bot.reply_to(message, f"Лимит паков для этого чата установлен на {new_limit}.")
    log(f"chat_id={chat_id}: Лимит паков установлен на {new_limit}")


@bot.message_handler(commands=["get_pack_limit"])
def get_pack_limit_command(message):
    chat_id = message.chat.id
    limit = get_pack_limit(chat_id)
    bot.reply_to(message, f"Текущий лимит паков для этого чата: {limit}.")
    log(f"chat_id={chat_id}: Запрошен лимит паков ({limit})")


@bot.message_handler(commands=["help"])
def help_command(message):
    help_text = (
        "Доступные команды:\n"
        "/random_pack — получить случайный стикер из сохранённых паков\n"
        "/stats — статистика по стикерпаков в чате\n"
        "/ban_pack <название_пака> — добавить пак в чёрный список (только для админов)\n"
        "/unban_pack <название_пака> — убрать пак из чёрного списка (только для админов)\n"
        "/list_packs — список всех паков и их статус (только для админов)\n"
        "/clear_packs — очистить базу паков чата (только для админов)\n"
        "/set_pack_limit <число> — установить лимит паков (только для админов)\n"
        "/get_pack_limit — узнать текущий лимит паков\n"
        "/set_reply_chance <число> — установить шанс ответа стикером (%)\n"
        "/get_reply_chance — узнать текущий шанс ответа стикером\n"
        "/help — показать это сообщение"
    )
    bot.reply_to(message, help_text)
    log(f"chat_id={message.chat.id}: Запрошена помощь (/help)")


@bot.message_handler(content_types=["text", "photo", "video", "animation", "video_note"])
def random_reply(message):
    chat_id = message.chat.id

    # === Проверка на альбом (media group) ===
    if hasattr(message, "media_group_id") and message.media_group_id:
        group_id = message.media_group_id
        now = time.time()
        # Если уже отвечали на этот альбом в последние 60 секунд → пропустить
        if group_id in processed_media_groups and now - processed_media_groups[group_id] < 60:
            return
        # Сохраняем отметку о реакции
        processed_media_groups[group_id] = now

    # === Логика реакции ===
    if message.content_type == "text":
        chance = get_reply_chance(chat_id)
        roll = random.random()
        if roll < chance:
            log(f"chat_id={chat_id}: Триггер сработал (roll={roll:.3f} < chance={chance})")
            send_random_sticker(chat_id, reply_to_message_id=message.message_id)
        else:
            log(f"chat_id={chat_id}: Триггер не сработал (roll={roll:.3f}, chance={chance})")
    else:
        # для фото/видео/гифок/кружочков → 100%
        log(f"chat_id={chat_id}: Медиа сообщение ({message.content_type}), реагируем 100%")
        send_random_sticker(chat_id, reply_to_message_id=message.message_id)
        

log("Бот запущен...")
bot.polling(none_stop=True)
