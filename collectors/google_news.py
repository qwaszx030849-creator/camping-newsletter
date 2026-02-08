"""
Google News RSS Collector
구글 뉴스 RSS 피드를 파싱하여 캠핑 관련 뉴스를 수집합니다.
"""
import feedparser
from datetime import datetime
from typing import List
from urllib.parse import quote
from .base import BaseCollector, ContentItem


class GoogleNewsCollector(BaseCollector):
    """Collector for Google News RSS"""
    
    RSS_BASE_URL = "https://news.google.com/rss/search"
    
    def __init__(self):
        super().__init__("google_news")
    
    def collect(self, keywords: List[str], max_items_per_keyword: int = 10) -> List[ContentItem]:
        """
        Collect news articles from Google News RSS
        
        Args:
            keywords: List of search keywords
            max_items_per_keyword: Maximum items to fetch per keyword
            
        Returns:
            List of ContentItem objects
        """
        items = []
        seen_urls = set()
        
        for keyword in keywords:
            try:
                # Build RSS URL for Korean news
                encoded_keyword = quote(keyword)
                rss_url = f"{self.RSS_BASE_URL}?q={encoded_keyword}&hl=ko&gl=KR&ceid=KR:ko"
                
                feed = feedparser.parse(rss_url)
                
                count = 0
                for entry in feed.entries:
                    if count >= max_items_per_keyword:
                        break
                    
                    url = entry.get("link", "")
                    
                    # Skip duplicates
                    if url in seen_urls:
                        continue
                    seen_urls.add(url)
                    
                    # Parse date
                    pub_date = None
                    if entry.get("published_parsed"):
                        try:
                            pub_date = datetime(*entry.published_parsed[:6])
                        except (TypeError, ValueError):
                            pass
                    
                    content_item = ContentItem(
                        title=self._clean_text(entry.get("title", "")),
                        url=url,
                        source="구글 뉴스",
                        description=self._clean_text(entry.get("summary", "")),
                        published_date=pub_date,
                        category="뉴스"
                    )
                    items.append(content_item)
                    count += 1
                
                self.logger.info(f"Collected {count} items for keyword: {keyword}")
                
            except Exception as e:
                self.logger.error(f"Error fetching Google News for '{keyword}': {e}")
                continue
        
        self.logger.info(f"Total collected from Google News: {len(items)} items")
        return items


if __name__ == "__main__":
    # Test the collector
    collector = GoogleNewsCollector()
    items = collector.collect(["캠핑장 운영", "캠핑장 지원사업"])
    for item in items[:5]:
        print(f"- {item.title}")
        print(f"  URL: {item.url}")
        print()
