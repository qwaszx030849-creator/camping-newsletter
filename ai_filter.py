"""
AI 필터링 + 요약 시스템 (Claude API)
=====================================
Step 1: 수집된 콘텐츠에서 캠핑장 운영자에게 유용한 콘텐츠 선별
Step 2: 선별된 콘텐츠에 핵심 요약 생성

모델 선택 전략:
- 1순위: Sonnet 4.6 (높은 정확도, 주당 약 110원)
- 2순위: Haiku 4.5 (크레딧/쿼터 부족 시 자동 폴백, 주당 약 30원)
- 3순위: 규칙 기반 (API 키 없거나 모든 모델 실패 시)
"""
import os
import anthropic
import json
from typing import List
from collectors.base import ContentItem
from config import ANTHROPIC_API_KEY, NEWSLETTER_ITEMS_COUNT


# 모델 우선순위 (환경변수로 오버라이드 가능)
PRIMARY_MODEL = os.getenv("CLAUDE_PRIMARY_MODEL", "claude-sonnet-4-6")
FALLBACK_MODEL = os.getenv("CLAUDE_FALLBACK_MODEL", "claude-haiku-4-5-20251001")

# Claude API 클라이언트
_client = None
# 폴백 상태 메모이제이션 (한 번 폴백되면 같은 실행 동안 재시도 안 함)
_disabled_models: set = set()


def _get_client():
    global _client
    if _client is None and ANTHROPIC_API_KEY:
        _client = anthropic.Anthropic(api_key=ANTHROPIC_API_KEY)
    return _client


def _is_quota_or_credit_error(err: Exception) -> bool:
    """크레딧/쿼터 부족 또는 모델 비활성 관련 에러인지 판단."""
    msg = str(err).lower()
    quota_signals = (
        "credit", "quota", "insufficient", "billing",
        "balance", "exceeded", "permission_error",
    )
    if any(sig in msg for sig in quota_signals):
        return True
    status = getattr(err, "status_code", None)
    return status in (402, 403, 429)


# ============================================================================
# Step 1: AI 필터링 - 캠핑장 운영자에게 유용한 콘텐츠 선별
# ============================================================================
FILTER_PROMPT = """당신은 캠핑장 담당 MD입니다. 캠핑장 사장님(캠지기)을 위한 주간 뉴스레터에 실을 콘텐츠를 선별합니다.

## 선별 기준: "캠핑장 사장님이 읽고 이번 주에 바로 써먹을 수 있는가?"

### 반드시 선별할 콘텐츠
- 캠핑장 매출/예약률을 올린 구체적인 성공 사례 (수치 포함이면 최고)
- 캠핑장 시설 개선 후 효과를 본 사례 (화장실, 샤워실 등)
- 캠퍼 후기에서 운영자가 참고할 수 있는 포인트가 명확한 글 (청결, 응대, 수영장, 아이 체험, 반려견, 사이트 간격, 재방문 이유, 불편사항)
- 지자체/플랫폼/지역 상권과 연계해 캠핑 수요를 만든 사례 (타 지역 지자체에 건의할 근거로 쓸 수 있는 경우)
- 숙박업 공통 리스크 공지 (오버부킹, 예약 취소 배상, 위생/원산지, 환불 규정)
- 예약/리뷰 관리 노하우 (네이버 플레이스, 블로그, 인스타)
- 계절별 운영 전략 (성수기 대비, 비수기 매출)
- 전국 캠핑장에 공통으로 적용되는 제도/안전/인허가 이슈
- 캠핑 산업 동향, 통계, 시장 변화, 운영 트렌드
- 고객 응대/불만 해결 실전 사례

### 반드시 제외할 콘텐츠
- 단순 캠핑장 방문 후기, 여행 코스 추천
- 특정 지역/지자체에만 해당하는 지원사업, 보조금, 공모, 교육, 행사 공지
- 특정 지역 공공 캠핑장 개장/정비 기사 중 운영 방식 인사이트가 없는 글
- 캠핑장 할인 받는 법, 예약 할인 팁, 쿠폰/프로모션 안내
- 캠핑 용품/장비 리뷰 (텐트, 침낭 등)
- 캠핑카/차박/1톤 트럭/캠핑카 정비업/차량 구매 콘텐츠
- 부동산 매매/임대/분양/경매
- 캠핑장 창업 일반론, 창업비용, 창업자금, 프랜차이즈 홍보
- 맛집, 음식, 밀키트
- 업체 광고/홍보 (시공업체, 마케팅대행사, CCTV업체, 난로업체 등)
- 특정 브랜드/제품 홍보글 (예: 프롬비 빅팬, 에어바운스 해외직구, 산으로간니모 등)
- 차박/노지 캠핑
- 알바/구인 정보
- 일반 자기계발/경영 일반론
- ⚠️ 펜션/카페/민박/풀빌라/리조트 위주 콘텐츠 (캠핑장이 부수적으로만 언급된 경우 제외)
- ⚠️ 제목에 "캠핑장"보다 "펜션"이나 "카페"가 먼저 나오는 기사는 반드시 제외

## 콘텐츠 목록
{content_list}

## 응답
캠핑장 사장님에게 가장 유용한 {count}개를 선별하세요. JSON 배열로만 응답하세요.
```json
[
  {{"index": 0, "category": "운영노하우", "reason": "선별 이유 한 줄"}},
  {{"index": 3, "category": "산업동향", "reason": "선별 이유 한 줄"}}
]
```

카테고리: 운영노하우, 매출전략, 마케팅, 시설개선, 산업동향, 고객관리, 후기인사이트, 지역연계, 리스크관리 중 택 1"""


