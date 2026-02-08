"""
Camping Newsletter Automation - Main Script
캠핑장 뉴스레터 자동화 메인 실행 스크립트
"""
import argparse
from datetime import datetime
from typing import List

from collectors.base import ContentItem
from collectors.government_support import GovernmentSupportCollector
from collectors.google_news import GoogleNewsCollector
from collectors.blog_collector import NaverBlogCollector
from ai_filter import filter_content
from newsletter_generator import save_newsletter, get_week_info
from kakao_sender import send_newsletter
from config import SEARCH_KEYWORDS



def collect_all_content() -> List[ContentItem]:
    """
    캠지기 메타인지 향상을 위한 콘텐츠 수집
    
    목표:
    - "타 캠핑장에서는 이렇게도 하는구나"
    - "이러니 장사가 잘되는구나"  
    - "생태계 흐름에 맞춰야겠구나"
    - "온/오프라인 관리가 중요하구나"
    """
    print("=" * 50)
    print("📡 캠지기 메타인지 향상 콘텐츠 수집")
    print("=" * 50)
    
    all_items = []
    blog_collector = NaverBlogCollector()
    
    # ========================================
    # 1. 캠핑장 운영자 실제 후기/노하우
    # "타 캠핑장에서는 이렇게도 하는구나"
    # ========================================
    print("\n🏆 [1] 캠핑장 운영자 노하우...")
    try:
        operator_keywords = [
            "캠핑장 운영 노하우",
            "캠핑장 사장 후기", 
            "캠핑장 창업 경험",
            "글램핑장 운영 일지",
        ]
        operator_items = blog_collector.collect(operator_keywords)
        all_items.extend(operator_items)
        print(f"   ✅ {len(operator_items)}개 수집")
    except Exception as e:
        print(f"   ❌ Error: {e}")
    
    # ========================================
    # 2. 고객 리뷰에서 배우는 점
    # "이러니 장사가 잘되는구나"
    # ========================================
    print("\n💬 [2] 고객 만족/불만 사례...")
    try:
        review_keywords = [
            "캠핑장 화장실 청결 좋았다",
            "캠핑장 사장님 친절",
            "캠핑장 재방문 이유",
            "캠핑장 별점 5점",
        ]
        review_items = blog_collector.collect(review_keywords)
        all_items.extend(review_items)
        print(f"   ✅ {len(review_items)}개 수집")
    except Exception as e:
        print(f"   ❌ Error: {e}")
    
    # ========================================
    # 3. 캠핑 트렌드 & 뉴스
    # "생태계 흐름에 맞춰야겠구나"
    # ========================================
    print("\n📈 [3] 캠핑 트렌드 뉴스...")
    try:
        trend_keywords = [
            "캠핑 트렌드",
            "글램핑 인기",
            "캠핑장 예약률 상승",
        ]
        news_collector = GoogleNewsCollector()
        trend_items = news_collector.collect(trend_keywords)
        all_items.extend(trend_items)
        print(f"   ✅ {len(trend_items)}개 수집")
    except Exception as e:
        print(f"   ❌ Error: {e}")
    
    # ========================================
    # 4. 시설 투자/개선 사례
    # "온/오프라인 관리가 중요하구나"
    # ========================================
    print("\n🏕️ [4] 시설 투자 사례...")
    try:
        facility_keywords = [
            "캠핑장 화장실 리모델링",
            "캠핑장 시설 개선 효과",
            "글램핑 시설 투자",
        ]
        facility_items = blog_collector.collect(facility_keywords)
        all_items.extend(facility_items)
        print(f"   ✅ {len(facility_items)}개 수집")
    except Exception as e:
        print(f"   ❌ Error: {e}")
    
    # ========================================
    # 5. 이벤트/프로모션 사례
    # ========================================
    print("\n🎉 [5] 이벤트 성공 사례...")
    try:
        event_keywords = [
            "캠핑장 이벤트 성공",
            "캠핑장 프로모션 효과",
            "캠핑장 비수기 마케팅",
        ]
        event_items = blog_collector.collect(event_keywords)
        all_items.extend(event_items)
        print(f"   ✅ {len(event_items)}개 수집")
    except Exception as e:
        print(f"   ❌ Error: {e}")
    
    # 중복 블로그 제거 (같은 블로거 글 1개로 제한)
    unique_items = _remove_duplicate_bloggers(all_items)
    
    print(f"\n📊 수집 완료: {len(all_items)}개 → 중복 제거 후 {len(unique_items)}개")
    return unique_items


