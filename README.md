# 🌅 새벽 길드봇

메이플랜드 새벽 길드를 위한 Python 디스코드 봇입니다.

## 🚀 설치 및 실행

### 1. Python 가상환경 생성 (권장)
```bash
python -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate
```

### 2. 의존성 설치
```bash
pip install -r requirements.txt
```

### 3. 환경변수 설정
`.env.example`을 참고하여 `.env` 파일을 생성하고 Discord 봇 토큰을 입력해주세요:

```env
DISCORD_TOKEN=your_bot_token_here
```

### 4. 봇 실행
```bash
python run.py
```

## 🤖 Discord Bot 설정

### Discord Developer Portal에서:
1. [Discord Developer Portal](https://discord.com/developers/applications) 접속
2. "New Application" 클릭하여 새 애플리케이션 생성
3. Bot 섹션에서 "Add Bot" 클릭
4. Token 복사 (환경변수 `DISCORD_TOKEN`에 사용)
5. OAuth2 > URL Generator에서 봇 권한 설정:
   - Scopes: `bot`, `applications.commands`
   - Bot Permissions: `Send Messages`, `Use Slash Commands`, `Read Message History` 등

### 디스코드 서버에 봇 초대:
1. OAuth2 URL Generator에서 생성된 URL로 봇 초대
2. 서버 ID 확인 (서버 우클릭 > ID 복사)

## 📁 프로젝트 구조

```
bot/
├── main.py            # 메인 봇 오케스트레이터
├── commands/          # 명령어 모듈들
│   ├── basic.py       # 기본 명령어 (!핑, !길드, !도움말)
│   └── ...            # 추가 기능 모듈들
├── utils/             # 유틸리티 함수들
│   └── helpers.py     # 헬퍼 함수들
├── config/            # 설정 파일들
│   └── settings.py    # 봇 설정값들
└── __init__.py
run.py                 # 봇 실행 파일
```

## 🎮 현재 기능

- `!핑` - 봇 응답속도 확인
- `!길드` - 새벽 길드 정보 표시  
- `!도움말` - 명령어 목록 표시

## 🔮 추후 추가 예정

- 메이플랜드 캐릭터 조회
- 길드원 관리 기능
- 이벤트 알림
- 보스 레이드 스케줄링

## 📝 개발 가이드

### 새 명령어 추가하기:
1. `bot/commands/` 폴더에 새 파일 생성
2. `commands.Cog` 클래스를 상속받아 명령어 정의
3. `setup(bot)` 함수로 Cog 등록
4. 봇 재시작 (자동으로 로드됨)

### 명령어 구조 예시:
```python
from discord.ext import commands

class NewCommands(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
    
    @commands.command(name='새명령어')
    async def new_command(self, ctx):
        await ctx.send("새 명령어입니다!")

async def setup(bot):
    await bot.add_cog(NewCommands(bot))
```

## 🤝 기여하기

1. Fork this repository
2. Create your feature branch (`git checkout -b feature/amazing-feature`)
3. Commit your changes (`git commit -m 'Add some amazing feature'`)
4. Push to the branch (`git push origin feature/amazing-feature`)
5. Open a Pull Request

## 📄 라이선스

MIT License