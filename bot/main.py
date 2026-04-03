import discord
from discord.ext import commands
import os
from dotenv import load_dotenv
import logging
from bot.config.settings import ALLOWED_CHANNELS, COMMAND_PREFIX

# 환경변수 로드
load_dotenv()

# 로깅 설정
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Intents 설정
intents = discord.Intents.default()
intents.message_content = True

# 봇 인스턴스 생성
bot = commands.Bot(command_prefix=COMMAND_PREFIX, intents=intents)

@bot.event
async def on_ready():
    logger.info(f'🌅 {bot.user}가 준비되었습니다!')
    logger.info(f'📊 {len(bot.guilds)}개 서버에서 활동 중')
    
    # 봇 상태 설정
    await bot.change_presence(
        activity=discord.Game(name="메이플랜드 새벽 길드")
    )

@bot.event
async def on_message(message):
    # 봇 자신의 메시지는 무시
    if message.author == bot.user:
        return
    
    # 허용된 채널 체크 (설정에서 비어있으면 모든 채널 허용)
    if ALLOWED_CHANNELS and str(message.channel.id) not in ALLOWED_CHANNELS:
        return
    
    # 명령어 처리
    await bot.process_commands(message)

@bot.event
async def on_command_error(ctx, error):
    """명령어 에러 핸들러"""
    if isinstance(error, commands.CommandNotFound):
        await ctx.send(f"❌ 알 수 없는 명령어입니다. `{COMMAND_PREFIX}도움말`을 확인해보세요!")
    elif isinstance(error, commands.MissingRequiredArgument):
        await ctx.send(f"❌ 명령어에 필요한 인수가 부족합니다.")
    else:
        logger.error(f"명령어 에러: {error}")
        await ctx.send("❌ 명령어 실행 중 오류가 발생했습니다.")

async def load_commands():
    """명령어 파일들을 동적으로 로드"""
    commands_dir = "bot/commands"
    
    for filename in os.listdir(commands_dir):
        if filename.endswith('.py') and not filename.startswith('__'):
            module_name = f"bot.commands.{filename[:-3]}"
            try:
                await bot.load_extension(module_name)
                logger.info(f"✅ 명령어 로드: {filename}")
            except Exception as e:
                logger.error(f"❌ 명령어 로드 실패 ({filename}): {e}")

async def main():
    """메인 실행 함수"""
    try:
        # 명령어 로드
        await load_commands()
        
        # 봇 실행
        await bot.start(os.getenv('DISCORD_TOKEN'))
    except Exception as e:
        logger.error(f"봇 실행 중 오류: {e}")

if __name__ == "__main__":
    import asyncio
    asyncio.run(main())