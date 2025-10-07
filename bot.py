import asyncio
import random
import aiosqlite
from aiogram import Bot, Dispatcher, types
from aiogram.filters import Command
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from config import BOT_TOKEN
from database import init_db

bot = Bot(token=BOT_TOKEN)
dp = Dispatcher()

# Збереження режиму відтворення для кожного користувача
play_modes = {}  # {user_id: "all"|"random"|"repeat"}
playing_tasks = {}  # для режиму repeat


@dp.message(Command("start"))
async def start_cmd(message: types.Message):
    text = (
        "🎧 Привіт! Я музичний бот.\n\n"
        "Команди:\n"
        "/upload – завантажити трек\n"
        "/play – відтворити треки\n"
        "/mode – змінити режим відтворення\n"
        "/stop – зупинити повтор\n\n"
        "Режими:\n🔁 Підряд усі\n🔀 Випадково\n🔂 Один трек"
    )
    await message.answer(text)


@dp.message(Command("upload"))
async def upload_cmd(message: types.Message):
    await message.answer("📤 Надішли мені аудіофайл, щоб я додав його до плейлісту.")


@dp.message(lambda msg: msg.audio)
async def handle_audio(message: types.Message):
    file_id = message.audio.file_id
    title = message.audio.title or "Без назви"

    async with aiosqlite.connect("music.db") as db:
        await db.execute(
            "INSERT INTO tracks (playlist_id, title, file_id) VALUES (1, ?, ?)",
            (title, file_id)
        )
        await db.commit()

    await message.answer(f"✅ Трек **{title}** додано до плейлісту!")


@dp.message(Command("mode"))
async def mode_cmd(message: types.Message):
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🔁 Підряд", callback_data="mode_all")],
        [InlineKeyboardButton(text="🔀 Випадково", callback_data="mode_random")],
        [InlineKeyboardButton(text="🔂 Один трек", callback_data="mode_repeat")]
    ])
    await message.answer("🎚 Оберіть режим відтворення:", reply_markup=keyboard)


@dp.callback_query(lambda c: c.data and c.data.startswith("mode_"))
async def set_mode(callback: types.CallbackQuery):
    user_id = callback.from_user.id
    mode = callback.data.split("_")[1]
    play_modes[user_id] = mode

    mode_text = {
        "all": "🔁 Підряд",
        "random": "🔀 Випадково",
        "repeat": "🔂 Один трек"
    }[mode]

    await callback.message.edit_text(f"✅ Режим відтворення змінено на {mode_text}")
    await callback.answer()


@dp.message(Command("play"))
async def play_cmd(message: types.Message):
    user_id = message.from_user.id
    mode = play_modes.get(user_id, "all")

    async with aiosqlite.connect("music.db") as db:
        async with db.execute("SELECT title, file_id FROM tracks") as cursor:
            tracks = await cursor.fetchall()

    if not tracks:
        await message.answer("😢 Немає треків для відтворення.")
        return

    # Зупиняємо попередній повтор
    if user_id in playing_tasks:
        playing_tasks[user_id].cancel()
        del playing_tasks[user_id]

    # 🔁 Підряд
    if mode == "all":
        await message.answer("▶️ Відтворення всіх треків підряд...")
        for title, file_id in tracks:
            await message.answer_audio(audio=file_id, caption=f"🎵 {title}")
            await asyncio.sleep(1)

    # 🔀 Випадково
    elif mode == "random":
        await message.answer("🎲 Відтворення у випадковому порядку...")
        random.shuffle(tracks)
        for title, file_id in tracks:
            await message.answer_audio(audio=file_id, caption=f"🎶 {title}")
            await asyncio.sleep(1)

    # 🔂 Один трек (повтор)
    elif mode == "repeat":
        await message.answer("🔂 Повтор поточного треку... Використай /stop щоб зупинити.")
        title, file_id = tracks[0]

        async def repeat_track():
            try:
                while True:
                    await message.answer_audio(audio=file_id, caption=f"🎧 {title} (повтор)")
                    await asyncio.sleep(5)
            except asyncio.CancelledError:
                pass

        task = asyncio.create_task(repeat_track())
        playing_tasks[user_id] = task


@dp.message(Command("stop"))
async def stop_cmd(message: types.Message):
    user_id = message.from_user.id
    task = playing_tasks.get(user_id)
    if task:
        task.cancel()
        del playing_tasks[user_id]
        await message.answer("⏹️ Відтворення зупинено.")
    else:
        await message.answer("❌ Немає активного відтворення.")


async def main():
    await init_db()
    print("✅ Бот запущено")
    await dp.start_polling(bot)


if __name__ == "__main__":
    asyncio.run(main())
