import asyncio
import json
import logging
import re
from collections import deque
from datetime import datetime, timedelta

import aiohttp
import discord
from discord.ext import commands

logger = logging.getLogger(__name__)

SESSION_URL = "https://megaphoneland.com/api/session"
WS_URL = "wss://megaphoneland.com/ws"
BUFFER_WINDOW = timedelta(hours=1)
MAX_BUFFER = 2000
MAX_RESULTS = 5


class Megaphone(commands.Cog):
    """확성기 실시간 수집 + 검색 명령어 (고확/마뇽/월코)"""

    def __init__(self, bot):
        self.bot = bot
        self.messages: deque = deque(maxlen=MAX_BUFFER)
        self._task: asyncio.Task | None = None
        self._session: aiohttp.ClientSession | None = None

    async def cog_load(self):
        self._task = asyncio.create_task(self._ws_loop())

    async def cog_unload(self):
        if self._task:
            self._task.cancel()
        if self._session:
            await self._session.close()

    async def _fetch_token(self) -> str | None:
        """세션 토큰 발급"""
        try:
            async with self._session.get(SESSION_URL) as r:
                data = await r.json()
                return data.get("token")
        except Exception as e:
            logger.error(f"확성기 세션 토큰 발급 실패: {e}")
            return None

    async def _ws_loop(self):
        """WS 연결 + 자동 재연결 (매 연결마다 토큰 재발급)"""
        backoff = 5
        self._session = aiohttp.ClientSession()

        while True:
            try:
                token = await self._fetch_token()
                if not token:
                    raise RuntimeError("토큰 발급 실패")

                url = f"{WS_URL}?token={token}"
                async with self._session.ws_connect(url, heartbeat=30) as ws:
                    logger.info("📢 확성기 WS 연결됨")
                    backoff = 5
                    async for msg in ws:
                        if msg.type == aiohttp.WSMsgType.TEXT:
                            self._handle_payload(msg.data)
                        elif msg.type in (aiohttp.WSMsgType.CLOSED, aiohttp.WSMsgType.ERROR):
                            break
            except asyncio.CancelledError:
                raise
            except Exception as e:
                logger.error(f"확성기 WS 오류: {e}")

            logger.info(f"확성기 WS 재연결 대기 {backoff}s")
            await asyncio.sleep(backoff)
            backoff = min(backoff * 2, 60)

    def _handle_payload(self, raw: str):
        try:
            payload = json.loads(raw)
        except json.JSONDecodeError:
            return

        ptype = payload.get("type")
        if ptype == "init":
            items = payload.get("messages", [])
        elif ptype == "messages":
            items = payload.get("data", [])
        else:
            return

        for item in items:
            self._add_message(item)

    def _add_message(self, item: dict):
        try:
            ts = datetime.strptime(item["time"], "%Y-%m-%d %H:%M:%S")
        except (KeyError, ValueError):
            ts = datetime.now()
        self.messages.append((ts, item))

    def _recent(self) -> list[tuple[datetime, dict]]:
        """1시간 이내 메시지, 최신순"""
        cutoff = datetime.now() - BUFFER_WINDOW
        return [m for m in reversed(self.messages) if m[0] >= cutoff]

    def _format_results(
        self, matches: list[tuple[datetime, dict]], keywords: list[str]
    ) -> str:
        if not matches:
            return "_1시간 이내 매칭되는 확성기가 없습니다._"

        lines = []
        for ts, item in matches[:MAX_RESULTS]:
            name = item.get("name", "?")
            content = item.get("content", "")
            # 키워드 bold 처리
            for kw in keywords:
                if kw:
                    content = re.sub(
                        f"({re.escape(kw)})", r"**\1**", content
                    )
            time_str = ts.strftime("%H:%M")
            lines.append(f"`{time_str}` **{name}**: {content}")
        return "\n".join(lines)

    async def _send_embed(
        self,
        ctx,
        title: str,
        matches: list[tuple[datetime, dict]],
        keywords: list[str],
    ):
        desc = self._format_results(matches, keywords)
        total = len(matches)
        embed = discord.Embed(
            title=title,
            description=desc,
            color=0xFF6B35,
        )
        shown = min(total, MAX_RESULTS)
        embed.set_footer(text=f"최근 1시간 · {total}건 중 {shown}건 표시")
        await ctx.send(embed=embed)

    @commands.command(name="고확")
    async def high_search(self, ctx, *, keyword: str = None):
        """확성기 키워드 검색 (공백으로 여러 단어 AND)"""
        if not keyword:
            await ctx.send("❌ 검색어를 입력해주세요. 예: `!고확 파엘`")
            return

        terms = keyword.split()
        matches = [
            (ts, item)
            for ts, item in self._recent()
            if all(t in item.get("content", "") for t in terms)
        ]
        await self._send_embed(ctx, f"📢 고확 검색: {keyword}", matches, terms)

    @commands.command(name="마뇽")
    async def manyong(self, ctx):
        """리프레 지역 마뇽/울음 매물 검색"""
        keywords = ["마뇽", "울음"]
        matches = []
        for ts, item in self._recent():
            if item.get("location") != "리프레":
                continue
            content = item.get("content", "")
            if not any(k in content for k in keywords):
                continue
            if not re.search(r"\d+", content):
                continue
            matches.append((ts, item))

        await self._send_embed(ctx, "🐉 마뇽 검색 (리프레)", matches, keywords)

    @commands.command(name="월코")
    async def wolco(self, ctx):
        """월코 시세 검색"""
        matches = []
        for ts, item in self._recent():
            content = item.get("content", "")
            if "월코" not in content:
                continue
            if not re.search(r"\d+", content):
                continue
            matches.append((ts, item))

        await self._send_embed(ctx, "💰 월코 검색", matches, ["월코"])


async def setup(bot):
    await bot.add_cog(Megaphone(bot))
