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
# 필요한 경우에만 privileged intents 활성화

# 봇 인스턴스 생성
bot = commands.Bot(command_prefix=COMMAND_PREFIX, intents=intents)

@bot.event
async def on_ready():
    import os
    import time
    
    start_time = time.strftime("%Y-%m-%d %H:%M:%S")
    process_id = os.getpid()
    
    logger.info(f'🌅 {bot.user}가 준비되었습니다! (PID: {process_id})')
    logger.info(f'📊 {len(bot.guilds)}개 서버에서 활동 중')
    logger.info(f'⏰ 시작 시간: {start_time}')
    
    # 봇 상태 설정
    await bot.change_presence(
        activity=discord.Game(name=f"메이플랜드 새벽 길드 | PID:{process_id}")
    )

# 중복 처리 방지를 위한 메시지 캐시
processed_messages = set()

@bot.event
async def on_message(message):
    # 봇 자신의 메시지는 무시
    if message.author == bot.user:
        return
    
    # 중복 처리 방지 (같은 메시지 ID)
    if message.id in processed_messages:
        logger.warning(f"⚠️ 중복 메시지 처리 시도 무시: {message.id}")
        return
    
    # 서버별 허용 채널 체크
    if message.guild and ALLOWED_CHANNELS:
        guild_id = message.guild.id
        if guild_id in ALLOWED_CHANNELS:
            # 해당 서버에 설정이 있으면 허용된 채널만 통과
            if message.channel.id not in ALLOWED_CHANNELS[guild_id]:
                return
        # 서버 설정이 없으면 모든 채널 허용
    
    # 명령어인 경우 로깅 및 캐시 추가
    if message.content.startswith(COMMAND_PREFIX):
        processed_messages.add(message.id)
        logger.info(f"📝 명령어 처리: {message.content[:50]} (User: {message.author}, Channel: {message.channel.id})")
        
        # 캐시 크기 제한 (최근 1000개만 유지)
        if len(processed_messages) > 1000:
            processed_messages.clear()
    
    # 명령어 처리
    await bot.process_commands(message)

@bot.event 
async def on_command_completion(ctx):
    """명령어 완료 시 로깅"""
    logger.info(f"✅ 명령어 완료: {ctx.command.name} (User: {ctx.author}, Channel: {ctx.channel.id})")

@bot.event
async def on_command_error(ctx, error):
    """명령어 에러 핸들러"""
    logger.error(f"❌ 명령어 에러 ({ctx.command}): {error}")
    
    if isinstance(error, commands.CommandNotFound):
        await ctx.send(f"❌ 알 수 없는 명령어입니다. `{COMMAND_PREFIX}도움말`을 확인해보세요!")
    elif isinstance(error, commands.MissingRequiredArgument):
        await ctx.send(f"❌ 명령어에 필요한 인수가 부족합니다.")
    else:
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
    import sys
    import signal
    
    # 중복 실행 방지
    def signal_handler(sig, frame):
        logger.info("봇 종료 신호를 받았습니다.")
        sys.exit(0)
    
    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)
    
    try:
        logger.info("🚀 새벽길드봇 시작 중...")
        asyncio.run(main())
    except KeyboardInterrupt:
        logger.info("👋 봇이 정상적으로 종료되었습니다.")
    except Exception as e:
        logger.error(f"❌ 봇 실행 중 치명적 오류: {e}")
        sys.exit(1)