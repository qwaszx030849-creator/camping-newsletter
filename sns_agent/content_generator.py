"""
SNS 콘텐츠 자동 생성 에이전트
캠핑장 프로파일 + 캠핏 데이터 → 인스타 캡션, 블로그 초안 자동 생성
"""
import json
import os
from datetime import datetime, timedelta
from typing import Optional
import google.generativeai as genai

# ── 설정 ─────────────────────────────────────────────────
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY", "")
genai.configure(api_key=GEMINI_API_KEY)

CLIENTS_DIR = os.path.join(os.path.dirname(__file__), "clients")


# ── 클라이언트 프로파일 로드 ──────────────────────────────
def load_profile(client_id: str) -> dict:
    profile_path = os.path.join(CLIENTS_DIR, client_id, "profile.json")
    with open(profile_path, "r", encoding="utf-8") as f:
        return json.load(f)


# ── 캠핏 데이터 입력 (수동 또는 자동) ────────────────────
def get_camfit_data(client_id: str) -> dict:
    """
    캠핏 어드민에서 가져온 데이터 입력 포인트.
    현재: 수동 입력 (사용자가 제공)
    향후: 캠핏 API 또는 스크래핑 자동화 연동
    """
    data_path = os.path.join(CLIENTS_DIR, client_id, "camfit_data.json")
    if os.path.exists(data_path):
        with open(data_path, "r", encoding="utf-8") as f:
            return json.load(f)
    # 기본 빈 데이터 반환 (데이터 없으면 일반 콘텐츠 생성)
    return {
        "occupancy_rate": None,
        "recent_reviews": [],
        "peak_days": [],
        "low_days": [],
        "monthly_revenue_trend": None,
        "data_date": None,
    }


# ── 인스타그램 캡션 생성 ──────────────────────────────────
def generate_instagram_caption(
    profile: dict,
    camfit_data: dict,
    post_theme: str,
    include_hashtags: bool = True
) -> dict:
    """
    인스타그램 포스트 캡션 + 해시태그 생성
    
    Returns:
        {
            "caption": str,
            "hashtags": str,
            "image_direction": str,  # 어떤 사진을 써야 하는지 방향
        }
    """
    model = genai.GenerativeModel("gemini-2.0-flash-exp")
    
    brand = profile.get("brand", {})
    location = profile.get("location", {})
    
    # 캠핏 데이터 기반 콘텐츠 전략 결정
    content_strategy = ""
    if camfit_data.get("occupancy_rate") is not None:
        rate = camfit_data["occupancy_rate"]
        if rate < 50:
            content_strategy = f"⚠️ 이번 주 예약률 {rate}% (낮음) → 공실 채우는 프로모션 강조"
        elif rate > 80:
            content_strategy = f"✅ 이번 주 예약률 {rate}% (높음) → 인기 캠핑장 이미지 강화"
    
    if camfit_data.get("recent_reviews"):
        best_review = camfit_data["recent_reviews"][0]
        content_strategy += f"\n✅ 최근 좋은 리뷰: '{best_review}' → 리뷰 강조 콘텐츠 활용 가능"
    
    prompt = f"""
당신은 전문 SNS 마케터입니다. 아래 캠핑장 정보를 바탕으로 인스타그램 포스트를 작성하세요.

## 캠핑장 정보
- 이름: {profile['name']}
- 위치: {location.get('address', '정보 없음')} ({location.get('region', '')})
- 콘셉트: {brand.get('main_concept', '자연 속 힐링 캠핑')}
- 톤앤매너: {brand.get('tone', '따뜻하고 감성적')}
- 핵심 키워드: {', '.join(brand.get('color_keywords', []))}
- 타겟: {brand.get('target_customer', '가족 캠퍼, 커플')}

## 오늘의 포스트 주제
{post_theme}

## 캠핏 데이터 인사이트 (있는 경우)
{content_strategy if content_strategy else '(데이터 없음 - 일반 콘텐츠 작성)'}

## 요구사항
1. **캡션**: 2~4 문단, 첫 줄은 반드시 눈길을 끄는 문장으로 시작
2. **이모지**: 자연스럽게 2~4개 사용
3. **CTA**: 마지막에 예약/방문 유도 문구 포함 (캠핏 예약 언급 가능)
4. **해시태그**: 20~25개, 대중적인 것과 틈새 태그 混合
5. **사진 방향**: 어떤 사진을 써야 할지 1줄로 설명

아래 JSON 형식으로만 응답하세요:
{{
  "caption": "캡션 내용",
  "hashtags": "#해시태그1 #해시태그2 ...",
  "image_direction": "사진 방향 설명"
}}
"""
    
    response = model.generate_content(prompt)
    text = response.text.strip()
    
    # JSON 파싱
    if "```json" in text:
        text = text.split("```json")[1].split("```")[0].strip()
    elif "```" in text:
        text = text.split("```")[1].split("```")[0].strip()
    
    return json.loads(text)


