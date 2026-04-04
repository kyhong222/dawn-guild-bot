"""자리값 조회 명령어"""
import discord
from discord.ext import commands
from urllib.parse import quote
from bot.config.settings import BOT_COLOR
from bot.utils.mashop import MashopAPI


class JariCommands(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.api = MashopAPI()

    @commands.command(name='자리값', aliases=['자리'])
    async def jari_command(self, ctx, *, query: str):
        """자리값 조회: !자리값 맵이름"""

        # 로딩 메시지
        loading_msg = await ctx.send("🔍 맵을 검색하고 있습니다...")

        try:
            # 맵 검색
            matches = await self.api.search_map(query)

            if not matches:
                await loading_msg.edit(content=f"❌ '{query}'와 일치하는 맵을 찾을 수 없습니다.")
                return

            if len(matches) > 1:
                # 후보가 여러 개
                embed = discord.Embed(
                    title=f"🔍 {len(matches)}개의 유사한 맵이 있습니다",
                    description="좀 더 정확한 검색어를 입력해주세요.",
                    color=BOT_COLOR
                )

                # 최대 10개까지 표시
                map_list = "\n".join([f"• {m}" for m in matches[:10]])
                if len(matches) > 10:
                    map_list += f"\n... 외 {len(matches) - 10}개"

                embed.add_field(
                    name="검색 결과",
                    value=map_list,
                    inline=False
                )

                await loading_msg.edit(content="", embed=embed)
                return

            # 맵이 하나만 매칭됨
            map_name = matches[0]
            await loading_msg.edit(content=f"🔍 '{map_name}' 자리값을 조회하고 있습니다...")

            # 가격 정보 조회
            price_info = await self.api.get_price_summary(map_name)

            if "error" in price_info:
                await loading_msg.edit(content=f"❌ {price_info['error']}")
                return

            # 결과 임베드 생성
            embed = discord.Embed(
                title=f"💰 {map_name}",
                color=BOT_COLOR,
                timestamp=ctx.message.created_at
            )

            # 팝니다 정보
            if price_info["sell_items"]:
                sell_lines = []
                for item in price_info["sell_items"]:
                    line = f"• **{item['price']}만**"
                    if item['comment']:
                        line += f" - {item['comment']}"
                    sell_lines.append(line)
                sell_text = "\n".join(sell_lines)
                embed.add_field(
                    name=f"📤 팝니다(최근 {len(price_info['sell_items'])}개) - 평균: {price_info['sell_avg']}만 메소",
                    value=sell_text,
                    inline=False
                )
            else:
                embed.add_field(
                    name="📤 팝니다",
                    value="현재 매물이 없습니다.",
                    inline=False
                )

            # 삽니다 정보
            if price_info["buy_items"]:
                buy_lines = []
                for item in price_info["buy_items"]:
                    line = f"• **{item['price']}만**"
                    if item['comment']:
                        line += f" - {item['comment']}"
                    buy_lines.append(line)
                buy_text = "\n".join(buy_lines)
                embed.add_field(
                    name=f"📥 삽니다(최근 {len(price_info['buy_items'])}개) - 평균: {price_info['buy_avg']}만 메소",
                    value=buy_text,
                    inline=False
                )
            else:
                embed.add_field(
                    name="📥 삽니다",
                    value="현재 매물이 없습니다.",
                    inline=False
                )

            # 메랜샵 링크
            mashop_url = f"https://mashop.kr/jari/{quote(map_name)}"
            embed.add_field(
                name="🔗 링크",
                value=f"[메랜샵에서 확인하기]({mashop_url})",
                inline=False
            )

            embed.set_footer(text="메랜샵 실시간 데이터")

            await loading_msg.edit(content="", embed=embed)

        except Exception as e:
            await loading_msg.edit(content=f"❌ 오류가 발생했습니다: {str(e)}")

    @jari_command.error
    async def jari_error(self, ctx, error):
        if isinstance(error, commands.MissingRequiredArgument):
            await ctx.send("❌ 사용법: `!자리값 맵이름`\n예시: `!자리값 블와둥`")


async def setup(bot):
    await bot.add_cog(JariCommands(bot))