def _remove_duplicate_bloggers(items: List[ContentItem]) -> List[ContentItem]:
    """같은 블로거의 글은 1개만 유지"""
    seen_bloggers = set()
    unique = []
    
    for item in items:
        # URL에서 블로거 ID 추출 (blog.naver.com/blogger_id/...)
        url = item.url or ""
        if "blog.naver.com/" in url:
            parts = url.split("blog.naver.com/")
            if len(parts) > 1:
                blogger_id = parts[1].split("/")[0]
                if blogger_id in seen_bloggers:
                    continue
                seen_bloggers.add(blogger_id)
        unique.append(item)
    
    return unique


def run_newsletter_pipeline(test_mode: bool = True, skip_send: bool = False):
    """
    Run the full newsletter pipeline
    
    Args:
        test_mode: If True, sends only to self for testing
        skip_send: If True, skips KakaoTalk sending
    """
    start_time = datetime.now()
    print("\n" + "=" * 60)
    print("🏕️  CAMPING NEWSLETTER AUTOMATION")
    print("=" * 60)
    print(f"Started at: {start_time.strftime('%Y-%m-%d %H:%M:%S')}")
    
    # Step 1: Collect content
    all_items = collect_all_content()
    
    if not all_items:
        print("\n❌ No content collected. Exiting.")
        return
    
    # Step 2: AI Filter
    print("\n" + "=" * 50)
    print("🤖 Filtering with AI...")
    print("=" * 50)
    
    filtered_items = filter_content(all_items)
    print(f"Selected {len(filtered_items)} items from {len(all_items)} candidates")
    
    for i, item in enumerate(filtered_items, 1):
        print(f"  {i}. [{item.category}] {item.title[:50]}...")
    
    # Step 3: Generate Newsletter
    print("\n" + "=" * 50)
    print("📝 Generating newsletter...")
    print("=" * 50)
    
    week_info = get_week_info()
    result = save_newsletter(filtered_items, week_info)
    
    print("\n📄 Newsletter Preview:")
    print("-" * 40)
    print(result["text_content"][:500] + "...")
    
    # Step 4: Send via KakaoTalk
    if not skip_send:
        print("\n" + "=" * 50)
        print("📨 Sending via KakaoTalk...")
        print("=" * 50)
        
        send_result = send_newsletter(result["text_content"], test_mode=test_mode)
        
        if send_result.get("success"):
            print("✅ Newsletter sent successfully!")
        else:
            print(f"⚠️ Send result: {send_result.get('error', 'Unknown error')}")
    else:
        print("\n⏭️ Skipping KakaoTalk send (--skip-send flag)")
    
    # Summary
    end_time = datetime.now()
    duration = (end_time - start_time).total_seconds()
    
    print("\n" + "=" * 60)
    print("✅ PIPELINE COMPLETE")
    print("=" * 60)
    print(f"Duration: {duration:.1f} seconds")
    print(f"Items collected: {len(all_items)}")
    print(f"Items selected: {len(filtered_items)}")
    print(f"Newsletter saved to: {result['text_path']}")
    print(f"Archive saved to: {result['archive_path']}")


def main():
    parser = argparse.ArgumentParser(description="Camping Newsletter Automation")
    parser.add_argument(
        "--test-mode",
        action="store_true",
        help="Run in test mode (send only to self)"
    )
    parser.add_argument(
        "--skip-send",
        action="store_true",
        help="Skip KakaoTalk sending"
    )
    parser.add_argument(
        "--collect-only",
        action="store_true",
        help="Only collect content, don't filter or send"
    )
    
    args = parser.parse_args()
    
    if args.collect_only:
        items = collect_all_content()
        print(f"\nCollected {len(items)} items. Exiting without filtering.")
    else:
        run_newsletter_pipeline(
            test_mode=args.test_mode or True,  # Default to test mode
            skip_send=args.skip_send
        )


if __name__ == "__main__":
    main()
