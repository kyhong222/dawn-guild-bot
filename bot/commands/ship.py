import discord
from discord.ext import commands
from datetime import datetime


class Ship(commands.Cog):
    """배 시간표 명령어"""

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
        """탑승 시각 기준 도착 시각 계산 (탑승 시각 + board_to_arrive분)"""
        minute = now.minute
        for i in range(cycle + 1):
            m = (minute + i) % 60
            if m % cycle == board_offset:
                h = (now.hour + (minute + i + board_to_arrive) // 60) % 24
                arrive_m = (m + board_to_arrive) % 60
                return f"{h:02d}:{arrive_m:02d}"
        return ""

    def _regular_status(self, now: datetime) -> tuple[str, str]:
        """일반 노선 (10분 주기) 상태 반환"""
        cycle = 10
        offset = now.minute % cycle

        next_board = self._next_time(now, 5, cycle)
        next_arrival = self._arrival_after_board(now, 5, cycle, 10)

        if 5 <= offset <= 9:
            # 탑승 가능
            close_min, close_sec = self._remaining(now, 0, cycle)
            arrival = self._arrival_after_board(now, 5, cycle, 10)
            status = f"🟢 탑승 가능 | {self._format_time(close_min, close_sec)} 후 마감 | {arrival} 도착"
        else:
            # 탑승 불가
            board_min, board_sec = self._remaining(now, 5, cycle)
            status = f"🔴 탑승 불가 | {self._format_time(board_min, board_sec)} 후 탑승 가능"

        detail = f"다음 탑승: {next_board} ({next_arrival} 도착)"
        return status, detail

    def _orbis_status(self, now: datetime) -> tuple[str, str]:
        """엘리니아-오르비스 (15분 주기) 상태 반환"""
        cycle = 15
        offset = now.minute % cycle

        next_board = self._next_time(now, 10, cycle)
        next_arrival = self._arrival_after_board(now, 10, cycle, 15)

        if 10 <= offset <= 13:
            # 탑승 가능
            close_min, close_sec = self._remaining(now, 14, cycle)
            arrival = self._arrival_after_board(now, 10, cycle, 15)
            status = f"🟢 탑승 가능 | {self._format_time(close_min, close_sec)} 후 마감 | {arrival} 도착"
        else:
            # 탑승 불가 (offset 14 or 0-9)
            board_min, board_sec = self._remaining(now, 10, cycle)
            status = f"🔴 탑승 불가 | {self._format_time(board_min, board_sec)} 후 탑승 가능"

        detail = f"다음 탑승: {next_board} ({next_arrival} 도착)"
        return status, detail

    @commands.command(name="배")
    async def ship(self, ctx):
        """배 시간표"""
        now = datetime.now()

        orbis_status, orbis_detail = self._orbis_status(now)
        regular_status, regular_detail = self._regular_status(now)

        embed = discord.Embed(
            title="⛵ 배 시간표",
            color=discord.Color.teal()
        )

        # 엘리니아 ↔ 오르비스
        embed.add_field(
            name="🚢 엘리니아 ↔ 오르비스 (15분 주기)",
            value=f"{orbis_status}\n{orbis_detail}",
            inline=False
        )

        # 일반 노선
        embed.add_field(
            name="🚤 기타 노선 (10분 주기)",
            value=f"{regular_status}\n{regular_detail}",
            inline=False
        )

        embed.set_footer(text=f"현재 시각: {now.strftime('%H:%M:%S')}")

        await ctx.send(embed=embed)


async def setup(bot):
    await bot.add_cog(Ship(bot))
