#!/usr/bin/env python3
"""
새벽 길드봇 메인 실행 파일
"""
import sys
import os

# 프로젝트 루트 디렉토리를 Python 경로에 추가
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from bot.main import main
import asyncio

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\n🌅 새벽 길드봇이 종료되었습니다.")
    except Exception as e:
        print(f"❌ 봇 실행 중 오류 발생: {e}")
        sys.exit(1)