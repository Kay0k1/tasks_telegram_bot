import aiosqlite
from typing import Optional, List, Tuple


class Database:
    def __init__(self, path: str = "bot.db"):
        self.path = path
        self.conn: Optional[aiosqlite.Connection] = None

    async def connect(self):
        self.conn = await aiosqlite.connect(self.path)
        await self.conn.execute("PRAGMA foreign_keys = ON")
        await self.init_db()

    async def init_db(self):
        await self.conn.executescript(
            """
            CREATE TABLE IF NOT EXISTS workers (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT UNIQUE NOT NULL
            );

            CREATE TABLE IF NOT EXISTS tasks (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                title TEXT NOT NULL,
                type TEXT,
                worker_id INTEGER,
                channel_message_id INTEGER,
                channel_id INTEGER,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY(worker_id) REFERENCES workers(id)
            );
            """
        )
        await self.conn.commit()

    async def add_worker(self, name: str) -> int:
        await self.conn.execute(
            "INSERT OR IGNORE INTO workers(name) VALUES(?)",
            (name,)
        )
        await self.conn.commit()
        row = await self.conn.execute_fetchone(
            "SELECT id FROM workers WHERE name=?",
            (name,),
        )
        return row[0]

    async def add_task(
        self,
        title: str,
        task_type: Optional[str] = None,
        worker_name: Optional[str] = None,
        message_id: Optional[int] = None,
        chat_id: Optional[int] = None,
    ) -> int:
        worker_id = None
        if worker_name:
            worker_id = await self.add_worker(worker_name)
        cursor = await self.conn.execute(
            "INSERT INTO tasks(title, type, worker_id, channel_message_id, channel_id) VALUES (?, ?, ?, ?, ?)",
            (title, task_type, worker_id, message_id, chat_id),
        )
        await self.conn.commit()
        return cursor.lastrowid

    async def assign_task(self, task_id: int, worker_name: str, task_type: str):
        worker_id = await self.add_worker(worker_name)
        await self.conn.execute(
            "UPDATE tasks SET worker_id=?, type=? WHERE id=?",
            (worker_id, task_type, task_id),
        )
        await self.conn.commit()

    async def get_unassigned_tasks(self) -> List[Tuple]:
        cursor = await self.conn.execute(
            "SELECT id, title FROM tasks WHERE worker_id IS NULL ORDER BY id"
        )
        return await cursor.fetchall()

    async def get_tasks(
        self,
        task_type: Optional[str] = None,
        worker_name: Optional[str] = None,
        month: Optional[str] = None,
    ) -> List[Tuple]:
        query = "SELECT t.id, t.title, t.type, w.name, t.created_at "
        query += "FROM tasks t LEFT JOIN workers w ON t.worker_id = w.id"
        conditions = []
        params: List = []
        if task_type:
            conditions.append("t.type = ?")
            params.append(task_type)
        if worker_name:
            conditions.append("w.name = ?")
            params.append(worker_name)
        if month:
            conditions.append("strftime('%Y-%m', t.created_at) = ?")
            params.append(month)
        if conditions:
            query += " WHERE " + " AND ".join(conditions)
        query += " ORDER BY t.created_at DESC"
        cursor = await self.conn.execute(query, tuple(params))
        return await cursor.fetchall()

    async def worker_stats(self, month: str) -> List[Tuple[str, int]]:
        cursor = await self.conn.execute(
            """
            SELECT w.name, COUNT(t.id) as cnt
            FROM tasks t
            JOIN workers w ON t.worker_id = w.id
            WHERE strftime('%Y-%m', t.created_at) = ?
            GROUP BY w.id
            ORDER BY cnt DESC
            """,
            (month,),
        )
        return await cursor.fetchall()
