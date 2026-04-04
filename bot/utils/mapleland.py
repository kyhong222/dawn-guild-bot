"""메랜지지 API 유틸리티"""
import aiohttp
import re
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

    def _tokenize_query(self, query: str) -> List[str]:
        """쿼리를 토큰으로 분리 (숫자+%는 하나의 토큰)"""
        tokens = []
        i = 0
        while i < len(query):
            # 숫자로 시작하면 연속된 숫자+% 묶음
            if query[i].isdigit():
                j = i
                while j < len(query) and (query[j].isdigit() or query[j] == '%'):
                    j += 1
                tokens.append(query[i:j])
                i = j
            else:
                tokens.append(query[i])
                i += 1
        return tokens

    def _match_abbreviation(self, query: str, item_name: str) -> bool:
        """줄임말 매칭 (파엘 → 파워 엘릭서, 드샤보 → 드래곤 샤인보우)"""
        # 공백 제거한 아이템 이름에서 토큰들이 순서대로 나타나는지 확인
        item_name_flat = item_name.replace(":", "").replace(" ", "")
        query_tokens = self._tokenize_query(query)

        pos = 0
        for token in query_tokens:
            idx = item_name_flat.find(token, pos)
            if idx == -1:
                return False
            pos = idx + len(token)

        return True

    async def search_item(self, query: str) -> List[Dict]:
        """아이템 이름 검색 (like 검색 + 줄임말 검색)"""
        all_items = await self.get_all_items()

        # 숫자+퍼 → 숫자+% 치환
        query = re.sub(r'(\d+)퍼', r'\1%', query)

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

    async def get_trades(self, item_code: int, filters: Dict = None) -> List[Dict]:
        """특정 아이템의 거래 목록 가져오기 (필터 적용)"""
        async with aiohttp.ClientSession() as session:
            async with session.get(
                f"{TRADE_API}?itemCode={item_code}",
                headers=HEADERS,
                timeout=10
            ) as response:
                if response.status == 200:
                    trades = await response.json()

                    # 필터 적용
                    if filters:
                        filtered = []
                        for t in trades:
                            item_opt = t.get("itemOption", {})

                            # 공격력 필터
                            if "pad" in filters:
                                pad = item_opt.get("incPAD", 0)
                                if pad != filters["pad"]:
                                    continue

                            # 합마 필터
                            if "hapma" in filters:
                                hapma = item_opt.get("hapma", 0)
                                if hapma != filters["hapma"]:
                                    continue

                            filtered.append(t)
                        return filtered

                    return trades
                return []

    async def get_price_summary(self, item_code: int, item_name: str, filters: Dict = None) -> Dict:
        """아이템 가격 요약 (팝니다 최저가 3개, 삽니다 최고가 3개)"""
        trades = await self.get_trades(item_code, filters)

        if not trades:
            return {"error": "거래 정보가 없습니다."}

        # 활성화된 매물만 필터링
        active_trades = [t for t in trades if t.get("tradeStatus") == True]

        # 팝니다/삽니다 분리
        sells = [t for t in active_trades if t.get("tradeType") == "sell"]
        buys = [t for t in active_trades if t.get("tradeType") == "buy"]

        # 팝니다 최저가순 정렬, 상위 3개
        sells_sorted = sorted(sells, key=lambda x: x.get("itemPrice", float('inf')))[:3]
        sell_items = [
            {"price": t.get("itemPrice", 0), "comment": t.get("comment", "")}
            for t in sells_sorted
        ]

        # 삽니다 최고가순 정렬, 상위 3개
        buys_sorted = sorted(buys, key=lambda x: x.get("itemPrice", 0), reverse=True)[:3]
        buy_items = [
            {"price": t.get("itemPrice", 0), "comment": t.get("comment", "")}
            for t in buys_sorted
        ]

        return {
            "item_code": item_code,
            "item_name": item_name,
            "sell_items": sell_items,
            "sell_count": len(sells),
            "buy_items": buy_items,
            "buy_count": len(buys),
        }
