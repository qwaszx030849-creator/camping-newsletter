"""
3단계 AI 필터링 시스템
=======================
1단계: 대량 수집 → 2단계: MD 관점 필터 → 3단계: 캠지기 관점 실용성 필터

캠핑장 담당 MD와 실제 운영자(캠지기) 관점에서 
정말 도움이 되는 콘텐츠만 선별합니다.
"""
import google.generativeai as genai
import json
from typing import List, Tuple
from collectors.base import ContentItem
from config import GEMINI_API_KEY, NEWSLETTER_ITEMS_COUNT


# Gemini API 설정
if GEMINI_API_KEY:
    genai.configure(api_key=GEMINI_API_KEY)


# ============================================================================
# 2단계: MD(상품기획자) 관점 필터 - 캠지기 메타인지 향상
# ============================================================================
MD_FILTER_PROMPT = """당신은 **캠핑장 담당 MD**입니다.
캠핑장 사장님(캠지기)이 뉴스레터를 읽고 아래 4가지 메타인지를 갖도록 콘텐츠를 선별합니다.

## 🎯 캠지기가 가져야 할 메타인지
1. **"타 캠핑장에서는 이렇게도 하는구나"** - 성공 사례, 차별화 전략
2. **"이러니 장사가 잘되는구나"** - 인기 캠핑장 비결, 재방문 높은 이유
3. **"생태계 흐름에 맞춰야겠구나"** - 캠핑 트렌드, 고객 니즈 변화
4. **"온/오프라인 관리가 중요하구나"** - 리뷰 관리, 시설 청결, 서비스

## ✅ 선별해야 할 콘텐츠
- **성공 캠핑장 운영 사례** - 예약 잘되는 곳, 재방문율 높은 곳의 비결
- **고객 응대/불만 대응** - 실제 해결 사례, 리뷰 관리 노하우
- **캠핑 트렌드 뉴스** - 시장 동향, 고객 니즈 변화
- **온라인 관리** - 네이버 플레이스, 예약 시스템, 리뷰 응대
- **오프라인 관리** - 청결, 시설, 화장실, 현장 서비스
- **계절별 운영/이벤트** - 성수기 준비, 비수기 활성화, 고객 이벤트

## ❌ 반드시 제외 (광고/쓸모없는 글)
- **업체 광고** - 세탁기 업체, 컨테이너 업체, 마케팅 대행사 홍보
- **캠핑장과 무관한 정부지원** - 다회용기, 출생친화정책 등 무관한 것
- **단순 캠핑 방문 후기** - "여기 다녀왔어요" 수준의 여행기
- **제품 리뷰** - 캠핑 장비, 텐트, 용품 리뷰

## 📋 콘텐츠 목록
{content_list}

## 📤 응답 형식 (JSON)
캠지기가 **"이거 도움 되겠다!"** 느낄 {count}개를 선별하세요.

```json
[
  {{"index": 0, "type": "성공사례", "insight": "타 캠핑장에서는 이렇게도 하는구나"}},
  {{"index": 3, "type": "트렌드", "insight": "생태계 흐름에 맞춰야겠구나"}},
  {{"index": 5, "type": "온라인관리", "insight": "온/오프라인 관리가 중요하구나"}}
]
```
"""








# ============================================================================
# 3단계: 캠지기(캠핑장 운영자) 관점 실용성 필터
# ============================================================================
CAMPGROUND_OWNER_FILTER_PROMPT = """당신은 **캠핑장을 직접 운영하는 사장님(캠지기)**입니다.
20년차 캠핑장 운영 경험이 있고, 현장에서 뭐가 정말 필요한지 압니다.

## 🎯 최종 검증 기준
"이 정보를 보고 **내 캠핑장에 바로 적용하거나, 당장 행동**할 수 있는가?"

## ✅ "실용적이다!"라고 느끼는 콘텐츠
1. **구체적인 운영 팁** - 청소 방법, 고객 응대, 예약 관리 등 바로 적용 가능
2. **투자 대비 효과** - "화장실 리모델링 후 후기 30% 증가" 같은 구체적 수치
3. **고객 만족 포인트** - 후기에서 언급된 구체적인 만족 요소
4. **마케팅 실전 노하우** - 인스타, 블로그 홍보 성공 사례
5. **신청 가능한 정부 지원** - 마감 전 신청 가능한 보조금/지원사업

## ❌ 이런 건 내게 쓸모없다! (절대 선택 금지)
- **다른 카페/커뮤니티 공지** - 스티커, 활동정지, 카페 운영 관련
- **캠핑용품 판매글** - 매트, 텐트, 침낭 등 제품 홍보
- **특정 캠핑장 예약 광고** - "예약 오픈", "사전예약 안내"
- **이벤트/프로모션** - 무료입장권, 할인 이벤트
- **차박지 공유** - 무료 주차장, 차박 장소 정보 (캠핑장 운영과 무관)
- **뜬구름 잡는 일반론** - "서비스가 중요합니다" 같은 막연한 조언

## 📋 MD가 선별한 콘텐츠 (2단계 통과)
{content_list}

## 📤 최종 선별
광고성 글을 **모두 빼고**, 정말 **실용적인 {count}개**만 골라주세요.

```json
[
  {{"index": 0, "category": "고객후기", "actionable": "청결 체크리스트 만들어 적용", "priority": 1}},
  {{"index": 3, "category": "운영노하우", "actionable": "성수기 알바 채용 기준 참고", "priority": 1}},
  {{"index": 5, "category": "마케팅", "actionable": "인스타 해시태그 전략 바로 적용", "priority": 2}}
]
```
"""


