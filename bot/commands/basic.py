"""
기본 명령어 모음
"""
import discord
from discord.ext import commands
from bot.config.settings import BOT_COLOR
import time
import random

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
            name="🍽️ !저메추, !저녁메뉴추천",
            value="저녁 메뉴를 랜덤으로 추천해줍니다.",
            inline=False
        )

        embed.add_field(
            name="🐟 !붕어",
            value="붕어(피아누스) 클리어 기록/확인.\n`!붕어취소` 기록 취소 | `!붕어알람` 알람 설정",
            inline=False
        )

        embed.set_footer(text="새벽길드봇")

        await ctx.send(embed=embed)

async def setup(bot):
    """Cog 로드 함수"""
    await bot.add_cog(BasicCommands(bot))