import asyncio
import random
from aiogram import Bot, Dispatcher, types, F
from aiogram.filters import Command
from config import BOT_TOKEN
from database import (
    init_db, add_track, get_all_tracks, get_favorite_tracks,
    delete_track, toggle_favorite, get_mode, set_mode, clear_all
)

bot = Bot(token=BOT_TOKEN)
dp = Dispatcher()

# 👋 Команда /start — головне меню з кнопками
@dp.message(Command("start"))
async def start_command(message: types.Message):
    keyboard = types.ReplyKeyboardMarkup(
        resize_keyboard=True,
        keyboard=[
            [
                types.KeyboardButton(text="▶️ Грати"),
                types.KeyboardButton(text="📂 Плейліст"),
            ],
            [
                types.KeyboardButton(text="💖 Улюблене"),
                types.KeyboardButton(text="⚙️ Режим"),
            ],
            [
                types.KeyboardButton(text="🧹 Очистити базу"),
                types.KeyboardButton(text="🧩 Debug"),
            ]
        ]
    )

    text = (
        "🎵 <b>Привіт!</b>\n"
        "Я музичний бот 🎧\n\n"
        "📀 Мої можливості:\n"
        "• Надішли аудіо — я додам його у плейліст\n"
        "• Натисни кнопку в  меню, щоб слухати або керувати треками 🎶"
    )

    await message.answer(text, reply_markup=keyboard, parse_mode="HTML")

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


# ▶️ /play — відтворення треків
@dp.message(Command("play"))
async def play_tracks(message: types.Message):
    tracks = await get_all_tracks()
    mode = await get_mode()

    if not tracks:
        await message.answer("❌ У плейлісті ще немає треків.")
        return

    # Випадковий режим
    if mode == "shuffle":
        random.shuffle(tracks)

    # Один трек
    if mode == "single":
        track = random.choice(tracks)
        await message.answer_audio(track[2], caption=f"🔂 {track[1]}")
        return

    # Підряд
    await message.answer(f"🎧 Відтворення {len(tracks)} трек(ів):")
    for track_id, title, file_id, fav in tracks:
        fav_mark = "⭐" if fav else ""
        await message.answer_audio(file_id, caption=f"{fav_mark} {title}")
        await asyncio.sleep(1)
    await message.answer("✅ Відтворення завершено.")


# 🎵 /playlist — усі треки
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


# 💖 /favorites — улюблені треки
@dp.message(Command("favorites"))
async def show_favorites(message: types.Message):
    favorites = await get_favorite_tracks()
    if not favorites:
        await message.answer("❌ У тебе ще немає улюблених треків.")
        return

    await message.answer(f"💖 Улюблені треки ({len(favorites)}):")
    for track_id, title, file_id in favorites:
        buttons = [
            types.InlineKeyboardButton(text="💔 Забрати", callback_data=f"fav:{track_id}"),
            types.InlineKeyboardButton(text="▶️ Грати", callback_data=f"playone:{track_id}")
        ]
        keyboard = types.InlineKeyboardMarkup(inline_keyboard=[buttons])
        await message.answer(f"⭐ {title}", reply_markup=keyboard)


# 🗑 Видалення одного треку
@dp.callback_query(F.data.startswith("del:"))
async def remove_track(callback: types.CallbackQuery):
    track_id = int(callback.data.split(":")[1])
    await delete_track(track_id)
    await callback.answer("Трек видалено ✅")
    await callback.message.edit_text("🗑 Трек видалено з плейліста.")


# ⭐ Улюблені / зняття
@dp.callback_query(F.data.startswith("fav:"))
async def fav_track(callback: types.CallbackQuery):
    track_id = int(callback.data.split(":")[1])
    await toggle_favorite(track_id)
    await callback.answer("⭐ Статус оновлено")
    await callback.message.edit_text("✅ Статус обраного оновлено.")


# ▶️ Відтворення одного улюбленого треку
@dp.callback_query(F.data.startswith("playone:"))
async def play_one_fav(callback: types.CallbackQuery):
    track_id = int(callback.data.split(":")[1])
    tracks = await get_favorite_tracks()
    for tid, title, file_id in tracks:
        if tid == track_id:
            await callback.message.answer_audio(file_id, caption=f"🎵 {title}")
            await callback.answer("▶️ Відтворюю трек")
            return
    await callback.answer("⚠️ Трек не знайдено.")


# 🧹 /clear — очищення бази
@dp.message(Command("clear"))
async def confirm_clear(message: types.Message):
    buttons = [
        [
            types.InlineKeyboardButton(text="✅ Так, очистити", callback_data="clear:yes"),
            types.InlineKeyboardButton(text="❌ Ні, скасувати", callback_data="clear:no")
        ]
    ]
    keyboard = types.InlineKeyboardMarkup(inline_keyboard=buttons)
    await message.answer("⚠️ Ви впевнені, що хочете **очистити базу**?", reply_markup=keyboard)


@dp.callback_query(F.data.startswith("clear:"))
async def handle_clear(callback: types.CallbackQuery):
    if callback.data == "clear:yes":
        await clear_all()
        await callback.answer("✅ Очищено")
        await callback.message.edit_text("🧹 Усі треки та налаштування видалено.")
    else:
        await callback.answer("❌ Скасовано")
        await callback.message.edit_text("Дія скасована.")

# 🧩 /debug — показати вміст бази
@dp.message(Command("debug"))
async def debug_db(message: types.Message):
    tracks = await get_all_tracks()
    if not tracks:
        await message.answer("❌ У базі немає треків.")
        return

    text = "📦 <b>Вміст бази:</b>\n\n"
    for t in tracks:
        track_id, title, file_id, fav = t
        fav_mark = "⭐" if fav else " "
        # скорочуємо file_id для зручності
        short_id = file_id[:10] + "..." if file_id else "❌ (порожній)"
        text += f"ID: {track_id} | {fav_mark} {title}\n🆔 {short_id}\n\n"

    await message.answer(text, parse_mode="HTML")

# ▶️ Кнопка “Грати”
@dp.message(F.text == "▶️ Грати")
async def button_play(message: types.Message):
    await play_tracks(message)

# 📂 Кнопка “Плейліст”
@dp.message(F.text == "📂 Плейліст")
async def button_playlist(message: types.Message):
    await show_playlist(message)

# 💖 Кнопка “Улюблене”
@dp.message(F.text == "💖 Улюблене")
async def button_fav(message: types.Message):
    await show_favorites(message)

# ⚙️ Кнопка “Режим”
@dp.message(F.text == "⚙️ Режим")
async def button_mode(message: types.Message):
    await change_mode(message)

# 🧹 Кнопка “Очистити базу”
@dp.message(F.text == "🧹 Очистити базу")
async def button_clear(message: types.Message):
    await confirm_clear(message)

# 🧩 Кнопка “Debug”
@dp.message(F.text == "🧩 Debug")
async def button_debug(message: types.Message):
    await debug_db(message)


# 🟢 Запуск
async def main():
    print("🎵 Бот запущено")
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())
