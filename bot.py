import os
import sqlite3
import random
from telebot import TeleBot, types

# 🔹 Твій токен
API_TOKEN = "ТВОЙ_АПІ_КЛЮЧ"
bot = TeleBot(API_TOKEN)

# 🔹 Підключення до постійної бази (НЕ створюється наново при оновленні коду)
os.makedirs("db", exist_ok=True)
conn = sqlite3.connect("db/music.db", check_same_thread=False)
cur = conn.cursor()

# 🔹 Створення таблиць, якщо їх ще немає
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
conn.commit()


# 🔹 Створення або вибір плейлісту
@bot.message_handler(commands=['start'])
def start(message):
    bot.send_message(message.chat.id,
        "🎵 Привіт! Надішли мені музичний файл, щоб додати його у свій плейліст.\n"
        "Команди:\n"
        "/mytracks – твій список треків\n"
        "/play – відтворити плейліст\n"
        "/mode – змінити режим відтворення"
    )


# 🔹 Завантаження треку
@bot.message_handler(content_types=['audio'])
def handle_audio(message):
    user_id = message.from_user.id
    username = message.from_user.username or "Без_імені"
    title = message.audio.title or message.audio.file_name or "Без назви"
    file_id = message.audio.file_id

    cur.execute("INSERT INTO tracks (user_id, username, title, file_id, playlist) VALUES (?, ?, ?, ?, ?)",
                (user_id, username, title, file_id, "default"))
    conn.commit()

    bot.send_message(message.chat.id, f"✅ Трек '{title}' додано у твій плейліст.")


# 🔹 Перегляд своїх треків
@bot.message_handler(commands=['mytracks'])
def list_tracks(message):
    user_id = message.from_user.id
    cur.execute("SELECT title FROM tracks WHERE user_id = ?", (user_id,))
    tracks = cur.fetchall()

    if not tracks:
        bot.send_message(message.chat.id, "❌ У тебе ще немає треків.")
    else:
        text = "🎧 Твої треки:\n" + "\n".join([f"• {t[0]}" for t in tracks])
        bot.send_message(message.chat.id, text)


# 🔹 Глобальна змінна для режиму відтворення
play_modes = {
    "sequential": "▶️ Підряд усі",
    "shuffle": "🔀 Випадково",
    "repeat_one": "🔂 Повтор поточного"
}
current_mode = "sequential"


# 🔹 Зміна режиму
@bot.message_handler(commands=['mode'])
def change_mode(message):
    global current_mode
    markup = types.InlineKeyboardMarkup()
    for key, name in play_modes.items():
        markup.add(types.InlineKeyboardButton(name, callback_data=f"mode_{key}"))
    bot.send_message(message.chat.id, "🎛 Обери режим відтворення:", reply_markup=markup)


@bot.callback_query_handler(func=lambda call: call.data.startswith("mode_"))
def set_mode(call):
    global current_mode
    current_mode = call.data.replace("mode_", "")
    bot.edit_message_text(f"✅ Режим змінено на: {play_modes[current_mode]}", call.message.chat.id, call.message.message_id)


# 🔹 Відтворення
@bot.message_handler(commands=['play'])
def play_playlist(message):
    user_id = message.from_user.id
    cur.execute("SELECT title, file_id FROM tracks WHERE user_id = ?", (user_id,))
    tracks = cur.fetchall()

    if not tracks:
        bot.send_message(message.chat.id, "❌ Немає треків для відтворення.")
        return

    if current_mode == "shuffle":
        random.shuffle(tracks)
    elif current_mode == "repeat_one":
        tracks = [tracks[0]]

    for title, file_id in tracks:
        bot.send_audio(message.chat.id, file_id, caption=f"🎵 {title}")
        if current_mode == "repeat_one":
            break


bot.polling(none_stop=True)
