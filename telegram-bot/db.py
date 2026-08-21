from __future__ import annotations

from contextlib import asynccontextmanager
from datetime import datetime
from pathlib import Path

import aiosqlite

DB_PATH = Path(__file__).with_name("booking.sqlite3")


async def init_db() -> None:
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute("""
            CREATE TABLE IF NOT EXISTS bookings (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL,
                username TEXT,
                client_name TEXT NOT NULL,
                phone TEXT NOT NULL,
                service_id INTEGER NOT NULL,
                service_name TEXT NOT NULL,
                master_id INTEGER NOT NULL,
                master_name TEXT NOT NULL,
                start_at TEXT NOT NULL,
                end_at TEXT NOT NULL,
                status TEXT NOT NULL DEFAULT 'active',
                reminder_sent INTEGER NOT NULL DEFAULT 0,
                created_at TEXT NOT NULL
            )
        """)
        await db.execute("""
            CREATE INDEX IF NOT EXISTS idx_bookings_master_time
            ON bookings(master_id, start_at, end_at, status)
        """)
        await db.execute("""
            CREATE INDEX IF NOT EXISTS idx_bookings_user
            ON bookings(user_id, status, start_at)
        """)
        await db.commit()


async def has_overlap(master_id: int, start_at: datetime, end_at: datetime) -> bool:
    async with aiosqlite.connect(DB_PATH) as db:
        cursor = await db.execute(
            """
            SELECT 1
            FROM bookings
            WHERE master_id = ?
              AND status = 'active'
              AND start_at < ?
              AND end_at > ?
            LIMIT 1
            """,
            (master_id, end_at.isoformat(), start_at.isoformat()),
        )
        return await cursor.fetchone() is not None


async def create_booking(
    *,
    user_id: int,
    username: str | None,
    client_name: str,
    phone: str,
    service_id: int,
    service_name: str,
    master_id: int,
    master_name: str,
    start_at: datetime,
    end_at: datetime,
) -> int | None:
    # BEGIN IMMEDIATE сериализует конкурирующие записи и не даёт двум клиентам
    # одновременно забронировать пересекающееся время одного мастера.
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute("BEGIN IMMEDIATE")

        cursor = await db.execute(
            """
            SELECT 1
            FROM bookings
            WHERE master_id = ?
              AND status = 'active'
              AND start_at < ?
              AND end_at > ?
            LIMIT 1
            """,
            (master_id, end_at.isoformat(), start_at.isoformat()),
        )
        if await cursor.fetchone():
            await db.rollback()
            return None

        cursor = await db.execute(
            """
            INSERT INTO bookings (
                user_id, username, client_name, phone,
                service_id, service_name, master_id, master_name,
                start_at, end_at, status, reminder_sent, created_at
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, 'active', 0, ?)
            """,
            (
                user_id,
                username,
                client_name,
                phone,
                service_id,
                service_name,
                master_id,
                master_name,
                start_at.isoformat(),
                end_at.isoformat(),
                datetime.now().isoformat(),
            ),
        )
        await db.commit()
        return int(cursor.lastrowid)


async def user_bookings(user_id: int, now: datetime) -> list[dict]:
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        cursor = await db.execute(
            """
            SELECT *
            FROM bookings
            WHERE user_id = ?
              AND status = 'active'
              AND end_at >= ?
            ORDER BY start_at
            """,
            (user_id, now.isoformat()),
        )
        return [dict(row) for row in await cursor.fetchall()]


async def cancel_booking(booking_id: int, user_id: int | None = None) -> dict | None:
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row

        if user_id is None:
            cursor = await db.execute(
                "SELECT * FROM bookings WHERE id = ? AND status = 'active'",
                (booking_id,),
            )
        else:
            cursor = await db.execute(
                """
                SELECT * FROM bookings
                WHERE id = ? AND user_id = ? AND status = 'active'
                """,
                (booking_id, user_id),
            )

        row = await cursor.fetchone()
        if not row:
            return None

        await db.execute(
            "UPDATE bookings SET status = 'cancelled' WHERE id = ?",
            (booking_id,),
        )
        await db.commit()
        return dict(row)


async def bookings_for_date(date_prefix: str) -> list[dict]:
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        cursor = await db.execute(
            """
            SELECT *
            FROM bookings
            WHERE status = 'active'
              AND start_at LIKE ?
            ORDER BY start_at
            """,
            (f"{date_prefix}%",),
        )
        return [dict(row) for row in await cursor.fetchall()]


async def due_reminders(now: datetime, until: datetime) -> list[dict]:
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        cursor = await db.execute(
            """
            SELECT *
            FROM bookings
            WHERE status = 'active'
              AND reminder_sent = 0
              AND start_at > ?
              AND start_at <= ?
            ORDER BY start_at
            """,
            (now.isoformat(), until.isoformat()),
        )
        return [dict(row) for row in await cursor.fetchall()]


async def mark_reminder_sent(booking_id: int) -> None:
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute(
            "UPDATE bookings SET reminder_sent = 1 WHERE id = ?",
            (booking_id,),
        )
        await db.commit()
