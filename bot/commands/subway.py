import discord
from discord.ext import commands
from datetime import datetime


class Subway(commands.Cog):
    """지하철 시간표 명령어"""

    def __init__(self, bot):
        self.bot = bot

    def _format_time(self, minutes: int, seconds: int) -> str:
        if minutes == 0:
            return f"{seconds}초"
        elif seconds == 0:
            return f"{minutes}분"
        else:
            return f"{minutes}분 {seconds}초"

    def _remaining(self, now: datetime, target_offset: int, cycle: int) -> tuple[int, int]:
        """현재 시각에서 다음 target_offset까지 남은 분/초 계산"""
        current_offset = now.minute % cycle
        current_second = now.second

        remaining_min = (target_offset - current_offset - 1) % cycle
        remaining_sec = 60 - current_second
        if remaining_sec == 60:
            remaining_sec = 0
            remaining_min = (target_offset - current_offset) % cycle

        return remaining_min, remaining_sec

    def _next_time(self, now: datetime, target_offset: int, cycle: int) -> str:
        """다음 target_offset 시각 반환"""
        minute = now.minute

        for i in range(cycle + 1):
            m = (minute + i) % 60
            if m % cycle == target_offset:
                h = (now.hour + (minute + i) // 60) % 24
                return f"{h:02d}:{m:02d}"

        return ""

    def _arrival_after_board(self, now: datetime, board_offset: int, cycle: int, board_to_arrive: int) -> str:
        """탑승 시각 기준 도착 시각 계산"""
        minute = now.minute
        for i in range(cycle + 1):
            m = (minute + i) % 60
            if m % cycle == board_offset:
                h = (now.hour + (minute + i + board_to_arrive) // 60) % 24
                arrive_m = (m + board_to_arrive) % 60
                return f"{h:02d}:{arrive_m:02d}"
        return ""

    def _status(self, now: datetime) -> tuple[str, str]:
        """지하철 상태 반환"""
        # 10분 주기, 탑승 offset 5~8, 마감 offset 9, 출발 offset 0, 도착 offset 1
        cycle = 10
        offset = now.minute % cycle

        # 탑승 시작 + 6분 = 도착 (5분 대기 + 1분 운행)
        next_board = self._next_time(now, 5, cycle)
        next_arrival = self._arrival_after_board(now, 5, cycle, 6)

        if 5 <= offset <= 8:
            # 탑승 가능
            close_min, close_sec = self._remaining(now, 9, cycle)
            arrival = self._arrival_after_board(now, 5, cycle, 6)
            status = f"🟢 탑승 가능 | {self._format_time(close_min, close_sec)} 후 마감 | {arrival} 도착"
        elif offset == 9:
            # 탑승 마감
            depart_min, depart_sec = self._remaining(now, 0, cycle)
            arrival = self._arrival_after_board(now, 5, cycle, 6)
            status = f"🟡 탑승 마감 | {self._format_time(depart_min, depart_sec)} 후 출발 | {arrival} 도착"
        else:
            # 탑승 불가 (offset 0-4)
            board_min, board_sec = self._remaining(now, 5, cycle)
            status = f"🔴 탑승 불가 | {self._format_time(board_min, board_sec)} 후 탑승 가능"

        detail = f"다음 탑승: {next_board} ({next_arrival} 도착)"
        return status, detail

    @commands.command(name="지하철")
    async def subway(self, ctx):
        """지하철 시간표"""
        now = datetime.now()

        status, detail = self._status(now)

        embed = discord.Embed(
            title="🚇 지하철 시간표",
            description="10분 주기 · 5분 전 탑승 · 1분 전 마감 · 운행 1분",
            color=discord.Color.dark_blue()
        )

        embed.add_field(
            name="📍 현재 상태",
            value=f"{status}\n{detail}",
            inline=False
        )

        embed.set_footer(text=f"현재 시각: {now.strftime('%H:%M:%S')}")

        await ctx.send(embed=embed)


async def setup(bot):
    await bot.add_cog(Subway(bot))
