"""
Government Support Collector
전국 캠핑장 운영자가 참고할 수 있는 제도/안전/인허가 이슈를 수집합니다.

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
    제도/안전 이슈 수집기
    지역 한정 지원사업보다 전국 캠핑장 운영자가 참고할 수 있는 정보 수집
    """
    
    API_URL = "https://openapi.naver.com/v1/search/news.json"
    
    # 지역 공고보다 전국 공통 제도/운영 리스크 중심 키워드
    SUPPORT_KEYWORDS = [
        "캠핑장 안전기준",
        "야영장 안전관리",
        "캠핑장 화재 안전",
        "캠핑장 물놀이 안전",
        "캠핑장 민원 대응",
        "야영장 등록 기준",
        "캠핑장 인허가",
    ]
    
    def __init__(self):
        super().__init__("government_support")
        self.client_id = NAVER_CLIENT_ID
        self.client_secret = NAVER_CLIENT_SECRET
    
    def collect(self, keywords: List[str] = None) -> List[ContentItem]:
        """전국 공통 제도/안전 관련 뉴스 수집"""
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
                    
                    # 지역 한정 공고/지원사업은 제외하고 운영 리스크 이슈만 유지
                    relevance_keywords = [
                        "안전", "등록", "인허가", "기준", "점검", "화재",
                        "물놀이", "민원", "위생", "소방", "야영장",
                    ]
                    local_notice_keywords = [
                        "지원사업", "보조금", "공모", "모집", "신청", "융자",
                        "시설개선 지원", "교육 실시", "집합 안전교육",
                    ]
                    is_relevant = any(kw in title or kw in description for kw in relevance_keywords)
                    is_local_notice = any(kw in title or kw in description for kw in local_notice_keywords)
                    
                    if not is_relevant or is_local_notice:
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
                        source="제도/안전",
                        description=description,
                        published_date=pub_date,
                        category="운영노하우"
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
