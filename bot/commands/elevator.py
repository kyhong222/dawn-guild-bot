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

        # 다음 탑승 시간 계산
        up_times = self._get_next_boarding_times(now, going_up=True, count=3)
        down_times = self._get_next_boarding_times(now, going_up=False, count=3)

        # 루디브리엄 상태 텍스트
        if state == 3:  # 루디 대기중
            ludi_status = f"**{seconds_left}초 후 출발**"
        else:
            first_down = down_times[0]
            diff = (first_down - now.replace(microsecond=0)).total_seconds()
            mins, secs = int(diff // 60), int(diff % 60)
            ludi_status = f"다음 탑승: {self._format_time(mins, secs)} 후"

        # 아랫마을 상태 텍스트
        if state == 1:  # 아랫마을 대기중
            arae_status = f"**{seconds_left}초 후 출발**"
        else:
            first_up = up_times[0]
            diff = (first_up - now.replace(microsecond=0)).total_seconds()
            mins, secs = int(diff // 60), int(diff % 60)
            arae_status = f"다음 탑승: {self._format_time(mins, secs)} 후"

        # 현재 상태 텍스트 (가운데 표시용)
        if state == 1:
            center_status = f"[ 아랫마을 대기중 ]"
        elif state == 2:
            center_status = f"[ ▲ 상승중 {seconds_left}초 ]"
        elif state == 3:
            center_status = f"[ 루디브리엄 대기중 ]"
        else:
            center_status = f"[ ▼ 하강중 {seconds_left}초 ]"

        # 시각적 레이아웃 구성
        down_times_str = ", ".join([t.strftime("%H:%M") for t in down_times])
        up_times_str = ", ".join([t.strftime("%H:%M") for t in up_times])

        layout = f"""```
┌─────────────────────────┐
│  루디브리엄 ({ludi_status})
│  탑승 가능: {down_times_str}
│          │
│          ▼
│  {center_status}
│          ▲
│          │
│  탑승 가능: {up_times_str}
│  아랫마을 ({arae_status})
└─────────────────────────┘
```"""

        # 임베드 생성
        embed = discord.Embed(
            title="🛗 엘레베이터 시간표",
            color=discord.Color.blue()
        )

        embed.add_field(name="", value=layout, inline=False)
        embed.set_footer(text=f"현재 시각: {now.strftime('%H:%M:%S')}")

        await ctx.send(embed=embed)


async def setup(bot):
    await bot.add_cog(Elevator(bot))
