"""
Naver Knowledge iN (지식iN) Collector
캠핑장 운영 관련 질문/답변을 수집합니다.
"""
import requests
from datetime import datetime
from typing import List
from .base import BaseCollector, ContentItem
import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from config import NAVER_CLIENT_ID, NAVER_CLIENT_SECRET


class NaverKinCollector(BaseCollector):
    """Collector for Naver Knowledge iN Search API"""

    API_URL = "https://openapi.naver.com/v1/search/kin.json"

    def __init__(self):
        super().__init__("naver_kin")
        self.client_id = NAVER_CLIENT_ID
        self.client_secret = NAVER_CLIENT_SECRET

    def collect(self, keywords: List[str], max_items_per_keyword: int = 10) -> List[ContentItem]:
        if not self.client_id or not self.client_secret:
            self.logger.warning("Naver API credentials not configured.")
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

                    content_item = ContentItem(
                        title=self._clean_text(item.get("title", "")),
                        url=url,
                        source="지식iN",
                        description=self._clean_text(item.get("description", "")),
                        published_date=None,
                        category="커뮤니티"
                    )
                    items.append(content_item)

                self.logger.info(f"Collected kin items for: {keyword}")

            except requests.RequestException as e:
                self.logger.error(f"Error fetching Naver Kin for '{keyword}': {e}")
                continue

        self.logger.info(f"Total collected from Naver Kin: {len(items)} items")
        return items
