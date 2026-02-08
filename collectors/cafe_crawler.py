"""
Naver Cafe Direct Crawler
네이버 카페에서 직접 게시글을 크롤링합니다.
Playwright를 사용하여 로그인 후 게시글을 수집합니다.
"""
import asyncio
import json
import os
from datetime import datetime
from typing import List, Optional
from playwright.async_api import async_playwright, Page
from .base import BaseCollector, ContentItem


class CafeCrawler(BaseCollector):
    """
    네이버 카페 직접 크롤러
    
    주요 타겟 카페:
    - 나무꾼77 (namuggun77): 캠핑장 운영자 커뮤니티
    - 캠핑퍼스트 (campingfirst): 캠퍼/운영자 혼합
    """
    
    # 크롤링할 카페 목록
    TARGET_CAFES = {
        "namuggun77": {
            "name": "나무꾼77",
            "url": "https://cafe.naver.com/namuggun77",
            "boards": ["캠핑장후기", "운영노하우", "시설투자"]
        },
        "campingfirst": {
            "name": "캠핑퍼스트", 
            "url": "https://cafe.naver.com/campingfirst",
            "boards": ["캠핑장추천", "캠핑후기"]
        },
    }
    
    def __init__(self):
        super().__init__("cafe_crawler")
        self.browser = None
        self.context = None
    
    async def _init_browser(self):
        """Initialize Playwright browser"""
        playwright = await async_playwright().start()
        self.browser = await playwright.chromium.launch(headless=True)
        self.context = await self.browser.new_context(
            user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
        )
    
    async def _close_browser(self):
        """Close browser"""
        if self.context:
            await self.context.close()
        if self.browser:
            await self.browser.close()
    
    async def _crawl_cafe_search(self, cafe_id: str, keyword: str, max_items: int = 10) -> List[ContentItem]:
        """
        카페 내 검색을 통해 게시글 수집
        """
        items = []
        cafe_info = self.TARGET_CAFES.get(cafe_id, {})
        cafe_name = cafe_info.get("name", cafe_id)
        
        try:
            page = await self.context.new_page()
            
            # 카페 검색 URL
            search_url = f"https://cafe.naver.com/{cafe_id}?iframe_url=/ArticleSearchList.nhn%3Fsearch.query%3D{keyword}%26search.sortBy%3Ddate"
            
            await page.goto(search_url, wait_until="networkidle", timeout=30000)
            await page.wait_for_timeout(2000)
            
            # iframe 내부 접근
            try:
                frame = page.frame(name="cafe_main")
                if frame:
                    # 게시글 목록 추출
                    articles = await frame.query_selector_all("a.article")
                    
                    for article in articles[:max_items]:
                        try:
                            title = await article.inner_text()
                            href = await article.get_attribute("href")
                            
                            if href and title:
                                url = f"https://cafe.naver.com{href}" if href.startswith("/") else href
                                
                                items.append(ContentItem(
                                    title=title.strip(),
                                    url=url,
                                    source=f"카페: {cafe_name}",
                                    description=f"[{keyword}] 관련 게시글",
                                    category="카페"
                                ))
                        except Exception as e:
                            self.logger.debug(f"Error parsing article: {e}")
                            continue
            except Exception as e:
                self.logger.warning(f"Could not access cafe iframe: {e}")
            
            await page.close()
            
        except Exception as e:
            self.logger.error(f"Error crawling cafe {cafe_id}: {e}")
        
        return items
    
    async def crawl_async(self, keywords: List[str], max_items: int = 20) -> List[ContentItem]:
        """
        비동기로 모든 카페에서 콘텐츠 수집
        """
        all_items = []
        
        await self._init_browser()
        
        try:
            for cafe_id in self.TARGET_CAFES:
                for keyword in keywords[:3]:  # 상위 3개 키워드만
                    items = await self._crawl_cafe_search(cafe_id, keyword, max_items=5)
                    all_items.extend(items)
                    self.logger.info(f"Crawled {len(items)} items from {cafe_id} for '{keyword}'")
                    await asyncio.sleep(1)  # Rate limiting
                    
        finally:
            await self._close_browser()
        
        # 중복 제거
        seen_urls = set()
        unique_items = []
        for item in all_items:
            if item.url not in seen_urls:
                seen_urls.add(item.url)
                unique_items.append(item)
        
        self.logger.info(f"Total unique items from cafes: {len(unique_items)}")
        return unique_items
    
    def collect(self, keywords: List[str]) -> List[ContentItem]:
        """
        동기 인터페이스 (BaseCollector 호환)
        """
        return asyncio.run(self.crawl_async(keywords))


