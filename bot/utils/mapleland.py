"""메랜지지 API 유틸리티"""
import aiohttp
from typing import Optional, List, Dict

ITEMS_API = "https://mapleland.gg/api/items"
TRADE_API = "https://api.mapleland.gg/trade"
HEADERS = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
    'Accept': '*/*',
    'Origin': 'https://mapleland.gg',
    'Referer': 'https://mapleland.gg/'
}


class MaplelandAPI:
    def __init__(self):
        self._item_cache: Optional[List[Dict]] = None

    async def get_all_items(self) -> List[Dict]:
        """모든 아이템 목록 가져오기 (캐싱)"""
        if self._item_cache is not None:
            return self._item_cache

        async with aiohttp.ClientSession() as session:
            async with session.get(
                ITEMS_API,
                headers=HEADERS,
                timeout=10
            ) as response:
                if response.status == 200:
                    self._item_cache = await response.json()
                    return self._item_cache
                return []

    def _match_abbreviation(self, query: str, item_name: str) -> bool:
        """줄임말 매칭 (파엘 → 파워 엘릭서)"""
        words = item_name.replace(":", " ").split()
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

    async def search_item(self, query: str) -> List[Dict]:
        """아이템 이름 검색 (like 검색 + 줄임말 검색)"""
        all_items = await self.get_all_items()
        query_lower = query.lower().replace(" ", "")

        matches = []
        for item in all_items:
            item_name = item.get("itemName", "")
            item_name_normalized = item_name.lower().replace(" ", "")

            # 1. 단순 포함 검색
            if query_lower in item_name_normalized:
                matches.append(item)
            # 2. 줄임말 매칭
            elif self._match_abbreviation(query, item_name):
                matches.append(item)

        return matches

    async def get_trades(self, item_code: int) -> List[Dict]:
        """특정 아이템의 거래 목록 가져오기"""
        async with aiohttp.ClientSession() as session:
            async with session.get(
                f"{TRADE_API}?itemCode={item_code}",
                headers=HEADERS,
                timeout=10
            ) as response:
                if response.status == 200:
                    return await response.json()
                return []

    async def get_price_summary(self, item_code: int, item_name: str) -> Dict:
        """아이템 가격 요약 (팝니다 최저가, 삽니다 최고가)"""
        trades = await self.get_trades(item_code)

        if not trades:
            return {"error": "거래 정보가 없습니다."}

        # 활성화된 매물만 필터링
        active_trades = [t for t in trades if t.get("tradeStatus") == True]

        # 팝니다/삽니다 분리
        sells = [t for t in active_trades if t.get("tradeType") == "sell"]
        buys = [t for t in active_trades if t.get("tradeType") == "buy"]

        # 팝니다 최저가
        sell_min = None
        sell_min_item = None
        if sells:
            sell_min_item = min(sells, key=lambda x: x.get("itemPrice", float('inf')))
            sell_min = sell_min_item.get("itemPrice", 0)

        # 삽니다 최고가
        buy_max = None
        buy_max_item = None
        if buys:
            buy_max_item = max(buys, key=lambda x: x.get("itemPrice", 0))
            buy_max = buy_max_item.get("itemPrice", 0)

        return {
            "item_code": item_code,
            "item_name": item_name,
            "sell_min": sell_min,
            "sell_comment": sell_min_item.get("comment", "") if sell_min_item else "",
            "sell_count": len(sells),
            "buy_max": buy_max,
            "buy_comment": buy_max_item.get("comment", "") if buy_max_item else "",
            "buy_count": len(buys),
        }
