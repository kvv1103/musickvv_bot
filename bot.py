import os
import sqlite3
import random
from telebot import TeleBot, types

# 🔹 Твій токен
API_TOKEN = "ТВОЙ_АПІ_КЛЮЧ"
bot = TeleBot(API_TOKEN)

# 🔹 Підключення до бази даних
os.makedirs("db", exist_ok=True)
conn = sqlite3.connect("db/music.db", check_same_thread=False)
cur = conn.cursor()

# 🔹 Створення таблиць, якщо ще немає
cur.execute("""
CREATE TABLE IF NOT EXISTS tracks (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER,
    username TEXT,
    title TEXT,
    file_id TEXT,
    playlist TEXT
)
""")

cur.execute("""
CREATE TABLE IF NOT EXISTS playlists (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER,
    name TEXT
)
""")

cur.execute("""
CREATE TABLE IF NOT EXISTS user_state (
    user_id INTEGER PRIMARY KEY,
    current_playlist TEXT
)
""")

conn.commit()


# 🔹 Глобальні режими відтворення
play_modes = {
    "sequential": "▶️ Підряд усі",
    "shuffle": "🔀 Випадково",
    "repeat_one": "🔂 Повтор поточного"
}
current_mode = "sequential"


# 🟢 Старт
@bot.message_handler(commands=['start'])
def start(message):
    user_id = message.from_user.id
    bot.send_message(
        message.chat.id,
        "🎧 Привіт! Це музичний бот.\n\n"
        "📂 Ти можеш:\n"
        "• Надіслати трек — щоб додати у поточний плейліст\n"
        "• Створити новий — /createplaylist\n"
        "• Перемкнутись на інший — /chooseplaylist\n"
        "• Подивитись свої плейлісти — /myplaylists\n"
        "• Слухати музику — /play\n"
        "• Змінити режим — /mode"
    )

    # Якщо користувач ще не має активного плейлісту — створюємо стандартний
    cur.execute("SELECT current_playlist FROM user_state WHERE user_id=?", (user_id,))
    row = cur.fetchone()
    if not row:
        cur.execute("INSERT OR REPLACE INTO user_state (user_id, current_playlist) VALUES (?, ?)", (user_id, "default"))
        cur.execute("INSERT OR IGNORE INTO playlists (user_id, name) VALUES (?, ?)", (user_id, "default"))
        conn.commit()


# 🟢 Створення нового плейлісту
@bot.message_handler(commands=['createplaylist'])
def create_playlist(message):
    bot.send_message(message.chat.id, "🎵 Введи назву нового плейлісту:")
    bot.register_next_step_handler(message, save_playlist)


def save_playlist(message):
    name = message.text.strip()
    user_id = message.from_user.id

    cur.execute("INSERT INTO playlists (user_id, name) VALUES (?, ?)", (user_id, name))
    cur.execute("UPDATE user_state SET current_playlist=? WHERE user_id=?", (name, user_id))
    conn.commit()

    bot.send_message(message.chat.id, f"✅ Плейліст '{name}' створено і обрано активним.")


# 🟢 Перегляд своїх плейлістів
@bot.message_handler(commands=['myplaylists'])
def my_playlists(message):
    user_id = message.from_user.id
    cur.execute("SELECT name FROM playlists WHERE user_id=?", (user_id,))
    playlists = [p[0] for p in cur.fetchall()]

    if not playlists:
        bot.send_message(message.chat.id, "❌ У тебе ще немає плейлістів.")
        return

    cur.execute("SELECT current_playlist FROM user_state WHERE user_id=?", (user_id,))
    current = cur.fetchone()[0]

    text = "🎶 Твої плейлісти:\n" + "\n".join(
        [f"• {p} {'(активний)' if p == current else ''}" for p in playlists]
    )
    bot.send_message(message.chat.id, text)


# 🟢 Вибір плейлісту
@bot.message_handler(commands=['chooseplaylist'])
def choose_playlist(message):
    user_id = message.from_user.id
    cur.execute("SELECT name FROM playlists WHERE user_id=?", (user_id,))
    playlists = cur.fetchall()

    if not playlists:
        bot.send_message(message.chat.id, "❌ У тебе ще немає плейлістів. Створи один командою /createplaylist.")
        return

    markup = types.InlineKeyboardMarkup()
    for (name,) in playlists:
        markup.add(types.InlineKeyboardButton(name, callback_data=f"choose_{name}"))
    bot.send_message(message.chat.id, "🎧 Обери плейліст:", reply_markup=markup)


@bot.callback_query_handler(func=lambda call: call.data.startswith("choose_"))
def set_playlist(call):
    name = call.data.replace("choose_", "")
    user_id = call.from_user.id
    cur.execute("UPDATE user_state SET current_playlist=? WHERE user_id=?", (name, user_id))
    conn.commit()
    bot.edit_message_text(f"✅ Активний плейліст змінено на: {name}", call.message.chat.id, call.message.message_id)


# 🟢 Завантаження треку
@bot.message_handler(content_types=['audio'])
def handle_audio(message):
    user_id = message.from_user.id
    username = message.from_user.username or "Без_імені"
    title = message.audio.title or message.audio.file_name or "Без назви"
    file_id = message.audio.file_id

    # Додаємо у поточний плейліст
    cur.execute("SELECT current_playlist FROM user_state WHERE user_id=?", (user_id,))
    current_playlist = cur.fetchone()[0]

    cur.execute("INSERT INTO tracks (user_id, username, title, file_id, playlist) VALUES (?, ?, ?, ?, ?)",
                (user_id, username, title, file_id, current_playlist))
    conn.commit()

    bot.send_message(message.chat.id, f"✅ Трек '{title}' додано у плейліст '{current_playlist}'.")


# 🟢 Режим відтворення
@bot.message_handler(commands=['mode'])
def change_mode(message):
    markup = types.InlineKeyboardMarkup()
    for key, name in play_modes.items():
        markup.add(types.InlineKeyboardButton(name, callback_data=f"mode_{key}"))
    bot.send_message(message.chat.id, "🎛 Обери режим відтворення:", reply_markup=markup)


@bot.callback_query_handler(func=lambda call: call.data.startswith("mode_"))
def set_mode(call):
    global current_mode
    current_mode = call.data.replace("mode_", "")
    bot.edit_message_text(f"✅ Режим змінено на: {play_modes[current_mode]}", call.message.chat.id, call.message.message_id)


# 🟢 Відтворення
@bot.message_handler(commands=['play'])
def play_playlist(message):
    user_id = message.from_user.id
    cur.execute("SELECT current_playlist FROM user_state WHERE user_id=?", (user_id,))
    playlist = cur.fetchone()[0]

    cur.execute("SELECT title, file_id FROM tracks WHERE user_id=? AND playlist=?", (user_id, playlist))
    tracks = cur.fetchall()

    if not tracks:
        bot.send_message(message.chat.id, f"❌ У плейлісті '{playlist}' немає треків.")
        return

    bot.send_message(message.chat.id, f"🎶 Відтворюємо плейліст: {playlist}")

    if current_mode == "shuffle":
        random.shuffle(tracks)
    elif current_mode == "repeat_one":
        tracks = [tracks[0]]

    for title, file_id in tracks:
        bot.send_audio(message.chat.id, file_id, caption=f"🎵 {title}")
        if current_mode == "repeat_one":
            break


bot.polling(none_stop=True)
