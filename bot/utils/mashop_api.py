"""
메랜샵 API 유틸리티
"""
import aiohttp
import asyncio
from typing import Dict, List, Optional
import urllib.parse
import re

class MashopAPI:
    def __init__(self):
        self.base_url = "https://mashop.kr"
        self.api_base = "https://api.mashop.kr"  # 실제 API 서버
        
    async def search_map(self, map_name: str) -> Dict:
        """맵 이름으로 검색"""
        try:
            async with aiohttp.ClientSession() as session:
                headers = {
                    'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36',
                    'Accept': 'application/json, text/plain, */*',
                    'Accept-Language': 'ko-KR,ko;q=0.9,en;q=0.8',
                    'Origin': 'https://mashop.kr',
                    'Referer': 'https://mashop.kr/'
                }
                
                # 1. 먼저 전체 맵 목록에서 검색할 맵 찾기
                maps_data = await self._get_all_maps(session, headers)
                target_map = self._find_matching_map(maps_data, map_name)
                
                if not target_map:
                    return {"error": f"'{map_name}' 맵을 찾을 수 없습니다."}
                
                # 2. 해당 맵의 자리값 정보 가져오기
                map_name = target_map['mapName']
                jari_data = await self._get_jari_data(session, headers, map_name)
                
                if jari_data:
                    return self._parse_jari_data(jari_data, map_name)
                else:
                    # 자리값 정보가 없는 경우
                    return {
                        "sell_prices": [],
                        "buy_prices": [],
                        "source_url": f"{self.base_url}/jari/{urllib.parse.quote(map_name)}",
                        "map_name": map_name,
                        "note": f"현재 '{map_name}'의 자리값 정보가 없습니다. 메랜샵에서 확인해보세요!"
                    }
                    
        except Exception as e:
            return {"error": f"검색 중 오류: {str(e)}"}
                
        except Exception as e:
            return {"error": f"검색 중 오류 발생: {str(e)}"}
    
    def _is_valid_result(self, content: str) -> bool:
        """유효한 결과인지 확인"""
        return len(content) > 100 and ("팝니다" in content or "삽니다" in content)
    
    async def _search_by_scraping(self, session: aiohttp.ClientSession, map_name: str) -> Dict:
        """웹 스크래핑으로 검색 (실제 API 찾기 전까지는 mock 데이터)"""
        try:
            # TODO: 실제 API 엔드포인트 리버스 엔지니어링 필요
            # 브라우저 개발자 도구에서 Network 탭을 확인하여 
            # 실제 검색 시 호출되는 API를 찾아야 함
            
            # 가능한 API 패턴들 (추측)
            possible_apis = [
                f"{self.base_url}/api/search",
                f"{self.base_url}/api/jari/search", 
                f"{self.base_url}/search",
                f"https://api.mashop.kr/search"
            ]
            
            headers = {
                'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36',
                'Accept': 'application/json, text/plain, */*',
                'Accept-Language': 'ko-KR,ko;q=0.9,en;q=0.8',
                'Referer': 'https://mashop.kr/'
            }
            
            for api_url in possible_apis:
                try:
                    params = {'q': map_name, 'query': map_name, 'keyword': map_name}
                    for param_key, param_value in params.items():
                        try:
                            async with session.get(
                                api_url, 
                                params={param_key: param_value},
                                headers=headers,
                                timeout=5
                            ) as response:
                                if response.status == 200:
                                    try:
                                        data = await response.json()
                                        if data and self._is_valid_api_response(data):
                                            return self._parse_api_response(data, map_name)
                                    except:
                                        # JSON이 아닐 수도 있음
                                        continue
                        except:
                            continue
                except:
                    continue
            
            # 실제 API를 찾지 못했으므로 임시 mock 데이터 반환
            return self._get_mock_data(map_name)
            
        except Exception as e:
            return {"error": f"검색 중 오류: {str(e)}"}
    
    async def _try_api_endpoint(self, session: aiohttp.ClientSession, api_url: str, map_name: str) -> Optional[Dict]:
        """API 엔드포인트 시도"""
        try:
            params = {"q": map_name, "query": map_name, "search": map_name}
            for param_key, param_value in params.items():
                try:
                    url = f"{api_url}?{param_key}={urllib.parse.quote(param_value)}"
                    async with session.get(url, timeout=5) as response:
                        if response.status == 200:
                            data = await response.json()
                            if data and isinstance(data, (dict, list)):
                                return {"data": data, "source": url}
                except:
                    continue
        except:
            pass
        return None
    
    async def _parse_map_data(self, content: str, session: aiohttp.ClientSession, url: str) -> Dict:
        """맵 데이터 파싱"""
        try:
            # HTML에서 가격 정보 추출
            sell_prices = self._extract_prices(content, "팝니다")
            buy_prices = self._extract_prices(content, "삽니다")
            
            return {
                "sell_prices": sell_prices[:5],  # 최신 5개
                "buy_prices": buy_prices[:5],   # 최신 5개
                "source_url": url
            }
        except Exception as e:
            return {"error": f"데이터 파싱 오류: {str(e)}"}
    
    def _extract_prices(self, content: str, price_type: str) -> List[int]:
        """가격 정보 추출"""
        prices = []
        
        # 가격 패턴 찾기 (예: "1000만 메소", "50만", "1억")
        price_patterns = [
            r'(\d+(?:\.\d+)?)\s*억',
            r'(\d+(?:\.\d+)?)\s*만',
            r'(\d+(?:,\d+)*)\s*메소'
        ]
        
        for pattern in price_patterns:
            matches = re.findall(pattern, content)
            for match in matches:
                try:
                    price = float(match.replace(',', ''))
                    if '억' in pattern:
                        price = int(price * 10000)  # 억 -> 만 메소
                    elif '만' in pattern:
                        price = int(price)  # 만 메소 그대로
                    else:
                        price = int(price / 10000)  # 메소 -> 만 메소
                    
                    if 1 <= price <= 100000:  # 1만 ~ 10억 범위
                        prices.append(price)
                except:
                    continue
        
        return sorted(prices, reverse=True)  # 최신순 (높은 가격순으로 정렬)
    
    async def _get_all_maps(self, session: aiohttp.ClientSession, headers: Dict) -> List[Dict]:
        """전체 맵 목록 가져오기"""
        try:
            async with session.get(f"{self.api_base}/api/maps/all", headers=headers, timeout=10) as response:
                if response.status == 200:
                    data = await response.json()
                    return data.get("mapInfoList", [])
        except:
            pass
        return []
    
    def _find_matching_map(self, maps_data: List[Dict], search_name: str) -> Optional[Dict]:
        """검색어와 일치하는 맵 찾기"""
        search_clean = search_name.replace(" ", "").lower()
        
        # 일반적인 줄임말 매칭
        nickname_map = {
            "죽둥": "죽은용의둥지",
            "망둥": "망가진용의둥지", 
            "페리": "페리온",
            "헤네": "헤네시스",
            "루디": "루디브리엄",
            "아쿠": "아쿠아로드",
            "깊바협1": "깊은 바다 협곡1",
            "깊바협2": "깊은 바다 협곡2",
            "위바협1": "위험한 바다 협곡1", 
            "위바협2": "위험한 바다 협곡2",
            "깊은바다1": "깊은 바다 협곡1",
            "깊은바다2": "깊은 바다 협곡2",
            "위험한바다1": "위험한 바다 협곡1",
            "위험한바다2": "위험한 바다 협곡2",
            "남용": "남겨진 용의 둥지",
            "남겨진용": "남겨진 용의 둥지"
        }
        
        # 줄임말을 실제 이름으로 변환
        if search_clean in nickname_map:
            search_clean = nickname_map[search_clean]
        
        # 더 적극적인 키워드 매칭도 시도
        keyword_expansions = {
            "깊은바다": "깊은바다협곡",
            "위험한바다": "위험한바다협곡", 
            "남용": "남겨진용의둥지"
        }
        
        for keyword, expansion in keyword_expansions.items():
            if keyword in search_clean:
                search_clean = search_clean.replace(keyword, expansion)
                break
        
        # 정확한 매칭 먼저 시도
        for map_info in maps_data:
            map_name = map_info['mapName']
            map_clean = map_name.replace(" ", "").replace(":", "").lower()
            
            if search_clean == map_clean:
                return map_info
        
        # 스마트 키워드 매칭
        search_keywords = self._extract_keywords(search_name)
        best_match = None
        max_score = 0
        
        for map_info in maps_data:
            map_name = map_info['mapName']
            score = self._calculate_match_score(search_keywords, map_name, search_name)
            
            if score > max_score and score >= 0.6:  # 60% 이상 매칭
                max_score = score
                best_match = map_info
        
        if best_match:
            return best_match
        
        # 포함 매칭 (fallback)
        for map_info in maps_data:
            map_name = map_info['mapName']
            map_clean = map_name.replace(" ", "").replace(":", "").lower()
            
            if search_clean in map_clean or map_clean in search_clean:
                return map_info
        
        # 부분 매칭 (한글)
        for map_info in maps_data:
            map_name = map_info['mapName']
            if search_name in map_name or map_name in search_name:
                return map_info
                
        return None
    
    async def _get_jari_data(self, session: aiohttp.ClientSession, headers: Dict, map_name: str) -> List[Dict]:
        """특정 맵의 자리값 데이터 가져오기"""
        try:
            # 최근 자리값 정보 가져오기
            async with session.get(f"{self.api_base}/api/jari/recent", headers=headers, timeout=10) as response:
                if response.status == 200:
                    data = await response.json()
                    return self._filter_by_map_name(data, map_name)
        except:
            pass
            
        return []
    
    def _filter_by_map_name(self, jari_data: List[Dict], target_map_name: str) -> List[Dict]:
        """특정 맵 이름의 자리값 데이터 필터링"""
        if not isinstance(jari_data, list):
            return []
            
        filtered_data = []
        for item in jari_data:
            if isinstance(item, dict) and item.get('mapName') == target_map_name:
                filtered_data.append(item)
                if len(filtered_data) >= 20:  # 최대 20개까지
                    break
        return filtered_data
    
    def _parse_jari_data(self, jari_data: List[Dict], map_name: str) -> Dict:
        """자리값 데이터 파싱"""
        try:
            sell_prices = []
            buy_prices = []
            
            # 실제 메랜샵 API 구조에 맞게 파싱
            for item in jari_data:
                try:
                    price = item.get('price', 0)
                    trade_type = item.get('tradeType', '')
                    
                    # 메소를 만 메소로 변환
                    price_in_man = price // 10000 if price >= 10000 else price
                    
                    if trade_type == 'SELL' and len(sell_prices) < 5:
                        sell_prices.append(price_in_man)
                    elif trade_type == 'BUY' and len(buy_prices) < 5:
                        buy_prices.append(price_in_man)
                        
                except:
                    continue
            
            # 가격이 없으면 안내 메시지 반환
            if not sell_prices and not buy_prices:
                return {
                    "sell_prices": [],
                    "buy_prices": [],
                    "source_url": f"{self.base_url}/jari/{urllib.parse.quote(map_name)}",
                    "map_name": map_name,
                    "note": f"현재 '{map_name}'의 자리값 정보가 없습니다. 메랜샵에서 확인해보세요!"
                }
                
            return {
                "sell_prices": sell_prices,
                "buy_prices": buy_prices,
                "source_url": f"{self.base_url}/jari/{urllib.parse.quote(map_name)}",
                "map_name": map_name
            }
            
        except Exception as e:
            return {"error": f"자리값 데이터 파싱 오류: {str(e)}"}
    
    def _get_mock_data(self, map_name: str) -> Dict:
        """임시 mock 데이터 (테스트용)"""
        # 일반적인 사냥터 가격 범위
        mock_data = {
            "죽둥": {"sell": [1200, 1150, 1100, 1080, 1000], "buy": [800, 850, 900, 920, 950]},
            "죽은용의둥지": {"sell": [1200, 1150, 1100, 1080, 1000], "buy": [800, 850, 900, 920, 950]},
            "페리온": {"sell": [300, 280, 250, 220, 200], "buy": [150, 160, 180, 190, 200]},
            "헤네시스": {"sell": [100, 90, 80, 70, 60], "buy": [30, 40, 50, 55, 60]},
            "망가진용의둥지": {"sell": [800, 750, 700, 680, 650], "buy": [400, 420, 450, 480, 500]},
            "망둥": {"sell": [800, 750, 700, 680, 650], "buy": [400, 420, 450, 480, 500]},
            "default": {"sell": [500, 480, 450, 420, 400], "buy": [200, 220, 250, 280, 300]}
        }
        
        # 키워드 매칭 (공백 제거해서 비교)
        clean_name = map_name.replace(" ", "")
        for key in mock_data.keys():
            if key in clean_name or clean_name in key:
                data = mock_data[key]
                return {
                    "sell_prices": data["sell"][:5],
                    "buy_prices": data["buy"][:5],
                    "source_url": f"{self.base_url}/jari/{urllib.parse.quote(map_name)}",
                    "note": "🚧 메랜샵 API는 로그인이 필요합니다. 현재는 임시 데이터를 표시 중입니다."
                }
        
        # 기본값
        data = mock_data["default"]
        return {
            "sell_prices": data["sell"][:5],
            "buy_prices": data["buy"][:5], 
            "source_url": f"{self.base_url}/jari/{urllib.parse.quote(map_name)}",
            "note": "🚧 메랜샵 API는 로그인이 필요합니다. 현재는 임시 데이터를 표시 중입니다."
        }
    
    def format_price_summary(self, data: Dict) -> str:
        """가격 요약 포맷팅"""
        if data.get("error"):
            return f"❌ 오류: {data['error']}"
        
        sell_prices = data.get("sell_prices", [])
        buy_prices = data.get("buy_prices", [])
        
        if not sell_prices and not buy_prices:
            note = data.get("note", "")
            if note:
                return f"📋 {note}"
            else:
                return "❌ 해당 맵의 자리값 정보를 찾을 수 없습니다."
        
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
    
    def _extract_keywords(self, search_text: str) -> List[str]:
        """검색어에서 키워드 추출"""
        # 숫자와 한글 분리
        keywords = []
        
        # 공통 줄임말 패턴
        patterns = {
            r'깊바협(\d+)': r'깊은 바다 협곡\1',
            r'위바협(\d+)': r'위험한 바다 협곡\1',
            r'남용': '남겨진 용의 둥지',
            r'죽둥': '죽은용의둥지',
            r'망둥': '망가진용의둥지'
        }
        
        import re
        expanded_text = search_text
        for pattern, replacement in patterns.items():
            expanded_text = re.sub(pattern, replacement, expanded_text)
        
        # 키워드 분리
        keywords.extend(expanded_text.replace(" ", "").split())
        keywords.extend(search_text.replace(" ", "").split())
        
        return list(set(keywords))  # 중복 제거
    
    def _calculate_match_score(self, search_keywords: List[str], map_name: str, original_search: str) -> float:
        """매칭 점수 계산"""
        map_clean = map_name.replace(" ", "").replace(":", "").lower()
        original_clean = original_search.replace(" ", "").lower()
        
        # 완전 일치 점수
        if original_clean in map_clean or map_clean in original_clean:
            return 1.0
        
        # 키워드 매칭 점수
        matched_keywords = 0
        for keyword in search_keywords:
            keyword_clean = keyword.replace(" ", "").lower()
            if keyword_clean in map_clean:
                matched_keywords += 1
        
        if not search_keywords:
            return 0.0
        
        keyword_score = matched_keywords / len(search_keywords)
        
        # 특별 보너스: 숫자 매칭
        import re
        search_numbers = re.findall(r'\d+', original_search)
        map_numbers = re.findall(r'\d+', map_name)
        
        number_bonus = 0.0
        if search_numbers and map_numbers:
            if any(num in map_numbers for num in search_numbers):
                number_bonus = 0.3
        
        return min(1.0, keyword_score + number_bonus)