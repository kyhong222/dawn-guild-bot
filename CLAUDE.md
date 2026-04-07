# 새벽 길드봇 (Dawn Guild Bot)

메이플랜드 "새벽" 길드를 위한 Python Discord 봇.

## Tech Stack

- Python 3.11+, discord.py 2.3.2, aiohttp, python-dotenv
- pytest for testing
- GitHub Actions CI/CD → Mac Mini 배포

## Project Structure

```
bot/
  main.py            # 봇 초기화, 이벤트 핸들러, 커맨드 동적 로딩
  commands/           # Cog 기반 명령어 모듈 (basic, elevator, jari, price)
  config/settings.py  # 접두사, 채널 허용, 색상, 메시지 설정
  utils/              # API 통합 (mapleland.py, mashop.py), 헬퍼
scripts/              # 배포/제어 스크립트, launchd plist
tests/                # pytest 테스트
```

## Commands

- `!핑` - 지연시간 확인
- `!주사위` - 1~100 랜덤
- `!도움말` - 명령어 목록
- `!엘레베이터` (`!엘베`) - 루디브리엄 엘리베이터 스케줄
- `!자리값` (`!자리`) - Mashop API로 맵 시세 조회
- `!시세` (`!가격`) - Mapleland API로 아이템 시세 조회

## Run & Test

```bash
python -m venv venv && source venv/bin/activate
pip install -r requirements.txt
# .env 에 DISCORD_TOKEN 설정
python run.py

# 테스트
pytest tests/ -v
```

## Key Patterns

- 모든 명령어는 `bot/commands/`에 Cog 클래스로 구현, 자동 로딩됨
- API 호출은 전부 async/await + aiohttp
- 검색은 2단계: 부분 문자열 매칭 → 초성/약어 매칭
- 가격 데이터는 인메모리 캐시 + 중앙값 기반 이상치 제거
- 채널 화이트리스트로 봇 사용 채널 제한 (settings.py)
- 중복 메시지 방지용 processed_messages set 사용

## Conventions

- 커밋 메시지: 이모지 접두사 + 한국어 (예: `🎨 엘레베이터 임베드 스타일로 변경`)
- 명령어 접두사: `!`
- 임베드 색상: `0xFF6B35` (새벽 오렌지)
- 한국어 UI/UX, 코드 주석도 한국어
