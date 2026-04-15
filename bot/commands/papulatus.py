"""
파풀라투스 알람 명령어 — 24시간 쿨타임
"""
import asyncio
import re
import logging
import discord
from discord.ext import commands
from datetime import datetime, timezone, timedelta
from bot.config.settings import BOT_COLOR
from bot.utils.boss_db import BossDB

logger = logging.getLogger(__name__)

KST = timezone(timedelta(hours=9))
COOLDOWN_HOURS = 24
BOSS_NAME = "파풀라투스"
BOSS_EMOJI = "⏰"
CMD_PREFIX = "파풀"


def format_remaining(td: timedelta) -> str:
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


def parse_time(text: str):
    text = text.strip()
    now_kst = datetime.now(KST)
    match = re.match(r'^(\d{1,2})/(\d{1,2})\s+(\d{1,2}):(\d{2})$', text)
    if match:
        try:
            dt = now_kst.replace(month=int(match.group(1)), day=int(match.group(2)),
                                 hour=int(match.group(3)), minute=int(match.group(4)), second=0, microsecond=0)
            return dt.astimezone(timezone.utc)
        except ValueError:
            return None
    match = re.match(r'^(\d{1,2}):(\d{2})$', text)
    if match:
        try:
            dt = now_kst.replace(hour=int(match.group(1)), minute=int(match.group(2)), second=0, microsecond=0)
            return dt.astimezone(timezone.utc)
        except ValueError:
            return None
    return None


# ─── View 클래스들 ───

class _BaseView(discord.ui.View):
    """공통 View 베이스"""

    def __init__(self, cog, ctx, timeout=60):
        super().__init__(timeout=timeout)
        self.cog = cog
        self.ctx = ctx
        self.message = None

    async def interaction_check(self, interaction: discord.Interaction) -> bool:
        if interaction.user.id != self.ctx.author.id:
            await interaction.response.send_message("❌ 본인만 누를 수 있습니다.", ephemeral=True)
            return False
        return True

    async def on_timeout(self):
        for item in self.children:
            item.disabled = True
        if self.message:
            try:
                await self.message.edit(view=self)
            except Exception:
                pass


class ClearConfirmView(_BaseView):
    """도전 가능 시 → 네 / 네(시간조정) / 아니요"""

    @discord.ui.button(label="네", style=discord.ButtonStyle.green, emoji="✅")
    async def confirm_now(self, interaction: discord.Interaction, button: discord.ui.Button):
        now = datetime.now(timezone.utc)
        result = await self.cog.db.record_clear(self.ctx.author.id, now)
        embed = self.cog._make_clear_embed(result, self.ctx)
        await interaction.response.edit_message(embed=embed, view=None)
        self.cog._schedule_next_alarm()
        self.stop()

    @discord.ui.button(label="네 (시간 조정)", style=discord.ButtonStyle.blurple, emoji="🕐")
    async def confirm_custom(self, interaction: discord.Interaction, button: discord.ui.Button):
        embed = discord.Embed(
            title=f"{BOSS_EMOJI} 클리어 시각을 입력해주세요",
            description=(
                f"`!{CMD_PREFIX} HH:MM` 또는 `!{CMD_PREFIX} MM/DD HH:MM`\n\n"
                f"예시:\n"
                f"• `!{CMD_PREFIX} 21:00` — 오늘 21시\n"
                f"• `!{CMD_PREFIX} 04/15 14:30` — 4월 15일 14시 30분"
            ),
            color=BOT_COLOR,
        )
        await interaction.response.edit_message(embed=embed, view=None)
        self.stop()

    @discord.ui.button(label="아니요", style=discord.ButtonStyle.grey, emoji="❌")
    async def cancel(self, interaction: discord.Interaction, button: discord.ui.Button):
        embed = discord.Embed(
            title=f"{BOSS_EMOJI} {self.ctx.author.display_name}님의 {BOSS_NAME} 현황",
            description="✅ **지금 도전 가능!**",
            color=0x00CC66,
        )
        await interaction.response.edit_message(embed=embed, view=None)
        self.stop()


