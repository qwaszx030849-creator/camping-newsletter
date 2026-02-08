"""
Naver Cafe Playwright Crawler
네이버 카페에 로그인하여 게시글을 수집합니다.

타겟 카페:
1. 캠차 (camcha)
2. 초캠장터 (autocamping) 
3. 캠핑퍼스트 (campingfirst)
4. 차박캠핑클럽 (chabakcamping)
5. 차박은내친구 (myfriendchabak)
6. 달구지캠핑 (dalguji)
"""
import asyncio
import os
import re
import json
from datetime import datetime, timedelta
from typing import List, Dict, Optional
from dataclasses import dataclass
from playwright.async_api import async_playwright, Page, Browser, BrowserContext
from dotenv import load_dotenv

load_dotenv()

# 쿠키 파일 경로
COOKIES_FILE = os.path.join(os.path.dirname(os.path.dirname(__file__)), "naver_cookies.json")


@dataclass
class CafeArticle:
    """카페 게시글 데이터"""
    title: str
    url: str
    cafe_name: str
    board_name: str
    author: str
    date: Optional[datetime]
    view_count: int
    like_count: int
    content_preview: str


class NaverCafePlaywrightCrawler:
    """
    Playwright 기반 네이버 카페 크롤러
    """
    
    # 타겟 카페 목록 (카페 URL ID)
    TARGET_CAFES = {
        # 카페ID: (카페명, 관심 게시판 키워드)
        "musicstar2": ("캠차", ["캠핑장", "후기", "추천", "사장님"]),
        "chocammall": ("초캠장터", ["캠핑장", "후기", "정보", "운영"]),
        "campingfirst": ("캠핑퍼스트", ["캠핑장", "운영", "사장", "시설"]),
        "chcamping": ("차박캠핑클럽", ["캠핑장", "후기", "추천", "차박"]),
        "gpsf": ("차박은내친구", ["캠핑장", "후기", "차박지"]),
        "joycamping": ("조이캠핑", ["캠핑장", "후기", "글램핑", "정보"]),
    }
    
    # 캠핑장 운영자 관점 필터 키워드
    OPERATOR_KEYWORDS = [
        "사장님", "운영자", "청결", "친절", "시설", "화장실", "샤워장",
        "재방문", "만족", "추천", "좋았", "최고", "서비스", "관리",
        "조용", "깨끗", "넓", "예약", "사이트", "전기", "수도",
    ]
    
    # 광고성/공지성 글 제외 키워드
    EXCLUDE_KEYWORDS = [
        # 카페 공지
        "스티커", "활동정지", "강제탈퇴", "카페 선정", "대표카페", "숲카페",
        "공지", "안내", "규정", "운영진",
        # 예약 광고
        "예약오픈", "사전예약", "예약이벤트", "1빠", "선착순",
        # 이벤트/프로모션
        "무료입장권", "입장권", "할인 이벤트", "이벤트",
        # 캠핑용품 판매
        "판매", "매트", "침낭", "텐트", "캠핑매트", "이너매트",
        "접이식", "차량용품", "루트웨이",
        # 차박지 정보 (운영과 무관)
        "차박지공유", "주차장", "무료주차",
    ]
    
    def __init__(self):
        self.naver_id = os.getenv("NAVER_ID", "")
        self.naver_pw = os.getenv("NAVER_PW", "")
        self.browser: Optional[Browser] = None
        self.context: Optional[BrowserContext] = None
        self.page: Optional[Page] = None
        self.is_logged_in = False
        self.playwright = None
    
    def _load_cookies(self) -> Optional[List[dict]]:
        """저장된 쿠키 파일 로드"""
        if os.path.exists(COOKIES_FILE):
            try:
                with open(COOKIES_FILE, "r", encoding="utf-8") as f:
                    cookies = json.load(f)
                    print(f"   📂 저장된 쿠키 로드: {len(cookies)}개")
                    return cookies
            except Exception as e:
                print(f"   ⚠️ 쿠키 로드 실패: {e}")
        return None
        
    async def start(self, headless: bool = True):
        """브라우저 시작 및 쿠키 로드"""
        self.playwright = await async_playwright().start()
        self.browser = await self.playwright.chromium.launch(
            headless=headless,
            args=['--disable-blink-features=AutomationControlled']
        )
        self.context = await self.browser.new_context()
        
        # 저장된 쿠키가 있으면 로드
        cookies = self._load_cookies()
        if cookies:
            await self.context.add_cookies(cookies)
            self.is_logged_in = True
            print("   ✅ 쿠키로 로그인 상태 복원")
        
        self.page = await self.context.new_page()
        
        # 봇 탐지 우회
        await self.page.add_init_script("""
            Object.defineProperty(navigator, 'webdriver', {
                get: () => undefined
            });
        """)
        
    async def close(self):
        """브라우저 종료"""
        try:
            if self.browser:
                await self.browser.close()
        except Exception:
            pass
        try:
            if self.playwright:
                await self.playwright.stop()
        except Exception:
            pass
            
    async def login(self) -> bool:
        """네이버 로그인"""
        if not self.naver_id or not self.naver_pw:
            print("❌ 네이버 로그인 정보가 없습니다.")
            return False
            
        try:
            print("🔐 네이버 로그인 시도 중...")
            
            # 네이버 로그인 페이지
            await self.page.goto("https://nid.naver.com/nidlogin.login")
            await self.page.wait_for_timeout(2000)
            
            # 아이디 입력 (클립보드 방식으로 봇 탐지 우회)
            await self.page.evaluate(f"""
                document.querySelector('#id').value = '{self.naver_id}';
            """)
            await self.page.wait_for_timeout(500)
            
            # 비밀번호 입력
            await self.page.evaluate(f"""
                document.querySelector('#pw').value = '{self.naver_pw}';
            """)
            await self.page.wait_for_timeout(500)
            
            # 로그인 버튼 클릭
            await self.page.click("#log\\.login")
            await self.page.wait_for_timeout(3000)
            
            # 로그인 성공 확인
            if "nid.naver.com" not in self.page.url:
                print("✅ 네이버 로그인 성공!")
                self.is_logged_in = True
                return True
            else:
                print("❌ 로그인 실패 - 캡차 또는 보안 문제 발생 가능")
                return False
                
        except Exception as e:
            print(f"❌ 로그인 오류: {e}")
            return False
    
    async def crawl_cafe_search(self, cafe_id: str, keyword: str, max_items: int = 10) -> List[CafeArticle]:
        """
        카페 내 검색으로 게시글 수집
        """
        articles = []
        cafe_name = self.TARGET_CAFES.get(cafe_id, (cafe_id, []))[0]
        
        try:
            # 카페 검색 URL
            search_url = f"https://cafe.naver.com/{cafe_id}?iframe_url=/ArticleSearchList.nhn%3Fsearch.query%3D{keyword}%26search.sortBy%3Ddate"
            
            await self.page.goto(search_url, wait_until="networkidle", timeout=30000)
            await self.page.wait_for_timeout(2000)
            
            # iframe 접근
            frame = self.page.frame(name="cafe_main")
            if not frame:
                print(f"   ⚠️ {cafe_name} 카페 프레임 접근 실패")
                return articles
            
            # 게시글 목록 수집
            article_elements = await frame.query_selector_all("a.article")
            
            for elem in article_elements[:max_items]:
                try:
                    title = await elem.inner_text()
                    href = await elem.get_attribute("href")
                    
                    if not title or not href:
                        continue
                    
                    # URL 생성
                    if href.startswith("/"):
                        url = f"https://cafe.naver.com{href}"
                    else:
                        url = href
                    
                    article = CafeArticle(
                        title=title.strip(),
                        url=url,
                        cafe_name=cafe_name,
                        board_name=keyword,
                        author="",
                        date=None,
                        view_count=0,
                        like_count=0,
                        content_preview=""
                    )
                    articles.append(article)
                    
                except Exception as e:
                    continue
            
            print(f"   📄 {cafe_name} '{keyword}': {len(articles)}개 수집")
            
        except Exception as e:
            print(f"   ❌ {cafe_name} 크롤링 오류: {e}")
        
        return articles
    
    async def crawl_popular_articles(self, cafe_id: str, max_items: int = 10) -> List[CafeArticle]:
        """
        카페 인기글 수집
        """
        articles = []
        cafe_name = self.TARGET_CAFES.get(cafe_id, (cafe_id, []))[0]
        
        try:
            # 카페 메인 페이지
            await self.page.goto(f"https://cafe.naver.com/{cafe_id}", wait_until="networkidle", timeout=30000)
            await self.page.wait_for_timeout(2000)
            
            # iframe 접근
            frame = self.page.frame(name="cafe_main")
            if not frame:
                return articles
            
            # 인기글/최신글 목록
            article_links = await frame.query_selector_all("a.article, a.board-list__item")
            
            for elem in article_links[:max_items]:
                try:
                    title = await elem.inner_text()
                    href = await elem.get_attribute("href")
                    
                    if title and href:
                        url = f"https://cafe.naver.com{href}" if href.startswith("/") else href
                        
                        # 캠핑장 관련 키워드 필터링
                        if any(kw in title for kw in ["캠핑장", "캠핑", "차박", "글램핑", "카라반"]):
                            article = CafeArticle(
                                title=title.strip(),
                                url=url,
                                cafe_name=cafe_name,
                                board_name="인기글",
                                author="",
                                date=None,
                                view_count=0,
                                like_count=0,
                                content_preview=""
                            )
                            articles.append(article)
                            
                except Exception:
                    continue
            
            print(f"   🔥 {cafe_name} 인기글: {len(articles)}개 수집")
            
        except Exception as e:
            print(f"   ❌ {cafe_name} 인기글 오류: {e}")
        
        return articles
    
    async def crawl_all_cafes(self, keywords: List[str] = None, max_per_cafe: int = 5) -> List[CafeArticle]:
        """
        모든 타겟 카페에서 게시글 수집
        """
        if not keywords:
            keywords = ["캠핑장 후기", "캠핑장 추천", "캠핑장 사장님"]
        
        all_articles = []
        
        # 브라우저 시작 및 로그인
        await self.start(headless=True)
        login_success = await self.login()
        
        if not login_success:
            print("⚠️ 로그인 없이 공개 게시글만 수집합니다.")
        
        try:
            for cafe_id, (cafe_name, _) in self.TARGET_CAFES.items():
                print(f"\n🏕️ {cafe_name} 카페 크롤링...")
                
                # 각 키워드로 검색
                for keyword in keywords[:2]:
                    articles = await self.crawl_cafe_search(cafe_id, keyword, max_per_cafe)
                    all_articles.extend(articles)
                    await asyncio.sleep(1)  # Rate limiting
                
                # 인기글/최신글
                popular = await self.crawl_popular_articles(cafe_id, max_per_cafe)
                all_articles.extend(popular)
                
                await asyncio.sleep(2)  # 카페 간 딜레이
                
        finally:
            await self.close()
        
        # 중복 제거
        seen_urls = set()
        unique_articles = []
        for article in all_articles:
            if article.url not in seen_urls:
                seen_urls.add(article.url)
                unique_articles.append(article)
        
        print(f"\n📊 중복 제거 후: {len(unique_articles)}개 게시글")
        
        # 광고성 글 필터링
        filtered_articles = self.filter_operator_relevant(unique_articles)
        
        print(f"📊 최종 수집: {len(filtered_articles)}개 게시글")
        return filtered_articles
    
    def filter_operator_relevant(self, articles: List[CafeArticle]) -> List[CafeArticle]:
        """
        캠핑장 운영자에게 유용한 게시글 필터링
        - 광고성/공지성 글 제외
        - 운영자 관점 키워드 포함 글 우선
        """
        filtered = []
        for article in articles:
            title = article.title
            
            # 1. 광고성/공지성 글 제외 (EXCLUDE_KEYWORDS)
            is_excluded = any(kw in title for kw in self.EXCLUDE_KEYWORDS)
            if is_excluded:
                print(f"      ❌ 제외: {title[:30]}...")
                continue
            
            # 2. 운영자 관련 키워드 포함 여부
            relevance_score = sum(1 for kw in self.OPERATOR_KEYWORDS if kw in title)
            
            # 키워드 있으면 우선 추가, 없어도 일단 포함 (AI 필터에서 걸러짐)
            filtered.append(article)
        
        print(f"      ✅ 사전 필터: {len(articles)}개 → {len(filtered)}개")
        return filtered


