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

    OPERATOR_SIGNALS = [
        "캠지기", "운영", "사장", "대표", "관리", "정비", "요금", "가격",
        "예약률", "예약 관리", "환불", "민원", "불만", "리뷰", "별점",
        "매출", "수익", "비수기", "성수기", "시설", "공사", "보수",
        "데크", "파쇄석", "타프존", "수영장", "샤워실", "화장실",
        "안전", "인허가", "등록", "신고", "주류허가", "지원사업",
    ]

    EXCLUDE_SIGNALS = [
        # 소비자용 후기/할인/홍보
        "할인 받는 팁", "할인받는 팁", "할인 받는법", "할인받는법",
        "할인 쿠폰", "입장권", "무료입장권", "참가자발표", "행사 예고",
        "예약 방법", "예약방법", "이용 안내", "다녀왔", "다녀온",
        "방문 후기", "솔직 후기", "이용 후기", "방문기", "1박", "2박", "추천", "가볼만한",
        "정기 캠핑", "정캠", "뉴스레터", "공지", "예약 숙소", "물놀이 명당",
        # 캠핑카/차량/용품
        "캠핑카", "캠핑트레일러", "카라반 구매", "카라반 매매",
        "1톤", "중고차", "정비업창업", "루프탑", "차박", "노지",
        "프롬비", "빅팬", "선풍기", "서큘레이터", "텐트", "타프 추천",
        "캠핑용품", "장비", "필수템", "준비물",
        # 광고/창업/매물
        "산으로간니모", "제휴마케팅", "광고", "홍보글", "홍보 글",
        "협찬", "체험단", "커미션", "구매링크", "파트너스",
        "창업", "사업자금", "대출", "매매", "양도", "급매", "분양", "매입 운영",
        "마케팅 대행", "광고 대행", "무료 상담", "상담 문의",
    ]

    REVIEW_INSIGHT_SIGNALS = [
        "재방문", "또 가고", "사장님 친절", "친절", "응대",
        "청결", "깨끗", "화장실", "샤워실", "개수대",
        "수영장", "물놀이", "아이", "체험", "프로그램",
        "반려견", "애견", "울타리", "사이트 간격", "사이트 배치",
        "매너타임", "소음", "환불", "양도", "예약", "불편", "관리",
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
        
        # Search with camping-site operator keywords.
        business_keywords = [
            "캠핑장 운영",
            "캠핑장 사장",
            "캠핑장 시설",
            "캠핑장 마케팅",
            "캠지기 운영",
            "야영장 인허가",
            "캠핑장 환불",
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
                    title = self._clean_text(item.get("title", ""))
                    description = self._clean_text(item.get("description", ""))
                    combined = f"{title} {description}".lower()
                    review_insight_score = sum(
                        1 for signal in self.REVIEW_INSIGHT_SIGNALS
                        if signal.lower() in combined
                    )
                    has_review_insight = review_insight_score >= 2

                    if any(signal.lower() in combined for signal in self.EXCLUDE_SIGNALS) and not has_review_insight:
                        continue

                    operator_score = sum(1 for signal in self.OPERATOR_SIGNALS if signal.lower() in combined)
                    if operator_score < 2 and not has_review_insight:
                        continue

                    content_item = ContentItem(
                        title=title,
                        url=url,
                        source=f"카페: {cafe_name}",
                        description=description,
                        published_date=None,  # Cafe API doesn't return date
                        category="커뮤니티",
                        score=float(operator_score + review_insight_score)
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
