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

    OPERATOR_SIGNALS = [
        "운영", "캠핑장 운영", "야영장", "인허가", "허가", "등록", "신고",
        "주류허가", "매점", "환불", "안전", "소방", "위생", "민원",
        "시설", "수익", "매출", "예약", "세금", "사업자",
    ]

    EXCLUDE_SIGNALS = [
        "캠핑카", "1톤", "중고차", "차박", "노지", "프롬비", "빅팬",
        "선풍기", "서큘레이터", "텐트", "캠핑용품", "준비물", "할인",
        "추천", "여행", "후기", "창업", "창업비용", "사업자금",
        "대출", "프랜차이즈", "매매", "양도", "분양",
    ]

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
                    title = self._clean_text(item.get("title", ""))
                    description = self._clean_text(item.get("description", ""))
                    combined = f"{title} {description}".lower()

                    if any(signal.lower() in combined for signal in self.EXCLUDE_SIGNALS):
                        continue

                    operator_score = sum(1 for signal in self.OPERATOR_SIGNALS if signal.lower() in combined)
                    if operator_score < 2:
                        continue

                    seen_urls.add(url)

                    content_item = ContentItem(
                        title=title,
                        url=url,
                        source="지식iN",
                        description=description,
                        published_date=None,
                        category="커뮤니티",
                        score=float(operator_score)
                    )
                    items.append(content_item)

                self.logger.info(f"Collected kin items for: {keyword}")

            except requests.RequestException as e:
                self.logger.error(f"Error fetching Naver Kin for '{keyword}': {e}")
                continue

        self.logger.info(f"Total collected from Naver Kin: {len(items)} items")
        return items
