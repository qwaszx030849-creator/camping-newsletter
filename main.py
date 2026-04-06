"""
Camping Newsletter Automation - Main Script
캠핑장 뉴스레터 자동화 메인 실행 스크립트
"""
import argparse
import json
import os
import glob
from datetime import datetime
from typing import List, Set

from collectors.base import ContentItem
from collectors.government_support import GovernmentSupportCollector
from collectors.google_news import GoogleNewsCollector
from collectors.blog_collector import NaverBlogCollector
from ai_filter import filter_content
from newsletter_generator import save_newsletter, get_week_info
from kakao_sender import send_newsletter
from config import SEARCH_KEYWORDS


def _load_previous_urls() -> Set[str]:
    """이전 뉴스레터에서 사용된 URL 목록을 로드하여 중복 방지"""
    used_urls = set()
    archive_dir = os.path.join(os.path.dirname(__file__), "archive")
    
    # archive 폴더의 모든 JSON 파일에서 URL 수집
    for json_file in glob.glob(os.path.join(archive_dir, "**", "*.json"), recursive=True):
        try:
            with open(json_file, "r", encoding="utf-8") as f:
                data = json.load(f)
                for item in data.get("items", []):
                    url = item.get("url", "")
                    if url:
                        used_urls.add(url)
        except (json.JSONDecodeError, Exception):
            continue
    
    print(f"📋 이전 뉴스레터에서 {len(used_urls)}개 URL 중복 방지 목록 로드")
    return used_urls


def _remove_previously_used(items: List[ContentItem], used_urls: Set[str]) -> List[ContentItem]:
    """이전 뉴스레터에 이미 사용된 URL 제거"""
    new_items = [item for item in items if item.url not in used_urls]
    removed = len(items) - len(new_items)
    if removed > 0:
        print(f"   🔄 이전 뉴스레터 중복 {removed}개 제거")
    return new_items



