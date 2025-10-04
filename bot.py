import asyncio
import os
from aiogram import Bot, Dispatcher, types
from aiogram.filters import Command
from aiogram.types import FSInputFile
from config import BOT_TOKEN, MUSIC_DIR

bot = Bot(token=BOT_TOKEN)
dp = Dispatcher()

# ======= Команди =========

@dp.message(Command("start"))
async def start_command(message: types.Message):
    await message.answer(
        "🎶 Привіт! Я музичний бот.\n\n"
        "Я можу надсилати треки з папки, створювати плейлісти та обране.\n"
        "Введи /help щоб побачити команди."
    )

@dp.message(Command("help"))
async def help_command(message: types.Message):
    await message.answer(
        "🎧 Доступні команди:\n"
        "/start — почати роботу\n"
        "/help — допомога\n"
        "/music — надіслати тестову пісню"
    )

@dp.message(Command("music"))
async def send_music(message: types.Message):
    # Беремо перший mp3 з папки music
    files = [f for f in os.listdir(MUSIC_DIR) if f.endswith(".mp3")]
    if not files:
        await message.answer("😔 У папці 'music/' немає файлів.")
        return

    file_path = os.path.join(MUSIC_DIR, files[0])
    audio = FSInputFile(file_path)
    name = os.path.splitext(files[0])[0]
    await message.answer_audio(audio, caption=f"🎵 {name}")

# ======= Запуск =========

async def main():
    print("Бот запущено 🚀")
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())