# ── 네이버 블로그 초안 생성 ────────────────────────────────
def generate_blog_draft(
    profile: dict,
    camfit_data: dict,
    post_topic: str,
    target_keywords: list = None
) -> dict:
    """
    네이버 블로그 포스트 초안 생성 (SEO 최적화)
    
    Returns:
        {
            "title": str,
            "sections": [{"heading": str, "content": str}],
            "seo_keywords": list,
            "meta_description": str,
            "estimated_read_time": str,
        }
    """
    model = genai.GenerativeModel("gemini-2.0-flash-exp")
    
    brand = profile.get("brand", {})
    location = profile.get("location", {})
    region = location.get("region", "")
    
    keywords_str = ", ".join(target_keywords) if target_keywords else f"{region} 캠핑장, {profile['name']}"
    
    prompt = f"""
당신은 네이버 블로그 SEO 전문가입니다. 캠핑장 블로그 포스트 초안을 작성하세요.

## 캠핑장 정보
- 이름: {profile['name']}
- 위치: {location.get('address', '')} ({region})
- 콘셉트: {brand.get('main_concept', '')}
- 타겟: {brand.get('target_customer', '')}

## 포스트 주제
{post_topic}

## 목표 키워드 (검색 최적화)
{keywords_str}

## 요구사항
1. **제목**: 검색 유입을 위한 SEO 제목 (35자 이내, 핵심 키워드 포함)
2. **구성**: 서론 + 본론 3~4섹션 + 결론 구조
3. **분량**: 섹션당 150~250자
4. **말투**: 방문기를 쓰듯 친근하고 생생하게
5. **CTA**: 결론에서 캠핏 예약 유도 (https://camfit.co.kr 언급)
6. **이미지 안내**: 각 섹션에 어떤 사진을 넣어야 할지 [사진: 설명] 형식으로 표시

아래 JSON 형식으로만 응답하세요:
{{
  "title": "블로그 제목",
  "sections": [
    {{"heading": "섹션 제목", "content": "내용 (이미지 안내 포함)"}},
    ...
  ],
  "seo_keywords": ["키워드1", "키워드2", ...],
  "meta_description": "검색 결과에 표시될 요약 (80자 이내)",
  "estimated_read_time": "3분"
}}
"""
    
    response = model.generate_content(prompt)
    text = response.text.strip()
    
    if "```json" in text:
        text = text.split("```json")[1].split("```")[0].strip()
    elif "```" in text:
        text = text.split("```")[1].split("```")[0].strip()
    
    return json.loads(text)


