"""
붕어(피아누스) 알람 데이터베이스 관리
"""
import aiosqlite
import os
from datetime import datetime, timezone, timedelta
from typing import Optional
from bot.config.settings import PIANUS_DB_PATH, PIANUS_COOLDOWN_DAYS

KST = timezone(timedelta(hours=9))


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
                    next_available_time TEXT NOT NULL,
                    created_at TEXT NOT NULL DEFAULT (datetime('now')),
                    updated_at TEXT NOT NULL DEFAULT (datetime('now'))
                )
            """)
            await db.execute("""
                CREATE TABLE IF NOT EXISTS pianus_alarms (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    discord_user_id INTEGER NOT NULL,
                    alarm_type TEXT NOT NULL,
                    alarm_value INTEGER NOT NULL,
                    alarm_time TEXT NOT NULL,
                    alarm_sent INTEGER NOT NULL DEFAULT 0,
                    UNIQUE(discord_user_id, alarm_type, alarm_value)
                )
            """)
            await db.commit()

    async def record_clear(self, user_id: int, clear_time: datetime) -> dict:
        """클리어 기록 저장 및 알람 시간 재계산"""
        next_available = clear_time + timedelta(days=PIANUS_COOLDOWN_DAYS)
        now = datetime.now(timezone.utc).isoformat()

        async with aiosqlite.connect(self.db_path) as db:
            await db.execute("""
                INSERT INTO pianus_records (discord_user_id, last_clear_time, next_available_time, created_at, updated_at)
                VALUES (?, ?, ?, ?, ?)
                ON CONFLICT(discord_user_id) DO UPDATE SET
                    last_clear_time = excluded.last_clear_time,
                    next_available_time = excluded.next_available_time,
                    updated_at = excluded.updated_at
            """, (user_id, clear_time.isoformat(), next_available.isoformat(), now, now))

            # 기존 알람의 alarm_time 재계산 + alarm_sent 리셋
            await self._recalculate_alarms(db, user_id, next_available)
            await db.commit()

        return {
            "last_clear_time": clear_time,
            "next_available_time": next_available,
        }

    async def _recalculate_alarms(self, db, user_id: int, next_available: datetime):
        """알람 시간을 next_available 기준으로 재계산"""
        cursor = await db.execute(
            "SELECT id, alarm_type, alarm_value FROM pianus_alarms WHERE discord_user_id = ?",
            (user_id,)
        )
        alarms = await cursor.fetchall()

        for alarm_id, alarm_type, alarm_value in alarms:
            alarm_time = self._compute_alarm_time(alarm_type, alarm_value, next_available)
            await db.execute(
                "UPDATE pianus_alarms SET alarm_time = ?, alarm_sent = 0 WHERE id = ?",
                (alarm_time.isoformat(), alarm_id)
            )

    @staticmethod
    def _compute_alarm_time(alarm_type: str, alarm_value: int, next_available: datetime) -> datetime:
        """알람 발송 시각 계산"""
        if alarm_type == "offset":
            # N분 전
            return next_available - timedelta(minutes=alarm_value)
        elif alarm_type == "morning":
            # 당일 HH시 (KST)
            available_kst = next_available.astimezone(KST)
            morning_kst = available_kst.replace(hour=alarm_value, minute=0, second=0, microsecond=0)
            # KST 시각을 UTC로 변환하여 저장
            return morning_kst.astimezone(timezone.utc)
        return next_available

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

    async def get_alarms(self, user_id: int) -> list:
        """유저의 알람 설정 조회"""
        async with aiosqlite.connect(self.db_path) as db:
            db.row_factory = aiosqlite.Row
            cursor = await db.execute(
                "SELECT * FROM pianus_alarms WHERE discord_user_id = ?",
                (user_id,)
            )
            rows = await cursor.fetchall()
            return [dict(row) for row in rows]

    async def add_alarm(self, user_id: int, alarm_type: str, alarm_value: int) -> Optional[datetime]:
        """알람 추가. 클리어 기록이 있으면 alarm_time 계산, 없으면 None 반환"""
        record = await self.get_record(user_id)
        if not record:
            return None

        next_available = record["next_available_time"]
        alarm_time = self._compute_alarm_time(alarm_type, alarm_value, next_available)
        now = datetime.now(timezone.utc)

        # 이미 지난 알람이면 sent=1로 저장
        alarm_sent = 1 if alarm_time <= now else 0

        async with aiosqlite.connect(self.db_path) as db:
            await db.execute("""
                INSERT INTO pianus_alarms (discord_user_id, alarm_type, alarm_value, alarm_time, alarm_sent)
                VALUES (?, ?, ?, ?, ?)
                ON CONFLICT(discord_user_id, alarm_type, alarm_value) DO UPDATE SET
                    alarm_time = excluded.alarm_time,
                    alarm_sent = excluded.alarm_sent
            """, (user_id, alarm_type, alarm_value, alarm_time.isoformat(), alarm_sent))
            await db.commit()

        return alarm_time

    async def remove_alarms(self, user_id: int):
        """유저의 모든 알람 해제"""
        async with aiosqlite.connect(self.db_path) as db:
            await db.execute(
                "DELETE FROM pianus_alarms WHERE discord_user_id = ?",
                (user_id,)
            )
            await db.commit()

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
        """알람 발송 완료 처리"""
        async with aiosqlite.connect(self.db_path) as db:
            await db.execute(
                "UPDATE pianus_alarms SET alarm_sent = 1 WHERE id = ?",
                (alarm_id,)
            )
            await db.commit()
