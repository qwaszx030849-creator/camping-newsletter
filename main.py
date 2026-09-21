"""
Camping Newsletter Automation - Main Script
캠핑장 뉴스레터 자동화 메인 실행 스크립트
"""
import argparse
import json
import os
import glob
from datetime import datetime
from editorial_policy import TARGET_ITEMS, TARGET_CANDIDATES, review_queries, same_article, canonical_url
from typing import List, Set, Tuple

from collectors.base import ContentItem
from collectors.google_news import GoogleNewsCollector
from collectors.blog_collector import NaverBlogCollector
from collectors.naver_news import NaverNewsCollector
from collectors.cafe_collector import NaverCafeCollector
from collectors.government_support import GovernmentSupportCollector
from collectors.kin_collector import NaverKinCollector
from ai_filter import filter_content, prepare_replacement_candidates, _extract_keywords
from newsletter_generator import save_newsletter, get_week_info
from kakao_sender import send_newsletter


def _load_previous_items() -> Tuple[Set[str], List[ContentItem]]:
    """이전 뉴스레터에서 사용된 URL과 주제 키워드를 로드하여 반복 소재를 방지."""
    used_urls: Set[str] = set()
    previous_items: List[ContentItem] = []
    archive_dir = os.path.join(os.path.dirname(__file__), "archive")
    current_week = get_week_info()
    current_filename = (
        f"newsletter_{current_week['year']}_{current_week['month']:02d}_"
        f"week{current_week['week_of_month']}.json"
    )

    for json_file in glob.glob(os.path.join(archive_dir, "**", "*.json"), recursive=True):
        if os.path.basename(json_file) == current_filename:
            continue
        try:
            with open(json_file, "r", encoding="utf-8") as f:
                data = json.load(f)
                for section_name in ("items", "review_candidates"):
                    for item in data.get(section_name, []):
                        url = item.get("url", "")
                        if url:
                            used_urls.add(canonical_url(url))
                        previous_items.append(
                            ContentItem(
                                title=item.get("title", ""),
                                url=url,
                                source=item.get("source", ""),
                                description=item.get("description") or item.get("summary", ""),
                                summary=item.get("summary", ""),
                                category=item.get("category", ""),
                            )
                        )
        except (json.JSONDecodeError, Exception):
            continue

    print(f"📋 이전 뉴스레터에서 {len(used_urls)}개 URL, {len(previous_items)}개 주제 중복 방지 목록 로드")
    return used_urls, previous_items


def _topic_keywords(title: str) -> Set[str]:
    """과거 발행 반복 판정용 제목 키워드. 일반 후기어는 제외해 다른 캠핑장 후기는 살린다."""
    generic_words = {
        "캠핑장", "캠핑", "글램핑", "오토캠핑", "야영장", "후기", "안내",
        "운영", "사례", "리뷰", "추천", "좋은", "아이와", "가족", "이번",
    }
    return {word for word in _extract_keywords(title) if word not in generic_words and len(word) >= 3}


def _is_previously_used_topic(item: ContentItem, previous_items: List[ContentItem]) -> bool:
    """URL이 달라도 과거 발행과 제목 주제가 거의 같으면 제외."""
    return any(same_article(item, previous) for previous in previous_items)



def _remove_previously_used(items: List[ContentItem], used_urls: Set[str], previous_items: List[ContentItem]) -> List[ContentItem]:
    """이전 뉴스레터에 이미 사용된 URL 또는 반복 주제 제거."""
    new_items = []
    removed_url = 0
    removed_topic = 0
    for item in items:
        if canonical_url(item.url) in used_urls:
            removed_url += 1
            continue
        if _is_previously_used_topic(item, previous_items):
            removed_topic += 1
            continue
        new_items.append(item)
    if removed_url or removed_topic:
        print(f"   🔄 이전 뉴스레터 중복 URL {removed_url}개, 반복 주제 {removed_topic}개 제거")
    return new_items


def _remove_duplicate_bloggers(items: List[ContentItem]) -> List[ContentItem]:
    """같은 블로거의 글은 1개만 유지"""
    seen_bloggers = set()
    unique = []
    for item in items:
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