# ── 월간 콘텐츠 캘린더 생성 ──────────────────────────────
def generate_monthly_calendar(profile: dict, camfit_data: dict, year: int = None, month: int = None) -> list:
    """
    한 달치 SNS 콘텐츠 캘린더 자동 생성
    
    Returns:
        [{"date": "2026-03-10", "platform": "instagram", "theme": "주제", "priority": "high"}]
    """
    now = datetime.now()
    if year is None:
        year = now.year
    if month is None:
        month = now.month + 1 if now.month < 12 else 1
    
    tier = profile.get("tier", "스타터")
    scope = profile.get("service_scope", {}).get(tier, {})
    
    instagram_count = scope.get("instagram_posts", 4)
    blog_count = scope.get("blog_posts", 2)
    
    model = genai.GenerativeModel("gemini-2.0-flash-exp")
    
    low_days = camfit_data.get("low_days", [])
    peak_days = camfit_data.get("peak_days", [])
    
    prompt = f"""
{year}년 {month}월 {profile['name']} 캠핑장 SNS 콘텐츠 캘린더를 생성하세요.

## 월간 의무 업로드 수
- 인스타그램: {instagram_count}개 포스트
- 네이버 블로그: {blog_count}개

## 캠핏 데이터
- 예약 많은 날: {peak_days if peak_days else '데이터 없음'}
- 예약 적은 날: {low_days if low_days else '데이터 없음'}
- 공실 채워야 할 주: {low_days if low_days else '없음'}

## 캠핑장 정보
- 콘셉트: {profile['brand'].get('main_concept', '')}
- 시즌: {month}월 {'봄' if 3 <= month <= 5 else '여름' if 6 <= month <= 8 else '가을' if 9 <= month <= 11 else '겨울'}

## 지침
- 예약 적은 날 전 2~3일에 프로모션 콘텐츠 배치
- 주말 직전(금요일)에 주말 캠핑 유도 콘텐츠
- 블로그는 SEO 효과를 위해 월 초/중순에 배치

아래 JSON 배열로만 응답하세요 (총 {instagram_count + blog_count}개):
[
  {{
    "date": "YYYY-MM-DD",
    "platform": "instagram 또는 blog",
    "theme": "콘텐츠 주제",
    "content_type": "일반/프로모션/시즌/리뷰",
    "priority": "high 또는 normal"
  }}
]
"""
    
    response = model.generate_content(prompt)
    text = response.text.strip()
    
    if "```json" in text:
        text = text.split("```json")[1].split("```")[0].strip()
    elif "```" in text:
        text = text.split("```")[1].split("```")[0].strip()
    
    return json.loads(text)


# ── 실행 예시 ─────────────────────────────────────────────
if __name__ == "__main__":
    print("🏕️ SNS 콘텐츠 생성 에이전트 테스트\n")
    
    client_id = "더빌리지"
    
    # 1. 프로파일 로드
    try:
        profile = load_profile(client_id)
        print(f"✅ 프로파일 로드: {profile['name']}")
    except Exception as e:
        print(f"❌ 프로파일 로드 실패: {e}")
        exit()
    
    # 2. 캠핏 데이터 로드 (없으면 빈 데이터)
    camfit_data = get_camfit_data(client_id)
    print(f"📊 캠핏 데이터: {'있음' if camfit_data.get('data_date') else '없음 (일반 콘텐츠로 생성)'}")
    
    # 3. 인스타그램 캡션 생성 테스트
    print("\n📸 인스타그램 캡션 생성 중...")
    try:
        caption_result = generate_instagram_caption(
            profile=profile,
            camfit_data=camfit_data,
            post_theme="봄 캠핑 시즌 오픈 안내 - 따뜻한 봄날 캠핑 분위기"
        )
        print(f"\n✅ 캡션 생성 완료!")
        print(f"📝 캡션:\n{caption_result['caption']}\n")
        print(f"#️⃣ 해시태그:\n{caption_result['hashtags']}\n")
        print(f"📷 사진 방향: {caption_result['image_direction']}")
        
        # 결과 저장
        output_dir = os.path.join(CLIENTS_DIR, client_id, "content_drafts")
        os.makedirs(output_dir, exist_ok=True)
        output_path = os.path.join(output_dir, f"instagram_{datetime.now().strftime('%Y%m%d_%H%M')}.json")
        with open(output_path, "w", encoding="utf-8") as f:
            json.dump(caption_result, f, ensure_ascii=False, indent=2)
        print(f"\n💾 저장됨: {output_path}")
        
    except Exception as e:
        print(f"❌ 캡션 생성 실패: {e}")
    
    # 4. 월간 캘린더 생성 테스트
    print("\n📅 3월 콘텐츠 캘린더 생성 중...")
    try:
        calendar = generate_monthly_calendar(profile, camfit_data, year=2026, month=3)
        print(f"\n✅ 캘린더 생성 완료! ({len(calendar)}개 콘텐츠)")
        for item in calendar:
            emoji = "📸" if item['platform'] == 'instagram' else "📝"
            priority = "🔴" if item.get('priority') == 'high' else "⚪"
            print(f"  {priority} {emoji} {item['date']} | {item['platform']} | {item['theme']}")
        
        # 저장
        cal_path = os.path.join(CLIENTS_DIR, client_id, f"calendar_2026_03.json")
        with open(cal_path, "w", encoding="utf-8") as f:
            json.dump(calendar, f, ensure_ascii=False, indent=2)
        print(f"\n💾 저장됨: {cal_path}")
        
    except Exception as e:
        print(f"❌ 캘린더 생성 실패: {e}")
