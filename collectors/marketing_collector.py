"""
마케팅 인사이트 수집기
=======================
1. 인스타그램 캠핑장 마케팅 성공 사례
2. 네이버 플레이스 광고 인사이트
3. 캠핑장 SNS 마케팅 팁

네이버 블로그/뉴스 검색을 통해 마케팅 관련 콘텐츠를 수집합니다.
"""
import os
import requests
from typing import List
from collectors.base import BaseCollector, ContentItem
from dotenv import load_dotenv

load_dotenv()


class MarketingInsightCollector(BaseCollector):
    """
    캠핑장 마케팅 인사이트 수집기
    - 인스타그램 마케팅 사례
    - 네이버 플레이스 광고 팁
    - SNS 마케팅 성공 사례
    """
    
    NAVER_NEWS_API = "https://openapi.naver.com/v1/search/news.json"
    NAVER_BLOG_API = "https://openapi.naver.com/v1/search/blog.json"
    
    # 마케팅 관련 검색 키워드
    MARKETING_KEYWORDS = [
        # 인스타그램 마케팅
        "캠핑장 인스타그램 마케팅",
        "캠핑장 인스타 광고",
        "글램핑 인스타그램 홍보",
        "캠핑장 SNS 마케팅 성공",
        "캠핑장 인플루언서 마케팅",
        
        # 네이버 플레이스 광고
        "캠핑장 네이버 플레이스",
        "캠핑장 네이버 광고",
        "글램핑 플레이스 등록",
        "캠핑장 예약률 높이는 방법",
        "캠핑장 리뷰 관리",
        
        # 일반 마케팅
        "캠핑장 홍보 방법",
        "캠핑장 마케팅 노하우",
        "캠핑장 예약 늘리기",
    ]
    
    def __init__(self):
        self.client_id = os.getenv("NAVER_CLIENT_ID", "")
        self.client_secret = os.getenv("NAVER_CLIENT_SECRET", "")
        self.headers = {
            "X-Naver-Client-Id": self.client_id,
            "X-Naver-Client-Secret": self.client_secret,
        }
    
    def _search_blog(self, keyword: str, display: int = 5) -> List[dict]:
        """네이버 블로그 검색"""
        try:
            params = {
                "query": keyword,
                "display": display,
                "sort": "sim"  # 정확도순
            }
            response = requests.get(
                self.NAVER_BLOG_API,
                headers=self.headers,
                params=params,
                timeout=10
            )
            if response.status_code == 200:
                return response.json().get("items", [])
        except Exception as e:
            print(f"      ⚠️ 블로그 검색 오류: {e}")
        return []
    
    def _search_news(self, keyword: str, display: int = 5) -> List[dict]:
        """네이버 뉴스 검색"""
        try:
            params = {
                "query": keyword,
                "display": display,
                "sort": "date"  # 최신순
            }
            response = requests.get(
                self.NAVER_NEWS_API,
                headers=self.headers,
                params=params,
                timeout=10
            )
            if response.status_code == 200:
                return response.json().get("items", [])
        except Exception as e:
            print(f"      ⚠️ 뉴스 검색 오류: {e}")
        return []
    
    def _clean_html(self, text: str) -> str:
        """HTML 태그 제거"""
        import re
        clean = re.sub(r'<[^>]+>', '', text)
        clean = clean.replace("&quot;", '"').replace("&amp;", "&")
        clean = clean.replace("&lt;", "<").replace("&gt;", ">")
        return clean.strip()
    
    def collect(self, keywords: List[str] = None) -> List[ContentItem]:
        """마케팅 인사이트 수집"""
        if not self.client_id or not self.client_secret:
            print("   ⚠️ 네이버 API 키가 없습니다.")
            return []
        
        if not keywords:
            keywords = self.MARKETING_KEYWORDS
        
        items = []
        seen_urls = set()
        
        print("   📱 인스타그램 마케팅 글 수집...")
        insta_keywords = [k for k in keywords if "인스타" in k][:3]
        for keyword in insta_keywords:
            results = self._search_blog(keyword, display=3)
            for item in results:
                url = item.get("link", "")
                if url in seen_urls:
                    continue
                seen_urls.add(url)
                
                items.append(ContentItem(
                    title=self._clean_html(item.get("title", "")),
                    url=url,
                    source="블로그",
                    description=self._clean_html(item.get("description", "")),
                    category="인스타마케팅"
                ))
        
        print(f"      ✅ 인스타 마케팅: {len([i for i in items if i.category == '인스타마케팅'])}개")
        
        print("   🗺️ 네이버 플레이스 광고 인사이트 수집...")
        place_keywords = [k for k in keywords if "플레이스" in k or "네이버 광고" in k][:2]
        for keyword in place_keywords:
            results = self._search_blog(keyword, display=3)
            for item in results:
                url = item.get("link", "")
                if url in seen_urls:
                    continue
                seen_urls.add(url)
                
                items.append(ContentItem(
                    title=self._clean_html(item.get("title", "")),
                    url=url,
                    source="블로그",
                    description=self._clean_html(item.get("description", "")),
                    category="플레이스광고"
                ))
        
        print(f"      ✅ 플레이스 광고: {len([i for i in items if i.category == '플레이스광고'])}개")
        
        print("   📈 마케팅 노하우 수집...")
        general_keywords = [k for k in keywords if "마케팅" in k or "홍보" in k][:3]
        for keyword in general_keywords:
            results = self._search_blog(keyword, display=3)
            for item in results:
                url = item.get("link", "")
                if url in seen_urls:
                    continue
                seen_urls.add(url)
                
                items.append(ContentItem(
                    title=self._clean_html(item.get("title", "")),
                    url=url,
                    source="블로그",
                    description=self._clean_html(item.get("description", "")),
                    category="마케팅"
                ))
        
        print(f"      ✅ 일반 마케팅: {len([i for i in items if i.category == '마케팅'])}개")
        
        print(f"   📊 총 마케팅 콘텐츠: {len(items)}개")
        return items


if __name__ == "__main__":
    collector = MarketingInsightCollector()
    items = collector.collect()
    
    print("\n=== 수집된 마케팅 콘텐츠 ===")
    for i, item in enumerate(items[:10], 1):
        print(f"{i}. [{item.category}] {item.title}")
        print(f"   {item.url}")
