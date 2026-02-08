"""
Government Support Collector
정부/지자체 캠핑장 관련 지원사업 정보를 수집합니다.

주요 소스:
- 기업마당 (bizinfo.go.kr)
- 중소벤처기업부
- 문화체육관광부
- 지자체 공고
"""
import requests
from datetime import datetime
from typing import List
from .base import BaseCollector, ContentItem
import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from config import NAVER_CLIENT_ID, NAVER_CLIENT_SECRET


class GovernmentSupportCollector(BaseCollector):
    """
    정부 지원사업 수집기
    네이버 뉴스/카페 검색을 통해 캠핑장 관련 정부 지원 정보 수집
    """
    
    API_URL = "https://openapi.naver.com/v1/search/news.json"
    
    # 정부 지원사업 전용 키워드
    SUPPORT_KEYWORDS = [
        # 직접 지원
        "캠핑장 지원사업 공고",
        "야영장 보조금",
        "관광사업자 지원금",
        "농촌관광 지원사업",
        "농촌체험휴양마을 공모",
        
        # 시설 지원
        "캠핑장 시설개선 지원",
        "친환경 관광시설 지원",
        "관광 편의시설 지원",
        
        # 융자/교육
        "관광사업자 융자",
        "소상공인 관광업",
        "관광업 교육 지원",
        
        # 인허가
        "야영장 등록 기준",
        "캠핑장 인허가",
    ]
    
    def __init__(self):
        super().__init__("government_support")
        self.client_id = NAVER_CLIENT_ID
        self.client_secret = NAVER_CLIENT_SECRET
    
    def collect(self, keywords: List[str] = None) -> List[ContentItem]:
        """정부 지원사업 관련 뉴스 수집"""
        if not self.client_id or not self.client_secret:
            self.logger.warning("Naver API credentials not configured")
            return []
        
        search_keywords = keywords or self.SUPPORT_KEYWORDS
        items = []
        seen_urls = set()
        
        headers = {
            "X-Naver-Client-Id": self.client_id,
            "X-Naver-Client-Secret": self.client_secret
        }
        
        for keyword in search_keywords:
            try:
                params = {
                    "query": keyword,
                    "display": 5,
                    "start": 1,
                    "sort": "date"
                }
                
                response = requests.get(self.API_URL, headers=headers, params=params, timeout=10)
                response.raise_for_status()
                
                data = response.json()
                
                for item in data.get("items", []):
                    url = item.get("link", "")
                    title = self._clean_text(item.get("title", ""))
                    description = self._clean_text(item.get("description", ""))
                    
                    # 정부 지원과 관련 있는지 필터링
                    relevance_keywords = ["지원", "공고", "모집", "신청", "보조금", "융자", "지자체", "정부"]
                    is_relevant = any(kw in title or kw in description for kw in relevance_keywords)
                    
                    if not is_relevant:
                        continue
                    
                    if url in seen_urls:
                        continue
                    seen_urls.add(url)
                    
                    # 날짜 파싱
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
                        title=title,
                        url=url,
                        source="정부지원",
                        description=description,
                        published_date=pub_date,
                        category="정부지원"
                    )
                    items.append(content_item)
                
                self.logger.info(f"Collected {len(data.get('items', []))} items for: {keyword}")
                
            except requests.RequestException as e:
                self.logger.error(f"Error fetching for '{keyword}': {e}")
                continue
        
        self.logger.info(f"Total government support items: {len(items)}")
        return items


class BizInfoCollector(BaseCollector):
    """
    기업마당(bizinfo.go.kr) 지원사업 수집기
    공공 API를 통해 캠핑장/관광업 관련 지원사업 수집
    
    Note: 실제 사용을 위해서는 공공데이터포털에서 API 키 발급 필요
    https://www.data.go.kr
    """
    
    # 기업마당 API (공공데이터포털)
    API_URL = "https://api.odcloud.kr/api/15083292/v1/uddi:4d01f31c-57bc-47b8-82b9-7a3b7e65e7cd"
    
    def __init__(self, api_key: str = None):
        super().__init__("bizinfo")
        self.api_key = api_key or os.getenv("DATA_GO_KR_API_KEY", "")
    
    def collect(self, keywords: List[str] = None) -> List[ContentItem]:
        """
        기업마당 API에서 지원사업 수집
        
        Note: API 키가 없으면 빈 리스트 반환
        """
        if not self.api_key:
            self.logger.info("BizInfo API key not configured. Skipping.")
            return []
        
        items = []
        
        try:
            params = {
                "serviceKey": self.api_key,
                "page": 1,
                "perPage": 20,
            }
            
            response = requests.get(self.API_URL, params=params, timeout=10)
            response.raise_for_status()
            
            data = response.json()
            
            for item in data.get("data", []):
                # 관광/캠핑 관련 필터링
                title = item.get("사업명", "")
                desc = item.get("지원내용", "")
                
                tourism_keywords = ["관광", "캠핑", "야영", "숙박", "레저", "농촌", "체험"]
                is_relevant = any(kw in title or kw in desc for kw in tourism_keywords)
                
                if not is_relevant:
                    continue
                
                content_item = ContentItem(
                    title=title,
                    url=item.get("신청URL", "https://www.bizinfo.go.kr"),
                    source="기업마당",
                    description=desc[:200] if desc else "",
                    category="정부지원"
                )
                items.append(content_item)
            
            self.logger.info(f"Collected {len(items)} items from BizInfo")
            
        except Exception as e:
            self.logger.error(f"Error fetching BizInfo: {e}")
        
        return items


if __name__ == "__main__":
    # Test government support collector
    print("=== Government Support Collector ===")
    collector = GovernmentSupportCollector()
    items = collector.collect()
    
    print(f"\nCollected {len(items)} items:")
    for item in items[:5]:
        print(f"- [{item.category}] {item.title}")
        print(f"  URL: {item.url}")
        print()