def collect_all_content() -> List[ContentItem]:
    """
    캠지기 메타인지 향상을 위한 콘텐츠 수집
    
    핵심 원칙: "캠핑장 사장님이 읽고 이번 주에 바로 써먹을 수 있는가?"
    
    목표:
    - "타 캠핑장에서는 이렇게도 하는구나" (운영 노하우)
    - "이러니 장사가 잘되는구나" (매출/성공 사례)
    - "생태계 흐름에 맞춰야겠구나" (산업 뉴스)
    - "온/오프라인 관리가 중요하구나" (마케팅/리뷰)
    """
    print("=" * 50)
    print("  camji-gi metainzi hyangsang contents sujib")
    print("=" * 50)
    
    all_items = []
    blog_collector = NaverBlogCollector()
    
    # ========================================
    # 1. 캠핑장 매출/수익 실전 사례
    # "이러니 장사가 잘되는구나"
    # ========================================
    print("\n[1] campingJang maechul/sueik silJeon saRye...")
    try:
        revenue_keywords = [
            "캠핑장 운영 매출 올리는 방법",
            "캠핑장 사장님 수익 노하우",
            "글램핑장 운영 수익 구조",
            "캠핑장 비수기 매출 전략 운영자",
            "캠핑장 성수기 매출 극대화 운영",
        ]
        revenue_items = blog_collector.collect(revenue_keywords)
        all_items.extend(revenue_items)
        print(f"   -> {len(revenue_items)}gae sujib")
    except Exception as e:
        print(f"   Error: {e}")
    
    # ========================================
    # 2. 예약률/재방문율 높이기
    # "타 캠핑장에서는 이렇게도 하는구나"
    # ========================================
    print("\n[2] yeYagRyul/jaeBangMunRyul nopigi...")
    try:
        booking_keywords = [
            "캠핑장 예약률 높이는 운영 노하우",
            "캠핑장 재방문율 높이는 사장님 전략",
            "캠핑장 고객 만족도 올리는 방법",
            "캠핑장 리뷰 관리 별점 올리기",
        ]
        booking_items = blog_collector.collect(booking_keywords)
        all_items.extend(booking_items)
        print(f"   -> {len(booking_items)}gae sujib")
    except Exception as e:
        print(f"   Error: {e}")
    
    # ========================================
    # 3. 캠핑장 온라인 마케팅 실전
    # "온/오프라인 관리가 중요하구나"
    # ========================================
    print("\n[3] online marketing silJeon...")
    try:
        marketing_keywords = [
            "캠핑장 네이버플레이스 상위노출 운영",
            "캠핑장 인스타그램 마케팅 예약 증가",
            "캠핑장 블로그 마케팅 효과 매출",
            "글램핑장 온라인 마케팅 성공사례",
        ]
        marketing_items = blog_collector.collect(marketing_keywords)
        all_items.extend(marketing_items)
        print(f"   -> {len(marketing_items)}gae sujib")
    except Exception as e:
        print(f"   Error: {e}")
    
    # ========================================
    # 4. 캠핑 산업 트렌드 & 뉴스
    # "생태계 흐름에 맞춰야겠구나"
    # ========================================
    print("\n[4] camping sanUp trend & news...")
    try:
        trend_keywords = [
            "캠핑장 산업 동향 2026",
            "캠핑장 운영 트렌드 변화",
            "글램핑 시장 성장 동향",
        ]
        news_collector = GoogleNewsCollector()
        trend_items = news_collector.collect(trend_keywords)
        all_items.extend(trend_items)
        print(f"   -> {len(trend_items)}gae sujib")
    except Exception as e:
        print(f"   Error: {e}")
    
    # ========================================
    # 5. 시설 개선 & 운영 효율화
    # ========================================
    print("\n[5] siSeol gaeSeon & unYeong hyoYulHwa...")
    try:
        facility_keywords = [
            "캠핑장 시설 개선 후 예약률 상승 사례",
            "캠핑장 화장실 리모델링 효과 운영",
            "캠핑장 사이트 조성 운영자 후기",
        ]
        facility_items = blog_collector.collect(facility_keywords)
        all_items.extend(facility_items)
        print(f"   -> {len(facility_items)}gae sujib")
    except Exception as e:
        print(f"   Error: {e}")
    
    # ========================================
    # 6. 정부 지원/정책
    # ========================================
    print("\n[6] jeongBu jiWon/jeongChaek...")
    try:
        gov_keywords = [
            "캠핑장 지원사업 보조금 2026",
            "야영장 인허가 정책 변경",
            "관광사업 소상공인 캠핑장 지원금",
        ]
        gov_items = blog_collector.collect(gov_keywords)
        all_items.extend(gov_items)
        print(f"   -> {len(gov_items)}gae sujib")
    except Exception as e:
        print(f"   Error: {e}")
    
    # 중복 블로그 제거 (같은 블로거 글 1개로 제한)
    unique_items = _remove_duplicate_bloggers(all_items)
    
    # 이전 뉴스레터에 사용된 URL 제거
    used_urls = _load_previous_urls()
    fresh_items = _remove_previously_used(unique_items, used_urls)
    
    print(f"\n📊 수집 완료: {len(all_items)}개 → 블로거 중복 제거 {len(unique_items)}개 → 이전 뉴스레터 중복 제거 {len(fresh_items)}개")
    return fresh_items


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
    print("  campingJang newsletter jadongHwa system")
    print("=" * 60)
    print(f"siJak siGan: {start_time.strftime('%Y-%m-%d %H:%M:%S')}")
    
    # 1단계: 콘텐츠 수집
    all_items = collect_all_content()
    
    if not all_items:
        print("\n  suJibdoen contents eobseum. jongRyo.")
        return
    
    # 2단계: AI 필터링
    print("\n" + "=" * 50)
    print("  contents filtering...")
    print("=" * 50)
    
    filtered_items = filter_content(all_items)
    print(f"chong {len(all_items)}gae jung {len(filtered_items)}gae seonByeol")
    
    for i, item in enumerate(filtered_items, 1):
        print(f"  {i}. [{item.category}] {item.title[:50]}...")
    
    # 3단계: 뉴스레터 생성
    print("\n" + "=" * 50)
    print("  newsletter saengSeong...")
    print("=" * 50)
    
    week_info = get_week_info()
    result = save_newsletter(filtered_items, week_info)
    
    print("\n  newsletter preview:")
    print("-" * 40)
    print(result["text_content"][:500] + "...")
    
    # 4단계: 카카오톡 발송
    if not skip_send:
        print("\n" + "=" * 50)
        print("  KakaoTalk balSong...")
        print("=" * 50)
        
        send_result = send_newsletter(result["text_content"], test_mode=test_mode)
        
        if send_result.get("success"):
            print("  newsletter balSong seongGong!")
        else:
            print(f"  balSong gyeolGwa: {send_result.get('error', 'unknown error')}")
    else:
        print("\n  KakaoTalk balSong geonNeoTtwim (--skip-send)")
    
    # 요약
    end_time = datetime.now()
    duration = (end_time - start_time).total_seconds()
    
    print("\n" + "=" * 60)
    print("  process wanRyo")
    print("=" * 60)
    print(f"soYo siGan: {duration:.1f}s")
    print(f"suJib: {len(all_items)}gae")
    print(f"seonByeol: {len(filtered_items)}gae")
    print(f"newsletter: {result['text_path']}")
    print(f"archive: {result['archive_path']}")


def main():
    parser = argparse.ArgumentParser(description="캠핑장 뉴스레터 자동화")
    parser.add_argument(
        "--test-mode",
        action="store_true",
        help="테스트 모드로 실행 (나에게만 발송)"
    )
    parser.add_argument(
        "--skip-send",
        action="store_true",
        help="카카오톡 발송 건너뛰기"
    )
    parser.add_argument(
        "--collect-only",
        action="store_true",
        help="콘텐츠 수집만 실행 (필터링 및 발송 제외)"
    )
    
    args = parser.parse_args()
    
    if args.collect_only:
        items = collect_all_content()
        print(f"\n{len(items)}개 항목 수집됨. 필터링 없이 종료합니다.")
    else:
        run_newsletter_pipeline(
            test_mode=args.test_mode or True,  # Default to test mode
            skip_send=args.skip_send
        )


if __name__ == "__main__":
    main()
