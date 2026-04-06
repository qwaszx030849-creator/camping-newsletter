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
1. **"타 캠핑장에서는 이렇게도 하는구나"** - 다른 캠핑장의 운영 전략, 차별화 포인트
2. **"이러니 장사가 잘되는구나"** - 예약률 높은 캠핑장의 비결, 재방문 유도 전략
3. **"생태계 흐름에 맞춰야겠구나"** - 캠핑 산업 동향, 고객 니즈 변화
4. **"온/오프라인 관리가 중요하구나"** - 리뷰 관리, 네이버 플레이스, 시설 청결

## ✅ 선별해야 할 콘텐츠 (캠핑장 사장님이 바로 적용 가능한 것만!)
- 캠핑장 매출/예약률을 올린 **구체적인 성공 사례** (수치 포함이면 최고)
- 캠핑장 **시설 개선** 후 효과를 본 사례 (화장실, 샤워실, 사이트 등)
- **예약/리뷰 관리** 노하우 (네이버 플레이스, 블로그, 인스타)
- **계절별 운영 전략** (성수기 대비, 비수기 매출 올리기)
- **고객 응대/불만 해결** 실전 사례
- 캠핑장에 해당되는 **정부 지원금/보조금** 신청 안내

## ❌ 반드시 제외 (아래에 해당하면 절대 선택하지 마세요!)
- **단순 캠핑장 방문 후기** - "여기 다녀왔어요", "캠핑 후기" 수준의 여행기
- **맛집/음식 콘텐츠** - 대게, 횟집, 맛집 추천 등
- **부동산/임대** - 토지 매매, 펜션 임대, 분양 콘텐츠
- **농업/재배** - 와사비 재배, 농장 운영 등
- **캠핑 용품/장비 리뷰** - 텐트, 침낭, 매트 추천
- **차박/노지 캠핑** - 무료 주차장, 차박지 정보
- **업체 광고/홍보** - 컨테이너 업체, 마케팅 대행사, 시공업체 광고
- **캠핑장과 무관한 정부지원** - 다회용기, 출생친화정책 등
- **뜬구름 잡는 일반론** - "서비스가 중요합니다" 같은 막연한 조언
- **다른 카페/커뮤니티 공지** - 스티커, 활동정지, 카페 운영 관련
- **순수 펜션** - 캠핑장이 아닌 펜션 추천/후기

## 📋 콘텐츠 목록
{content_list}

## 📤 응답 형식 (JSON)
캠지기가 **"이거 도움 되겠다!"** 느낄 {count}개를 선별하세요.
반드시 위의 제외 목록에 해당하는 콘텐츠는 포함하지 마세요!

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

## 🎯 최종 검증 - 이 질문에 "YES"인 글만 선택하세요
**"이 글을 읽고 내 캠핑장에 이번 주에 바로 적용하거나 참고할 수 있는 구체적인 내용이 있는가?"**

## ✅ "이거다!" 싶은 콘텐츠 (이런 글만 선택)
1. **캠핑장 매출을 올린 구체적 사례** - "화장실 리모델링 후 예약 30% 증가" 같은 수치
2. **캠핑장 운영 실전 팁** - 청소 체크리스트, 고객 응대 매뉴얼, 예약 관리 방법
3. **성공한 캠핑장의 비결** - 예약률 높은 캠핑장이 뭘 다르게 하는지
4. **온라인 마케팅 실전** - 네이버 플레이스, 인스타그램 활용 사례
5. **고객 불만 해결 사례** - 실제로 어떻게 해결했는지
6. **캠핑장 지원금/보조금** - 신청 가능한 정부 지원 정보