class SimpleCafeCollector(BaseCollector):
    """
    네이버 카페 검색 API를 활용한 간단한 수집기 (로그인 불필요)
    기존 cafe_collector.py보다 더 타겟팅된 검색
    """
    
    import requests
    
    API_URL = "https://openapi.naver.com/v1/search/cafearticle.json"
    
    # 캠핑장 운영자 관점 키워드
    OPERATOR_KEYWORDS = [
        # 고객 후기 분석
        "캠핑장 재방문 후기",
        "캠핑장 사장님 친절",
        "캠핑장 시설 깨끗",
        "캠핑장 서비스 만족",
        
        # 운영 노하우
        "캠핑장 운영 노하우",
        "캠핑장 매출 증가",
        "캠핑장 예약 관리",
        
        # 시설 투자
        "글램핑 시설 후기",
        "카라반 도입 후기",
        "캠핑장 리모델링",
    ]
    
    def __init__(self):
        super().__init__("simple_cafe")
        import sys
        import os
        sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
        from config import NAVER_CLIENT_ID, NAVER_CLIENT_SECRET
        self.client_id = NAVER_CLIENT_ID
        self.client_secret = NAVER_CLIENT_SECRET
    
    def collect(self, keywords: List[str] = None) -> List[ContentItem]:
        """카페 검색으로 운영자 관련 콘텐츠 수집"""
        import requests
        
        if not self.client_id or not self.client_secret:
            self.logger.warning("Naver API credentials not configured")
            return []
        
        search_keywords = keywords or self.OPERATOR_KEYWORDS
        items = []
        seen_urls = set()
        
        headers = {
            "X-Naver-Client-Id": self.client_id,
            "X-Naver-Client-Secret": self.client_secret
        }
        
        for keyword in search_keywords[:8]:  # 상위 8개 키워드
            try:
                params = {
                    "query": keyword,
                    "display": 5,
                    "sort": "date"
                }
                
                response = requests.get(self.API_URL, headers=headers, params=params, timeout=10)
                response.raise_for_status()
                
                data = response.json()
                
                for item in data.get("items", []):
                    url = item.get("link", "")
                    
                    if url in seen_urls:
                        continue
                    seen_urls.add(url)
                    
                    cafe_name = item.get("cafename", "네이버 카페")
                    
                    content_item = ContentItem(
                        title=self._clean_text(item.get("title", "")),
                        url=url,
                        source=f"카페: {cafe_name}",
                        description=self._clean_text(item.get("description", "")),
                        category="카페"
                    )
                    items.append(content_item)
                
                self.logger.info(f"Collected cafe articles for: {keyword}")
                
            except Exception as e:
                self.logger.error(f"Error: {e}")
                continue
        
        self.logger.info(f"Total from cafe search: {len(items)} items")
        return items


if __name__ == "__main__":
    # Test simple collector
    collector = SimpleCafeCollector()
    items = collector.collect()
    
    print(f"\n=== Collected {len(items)} items ===")
    for item in items[:5]:
        print(f"- {item.title}")
        print(f"  Source: {item.source}")
        print(f"  URL: {item.url}")
        print()
