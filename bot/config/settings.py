"""
봇 설정 파일
"""

# 명령어 접두사
COMMAND_PREFIX = "!"

# 허용된 채널 ID 리스트 (비어있으면 모든 채널 허용)
ALLOWED_CHANNELS = [
    # "1489498930277257339",  # 새벽봇 채널
    # 추가 채널 ID들...
]

# 봇 색상 설정 (임베드용)
BOT_COLOR = 0xFF6B35  # 새벽 오렌지색

# 에러 메시지
ERROR_MESSAGES = {
    "command_not_found": "❌ 알 수 없는 명령어입니다.",
    "missing_argument": "❌ 필요한 인수가 부족합니다.",
    "permission_denied": "❌ 권한이 없습니다.",
    "unexpected_error": "❌ 예기치 못한 오류가 발생했습니다."
}

# 성공 메시지
SUCCESS_MESSAGES = {
    "command_success": "✅ 명령어가 성공적으로 실행되었습니다.",
}

# 길드 정보
GUILD_INFO = {
    "name": "새벽",
    "game": "메이플랜드",
    "description": "메이플랜드에서 활동하는 새벽 길드입니다!",
    "activity_time": "새벽/밤"
}