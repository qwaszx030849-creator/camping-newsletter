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
    
    # ================================================================
    # 운영자 관점 신호 단어 (이 단어가 많을수록 운영자에게 유용한 글)
    # ================================================================
    OPERATOR_SIGNALS = [
        # 매출/수익 관련
        "매출", "수익", "순이익", "인건비", "영업이익", "원가", "객단가",
        "매출 상승", "매출 증가", "수익 구조",
        # 예약/고객 관련
        "예약률", "예약 관리", "재방문", "재방문율", "고객 만족", "고객 응대",
        "고객 불만", "리뷰 관리", "별점", "후기 관리", "만족도",
        # 운영 관련
        "운영 노하우", "운영 전략", "운영 팁", "운영자", "사장님", "대표님",
        "캠지기", "관리인", "직원 관리", "인력 관리", "체크리스트",
        "체크인", "체크아웃", "청소", "청결", "위생", "안전 관리",
        # 마케팅 관련
        "마케팅", "네이버플레이스", "네이버 플레이스", "인스타그램", "블로그 마케팅",
        "상위노출", "검색 최적화", "홍보", "온라인 마케팅", "sns 마케팅",
        "브랜딩", "입소문", "바이럴",
        # 시설/투자 관련
        "시설 개선", "리모델링", "시설 투자", "사이트 조성", "데크 시공",
        "화장실 리모델링", "샤워실", "개수대", "전기 시설", "와이파이",
        # 사업 전략
        "성수기 대비", "비수기 전략", "비수기 매출", "계절별 운영",
        "이벤트 기획", "프로그램 운영", "체험 프로그램",
        "위탁 운영", "위탁경영", "프랜차이즈",
        # 제도/정책
        "야영장 등록", "인허가", "지원사업", "보조금", "지원금",
        "안전점검", "소방 점검", "위생 점검",
        # 차별화/벤치마킹
        "차별화", "경쟁력", "벤치마킹", "성공 사례", "성공 비결",
    ]

    # ================================================================
    # 방문객/소비자 관점 신호 (이 단어가 많으면 운영자용이 아님)
    # ================================================================
    VISITOR_SIGNALS = [
        # 여행/방문 후기
        "다녀왔", "다녀온", "방문 후기", "솔직 후기", "여행 후기", "캠핑 후기",
        "추천 바로가기", "바로가기", "예약 바로가기",
        "여행지 추천", "여행 코스", "가볼만한 곳", "숨겨진 보석",
        "벚꽃 여행", "벚꽃 캠핑", "단풍 여행", "겨울 여행",
        "개화시기", "만개 시기", "축제 일정",
        "데이트 코스", "가족 나들이", "아이와 함께",
        "근처 맛집", "주변 맛집", "주변 관광지",
        # 캠핑 용품/장비
        "텐트 추천", "캠핑용품", "매트 추천", "침낭 추천", "캠핑 장비",
        "전기그릴", "그릴 비교", "그릴 추천", "버너 추천",
        "캠핑 체어", "캠핑 테이블", "타프 추천",
        "쿨러", "아이스박스", "필수템", "캠핑 준비물",
        # 음식/요리
        "맛집", "먹방", "횟집", "대게", "밀키트", "냉면",
        "레시피", "캠핑 요리", "캠핑 음식", "식당 추천",
        "보리냉면", "삼겹살",
        # 제품/업체 광고
        "컨테이너 업체", "시공 업체", "설치 업체",
        "에어컨 설치", "벽걸이 에어컨", "냉난방",
        "카드단말기", "결제단말기", "pos기",
        "냉동고", "냉장고", "쇼케이스", "자판기",
        "커피머신", "렌탈", "드론촬영",
        "세탁기", "건조기", "트램폴린",
        # 부동산
        "임대", "매매", "분양", "토지 매입", "부동산",
        # 차박/노지
        "차박", "노지 캠핑", "무료 주차",
        # 펜션
        "펜션 추천", "펜션 후기", "민박 추천",
        # 일반 서적/자기계발
        "읽고 주저리", "책 리뷰", "독서 감상", "서평",
        # 대출/금융
        "대출", "금리", "한도", "융자",
        # 구인/구직
        "알바 모집", "구인", "채용공고",
        # 농업
        "재배", "농장", "와사비", "작물",
        # 캠지기에게 필요 없는 홍보/제품/차량/창업성 콘텐츠
        "1톤", "캠핑카", "캠핑트레일러", "캠핑카 정비", "산으로간니모",
        "프롬비", "빅팬", "선풍기", "서큘레이터", "에어바운스 해외직구",
        "해외직구", "할인 받는법", "할인 받는 팁", "할인받는법", "할인받는 팁",
        "제휴마케팅", "커미션", "파트너스", "구매링크", "협찬", "체험단",
        "캠핑장 창업", "창업 비용", "창업자금", "사업자금",
    ]

    REVIEW_INSIGHT_SIGNALS = [
        "재방문", "또 가고", "사장님 친절", "친절", "응대",
        "청결", "깨끗", "화장실", "샤워실", "개수대",
        "수영장", "물놀이", "아이", "체험", "프로그램",
        "반려견", "애견", "울타리", "사이트 간격", "사이트 배치",
        "매너타임", "소음", "환불", "양도", "예약", "불편", "관리",
    ]

    def collect(self, keywords: List[str], max_items_per_keyword: int = 10) -> List[ContentItem]:
        """
        Collect blog posts from Naver Blog Search API
        운영자 관점 점수제로 필터링하여 캠지기에게 유용한 글만 수집
        """
        if not self.client_id or not self.client_secret:
            self.logger.warning("Naver API credentials not configured. Skipping Naver Blog collection.")
            return []
        
        items = []
        seen_urls = set()
        
        # 캠핑장 관련 필수 키워드
        CAMPING_REQUIRED_WORDS = [
            "캠핑장", "글램핑", "야영장", "오토캠핑", "카라반",
            "캠지기", "캠핑사이트"
        ]
        
        headers = {
            "X-Naver-Client-Id": self.client_id,
            "X-Naver-Client-Secret": self.client_secret
        }
        
        for keyword in keywords:
            try:
                search_query = keyword
                
                params = {
                    "query": search_query,
                    "display": max_items_per_keyword * 5,
                    "start": 1,
                    "sort": "date"
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
                    
                    combined_text = f"{title} {description}"
                    combined_lower = combined_text.lower()
                    
                    # 1단계: 캠핑장 관련 단어 필수
                    is_camping_related = any(word in combined_lower for word in CAMPING_REQUIRED_WORDS)
                    if not is_camping_related:
                        continue
                    
                    # 2단계: 운영자 관점 점수 계산
                    operator_score = sum(1 for w in self.OPERATOR_SIGNALS if w in combined_lower)
                    visitor_score = sum(1 for w in self.VISITOR_SIGNALS if w in combined_lower)
                    review_insight_score = sum(1 for w in self.REVIEW_INSIGHT_SIGNALS if w in combined_lower)
                    has_review_insight = review_insight_score >= 2
                    
                    # 운영자 신호가 약하더라도 후기 안에 운영 포인트가 있으면 후보로 남김
                    if operator_score < 2 and not has_review_insight:
                        continue
                    
                    # 방문객 점수가 높아도 운영 포인트가 있는 후기는 인사이트 후보로 유지
                    if visitor_score > operator_score and not has_review_insight:
                        continue
                    
                    # 제목에 운영자 신호가 하나도 없으면 제외
                    title_lower = title.lower()
                    title_has_operator_signal = any(w in title_lower for w in self.OPERATOR_SIGNALS)
                    title_has_visitor_signal = any(w in title_lower for w in self.VISITOR_SIGNALS)
                    if not title_has_operator_signal and title_has_visitor_signal and not has_review_insight:
                        continue
                    
                    seen_urls.add(url)
                    
                    # Parse date
                    pub_date = None
                    if item.get("postdate"):
                        try:
                            pub_date = datetime.strptime(item["postdate"], "%Y%m%d")
                        except ValueError:
                            pass
                    
                    # 점수를 저장하여 나중에 정렬에 활용
                    net_score = operator_score + review_insight_score - visitor_score
                    
                    content_item = ContentItem(
                        title=title,
                        url=url,
                        source="네이버 블로그",
                        description=description,
                        published_date=pub_date,
                        category="블로그",
                        score=float(net_score)
                    )
                    items.append(content_item)
                    count += 1
                
                self.logger.info(f"Collected {count} operator-focused posts for: {keyword}")
                
            except requests.RequestException as e:
                self.logger.error(f"Error fetching Naver Blog for '{keyword}': {e}")
                continue
        
        # 운영자 관점 점수 높은 순으로 정렬
        items.sort(key=lambda x: x.score, reverse=True)
        
        self.logger.info(f"Total collected from Naver Blog: {len(items)} operator-focused items")
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
