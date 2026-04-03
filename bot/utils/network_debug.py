"""
메랜샵 네트워크 디버깅 도구
브라우저에서 실제 API 호출을 찾는 방법 가이드
"""
import asyncio
import aiohttp
from urllib.parse import quote_plus

class MashopNetworkDebugger:
    def __init__(self):
        self.base_url = "https://mashop.kr"
        
    async def check_common_endpoints(self):
        """일반적인 API 엔드포인트 패턴들을 확인"""
        common_patterns = [
            "/api/search",
            "/api/jari",
            "/api/spots",
            "/api/maps", 
            "/api/v1/search",
            "/search",
            "/_next/data",  # Next.js API
            "/data/search",
            "/backend/search",
            "/.netlify/functions",  # Netlify Functions
            "/api/spot/search"
        ]
        
        headers = {
            'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36',
            'Accept': 'application/json, text/plain, */*',
            'Accept-Language': 'ko-KR,ko;q=0.9,en;q=0.8',
            'Referer': 'https://mashop.kr/'
        }
        
        print("🔍 메랜샵 API 엔드포인트 스캔 중...")
        
        async with aiohttp.ClientSession() as session:
            for pattern in common_patterns:
                try:
                    test_urls = [
                        f"{self.base_url}{pattern}",
                        f"{self.base_url}{pattern}?q=죽둥",
                        f"{self.base_url}{pattern}?query=죽둥",
                        f"{self.base_url}{pattern}?search=죽둥"
                    ]
                    
                    for url in test_urls:
                        try:
                            async with session.get(url, headers=headers, timeout=3) as response:
                                content_type = response.headers.get('Content-Type', '')
                                if response.status == 200 and 'json' in content_type:
                                    print(f"✅ 발견! {url} - Status: {response.status}")
                                    try:
                                        data = await response.json()
                                        if data:
                                            print(f"   응답 구조: {type(data)} - 키: {list(data.keys()) if isinstance(data, dict) else 'Array'}")
                                    except:
                                        pass
                                elif response.status in [404, 405]:
                                    continue
                                else:
                                    print(f"🔍 {url} - Status: {response.status}, Type: {content_type}")
                        except asyncio.TimeoutError:
                            continue
                        except Exception:
                            continue
                except Exception:
                    continue
                    
        print("\n📋 브라우저에서 실제 API 찾는 방법:")
        self.print_browser_guide()
    
    def print_browser_guide(self):
        """브라우저에서 API를 찾는 가이드 출력"""
        print("""
🌐 브라우저에서 메랜샵 실제 API 찾기:

1. Chrome에서 https://mashop.kr 접속
2. F12 → Network 탭 열기  
3. XHR 또는 Fetch 필터 체크
4. 검색창에 "죽둥" 입력하고 검색
5. Network 탭에서 새로 생긴 요청들 확인

🔍 찾아야 할 정보:
- Request URL: /api/something?q=죽둥 형태
- Request Method: GET/POST
- Response: JSON 데이터 구조
- Headers: 필요한 인증 헤더들

📝 예상 API 형태:
- GET /api/search?q=죽둥
- GET /api/jari/search?query=죽둥  
- POST /api/search (body에 query)

💡 찾은 API 정보를 알려주시면 실제 연동해드릴게요!
        """)

async def debug_mashop_api():
    """메랜샵 API 디버깅 실행"""
    debugger = MashopNetworkDebugger()
    await debugger.check_common_endpoints()

if __name__ == "__main__":
    asyncio.run(debug_mashop_api())