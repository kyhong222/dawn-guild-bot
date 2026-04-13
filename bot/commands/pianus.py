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


def format_alarm_description(alarm_type: str, alarm_value: int) -> str:
    """알람 설정을 한국어로 표시"""
    if alarm_type == "offset":
        if alarm_value >= 60:
            return f"{alarm_value // 60}시간전"
        return f"{alarm_value}분전"
    elif alarm_type == "morning":
        return f"당일{alarm_value}시"
    return str(alarm_value)


def parse_alarm_input(text: str):
    """
    알람 입력 파싱.
    반환: (alarm_type, alarm_value) 또는 None

    지원 형식:
    - "30분전", "5분전" → ("offset", 30)
    - "2시간전", "12시간전" → ("offset", 120)
    - "당일9시", "당일21시" → ("morning", 9)
    """
    text = text.strip()

    # N분전
    match = re.match(r'^(\d+)\s*분\s*전$', text)
    if match:
        minutes = int(match.group(1))
        if minutes <= 0:
            return None
        return ("offset", minutes)

    # N시간전
    match = re.match(r'^(\d+)\s*시간\s*전$', text)
    if match:
        hours = int(match.group(1))
        if hours <= 0:
            return None
        return ("offset", hours * 60)

    # 당일HH시
    match = re.match(r'^당일\s*(\d{1,2})\s*시$', text)
    if match:
        hour = int(match.group(1))
        if 0 <= hour <= 23:
            return ("morning", hour)
        return None

    return None


