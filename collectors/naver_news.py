"""
Naver News API Collector
네이버 뉴스 검색 API를 사용하여 캠핑 관련 뉴스를 수집합니다.
"""
import requests
from datetime import datetime
from typing import List
from .base import BaseCollector, ContentItem, logger
import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from config import NAVER_CLIENT_ID, NAVER_CLIENT_SECRET


class NaverNewsCollector(BaseCollector):
    """Collector for Naver News API"""
    
    API_URL = "https://openapi.naver.com/v1/search/news.json"
    
    def __init__(self):
        super().__init__("naver_news")
        self.client_id = NAVER_CLIENT_ID
        self.client_secret = NAVER_CLIENT_SECRET
    
    def collect(self, keywords: List[str], max_items_per_keyword: int = 10) -> List[ContentItem]:
        """
        Collect news articles from Naver News API
        
        Args:
            keywords: List of search keywords
            max_items_per_keyword: Maximum items to fetch per keyword
            
        Returns:
            List of ContentItem objects
        """
        if not self.client_id or not self.client_secret:
            self.logger.warning("Naver API credentials not configured. Skipping Naver News collection.")
            return []
        
        items = []
        seen_urls = set()
        
        headers = {
            "X-Naver-Client-Id": self.client_id,
            "X-Naver-Client-Secret": self.client_secret
        }
        
        for keyword in keywords:
            try:
                params = {
                    "query": keyword,
                    "display": max_items_per_keyword,
                    "start": 1,
                    "sort": "date"  # 최신순
                }
                
                response = requests.get(self.API_URL, headers=headers, params=params, timeout=10)
                response.raise_for_status()
                
                data = response.json()
                
                for item in data.get("items", []):
                    url = item.get("link", "")
                    
                    # Skip duplicates
                    if url in seen_urls:
                        continue
                    seen_urls.add(url)
                    
                    # Parse date
                    pub_date = None
                    if item.get("pubDate"):
                        try:
                            pub_date = datetime.strptime(
                                item["pubDate"], 
                                "%a, %d %b %Y %H:%M:%S %z"
                            )
                        except ValueError:
                            pass
                    
                    content_item = ContentItem(
                        title=self._clean_text(item.get("title", "")),
                        url=url,
                        source="네이버 뉴스",
                        description=self._clean_text(item.get("description", "")),
                        published_date=pub_date,
                        category="뉴스"
                    )
                    items.append(content_item)
                    
                self.logger.info(f"Collected {len(data.get('items', []))} items for keyword: {keyword}")
                
            except requests.RequestException as e:
                self.logger.error(f"Error fetching Naver News for '{keyword}': {e}")
                continue
        
        self.logger.info(f"Total collected from Naver News: {len(items)} items")
        return items


if __name__ == "__main__":
    # Test the collector
    collector = NaverNewsCollector()
    items = collector.collect(["캠핑장 운영", "글램핑 트렌드"])
    for item in items[:5]:
        print(f"- {item.title}")
        print(f"  URL: {item.url}")
        print()
