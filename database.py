import aiosqlite
from config import DB_NAME


# 📦 Ініціалізація бази даних
async def init_db():
    async with aiosqlite.connect(DB_NAME) as db:
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
                favorite INTEGER DEFAULT 0,
                FOREIGN KEY (playlist_id) REFERENCES playlists(id)
            )
        """)

        await db.execute("""
            CREATE TABLE IF NOT EXISTS settings (
                id INTEGER PRIMARY KEY CHECK (id = 1),
                mode TEXT DEFAULT 'sequential'
            )
        """)

        # Додаємо базові записи, якщо ще немає
        await db.execute("""
            INSERT OR IGNORE INTO playlists (id, user_id, name)
            VALUES (1, 0, 'Головний плейліст')
        """)
        await db.execute("""
            INSERT OR IGNORE INTO settings (id, mode)
            VALUES (1, 'sequential')
        """)
        await db.commit()


# ➕ Додати трек
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
            "SELECT id, title, file_id, favorite FROM tracks WHERE playlist_id = 1"
        ) as cursor:
            return await cursor.fetchall()


# 🎵 Отримати улюблені треки
async def get_favorite_tracks():
    async with aiosqlite.connect(DB_NAME) as db:
        async with db.execute(
            "SELECT id, title, file_id FROM tracks WHERE favorite = 1"
        ) as cursor:
            return await cursor.fetchall()


# 🗑 Видалити трек
async def delete_track(track_id: int):
    async with aiosqlite.connect(DB_NAME) as db:
        await db.execute("DELETE FROM tracks WHERE id = ?", (track_id,))
        await db.commit()


# ⭐ Перемикач “Обране”
async def toggle_favorite(track_id: int):
    async with aiosqlite.connect(DB_NAME) as db:
        async with db.execute(
            "SELECT favorite FROM tracks WHERE id = ?", (track_id,)
        ) as cursor:
            row = await cursor.fetchone()
            if not row:
                return
            new_state = 0 if row[0] else 1
            await db.execute(
                "UPDATE tracks SET favorite = ? WHERE id = ?", (new_state, track_id)
            )
            await db.commit()


# ⚙️ Режими
async def get_mode():
    async with aiosqlite.connect(DB_NAME) as db:
        async with db.execute("SELECT mode FROM settings WHERE id = 1") as cursor:
            row = await cursor.fetchone()
            return row[0] if row else "sequential"


async def set_mode(mode: str):
    async with aiosqlite.connect(DB_NAME) as db:
        await db.execute("UPDATE settings SET mode = ? WHERE id = 1", (mode,))
        await db.commit()
