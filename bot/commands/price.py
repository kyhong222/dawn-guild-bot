"""아이템 시세 조회 명령어"""
import discord
from discord.ext import commands
import re
from bot.config.settings import BOT_COLOR
from bot.utils.mapleland import MaplelandAPI


class PriceCommands(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.api = MaplelandAPI()

    @commands.command(name='시세', aliases=['가격'])
    async def price_command(self, ctx, *, query: str):
        """아이템 시세 조회: !시세 아이템이름"""

        loading_msg = await ctx.send("🔍 아이템을 검색하고 있습니다...")

        try:
            # 필터 파싱 (공N, 합마N)
            filters = {}
            filter_text = ""

            # 공격력 필터: 공5, 공 5
            pad_match = re.match(r'^공\s*(\d+)\s*(.+)$', query)
            if pad_match:
                filters["pad"] = int(pad_match.group(1))
                query = pad_match.group(2).strip()
                filter_text = f"공격력 {filters['pad']}"

            # 합마 필터: 합마120, 합마 120
            hapma_match = re.match(r'^합마\s*(\d+)\s*(.+)$', query)
            if hapma_match:
                filters["hapma"] = int(hapma_match.group(1))
                query = hapma_match.group(2).strip()
                filter_text = f"합마 {filters['hapma']}"

            # 아이템 검색
            matches = await self.api.search_item(query)

            if not matches:
                await loading_msg.edit(content=f"❌ '{query}'와 일치하는 아이템을 찾을 수 없습니다.")
                return

            if len(matches) > 1:
                # 정확히 일치하는 아이템이 있으면 선택
                exact_match = None
                query_normalized = query.lower().replace(" ", "")
                for item in matches:
                    if item["itemName"].lower().replace(" ", "") == query_normalized:
                        exact_match = item
                        break

                if exact_match:
                    matches = [exact_match]
                else:
                    # 후보가 여러 개
                    embed = discord.Embed(
                        title=f"🔍 {len(matches)}개의 유사한 아이템이 있습니다",
                        description="좀 더 정확한 검색어를 입력해주세요.",
                        color=BOT_COLOR
                    )

                    # 최대 10개까지 표시
                    item_list = "\n".join([f"• {item['itemName']}" for item in matches[:10]])
                    if len(matches) > 10:
                        item_list += f"\n... 외 {len(matches) - 10}개"

                    embed.add_field(
                        name="검색 결과",
                        value=item_list,
                        inline=False
                    )

                    await loading_msg.edit(content="", embed=embed)
                    return

            # 아이템이 하나만 매칭됨
            item = matches[0]
            item_code = item["itemCode"]
            item_name = item["itemName"]

            await loading_msg.edit(content=f"🔍 '{item_name}' 시세를 조회하고 있습니다...")

            # 가격 정보 조회
            price_info = await self.api.get_price_summary(item_code, item_name, filters if filters else None)

            if "error" in price_info:
                await loading_msg.edit(content=f"❌ {price_info['error']}")
                return

            # 결과 임베드 생성
            title = f"💰 {item_name}"
            if filter_text:
                title += f" ({filter_text})"

            embed = discord.Embed(
                title=title,
                color=BOT_COLOR,
                timestamp=ctx.message.created_at
            )

            # 팝니다 최저가 3개
            if price_info["sell_items"]:
                sell_lines = []
                for item in price_info["sell_items"]:
                    line = f"• **{item['price']:,}** 메소"
                    if item['comment']:
                        line += f" - {item['comment']}"
                    sell_lines.append(line)
                sell_text = "\n".join(sell_lines)
                embed.add_field(
                    name=f"📤 팝니다 최저가 ({price_info['sell_count']}개 매물)",
                    value=sell_text,
                    inline=False
                )
            else:
                embed.add_field(
                    name="📤 팝니다",
                    value="현재 매물이 없습니다.",
                    inline=False
                )

            # 삽니다 최고가 3개
            if price_info["buy_items"]:
                buy_lines = []
                for item in price_info["buy_items"]:
                    line = f"• **{item['price']:,}** 메소"
                    if item['comment']:
                        line += f" - {item['comment']}"
                    buy_lines.append(line)
                buy_text = "\n".join(buy_lines)
                embed.add_field(
                    name=f"📥 삽니다 최고가 ({price_info['buy_count']}개 매물)",
                    value=buy_text,
                    inline=False
                )
            else:
                embed.add_field(
                    name="📥 삽니다",
                    value="현재 매물이 없습니다.",
                    inline=False
                )

            # 메랜지지 링크
            embed.add_field(
                name="🔗 링크",
                value=f"[메랜지지에서 확인하기](https://mapleland.gg/item/{item_code})",
                inline=False
            )

            embed.set_footer(text="메랜지지 실시간 데이터")

            await loading_msg.edit(content="", embed=embed)

        except Exception as e:
            await loading_msg.edit(content=f"❌ 오류가 발생했습니다: {str(e)}")

    @price_command.error
    async def price_error(self, ctx, error):
        if isinstance(error, commands.MissingRequiredArgument):
            await ctx.send("❌ 사용법: `!시세 아이템이름`\n예시: `!시세 파워엘릭서`")


async def setup(bot):
    await bot.add_cog(PriceCommands(bot))
