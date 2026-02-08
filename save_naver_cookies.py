"""
네이버 로그인 및 쿠키 저장 스크립트
이 스크립트를 실행하면 브라우저가 열리고, 직접 로그인하면 쿠키가 저장됩니다.
저장된 쿠키는 카페 크롤러에서 자동으로 사용됩니다.

사용법:
    python save_naver_cookies.py
"""
import asyncio
import os
import json
from playwright.async_api import async_playwright

COOKIES_FILE = os.path.join(os.path.dirname(__file__), "naver_cookies.json")


async def save_cookies():
    """
    브라우저를 열어 수동 로그인 후 쿠키를 저장합니다.
    """
    print("=" * 50)
    print("🔐 네이버 로그인 및 쿠키 저장")
    print("=" * 50)
    print()
    print("1. 브라우저가 열리면 네이버에 직접 로그인하세요.")
    print("2. 로그인 완료 후, 터미널에서 Enter를 누르세요.")
    print("3. 쿠키가 저장되고 브라우저가 닫힙니다.")
    print()
    
    playwright = await async_playwright().start()
    
    # 브라우저를 보이게 (headless=False) 열기
    browser = await playwright.chromium.launch(headless=False)
    context = await browser.new_context()
    page = await context.new_page()
    
    # 네이버 로그인 페이지로 이동
    await page.goto("https://nid.naver.com/nidlogin.login")
    
    print("🌐 브라우저가 열렸습니다. 네이버에 로그인하세요.")
    print()
    
    # 사용자가 로그인할 때까지 대기
    input("✅ 로그인을 완료했으면 Enter를 누르세요... ")
    
    # 쿠키 저장
    cookies = await context.cookies()
    
    with open(COOKIES_FILE, "w", encoding="utf-8") as f:
        json.dump(cookies, f, ensure_ascii=False, indent=2)
    
    print()
    print(f"✅ 쿠키가 저장되었습니다: {COOKIES_FILE}")
    print(f"   총 {len(cookies)}개의 쿠키가 저장됨")
    
    # 브라우저 닫기
    await browser.close()
    await playwright.stop()
    
    print()
    print("🎉 이제 카페 크롤러를 실행하면 자동으로 로그인됩니다!")
    print("   python main.py --skip-send")


async def load_cookies():
    """저장된 쿠키를 로드하여 반환합니다."""
    if not os.path.exists(COOKIES_FILE):
        return None
    
    with open(COOKIES_FILE, "r", encoding="utf-8") as f:
        return json.load(f)


async def test_cookies():
    """저장된 쿠키로 로그인이 되는지 테스트합니다."""
    cookies = await load_cookies()
    
    if not cookies:
        print("❌ 저장된 쿠키가 없습니다. 먼저 로그인하세요.")
        return False
    
    print("🔍 저장된 쿠키로 로그인 테스트 중...")
    
    playwright = await async_playwright().start()
    browser = await playwright.chromium.launch(headless=True)
    context = await browser.new_context()
    
    # 쿠키 로드
    await context.add_cookies(cookies)
    
    page = await context.new_page()
    await page.goto("https://cafe.naver.com")
    await page.wait_for_timeout(2000)
    
    # 로그인 상태 확인
    try:
        login_area = await page.query_selector(".gnb_my_info, .gnb_btn_login")
        if login_area:
            text = await login_area.inner_text()
            if "로그인" in text:
                print("❌ 로그인되지 않았습니다. 쿠키를 다시 저장해주세요.")
                result = False
            else:
                print("✅ 로그인 성공! 쿠키가 유효합니다.")
                result = True
        else:
            print("✅ 로그인 상태로 추정됩니다.")
            result = True
    except:
        print("⚠️ 로그인 상태를 확인할 수 없습니다.")
        result = True
    
    await browser.close()
    await playwright.stop()
    
    return result


if __name__ == "__main__":
    import sys
    
    if len(sys.argv) > 1 and sys.argv[1] == "test":
        # 쿠키 테스트
        asyncio.run(test_cookies())
    else:
        # 쿠키 저장
        asyncio.run(save_cookies())