# ============================================================================
# Step 2: AI 요약 생성
# ============================================================================
SUMMARY_PROMPT = """아래 콘텐츠들의 핵심 요약을 생성해주세요. 캠핑장 사장님이 빠르게 읽을 수 있도록 각 콘텐츠에 대해 2~3줄로 요약합니다.

요약 규칙:
- 첫 줄: 핵심 인사이트 (캠핑장 사장님이 얻을 수 있는 것)
- 둘째 줄: 구체적인 수치나 방법이 있으면 포함
- 후기 콘텐츠는 "이 캠핑장이 왜 좋게 보였는지"와 "내 캠핑장에 적용할 운영 포인트"를 분리해서 작성
- "~합니다" 체로 작성
- 광고성 문구 제거, 팩트만

## 콘텐츠 목록
{content_list}

## 응답
JSON 배열로만 응답하세요.
```json
[
  {{"index": 0, "summary": "요약 내용"}},
  {{"index": 1, "summary": "요약 내용"}}
]
```"""


def _call_claude(prompt: str) -> str:
    """Claude API 호출 (Sonnet → Haiku 자동 폴백)"""
    client = _get_client()
    if not client:
        return ""

    models_to_try = [m for m in (PRIMARY_MODEL, FALLBACK_MODEL) if m not in _disabled_models]
    if not models_to_try:
        return ""

    for model in models_to_try:
        try:
            response = client.messages.create(
                model=model,
                max_tokens=2000,
                messages=[{"role": "user", "content": prompt}],
            )
            usage = getattr(response, "usage", None)
            if usage:
                print(f"    ✓ {model} 사용 (in={usage.input_tokens}, out={usage.output_tokens})")
            else:
                print(f"    ✓ {model} 사용")
            return response.content[0].text
        except Exception as e:
            if _is_quota_or_credit_error(e):
                print(f"    ⚠ {model} 사용 불가 (크레딧/쿼터): {e}")
                _disabled_models.add(model)
                continue  # 다음 모델 시도
            print(f"    ✗ {model} 오류: {e}")
            return ""  # 일시적 네트워크 오류 등 → 규칙 기반 폴백

    print("    ⚠ 모든 Claude 모델 사용 불가 → 규칙 기반 필터로 폴백")
    return ""


def _parse_json_response(response_text: str) -> list:
    """JSON 응답 파싱"""
    decoder = json.JSONDecoder()
    for match in re.finditer(r'\[', response_text):
        try:
            parsed, _ = decoder.raw_decode(response_text[match.start():])
            if isinstance(parsed, list):
                return parsed
        except json.JSONDecodeError:
            continue
    print("    JSON parsing error: valid JSON array not found")
    return []


def _format_content_list(items: List[ContentItem]) -> str:
    """콘텐츠 목록을 프롬프트용 문자열로 변환"""
    lines = []
    for i, item in enumerate(items):
        desc = item.description[:200] if item.description else ""
        lines.append(f"[{i}] 제목: {item.title}")
        lines.append(f"    출처: {item.source}")
        lines.append(f"    내용: {desc}")
        lines.append("")
    return "\n".join(lines)


# ============================================================================
# 규칙 기반 필터 (Claude API 키 없을 때 + 강화 버전)
# ============================================================================

import re

