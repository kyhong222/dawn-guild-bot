# 🌅 새벽 길드봇

메이플랜드 새벽 길드를 위한 디스코드 봇입니다.

## 🚀 설치 및 실행

### 1. 의존성 설치
```bash
npm install
```

### 2. 환경변수 설정
`.env.example`을 참고하여 `.env` 파일을 생성하고 다음 정보를 입력해주세요:

```env
DISCORD_TOKEN=your_bot_token_here
CLIENT_ID=your_client_id_here
GUILD_ID=your_guild_id_here
```

### 3. 커맨드 등록
```bash
npm run deploy
```

### 4. 봇 실행
```bash
npm start
# 또는 개발 모드
npm run dev
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
src/
├── index.js           # 메인 봇 파일
├── deploy-commands.js # 커맨드 등록 스크립트
├── commands/          # 슬래시 커맨드들
│   ├── ping.js        # 핑 커맨드
│   └── guild.js       # 길드 정보 커맨드
├── events/            # 이벤트 핸들러들
│   ├── ready.js       # 봇 준비 이벤트
│   └── interactionCreate.js # 상호작용 이벤트
└── utils/             # 유틸리티 함수들
```

## 🎮 현재 기능

- `/핑` - 봇 응답속도 확인
- `/길드` - 새벽 길드 정보 표시

## 🔮 추후 추가 예정

- 메이플랜드 캐릭터 조회
- 길드원 관리 기능
- 이벤트 알림
- 보스 레이드 스케줄링

## 📝 개발 가이드

### 새 커맨드 추가하기:
1. `src/commands/` 폴더에 새 파일 생성
2. SlashCommandBuilder로 커맨드 정의
3. `npm run deploy`로 커맨드 등록
4. 봇 재시작

### 새 이벤트 추가하기:
1. `src/events/` 폴더에 새 파일 생성
2. 이벤트 핸들러 작성
3. 봇 재시작

## 🤝 기여하기

1. Fork this repository
2. Create your feature branch (`git checkout -b feature/amazing-feature`)
3. Commit your changes (`git commit -m 'Add some amazing feature'`)
4. Push to the branch (`git push origin feature/amazing-feature`)
5. Open a Pull Request

## 📄 라이선스

MIT License