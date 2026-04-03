"""
메랜샵 자리값 조회 명령어
"""
import discord
from discord.ext import commands
from bot.config.settings import BOT_COLOR
from bot.utils.mashop_simple import SimpleMashopAPI
import asyncio
from typing import Dict

class MashopCommands(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.mashop_api = SimpleMashopAPI()

    @commands.command(name='자리값', aliases=['자리', '가격'])
    async def check_spot_price(self, ctx, *, map_name: str):
        """자리값 조회: !자리값 맵이름"""
        
        # 로딩 메시지
        loading_msg = await ctx.send("🔍 메랜샵에서 자리값을 검색하고 있습니다...")
        
        try:
            # 메랜샵에서 검색
            data = await self.mashop_api.search_map(map_name)
            
            if data.get("error"):
                await loading_msg.edit(content=f"❌ {data['error']}")
                return
            
            # 검색 결과가 애매한 경우 체크
            if self._is_ambiguous_result(data):
                await loading_msg.edit(
                    content="⚠️ 검색 결과가 여러 개입니다. 맵 이름을 조금 더 정확히 입력해주세요."
                )
                return
            
            # 결과 포맷팅
            price_summary = self.mashop_api.format_price_summary(data)
            
            # 임베드 생성
            map_display_name = data.get('map_name', map_name)
            embed = discord.Embed(
                title=f"📊 {map_display_name} 자리값",
                description=price_summary,
                color=BOT_COLOR,
                timestamp=ctx.message.created_at
            )
            
            # 상세 정보 추가
            sell_prices = data.get("sell_prices", [])
            buy_prices = data.get("buy_prices", [])
            
            if sell_prices:
                sell_text = " / ".join([f"{p}만" for p in sell_prices[:5]])
                embed.add_field(
                    name="💰 팝니다 (최신 5개)",
                    value=sell_text,
                    inline=False
                )
            
            if buy_prices:
                buy_text = " / ".join([f"{p}만" for p in buy_prices[:5]])
                embed.add_field(
                    name="💳 삽니다 (최신 5개)", 
                    value=buy_text,
                    inline=False
                )
            
            # 자리값 정보가 없는 경우 추가 안내
            if not sell_prices and not buy_prices:
                embed.add_field(
                    name="💡 참고",
                    value="현재 해당 맵의 자리값 거래가 활발하지 않습니다.\n메랜샵에서 직접 확인하거나 다른 맵을 검색해보세요!",
                    inline=False
                )
            
            # 출처 정보
            if data.get("source_url"):
                embed.add_field(
                    name="🔗 출처",
                    value=f"[메랜샵에서 확인하기]({data['source_url']})",
                    inline=False
                )
            
            import time
            response_id = int(time.time() * 1000) % 100000  # 고유 응답 ID
            embed.set_footer(text=f"💡 새벽길드봇 응답 #{response_id} | 메랜샵 실시간 데이터")
            
            await loading_msg.edit(content="", embed=embed)
            
        except asyncio.TimeoutError:
            await loading_msg.edit(content="⏰ 검색 시간이 초과되었습니다. 다시 시도해주세요.")
            
        except Exception as e:
            await loading_msg.edit(content=f"❌ 자리값 검색 중 오류가 발생했습니다: {str(e)}")
    
    def _is_ambiguous_result(self, data: Dict) -> bool:
        """검색 결과가 애매한지 확인"""
        # 실제 API에서 multiple results를 체크하는 로직
        # 지금은 임시로 False 반환
        return False
    
    @commands.command(name='자리값도움말')
    async def spot_price_help(self, ctx):
        """자리값 명령어 도움말"""
        embed = discord.Embed(
            title="📊 자리값 조회 도움말",
            color=BOT_COLOR,
            timestamp=ctx.message.created_at
        )
        
        embed.add_field(
            name="🔍 사용법",
            value="`!자리값 맵이름`\n`!자리 맵이름`\n`!가격 맵이름`",
            inline=False
        )
        
        embed.add_field(
            name="📝 예시",
            value="`!자리값 죽둥`\n`!자리값 죽은 용의 둥지`\n`!자리값 페리온`",
            inline=False
        )
        
        embed.add_field(
            name="💡 팁",
            value="• 줄임말로 검색 가능 (죽둥, 페리 등)\n• 정확한 맵 이름일수록 정확한 결과\n• 검색 결과가 여러 개면 더 정확히 입력",
            inline=False
        )
        
        embed.set_footer(text="메랜샵(mashop.kr) 데이터 기반")
        
        await ctx.send(embed=embed)

async def setup(bot):
    """Cog 로드 함수"""
    await bot.add_cog(MashopCommands(bot))