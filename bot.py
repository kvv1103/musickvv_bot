import asyncio
import random
from aiogram import Bot, Dispatcher, types, F
from aiogram.filters import Command
from config import BOT_TOKEN
from database import (
    init_db, add_track, get_all_tracks,
    delete_track, toggle_favorite,
    get_mode, set_mode
)

bot = Bot(token=BOT_TOKEN)
dp = Dispatcher()


# 🔹 Ініціалізація бази
@dp.startup()
async def on_startup():
    await init_db()
    print("✅ Базу даних ініціалізовано")


# 📥 Додавання нового треку
@dp.message(F.audio)
async def upload_audio(message: types.Message):
    audio = message.audio
    title = audio.title or audio.file_name or "Невідомий трек"
    file_id = audio.file_id

    await add_track(title, file_id)
    await message.answer(f"🎶 Трек **{title}** додано до плейлісту!")


# ⚙️ Команда /mode — вибір режиму
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


# ▶️ /play — відтворення
@dp.message(Command("play"))
async def play_tracks(message: types.Message):
    tracks = await get_all_tracks()
    mode = await get_mode()

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

    await message.answer(f"🎧 Відтворення {len(tracks)} трек(ів):")
    for track_id, title, file_id, fav in tracks:
        fav_mark = "⭐" if fav else ""
        await message.answer_audio(file_id, caption=f"{fav_mark} {title}")
        await asyncio.sleep(1)
    await message.answer("✅ Відтворення завершено.")


# 🎵 /playlist — перегляд усіх треків
@dp.message(Command("playlist"))
async def show_playlist(message: types.Message):
    tracks = await get_all_tracks()
    if not tracks:
        await message.answer("❌ У плейлісті ще немає треків.")
        return

    for track_id, title, file_id, fav in tracks:
        fav_mark = "⭐" if fav else ""
        buttons = [
            types.InlineKeyboardButton(text="🗑 Видалити", callback_data=f"del:{track_id}"),
            types.InlineKeyboardButton(
                text="⭐ Обране" if not fav else "💔 Забрати",
                callback_data=f"fav:{track_id}"
            ),
        ]
        keyboard = types.InlineKeyboardMarkup(inline_keyboard=[buttons])
        await message.answer(f"{fav_mark} {title}", reply_markup=keyboard)


# 🗑 Видалення треку
@dp.callback_query(F.data.startswith("del:"))
async def remove_track(callback: types.CallbackQuery):
    track_id = int(callback.data.split(":")[1])
    await delete_track(track_id)
    await callback.answer("Трек видалено ✅")
    await callback.message.edit_text("🗑 Трек видалено з плейліста.")


# ⭐ Додавання/зняття “Обраного”
@dp.callback_query(F.data.startswith("fav:"))
async def fav_track(callback: types.CallbackQuery):
    track_id = int(callback.data.split(":")[1])
    await toggle_favorite(track_id)
    await callback.answer("Статус оновлено ⭐")
    await callback.message.edit_text("✅ Статус обраного оновлено.")


# 🟢 Запуск
async def main():
    print("🎵 Бот запущено")
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())
