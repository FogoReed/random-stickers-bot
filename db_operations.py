import sqlite3
import datetime
import random
import telebot

# Global database connection
conn = sqlite3.connect("packs.db", check_same_thread=False)

def log(msg):
    """Log messages with timestamp."""
    print(f"{datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')} - {msg}")

def init_db():
    """Initialize database tables and indexes."""
    with conn:
        cur = conn.cursor()
        # Create packs table
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
        # Create chat_settings table
        cur.execute("""
        CREATE TABLE IF NOT EXISTS chat_settings (
            chat_id INTEGER PRIMARY KEY,
            pack_limit INTEGER DEFAULT 50,
            reply_chance REAL DEFAULT 0.05
        )
        """)
        # Create users table
        cur.execute("""
        CREATE TABLE IF NOT EXISTS users (
            user_id INTEGER PRIMARY KEY,
            first_name TEXT,
            last_name TEXT,
            username TEXT,
            last_active TIMESTAMP,
            sticker_calls INTEGER DEFAULT 0,
            media_calls INTEGER DEFAULT 0,
            language TEXT DEFAULT 'en'
        )
        """)
        conn.commit()

        # Add indexes for faster queries
        cur.execute("CREATE INDEX IF NOT EXISTS idx_packs_chat_id ON packs(chat_id)")
        cur.execute("CREATE INDEX IF NOT EXISTS idx_users_last_active ON users(last_active)")
        cur.execute("CREATE INDEX IF NOT EXISTS idx_users_username ON users(username)")
        conn.commit()

        # Check and add reply_chance column if missing
        cur.execute("PRAGMA table_info(chat_settings)")
        columns = [col[1] for col in cur.fetchall()]
        if "reply_chance" not in columns:
            cur.execute("ALTER TABLE chat_settings ADD COLUMN reply_chance REAL DEFAULT 0.05")
            conn.commit()
            log("Column reply_chance added to chat_settings")

        # Check and add language column if missing
        cur.execute("PRAGMA table_info(users)")
        columns = [col[1] for col in cur.fetchall()]
        if "language" not in columns:
            cur.execute("ALTER TABLE users ADD COLUMN language TEXT DEFAULT 'en'")
            conn.commit()
            log("Column language added to users")

def get_pack_limit(chat_id):
    """Get the pack limit for a chat."""
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
    """Get the reply chance for a chat."""
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
    """Set the reply chance for a chat."""
    with conn:
        cur = conn.cursor()
        cur.execute("INSERT OR REPLACE INTO chat_settings (chat_id, pack_limit, reply_chance) "
                    "VALUES (?, COALESCE((SELECT pack_limit FROM chat_settings WHERE chat_id=?), 50), ?)",
                    (chat_id, chat_id, chance))

def count_packs(chat_id):
    """Count the number of allowed packs in a chat."""
    with conn:
        cur = conn.cursor()
        cur.execute("SELECT COUNT(*) FROM packs WHERE chat_id=? AND status='allowed'", (chat_id,))
        row = cur.fetchone()
        return row[0] if row else 0

def count_stickers(chat_id):
    """Count the total number of stickers in allowed packs for a chat."""
    with conn:
        cur = conn.cursor()
        cur.execute("SELECT SUM(sticker_count) FROM packs WHERE chat_id=? AND status='allowed'", (chat_id,))
        row = cur.fetchone()
        return row[0] if row and row[0] else 0

def send_random_sticker(bot, chat_id, reply_to_message_id=None):
    """Send a random sticker from allowed packs."""
    with conn:
        cur = conn.cursor()
        cur.execute("SELECT set_name FROM packs WHERE chat_id=? AND status='allowed' ORDER BY RANDOM() LIMIT 1",
                    (chat_id,))
        row = cur.fetchone()

    if not row:
        log(f"chat_id={chat_id}: No saved packs for sending sticker")
        return False
    pack_name = row[0]

    try:
        sticker_set = bot.get_sticker_set(pack_name)
        sticker = random.choice(sticker_set.stickers)
        bot.send_sticker(chat_id, sticker.file_id, reply_to_message_id=reply_to_message_id)
        log(f"chat_id={chat_id}: Sent sticker from pack '{pack_name}'")
        return True
    except Exception as e:
        log(f"chat_id={chat_id}: Error sending sticker from pack '{pack_name}': {e}")
        return False

def update_user(user, is_media=False):
    """Save or update user information."""
    with conn:
        cur = conn.cursor()
        cur.execute("""
        INSERT INTO users (user_id, first_name, last_name, username, last_active, sticker_calls, media_calls, language)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        ON CONFLICT(user_id) DO UPDATE SET
            first_name=excluded.first_name,
            last_name=excluded.last_name,
            username=excluded.username,
            last_active=excluded.last_active,
            sticker_calls=users.sticker_calls + excluded.sticker_calls,
            media_calls=users.media_calls + excluded.media_calls
        """, (
            user.id,
            user.first_name,
            user.last_name,
            user.username,
            datetime.datetime.now(),
            0 if is_media else 1,
            1 if is_media else 0,
            "en"  # Default language
        ))
        conn.commit()