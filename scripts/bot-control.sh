#!/bin/bash
# 봇 제어 스크립트

BOT_DIR="/Users/mighty/.openclaw/workspace-mapleland-guild"
LOG_FILE="$HOME/dawn-bot.log"

case "$1" in
    start)
        echo "▶️  봇 시작 중..."
        cd "$BOT_DIR"
        nohup python3 run.py > "$LOG_FILE" 2>&1 &
        sleep 2
        if pgrep -f "python3.*run.py" > /dev/null; then
            echo "✅ 봇 시작됨 (PID: $(pgrep -f 'python3.*run.py'))"
        else
            echo "❌ 봇 시작 실패"
            exit 1
        fi
        ;;
    stop)
        echo "🛑 봇 종료 중..."
        pkill -f "python3.*run.py" || true
        echo "✅ 봇 종료됨"
        ;;
    restart)
        $0 stop
        sleep 2
        $0 start
        ;;
    status)
        if pgrep -f "python3.*run.py" > /dev/null; then
            echo "✅ 봇 실행 중 (PID: $(pgrep -f 'python3.*run.py'))"
        else
            echo "⏹️  봇 실행 안 됨"
        fi
        ;;
    logs)
        tail -f "$LOG_FILE"
        ;;
    *)
        echo "사용법: $0 {start|stop|restart|status|logs}"
        exit 1
        ;;
esac