# 제목에 하나라도 있으면 즉시 탈락 (hard reject)
_HARD_REJECT_TITLE = [
    # 부동산/매물/경매
    "매매", "분양", "임대", "경매", "급매", "매물", "매각", "부지",
    "토지", "건축 면적", "객실,", "할인 모텔", "숙박시설 허가",
    "양도", "매입 운영",
    "풀빌라", "리조트 캠핑장",
    # 펜션/카페/민박 위주 콘텐츠
    "펜션 매출", "카페 펜션", "카페 매출", "펜션 운영", "펜션 수익",
    "펜션 사장님", "민박 운영", "게스트하우스", "숙박업",
    # 업체 광고/홍보
    "CCTV", "에어컨", "벽걸이", "냉난방", "컨테이너", "시공",
    "설치후기", "세탁기", "건조기", "드론 조종", "배럴사우나",
    "온수욕조", "이동식 주택", "자부심", "1세대", "1등 건축가",
    "에코캐빈", "ODM", "반도에너지",
    # 난로/화목/펠렛 업체 광고
    "화목난로", "펠렛난로", "파이어우드", "벽난로 설치",
    # 마케팅 대행사 광고
    "마케팅 대행", "광고 대행", "퓨처랩", "대행사",
    "브랜드 메이킹", "상담 문의 드", "무료 상담",
    # MLM/자기계발/낚시
    "드림투유", "수익파이프라인", "마이너스였던 인생", "플러스로 바뀐",
    "런닝맨", "나는 솔로", "유재석", "진실은?", "충격",
    "네트워크 마케팅", "자기계발",
    # 방문 후기/여행
    "다녀왔", "다녀온", "방문 후기", "여행 후기", "여행 코스",
    "바로가기", "가볼만한 곳", "숨겨진 보석", "벚꽃", "단풍",
    "데이트 코스", "아이와 함께", "TOP 5", "TOP 10", "TOP 3",
    "할인 받는 팁", "할인받는 팁", "할인 받는법", "할인받는법",
    "할인 쿠폰", "할인 받기", "할인받기", "예약 숙소", "물놀이 명당",
    "행사 예고", "참가자발표", "참가자 발표", "정기 캠핑", "정캠",
    "뉴스레터",
    "지원사업 모집", "지원 사업 모집", "우수캠핑장 지원사업",
    "사업자 집합 안전교육", "집합 안전교육", "공모사업", "공모 사업",
    "정식 개장", "시설 19일 개장", "글램핑장 19일 개장",
    "글램핑 개장", "여름 관광객 맞이",
    # 캠핑 용품/장비
    "텐트 추천", "캠핑용품", "매트 추천", "침낭 추천", "그릴 추천",
    "필수템", "캠핑 준비물", "프롬비", "빅팬", "선풍기", "서큘레이터",
    "에어바운스", "해외직구",
    # 캠핑카/차량
    "캠핑카", "1톤", "캠핑트레일러", "캠핑카정비업", "캠핑카 정비",
    "중고 캠핑카", "루프탑", "차량용품", "캠지기 버스", "버스 빌려",
    # 음식
    "맛집", "먹방", "밀키트", "냉면", "레시피",
    # 차박/노지
    "차박", "노지 캠핑",
    # 구인/알바
    "알바 찾기", "알바 모집", "구인", "채용",
    # 자판기/무인
    "무인자판기", "무인 자판기", "자판기 창업", "키오스크 수익",
    # 블로그 광고 대행
    "마케팅 대행", "광고 대행", "블로그 광고", "효과 리포트",
    # 일반 창업/투자
    "소액수익형", "수익형 부동산", "투자 가이드",
    "캠핑장 창업", "창업 비용", "창업비용", "창업자금", "사업자금",
    "정비업창업", "프랜차이즈",
    # 특정 홍보성 사례
    "산으로간니모", "홍보글", "홍보 글",
    # 6차 산업/농업
    "6차 산업", "관광농원", "농막",
    # 음식/식자재/주점 (캠핑장과 무관)
    "모찌", "도후", "이자카야", "주점", "식자재",
    "마켓오지", "감성주점", "포차", "안주",
    # 소비자용 가이드/안내
    "초보 가이드", "캠핑 초보", "이용 안내", "예약 및 이용",
    "장비 체크리스트", "캠핑 가이드 총정리",
    # 사이트 번호 후기 (방문 후기 패턴)
    "사이트 1번", "사이트 2번", "사이트 3번", "사이트 4번", "사이트 5번",
    "사이트 6번", "사이트 7번", "사이트 8번", "사이트 9번", "사이트 10번",
    # 질문글
    "배우고 싶어요", "알려주세요", "조언 부탁",
    "하고싶은데", "하고 싶은데", "뭐부터 알아봐",
    # 추천/소개 후기 패턴
    "캠핏 추천", "캠핑장 추천 후기", "방갈로까지", "수영장 카라반",
    "가족 추천", "예약 꿀팁", "인상깊었던", "캠핑 이웃",
    "홈페이지제작", "방방이", "키즈카페 인기 아이템", "산으로 간 니모",
]