class RecordManageView(_BaseView):
    """쿨타임 이내 → 기록 수정 / 기록 삭제"""

    @discord.ui.button(label="기록 수정", style=discord.ButtonStyle.blurple, emoji="✏️")
    async def edit_record(self, interaction: discord.Interaction, button: discord.ui.Button):
        embed = discord.Embed(
            title=f"{BOSS_EMOJI} 클리어 시각을 입력해주세요",
            description=(
                f"`!{CMD_PREFIX} HH:MM` 또는 `!{CMD_PREFIX} MM/DD HH:MM`\n\n"
                f"예시:\n"
                f"• `!{CMD_PREFIX} 21:00` — 오늘 21시\n"
                f"• `!{CMD_PREFIX} 04/15 14:30` — 4월 15일 14시 30분"
            ),
            color=BOT_COLOR,
        )
        await interaction.response.edit_message(embed=embed, view=None)
        self.stop()

    @discord.ui.button(label="기록 삭제", style=discord.ButtonStyle.red, emoji="🗑️")
    async def delete_record(self, interaction: discord.Interaction, button: discord.ui.Button):
        record = await self.cog.db.get_record(self.ctx.author.id)
        if record:
            clear_kst = record["last_clear_time"].astimezone(KST)
            await self.cog.db.delete_record(self.ctx.author.id)
            embed = discord.Embed(
                title=f"{BOSS_EMOJI} {BOSS_NAME} 기록 삭제 완료",
                description=f"**{clear_kst.strftime('%m/%d(%a) %H:%M')}** 클리어 기록이 삭제되었습니다.",
                color=BOT_COLOR,
            )
        else:
            embed = discord.Embed(title="ℹ️ 이미 삭제되었습니다.", color=BOT_COLOR)
        await interaction.response.edit_message(embed=embed, view=None)
        self.cog._schedule_next_alarm()
        self.stop()


class AlarmManageView(_BaseView):
    """알람 설정 후 → 알람 수정 / 알람 삭제"""

    @discord.ui.button(label="알람 수정", style=discord.ButtonStyle.blurple, emoji="✏️")
    async def edit_alarm(self, interaction: discord.Interaction, button: discord.ui.Button):
        embed = discord.Embed(
            title=f"{BOSS_EMOJI} 알람 시간을 변경해주세요",
            description=(
                f"`!{CMD_PREFIX}알람 N시간전`\n\n"
                f"예시:\n"
                f"• `!{CMD_PREFIX}알람 2시간전`\n"
                f"• `!{CMD_PREFIX}알람 12시간전`"
            ),
            color=BOT_COLOR,
        )
        await interaction.response.edit_message(embed=embed, view=None)
        self.stop()

    @discord.ui.button(label="알람 삭제", style=discord.ButtonStyle.red, emoji="🗑️")
    async def delete_alarm(self, interaction: discord.Interaction, button: discord.ui.Button):
        removed = await self.cog.db.remove_alarm(self.ctx.author.id)
        if removed:
            embed = discord.Embed(
                title=f"🔕 {BOSS_NAME} 알람 삭제 완료",
                description="알람이 삭제되었습니다. 더 이상 DM 알림이 가지 않습니다.",
                color=BOT_COLOR,
            )
        else:
            embed = discord.Embed(title="ℹ️ 이미 삭제되었습니다.", color=BOT_COLOR)
        await interaction.response.edit_message(embed=embed, view=None)
        self.cog._schedule_next_alarm()
        self.stop()


# ─── Cog ───

