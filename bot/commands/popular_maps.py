"""
인기 자리 맵 추천 명령어
"""
import discord
from discord.ext import commands
from bot.config.settings import BOT_COLOR
import aiohttp

class PopularMapsCommands(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @commands.command(name='인기맵', aliases=['핫맵', '인기자리'])
    async def popular_maps(self, ctx):
        """현재 가장 활발하게 거래되는 맵들을 보여줍니다"""
        
        try:
            async with aiohttp.ClientSession() as session:
                headers = {
                    'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36',
                    'Accept': 'application/json, text/plain, */*',
                    'Origin': 'https://mashop.kr',
                    'Referer': 'https://mashop.kr/'
                }
                
                async with session.get("https://api.mashop.kr/api/jari/recent", headers=headers, timeout=10) as response:
                    if response.status == 200:
                        data = await response.json()
                        
                        # 맵별 거래 빈도 계산
                        map_count = {}
                        for item in data[:100]:  # 최신 100개
                            map_name = item.get('mapName', '')
                            if map_name:
                                map_count[map_name] = map_count.get(map_name, 0) + 1
                        
                        # 빈도순 정렬
                        sorted_maps = sorted(map_count.items(), key=lambda x: x[1], reverse=True)
                        
                        embed = discord.Embed(
                            title="🔥 현재 핫한 자리 맵",
                            description="최근 100개 거래 기준으로 가장 활발한 맵들입니다!",
                            color=BOT_COLOR,
                            timestamp=ctx.message.created_at
                        )
                        
                        if sorted_maps:
                            hot_maps_text = ""
                            for i, (map_name, count) in enumerate(sorted_maps[:10], 1):
                                hot_maps_text += f"{i:2d}. **{map_name}** ({count}회)\n"
                            
                            embed.add_field(
                                name="📊 거래 활발한 맵 TOP 10",
                                value=hot_maps_text,
                                inline=False
                            )
                        else:
                            embed.add_field(
                                name="📭 안내",
                                value="현재 활발한 거래가 없습니다.",
                                inline=False
                            )
                        
                        embed.add_field(
                            name="💡 사용법",
                            value="`!자리값 맵이름`으로 자세한 가격을 확인하세요!",
                            inline=False
                        )
                        
                        embed.set_footer(text="메랜샵 실시간 데이터 기반")
                        
                        await ctx.send(embed=embed)
                    else:
                        await ctx.send("❌ 인기 맵 정보를 가져올 수 없습니다.")
                        
        except Exception as e:
            await ctx.send(f"❌ 인기 맵 조회 중 오류 발생: {str(e)}")

async def setup(bot):
    """Cog 로드 함수"""
    await bot.add_cog(PopularMapsCommands(bot))