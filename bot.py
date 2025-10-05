import asyncio
import random
from aiogram import Bot, Dispatcher, types
from aiogram.filters import Command
from aiogram.types import Message
import aiosqlite
from config import BOT_TOKEN
from database import init_db, DB_NAME

bot = Bot(token=BOT_TOKEN)
dp = Dispatcher()

# Пам’ять для режимів відтворення
user_play_modes = {}

# ==================== Команди ====================

@dp.message(Command("start"))
async def start_cmd(message: Message):
    async with aiosqlite.connect(DB_NAME) as db:
        await db.execute(
            "INSERT OR IGNORE INTO users (user_id, username) VALUES (?, ?)",
            (message.from_user.id, message.from_user.username)
        )
        await db.commit()
    await message.answer(
        "🎶 Привіт! Я музичний бот.\n\n"
        "📀 Надішли мені аудіо — я збережу його у твоїй бібліотеці.\n"
        "🎧 Команди:\n"
        "/mytracks — показати твої треки\n"
        "/newplaylist <назва> — створити плейліст\n"
        "/myplaylists — показати плейлісти\n"
        "/addtoplaylist <id_плейліста> <id_треку> — додати трек до плейліста\n\n"
        "Режими відтворення:\n"
        "/play <id> — звичайне відтворення\n"
        "/shuffle <id> — випадкове відтворення\n"
        "/loop <id_треку> — повтор одного треку\n"
        "/stop — зупинити повтор"
    )

# ================================================

@dp.message(Command("mytracks"))
async def show_my_tracks(message: Message):
    async with aiosqlite.connect(DB_NAME) as db:
        cursor = await db.execute(
            "SELECT id, title FROM tracks WHERE user_id = ?",
            (message.from_user.id,)
        )
        rows = await cursor.fetchall()
    if not rows:
        await message.answer("У тебе ще немає треків 🎵")
        return
    text = "\n".join([f"{tid}. {title}" for tid, title in rows])
    await message.answer(f"🎧 Твої треки:\n{text}")

# ================================================

@dp.message(Command("newplaylist"))
async def new_playlist(message: Message):
    args = message.text.split(maxsplit=1)
    if len(args) < 2:
        await message.answer("Вкажи назву плейліста: `/newplaylist Моя музика`")
        return
    name = args[1]
    async with aiosqlite.connect(DB_NAME) as db:
        await db.execute(
            "INSERT INTO playlists (user_id, name) VALUES (?, ?)",
            (message.from_user.id, name)
        )
        await db.commit()
    await message.answer(f"✅ Плейліст '{name}' створено!")

# ================================================

@dp.message(Command("myplaylists"))
async def show_playlists(message: Message):
    async with aiosqlite.connect(DB_NAME) as db:
        cursor = await db.execute(
            "SELECT id, name FROM playlists WHERE user_id = ?",
            (message.from_user.id,)
        )
        playlists = await cursor.fetchall()
    if not playlists:
        await message.answer("У тебе ще немає плейлістів 🎶")
        return
    text = "\n".join([f"{pid}. {name}" for pid, name in playlists])
    await message.answer(f"📂 Твої плейлісти:\n{text}")

# ================================================

@dp.message(Command("addtoplaylist"))
async def add_to_playlist(message: Message):
    args = message.text.split()
    if len(args) < 3:
        await message.answer("Вкажи: `/addtoplaylist <id_плейліста> <id_треку>`")
        return
    playlist_id, track_id = args[1], args[2]
    async with aiosqlite.connect(DB_NAME) as db:
        await db.execute(
            "INSERT INTO playlist_tracks (playlist_id, track_id) VALUES (?, ?)",
            (playlist_id, track_id)
        )
        await db.commit()
    await message.answer("✅ Трек додано до плейліста!")

# ================================================

@dp.message(lambda msg: msg.audio is not None)
async def save_audio(message: Message):
    file_id = message.audio.file_id
    title = message.audio.title or message.audio.file_name or "Без назви"
    async with aiosqlite.connect(DB_NAME) as db:
        await db.execute(
            "INSERT INTO tracks (user_id, file_id, title) VALUES (?, ?, ?)",
            (message.from_user.id, file_id, title)
        )
        await db.commit()
    await message.answer(f"✅ Трек '{title}' збережено!")

# ================================================
# 🎧 Відтворення треків з плейліста
# ================================================

@dp.message(Command("play"))
async def play_playlist(message: types.Message):
    args = message.text.split(maxsplit=1)
    if len(args) < 2:
        await message.answer("Вкажи ID плейліста: `/play 1`")
        return
    playlist_id = args[1]

    async with aiosqlite.connect(DB_NAME) as db:
        cursor = await db.execute("""
            SELECT tracks.file_id, tracks.title
            FROM playlist_tracks
            JOIN tracks ON playlist_tracks.track_id = tracks.id
            WHERE playlist_tracks.playlist_id = ?
        """, (playlist_id,))
        tracks = await cursor.fetchall()

    if not tracks:
        await message.answer("❌ У цьому плейлісті немає треків.")
        return

    user_play_modes[message.from_user.id] = "normal"
    await message.answer("▶️ Відтворення підряд...")

    for file_id, title in tracks:
        await message.answer_audio(audio=file_id, caption=title)

# ================================================

@dp.message(Command("shuffle"))
async def shuffle_playlist(message: types.Message):
    args = message.text.split(maxsplit=1)
    if len(args) < 2:
        await message.answer("Вкажи ID плейліста: `/shuffle 1`")
        return
    playlist_id = args[1]

    async with aiosqlite.connect(DB_NAME) as db:
        cursor = await db.execute("""
            SELECT tracks.file_id, tracks.title
            FROM playlist_tracks
            JOIN tracks ON playlist_tracks.track_id = tracks.id
            WHERE playlist_tracks.playlist_id = ?
        """, (playlist_id,))
        tracks = await cursor.fetchall()

    if not tracks:
        await message.answer("❌ У цьому плейлісті немає треків.")
        return

    random.shuffle(tracks)
    user_play_modes[message.from_user.id] = "shuffle"
    await message.answer("🔀 Випадкове відтворення...")

    for file_id, title in tracks:
        await message.answer_audio(audio=file_id, caption=title)

# ================================================

@dp.message(Command("loop"))
async def loop_track(message: types.Message):
    args = message.text.split(maxsplit=1)
    if len(args) < 2:
        await message.answer("Вкажи ID треку: `/loop 3`")
        return
    track_id = args[1]

    async with aiosqlite.connect(DB_NAME) as db:
        cursor = await db.execute("SELECT file_id, title FROM tracks WHERE id = ?", (track_id,))
        track = await cursor.fetchone()

    if not track:
        await message.answer("❌ Трек не знайдено.")
        return

    file_id, title = track
    user_play_modes[message.from_user.id] = "loop"
    await message.answer(f"🔁 Повторюю трек '{title}'. Напиши `/stop`, щоб зупинити.")

    while user_play_modes.get(message.from_user.id) == "loop":
        await message.answer_audio(audio=file_id, caption=title)
        await asyncio.sleep(5)  # затримка між повторами

# ================================================

@dp.message(Command("stop"))
async def stop_loop(message: types.Message):
    user_play_modes[message.from_user.id] = "stopped"
    await message.answer("⏹️ Відтворення зупинено.")

# ================================================

async def main():
    print("🎵 Запуск музичного бота...")
    await init_db()
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())