_HARD_REJECT_TEXT = [
    "광고 대행사", "마케팅 대행사", "실행사만의 노하우", "파트너가 필요",
    "홈페이지제작", "예약률 30% 높이는 비밀", "키즈카페 인기 아이템",
    "요즘 캠핑장, 키즈카페, 펜션 사장님", "예약 꿀팁", "산으로 간 니모",
    "협찬", "체험단", "제휴마케팅", "커미션을 지급", "구매링크",
    "국성부동산매니지먼트", "원스톱", "더 늦기 전에 시작하세요",
    "무료 진단", "무료 컨설팅", "관리 전:", "관리 후:",
    "자부담", "신청서 제출", "모집합니다", "마케팅전략팀",
    "문화관광공사", "지자체 공모", "군청", "시청 관광과",
    "정식 개장하고 본격적인 운영", "여름 관광객들에게 선보인다",
    "통합예약시스템", "멤버쉽 대상으로", "멤버십 대상으로",
]

# 본문에 있으면 감점 (soft penalty)
_SOFT_NEGATIVE = [
    "문의하세요", "상담 문의", "무료 상담", "견적 문의",
    "지금 바로 문의", "중개 안내", "전문 중개",
    "제품구매 설치", "구매 문의", "설치 사례",
    "판매합니다", "할인 이벤트", "특별 할인",
    "할인 받는 팁", "할인받는 팁", "할인 받는법", "할인받는법",
    "제휴마케팅", "커미션", "파트너스", "구매링크", "협찬", "체험단",
    "대출", "금리", "한도", "융자",
    "카라반 매매", "중고 카라반",
    "펜션 추천", "펜션 후기", "민박",
    "모텔", "호텔", "리조트",
    # 펜션/카페 위주 본문
    "펜션 사장님", "카페 운영", "카페 사장님", "풀빌라 운영",
    "펜션 매출", "펜션 예약", "카페 매출",
    # 광고성 패턴
    "수천 건 이상의 설치", "고객 리뷰가 말해", "지금 바로",
    "상담 도와드리겠습니다", "문의 주시면", "전화 주세요",
    "효과 리포트", "성과 보고서",
    "산으로간니모", "프롬비", "빅팬", "에어바운스", "해외직구",
]

# 강한 긍정 신호 (운영자에게 직접 도움이 되는 내용)
_STRONG_POSITIVE = [
    # 매출/수익 (구체적)
    "매출 올리", "매출 상승", "매출 증가", "매출 극대화",
    "예약률 높", "예약률 상승", "예약 증가",
    "재방문율", "재방문 높", "고객 만족도",
    "재방문 후기", "또 가고 싶은", "다시 방문", "사장님 친절",
    "아이 체험", "체험 프로그램", "수영장 운영", "반려견", "애견",
    "사이트 간격", "사이트 배치", "청결", "화장실 깨끗", "샤워실 깨끗",
    # 운영 노하우
    "운영 노하우", "운영 전략", "운영 팁", "운영 비결",
    "성공 비결", "성공 사례", "성공한 캠핑장",
    "체크리스트", "체크인", "체크아웃",
    # 마케팅 실전
    "네이버플레이스", "상위노출", "마케팅 효과", "마케팅 성공",
    "인스타 마케팅", "블로그 마케팅",
    "예약 폭주", "입소문",
    # 시설 개선
    "리모델링 후", "시설 개선 후", "시설 투자 효과",
    "화장실 리모델링", "샤워실 개선",
    # 정부 지원
    "지원사업", "보조금", "지원금 신청", "국비",
    "야영장 안전", "야영장 활성화",
    # 비수기/성수기
    "비수기 매출", "비수기 전략", "성수기 대비",
    # 산업 동향 (뉴스)
    "캠핑 시장", "캠핑 산업", "글램핑 시장", "야영장 등록",
    "캠핑 인구", "캠핑 트렌드",
]

# 소스별 보너스
_SOURCE_BONUS = {
    "네이버 뉴스": 3.0,  # 뉴스 기사는 광고일 확률 낮음
    "구글 뉴스": 2.0,
    "네이버 블로그": 0.0,  # 블로그는 기본
}


def _classify_category(item: ContentItem) -> str:
    """콘텐츠 카테고리 자동 분류"""
    text = f"{item.title} {item.description}".lower()
    if any(w in text for w in ["후기", "재방문", "친절", "청결", "아이", "수영장", "체험", "애견", "반려견", "사이트 간격"]):
        return "후기인사이트"
    if any(w in text for w in ["지자체", "지역경제", "지역 활성화", "숙박쿠폰", "숙박 할인", "기획전", "체류형", "관광활성화"]):
        return "지역연계"
    if any(w in text for w in ["오버부킹", "배상책임", "배상", "위생", "원산지", "단속", "예약 취소"]):
        return "리스크관리"
    if any(w in text for w in ["인허가", "안전점검", "안전기준", "등록 기준", "민원"]):
        return "운영노하우"
    if any(w in text for w in ["시장", "동향", "트렌드", "통계", "산업", "성장", "인구"]):
        return "산업동향"
    if any(w in text for w in ["마케팅", "인스타", "플레이스", "상위노출", "블로그", "sns", "홍보"]):
        return "마케팅"
    if any(w in text for w in ["시설", "리모델링", "화장실", "샤워", "사이트 조성", "데크"]):
        return "시설개선"
    if any(w in text for w in ["매출", "수익", "예약률", "재방문", "객단가"]):
        return "매출전략"
    if any(w in text for w in ["고객", "리뷰", "별점", "불만", "응대", "만족"]):
        return "고객관리"
    return "운영노하우"


