import asyncio
import random
import aiosqlite
from aiogram import Bot, Dispatcher, types
from aiogram.filters import Command
from config import BOT_TOKEN

bot = Bot(token=BOT_TOKEN)
dp = Dispatcher()

DB_PATH = "db/music.db"

# ================== Ініціалізація бази ==================
async def init_db():
    import os
    os.makedirs("db", exist_ok=True)
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute("""
        CREATE TABLE IF NOT EXISTS tracks (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER,
            username TEXT,
            title TEXT,
            file_id TEXT,
            playlist TEXT
        )
        """)
        await db.execute("""
        CREATE TABLE IF NOT EXISTS playlists (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER,
            name TEXT
        )
        """)
        await db.execute("""
        CREATE TABLE IF NOT EXISTS user_state (
            user_id INTEGER PRIMARY KEY,
            current_playlist TEXT
        )
        """)
        await db.commit()

# ================== Режими відтворення ==================
play_modes = {
    "sequential": "▶️ Підряд усі",
    "shuffle": "🔀 Випадково",
    "repeat_one": "🔂 Повтор поточного"
}
user_modes = {}  # зберігає режим для кожного користувача

# ================== Старт ==================
@dp.message(Command("start"))
async def start_cmd(message: types.Message):
    user_id = message.from_user.id
    async with aiosqlite.connect(DB_PATH) as db:
        # Створення стандартного плейліста, якщо новий користувач
        await db.execute("INSERT OR IGNORE INTO playlists (user_id, name) VALUES (?, ?)", (user_id, "default"))
        await db.execute("INSERT OR IGNORE INTO user_state (user_id, current_playlist) VALUES (?, ?)", (user_id, "default"))
        await db.commit()
    await message.answer(
        "🎧 Привіт! Музичний бот на aiogram.\n\n"
        "📂 Команди:\n"
        "/createplaylist — створити новий плейліст\n"
        "/chooseplaylist — вибір активного плейліста\n"
        "/myplaylists — переглянути свої плейлісти\n"
        "/play — відтворення поточного плейліста\n"
        "/mode — змінити режим відтворення\n"
        "Надішли аудіо — щоб додати його у поточний плейліст."
    )

# ================== Створення плейліста ==================
@dp.message(Command("createplaylist"))
async def create_playlist(message: types.Message):
    await message.answer("Введи назву нового плейліста:")
    await dp.register_message_handler(save_playlist, state=None, content_types=types.ContentTypes.TEXT, lambda message: True)

async def save_playlist(message: types.Message):
    name = message.text.strip()
    user_id = message.from_user.id
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute("INSERT INTO playlists (user_id, name) VALUES (?, ?)", (user_id, name))
        await db.execute("UPDATE user_state SET current_playlist=? WHERE user_id=?", (name, user_id))
        await db.commit()
    await message.answer(f"✅ Плейліст '{name}' створено і обрано активним.")

# ================== Перегляд плейлістів ==================
@dp.message(Command("myplaylists"))
async def my_playlists(message: types.Message):
    user_id = message.from_user.id
    async with aiosqlite.connect(DB_PATH) as db:
        cursor = await db.execute("SELECT name FROM playlists WHERE user_id=?", (user_id,))
        playlists = [row[0] for row in await cursor.fetchall()]
        cursor = await db.execute("SELECT current_playlist FROM user_state WHERE user_id=?", (user_id,))
        current = (await cursor.fetchone())[0]

    if not playlists:
        await message.answer("❌ У тебе ще немає плейлістів.")
        return
    text = "🎶 Твої плейлісти:\n" + "\n".join([f"• {p} {'(активний)' if p==current else ''}" for p in playlists])
    await message.answer(text)

# ================== Вибір активного плейліста ==================
@dp.message(Command("chooseplaylist"))
async def choose_playlist(message: types.Message):
    user_id = message.from_user.id
    async with aiosqlite.connect(DB_PATH) as db:
        cursor = await db.execute("SELECT name FROM playlists WHERE user_id=?", (user_id,))
        playlists = [row[0] for row in await cursor.fetchall()]
    if not playlists:
        await message.answer("❌ У тебе немає плейлістів.")
        return
    markup = types.InlineKeyboardMarkup()
    for name in playlists:
        markup.add(types.InlineKeyboardButton(name, callback_data=f"choose_{name}"))
    await message.answer("🎧 Обери плейліст:", reply_markup=markup)

@dp.callback_query(lambda call: call.data.startswith("choose_"))
async def set_playlist(call: types.CallbackQuery):
    name = call.data.replace("choose_", "")
    user_id = call.from_user.id
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute("UPDATE user_state SET current_playlist=? WHERE user_id=?", (name, user_id))
        await db.commit()
    await call.message.edit_text(f"✅ Активний плейліст змінено на: {name}")

# ================== Завантаження треку ==================
@dp.message(lambda message: message.audio is not None)
async def handle_audio(message: types.Message):
    user_id = message.from_user.id
    username = message.from_user.username or "Без_імені"
    title = message.audio.title or message.audio.file_name or "Без назви"
    file_id = message.audio.file_id
    async with aiosqlite.connect(DB_PATH) as db:
        cursor = await db.execute("SELECT current_playlist FROM user_state WHERE user_id=?", (user_id,))
        current_playlist = (await cursor.fetchone())[0]
        await db.execute("INSERT INTO tracks (user_id, username, title, file_id, playlist) VALUES (?, ?, ?, ?, ?)",
                         (user_id, username, title, file_id, current_playlist))
        await db.commit()
    await message.answer(f"✅ Трек '{title}' додано у плейліст '{current_playlist}'.")

# ================== Зміна режиму ==================
@dp.message(Command("mode"))
async def change_mode(message: types.Message):
    markup = types.InlineKeyboardMarkup()
    for key, name in play_modes.items():
        markup.add(types.InlineKeyboardButton(name, callback_data=f"mode_{key}"))
    await message.answer("🎛 Обери режим відтворення:", reply_markup=markup)

@dp.callback_query(lambda call: call.data.startswith("mode_"))
async def set_mode(call: types.CallbackQuery):
    user_modes[call.from_user.id] = call.data.replace("mode_", "")
    await call.message.edit_text(f"✅ Режим змінено на: {play_modes[user_modes[call.from_user.id]]}")

# ================== Відтворення плейліста ==================
@dp.message(Command("play"))
async def play_playlist(message: types.Message):
    user_id = message.from_user.id
    async with aiosqlite.connect(DB_PATH) as db:
        cursor = await db.execute("SELECT current_playlist FROM user_state WHERE user_id=?", (user_id,))
        playlist = (await cursor.fetchone())[0]
        cursor = await db.execute("SELECT title, file_id FROM tracks WHERE user_id=? AND playlist=?", (user_id, playlist))
        tracks = await cursor.fetchall()

    if not tracks:
        await message.answer(f"❌ У плейлісті '{playlist}' немає треків.")
        return

    await message.answer(f"🎶 Відтворюємо плейліст: {playlist}")

    mode = user_modes.get(user_id, "sequential")
    if mode == "shuffle":
        random.shuffle(tracks)
    elif mode == "repeat_one":
        tracks = [tracks[0]]

    for title, file_id in tracks:
        await bot.send_audio(message.chat.id, file_id, caption=f"🎵 {title}")
        if mode == "repeat_one":
            break

# ================== Головна функція ==================
async def main():
    await init_db()
    print("🎵 Музичний бот запущено...")
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())