def parse_time_input(text: str) -> datetime:
    """
    시간 입력 파싱 (KST 기준).
    반환: UTC datetime 또는 None

    지원 형식:
    - "MM/DD HH:mm" → 해당 날짜 시각 (올해 기준)
    - "HH:mm" → 오늘 해당 시각
    """
    text = text.strip()
    now_kst = datetime.now(KST)

    # MM/DD HH:mm
    match = re.match(r'^(\d{1,2})/(\d{1,2})\s+(\d{1,2}):(\d{2})$', text)
    if match:
        month, day = int(match.group(1)), int(match.group(2))
        hour, minute = int(match.group(3)), int(match.group(4))
        try:
            dt_kst = now_kst.replace(month=month, day=day, hour=hour, minute=minute, second=0, microsecond=0)
            return dt_kst.astimezone(timezone.utc)
        except ValueError:
            return None

    # HH:mm
    match = re.match(r'^(\d{1,2}):(\d{2})$', text)
    if match:
        hour, minute = int(match.group(1)), int(match.group(2))
        try:
            dt_kst = now_kst.replace(hour=hour, minute=minute, second=0, microsecond=0)
            return dt_kst.astimezone(timezone.utc)
        except ValueError:
            return None

    return None


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
                # 현재 시점에서 이미 발송해야 할 알람 먼저 처리
                now = datetime.now(timezone.utc)
                due_alarms = await self.db.get_all_due_alarms(now)
                for alarm in due_alarms:
                    await self._send_alarm(alarm)

                # 다음 대기할 알람 조회
                next_alarm = await self.db.get_next_pending_alarm()
                if not next_alarm:
                    # 대기할 알람이 없으면 1시간마다 체크 (새 알람 등록 시 reschedule됨)
                    await asyncio.sleep(3600)
                    continue

                alarm_time = datetime.fromisoformat(next_alarm["alarm_time"])
                now = datetime.now(timezone.utc)
                wait_seconds = (alarm_time - now).total_seconds()

                if wait_seconds > 0:
                    logger.info(f"🐟 다음 알람까지 {wait_seconds:.0f}초 대기")
                    await asyncio.sleep(wait_seconds)

                # 발송 시점 도달 - 해당 시점의 모든 due 알람 처리
                now = datetime.now(timezone.utc)
                due_alarms = await self.db.get_all_due_alarms(now)
                for alarm in due_alarms:
                    await self._send_alarm(alarm)

            except asyncio.CancelledError:
                logger.info("🐟 알람 스케줄러 종료")
                return
            except Exception as e:
                logger.error(f"🐟 알람 스케줄러 오류: {e}")
                await asyncio.sleep(60)  # 오류 시 1분 후 재시도

    async def _send_alarm(self, alarm: dict):
        """DM으로 알람 발송"""
        user_id = alarm["discord_user_id"]
        alarm_id = alarm["id"]

        try:
            user = await self.bot.fetch_user(user_id)
            next_available = datetime.fromisoformat(alarm["next_available_time"])
            next_kst = next_available.astimezone(KST)
            now = datetime.now(timezone.utc)
            remaining = next_available - now

            alarm_desc = format_alarm_description(alarm["alarm_type"], alarm["alarm_value"])

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
            embed.set_footer(text=f"알람 설정: {alarm_desc}")

            await user.send(embed=embed)
            logger.info(f"🐟 알람 발송 완료: user={user_id}, 설정={alarm_desc}")

        except discord.Forbidden:
            logger.warning(f"🐟 DM 발송 실패 (DM 차단): user={user_id}")
        except Exception as e:
            logger.error(f"🐟 알람 발송 오류: user={user_id}, error={e}")

        # 성공/실패 관계없이 sent 처리 (무한 재시도 방지)
        await self.db.mark_alarm_sent(alarm_id)

    # ─── 명령어 ───

    @commands.command(name='붕어도움말', aliases=['붕어도움'])
    async def pianus_help(self, ctx):
        """붕어(피아누스) 관련 명령어 안내"""
        embed = discord.Embed(
            title="🐟 붕어(피아누스) 명령어 안내",
            description=f"피아누스는 {PIANUS_COOLDOWN_DAYS}일 쿨타임 보스입니다.",
            color=BOT_COLOR,
        )

        embed.add_field(
            name="📝 !붕어완료, !붕어완",
            value=(
                "클리어 시각을 기록합니다.\n"
                "• `!붕어완료` — 지금 시각 기준\n"
                "• `!붕어완료 21:00` — 오늘 21시\n"
                "• `!붕어완료 04/13 21:00` — 4월 13일 21시"
            ),
            inline=False,
        )
        embed.add_field(
            name="🔍 !붕어확인, !붕어",
            value="현재 상태와 다음 도전 가능 시각을 확인합니다.",
            inline=False,
        )
        embed.add_field(
            name="🔔 !붕어알람설정",
            value=(
                "DM으로 알람을 받습니다.\n"
                "• `!붕어알람설정 30분전`\n"
                "• `!붕어알람설정 2시간전`\n"
                "• `!붕어알람설정 당일9시`"
            ),
            inline=False,
        )
        embed.add_field(
            name="📋 !붕어알람목록",
            value="등록된 알람과 다음 발송 예정 시각을 확인합니다.",
            inline=False,
        )
        embed.add_field(
            name="🔕 !붕어알람삭제, !붕어알람취소",
            value="설정된 모든 알람을 삭제합니다.",
            inline=False,
        )

        embed.set_footer(text="새벽길드봇")
        await ctx.send(embed=embed)

    @commands.command(name='붕어완료', aliases=['붕어완'])
    async def pianus_clear(self, ctx, *, time_input: str = None):
        """클리어 시각 기록"""
        if time_input:
            clear_time = parse_time_input(time_input)
            if not clear_time:
                embed = discord.Embed(
                    title="❌ 시간 형식 오류",
                    description=(
                        "올바른 형식으로 입력해주세요.\n\n"
                        "• `!붕어완료 21:00` — 오늘 21시\n"
                        "• `!붕어완료 04/13 21:00` — 4월 13일 21시"
                    ),
                    color=0xFF3333,
                )
                await ctx.send(embed=embed)
                return
        else:
            clear_time = datetime.now(timezone.utc)

        result = await self.db.record_clear(ctx.author.id, clear_time)

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

        # 알람이 설정되어 있으면 재계산되었음을 안내
        alarms = await self.db.get_alarms(ctx.author.id)
        if alarms:
            alarm_descs = [format_alarm_description(a["alarm_type"], a["alarm_value"]) for a in alarms]
            embed.add_field(
                name="🔔 알람 재설정됨",
                value=", ".join(alarm_descs),
                inline=False,
            )

        embed.set_footer(text=f"요청자: {ctx.author.display_name}")
        await ctx.send(embed=embed)

        # 알람 스케줄러 갱신
        self._schedule_next_alarm()

    @commands.command(name='붕어확인', aliases=['붕어'])
    async def pianus_check(self, ctx):
        """현재 상태 확인"""
        record = await self.db.get_record(ctx.author.id)

        if not record:
            embed = discord.Embed(
                title="🐟 붕어 기록 없음",
                description="아직 클리어 기록이 없습니다.\n`!붕어완료`로 기록을 시작하세요!",
                color=BOT_COLOR,
            )
            await ctx.send(embed=embed)
            return

        now = datetime.now(timezone.utc)
        next_available = record["next_available_time"]
        clear_kst = record["last_clear_time"].astimezone(KST)
        next_kst = next_available.astimezone(KST)
        remaining = next_available - now

        if remaining.total_seconds() <= 0:
            status = "✅ 지금 도전 가능!"
            status_color = 0x00CC66
        else:
            status = f"⏳ {format_remaining(remaining)} 남음"
            status_color = BOT_COLOR

        embed = discord.Embed(
            title=f"🐟 {ctx.author.display_name}님의 붕어 현황",
            description=status,
            color=status_color,
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

        # 알람 정보
        alarms = await self.db.get_alarms(ctx.author.id)
        if alarms:
            alarm_lines = []
            for a in alarms:
                desc = format_alarm_description(a["alarm_type"], a["alarm_value"])
                sent = "✅" if a["alarm_sent"] else "⏳"
                alarm_lines.append(f"{sent} {desc}")
            embed.add_field(
                name="🔔 알람 설정",
                value="\n".join(alarm_lines),
                inline=False,
            )
        else:
            embed.add_field(
                name="🔔 알람 설정",
                value="없음 (`!붕어알람설정`으로 추가)",
                inline=False,
            )

        await ctx.send(embed=embed)

    @commands.command(name='붕어알람설정')
    async def pianus_alarm_set(self, ctx, *, alarm_input: str = None):
        """알람 설정"""
        if not alarm_input:
            embed = discord.Embed(
                title="❌ 알람 형식을 입력해주세요",
                description=(
                    "• `!붕어알람설정 30분전`\n"
                    "• `!붕어알람설정 2시간전`\n"
                    "• `!붕어알람설정 당일9시` — 도전 가능일 아침 9시"
                ),
                color=0xFF3333,
            )
            await ctx.send(embed=embed)
            return

        parsed = parse_alarm_input(alarm_input)
        if not parsed:
            embed = discord.Embed(
                title="❌ 알람 형식 오류",
                description=(
                    "올바른 형식으로 입력해주세요.\n\n"
                    "• `!붕어알람설정 30분전`\n"
                    "• `!붕어알람설정 2시간전`\n"
                    "• `!붕어알람설정 당일9시`"
                ),
                color=0xFF3333,
            )
            await ctx.send(embed=embed)
            return

        alarm_type, alarm_value = parsed

        # 클리어 기록 확인
        record = await self.db.get_record(ctx.author.id)
        if not record:
            await ctx.send("❌ 먼저 `!붕어완료`로 클리어 기록을 등록해주세요.")
            return

        # DM 발송 가능 여부 테스트
        try:
            test_embed = discord.Embed(
                title="🐟 붕어 알람 테스트",
                description="알람이 정상적으로 설정되었습니다! 이 DM으로 알람이 발송됩니다.",
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
        alarm_time = await self.db.add_alarm(ctx.author.id, alarm_type, alarm_value)
        alarm_desc = format_alarm_description(alarm_type, alarm_value)
        alarm_kst = alarm_time.astimezone(KST)

        embed = discord.Embed(
            title="🔔 붕어 알람 설정 완료!",
            color=BOT_COLOR,
        )
        embed.add_field(
            name="알람",
            value=alarm_desc,
            inline=True,
        )
        embed.add_field(
            name="다음 알람 시각",
            value=alarm_kst.strftime("%m/%d(%a) %H:%M KST"),
            inline=True,
        )
        embed.set_footer(text="테스트 DM을 확인해주세요!")
        await ctx.send(embed=embed)

        # 알람 스케줄러 갱신
        self._schedule_next_alarm()

    @commands.command(name='붕어알람목록')
    async def pianus_alarm_list(self, ctx):
        """등록된 알람 목록 확인"""
        alarms = await self.db.get_alarms(ctx.author.id)
        if not alarms:
            await ctx.send("ℹ️ 설정된 알람이 없습니다. `!붕어알람설정`으로 추가하세요.")
            return

        embed = discord.Embed(
            title=f"🔔 {ctx.author.display_name}님의 붕어 알람 목록",
            color=BOT_COLOR,
        )

        for a in alarms:
            desc = format_alarm_description(a["alarm_type"], a["alarm_value"])
            alarm_time = datetime.fromisoformat(a["alarm_time"]).astimezone(KST)
            sent = "✅ 발송 완료" if a["alarm_sent"] else f"⏳ {alarm_time.strftime('%m/%d(%a) %H:%M')} 예정"
            embed.add_field(
                name=f"🔹 {desc}",
                value=sent,
                inline=False,
            )

        embed.set_footer(text="알람은 DM으로 발송됩니다")
        await ctx.send(embed=embed)

    @commands.command(name='붕어알람삭제', aliases=['붕어알람취소'])
    async def pianus_alarm_remove(self, ctx):
        """모든 알람 삭제"""
        alarms = await self.db.get_alarms(ctx.author.id)
        if not alarms:
            await ctx.send("ℹ️ 설정된 알람이 없습니다.")
            return

        await self.db.remove_alarms(ctx.author.id)

        embed = discord.Embed(
            title="🔕 붕어 알람 삭제 완료",
            description=f"{len(alarms)}개의 알람이 삭제되었습니다.",
            color=BOT_COLOR,
        )
        await ctx.send(embed=embed)

        # 알람 스케줄러 갱신
        self._schedule_next_alarm()

    # ─── 에러 핸들러 ───

    @pianus_clear.error
    async def pianus_clear_error(self, ctx, error):
        if isinstance(error, commands.CommandInvokeError):
            await ctx.send("❌ 오류가 발생했습니다. 다시 시도해주세요.")


async def setup(bot):
    await bot.add_cog(PianusCommands(bot))
