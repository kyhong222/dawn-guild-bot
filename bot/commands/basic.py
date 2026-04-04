"""
기본 명령어 모음
"""
import discord
from discord.ext import commands
from bot.config.settings import BOT_COLOR
import time

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
            name="🏓 기본 명령어",
            value="`!핑` - 봇 응답속도 확인\n`!도움말` - 이 메시지 표시",
            inline=False
        )

        embed.add_field(
            name="💰 자리값 조회",
            value="`!자리값 맵이름` - 메랜샵 자리값 조회\n예시: `!자리값 블와둥`",
            inline=False
        )

        embed.set_footer(text="메랜샵 데이터 기반")
        
        await ctx.send(embed=embed)

async def setup(bot):
    """Cog 로드 함수"""
    await bot.add_cog(BasicCommands(bot))