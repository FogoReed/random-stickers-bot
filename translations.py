from db_operations import conn, get_chat_language, set_chat_language

# Translation dictionary for Russian, Ukrainian, and English
TRANSLATIONS = {
    "ru": {
        "no_packs": "В этом чате ещё нет сохранённых стикерпаков.",
        "stats": "Сохранено паков: {count}\nСуммарное количество стикеров: {stickers_total}\nЛимит паков: {limit}",
        "set_reply_chance_usage": "Использование: /set_reply_chance <число в %>",
        "invalid_chance": "Введите число от 0 до 100.",
        "reply_chance_set": "Шанс ответа стикером установлен на {chance}%",
        "get_reply_chance": "Текущий шанс ответа стикером: {chance:.2f}%",
        "ban_pack_usage": "Использование: /ban_pack <название_пака>",
        "pack_not_found": "Пак {pack_name} не найден в базе.",
        "pack_banned": "Пак {pack_name} добавлен в ЧС 🚫",
        "unban_pack_usage": "Использование: /unban_pack <название_пака>",
        "pack_unbanned": "Пак {pack_name} убран из ЧС ✅",
        "pack_list": "Список паков:",
        "packs_cleared": "База паков для этого чата очищена.",
        "set_pack_limit_usage": "Использование: /set_pack_limit <число>",
        "invalid_limit": "Пожалуйста, введите положительное число.",
        "pack_limit_set": "Лимит паков для этого чата установлен на {limit}.",
        "get_pack_limit": "Текущий лимит паков для этого чата: {limit}.",
        "help": (
            "Доступные команды:\n"
            "/random_pack — получить случайный стикер из сохранённых паков\n"
            "/stats — статистика по стикерпаков в чате\n"
            "/top_users — вывести рейтинг пользователей с наибольшим количеством отправленных стикеров и реакций на медиа\n"
            "/ban_pack <название_пака> — добавить пак в чёрный список (только для админов)\n"
            "/unban_pack <название_пака> — убрать пак из чёрного списка (только для админов)\n"
            "/list_packs — список всех паков и их статус\n"
            "/clear_packs — очистить базу паков чата (только для админов)\n"
            "/set_pack_limit <число> — установить лимит паков (только для админов)\n"
            "/get_pack_limit — узнать текущий лимит паков\n"
            "/set_reply_chance <число> — установить шанс ответа стикером (%) (только для админов)\n"
            "/get_reply_chance — узнать текущий шанс ответа стикером\n"
            "/set_language — выбрать язык чата через кнопки\n"
            "/help — показать это сообщение"
        ),
        "no_users": "Пока нет данных по пользователям.",
        "top_users": "🏆 Топ пользователей:",
        "set_language_usage": "Используйте кнопки для выбора языка чата.",
        "language_changed": "Язык чата изменён.",
        "select_language": "Выберите язык чата:",
        "lang_ru": "Русский",
        "lang_uk": "Українська",
        "lang_en": "English",
        "invalid_callback": "Ошибка: неверный запрос или вы не можете изменить язык чата.",
        "unsupported_language": "Ошибка: неподдерживаемый язык.",
        "stickers_label": "стикеры",
        "media_label": "медиа",
        "admin_only": "Только администраторы могут выполнять эту команду."
    },
    "uk": {
        "no_packs": "У цьому чаті ще немає збережених стікерпаків.",
        "stats": "Збережено паків: {count}\nЗагальна кількість стікерів: {stickers_total}\nЛіміт паків: {limit}",
        "set_reply_chance_usage": "Використання: /set_reply_chance <число в %>",
        "invalid_chance": "Введіть число від 0 до 100.",
        "reply_chance_set": "Шанс відповіді стікером встановлено на {chance}%",
        "get_reply_chance": "Поточний шанс відповіді стікером: {chance:.2f}%",
        "ban_pack_usage": "Використання: /ban_pack <назва_паку>",
        "pack_not_found": "Пак {pack_name} не знайдено в базі.",
        "pack_banned": "Пак {pack_name} додано до чорного списку 🚫",
        "unban_pack_usage": "Використання: /unban_pack <назва_паку>",
        "pack_unbanned": "Пак {pack_name} видалено з чорного списку ✅",
        "pack_list": "Список паків:",
        "packs_cleared": "База паків для цього чату очищена.",
        "set_pack_limit_usage": "Використання: /set_pack_limit <число>",
        "invalid_limit": "Будь ласка, введіть позитивне число.",
        "pack_limit_set": "Ліміт паків для цього чату встановлено на {limit}.",
        "get_pack_limit": "Поточний ліміт паків для цього чату: {limit}.",
        "help": (
            "Доступні команди:\n"
            "/random_pack — отримати випадковий стікер зі збережених паків\n"
            "/stats — статистика стікерпаків у чаті\n"
            "/top_users — вивести рейтинг користувачів з найбільшою кількістю надісланих стікерів та реакцій на медіа\n"
            "/ban_pack <назва_паку> — додати пак до чорного списку (тільки для адмінів)\n"
            "/unban_pack <назва_паку> — видалити пак з чорного списку (тільки для адмінів)\n"
            "/list_packs — список усіх паків та їх статус\n"
            "/clear_packs — очистити базу паків чату (тільки для адмінів)\n"
            "/set_pack_limit <число> — встановити ліміт паків (тільки для адмінів)\n"
            "/get_pack_limit — дізнатися поточний ліміт паків\n"
            "/set_reply_chance <число> — встановити шанс відповіді стікером (%) (тільки для адмінів)\n"
            "/get_reply_chance — дізнатися поточний шанс відповіді стікером\n"
            "/set_language — обрати мову чату через кнопки\n"
            "/help — показати це повідомлення"
        ),
        "no_users": "Поки немає даних про користувачів.",
        "top_users": "🏆 Топ користувачів:",
        "set_language_usage": "Використовуйте кнопки для вибору мови чату.",
        "language_changed": "Мову чату змінено.",
        "select_language": "Оберіть мову чату:",
        "lang_ru": "Русский",
        "lang_uk": "Українська",
        "lang_en": "English",
        "invalid_callback": "Помилка: невірний запит або ви не можете змінити мову чату.",
        "unsupported_language": "Помилка: непідтримувана мова.",
        "stickers_label": "стікері",
        "media_label": "медіа",
        "admin_only": "Тільки адміністратори можуть виконувати цю команду."
    },
    "en": {
        "no_packs": "No sticker packs saved in this chat yet.",
        "stats": "Saved packs: {count}\nTotal stickers: {stickers_total}\nPack limit: {limit}",
        "set_reply_chance_usage": "Usage: /set_reply_chance <number in %>",
        "invalid_chance": "Enter a number between 0 and 100.",
        "reply_chance_set": "Sticker reply chance set to {chance}%",
        "get_reply_chance": "Current sticker reply chance: {chance:.2f}%",
        "ban_pack_usage": "Usage: /ban_pack <pack_name>",
        "pack_not_found": "Pack {pack_name} not found in the database.",
        "pack_banned": "Pack {pack_name} added to blacklist 🚫",
        "unban_pack_usage": "Usage: /unban_pack <pack_name>",
        "pack_unbanned": "Pack {pack_name} removed from blacklist ✅",
        "pack_list": "List of packs:",
        "packs_cleared": "Pack database for this chat cleared.",
        "set_pack_limit_usage": "Usage: /set_pack_limit <number>",
        "invalid_limit": "Please enter a positive number.",
        "pack_limit_set": "Pack limit for this chat set to {limit}.",
        "get_pack_limit": "Current pack limit for this chat: {limit}.",
        "help": (
            "Available commands:\n"
            "/random_pack — get a random sticker from saved packs\n"
            "/stats — show statistics for sticker packs in the chat\n"
            "/top_users — display ranking of users with the most sent stickers and media reactions\n"
            "/ban_pack <pack_name> — add a pack to the blacklist (admin only)\n"
            "/unban_pack <pack_name> — remove a pack from the blacklist (admin only)\n"
            "/list_packs — list all packs and their status\n"
            "/clear_packs — clear the pack database for this chat (admin only)\n"
            "/set_pack_limit <number> — set the pack limit (admin only)\n"
            "/get_pack_limit — check the current pack limit\n"
            "/set_reply_chance <number> — set the sticker reply chance (%) (admin only)\n"
            "/get_reply_chance — check the current sticker reply chance\n"
            "/set_language — select the chat's language via buttons\n"
            "/help — show this message"
        ),
        "no_users": "No user data available yet.",
        "top_users": "🏆 Top users:",
        "set_language_usage": "Use the buttons to select the chat's language.",
        "language_changed": "Chat language changed.",
        "select_language": "Select the chat's language:",
        "lang_ru": "Русский",
        "lang_uk": "Українська",
        "lang_en": "English",
        "invalid_callback": "Error: invalid request or you cannot change the chat's language.",
        "unsupported_language": "Error: unsupported language.",
        "stickers_label": "stickers",
        "media_label": "media",
        "admin_only": "Only administrators can execute this command."
    }
}

def get_translation(lang, key):
    """Get translation for a given key and language."""
    return TRANSLATIONS.get(lang, TRANSLATIONS["en"]).get(key, TRANSLATIONS["en"][key])

def set_user_language(user_id, lang):
    """Deprecated: Use set_chat_language instead."""
    pass

def get_user_language(user_id, chat_id):
    """Get the language for a chat, ignoring user_id."""
    return get_chat_language(chat_id)