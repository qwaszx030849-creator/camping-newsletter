"""
Configuration settings for Camping Newsletter Automation System
"""
import os
from dotenv import load_dotenv

load_dotenv()

# API Keys
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY", "")
NAVER_CLIENT_ID = os.getenv("NAVER_CLIENT_ID", "")
NAVER_CLIENT_SECRET = os.getenv("NAVER_CLIENT_SECRET", "")
KAKAO_API_KEY = os.getenv("KAKAO_API_KEY", "")

# ========================================
# 콘텐츠 유형별 검색 키워드
# ========================================

# 1. 고객 후기/사례 - 다른 캠핑장의 좋은 후기 분석
CUSTOMER_REVIEW_KEYWORDS = [
    "캠핑장 후기 최고",
    "캠핑장 재방문 후기",
    "캠핑장 만족도",
    "캠핑장 서비스 좋은",
    "캠핑장 추천 이유",
    "캠핑장 사장님 친절",
]

# 2. 정부 지원사업/보조금
GOVERNMENT_SUPPORT_KEYWORDS = [
    "캠핑장 지원사업",
    "캠핑장 보조금",
    "관광사업자 지원금",
    "농촌체험휴양마을 지원",
    "소상공인 관광업 지원",
    "야영장 인허가",
]

# 3. 시설 투자 사례
FACILITY_INVESTMENT_KEYWORDS = [
    "글램핑 시설 투자",
    "카라반 사이트 설치",
    "캠핑장 화장실 리모델링",
    "캠핑장 샤워장 시설",
    "캠핑장 인프라 개선",
    "펜션 캠핑장 전환",
]

# 4. 마케팅 성공 사례
MARKETING_KEYWORDS = [
    "캠핑장 마케팅 성공",
    "캠핑장 예약률 상승",
    "캠핑장 SNS 마케팅",
    "캠핑장 홍보 효과",
    "캠핑장 입소문",
    "캠핑장 블로그 마케팅",
]

# 5. 캠핑장 동향/트렌드
TREND_KEYWORDS = [
    "캠핑장 트렌드 2026",
    "글램핑 시장 동향",
    "캠핑 산업 성장",
    "캠핑장 매출 현황",
    "캠핑장 운영 현황",
    "오토캠핑장 동향",
]

# 전체 키워드 (모든 유형 합침)
SEARCH_KEYWORDS = (
    CUSTOMER_REVIEW_KEYWORDS + 
    GOVERNMENT_SUPPORT_KEYWORDS + 
    FACILITY_INVESTMENT_KEYWORDS + 
    MARKETING_KEYWORDS + 
    TREND_KEYWORDS
)

# 콘텐츠 유형별 목표 수량 (총 10개)
CONTENT_DISTRIBUTION = {
    "고객후기": 2,
    "정부지원": 2,
    "시설투자": 2,
    "마케팅": 2,
    "동향": 2,
}

# Newsletter settings
NEWSLETTER_ITEMS_COUNT = 10
NEWSLETTER_TITLE_PREFIX = "🏕️ 캠핑장 운영 뉴스레터"

# Output settings
OUTPUT_DIR = os.path.join(os.path.dirname(__file__), "output")
ARCHIVE_DIR = os.path.join(os.path.dirname(__file__), "archive")

