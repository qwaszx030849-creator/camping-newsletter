"""
Naver Blog Search Collector
네이버 블로그 검색 API를 사용하여 캠핑 관련 블로그 포스트를 수집합니다.
"""
import requests
from datetime import datetime
from typing import List
from .base import BaseCollector, ContentItem
import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from config import NAVER_CLIENT_ID, NAVER_CLIENT_SECRET


class NaverBlogCollector(BaseCollector):
    """Collector for Naver Blog Search API"""
    
    API_URL = "https://openapi.naver.com/v1/search/blog.json"
    
    def __init__(self):
        super().__init__("naver_blog")
        self.client_id = NAVER_CLIENT_ID
        self.client_secret = NAVER_CLIENT_SECRET
    
    def collect(self, keywords: List[str], max_items_per_keyword: int = 10) -> List[ContentItem]:
        """
        Collect blog posts from Naver Blog Search API
        
        Args:
            keywords: List of search keywords
            max_items_per_keyword: Maximum items to fetch per keyword
            
        Returns:
            List of ContentItem objects
        """
        if not self.client_id or not self.client_secret:
            self.logger.warning("Naver API credentials not configured. Skipping Naver Blog collection.")
            return []
        
        items = []
        seen_urls = set()
        
        # 캠핑장 관련 필수 키워드 (제목이나 내용에 하나라도 있어야 함)
        CAMPING_REQUIRED_WORDS = [
            "캠핑장", "글램핑", "야영장", "오토캠핑", "카라반",
            "펜션", "캠지기", "캠핑사이트"
        ]
        
        headers = {
            "X-Naver-Client-Id": self.client_id,
            "X-Naver-Client-Secret": self.client_secret
        }
        
        for keyword in keywords:
            try:
                # 키워드 자체만 사용 (추가 단어 없이 원본 키워드 검색)
                search_query = keyword
                
                params = {
                    "query": search_query,
                    "display": max_items_per_keyword * 5,  # 중복 제거 위해 충분히 가져옴
                    "start": 1,
                    "sort": "date"  # 날짜순으로 매주 새로운 콘텐츠 확보
                }
                
                response = requests.get(self.API_URL, headers=headers, params=params, timeout=10)
                response.raise_for_status()
                
                data = response.json()
                count = 0
                
                for item in data.get("items", []):
                    if count >= max_items_per_keyword:
                        break
                    
                    url = item.get("link", "")
                    title = self._clean_text(item.get("title", ""))
                    description = self._clean_text(item.get("description", ""))
                    
                    if url in seen_urls:
                        continue
                    
                    # 🔍 캠핑장 관련 필터링: 제목이나 설명에 캠핑장 관련 단어가 있어야 함
                    combined_text = f"{title} {description}".lower()
                    is_camping_related = any(word in combined_text for word in CAMPING_REQUIRED_WORDS)
                    
                    if not is_camping_related:
                        continue  # 캠핑장과 무관한 글 제외
                    
                    seen_urls.add(url)
                    
                    # Parse date (format: YYYYMMDD)
                    pub_date = None
                    if item.get("postdate"):
                        try:
                            pub_date = datetime.strptime(item["postdate"], "%Y%m%d")
                        except ValueError:
                            pass
                    
                    content_item = ContentItem(
                        title=title,
                        url=url,
                        source="네이버 블로그",
                        description=description,
                        published_date=pub_date,
                        category="블로그"
                    )
                    items.append(content_item)
                    count += 1
                
                self.logger.info(f"Collected {count} camping-related blog posts for keyword: {keyword}")
                
            except requests.RequestException as e:
                self.logger.error(f"Error fetching Naver Blog for '{keyword}': {e}")
                continue
        
        self.logger.info(f"Total collected from Naver Blog: {len(items)} items")
        return items


class TistoryCollector(BaseCollector):
    """
    Collector for Tistory blogs via Naver/Google search
    티스토리는 별도 API가 없어 검색 엔진을 통해 수집합니다.
    """
    
    API_URL = "https://openapi.naver.com/v1/search/blog.json"
    
    def __init__(self):
        super().__init__("tistory")
        self.client_id = NAVER_CLIENT_ID
        self.client_secret = NAVER_CLIENT_SECRET
    
    def collect(self, keywords: List[str], max_items_per_keyword: int = 5) -> List[ContentItem]:
        """Collect Tistory posts by searching with site filter"""
        if not self.client_id or not self.client_secret:
            self.logger.warning("Naver API credentials not configured. Skipping Tistory collection.")
            return []
        
        items = []
        seen_urls = set()
        
        headers = {
            "X-Naver-Client-Id": self.client_id,
            "X-Naver-Client-Secret": self.client_secret
        }
        
        for keyword in keywords:
            try:
                # Search with tistory site filter
                search_query = f"{keyword} site:tistory.com"
                
                params = {
                    "query": search_query,
                    "display": max_items_per_keyword,
                    "start": 1,
                    "sort": "date"
                }
                
                response = requests.get(self.API_URL, headers=headers, params=params, timeout=10)
                response.raise_for_status()
                
                data = response.json()
                
                for item in data.get("items", []):
                    url = item.get("link", "")
                    
                    # Only include tistory.com URLs
                    if "tistory.com" not in url:
                        continue
                    
                    if url in seen_urls:
                        continue
                    seen_urls.add(url)
                    
                    pub_date = None
                    if item.get("postdate"):
                        try:
                            pub_date = datetime.strptime(item["postdate"], "%Y%m%d")
                        except ValueError:
                            pass
                    
                    content_item = ContentItem(
                        title=self._clean_text(item.get("title", "")),
                        url=url,
                        source="티스토리",
                        description=self._clean_text(item.get("description", "")),
                        published_date=pub_date,
                        category="블로그"
                    )
                    items.append(content_item)
                
                self.logger.info(f"Collected Tistory posts for keyword: {keyword}")
                
            except requests.RequestException as e:
                self.logger.error(f"Error fetching Tistory for '{keyword}': {e}")
                continue
        
        self.logger.info(f"Total collected from Tistory: {len(items)} items")
        return items


if __name__ == "__main__":
    # Test the collectors
    print("=== Naver Blog ===")
    collector = NaverBlogCollector()
    items = collector.collect(["캠핑장 운영"])
    for item in items[:3]:
        print(f"- {item.title}")
        print(f"  URL: {item.url}")
        print()
    
    print("=== Tistory ===")
    collector = TistoryCollector()
    items = collector.collect(["캠핑장 운영"])
    for item in items[:3]:
        print(f"- {item.title}")
        print(f"  URL: {item.url}")
        print()