def _has_review_insight(item: ContentItem) -> bool:
    """방문 후기라도 운영자가 벤치마킹할 포인트가 있으면 허용."""
    text = f"{item.title} {item.description}".lower()
    review_words = [
        "후기", "다녀왔", "다녀온", "방문기", "재방문", "또 가고",
        "추천 이유", "좋았던 점", "아쉬운 점",
    ]
    insight_words = [
        "사장님", "친절", "응대", "청결", "깨끗", "화장실", "샤워실",
        "개수대", "수영장", "물놀이", "아이", "체험", "프로그램",
        "반려견", "애견", "울타리", "사이트 간격", "사이트 배치",
        "그늘", "소음", "매너타임", "환불", "양도", "예약", "재방문",
        "불편", "개선", "관리",
    ]
    return any(w in text for w in review_words) and any(w in text for w in insight_words)


def _is_hard_rejected(item: ContentItem) -> bool:
    """제목 기반 즉시 탈락 판정"""
    title = item.title.lower()
    combined = f"{item.title} {item.description}".lower()
    operator_context_words = [
        "운영", "캠지기", "예약률", "예약 관리", "리뷰 관리", "후기 관리",
        "재방문", "만족도", "고객 불만", "응대", "요금", "가격",
        "매출", "수익", "시설 개선", "리모델링", "안전", "인허가",
    ]
    has_operator_context = any(w in combined for w in operator_context_words)
    has_review_insight = _has_review_insight(item)

    local_region_terms = [
        "경상북도", "경상남도", "전라북도", "전라남도", "충청북도", "충청남도",
        "강원도", "경기도", "제주도", "서울시", "부산시", "대구시", "인천시",
        "광주시", "대전시", "울산시", "세종시",
        "양평군", "고창군", "완주군", "청도군", "무주군", "아산시",
    ]
    local_notice_terms = [
        "지원사업", "보조금", "공모", "모집", "교육 실시", "집합 안전교육",
        "선제 실시", "개장", "정식 개장", "시설 정비", "시설 개선비",
    ]
    if any(w.lower() in combined for w in local_region_terms) and any(
        w.lower() in combined for w in local_notice_terms
    ) and not has_review_insight:
        return True

    if item.published_date:
        from datetime import datetime
        try:
            pub = item.published_date.replace(tzinfo=None) if item.published_date.tzinfo else item.published_date
            days_old = (datetime.now() - pub).days
            if item.source in ["네이버 뉴스", "구글 뉴스"] and days_old > 180:
                return True
            if item.source == "네이버 블로그" and days_old > 365:
                return True
        except Exception:
            pass

    for signal in _HARD_REJECT_TITLE:
        if signal.lower() in title and not has_review_insight:
            return True

    for signal in _HARD_REJECT_TEXT:
        if signal.lower() in combined and not has_review_insight:
            return True
    # URL 패턴 기반 탈락
    url = item.url.lower()
    if any(domain in url for domain in ["pension114", "auction-run", "glorykorea"]):
        return True

    # 뉴스: 캠핑장이 핵심 주제인지 확인 (단순 언급만 있는 뉴스 제거)
    camping_words = ["캠핑장", "글램핑", "야영장", "오토캠핑", "캠지기"]
    if item.source in ["네이버 뉴스", "구글 뉴스"]:
        # 제목에 캠핑 관련 단어가 반드시 있어야 함
        title_has_camping = any(w in title for w in camping_words)
        if not title_has_camping:
            return True

    # 캠핑장 운영과 무관한 주제 (캠핑장이 언급만 되는 경우)
    irrelevant_topics = [
        "아파트", "분양권", "입주", "모델하우스", "부동산 시세",
        "가볼 만한 곳", "여행 코스", "관광지", "해변이 어우러",
    ]
    if any(w in combined for w in irrelevant_topics):
        if not has_review_insight:
            return True

    # 제품 광고/리뷰 패턴 탈락
    ad_patterns = [
        "구매 고객", "별점 5점", "쿠팡", "최저가", "할인 코드",
        "지금 바로 구매", "구매링크", "파트너스", "실사용 리뷰",
        "워터펌프", "정수기", "공기청정", "선풍기", "에어건",
        "송풍기", "충전식", "갓성비", "가성비 추천", "제품 리뷰",
        "자판기 판매", "자판기 매출", "생필품자판기", "무인판매기",
    ]
    if any(p.lower() in combined for p in ad_patterns):
        return True

    # 지방자치/정치/무관한 뉴스
    politics_words = ["시장 예비후보", "의회", "임시회", "공약 발표", "종량제",
                       "쓰레기", "패트롤", "자원회수시설"]
    if item.source in ["네이버 뉴스", "구글 뉴스", "정부지원"]:
        if any(w in combined for w in politics_words):
            return True

    # 정부지원/카페/지식iN: 제목에 캠핑 관련 단어 필수
    camp_check_sources = ["정부지원", "지식iN"]
    if item.source in camp_check_sources or item.source.startswith("카페:"):
        camp_words_title = ["캠핑장", "글램핑", "야영장", "오토캠핑", "캠지기", "카라반", "캠핑"]
        if not any(w in title for w in camp_words_title):
            return True

    # 카페: 방문 후기/소비자 관점 (운영자용이 아닌 콘텐츠)
    if item.source.startswith("카페:"):
        visitor_patterns = ["후기", "다녀왔", "다녀온", "캠핑 후기", "방문기",
                            "쉬고 온", "추천해요", "이야기~~~", "이야기~",
                            "예약 방법", "예약방법", "모이세요", "오픈합니다",
                            "1박", "2박", "미니멀", "캠이야기", "공지"]
        if any(p in title for p in visitor_patterns) and not has_operator_context and not has_review_insight:
            return True

    # 블로그: 제목이 펜션/카페 위주이고 캠핑장은 부수적 언급인 경우
    if item.source == "네이버 블로그":
        pension_cafe_words = ["펜션", "카페", "민박", "풀빌라", "게스트하우스", "숙박업"]
        camping_words_check = ["캠핑장", "오토캠핑", "야영장", "글램핑장", "캠지기"]
        title_has_pension = any(w in title for w in pension_cafe_words)
        title_has_camping = any(w in title for w in camping_words_check)
        # 제목에 펜션/카페가 있고 캠핑장이 없으면 탈락
        if title_has_pension and not title_has_camping:
            return True
        # 제목에서 펜션/카페가 캠핑장보다 먼저 나오면 탈락
        if title_has_pension and title_has_camping:
            first_pension = min((title.find(w) for w in pension_cafe_words if w in title), default=999)
            first_camping = min((title.find(w) for w in camping_words_check if w in title), default=999)
            if first_pension < first_camping:
                return True

    # 블로그: 캠핑장 단어가 제목에 없으면 운영자용일 가능성 매우 낮음
    if item.source == "네이버 블로그":
        camp_words_strict = ["캠핑장", "오토캠핑", "야영장", "글램핑장", "캠지기"]
        if not any(w in title for w in camp_words_strict):
            return True

    # 블로그: 방문 후기 패턴 (오토캠핑장 후기, ~ 후기 등 - 운영자가 아닌 소비자 후기)
    if item.source == "네이버 블로그":
        visitor_review_patterns = [
            "캠핑장 후기", "오토캠핑장 후기", "글램핑장 후기", "야영장 후기",
            "다녀온 ", "다녀왔", "방문 후기", "1박 2일", "1박2일",
            "이용 후기", "체험 후기",
        ]
        for p in visitor_review_patterns:
            if p in title and not has_operator_context and not has_review_insight:
                return True

    return False


