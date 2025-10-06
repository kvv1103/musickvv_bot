import aiosqlite

async def init_db():
    async with aiosqlite.connect("data/music.db") as db:
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
                FOREIGN KEY (playlist_id) REFERENCES playlists (id)
            )
        """)
        await db.commit()