def collect_all_content() -> List[ContentItem]:
    """
    캠핑장 운영자를 위한 콘텐츠 수집

    수집 소스:
    1. 네이버 블로그 - 운영 노하우, 매출 사례, 마케팅
    2. 네이버 뉴스 - 캠핑 산업 동향, 정책
    3. 구글 뉴스 RSS - 캠핑 산업 트렌드
    """
    print("=" * 50)
    print("  캠핑장 뉴스레터 콘텐츠 수집")
    print("=" * 50)

    all_items = []

    # ========================================
    # 1. 네이버 블로그 - 캠핑장 운영 실전
    # ========================================
    print("\n[1/6] 네이버 블로그 수집...")
    try:
        blog_keywords = review_queries(datetime.now().month)
        blog_items = NaverBlogCollector().collect(blog_keywords, max_items_per_keyword=20)
        all_items.extend(blog_items)
        print(f"   -> {len(blog_items)}개 수집")
    except Exception as e:
        print(f"   Error: {e}")

    # ========================================
    # 2. 네이버 뉴스 - 캠핑 산업 동향
    # ========================================
    print("\n[2/6] 네이버 뉴스 수집...")
    try:
        news_keywords = [
            "캠핑 산업 동향 시장",
            "캠핑장 재방문 만족도 조사",
            "캠핑장 이용객 만족도 리뷰",
            "숙박업 데이터 마케팅 리뷰 관리",
            "오토캠핑장 운영 트렌드",
        ]
        if datetime.now().month in (6, 7, 8, 9):
            news_keywords.extend([
                "캠핑장 성수기 운영 트렌드",
                "야영장 환불 예약 취소 분쟁",
            ])
        news_items = NaverNewsCollector().collect(news_keywords)
        all_items.extend(news_items)
        print(f"   -> {len(news_items)}개 수집")
    except Exception as e:
        print(f"   Error: {e}")

    # ========================================
    # 3. 구글 뉴스 RSS - 캠핑 트렌드
    # ========================================
    print("\n[3/6] 구글 뉴스 수집...")
    try:
        google_keywords = [
            "캠핑장 산업 동향 2026",
            "오토캠핑장 운영 트렌드",
            "캠핑장 이용객 설문 통계",
            "캠핑장 고객 리뷰 만족도",
            "숙박업 데이터 기반 마케팅",
        ]
        google_items = GoogleNewsCollector().collect(google_keywords)
        all_items.extend(google_items)
        print(f"   -> {len(google_items)}개 수집")
    except Exception as e:
        print(f"   Error: {e}")

    # ========================================
    # 4. 네이버 카페 - 캠핑 커뮤니티
    # ========================================
    print("\n[4/6] 네이버 카페 수집...")
    try:
        cafe_keywords = review_queries(datetime.now().month)
        cafe_items = NaverCafeCollector().collect(cafe_keywords, max_items_per_keyword=50)
        all_items.extend(cafe_items)
        print(f"   -> {len(cafe_items)}개 수집")
    except Exception as e:
        print(f"   Error: {e}")

    # 후처리
    unique_items = list({canonical_url(item.url): item for item in all_items if item.url}.values())
    used_urls, previous_items = _load_previous_items()
    fresh_items = _remove_previously_used(unique_items, used_urls, previous_items)

    print(f"\n📊 수집 완료: {len(all_items)}개 → 중복 제거 {len(unique_items)}개 → 최종 {len(fresh_items)}개")
    return fresh_items


def run_newsletter_pipeline(test_mode: bool = True, skip_send: bool = False, force: bool = False):
    """뉴스레터 파이프라인 실행"""
    start_time = datetime.now()
    print("\n" + "=" * 60)
    print("  캠핑장 뉴스레터 자동화 시스템")
    print("=" * 60)
    print(f"시작 시간: {start_time.strftime('%Y-%m-%d %H:%M:%S')}")

    week_info = get_week_info()
    current_path = os.path.join(os.path.dirname(__file__), "output",
        f"newsletter_{week_info['year']}_{week_info['month']:02d}_week{week_info['week_of_month']}.json")
    if os.path.exists(current_path) and not force:
        with open(current_path, encoding="utf-8") as handle:
            existing = json.load(handle)
        if existing.get("review_status") in ("reviewed", "approved", "published") or (
            len(existing.get("items", [])) == TARGET_ITEMS
            and len(existing.get("review_candidates", [])) >= TARGET_CANDIDATES
            and existing.get("quality", {}).get("editorial_version") == 2
        ):
            print("Existing reviewed/complete edition preserved; use --force to regenerate.")
            return

    # 1단계: 콘텐츠 수집
    all_items = collect_all_content()

    if not all_items:
        print("\n  수집된 콘텐츠 없음. 종료.")
        return

    # 2단계: AI 필터링 + 요약
    print("\n" + "=" * 50)
    print("  AI 필터링 + 요약 생성...")
    print("=" * 50)

    filtered_items = filter_content(all_items, count=TARGET_ITEMS)
    replacement_candidates = prepare_replacement_candidates(all_items, filtered_items)
    print(f"총 {len(all_items)}개 중 {len(filtered_items)}개 선별")

    # 3단계: 뉴스레터 생성
    print("\n" + "=" * 50)
    print("  뉴스레터 생성...")
    print("=" * 50)

    week_info = get_week_info()
    result = save_newsletter(filtered_items, week_info, replacement_candidates)

    print("\n  뉴스레터 미리보기:")
    print("-" * 40)
    print(result["text_content"][:800] + "...")

    # 4단계: 카카오톡 발송
    if not skip_send:
        print("\n" + "=" * 50)
        print("  카카오톡 발송...")
        print("=" * 50)

        send_result = send_newsletter(result["text_content"], test_mode=test_mode)

        if send_result.get("success"):
            print("  뉴스레터 발송 성공!")
        else:
            print(f"  발송 결과: {send_result.get('error', 'unknown error')}")
    else:
        print("\n  카카오톡 발송 건너뜀 (--skip-send)")

    # 요약
    end_time = datetime.now()
    duration = (end_time - start_time).total_seconds()

    print("\n" + "=" * 60)
    print("  프로세스 완료")
    print("=" * 60)
    print(f"소요 시간: {duration:.1f}s")
    print(f"수집: {len(all_items)}개")
    print(f"선별: {len(filtered_items)}개")
    print(f"뉴스레터: {result['text_path']}")
    print(f"아카이브: {result['archive_path']}")


def main():
    parser = argparse.ArgumentParser(description="캠핑장 뉴스레터 자동화")
    parser.add_argument("--test-mode", action="store_true", help="테스트 모드 (나에게만 발송)")
    parser.add_argument("--skip-send", action="store_true", help="카카오톡 발송 건너뛰기")
    parser.add_argument("--force", action="store_true", help="Regenerate the current edition explicitly")
    parser.add_argument("--collect-only", action="store_true", help="콘텐츠 수집만 실행")

    args = parser.parse_args()

    if args.collect_only:
        items = collect_all_content()
        print(f"\n{len(items)}개 항목 수집됨.")
    else:
        run_newsletter_pipeline(
            test_mode=args.test_mode or True,
            skip_send=args.skip_send,
            force=args.force
        )


if __name__ == "__main__":
    main()