## ❌ 절대 선택하지 마세요! (이런 글은 무조건 제외)
- **캠핑장과 직접 관련 없는 일반적 경영/자기계발 이야기** - "모든 개인은 회사다" 같은 일반론
- **여행지/관광지 추천** - 온천, 리조트, 여행코스 추천
- **특정 업체의 제품/서비스 홍보** - "OO업체 추천", "XX 시공 사례" 등 업체 광고
- **캠핑장 예약/방문 안내** - 특정 캠핑장 오시는길, 예약오픈 안내
- **동화책/소설/엔터테인먼트** - 캠핑 관련 창작물
- **일반적인 마케팅 이론** - 캠핑장이 아닌 일반 업종 마케팅
- **다른 카페/커뮤니티 공지** - 스티커, 활동정지, 카페 운영 관련
- **캠핑용품 판매/리뷰** - 매트, 텐트, 침낭 등 제품 홍보

## 📋 MD가 선별한 콘텐츠 (2단계 통과)
{content_list}

## 📤 최종 선별
위 ❌ 목록에 해당하는 글을 **반드시 전부 빼고**, 정말 **캠핑장 사장님이 읽고 도움 받을 {count}개**만 골라주세요.

```json
[
  {{"index": 0, "category": "운영노하우", "actionable": "청결 체크리스트 만들어 적용", "priority": 1}},
  {{"index": 3, "category": "성공사례", "actionable": "성수기 알바 채용 기준 참고", "priority": 1}},
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
        print(f"    Gemini API error: {e}")
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
        print(f"    JSON parsing error: {e}")
    return []


def _format_content_list(items: List[ContentItem]) -> str:
    """콘텐츠 목록을 프롬프트용 문자열로 변환"""
    content_list = ""
    for i, item in enumerate(items):
        desc = item.description[:300] if item.description else ""
        content_list += f"""
[{i}] title: {item.title}
    source: {item.source}
    desc: {desc}
"""
    return content_list


# ============================================================================
# 규칙 기반 점수 필터 (Gemini API 키 없을 때 사용)
# ============================================================================

# 제목/내용에서 운영자 인사이트 제공 여부를 판별하는 강한 신호
_STRONG_POSITIVE_SIGNALS = [
    # 매출/수익 관련 (캠핑장 사장이 직접 관심 가지는 핵심 주제)
    "매출 올리", "매출 상승", "매출 증가", "매출 극대화",
    "수익 구조", "수익 모델", "순이익", "영업이익",
    "예약률 높", "예약률 상승", "예약 증가",
    "재방문율", "재방문 높", "고객 만족도",
    # 운영 노하우/전략
    "운영 노하우", "운영 전략", "운영 팁", "운영 비결",
    "성공 비결", "성공 사례", "성공한 캠핑장",
    "위탁 운영", "위탁경영",
    # 마케팅 실전
    "네이버플레이스 상위", "상위노출", "마케팅 효과", "마케팅 성공",
    "인스타 마케팅", "블로그 마케팅", "온라인 마케팅",
    "예약 밀리", "예약 폭주",
    # 시설 개선 효과
    "리모델링 후", "시설 개선 후", "시설 투자 효과",
    # 정부 지원
    "지원사업", "보조금", "지원금 신청",
    # 비수기/성수기 전략
    "비수기 매출", "비수기 전략", "성수기 대비", "성수기 준비",
]

# 캠핑장 운영과 무관한 콘텐츠를 나타내는 강한 신호
_STRONG_NEGATIVE_SIGNALS = [
    # 방문객/여행 후기
    "다녀왔", "다녀온", "방문 후기", "솔직 후기", "여행 후기",
    "추천 바로가기", "바로가기", "예약 바로가기",
    "가볼만한 곳", "숨겨진 보석", "여행지 추천", "여행 코스",
    "벚꽃 여행", "벚꽃 캠핑", "단풍 여행", "겨울 여행",
    "개화시기", "만개 시기", "축제 일정",
    "데이트 코스", "가족 나들이", "아이와 함께",
    "근처 맛집", "주변 맛집", "주변 관광지",
    "완벽 가이드", "여행 가이드",
    # 캠핑 용품/장비
    "전기그릴", "그릴 비교", "그릴 추천", "버너 추천",
    "텐트 추천", "캠핑용품 추천", "매트 추천", "침낭 추천",
    "캠핑 체어", "캠핑 테이블", "타프 추천",
    "쿨러 추천", "아이스박스", "필수템", "캠핑 준비물",
    # 음식/밀키트/요리
    "밀키트", "냉면", "보리냉면", "맛집", "먹방",
    "레시피", "캠핑 요리", "캠핑 음식",
    "고기 파티", "삼겹살 추천",
    # 설비/업체 광고
    "에어컨 설치", "벽걸이 에어컨", "냉난방 설치",
    "컨테이너 업체", "시공 업체", "설치 업체",
    "문의하세요", "상담 문의", "무료 상담", "견적 문의",
    "반도에너지", "지금 바로 문의",
    # 일반 서적/자기계발
    "읽고 주저리", "책 리뷰", "독서 감상", "서평",
    "판매합니다", "물어보다",
    "마이너스였던 인생", "플러스로 바뀐", "수익파이프라인",
    "자기계발", "드림투유", "네트워크 마케팅",
    # 부동산/금융/매물
    "임대", "매매", "분양", "대출", "금리",
    "토지 면적", "건축 면적", "매각", "부지 매물",
    "레저시설 부지", "관광농원 매매", "수익형 부동산",
    # 엔터테인먼트/연예/낚시성 제목
    "런닝맨", "나는 솔로", "유재석", "유퀴즈",
    "진실은?", "충격 고백", "논란",
    # 일반 무인판매기/자판기 창업 (캠핑장 직접 운영이 아닌 일반 창업)
    "무인판매기 창업", "자판기 창업", "무인 창업",
    # 일반 숙박업 광고 (모텔·호텔 나열형)
    "모텔, 호텔", "호텔, 리조트, 펜션",
    # 할로윈/개인 행사 후기
    "할로윈데이캠핑", "할로윈캠핑",
    # 캠핑장 추천/명소 추천 (방문객 대상 콘텐츠, 운영자 인사이트 X)
    "TOP 5 추천", "TOP 3 추천", "TOP 10 추천", "명소 추천",
    "어디로 갈까", "힐링 명소", "프라이빗한 힐링",
    "캠핑장 추천 베스트", "글램핑장 추천 순위",
    # 부동산 투자/매수 관점 (기존 운영자가 아닌 투자자 대상)
    "급매 물건", "매수 전략", "저가 매수", "침체기 매수",
    "캠핑장 급매", "글램핑장 급매", "캠핑장 인수",
    # 카라반/중고 차량 거래업체 광고
    "중고 카라반", "카라반 거래", "카라반 잭 사용",
    "카라반 매매", "수천 대의 카라반",
    # 마케팅 대행사/블로그 대행 광고
    "블로그 광고 브랜드", "블로그 광고 대행",
    "마케팅 대행사", "광고 대행",
    "효과 리포트 제공", "차별화된 콘텐츠",
    # 특정 업체 제품 홍보/ODM 업체
    "ODM MON모델", "ODM STAY", "자부심 뿜뿜",
]


def _rule_based_score(item: ContentItem) -> float:
    """
    규칙 기반 콘텐츠 점수 (Gemini 없을 때 사용)
    높을수록 운영자에게 유용한 콘텐츠
    """
    text = f"{item.title} {item.description}".lower()
    title = item.title.lower()
    
    score = 0.0
    
    # 강한 긍정 신호 (제목에 있으면 +3, 본문에 있으면 +1.5)
    for signal in _STRONG_POSITIVE_SIGNALS:
        if signal in title:
            score += 3.0
        elif signal in text:
            score += 1.5
    
    # 강한 부정 신호 (제목에 있으면 -5, 본문에 있으면 -2)
    for signal in _STRONG_NEGATIVE_SIGNALS:
        if signal in title:
            score -= 5.0
        elif signal in text:
            score -= 2.0
    
    # 보너스: "사장님", "대표님", "운영자", "캠지기" 언급 → 운영자 대상 글
    owner_words = ["사장님", "대표님", "운영자", "캠지기", "관리인"]
    for w in owner_words:
        if w in text:
            score += 2.0
    
    # 페널티: 제목이 특정 지역 + 여행/캠핑장 추천 패턴
    import re
    if re.search(r'(벚꽃|단풍|여행|축제).*(캠핑장|글램핑).*(추천|바로가기)', title):
        score -= 10.0
    if re.search(r'(캠핑장|글램핑).*(추천|후기).*(바로가기)', title):
        score -= 10.0
    
    return score


def step2_md_filter(items: List[ContentItem], target_count: int = 20) -> List[ContentItem]:
    """
    2단계: MD 관점 필터링
    - Gemini API 있으면 AI 필터링
    - 없으면 규칙 기반 점수제로 필터링
    """
    print(f"\n  [step2] MD gwanJeom filtering ({len(items)} -> {target_count})")
    
    if len(items) <= target_count:
        return items
    
    if GEMINI_API_KEY:
        content_list = _format_content_list(items)
        prompt = MD_FILTER_PROMPT.format(content_list=content_list, count=target_count)
        
        response = _call_gemini(prompt)
        selections = _parse_json_response(response)
        
        if selections:
            result = []
            for sel in selections:
                idx = sel.get("index", -1)
                if 0 <= idx < len(items):
                    item = items[idx]
                    item.category = sel.get("type", "gi-ta")
                    result.append(item)
            
            print(f"    AI seonByeol: {len(result)}gae")
            return result[:target_count]
    
    # Gemini 없거나 실패 시: 규칙 기반 점수 필터링
    print("    gyuChik giBan jeomSu filtering...")
    scored = [(item, _rule_based_score(item)) for item in items]
    scored.sort(key=lambda x: x[1], reverse=True)
    
    # 점수 0 이하인 것은 가능하면 제외
    result = [item for item, sc in scored if sc > 0][:target_count]
    
    # 부족하면 점수 높은 순으로 채움
    if len(result) < target_count:
        existing_urls = {item.url for item in result}
        for item, sc in scored:
            if item.url not in existing_urls:
                result.append(item)
                if len(result) >= target_count:
                    break
    
    print(f"    gyuChik giban seonByeol: {len(result)}gae (score > 0: {sum(1 for _, s in scored if s > 0)}gae)")
    return result[:target_count]


def _remove_duplicate_topics(items: List[ContentItem]) -> List[ContentItem]:
    """
    유사한 주제의 기사가 여러 개일 때 가장 점수 높은 1개만 유지
    예: 무인자판기 관련 글 3개 → 상위 1개만
    """
    import re
    
    # 주제 클러스터 키워드 (같은 그룹으로 묶을 키워드들)
    topic_clusters = [
        ["무인 자판기", "무인자판기", "키오스크 수익", "자판기 운영", "자판기 도입"],
        ["네이버플레이스", "네이버 플레이스", "상위노출"],
        ["인허가", "사업계획 승인", "등록 절차"],
        ["리모델링", "시설 개선", "시설 투자"],
    ]
    
    cluster_best = {}  # cluster_id -> (item, score)
    non_clustered = []
    
    for item in items:
        text = f"{item.title} {item.description}".lower()
        score = _rule_based_score(item)
        matched_cluster = None
        
        for cid, keywords in enumerate(topic_clusters):
            if any(kw in text for kw in keywords):
                matched_cluster = cid
                break
        
        if matched_cluster is not None:
            if matched_cluster not in cluster_best or score > cluster_best[matched_cluster][1]:
                cluster_best[matched_cluster] = (item, score)
        else:
            non_clustered.append(item)
    
    result = [entry[0] for entry in cluster_best.values()] + non_clustered
    removed = len(items) - len(result)
    if removed > 0:
        print(f"    🔄 유사 주제 중복 {removed}개 제거")
    return result


def step3_owner_filter(items: List[ContentItem], target_count: int = 10) -> List[ContentItem]:
    """
    3단계: 캠지기(운영자) 관점 실용성 필터링
    - Gemini API 있으면 AI 필터링
    - 없으면 규칙 기반 점수제로 2차 필터링
    - 아이템 수가 target_count 이하라도 score <= 0인 노이즈는 제거
    """
    print(f"\n  [step3] camJiGi silYongSeong filtering ({len(items)} -> {target_count})")
    
    # 유사 주제 중복 제거
    items = _remove_duplicate_topics(items)
    
    # 아이템 수가 target_count 이하라도, 노이즈(score <= 0)는 반드시 제거
    scored = [(item, _rule_based_score(item)) for item in items]
    clean_items = [item for item, sc in scored if sc > 0]
    removed_noise = len(items) - len(clean_items)
    if removed_noise > 0:
        print(f"    🗑️ 품질 미달(score≤0) {removed_noise}개 제거")
    items = clean_items if clean_items else items  # 전부 제거되면 원본 유지
    
    if GEMINI_API_KEY:
        content_list = _format_content_list(items)
        prompt = CAMPGROUND_OWNER_FILTER_PROMPT.format(content_list=content_list, count=target_count)
        
        response = _call_gemini(prompt)
        selections = _parse_json_response(response)
        
        if selections:
            result = []
            for sel in selections:
                idx = sel.get("index", -1)
                if 0 <= idx < len(items):
                    item = items[idx]
                    item.category = sel.get("category", item.category)
                    item.score = sel.get("priority", 3)
                    result.append(item)
            
            result.sort(key=lambda x: x.score if x.score else 3)
            print(f"    AI choejong seonByeol: {len(result)}gae")
            return result[:target_count]
    
    # Gemini 없거나 실패 시: 규칙 기반 2차 필터링
    print("    gyuChik giban 2cha filtering...")
    scored = [(item, _rule_based_score(item)) for item in items]
    scored.sort(key=lambda x: x[1], reverse=True)
    
    result = []
    for item, sc in scored[:target_count]:
        # 카테고리 자동 분류
        text = f"{item.title} {item.description}".lower()
        if any(w in text for w in ["매출", "수익", "예약률", "재방문"]):
            item.category = "maeChul/seongGong"
        elif any(w in text for w in ["마케팅", "인스타", "플레이스", "상위노출", "블로그"]):
            item.category = "marketing"
        elif any(w in text for w in ["지원사업", "보조금", "지원금", "인허가"]):
            item.category = "jeongBuJiWon"
        elif any(w in text for w in ["시설", "리모델링", "화장실", "사이트 조성"]):
            item.category = "siSeolGaeSeon"
        elif any(w in text for w in ["트렌드", "동향", "시장", "통계"]):
            item.category = "trend"
        else:
            item.category = "unYeongNoHaWoo"
        item.score = sc
        result.append(item)
    
    print(f"    choejong seonByeol: {len(result)}gae")
    return result


def filter_content_3step(
    items: List[ContentItem], 
    final_count: int = NEWSLETTER_ITEMS_COUNT
) -> List[ContentItem]:
    """
    3단계 필터링 파이프라인 (AI 또는 규칙 기반)
    
    1단계: 수집 (이미 완료, items로 전달됨)
    2단계: MD 관점 필터링 (운영에 도움되는 콘텐츠)
    3단계: 캠지기 관점 필터링 (실용적, 적용 가능한 콘텐츠)
    """
    print("\n" + "=" * 60)
    mode = "AI (Gemini)" if GEMINI_API_KEY else "gyuChik giban jeomSuje"
    print(f"  3danGye filtering siJak [{mode}]")
    print("=" * 60)
    print(f"  ipRyeok: {len(items)}gae contents")
    
    if not items:
        return []
    
    # 2단계에서는 최종 개수의 2배 선별 (여유분 확보)
    step2_count = min(final_count * 2, len(items))
    
    # 2단계: MD 관점 필터링
    md_filtered = step2_md_filter(items, target_count=step2_count)
    
    # 3단계: 캠지기 관점 실용성 필터링
    final_result = step3_owner_filter(md_filtered, target_count=final_count)
    
    print("\n" + "-" * 60)
    print(f"  choejong gyeolGwa: {len(final_result)}gae seonByeol")
    print("-" * 60)
    
    for i, item in enumerate(final_result, 1):
        sc = f"(score:{item.score:.1f})" if item.score else ""
        print(f"   {i}. [{item.category}] {sc} {item.title[:50]}...")
    
    return final_result


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
