"""
Newsletter Generator
선별된 콘텐츠로 뉴스레터를 생성합니다.
"""
from datetime import datetime
from typing import List
import os
import json
from collectors.base import ContentItem
from config import NEWSLETTER_TITLE_PREFIX, OUTPUT_DIR, ARCHIVE_DIR


def get_week_info(date: datetime = None) -> dict:
    """Get year, month, and week number for the given date"""
    if date is None:
        date = datetime.now()
    
    # ISO week number
    year = date.year
    month = date.month
    week = date.isocalendar()[1]
    
    # Calculate week of month (approximate)
    first_day = datetime(year, month, 1)
    week_of_month = ((date.day - 1) // 7) + 1
    
    return {
        "year": year,
        "month": month,
        "week": week,
        "week_of_month": week_of_month,
        "date": date.strftime("%Y-%m-%d"),
        "display": f"{year}년 {month}월 {week_of_month}주차"
    }


def generate_newsletter_text(items: List[ContentItem], week_info: dict = None) -> str:
    """
    Generate newsletter text content for KakaoTalk
    카카오톡에서 예쁘게 보이는 포맷
    
    Args:
        items: List of filtered ContentItem objects
        week_info: Week information dictionary
        
    Returns:
        Formatted newsletter text
    """
    if week_info is None:
        week_info = get_week_info()
    
    # 카카오톡 스타일 헤더
    lines = [
        "┏━━━━━━━━━━━━━━━━━━━┓",
        f"  🏕️ 캠핑장 운영 뉴스레터",
        f"  📅 {week_info['display']}",
        "┗━━━━━━━━━━━━━━━━━━━┛",
        "",
    ]
    
    # 콘텐츠 아이템 (카카오톡 가독성 높은 포맷)
    for i, item in enumerate(items, 1):
        # 제목 줄
        lines.append(f"📌 {i}. {item.title}")
        lines.append("")
        
        # 설명 (있으면)
        if item.description:
            short_desc = item.description[:60]
            if len(item.description) > 60:
                short_desc += "..."
            lines.append(f"💬 {short_desc}")
            lines.append("")
        
        # 링크
        lines.append(f"🔗 {item.url}")
        lines.append("")
        lines.append("─────────────────────")
        lines.append("")
    
    # 푸터
    lines.extend([
        "",
        "📊 지난 뉴스레터 모아보기",
        "👉 camping-newsletter.vercel.app",
        "",
        "💡 매주 월요일 오전 9시 발송",
        "━━━━━━━━━━━━━━━━━━━━━"
    ])
    
    return "\n".join(lines)


def generate_newsletter_json(items: List[ContentItem], week_info: dict = None) -> dict:
    """
    Generate newsletter as JSON for dashboard storage
    
    Args:
        items: List of filtered ContentItem objects
        week_info: Week information dictionary
        
    Returns:
        Newsletter data as dictionary
    """
    if week_info is None:
        week_info = get_week_info()
    
    return {
        "id": f"{week_info['year']}-{week_info['month']:02d}-week{week_info['week_of_month']}",
        "title": f"{NEWSLETTER_TITLE_PREFIX} - {week_info['display']}",
        "week_info": week_info,
        "created_at": datetime.now().isoformat(),
        "items": [item.to_dict() for item in items],
        "items_count": len(items)
    }


def save_newsletter(items: List[ContentItem], week_info: dict = None) -> dict:
    """
    Save newsletter to both text and JSON formats
    
    Returns:
        Dictionary with file paths
    """
    if week_info is None:
        week_info = get_week_info()
    
    # Create directories
    os.makedirs(OUTPUT_DIR, exist_ok=True)
    os.makedirs(ARCHIVE_DIR, exist_ok=True)
    
    # File paths
    base_filename = f"newsletter_{week_info['year']}_{week_info['month']:02d}_week{week_info['week_of_month']}"
    
    text_path = os.path.join(OUTPUT_DIR, f"{base_filename}.txt")
    json_path = os.path.join(OUTPUT_DIR, f"{base_filename}.json")
    
    # Archive path (organized by year/month)
    archive_year_dir = os.path.join(ARCHIVE_DIR, str(week_info['year']))
    archive_month_dir = os.path.join(archive_year_dir, f"{week_info['month']:02d}")
    os.makedirs(archive_month_dir, exist_ok=True)
    archive_json_path = os.path.join(archive_month_dir, f"{base_filename}.json")
    
    # Generate content
    text_content = generate_newsletter_text(items, week_info)
    json_content = generate_newsletter_json(items, week_info)
    
    # Save files
    with open(text_path, 'w', encoding='utf-8') as f:
        f.write(text_content)
    
    with open(json_path, 'w', encoding='utf-8') as f:
        json.dump(json_content, f, ensure_ascii=False, indent=2)
    
    with open(archive_json_path, 'w', encoding='utf-8') as f:
        json.dump(json_content, f, ensure_ascii=False, indent=2)
    
    print(f"Newsletter saved:")
    print(f"  Text: {text_path}")
    print(f"  JSON: {json_path}")
    print(f"  Archive: {archive_json_path}")
    
    return {
        "text_path": text_path,
        "json_path": json_path,
        "archive_path": archive_json_path,
        "text_content": text_content,
        "json_content": json_content
    }


if __name__ == "__main__":
    # Test newsletter generation
    test_items = [
        ContentItem(
            title="2026년 친환경 캠핑장 시설개선 지원사업 공고",
            url="https://example.com/1",
            source="정부24",
            description="중소기업청에서 친환경 캠핑장 시설개선을 위한 보조금 지원사업을 공고했습니다.",
            category="정책"
        ),
        ContentItem(
            title="글램핑 시장 전년 대비 30% 성장",
            url="https://example.com/2",
            source="한경",
            description="한국관광공사 발표에 따르면 글램핑 시장이 작년 대비 30% 성장했습니다.",
            category="트렌드"
        ),
    ]
    
    result = save_newsletter(test_items)
    print("\n--- Newsletter Text ---")
    print(result["text_content"])
