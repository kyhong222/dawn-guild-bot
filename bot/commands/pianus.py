"""
붕어(피아누스) 알람 명령어
"""
import asyncio
import re
import logging
import discord
from discord.ext import commands
from datetime import datetime, timezone, timedelta
from bot.config.settings import BOT_COLOR, PIANUS_COOLDOWN_DAYS
from bot.utils.pianus_db import PianusDB

logger = logging.getLogger(__name__)

KST = timezone(timedelta(hours=9))


def format_remaining(td: timedelta) -> str:
    """남은 시간을 한국어로 포맷"""
    total_seconds = int(td.total_seconds())
    if total_seconds <= 0:
        return "지금 가능!"

    days = total_seconds // 86400
    hours = (total_seconds % 86400) // 3600
    minutes = (total_seconds % 3600) // 60

    parts = []
    if days > 0:
        parts.append(f"{days}일")
    if hours > 0:
        parts.append(f"{hours}시간")
    if minutes > 0:
        parts.append(f"{minutes}분")

    return " ".join(parts) if parts else "1분 미만"


class PianusCommands(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.db = PianusDB()
        self._alarm_task: asyncio.Task = None

    async def cog_load(self):
        """Cog 로드 시 DB 초기화 및 알람 스케줄러 시작"""
        await self.db.init_db()
        logger.info("🐟 붕어 DB 초기화 완료")
        self._schedule_next_alarm()

    async def cog_unload(self):
        """Cog 언로드 시 알람 태스크 취소"""
        if self._alarm_task and not self._alarm_task.done():
            self._alarm_task.cancel()

    # ─── 알람 스케줄러 ───

    def _schedule_next_alarm(self):
        """다음 알람을 스케줄링"""
        if self._alarm_task and not self._alarm_task.done():
            self._alarm_task.cancel()
        self._alarm_task = asyncio.create_task(self._alarm_loop())

    async def _alarm_loop(self):
        """가장 빠른 알람까지 대기 후 발송, 반복"""
        await self.bot.wait_until_ready()

        while not self.bot.is_closed():
            try:
                # 이미 발송해야 할 알람 먼저 처리
                now = datetime.now(timezone.utc)
                due_alarms = await self.db.get_all_due_alarms(now)
                for alarm in due_alarms:
                    await self._send_alarm(alarm)

                # 다음 알람 조회
                next_alarm = await self.db.get_next_pending_alarm()
                if not next_alarm:
                    await asyncio.sleep(3600)
                    continue

                alarm_time = datetime.fromisoformat(next_alarm["alarm_time"])
                now = datetime.now(timezone.utc)
                wait_seconds = (alarm_time - now).total_seconds()

                if wait_seconds > 0:
                    logger.info(f"🐟 다음 알람까지 {wait_seconds:.0f}초 대기")
                    await asyncio.sleep(wait_seconds)

                # 발송 시점의 모든 due 알람 처리
                now = datetime.now(timezone.utc)
                due_alarms = await self.db.get_all_due_alarms(now)
                for alarm in due_alarms:
                    await self._send_alarm(alarm)

            except asyncio.CancelledError:
                logger.info("🐟 알람 스케줄러 종료")
                return
            except Exception as e:
                logger.error(f"🐟 알람 스케줄러 오류: {e}")
                await asyncio.sleep(60)

    async def _send_alarm(self, alarm: dict):
        """DM으로 알람 발송"""
        user_id = alarm["discord_user_id"]

        try:
            user = await self.bot.fetch_user(user_id)
            next_available = datetime.fromisoformat(alarm["next_available_time"])
            next_kst = next_available.astimezone(KST)
            now = datetime.now(timezone.utc)
            remaining = next_available - now

            embed = discord.Embed(
                title="🐟 붕어 알람!",
                color=BOT_COLOR,
            )

            if remaining.total_seconds() <= 0:
                embed.description = "피아누스에 도전할 수 있습니다!"
            else:
                embed.description = (
                    f"피아누스 도전 가능 시각이 다가오고 있습니다!\n"
                    f"남은 시간: **{format_remaining(remaining)}**"
                )

            embed.add_field(
                name="⏰ 도전 가능 시각",
                value=next_kst.strftime("%m/%d(%a) %H:%M KST"),
                inline=False,
            )
            embed.set_footer(text=f"알람 설정: {alarm['hours_before']}시간 전")

            await user.send(embed=embed)
            logger.info(f"🐟 알람 발송 완료: user={user_id}")

        except discord.Forbidden:
            logger.warning(f"🐟 DM 발송 실패 (DM 차단): user={user_id}")
        except Exception as e:
            logger.error(f"🐟 알람 발송 오류: user={user_id}, error={e}")

        # 성공/실패 관계없이 sent 처리
        await self.db.mark_alarm_sent(user_id)

    # ─── 명령어 ───

    @commands.command(name='붕어')
    async def pianus_command(self, ctx):
        """붕어 기록/확인 (기록 없거나 7일 지남 → 기록, 7일 이내 → 현황)"""
        record = await self.db.get_record(ctx.author.id)
        now = datetime.now(timezone.utc)

        # 기록이 없거나 7일 지났으면 → 현재 시각 기록
        if not record or now >= record["next_available_time"]:
            result = await self.db.record_clear(ctx.author.id, now)

            clear_kst = result["last_clear_time"].astimezone(KST)
            next_kst = result["next_available_time"].astimezone(KST)

            embed = discord.Embed(
                title="🐟 붕어 클리어 기록 완료!",
                color=BOT_COLOR,
            )
            embed.add_field(
                name="🕐 클리어 시각",
                value=clear_kst.strftime("%m/%d(%a) %H:%M KST"),
                inline=True,
            )
            embed.add_field(
                name="⏰ 다음 도전 가능",
                value=next_kst.strftime("%m/%d(%a) %H:%M KST"),
                inline=True,
            )

            # 알람 설정 안내
            alarm = await self.db.get_alarm(ctx.author.id)
            if alarm:
                embed.add_field(
                    name="🔔 알람",
                    value=f"{alarm['hours_before']}시간 전 알람 재설정됨",
                    inline=False,
                )
            else:
                embed.add_field(
                    name="🔔 알람",
                    value="`!붕어알람`으로 알람을 설정할 수 있습니다.",
                    inline=False,
                )

            embed.set_footer(text=f"요청자: {ctx.author.display_name}")
            await ctx.send(embed=embed)
            self._schedule_next_alarm()

        # 7일 이내 → 현황 안내
        else:
            next_available = record["next_available_time"]
            clear_kst = record["last_clear_time"].astimezone(KST)
            next_kst = next_available.astimezone(KST)
            remaining = next_available - now

            embed = discord.Embed(
                title=f"🐟 {ctx.author.display_name}님의 붕어 현황",
                description=f"⏳ **{format_remaining(remaining)}** 남음",
                color=BOT_COLOR,
            )
            embed.add_field(
                name="🕐 마지막 클리어",
                value=clear_kst.strftime("%m/%d(%a) %H:%M"),
                inline=True,
            )
            embed.add_field(
                name="⏰ 다음 도전 가능",
                value=next_kst.strftime("%m/%d(%a) %H:%M"),
                inline=True,
            )

            alarm = await self.db.get_alarm(ctx.author.id)
            if alarm:
                alarm_time_kst = datetime.fromisoformat(alarm["alarm_time"]).astimezone(KST)
                sent_text = "✅ 발송 완료" if alarm["alarm_sent"] else f"⏳ {alarm_time_kst.strftime('%m/%d %H:%M')} 발송 예정"
                embed.add_field(
                    name=f"🔔 알람 ({alarm['hours_before']}시간 전)",
                    value=sent_text,
                    inline=False,
                )

            await ctx.send(embed=embed)

    @commands.command(name='붕어취소')
    async def pianus_cancel(self, ctx):
        """마지막 붕어 기록 취소"""
        record = await self.db.get_record(ctx.author.id)
        if not record:
            await ctx.send("ℹ️ 취소할 클리어 기록이 없습니다.")
            return

        clear_kst = record["last_clear_time"].astimezone(KST)
        await self.db.delete_record(ctx.author.id)

        embed = discord.Embed(
            title="🐟 붕어 기록 취소 완료",
            description=(
                f"**{clear_kst.strftime('%m/%d(%a) %H:%M')}** 클리어 기록이 삭제되었습니다.\n"
                "다음 `!붕어` 입력 시 새로 기록됩니다."
            ),
            color=BOT_COLOR,
        )
        await ctx.send(embed=embed)
        self._schedule_next_alarm()

    @commands.command(name='붕어알람', aliases=['붕어알림'])
    async def pianus_alarm(self, ctx, *, alarm_input: str = None):
        """붕어 알람 설정 (기본 1시간 전, N시간전 지정 가능)"""
        # 클리어 기록 확인
        record = await self.db.get_record(ctx.author.id)
        if not record:
            await ctx.send("❌ 먼저 `!붕어`로 클리어 기록을 등록해주세요.")
            return

        # 시간 파싱
        hours_before = 1  # 기본값
        if alarm_input:
            match = re.match(r'^(\d+)\s*시간\s*전$', alarm_input.strip())
            if not match:
                embed = discord.Embed(
                    title="❌ 알람 형식 오류",
                    description=(
                        "올바른 형식으로 입력해주세요.\n\n"
                        "• `!붕어알람` — 1시간 전 알람\n"
                        "• `!붕어알람 2시간전`\n"
                        "• `!붕어알람 12시간전`"
                    ),
                    color=0xFF3333,
                )
                await ctx.send(embed=embed)
                return
            hours_before = int(match.group(1))
            if hours_before <= 0 or hours_before > 168:
                await ctx.send("❌ 1~168시간 사이로 입력해주세요.")
                return

        # DM 발송 테스트
        try:
            test_embed = discord.Embed(
                title="🐟 붕어 알람 테스트",
                description=f"알람이 설정되었습니다! {hours_before}시간 전에 이 DM으로 알림을 보내드립니다.",
                color=BOT_COLOR,
            )
            await ctx.author.send(embed=test_embed)
        except discord.Forbidden:
            embed = discord.Embed(
                title="❌ DM을 보낼 수 없습니다",
                description=(
                    "알람은 DM으로 발송됩니다.\n"
                    "**서버 설정 → 개인정보 보호 → '서버 멤버가 보내는 다이렉트 메시지'**를 켜주세요."
                ),
                color=0xFF3333,
            )
            await ctx.send(embed=embed)
            return

        # 알람 저장
        alarm_time = await self.db.set_alarm(ctx.author.id, hours_before)
        alarm_kst = alarm_time.astimezone(KST)

        embed = discord.Embed(
            title="🔔 붕어 알람 설정 완료!",
            color=BOT_COLOR,
        )
        embed.add_field(name="알람", value=f"{hours_before}시간 전", inline=True)
        embed.add_field(
            name="다음 알람",
            value=alarm_kst.strftime("%m/%d(%a) %H:%M KST"),
            inline=True,
        )
        embed.set_footer(text="테스트 DM을 확인해주세요!")
        await ctx.send(embed=embed)
        self._schedule_next_alarm()


async def setup(bot):
    await bot.add_cog(PianusCommands(bot))
