#!/bin/bash
# 맥미니에서 수동 배포할 때 사용하는 스크립트

set -e

BOT_DIR="/Users/mighty/.openclaw/workspace-mapleland-guild"
LOG_FILE="$HOME/dawn-bot.log"

echo "🚀 새벽길드봇 배포 시작..."

cd "$BOT_DIR"

# 최신 코드 가져오기
echo "📥 코드 업데이트 중..."
git fetch origin main
git reset --hard origin/main

# 의존성 설치
echo "📦 의존성 설치 중..."
pip3 install -r requirements.txt --quiet

# 기존 봇 종료
echo "🛑 기존 봇 종료 중..."
pkill -f "python3.*run.py" || true
sleep 2

# 봇 실행
echo "▶️  봇 시작 중..."
nohup python3 run.py > "$LOG_FILE" 2>&1 &

# 실행 확인
sleep 3
if pgrep -f "python3.*run.py" > /dev/null; then
    echo "✅ 봇이 성공적으로 시작되었습니다!"
    echo "📄 로그: tail -f $LOG_FILE"
else
    echo "❌ 봇 시작 실패"
    tail -20 "$LOG_FILE"
    exit 1
fi