class PapulatusCommands(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.db = BossDB("papulatus", COOLDOWN_HOURS)
        self._alarm_task: asyncio.Task = None

    async def cog_load(self):
        await self.db.init_db()
        logger.info(f"{BOSS_EMOJI} {BOSS_NAME} DB 초기화 완료")
        self._schedule_next_alarm()

    async def cog_unload(self):
        if self._alarm_task and not self._alarm_task.done():
            self._alarm_task.cancel()

    # ─── 알람 스케줄러 ───

    def _schedule_next_alarm(self):
        if self._alarm_task and not self._alarm_task.done():
            self._alarm_task.cancel()
        self._alarm_task = asyncio.create_task(self._alarm_loop())

    async def _alarm_loop(self):
        await self.bot.wait_until_ready()
        while not self.bot.is_closed():
            try:
                now = datetime.now(timezone.utc)
                for alarm in await self.db.get_all_due_alarms(now):
                    await self._send_alarm(alarm)

                next_alarm = await self.db.get_next_pending_alarm()
                if not next_alarm:
                    await asyncio.sleep(3600)
                    continue

                wait = (datetime.fromisoformat(next_alarm["alarm_time"]) - datetime.now(timezone.utc)).total_seconds()
                if wait > 0:
                    await asyncio.sleep(wait)

                now = datetime.now(timezone.utc)
                for alarm in await self.db.get_all_due_alarms(now):
                    await self._send_alarm(alarm)
            except asyncio.CancelledError:
                return
            except Exception as e:
                logger.error(f"{BOSS_EMOJI} 알람 오류: {e}")
                await asyncio.sleep(60)

    async def _send_alarm(self, alarm: dict):
        user_id = alarm["discord_user_id"]
        try:
            user = await self.bot.fetch_user(user_id)
            next_available = datetime.fromisoformat(alarm["next_available_time"])
            remaining = next_available - datetime.now(timezone.utc)
            embed = discord.Embed(title=f"{BOSS_EMOJI} {BOSS_NAME} 알람!", color=BOT_COLOR)
            if remaining.total_seconds() <= 0:
                embed.description = f"{BOSS_NAME}에 도전할 수 있습니다!"
            else:
                embed.description = f"{BOSS_NAME} 도전 가능 시각이 다가오고 있습니다!\n남은 시간: **{format_remaining(remaining)}**"
            embed.add_field(name="⏰ 도전 가능 시각", value=next_available.astimezone(KST).strftime("%m/%d(%a) %H:%M KST"), inline=False)
            embed.set_footer(text=f"알람 설정: {alarm['hours_before']}시간 전")
            await user.send(embed=embed)
        except discord.Forbidden:
            logger.warning(f"{BOSS_EMOJI} DM 실패: user={user_id}")
        except Exception as e:
            logger.error(f"{BOSS_EMOJI} 알람 오류: user={user_id}, {e}")
        await self.db.mark_alarm_sent(user_id)

    # ─── 헬퍼 ───

    def _make_clear_embed(self, result: dict, ctx) -> discord.Embed:
        clear_kst = result["last_clear_time"].astimezone(KST)
        next_kst = result["next_available_time"].astimezone(KST)
        embed = discord.Embed(title=f"{BOSS_EMOJI} {BOSS_NAME} 클리어 기록 완료!", color=BOT_COLOR)
        embed.add_field(name="🕐 클리어 시각", value=clear_kst.strftime("%m/%d(%a) %H:%M KST"), inline=True)
        embed.add_field(name="⏰ 다음 도전 가능", value=next_kst.strftime("%m/%d(%a) %H:%M KST"), inline=True)
        embed.add_field(name="🔔 알람", value=f"`!{CMD_PREFIX}알람`으로 알람을 설정할 수 있습니다.", inline=False)
        embed.set_footer(text=f"요청자: {ctx.author.display_name}")
        return embed

    async def _send_clear_result(self, ctx, result: dict):
        clear_kst = result["last_clear_time"].astimezone(KST)
        next_kst = result["next_available_time"].astimezone(KST)
        embed = discord.Embed(title=f"{BOSS_EMOJI} {BOSS_NAME} 클리어 기록 완료!", color=BOT_COLOR)
        embed.add_field(name="🕐 클리어 시각", value=clear_kst.strftime("%m/%d(%a) %H:%M KST"), inline=True)
        embed.add_field(name="⏰ 다음 도전 가능", value=next_kst.strftime("%m/%d(%a) %H:%M KST"), inline=True)
        alarm = await self.db.get_alarm(ctx.author.id)
        if alarm:
            embed.add_field(name="🔔 알람", value=f"{alarm['hours_before']}시간 전 알람 재설정됨", inline=False)
        else:
            embed.add_field(name="🔔 알람", value=f"`!{CMD_PREFIX}알람`으로 알람을 설정할 수 있습니다.", inline=False)
        embed.set_footer(text=f"요청자: {ctx.author.display_name}")
        await ctx.send(embed=embed)
        self._schedule_next_alarm()

    # ─── 명령어 ───

    @commands.command(name='파풀')
    async def boss_command(self, ctx, *, time_input: str = None):
        record = await self.db.get_record(ctx.author.id)
        now = datetime.now(timezone.utc)

        # 특정 시각 직접 입력 → 바로 기록
        if time_input:
            clear_time = parse_time(time_input)
            if not clear_time:
                embed = discord.Embed(title="❌ 시간 형식 오류", description=(
                    f"올바른 형식으로 입력해주세요.\n\n"
                    f"• `!{CMD_PREFIX} 21:00` — 오늘 21시\n"
                    f"• `!{CMD_PREFIX} 04/13 21:00` — 특정일"
                ), color=0xFF3333)
                await ctx.send(embed=embed)
                return
            result = await self.db.record_clear(ctx.author.id, clear_time)
            return await self._send_clear_result(ctx, result)

        # 기록이 없거나 쿨타임 지남 → 현황 + 클리어 확인 버튼
        if not record or now >= record["next_available_time"]:
            embed = discord.Embed(
                title=f"{BOSS_EMOJI} {ctx.author.display_name}님의 {BOSS_NAME} 현황",
                description="✅ **지금 도전 가능!**",
                color=0x00CC66,
            )
            if record:
                clear_kst = record["last_clear_time"].astimezone(KST)
                embed.add_field(name="🕐 마지막 클리어", value=clear_kst.strftime("%m/%d(%a) %H:%M"), inline=True)

            alarm = await self.db.get_alarm(ctx.author.id)
            if alarm:
                embed.add_field(name=f"🔔 알람 ({alarm['hours_before']}시간 전)", value="다음 기록 시 재설정됨", inline=True)

            embed.add_field(
                name=f"🐟 {BOSS_NAME}를 방금 클리어 하였나요?",
                value="아래 버튼을 눌러주세요.",
                inline=False,
            )

            view = ClearConfirmView(self, ctx)
            msg = await ctx.send(embed=embed, view=view)
            view.message = msg

        # 쿨타임 이내 → 현황 + 기록 수정/삭제 버튼
        else:
            next_available = record["next_available_time"]
            remaining = next_available - now
            embed = discord.Embed(
                title=f"{BOSS_EMOJI} {ctx.author.display_name}님의 {BOSS_NAME} 현황",
                description=f"⏳ **{format_remaining(remaining)}** 남음", color=BOT_COLOR,
            )
            embed.add_field(name="🕐 마지막 클리어", value=record["last_clear_time"].astimezone(KST).strftime("%m/%d(%a) %H:%M"), inline=True)
            embed.add_field(name="⏰ 다음 도전 가능", value=next_available.astimezone(KST).strftime("%m/%d(%a) %H:%M"), inline=True)
            alarm = await self.db.get_alarm(ctx.author.id)
            if alarm:
                alarm_kst = datetime.fromisoformat(alarm["alarm_time"]).astimezone(KST)
                sent = "✅ 발송 완료" if alarm["alarm_sent"] else f"⏳ {alarm_kst.strftime('%m/%d %H:%M')} 발송 예정"
                embed.add_field(name=f"🔔 알람 ({alarm['hours_before']}시간 전)", value=sent, inline=False)
            else:
                embed.add_field(name="🔕 알람 미설정", value=f"`!{CMD_PREFIX}알람`으로 알람을 설정할 수 있습니다.", inline=False)

            view = RecordManageView(self, ctx)
            msg = await ctx.send(embed=embed, view=view)
            view.message = msg

    @commands.command(name='파풀알람', aliases=['파풀알림'])
    async def boss_alarm(self, ctx, *, alarm_input: str = None):
        record = await self.db.get_record(ctx.author.id)
        if not record:
            await ctx.send(f"❌ 먼저 `!{CMD_PREFIX}`로 클리어 기록을 등록해주세요.")
            return

        hours_before = 1
        if alarm_input:
            match = re.match(r'^(\d+)\s*시간\s*전$', alarm_input.strip())
            if not match:
                embed = discord.Embed(title="❌ 알람 형식 오류", description=(
                    f"올바른 형식으로 입력해주세요.\n\n"
                    f"• `!{CMD_PREFIX}알람` — 1시간 전 알람\n"
                    f"• `!{CMD_PREFIX}알람 2시간전`\n"
                    f"• `!{CMD_PREFIX}알람 12시간전`"
                ), color=0xFF3333)
                await ctx.send(embed=embed)
                return
            hours_before = int(match.group(1))
            if hours_before <= 0 or hours_before > COOLDOWN_HOURS:
                await ctx.send(f"❌ 1~{COOLDOWN_HOURS}시간 사이로 입력해주세요.")
                return

        # DM 발송 테스트
        try:
            test_embed = discord.Embed(title=f"{BOSS_EMOJI} {BOSS_NAME} 알람 테스트",
                                       description=f"알람이 설정되었습니다! {hours_before}시간 전에 이 DM으로 알림을 보내드립니다.", color=BOT_COLOR)
            await ctx.author.send(embed=test_embed)
        except discord.Forbidden:
            embed = discord.Embed(title="❌ DM을 보낼 수 없습니다", description=(
                "알람은 DM으로 발송됩니다.\n**서버 설정 → 개인정보 보호 → '서버 멤버가 보내는 다이렉트 메시지'**를 켜주세요."
            ), color=0xFF3333)
            await ctx.send(embed=embed)
            return

        # 알람 저장 및 결과 표시 + 버튼
        alarm_time = await self.db.set_alarm(ctx.author.id, hours_before)
        embed = discord.Embed(title=f"🔔 {BOSS_NAME} 알람 설정 완료!", color=BOT_COLOR)
        embed.add_field(name="알람", value=f"{hours_before}시간 전", inline=True)
        embed.add_field(name="다음 알람", value=alarm_time.astimezone(KST).strftime("%m/%d(%a) %H:%M KST"), inline=True)
        embed.set_footer(text="테스트 DM을 확인해주세요!")

        view = AlarmManageView(self, ctx)
        msg = await ctx.send(embed=embed, view=view)
        view.message = msg
        self._schedule_next_alarm()


async def setup(bot):
    await bot.add_cog(PapulatusCommands(bot))
