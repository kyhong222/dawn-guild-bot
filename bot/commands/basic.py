"""
기본 명령어 모음
"""
import discord
from discord.ext import commands
from bot.config.settings import BOT_COLOR
import time
import random
from datetime import date

class BasicCommands(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @commands.command(name='핑', aliases=['ping'])
    async def ping_command(self, ctx):
        """봇의 응답 속도를 확인합니다"""
        start_time = time.time()
        
        # 임시 메시지 전송
        message = await ctx.send("🏓 퐁! 측정 중...")
        
        # 응답 시간 계산
        end_time = time.time()
        response_time = round((end_time - start_time) * 1000)
        bot_latency = round(self.bot.latency * 1000)
        
        # 임베드 메시지로 업데이트
        embed = discord.Embed(
            title="🏓 퐁!",
            color=BOT_COLOR,
            timestamp=ctx.message.created_at
        )
        embed.add_field(
            name="📡 봇 지연시간", 
            value=f"{bot_latency}ms", 
            inline=True
        )
        embed.add_field(
            name="🔄 응답 시간", 
            value=f"{response_time}ms", 
            inline=True
        )
        response_id = int(time.time() * 1000) % 100000
        embed.set_footer(text=f"새벽길드봇 #{response_id} | 요청자: {ctx.author.display_name}")
        
        await message.edit(content="", embed=embed)

    @commands.command(name='주사위', aliases=['굴려'])
    async def dice_command(self, ctx):
        """1~100 사이 랜덤 숫자"""
        result = random.randint(1, 100)
        await ctx.send(f"🎲 **{ctx.author.display_name}**님이 주사위를 굴려 **{result}**이(가) 나왔습니다!")

    @commands.command(name='점메추', aliases=['점심메뉴추천'])
    async def lunch_command(self, ctx):
        """점심 메뉴 랜덤 추천 (든든한 메뉴 위주)"""
        menus = [
            "🍖 삼겹살", "🥩 갈비", "🍛 카레 돈까스", "🍚 김치찌개 백반",
            "🥘 된장찌개 정식", "🍜 짬뽕", "🍲 부대찌개", "🐙 족발/보쌈",
            "🍳 제육볶음 정식", "🥩 스테이크 덮밥", "🍖 감자탕", "🍜 칼국수",
            "🥘 순두부찌개 정식", "🍚 불고기 백반", "🍝 크림파스타",
            "🍔 수제버거", "🍗 치킨 도시락", "🥟 왕만두", "🍜 짜장면",
            "🍲 샤브샤브", "🍱 한식 정식", "🐟 생선구이 정식", "🍛 돈까스",
            "🥩 소고기국밥", "🍖 뼈해장국", "🍚 쌈밥 정식", "🥘 육개장",
            "🍜 우동", "🍲 김치찜", "🍖 갈비탕",
        ]
        pick = random.choice(menus)
        await ctx.send(f"🍽️ **{ctx.author.display_name}**님의 오늘 점심은... **{pick}** 어떠세요?")

    @commands.command(name='저메추', aliases=['저녁메뉴추천'])
    async def dinner_command(self, ctx):
        """저녁 메뉴 랜덤 추천"""
        menus = [
            "🍕 피자", "🍔 햄버거", "🍜 라면", "🍣 초밥", "🍗 치킨",
            "🥘 찌개", "🍖 삼겹살", "🍲 샤브샤브", "🥩 스테이크", "🍝 파스타",
            "🌮 타코", "🥟 만두", "🍛 카레", "🥗 샐러드", "🍱 도시락",
            "🐟 회", "🥓 김치찌개", "🍚 비빔밥", "🥘 된장찌개", "🍜 쌀국수",
            "🧆 떡볶이", "🥪 샌드위치", "🍢 오뎅", "🥩 갈비", "🍲 부대찌개",
            "🐙 족발/보쌈", "🍳 제육볶음", "🥘 순두부찌개", "🍜 짜장면", "🍜 짬뽕",
        ]
        pick = random.choice(menus)
        await ctx.send(f"🍽️ **{ctx.author.display_name}**님의 오늘 저녁은... **{pick}** 어떠세요?")

    @commands.command(name='안주추천', aliases=['안주', '술안주'])
    async def snack_command(self, ctx):
        """술안주 랜덤 추천"""
        menus = [
            "🍗 치킨", "🐙 족발", "🥓 보쌈", "🐟 회/사시미", "🥩 곱창",
            "🍖 삼겹살", "🥟 만두", "🍢 오뎅탕", "🍳 계란말이",
            "🦑 마른오징어", "🍕 피자", "🥩 육회",
            "🐔 닭발", "🐙 낙지볶음", "🥘 김치전", "🧆 떡볶이", "🍖 양꼬치",
            "🐚 조개구이", "🥩 갈비", "🍳 두부김치", "🐟 광어회", "🍖 대창",
            "🦐 새우튀김", "🥗 골뱅이소면", "🐙 쭈꾸미", "🍢 어묵탕",
        ]
        pick = random.choice(menus)
        await ctx.send(f"🍺 **{ctx.author.display_name}**님의 오늘 안주는... **{pick}** 어떠세요?")

    @commands.command(name='오늘의운세', aliases=['운세'])
    async def fortune_command(self, ctx):
        """오늘의 운세 (유저별 하루 고정)"""
        # 디코ID * 날짜 기반 시드 → 같은 날 같은 유저는 항상 같은 결과
        today = date.today()
        seed = ctx.author.id * (today.year * 10000 + today.month * 100 + today.day)
        rng = random.Random(seed)

        # 운세 등급 가중 랜덤 (대길~소길 확률 높게, 대흉 낮게)
        # 대길15% / 길25% / 소길30% / 평18% / 흉9% / 대흉3%
        # 등급: (이름, 코멘트, 점수 하한, 점수 상한)
        grades = [
            ("🌟 대길", "오늘은 모든 일이 술술 풀리는 날! 메소도 아이템도 대박!", 90, 100),
            ("✨ 길", "좋은 기운이 가득한 하루! 드랍 운이 좋을지도?", 75, 89),
            ("☀️ 소길", "무난하게 흘러가는 하루. 꾸준히 하면 좋은 일이!", 50, 74),
            ("🌥️ 평", "평범한 하루. 큰 욕심 부리지 않는 게 좋겠어요.", 25, 49),
            ("🌧️ 흉", "조금 조심해야 할 하루. 강화는 내일 하는 게...", 10, 24),
            ("⛈️ 대흉", "오늘은 쉬어가는 날로! 강화/주문서는 절대 금지!", 1, 9),
        ]
        weights = [15, 25, 30, 18, 9, 3]
        grade, comment, score_min, score_max = rng.choices(grades, weights=weights, k=1)[0]
        luck = rng.randint(score_min, score_max)

        # 오늘의 럭키 넘버
        lucky_number = rng.randint(1, 100)

        embed = discord.Embed(
            title=f"🔮 {ctx.author.display_name}님의 오늘의 운세",
            description=f"**{grade}** ({luck}점)",
            color=BOT_COLOR,
        )
        embed.add_field(name="💬 한마디", value=comment, inline=False)
        embed.add_field(name="🔢 럭키 넘버", value=str(lucky_number), inline=True)
        embed.set_footer(text=f"{today.strftime('%Y년 %m월 %d일')} 운세")

        await ctx.send(embed=embed)

    @commands.command(name='도움말', aliases=['명령어'])
    async def help_command(self, ctx):
        """사용 가능한 명령어 목록을 표시합니다"""
        embed = discord.Embed(
            title="🌅 새벽 길드봇 명령어",
            description="사용 가능한 명령어들입니다.",
            color=BOT_COLOR,
            timestamp=ctx.message.created_at
        )
        
        embed.add_field(
            name="🎲 !주사위, !굴려",
            value="1~100 사이 랜덤 숫자를 뽑습니다.",
            inline=False
        )

        embed.add_field(
            name="💰 !자리, !자리값",
            value="메랜샵에서 자리값을 검색합니다.\n예시: `!자리 남둥`",
            inline=False
        )

        embed.add_field(
            name="📊 !시세, !가격",
            value="메랜지지에서 매물의 가격을 검색합니다.\n예시: `!가격 파엘`",
            inline=False
        )

        embed.add_field(
            name="🛗 !엘레베이터, !엘베",
            value="루디브리엄 엘레베이터 시간표를 확인합니다.",
            inline=False
        )

        embed.add_field(
            name="⛵ !배",
            value="배 시간표를 확인합니다.",
            inline=False
        )

        embed.add_field(
            name="🚇 !지하철",
            value="지하철 시간표를 확인합니다.",
            inline=False
        )

        embed.add_field(
            name="📢 !고확, !마뇽, !월코",
            value="실시간 확성기 검색 (최근 1시간).\n예시: `!고확 파엘`",
            inline=False
        )

        embed.add_field(
            name="🔮 !운세, !오늘의운세",
            value="오늘의 운세를 확인합니다. (하루 고정)",
            inline=False
        )

        embed.add_field(
            name="🍽️ !점메추, !저메추, !안주추천",
            value="점심/저녁/안주 메뉴를 랜덤으로 추천해줍니다.",
            inline=False
        )

        embed.add_field(
            name="🐟 !붕어, !붕어알람",
            value="붕어(피아누스) 클리어 기록/확인 및 알람 설정.",
            inline=False
        )

        embed.add_field(
            name="⏰ !파풀, !파풀알람",
            value="파풀라투스 클리어 기록/확인 및 알람 설정.",
            inline=False
        )

        embed.add_field(
            name="📢 공지 알림",
            value="메이플랜드 공지사항 자동 알림 (5분 간격).\n`!공지확인`으로 수동 확인 가능.",
            inline=False
        )

        embed.set_footer(text="새벽길드봇")

        await ctx.send(embed=embed)

async def setup(bot):
    """Cog 로드 함수"""
    await bot.add_cog(BasicCommands(bot))