def _rule_based_score(item: ContentItem) -> float:
    """규칙 기반 점수 (높을수록 유용)"""
    if _is_hard_rejected(item):
        return -999.0

    text = f"{item.title} {item.description}".lower()
    title = item.title.lower()
    score = 0.0

    # 강한 긍정 신호
    for s in _STRONG_POSITIVE:
        if s.lower() in title:
            score += 4.0
        elif s.lower() in text:
            score += 2.0

    # 소프트 감점
    for s in _SOFT_NEGATIVE:
        if s.lower() in title:
            score -= 6.0
        elif s.lower() in text:
            score -= 2.0

    # 소스 보너스
    score += _SOURCE_BONUS.get(item.source, 0.0)

    # 운영자 대상 글 보너스
    owner_words = ["사장님", "대표님", "운영자", "캠지기", "관리인"]
    for w in owner_words:
        if w in text:
            score += 2.0

    # 날짜 보너스: 최근 글이면 가산
    if item.published_date:
        from datetime import datetime, timezone
        now = datetime.now()
        try:
            pub = item.published_date.replace(tzinfo=None) if item.published_date.tzinfo else item.published_date
            days_old = (now - pub).days
            if days_old <= 7:
                score += 3.0
            elif days_old <= 14:
                score += 1.5
            elif days_old > 90:
                score -= 3.0
        except:
            pass

    return score


