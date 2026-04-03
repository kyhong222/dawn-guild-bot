"""
간단한 메랜샵 API - 실제 메랜샵처럼 작동
"""
import aiohttp
from typing import Dict, List, Optional
import urllib.parse

class SimpleMashopAPI:
    def __init__(self):
        self.base_url = "https://mashop.kr"
        self.api_base = "https://api.mashop.kr"
        
    async def search_map(self, search_name: str) -> Dict:
        """메랜샵 스타일 맵 검색 + 자리값 가져오기"""
        try:
            async with aiohttp.ClientSession() as session:
                headers = {
                    'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36',
                    'Accept': 'application/json, text/plain, */*',
                    'Origin': 'https://mashop.kr',
                    'Referer': 'https://mashop.kr/'
                }
                
                # 1️⃣ 전체 맵 목록 가져오기
                maps_data = await self._get_all_maps(session, headers)
                
                # 2️⃣ 메랜샵 스타일 검색
                target_map = self._search_like_mashop(maps_data, search_name)
                
                if not target_map:
                    return {"error": f"'{search_name}' 맵을 찾을 수 없습니다."}
                
                # 3️⃣ 해당 맵의 자리값 가져오기
                map_name = target_map['mapName']
                jari_data = await self._get_recent_jari(session, headers, map_name)
                
                # 4️⃣ 결과 포맷팅
                return self._format_result(jari_data, map_name)
                
        except Exception as e:
            return {"error": f"검색 중 오류: {str(e)}"}
    
    async def _get_all_maps(self, session: aiohttp.ClientSession, headers: Dict) -> List[Dict]:
        """전체 맵 목록"""
        try:
            async with session.get(f"{self.api_base}/api/maps/all", headers=headers) as response:
                if response.status == 200:
                    data = await response.json()
                    return data.get("mapInfoList", [])
        except:
            pass
        return []
    
    def _search_like_mashop(self, maps_data: List[Dict], search_name: str) -> Optional[Dict]:
        """메랜샵 웹사이트처럼 검색"""
        search_text = search_name.strip().replace(" ", "").lower()
        
        # 🎯 메랜샵 실제 줄임말들 (사용자들이 자주 쓰는)
        shortcuts = {
            "깊바협1": "깊은바다협곡1", "깊바협2": "깊은바다협곡2",
            "위바협1": "위험한바다협곡1", "위바협2": "위험한바다협곡2", 
            "죽둥": "죽은용의둥지", "망둥": "망가진용의둥지",
            "남용": "남겨진용의둥지"
        }
        
        # 줄임말 변환
        if search_text in shortcuts:
            search_text = shortcuts[search_text]
        
        # 검색 (메랜샵 방식: 포함 검색)
        for map_info in maps_data:
            map_clean = map_info['mapName'].replace(" ", "").replace(":", "").lower()
            
            # 포함 검색 (양방향)
            if search_text in map_clean or map_clean in search_text:
                return map_info
        
        return None
    
    async def _get_recent_jari(self, session: aiohttp.ClientSession, headers: Dict, map_name: str) -> List[Dict]:
        """최신 자리값 정보"""
        try:
            async with session.get(f"{self.api_base}/api/jari/recent", headers=headers) as response:
                if response.status == 200:
                    data = await response.json()
                    # 해당 맵만 필터링
                    return [item for item in data if item.get('mapName') == map_name]
        except:
            pass
        return []
    
    def _format_result(self, jari_data: List[Dict], map_name: str) -> Dict:
        """결과 포맷팅"""
        sell_prices = []
        buy_prices = []
        
        # 가격 추출
        for item in jari_data[:10]:  # 최대 10개
            price = item.get('price', 0) // 10000  # 만 메소 변환
            trade_type = item.get('tradeType', '')
            
            if trade_type == 'SELL' and len(sell_prices) < 5:
                sell_prices.append(price)
            elif trade_type == 'BUY' and len(buy_prices) < 5:
                buy_prices.append(price)
        
        # 자리값이 없는 경우
        if not sell_prices and not buy_prices:
            return {
                "sell_prices": [],
                "buy_prices": [],
                "source_url": f"{self.base_url}/jari/{urllib.parse.quote(map_name)}",
                "map_name": map_name,
                "note": f"현재 '{map_name}'의 자리값 정보가 없습니다."
            }
        
        return {
            "sell_prices": sell_prices,
            "buy_prices": buy_prices,
            "source_url": f"{self.base_url}/jari/{urllib.parse.quote(map_name)}",
            "map_name": map_name
        }
    
    def format_price_summary(self, data: Dict) -> str:
        """가격 요약"""
        if data.get("error"):
            return f"❌ 오류: {data['error']}"
        
        sell_prices = data.get("sell_prices", [])
        buy_prices = data.get("buy_prices", [])
        
        if not sell_prices and not buy_prices:
            note = data.get("note", "자리값 정보가 없습니다.")
            return f"📭 {note}"
        
        summary = []
        if sell_prices:
            avg_sell = sum(sell_prices) // len(sell_prices)
            summary.append(f"**팝니다**: {avg_sell}만 메소")
        
        if buy_prices:
            avg_buy = sum(buy_prices) // len(buy_prices) 
            summary.append(f"**삽니다**: {avg_buy}만 메소")
        
        result = " / ".join(summary) + "로 형성되어 있습니다."
        
        if data.get("note"):
            result += f"\n\n{data['note']}"
        
        return result