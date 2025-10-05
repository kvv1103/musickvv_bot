import asyncio
from aiogram import Bot, Dispatcher, types
from aiogram.filters import Command
from aiogram.types import Message
from config import BOT_TOKEN
from database import init_db, DB_NAME
import aiosqlite

bot = Bot(token=BOT_TOKEN)
dp = Dispatcher()

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
        "🎶 Привіт! Надішли мені аудіо, і я додам його до твоїх треків.\n"
        "Команди:\n"
        "/mytracks — показати твої треки\n"
        "/newplaylist <назва> — створити плейліст\n"
        "/myplaylists — показати плейлісти"
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

async def main():
    print("Запуск 24/7 музичного бота 🎵")
    await init_db()
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())
