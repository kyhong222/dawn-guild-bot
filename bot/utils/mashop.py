"""메랜샵 API 유틸리티"""
import aiohttp
from typing import Optional, List, Dict
from urllib.parse import quote

API_BASE = "https://api.mashop.kr/api"
HEADERS = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
    'Accept': '*/*',
    'Origin': 'https://mashop.kr',
    'Referer': 'https://mashop.kr/'
}


class MashopAPI:
    def __init__(self):
        self._map_cache: Optional[List[Dict]] = None

    async def get_all_maps(self) -> List[Dict]:
        """모든 맵 목록 가져오기 (캐싱)"""
        if self._map_cache is not None:
            return self._map_cache

        async with aiohttp.ClientSession() as session:
            async with session.get(
                f"{API_BASE}/maps/all",
                headers=HEADERS,
                timeout=10
            ) as response:
                if response.status == 200:
                    data = await response.json()
                    self._map_cache = data.get("mapInfoList", [])
                    return self._map_cache
                return []

    def _match_abbreviation(self, query: str, map_name: str) -> bool:
        """줄임말 매칭 (블와둥 → 블루 와이번의 둥지)"""
        # 맵 이름에서 단어 추출 (: 와 공백으로 분리)
        words = []
        for part in map_name.replace(":", " ").split():
            words.append(part)

        # 쿼리의 각 글자가 순서대로 단어 시작과 매칭되는지 확인
        query_chars = list(query)
        word_idx = 0

        for char in query_chars:
            found = False
            while word_idx < len(words):
                if words[word_idx].startswith(char):
                    found = True
                    word_idx += 1
                    break
                word_idx += 1
            if not found:
                return False

        return True

    async def search_map(self, query: str) -> List[str]:
        """맵 이름 검색 (like 검색 + 줄임말 검색)"""
        all_maps = await self.get_all_maps()
        query_lower = query.lower().replace(" ", "")

        matches = []
        for map_info in all_maps:
            map_name = map_info.get("mapName", "")
            map_name_normalized = map_name.lower().replace(" ", "")

            # 1. 단순 포함 검색
            if query_lower in map_name_normalized:
                matches.append(map_name)
            # 2. 줄임말 매칭
            elif self._match_abbreviation(query, map_name):
                matches.append(map_name)

        return matches

    async def get_trades(self, map_name: str) -> List[Dict]:
        """특정 맵의 거래 목록 가져오기"""
        async with aiohttp.ClientSession() as session:
            encoded_name = quote(map_name)
            async with session.get(
                f"{API_BASE}/maps?keyword={encoded_name}",
                headers=HEADERS,
                timeout=10
            ) as response:
                if response.status == 200:
                    return await response.json()
                return []

    async def get_price_summary(self, map_name: str) -> Dict:
        """맵의 가격 요약 정보"""
        trades = await self.get_trades(map_name)

        if not trades:
            return {"error": "거래 정보가 없습니다."}

        # 팝니다/삽니다 분리
        sells = [t for t in trades if t.get("tradeType") == "SELL" and not t.get("isCompleted")]
        buys = [t for t in trades if t.get("tradeType") == "BUY" and not t.get("isCompleted")]

        # 시간순 정렬 (최신순)
        sells.sort(key=lambda x: x.get("createTime", ""), reverse=True)
        buys.sort(key=lambda x: x.get("createTime", ""), reverse=True)

        # 최근 5개씩
        recent_sells = sells[:5]
        recent_buys = buys[:5]

        # 가격 추출 (만메소 단위로 변환)
        sell_prices = [t.get("price", 0) // 10000 for t in recent_sells]
        buy_prices = [t.get("price", 0) // 10000 for t in recent_buys]

        return {
            "map_name": map_name,
            "sell_prices": sell_prices,
            "buy_prices": buy_prices,
            "sell_avg": sum(sell_prices) // len(sell_prices) if sell_prices else 0,
            "buy_avg": sum(buy_prices) // len(buy_prices) if buy_prices else 0,
        }
