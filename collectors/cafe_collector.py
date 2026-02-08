"""
Naver Cafe Collector
네이버 카페 (캠핑퍼스트, 초캠장터 등) 게시글을 수집합니다.

Note: 네이버 카페는 공식 API가 제한적이므로 
네이버 카페 검색 API를 활용합니다.
"""
import requests
from datetime import datetime
from typing import List
from .base import BaseCollector, ContentItem
import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from config import NAVER_CLIENT_ID, NAVER_CLIENT_SECRET


class NaverCafeCollector(BaseCollector):
    """Collector for Naver Cafe Search API"""
    
    API_URL = "https://openapi.naver.com/v1/search/cafearticle.json"
    
    # Target cafes for camping business content
    TARGET_CAFES = [
        "캠핑퍼스트",
        "초캠장터", 
        "오토캠핑",
        "캠핑클럽",
    ]
    
    def __init__(self):
        super().__init__("naver_cafe")
        self.client_id = NAVER_CLIENT_ID
        self.client_secret = NAVER_CLIENT_SECRET
    
    def collect(self, keywords: List[str], max_items_per_keyword: int = 10) -> List[ContentItem]:
        """
        Collect cafe articles from Naver Cafe Search API
        
        Args:
            keywords: List of search keywords
            max_items_per_keyword: Maximum items to fetch per keyword
            
        Returns:
            List of ContentItem objects
        """
        if not self.client_id or not self.client_secret:
            self.logger.warning("Naver API credentials not configured. Skipping Naver Cafe collection.")
            return []
        
        items = []
        seen_urls = set()
        
        headers = {
            "X-Naver-Client-Id": self.client_id,
            "X-Naver-Client-Secret": self.client_secret
        }
        
        # Search with camping-related keywords
        business_keywords = [
            "캠핑장 운영",
            "캠핑장 사장",
            "캠핑장 창업",
            "캠핑장 시설",
            "캠핑장 마케팅",
        ]
        
        search_keywords = keywords + business_keywords
        
        for keyword in search_keywords:
            try:
                params = {
                    "query": keyword,
                    "display": max_items_per_keyword,
                    "start": 1,
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
                    
                    # Get cafe name from the response
                    cafe_name = item.get("cafename", "네이버 카페")
                    
                    content_item = ContentItem(
                        title=self._clean_text(item.get("title", "")),
                        url=url,
                        source=f"카페: {cafe_name}",
                        description=self._clean_text(item.get("description", "")),
                        published_date=None,  # Cafe API doesn't return date
                        category="커뮤니티"
                    )
                    items.append(content_item)
                
                self.logger.info(f"Collected {len(data.get('items', []))} cafe articles for keyword: {keyword}")
                
            except requests.RequestException as e:
                self.logger.error(f"Error fetching Naver Cafe for '{keyword}': {e}")
                continue
        
        self.logger.info(f"Total collected from Naver Cafe: {len(items)} items")
        return items


if __name__ == "__main__":
    # Test the collector
    collector = NaverCafeCollector()
    items = collector.collect(["캠핑장 운영", "글램핑"])
    for item in items[:5]:
        print(f"- {item.title}")
        print(f"  Source: {item.source}")
        print(f"  URL: {item.url}")
        print()