# 기존 수집기와 호환되는 인터페이스
def collect_from_cafes_sync(keywords: List[str] = None) -> List[dict]:
    """동기 인터페이스 - main.py에서 호출용"""
    async def _collect():
        crawler = NaverCafePlaywrightCrawler()
        articles = await crawler.crawl_all_cafes(keywords)
        
        # ContentItem 형식으로 변환
        result = []
        for article in articles:
            result.append({
                "title": article.title,
                "url": article.url,
                "source": f"카페: {article.cafe_name}",
                "description": article.content_preview or f"{article.board_name} 게시글",
                "category": "카페",
            })
        return result
    
    return asyncio.run(_collect())


if __name__ == "__main__":
    # 테스트 실행
    print("=" * 50)
    print("🏕️ 네이버 카페 크롤러 테스트")
    print("=" * 50)
    
    async def test():
        crawler = NaverCafePlaywrightCrawler()
        articles = await crawler.crawl_all_cafes(
            keywords=["캠핑장 후기", "캠핑장 추천"],
            max_per_cafe=3
        )
        
        print("\n=== 수집된 게시글 ===")
        for i, article in enumerate(articles[:10], 1):
            print(f"{i}. [{article.cafe_name}] {article.title}")
            print(f"   URL: {article.url}")
            print()
    
    asyncio.run(test())