def _extract_keywords(text: str) -> set:
    """텍스트에서 핵심 키워드 셋 추출"""
    # 한글 단어 2글자 이상만 추출
    words = re.findall(r'[가-힣]{2,}', text)
    return set(words)


def _deduplicate_similar(items: List[ContentItem]) -> List[ContentItem]:
    """유사한 내용의 기사 중복 제거 (제목+본문 키워드 겹침 기반)"""
    unique = []
    seen_keyword_sets = []
    for item in items:
        combined = f"{item.title} {item.description}"
        kw = _extract_keywords(combined)
        is_dup = False
        for seen_kw in seen_keyword_sets:
            if len(kw) > 3 and len(seen_kw) > 3:
                overlap = len(kw & seen_kw)
                smaller = min(len(kw), len(seen_kw))
                if smaller > 0 and overlap / smaller > 0.5:
                    is_dup = True
                    break
        if not is_dup:
            seen_keyword_sets.append(kw)
            unique.append(item)
    removed = len(items) - len(unique)
    if removed > 0:
        print(f"    🔄 유사 내용 중복: {removed}개 제거")
    return unique


def _is_similar_topic(item: ContentItem, selected: List[ContentItem]) -> bool:
    """이미 선별된 콘텐츠와 같은 소재인지 판정."""
    kw = _extract_keywords(f"{item.title} {item.description}")
    if len(kw) <= 3:
        return False

    for existing in selected:
        seen_kw = _extract_keywords(f"{existing.title} {existing.description}")
        if len(seen_kw) <= 3:
            continue
        overlap = len(kw & seen_kw)
        smaller = min(len(kw), len(seen_kw))
        if smaller > 0 and overlap / smaller >= 0.45:
            return True
    return False


def _source_group(item: ContentItem) -> str:
    """소스 상한 적용을 위한 출처 그룹명."""
    if item.source.startswith("카페:"):
        return "카페"
    return item.source


def _balance_items(items: List[ContentItem], pool: List[ContentItem], count: int) -> List[ContentItem]:
    """특정 출처/카테고리가 과도하게 몰리지 않도록 최종 선별 목록을 보정."""
    source_limits = {
        "지식iN": 2,
        "카페": 2,
        "구글 뉴스": 3,
        "네이버 뉴스": 4,
        "네이버 블로그": 4,
        "정부지원": 3,
    }
    default_category_limit = 3
    category_limits = {
        "후기인사이트": 5,
        "운영노하우": 4,
        "지역연계": 3,
        "리스크관리": 4,
    }

    selected = []
    selected_urls = set()
    source_count = {}
    category_count = {}

    def can_add(item: ContentItem) -> bool:
        if item.url in selected_urls or _is_hard_rejected(item):
            return False
        if _is_similar_topic(item, selected):
            return False
        source = _source_group(item)
        if source_count.get(source, 0) >= source_limits.get(source, 3):
            return False
        cat = item.category or _classify_category(item)
        if category_count.get(cat, 0) >= category_limits.get(cat, default_category_limit):
            return False
        return True

    def add(item: ContentItem) -> None:
        if not item.category or item.category in ["블로그", "커뮤니티"]:
            item.category = _classify_category(item)
        selected.append(item)
        selected_urls.add(item.url)
        source = _source_group(item)
        source_count[source] = source_count.get(source, 0) + 1
        category_count[item.category] = category_count.get(item.category, 0) + 1

    for item in items:
        if can_add(item):
            add(item)
        if len(selected) >= count:
            return selected

    scored_pool = [(item, _rule_based_score(item)) for item in pool if item.url not in selected_urls]
    scored_pool.sort(key=lambda x: x[1], reverse=True)

    for item, score in scored_pool:
        if score <= -5.0:
            continue
        if can_add(item):
            add(item)
        if len(selected) >= count:
            break

    return selected