def _call_gemini(prompt: str) -> str:
    """Gemini API 호출"""
    try:
        model = genai.GenerativeModel('gemini-1.5-flash')
        response = model.generate_content(prompt)
        return response.text
    except Exception as e:
        print(f"    ⚠️ Gemini API 오류: {e}")
        return ""


def _parse_json_response(response_text: str) -> list:
    """JSON 응답 파싱"""
    try:
        json_start = response_text.find('[')
        json_end = response_text.rfind(']') + 1
        if json_start != -1 and json_end > json_start:
            json_str = response_text[json_start:json_end]
            return json.loads(json_str)
    except Exception as e:
        print(f"    ⚠️ JSON 파싱 오류: {e}")
    return []


def _format_content_list(items: List[ContentItem]) -> str:
    """콘텐츠 목록을 프롬프트용 문자열로 변환"""
    content_list = ""
    for i, item in enumerate(items):
        desc = item.description[:300] if item.description else ""
        content_list += f"""
[{i}] 제목: {item.title}
    출처: {item.source}
    설명: {desc}
"""
    return content_list


def step2_md_filter(items: List[ContentItem], target_count: int = 20) -> List[ContentItem]:
    """
    2단계: MD 관점 필터링
    - 캠핑장 운영에 도움이 되는 콘텐츠 선별
    - 지역 한정 정부지원은 최소화
    """
    print(f"\n🎯 [2단계] MD 관점 필터링 ({len(items)}개 → {target_count}개)")
    
    if not GEMINI_API_KEY:
        print("    ⚠️ Gemini API 키 없음. 첫 항목들 반환")
        return items[:target_count]
    
    if len(items) <= target_count:
        return items
    
    content_list = _format_content_list(items)
    prompt = MD_FILTER_PROMPT.format(content_list=content_list, count=target_count)
    
    response = _call_gemini(prompt)
    selections = _parse_json_response(response)
    
    if not selections:
        print("    ⚠️ AI 응답 파싱 실패. 첫 항목들 반환")
        return items[:target_count]
    
    result = []
    for sel in selections:
        idx = sel.get("index", -1)
        if 0 <= idx < len(items):
            item = items[idx]
            item.category = sel.get("type", "기타")
            result.append(item)
    
    print(f"    ✅ MD 선별 완료: {len(result)}개")
    
    # 선별 결과 요약
    categories = {}
    for item in result:
        cat = item.category
        categories[cat] = categories.get(cat, 0) + 1
    print(f"    📊 유형별: {categories}")
    
    return result[:target_count]


def step3_owner_filter(items: List[ContentItem], target_count: int = 10) -> List[ContentItem]:
    """
    3단계: 캠지기(운영자) 관점 실용성 필터링
    - 실제 적용 가능한 콘텐츠만 최종 선별
    """
    print(f"\n🏕️ [3단계] 캠지기 실용성 필터링 ({len(items)}개 → {target_count}개)")
    
    if not GEMINI_API_KEY:
        print("    ⚠️ Gemini API 키 없음. 첫 항목들 반환")
        return items[:target_count]
    
    if len(items) <= target_count:
        return items
    
    content_list = _format_content_list(items)
    prompt = CAMPGROUND_OWNER_FILTER_PROMPT.format(content_list=content_list, count=target_count)
    
    response = _call_gemini(prompt)
    selections = _parse_json_response(response)
    
    if not selections:
        print("    ⚠️ AI 응답 파싱 실패. 첫 항목들 반환")
        return items[:target_count]
    
    result = []
    for sel in selections:
        idx = sel.get("index", -1)
        if 0 <= idx < len(items):
            item = items[idx]
            item.category = sel.get("category", item.category)
            item.score = sel.get("priority", 3)
            result.append(item)
    
    # 우선순위로 정렬 (낮은 숫자가 높은 우선순위)
    result.sort(key=lambda x: x.score if x.score else 3)
    
    print(f"    ✅ 최종 선별 완료: {len(result)}개")
    
    return result[:target_count]


