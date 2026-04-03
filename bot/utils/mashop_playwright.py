"""
Playwright를 사용한 메랜샵 실제 API 분석
"""
import asyncio
from playwright.async_api import async_playwright
import json

async def capture_mashop_api():
    """실제 브라우저로 메랜샵 API 캡처"""
    
    api_calls = []
    
    async with async_playwright() as p:
        # 헤드리스 모드로 브라우저 실행
        browser = await p.chromium.launch(headless=False)  # 디버깅을 위해 헤드리스 false
        context = await browser.new_context()
        page = await context.new_page()
        
        # 네트워크 요청 감지
        async def handle_request(request):
            url = request.url
            method = request.method
            
            # API 관련 요청만 필터링
            if any(keyword in url for keyword in ['api', 'search', 'jari', 'spot', 'map']):
                print(f"🔍 요청 감지: {method} {url}")
                
                api_call = {
                    'method': method,
                    'url': url,
                    'headers': dict(request.headers),
                    'post_data': request.post_data if method == 'POST' else None
                }
                api_calls.append(api_call)
        
        # 네트워크 응답 감지
        async def handle_response(response):
            url = response.url
            status = response.status
            
            if any(keyword in url for keyword in ['api', 'search', 'jari', 'spot', 'map']):
                try:
                    content_type = response.headers.get('content-type', '')
                    if 'json' in content_type:
                        json_data = await response.json()
                        print(f"✅ JSON 응답: {status} {url}")
                        print(f"   응답 데이터: {json.dumps(json_data, ensure_ascii=False, indent=2)[:500]}...")
                    else:
                        text_data = await response.text()
                        print(f"📄 텍스트 응답: {status} {url} ({len(text_data)} chars)")
                        if len(text_data) < 200:
                            print(f"   내용: {text_data}")
                except Exception as e:
                    print(f"❌ 응답 파싱 실패: {url} - {e}")
        
        # 이벤트 리스너 등록
        page.on('request', handle_request)
        page.on('response', handle_response)
        
        try:
            print("🌐 메랜샵 접속 중...")
            await page.goto('https://mashop.kr', timeout=30000)
            
            # 페이지 로딩 대기
            await page.wait_for_timeout(3000)
            print("✅ 페이지 로딩 완료")
            
            # 검색 시도 - 다양한 방법으로
            search_selectors = [
                'input[type="text"]',
                'input[placeholder*="검색"]', 
                'input[placeholder*="찾기"]',
                '[data-testid="search"]',
                '.search-input',
                '#search'
            ]
            
            search_input = None
            for selector in search_selectors:
                try:
                    search_input = await page.query_selector(selector)
                    if search_input:
                        print(f"🔍 검색창 발견: {selector}")
                        break
                except:
                    continue
            
            if search_input:
                print("📝 '죽둥' 검색 중...")
                await search_input.fill('죽둥')
                await page.wait_for_timeout(1000)
                
                # 엔터키로 검색
                await search_input.press('Enter')
                await page.wait_for_timeout(3000)
                
                print("🔄 추가 검색 시도...")
                # 검색 버튼도 찾아서 클릭
                search_buttons = [
                    'button[type="submit"]',
                    'button:has-text("검색")',
                    'button:has-text("찾기")',
                    '.search-button',
                    '[data-testid="search-btn"]'
                ]
                
                for btn_selector in search_buttons:
                    try:
                        btn = await page.query_selector(btn_selector)
                        if btn:
                            print(f"🔘 검색 버튼 클릭: {btn_selector}")
                            await btn.click()
                            await page.wait_for_timeout(2000)
                            break
                    except:
                        continue
            else:
                print("⚠️ 검색창을 찾을 수 없습니다. 페이지 구조 분석 중...")
                
                # 페이지의 모든 input 태그 출력
                inputs = await page.query_selector_all('input')
                print(f"📋 발견된 input 태그들 ({len(inputs)}개):")
                for i, inp in enumerate(inputs[:5]):  # 처음 5개만
                    try:
                        placeholder = await inp.get_attribute('placeholder')
                        input_type = await inp.get_attribute('type') 
                        class_name = await inp.get_attribute('class')
                        print(f"  {i+1}. type={input_type}, placeholder='{placeholder}', class='{class_name}'")
                    except:
                        pass
            
            # 추가 대기 시간
            print("⏳ 네트워크 요청 완료 대기 중...")
            await page.wait_for_timeout(5000)
            
        except Exception as e:
            print(f"❌ 페이지 처리 중 오류: {e}")
        
        finally:
            await browser.close()
    
    print(f"\n📊 캡처된 API 호출 총 {len(api_calls)}개:")
    for i, call in enumerate(api_calls, 1):
        print(f"{i}. {call['method']} {call['url']}")
        if call['post_data']:
            print(f"   POST 데이터: {call['post_data']}")
    
    return api_calls

if __name__ == "__main__":
    asyncio.run(capture_mashop_api())