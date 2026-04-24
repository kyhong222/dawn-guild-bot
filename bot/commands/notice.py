"""
메이플랜드 공지사항 알림 Cog
"""
import logging
import discord
from discord.ext import commands, tasks
from bot.config.settings import BOT_COLOR, NOTICE_CHANNEL_ID, NOTICE_ROLE_ID, NOTICE_CHECK_INTERVAL
from bot.utils.notice_scraper import init_db, check_new_notices, CATEGORY_EMOJI

logger = logging.getLogger(__name__)


class NoticeCommands(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    async def cog_load(self):
        await init_db()
        logger.info("📢 공지 알림 DB 초기화 완료")
        self.check_notices_loop.start()

    async def cog_unload(self):
        self.check_notices_loop.cancel()

    @tasks.loop(seconds=NOTICE_CHECK_INTERVAL)
    async def check_notices_loop(self):
        """주기적으로 공지사항 확인"""
        try:
            new_posts = await check_new_notices()

            if not new_posts:
                return

            channel = self.bot.get_channel(NOTICE_CHANNEL_ID)
            if not channel:
                logger.warning("📢 공지 알림 채널을 찾을 수 없습니다.")
                return

            for post in new_posts:
                emoji = CATEGORY_EMOJI.get(post["category"], "📢")

                embed = discord.Embed(
                    title=f"{emoji} [{post['category']}] {post['title']}",
                    url=post["url"],
                    color=BOT_COLOR,
                )
                embed.add_field(
                    name="📅 날짜",
                    value=post["createdAt"],
                    inline=True,
                )
                embed.set_footer(text="메이플랜드 공지사항")

                # @길드원 멘션 + 임베드
                await channel.send(
                    content=f"<@&{NOTICE_ROLE_ID}> 새 공지가 올라왔습니다!",
                    embed=embed,
                )
                logger.info(f"📢 공지 알림 발송: [{post['category']}] {post['title']}")

        except Exception as e:
            logger.error(f"📢 공지 확인 오류: {e}")

    @check_notices_loop.before_loop
    async def before_check(self):
        await self.bot.wait_until_ready()

    @commands.command(name="공지확인")
    async def manual_check(self, ctx):
        """수동으로 공지 확인"""
        msg = await ctx.send("🔍 공지사항을 확인하고 있습니다...")

        new_posts = await check_new_notices()

        if not new_posts:
            await msg.edit(content="✅ 새로운 공지가 없습니다.")
            return

        await msg.edit(content=f"📢 새 공지 {len(new_posts)}건을 발견했습니다!")

        for post in new_posts:
            emoji = CATEGORY_EMOJI.get(post["category"], "📢")
            embed = discord.Embed(
                title=f"{emoji} [{post['category']}] {post['title']}",
                url=post["url"],
                color=BOT_COLOR,
            )
            embed.add_field(name="📅 날짜", value=post["createdAt"], inline=True)
            embed.set_footer(text="메이플랜드 공지사항")

            await ctx.send(
                content=f"<@&{NOTICE_ROLE_ID}> 새 공지가 올라왔습니다!",
                embed=embed,
            )


async def setup(bot):
    await bot.add_cog(NoticeCommands(bot))
