import asyncio
import random
from aiogram import Bot, Dispatcher, types, F
from aiogram.filters import Command
from config import BOT_TOKEN
from database import init_db, add_track, get_all_tracks, get_mode, set_mode

bot = Bot(token=BOT_TOKEN)
dp = Dispatcher()


# 🔹 Під час запуску — ініціалізація бази
@dp.startup()
async def on_startup():
    await init_db()
    print("✅ Базу даних ініціалізовано")


# 📥 Завантаження нового треку
@dp.message(F.audio)
async def upload_audio(message: types.Message):
    audio = message.audio
    title = audio.title or audio.file_name or "Невідомий трек"
    file_id = audio.file_id

    await add_track(title, file_id)
    await message.answer(f"🎶 Трек **{title}** додано до плейлісту!")


# ⚙️ Команда /mode — змінити режим відтворення
@dp.message(Command("mode"))
async def change_mode(message: types.Message):
    buttons = [
        [types.InlineKeyboardButton(text="🔁 Підряд", callback_data="mode:sequential")],
        [types.InlineKeyboardButton(text="🔀 Випадково", callback_data="mode:shuffle")],
        [types.InlineKeyboardButton(text="🔂 Один трек", callback_data="mode:single")],
    ]
    keyboard = types.InlineKeyboardMarkup(inline_keyboard=buttons)
    mode = await get_mode()
    await message.answer(f"Поточний режим: **{mode}**", reply_markup=keyboard)


# 🔘 Обробка вибору режиму
@dp.callback_query(F.data.startswith("mode:"))
async def select_mode(callback: types.CallbackQuery):
    mode = callback.data.split(":")[1]
    await set_mode(mode)
    await callback.answer(f"Режим змінено на: {mode}")
    await callback.message.edit_text(f"✅ Режим встановлено: {mode}")


# ▶️ Команда /play — відтворення з урахуванням режиму
@dp.message(Command("play"))
async def play_tracks(message: types.Message):
    tracks = await get_all_tracks()
    mode = await get_mode()
    print(f"[DEBUG] Режим: {mode}, треків: {len(tracks)}")

    if not tracks:
        await message.answer("❌ У плейлісті ще немає треків.")
        return

    # Режим "випадково"
    if mode == "shuffle":
        random.shuffle(tracks)

    # Режим "один трек"
    if mode == "single":
        track = random.choice(tracks)
        await message.answer_audio(track[2], caption=f"🔂 {track[1]}")
        return

    # Режим "підряд"
    await message.answer(f"🎧 Відтворення {len(tracks)} трек(ів):")
    for track_id, title, file_id in tracks:
        try:
            await message.answer_audio(file_id, caption=f"🎵 {title}")
            await asyncio.sleep(1)
        except Exception as e:
            print(f"[ERROR] Не вдалося відтворити {title}: {e}")

    await message.answer("✅ Відтворення завершено.")


# 🟢 Запуск бота
async def main():
    print("🎵 Бот запущено")
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())
