"""
붕어(피아누스) 알람 데이터베이스 관리
"""
import aiosqlite
import os
from datetime import datetime, timezone, timedelta
from typing import Optional
from bot.config.settings import PIANUS_DB_PATH, PIANUS_COOLDOWN_DAYS


class PianusDB:
    def __init__(self):
        self.db_path = PIANUS_DB_PATH

    async def init_db(self):
        """DB 초기화 - 테이블 생성"""
        os.makedirs(os.path.dirname(self.db_path), exist_ok=True)

        async with aiosqlite.connect(self.db_path) as db:
            await db.execute("""
                CREATE TABLE IF NOT EXISTS pianus_records (
                    discord_user_id INTEGER PRIMARY KEY,
                    last_clear_time TEXT NOT NULL,
                    next_available_time TEXT NOT NULL
                )
            """)
            await db.execute("""
                CREATE TABLE IF NOT EXISTS pianus_alarms (
                    discord_user_id INTEGER PRIMARY KEY,
                    hours_before INTEGER NOT NULL DEFAULT 1,
                    alarm_time TEXT NOT NULL,
                    alarm_sent INTEGER NOT NULL DEFAULT 0
                )
            """)
            await db.commit()

    async def get_record(self, user_id: int) -> Optional[dict]:
        """유저의 붕어 기록 조회"""
        async with aiosqlite.connect(self.db_path) as db:
            db.row_factory = aiosqlite.Row
            cursor = await db.execute(
                "SELECT * FROM pianus_records WHERE discord_user_id = ?",
                (user_id,)
            )
            row = await cursor.fetchone()
            if not row:
                return None
            return {
                "discord_user_id": row["discord_user_id"],
                "last_clear_time": datetime.fromisoformat(row["last_clear_time"]),
                "next_available_time": datetime.fromisoformat(row["next_available_time"]),
            }

    async def record_clear(self, user_id: int, clear_time: datetime) -> dict:
        """클리어 기록 저장 및 알람 시간 재계산"""
        next_available = clear_time + timedelta(days=PIANUS_COOLDOWN_DAYS)

        async with aiosqlite.connect(self.db_path) as db:
            await db.execute("""
                INSERT INTO pianus_records (discord_user_id, last_clear_time, next_available_time)
                VALUES (?, ?, ?)
                ON CONFLICT(discord_user_id) DO UPDATE SET
                    last_clear_time = excluded.last_clear_time,
                    next_available_time = excluded.next_available_time
            """, (user_id, clear_time.isoformat(), next_available.isoformat()))

            # 알람이 있으면 시간 재계산 + alarm_sent 리셋
            cursor = await db.execute(
                "SELECT hours_before FROM pianus_alarms WHERE discord_user_id = ?",
                (user_id,)
            )
            row = await cursor.fetchone()
            if row:
                hours_before = row[0]
                alarm_time = next_available - timedelta(hours=hours_before)
                now = datetime.now(timezone.utc)
                alarm_sent = 1 if alarm_time <= now else 0
                await db.execute("""
                    UPDATE pianus_alarms
                    SET alarm_time = ?, alarm_sent = ?
                    WHERE discord_user_id = ?
                """, (alarm_time.isoformat(), alarm_sent, user_id))

            await db.commit()

        return {
            "last_clear_time": clear_time,
            "next_available_time": next_available,
        }

    async def delete_record(self, user_id: int) -> bool:
        """유저의 클리어 기록 삭제"""
        async with aiosqlite.connect(self.db_path) as db:
            cursor = await db.execute(
                "DELETE FROM pianus_records WHERE discord_user_id = ?",
                (user_id,)
            )
            await db.commit()
            return cursor.rowcount > 0

    async def set_alarm(self, user_id: int, hours_before: int) -> Optional[datetime]:
        """알람 설정. 클리어 기록이 있어야 설정 가능. 알람 시각 반환."""
        record = await self.get_record(user_id)
        if not record:
            return None

        next_available = record["next_available_time"]
        alarm_time = next_available - timedelta(hours=hours_before)
        now = datetime.now(timezone.utc)
        alarm_sent = 1 if alarm_time <= now else 0

        async with aiosqlite.connect(self.db_path) as db:
            await db.execute("""
                INSERT INTO pianus_alarms (discord_user_id, hours_before, alarm_time, alarm_sent)
                VALUES (?, ?, ?, ?)
                ON CONFLICT(discord_user_id) DO UPDATE SET
                    hours_before = excluded.hours_before,
                    alarm_time = excluded.alarm_time,
                    alarm_sent = excluded.alarm_sent
            """, (user_id, hours_before, alarm_time.isoformat(), alarm_sent))
            await db.commit()

        return alarm_time

    async def get_alarm(self, user_id: int) -> Optional[dict]:
        """유저의 알람 설정 조회"""
        async with aiosqlite.connect(self.db_path) as db:
            db.row_factory = aiosqlite.Row
            cursor = await db.execute(
                "SELECT * FROM pianus_alarms WHERE discord_user_id = ?",
                (user_id,)
            )
            row = await cursor.fetchone()
            if not row:
                return None
            return dict(row)

    async def remove_alarm(self, user_id: int) -> bool:
        """유저의 알람 해제"""
        async with aiosqlite.connect(self.db_path) as db:
            cursor = await db.execute(
                "DELETE FROM pianus_alarms WHERE discord_user_id = ?",
                (user_id,)
            )
            await db.commit()
            return cursor.rowcount > 0

    async def get_next_pending_alarm(self) -> Optional[dict]:
        """가장 빠른 미발송 알람 조회 (스케줄러용)"""
        async with aiosqlite.connect(self.db_path) as db:
            db.row_factory = aiosqlite.Row
            cursor = await db.execute("""
                SELECT a.*, r.next_available_time
                FROM pianus_alarms a
                JOIN pianus_records r ON a.discord_user_id = r.discord_user_id
                WHERE a.alarm_sent = 0
                ORDER BY a.alarm_time ASC
                LIMIT 1
            """)
            row = await cursor.fetchone()
            if not row:
                return None
            return dict(row)

    async def get_all_due_alarms(self, now: datetime) -> list:
        """현재 시각 기준으로 발송해야 할 모든 알람 조회"""
        async with aiosqlite.connect(self.db_path) as db:
            db.row_factory = aiosqlite.Row
            cursor = await db.execute("""
                SELECT a.*, r.next_available_time
                FROM pianus_alarms a
                JOIN pianus_records r ON a.discord_user_id = r.discord_user_id
                WHERE a.alarm_sent = 0 AND a.alarm_time <= ?
                ORDER BY a.alarm_time ASC
            """, (now.isoformat(),))
            rows = await cursor.fetchall()
            return [dict(row) for row in rows]

    async def mark_alarm_sent(self, alarm_id: int):
        """알람 발송 완료 처리 (discord_user_id 기준)"""
        async with aiosqlite.connect(self.db_path) as db:
            await db.execute(
                "UPDATE pianus_alarms SET alarm_sent = 1 WHERE discord_user_id = ?",
                (alarm_id,)
            )
            await db.commit()