def _rule_based_filter(items: List[ContentItem], count: int) -> List[ContentItem]:
    """강화된 규칙 기반 필터링"""
    print("    강화된 규칙 기반 필터링...")

    # 1단계: hard reject 제거
    candidates = [item for item in items if not _is_hard_rejected(item)]
    rejected = len(items) - len(candidates)
    print(f"    🚫 hard reject: {rejected}개 제거 → {len(candidates)}개 남음")

    # 1.5단계: 유사 제목 중복 제거
    candidates = _deduplicate_similar(candidates)

    # 2단계: 점수 계산 + 정렬
    scored = [(item, _rule_based_score(item)) for item in candidates]
    scored.sort(key=lambda x: x[1], reverse=True)

    # 3단계: 카테고리 다양성 확보 (같은 카테고리 최대 3개)
    category_count = {}
    result = []
    for item, sc in scored:
        if sc <= -5.0:
            continue
        cat = _classify_category(item)
        item.category = cat
        if category_count.get(cat, 0) >= 3:
            continue
        category_count[cat] = category_count.get(cat, 0) + 1
        result.append(item)
        if len(result) >= count:
            break

    # 부족하면 남은 것에서 채움
    if len(result) < count:
        existing_urls = {item.url for item in result}
        for item, sc in scored:
            if item.url not in existing_urls and sc > -5.0:
                item.category = _classify_category(item)
                result.append(item)
                if len(result) >= count:
                    break

    # summary 생성 (description 정리)
    result = _balance_items(result, candidates, count)

    for item in result:
        if not item.summary and item.description:
            # HTML 엔티티 정리 + 깔끔하게 자르기
            desc = item.description.replace("&quot;", '"').replace("&amp;", "&").replace("&lt;", "<").replace("&gt;", ">")
            item.summary = desc[:200].strip()

    print(f"    ✅ 최종 선별: {len(result)}개")
    for i, item in enumerate(result, 1):
        print(f"      {i}. [{item.category}] {item.title[:50]}...")

    return result[:count]


# ============================================================================
# 메인 파이프라인
# ============================================================================

def filter_content(items: List[ContentItem], count: int = NEWSLETTER_ITEMS_COUNT) -> List[ContentItem]:
    """
    메인 필터링 + 요약 파이프라인

    1. AI 필터링: 수집된 콘텐츠에서 유용한 것만 선별
    2. AI 요약: 선별된 콘텐츠에 핵심 요약 생성
    """
    print("\n" + "=" * 60)
    has_api = bool(ANTHROPIC_API_KEY)
    if has_api:
        mode = f"Claude AI (1순위: {PRIMARY_MODEL} / 2순위: {FALLBACK_MODEL})"
    else:
        mode = "규칙 기반 (API 키 없음)"
    print(f"  필터링 시작 [{mode}] ({len(items)}개 → {count}개)")
    print("=" * 60)

    if not items:
        return []

    eligible_items = [item for item in items if not _is_hard_rejected(item)]
    rejected = len(items) - len(eligible_items)
    if rejected:
        print(f"  사전 제외 필터: {rejected}개 제거 → {len(eligible_items)}개 후보")

    if not eligible_items:
        return []

    if not has_api:
        return _rule_based_filter(eligible_items, count)

    # === Step 1: AI 필터링 ===
    print(f"\n  [Step 1] AI 필터링 ({len(eligible_items)}개 → {count}개)...")
    content_list = _format_content_list(eligible_items)
    prompt = FILTER_PROMPT.format(content_list=content_list, count=count)

    response = _call_claude(prompt)
    selections = _parse_json_response(response)

    if not selections:
        print("    AI 필터링 실패, 규칙 기반으로 폴백")
        return _rule_based_filter(eligible_items, count)

    filtered = []
    selected_urls = set()
    for sel in selections:
        idx = sel.get("index", -1)
        if 0 <= idx < len(eligible_items):
            item = eligible_items[idx]
            if _is_hard_rejected(item) or item.url in selected_urls or _is_similar_topic(item, filtered):
                continue
            selected_urls.add(item.url)
            item.category = sel.get("category", "기타")
            filtered.append(item)

    print(f"    선별 완료: {len(filtered)}개")
    for i, item in enumerate(filtered, 1):
        print(f"      {i}. [{item.category}] {item.title[:50]}...")

    if not filtered:
        return _rule_based_filter(eligible_items, count)

    balanced = _balance_items(filtered, eligible_items, count)
    if len(balanced) != len(filtered):
        print(f"    소스 균형 보정: {len(filtered)}개 → {len(balanced)}개")
    filtered = balanced

    # === Step 2: AI 요약 생성 ===
    print(f"\n  [Step 2] AI 요약 생성 ({len(filtered)}개)...")
    summary_content = _format_content_list(filtered)
    summary_prompt = SUMMARY_PROMPT.format(content_list=summary_content)

    summary_response = _call_claude(summary_prompt)
    summaries = _parse_json_response(summary_response)

    if summaries:
        for s in summaries:
            idx = s.get("index", -1)
            if 0 <= idx < len(filtered):
                filtered[idx].summary = s.get("summary", "")
        print(f"    요약 생성 완료: {sum(1 for f in filtered if f.summary)}개")
    else:
        print("    요약 생성 실패, description 사용")
        for item in filtered:
            if not item.summary and item.description:
                item.summary = item.description[:150]

    print("\n" + "-" * 60)
    print(f"  최종 결과: {len(filtered)}개")
    print("-" * 60)
    for i, item in enumerate(filtered, 1):
        print(f"   {i}. [{item.category}] {item.title[:50]}...")
        if item.summary:
            print(f"      → {item.summary[:60]}...")

    return filtered[:count]
