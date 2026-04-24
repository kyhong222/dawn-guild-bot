"""
메이플랜드 공지사항 스크래퍼
"""
import asyncio
import logging
import re
import aiohttp
import aiosqlite
import os

logger = logging.getLogger(__name__)
from typing import List
from bot.config.settings import NOTICE_DB_PATH

CATEGORIES = {
    "안내": "%EC%95%88%EB%82%B4",
    "점검": "%EC%A0%90%EA%B2%80",
    "업데이트": "%EC%97%85%EB%8D%B0%EC%9D%B4%ED%8A%B8",
}

CATEGORY_EMOJI = {
    "안내": "📢",
    "점검": "🔧",
    "업데이트": "🆕",
}


async def init_db():
    """DB 초기화"""
    os.makedirs(os.path.dirname(NOTICE_DB_PATH), exist_ok=True)
    async with aiosqlite.connect(NOTICE_DB_PATH) as db:
        await db.execute("""
            CREATE TABLE IF NOT EXISTS notice_last_seen (
                category TEXT PRIMARY KEY,
                last_id INTEGER NOT NULL DEFAULT 0
            )
        """)
        await db.commit()


async def get_last_seen_id(category: str) -> int:
    """카테고리별 마지막으로 본 게시글 ID"""
    async with aiosqlite.connect(NOTICE_DB_PATH) as db:
        cursor = await db.execute(
            "SELECT last_id FROM notice_last_seen WHERE category = ?",
            (category,)
        )
        row = await cursor.fetchone()
        return row[0] if row else 0


async def set_last_seen_id(category: str, last_id: int):
    """카테고리별 마지막 ID 갱신"""
    async with aiosqlite.connect(NOTICE_DB_PATH) as db:
        await db.execute("""
            INSERT INTO notice_last_seen (category, last_id) VALUES (?, ?)
            ON CONFLICT(category) DO UPDATE SET last_id = excluded.last_id
        """, (category, last_id))
        await db.commit()


async def fetch_notices(category_encoded: str, max_retries: int = 3) -> List[dict]:
    """카테고리별 공지사항 파싱. 429 시 재시도."""
    url = f"https://maple.land/board/notices?category={category_encoded}"

    for attempt in range(max_retries):
        async with aiohttp.ClientSession() as session:
            async with session.get(url, timeout=aiohttp.ClientTimeout(total=15)) as resp:
                if resp.status == 429:
                    # Rate limit — Retry-After 헤더 또는 기본 30초 대기 후 재시도
                    retry_after = int(resp.headers.get("Retry-After", 30))
                    logger.warning(f"📢 429 Rate Limited ({category_encoded}), {retry_after}초 후 재시도 ({attempt+1}/{max_retries})")
                    await asyncio.sleep(retry_after)
                    continue
                if resp.status != 200:
                    logger.warning(f"📢 공지 조회 실패: status={resp.status} ({category_encoded})")
                    return []
                html = await resp.text()
                break
    else:
        # 모든 재시도 실패
        logger.error(f"📢 공지 조회 재시도 초과 ({category_encoded})")
        return []

    # Next.js RSC 이스케이프 해제 후 정규식 파싱
    cleaned = html.replace('\\"', '"')

    posts = []
    pattern = r'"id":(\d+),"documentId":"([^"]+)","title":"((?:[^"\\]|\\.)*)","category":"([^"]+)","views":(\d+),"createdAt":"([^"]+)"'
    for m in re.finditer(pattern, cleaned):
        posts.append({
            "id": int(m.group(1)),
            "documentId": m.group(2),
            "title": m.group(3),
            "category": m.group(4),
            "views": int(m.group(5)),
            "createdAt": m.group(6),
            "url": f"https://maple.land/board/notices/{m.group(2)}",
        })

    return posts


async def check_new_notices() -> List[dict]:
    """모든 카테고리에서 새 공지 확인. 새 글 목록 반환."""
    new_posts = []

    for category, encoded in CATEGORIES.items():
        try:
            posts = await fetch_notices(encoded)
            if not posts:
                continue

            last_seen = await get_last_seen_id(category)
            max_id = max(p["id"] for p in posts)

            if last_seen == 0:
                # 최초 실행: 현재 최대 ID만 저장 (알림 안 보냄)
                await set_last_seen_id(category, max_id)
                continue

            # 새 글 필터 (id가 last_seen보다 큰 것)
            new = [p for p in posts if p["id"] > last_seen]

            if new:
                new.sort(key=lambda p: p["id"])
                new_posts.extend(new)
                await set_last_seen_id(category, max_id)

        except Exception:
            continue

    return new_posts
