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
from collectors.google_news import GoogleNewsCollector
from collectors.blog_collector import NaverBlogCollector
from collectors.naver_news import NaverNewsCollector
from collectors.cafe_collector import NaverCafeCollector
from collectors.government_support import GovernmentSupportCollector
from collectors.kin_collector import NaverKinCollector
from ai_filter import filter_content, prepare_replacement_candidates
from newsletter_generator import save_newsletter, get_week_info
from kakao_sender import send_newsletter


def _load_previous_urls() -> Set[str]:
    """이전 뉴스레터에서 사용된 URL 목록을 로드하여 중복 방지"""
    used_urls = set()
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
        blog_keywords = [
            "캠핑장 운영 매출 노하우",
            "오토캠핑장 운영 성공 사례",
            "캠핑장 사장님 예약률 높이는 방법",
            "캠핑장 리뷰 관리 네이버플레이스",
            "캠핑장 재방문 후기 청결 친절",
            "캠핑장 수영장 후기 아이 체험",
            "캠핑장 시설 개선 사이트 조성",
            "캠핑장 비수기 운영 전략",
            "오토캠핑장 성수기 준비",
            "캠핑장 사이트 데크 조성",
        ]
        if datetime.now().month in (6, 7, 8, 9):
            blog_keywords.extend([
                "캠핑장 여름 운영 수영장 후기",
                "캠핑장 가을 성수기 예약 전략",
                "캠핑장 우천 환불 운영 사례",
            ])
        blog_items = NaverBlogCollector().collect(blog_keywords)
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
            "캠핑장 예약 플랫폼 시장",
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
            "캠핑장 예약 플랫폼 시장",
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
        cafe_keywords = [
            "캠핑장 운영 노하우 캠지기",
            "오토캠핑장 사장님 운영 팁",
            "캠핑장 예약 관리 성수기",
            "캠핑장 사이트 관리 정비",
            "캠핑장 재방문 후기 친절 청결",
            "캠핑장 수영장 후기 아이 체험",
            "캠핑장 환불 응대 후기",
            "캠지기 평일 운영 일상",
        ]
        cafe_items = NaverCafeCollector().collect(cafe_keywords)
        all_items.extend(cafe_items)
        print(f"   -> {len(cafe_items)}개 수집")
    except Exception as e:
        print(f"   Error: {e}")

    # ========================================
    # 5. 정부 지원사업 - 보조금/공모
    # ========================================
    print("\n[5/6] 정부 지원사업 수집...")
    try:
        gov_items = GovernmentSupportCollector().collect()[:2]
        all_items.extend(gov_items)
        print(f"   -> {len(gov_items)}개 수집 (전국 공통 참고용만 제한 반영)")
    except Exception as e:
        print(f"   Error: {e}")

    # ========================================
    # 6. 지식iN - 운영자 Q&A
    # ========================================
    print("\n[6/6] 지식iN 수집...")
    try:
        kin_keywords = [
            "캠핑장 운영 방법 허가",
            "오토캠핑장 인허가 절차",
            "캠핑장 매출 수익",
            "야영장 등록 신고",
        ]
        kin_items = NaverKinCollector().collect(kin_keywords)
        all_items.extend(kin_items)
        print(f"   -> {len(kin_items)}개 수집")
    except Exception as e:
        print(f"   Error: {e}")

    # 후처리
    unique_items = _remove_duplicate_bloggers(all_items)
    used_urls = _load_previous_urls()
    fresh_items = _remove_previously_used(unique_items, used_urls)

    print(f"\n📊 수집 완료: {len(all_items)}개 → 중복 제거 {len(unique_items)}개 → 최종 {len(fresh_items)}개")
    return fresh_items


def run_newsletter_pipeline(test_mode: bool = True, skip_send: bool = False):
    """뉴스레터 파이프라인 실행"""
    start_time = datetime.now()
    print("\n" + "=" * 60)
    print("  캠핑장 뉴스레터 자동화 시스템")
    print("=" * 60)
    print(f"시작 시간: {start_time.strftime('%Y-%m-%d %H:%M:%S')}")

    # 1단계: 콘텐츠 수집
    all_items = collect_all_content()

    if not all_items:
        print("\n  수집된 콘텐츠 없음. 종료.")
        return

    # 2단계: AI 필터링 + 요약
    print("\n" + "=" * 50)
    print("  AI 필터링 + 요약 생성...")
    print("=" * 50)

    filtered_items = filter_content(all_items)
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
    parser.add_argument("--collect-only", action="store_true", help="콘텐츠 수집만 실행")

    args = parser.parse_args()

    if args.collect_only:
        items = collect_all_content()
        print(f"\n{len(items)}개 항목 수집됨.")
    else:
        run_newsletter_pipeline(
            test_mode=args.test_mode or True,
            skip_send=args.skip_send
        )


if __name__ == "__main__":
    main()
