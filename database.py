import aiosqlite
from config import DB_NAME

# 📦 Ініціалізація бази даних
async def init_db():
    async with aiosqlite.connect(DB_NAME) as db:
        # Створюємо таблиці, якщо їх ще немає
        await db.execute("""
            CREATE TABLE IF NOT EXISTS playlists (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER,
                name TEXT
            )
        """)

        await db.execute("""
            CREATE TABLE IF NOT EXISTS tracks (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                playlist_id INTEGER,
                title TEXT,
                file_id TEXT,
                FOREIGN KEY (playlist_id) REFERENCES playlists(id)
            )
        """)

        # Таблиця для режиму відтворення
        await db.execute("""
            CREATE TABLE IF NOT EXISTS settings (
                id INTEGER PRIMARY KEY CHECK (id = 1),
                mode TEXT DEFAULT 'sequential'
            )
        """)

        # Створюємо записи за замовчуванням
        await db.execute("""
            INSERT OR IGNORE INTO playlists (id, user_id, name)
            VALUES (1, 0, 'Головний плейліст')
        """)
        await db.execute("""
            INSERT OR IGNORE INTO settings (id, mode)
            VALUES (1, 'sequential')
        """)
        await db.commit()


# ➕ Додати трек до бази
async def add_track(title: str, file_id: str):
    async with aiosqlite.connect(DB_NAME) as db:
        await db.execute(
            "INSERT INTO tracks (playlist_id, title, file_id) VALUES (1, ?, ?)",
            (title, file_id)
        )
        await db.commit()


# 🎵 Отримати всі треки
async def get_all_tracks():
    async with aiosqlite.connect(DB_NAME) as db:
        async with db.execute(
            "SELECT id, title, file_id FROM tracks WHERE playlist_id = 1"
        ) as cursor:
            return await cursor.fetchall()


# ⚙️ Отримати поточний режим
async def get_mode():
    async with aiosqlite.connect(DB_NAME) as db:
        async with db.execute("SELECT mode FROM settings WHERE id = 1") as cursor:
            row = await cursor.fetchone()
            return row[0] if row else "sequential"


# ⚙️ Змінити режим
async def set_mode(mode: str):
    async with aiosqlite.connect(DB_NAME) as db:
        await db.execute("UPDATE settings SET mode = ? WHERE id = 1", (mode,))
        await db.commit()
