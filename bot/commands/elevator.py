import discord
from discord.ext import commands
from datetime import datetime


class Elevator(commands.Cog):
    """엘레베이터 시간표 명령어"""

    def __init__(self, bot):
        self.bot = bot

    def _get_state(self, minute: int) -> int:
        """분을 기준으로 상태 반환 (0-3)"""
        # 분 % 4:
        # 1: 아랫마을 대기
        # 2: 위로 운행중
        # 3: 루디브리엄 대기
        # 0: 아래로 운행중
        return minute % 4

    def _get_status_text(self, state: int) -> tuple[str, str]:
        """상태에 따른 텍스트 반환 (상태명, 방향)"""
        if state == 1:
            return "아랫마을 대기중", "루디브리엄 방면"
        elif state == 2:
            return "루디브리엄으로 운행중", ""
        elif state == 3:
            return "루디브리엄 대기중", "아랫마을 방면"
        else:  # state == 0
            return "아랫마을로 운행중", ""

    def _format_time(self, minutes: int, seconds: int) -> str:
        """시간 포맷팅"""
        if minutes == 0:
            return f"{seconds}초"
        elif seconds == 0:
            return f"{minutes}분"
        else:
            return f"{minutes}분 {seconds}초"

    def _get_next_boarding_times(self, now: datetime, going_up: bool, count: int = 3) -> list[datetime]:
        """다음 탑승 가능 시간 목록 반환"""
        # going_up=True: 아랫마을→루디 (state 1에서 탑승)
        # going_up=False: 루디→아랫마을 (state 3에서 탑승)
        target_state = 1 if going_up else 3

        times = []
        current_minute = now.minute
        current_hour = now.hour

        # 현재 상태가 탑승 가능하면 현재 시간 포함
        if self._get_state(current_minute) == target_state:
            times.append(now.replace(second=0, microsecond=0))

        # 다음 탑승 시간들 찾기
        minute = current_minute + 1
        hour = current_hour

        while len(times) < count:
            if minute >= 60:
                minute -= 60
                hour = (hour + 1) % 24

            if self._get_state(minute) == target_state:
                times.append(now.replace(hour=hour, minute=minute, second=0, microsecond=0))

            minute += 1

        return times

    @commands.command(name="엘레베이터", aliases=["엘베"])
    async def elevator(self, ctx):
        """루디브리엄 엘레베이터 시간표"""
        now = datetime.now()
        current_minute = now.minute
        current_second = now.second
        state = self._get_state(current_minute)

        status_text, direction = self._get_status_text(state)
        seconds_left = 60 - current_second

        # 임베드 생성
        embed = discord.Embed(
            title="🛗 엘레베이터 시간표",
            color=discord.Color.blue()
        )

        # 현재 상태
        if state == 1:  # 아랫마을 대기
            status_value = f"**{status_text}**\n⚠️ {seconds_left}초 후 출발! ({direction})"
        elif state == 3:  # 루디브리엄 대기
            status_value = f"**{status_text}**\n⚠️ {seconds_left}초 후 출발! ({direction})"
        elif state == 2:  # 위로 운행중
            status_value = f"**{status_text}**\n{seconds_left}초 후 루디브리엄 도착"
        else:  # 아래로 운행중
            status_value = f"**{status_text}**\n{seconds_left}초 후 아랫마을 도착"

        embed.add_field(name="📍 현재 상태", value=status_value, inline=False)

        # 아랫마을 → 루디브리엄
        up_times = self._get_next_boarding_times(now, going_up=True, count=3)
        up_text = ""

        if state == 1:  # 지금 탑승 가능
            up_text = f"**지금 탑승 가능!** ({seconds_left}초 후 출발)\n"
            up_text += "다음: " + ", ".join([t.strftime("%H:%M") for t in up_times[1:]])
        else:
            first_time = up_times[0]
            diff = (first_time - now.replace(microsecond=0)).total_seconds()
            minutes = int(diff // 60)
            seconds = int(diff % 60)
            up_text = f"다음 탑승: {first_time.strftime('%H:%M')} ({self._format_time(minutes, seconds)} 후)\n"
            up_text += "탑승 가능: " + ", ".join([t.strftime("%H:%M") for t in up_times])

        embed.add_field(name="🔼 아랫마을 → 루디브리엄", value=up_text, inline=False)

        # 루디브리엄 → 아랫마을
        down_times = self._get_next_boarding_times(now, going_up=False, count=3)
        down_text = ""

        if state == 3:  # 지금 탑승 가능
            down_text = f"**지금 탑승 가능!** ({seconds_left}초 후 출발)\n"
            down_text += "다음: " + ", ".join([t.strftime("%H:%M") for t in down_times[1:]])
        else:
            first_time = down_times[0]
            diff = (first_time - now.replace(microsecond=0)).total_seconds()
            minutes = int(diff // 60)
            seconds = int(diff % 60)
            down_text = f"다음 탑승: {first_time.strftime('%H:%M')} ({self._format_time(minutes, seconds)} 후)\n"
            down_text += "탑승 가능: " + ", ".join([t.strftime("%H:%M") for t in down_times])

        embed.add_field(name="🔽 루디브리엄 → 아랫마을", value=down_text, inline=False)

        # 푸터에 현재 시각
        embed.set_footer(text=f"현재 시각: {now.strftime('%H:%M:%S')}")

        await ctx.send(embed=embed)


async def setup(bot):
    await bot.add_cog(Elevator(bot))
