"""
보스 타이머 공용 데이터베이스 관리
"""
import aiosqlite
import os
from datetime import datetime, timezone, timedelta
from typing import Optional
from bot.config.settings import BOSS_DB_PATH


class BossDB:
    def __init__(self, boss_type: str, cooldown_hours: int):
        self.boss_type = boss_type
        self.cooldown_hours = cooldown_hours
        self.db_path = BOSS_DB_PATH

    async def init_db(self):
        """DB 초기화 - 테이블 생성"""
        os.makedirs(os.path.dirname(self.db_path), exist_ok=True)

        async with aiosqlite.connect(self.db_path) as db:
            await db.execute("""
                CREATE TABLE IF NOT EXISTS boss_records (
                    discord_user_id INTEGER NOT NULL,
                    boss_type TEXT NOT NULL,
                    last_clear_time TEXT NOT NULL,
                    next_available_time TEXT NOT NULL,
                    PRIMARY KEY (discord_user_id, boss_type)
                )
            """)
            await db.execute("""
                CREATE TABLE IF NOT EXISTS boss_alarms (
                    discord_user_id INTEGER NOT NULL,
                    boss_type TEXT NOT NULL,
                    hours_before INTEGER NOT NULL DEFAULT 1,
                    alarm_time TEXT NOT NULL,
                    alarm_sent INTEGER NOT NULL DEFAULT 0,
                    PRIMARY KEY (discord_user_id, boss_type)
                )
            """)
            await db.commit()

    async def get_record(self, user_id: int) -> Optional[dict]:
        """유저의 보스 기록 조회"""
        async with aiosqlite.connect(self.db_path) as db:
            db.row_factory = aiosqlite.Row
            cursor = await db.execute(
                "SELECT * FROM boss_records WHERE discord_user_id = ? AND boss_type = ?",
                (user_id, self.boss_type)
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
        next_available = clear_time + timedelta(hours=self.cooldown_hours)

        async with aiosqlite.connect(self.db_path) as db:
            await db.execute("""
                INSERT INTO boss_records (discord_user_id, boss_type, last_clear_time, next_available_time)
                VALUES (?, ?, ?, ?)
                ON CONFLICT(discord_user_id, boss_type) DO UPDATE SET
                    last_clear_time = excluded.last_clear_time,
                    next_available_time = excluded.next_available_time
            """, (user_id, self.boss_type, clear_time.isoformat(), next_available.isoformat()))

            # 알람이 있으면 시간 재계산 + alarm_sent 리셋
            cursor = await db.execute(
                "SELECT hours_before FROM boss_alarms WHERE discord_user_id = ? AND boss_type = ?",
                (user_id, self.boss_type)
            )
            row = await cursor.fetchone()
            if row:
                hours_before = row[0]
                alarm_time = next_available - timedelta(hours=hours_before)
                now = datetime.now(timezone.utc)
                alarm_sent = 1 if alarm_time <= now else 0
                await db.execute("""
                    UPDATE boss_alarms SET alarm_time = ?, alarm_sent = ?
                    WHERE discord_user_id = ? AND boss_type = ?
                """, (alarm_time.isoformat(), alarm_sent, user_id, self.boss_type))

            await db.commit()

        return {
            "last_clear_time": clear_time,
            "next_available_time": next_available,
        }

    async def delete_record(self, user_id: int) -> bool:
        """유저의 클리어 기록 삭제"""
        async with aiosqlite.connect(self.db_path) as db:
            cursor = await db.execute(
                "DELETE FROM boss_records WHERE discord_user_id = ? AND boss_type = ?",
                (user_id, self.boss_type)
            )
            await db.commit()
            return cursor.rowcount > 0

    async def set_alarm(self, user_id: int, hours_before: int) -> Optional[datetime]:
        """알람 설정"""
        record = await self.get_record(user_id)
        if not record:
            return None

        next_available = record["next_available_time"]
        alarm_time = next_available - timedelta(hours=hours_before)
        now = datetime.now(timezone.utc)
        alarm_sent = 1 if alarm_time <= now else 0

        async with aiosqlite.connect(self.db_path) as db:
            await db.execute("""
                INSERT INTO boss_alarms (discord_user_id, boss_type, hours_before, alarm_time, alarm_sent)
                VALUES (?, ?, ?, ?, ?)
                ON CONFLICT(discord_user_id, boss_type) DO UPDATE SET
                    hours_before = excluded.hours_before,
                    alarm_time = excluded.alarm_time,
                    alarm_sent = excluded.alarm_sent
            """, (user_id, self.boss_type, hours_before, alarm_time.isoformat(), alarm_sent))
            await db.commit()

        return alarm_time

    async def get_alarm(self, user_id: int) -> Optional[dict]:
        """유저의 알람 설정 조회"""
        async with aiosqlite.connect(self.db_path) as db:
            db.row_factory = aiosqlite.Row
            cursor = await db.execute(
                "SELECT * FROM boss_alarms WHERE discord_user_id = ? AND boss_type = ?",
                (user_id, self.boss_type)
            )
            row = await cursor.fetchone()
            if not row:
                return None
            return dict(row)

    async def remove_alarm(self, user_id: int) -> bool:
        """유저의 알람 해제"""
        async with aiosqlite.connect(self.db_path) as db:
            cursor = await db.execute(
                "DELETE FROM boss_alarms WHERE discord_user_id = ? AND boss_type = ?",
                (user_id, self.boss_type)
            )
            await db.commit()
            return cursor.rowcount > 0

    async def get_next_pending_alarm(self) -> Optional[dict]:
        """이 보스의 가장 빠른 미발송 알람 조회"""
        async with aiosqlite.connect(self.db_path) as db:
            db.row_factory = aiosqlite.Row
            cursor = await db.execute("""
                SELECT a.*, r.next_available_time
                FROM boss_alarms a
                JOIN boss_records r ON a.discord_user_id = r.discord_user_id AND a.boss_type = r.boss_type
                WHERE a.alarm_sent = 0 AND a.boss_type = ?
                ORDER BY a.alarm_time ASC
                LIMIT 1
            """, (self.boss_type,))
            row = await cursor.fetchone()
            if not row:
                return None
            return dict(row)

    async def get_all_due_alarms(self, now: datetime) -> list:
        """이 보스의 발송해야 할 모든 알람 조회"""
        async with aiosqlite.connect(self.db_path) as db:
            db.row_factory = aiosqlite.Row
            cursor = await db.execute("""
                SELECT a.*, r.next_available_time
                FROM boss_alarms a
                JOIN boss_records r ON a.discord_user_id = r.discord_user_id AND a.boss_type = r.boss_type
                WHERE a.alarm_sent = 0 AND a.boss_type = ? AND a.alarm_time <= ?
                ORDER BY a.alarm_time ASC
            """, (self.boss_type, now.isoformat()))
            rows = await cursor.fetchall()
            return [dict(row) for row in rows]

    async def mark_alarm_sent(self, user_id: int):
        """알람 발송 완료 처리"""
        async with aiosqlite.connect(self.db_path) as db:
            await db.execute(
                "UPDATE boss_alarms SET alarm_sent = 1 WHERE discord_user_id = ? AND boss_type = ?",
                (user_id, self.boss_type)
            )
            await db.commit()