def filter_content_3step(
    items: List[ContentItem], 
    final_count: int = NEWSLETTER_ITEMS_COUNT
) -> List[ContentItem]:
    """
    3단계 AI 필터링 파이프라인
    
    1단계: 수집 (이미 완료, items로 전달됨)
    2단계: MD 관점 필터링 (운영에 도움되는 콘텐츠)
    3단계: 캠지기 관점 필터링 (실용적, 적용 가능한 콘텐츠)
    4단계: 강제 비율 조정 (마케팅/정부지원 50% 이하)
    
    Args:
        items: 1단계에서 수집된 모든 콘텐츠
        final_count: 최종 선별할 개수 (기본 10개)
    
    Returns:
        최종 선별된 실용적인 콘텐츠 리스트
    """
    print("\n" + "=" * 60)
    print("🔄 3단계 AI 필터링 시작")
    print("=" * 60)
    print(f"📥 입력: {len(items)}개 콘텐츠")
    
    if not items:
        return []
    
    # 2단계에서는 최종 개수의 2배 선별 (여유분 확보)
    step2_count = min(final_count * 2, len(items))
    
    # 2단계: MD 관점 필터링
    md_filtered = step2_md_filter(items, target_count=step2_count)
    
    # 3단계: 캠지기 관점 실용성 필터링
    after_step3 = step3_owner_filter(md_filtered, target_count=final_count + 5)  # 여유분 확보
    
    # 4단계: 강제 비율 조정 (코드로 강제 적용)
    final_result = _balance_content_types(after_step3, items, final_count)
    
    print("\n" + "-" * 60)
    print(f"📤 최종 결과: {len(final_result)}개 선별")
    print("-" * 60)
    
    for i, item in enumerate(final_result, 1):
        priority = "⭐" * (4 - (item.score or 3))
        print(f"   {i}. [{item.category}] {priority} {item.title[:40]}...")
    
    return final_result


def _balance_content_types(filtered: List[ContentItem], all_items: List[ContentItem], target_count: int) -> List[ContentItem]:
    """
    콘텐츠 유형별 강제 비율 조정
    - 마케팅(인스타/플레이스): 최대 4개 (40%)
    - 정부지원: 최대 3개 (30%)
    - 나머지(뉴스/블로그/카페): 최소 3개 (30%)
    """
    print("\n⚖️ [4단계] 콘텐츠 비율 조정...")
    
    # 유형별 분류
    marketing = []
    gov_support = []
    others = []
    
    for item in filtered:
        cat = (item.category or "").lower()
        if "마케팅" in cat or "인스타" in cat or "플레이스" in cat or "sns" in cat:
            marketing.append(item)
        elif "정부" in cat or "지원" in cat:
            gov_support.append(item)
        else:
            others.append(item)
    
    # 비율 적용 (마케팅 4개, 정부지원 3개, 나머지 3개)
    max_marketing = 4
    max_gov = 3
    min_others = target_count - max_marketing - max_gov
    
    result = []
    
    # 마케팅 추가 (최대 4개)
    result.extend(marketing[:max_marketing])
    
    # 정부지원 추가 (최대 3개)
    result.extend(gov_support[:max_gov])
    
    # 나머지 추가
    result.extend(others[:min_others])
    
    # 부족하면 원본에서 추가
    if len(result) < target_count:
        remaining = target_count - len(result)
        # 기존 URL 제외하고 추가
        existing_urls = {item.url for item in result}
        for item in all_items:
            if item.url not in existing_urls:
                cat = (item.category or "").lower()
                # 마케팅/정부지원이 아닌 것 우선
                if "마케팅" not in cat and "정부" not in cat and "지원" not in cat:
                    result.append(item)
                    if len(result) >= target_count:
                        break
    
    # 그래도 부족하면 아무거나 추가
    if len(result) < target_count:
        existing_urls = {item.url for item in result}
        for item in filtered:
            if item.url not in existing_urls:
                result.append(item)
                if len(result) >= target_count:
                    break
    
    # 결과 요약
    categories = {}
    for item in result:
        cat = item.category or "기타"
        categories[cat] = categories.get(cat, 0) + 1
    print(f"   📊 최종 유형별: {categories}")
    
    return result[:target_count]


# 기존 filter_content 함수와의 호환성 유지
def filter_content(items: List[ContentItem], count: int = NEWSLETTER_ITEMS_COUNT) -> List[ContentItem]:
    """기존 함수와의 호환성을 위한 wrapper"""
    return filter_content_3step(items, final_count=count)


if __name__ == "__main__":
    # 테스트
    test_items = [
        ContentItem(
            title="인천시 다회용기 지원사업 공모",
            url="https://example.com/1",
            source="정부24",
            description="인천시에서 다회용기 지원사업을 공모합니다. 인천 지역 캠핑장만 해당..."
        ),
        ContentItem(
            title="캠핑장 화장실 리모델링 후 후기 폭발한 사장님 이야기",
            url="https://example.com/2",
            source="캠차",
            description="화장실 리모델링에 2천만원 투자했는데, 후기에 '화장실 깨끗해서 재방문' 댓글이 급증..."
        ),
        ContentItem(
            title="2026년 전국 야영장 시설개선 보조금 신청 안내",
            url="https://example.com/3",
            source="문화체육관광부",
            description="전국 야영장 대상 시설개선 보조금 최대 5천만원 지원. 신청기간 2월 1일~28일..."
        ),
    ]
    
    result = filter_content_3step(test_items, final_count=2)
    print("\n최종 선별 결과:")
    for item in result:
        print(f"  - [{item.category}] {item.title}")
