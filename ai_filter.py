"""
AI 필터링 + 요약 시스템 (Claude API)
=====================================
Step 1: 수집된 콘텐츠에서 캠핑장 운영자에게 유용한 콘텐츠 선별
Step 2: 선별된 콘텐츠에 핵심 요약 생성
"""
import anthropic
import json
from typing import List
from collectors.base import ContentItem
from config import ANTHROPIC_API_KEY, NEWSLETTER_ITEMS_COUNT


# Claude API 클라이언트
_client = None

def _get_client():
    global _client
    if _client is None and ANTHROPIC_API_KEY:
        _client = anthropic.Anthropic(api_key=ANTHROPIC_API_KEY)
    return _client


# ============================================================================
# Step 1: AI 필터링 - 캠핑장 운영자에게 유용한 콘텐츠 선별
# ============================================================================
FILTER_PROMPT = """당신은 캠핑장 담당 MD입니다. 캠핑장 사장님(캠지기)을 위한 주간 뉴스레터에 실을 콘텐츠를 선별합니다.

## 선별 기준: "캠핑장 사장님이 읽고 이번 주에 바로 써먹을 수 있는가?"

### 반드시 선별할 콘텐츠
- 캠핑장 매출/예약률을 올린 구체적인 성공 사례 (수치 포함이면 최고)
- 캠핑장 시설 개선 후 효과를 본 사례 (화장실, 샤워실 등)
- 예약/리뷰 관리 노하우 (네이버 플레이스, 블로그, 인스타)
- 계절별 운영 전략 (성수기 대비, 비수기 매출)
- 캠핑장 관련 정부 지원금/보조금 정보
- 캠핑 산업 동향, 통계, 시장 변화
- 고객 응대/불만 해결 실전 사례

### 반드시 제외할 콘텐츠
- 단순 캠핑장 방문 후기, 여행 코스 추천
- 캠핑 용품/장비 리뷰 (텐트, 침낭 등)
- 부동산 매매/임대/분양/경매
- 맛집, 음식, 밀키트
- 업체 광고/홍보 (시공업체, 마케팅대행사, CCTV업체, 난로업체 등)
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

카테고리: 운영노하우, 매출전략, 마케팅, 시설개선, 정부지원, 산업동향, 고객관리 중 택 1"""


# ============================================================================
# Step 2: AI 요약 생성
# ============================================================================
SUMMARY_PROMPT = """아래 콘텐츠들의 핵심 요약을 생성해주세요. 캠핑장 사장님이 빠르게 읽을 수 있도록 각 콘텐츠에 대해 2~3줄로 요약합니다.

요약 규칙:
- 첫 줄: 핵심 인사이트 (캠핑장 사장님이 얻을 수 있는 것)
- 둘째 줄: 구체적인 수치나 방법이 있으면 포함
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
    """Claude API 호출"""
    client = _get_client()
    if not client:
        return ""
    try:
        response = client.messages.create(
            model="claude-haiku-4-5-20251001",
            max_tokens=2000,
            messages=[{"role": "user", "content": prompt}]
        )
        return response.content[0].text
    except Exception as e:
        print(f"    Claude API error: {e}")
        return ""


def _parse_json_response(response_text: str) -> list:
    """JSON 응답 파싱"""
    try:
        json_start = response_text.find('[')
        json_end = response_text.rfind(']') + 1
        if json_start != -1 and json_end > json_start:
            return json.loads(response_text[json_start:json_end])
    except Exception as e:
        print(f"    JSON parsing error: {e}")
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
    # 캠핑 용품/장비
    "텐트 추천", "캠핑용품", "매트 추천", "침낭 추천", "그릴 추천",
    "필수템", "캠핑 준비물",
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
    # 6차 산업/농업
    "6차 산업", "관광농원", "농막",
]

# 본문에 있으면 감점 (soft penalty)
_SOFT_NEGATIVE = [
    "문의하세요", "상담 문의", "무료 상담", "견적 문의",
    "지금 바로 문의", "중개 안내", "전문 중개",
    "제품구매 설치", "구매 문의", "설치 사례",
    "판매합니다", "할인 이벤트", "특별 할인",
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
]

# 강한 긍정 신호 (운영자에게 직접 도움이 되는 내용)
_STRONG_POSITIVE = [
    # 매출/수익 (구체적)
    "매출 올리", "매출 상승", "매출 증가", "매출 극대화",
    "예약률 높", "예약률 상승", "예약 증가",
    "재방문율", "재방문 높", "고객 만족도",
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
    if any(w in text for w in ["지원사업", "보조금", "지원금", "국비", "공모", "인허가", "안전점검"]):
        return "정부지원"
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


def _is_hard_rejected(item: ContentItem) -> bool:
    """제목 기반 즉시 탈락 판정"""
    title = item.title.lower()
    for signal in _HARD_REJECT_TITLE:
        if signal.lower() in title:
            return True
    # URL 패턴 기반 탈락
    url = item.url.lower()
    if any(domain in url for domain in ["pension114", "auction-run", "glorykorea"]):
        return True

    # 뉴스: 캠핑장이 핵심 주제인지 확인 (단순 언급만 있는 뉴스 제거)
    combined = f"{item.title} {item.description}".lower()
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
                            "1박2일", "미니멀", "캠이야기"]
        if any(p in title for p in visitor_patterns):
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
    mode = "Claude AI (haiku)" if has_api else "규칙 기반"
    print(f"  필터링 시작 [{mode}] ({len(items)}개 → {count}개)")
    print("=" * 60)

    if not items:
        return []

    if not has_api:
        return _rule_based_filter(items, count)

    # === Step 1: AI 필터링 ===
    print(f"\n  [Step 1] AI 필터링 ({len(items)}개 → {count}개)...")
    content_list = _format_content_list(items)
    prompt = FILTER_PROMPT.format(content_list=content_list, count=count)

    response = _call_claude(prompt)
    selections = _parse_json_response(response)

    if not selections:
        print("    AI 필터링 실패, 규칙 기반으로 폴백")
        return _rule_based_filter(items, count)

    filtered = []
    for sel in selections:
        idx = sel.get("index", -1)
        if 0 <= idx < len(items):
            item = items[idx]
            item.category = sel.get("category", "기타")
            filtered.append(item)

    print(f"    선별 완료: {len(filtered)}개")
    for i, item in enumerate(filtered, 1):
        print(f"      {i}. [{item.category}] {item.title[:50]}...")

    if not filtered:
        return _rule_based_filter(items, count)

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
