"""
SNS 마케팅 대행 서비스 - 메인 실행 스크립트
사용법:
  python sns_main.py --client 더빌리지 --action generate    # 이번 달 콘텐츠 생성
  python sns_main.py --client 더빌리지 --action calendar    # 다음 달 캘린더 생성
  python sns_main.py --client 더빌리지 --action report      # 월간 리포트 생성
  python sns_main.py --action list                           # 클라이언트 목록
"""
import argparse
import json
import os
import sys

# 현재 디렉토리를 Python 경로에 추가
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from sns_agent.content_generator import (
    load_profile, get_camfit_data,
    generate_instagram_caption, generate_blog_draft,
    generate_monthly_calendar
)
from sns_agent.monthly_report import generate_monthly_report

CLIENTS_DIR = os.path.join(os.path.dirname(__file__), "sns_agent", "clients")


def list_clients():
    """등록된 클라이언트 목록 출력"""
    print("\n📋 등록된 클라이언트 목록")
    print("─" * 50)
    
    if not os.path.exists(CLIENTS_DIR):
        print("  (등록된 클라이언트 없음)")
        return
    
    for client_id in os.listdir(CLIENTS_DIR):
        profile_path = os.path.join(CLIENTS_DIR, client_id, "profile.json")
        if os.path.exists(profile_path):
            with open(profile_path, "r", encoding="utf-8") as f:
                p = json.load(f)
            fee = p.get('monthly_fee', 0) // 10000
            vat = p.get('vat_fee', 0) // 10000
            print(f"  🏕️  {p['name']} | {p.get('tier','?')} | {fee}만원 (VAT {vat}만원)")


def run_generate(client_id: str):
    """이달 SNS 콘텐츠 초안 생성"""
    print(f"\n🚀 [{client_id}] 콘텐츠 생성 시작...")
    
    profile = load_profile(client_id)
    camfit_data = get_camfit_data(client_id)
    
    tier = profile.get("tier", "스타터")
    scope = profile.get("service_scope", {}).get(tier, {})
    
    instagram_count = scope.get("instagram_posts", 4)
    blog_count = scope.get("blog_posts", 2)
    themes = profile.get("content_themes", {}).get("recurring", [])
    
    output_dir = os.path.join(CLIENTS_DIR, client_id, "content_drafts")
    os.makedirs(output_dir, exist_ok=True)
    
    from datetime import datetime
    now = datetime.now()
    
    # 인스타그램 캡션 생성
    print(f"\n📸 인스타그램 캡션 {instagram_count}개 생성 중...")
    for i in range(instagram_count):
        theme = themes[i % len(themes)] if themes else f"캠핑장 일상 #{i+1}"
        print(f"  [{i+1}/{instagram_count}] {theme}")
        try:
            result = generate_instagram_caption(profile, camfit_data, theme)
            filename = f"instagram_{now.strftime('%Y%m')}_{i+1:02d}.json"
            with open(os.path.join(output_dir, filename), "w", encoding="utf-8") as f:
                json.dump({**result, "theme": theme, "created_at": now.isoformat()}, f, ensure_ascii=False, indent=2)
            print(f"  ✅ 저장: {filename}")
        except Exception as e:
            print(f"  ❌ 실패: {e}")
    
    # 블로그 초안 생성
    print(f"\n📝 블로그 초안 {blog_count}개 생성 중...")
    blog_topics = [
        f"{profile['location'].get('region', '')} 캠핑장 추천 - {profile['name']} 솔직 후기",
        f"{profile['name']} 시설 완전 정복 - 알아두면 좋은 꿀팁"
    ]
    for i in range(blog_count):
        topic = blog_topics[i % len(blog_topics)]
        print(f"  [{i+1}/{blog_count}] {topic}")
        try:
            result = generate_blog_draft(profile, camfit_data, topic)
            filename = f"blog_{now.strftime('%Y%m')}_{i+1:02d}.json"
            with open(os.path.join(output_dir, filename), "w", encoding="utf-8") as f:
                json.dump({**result, "topic": topic, "created_at": now.isoformat()}, f, ensure_ascii=False, indent=2)
            print(f"  ✅ 저장: {filename}")
        except Exception as e:
            print(f"  ❌ 실패: {e}")
    
    print(f"\n✅ 콘텐츠 생성 완료! 저장 위치: {output_dir}")
    print(f"   → 각 파일을 검토 후 실제 채널에 발행하세요.")


def run_calendar(client_id: str):
    """다음 달 콘텐츠 캘린더 생성"""
    from datetime import datetime
    now = datetime.now()
    next_month = now.month + 1 if now.month < 12 else 1
    next_year = now.year if now.month < 12 else now.year + 1
    
    print(f"\n📅 [{client_id}] {next_year}년 {next_month}월 캘린더 생성 중...")
    
    profile = load_profile(client_id)
    camfit_data = get_camfit_data(client_id)
    
    calendar = generate_monthly_calendar(profile, camfit_data, year=next_year, month=next_month)
    
    # 저장
    cal_path = os.path.join(CLIENTS_DIR, client_id, f"calendar_{next_year}_{next_month:02d}.json")
    with open(cal_path, "w", encoding="utf-8") as f:
        json.dump(calendar, f, ensure_ascii=False, indent=2)
    
    print(f"\n✅ 캘린더 생성 완료! ({len(calendar)}개 콘텐츠)")
    print("─" * 55)
    for item in calendar:
        emoji = "📸" if item['platform'] == 'instagram' else "📝"
        priority = "🔴 [중요]" if item.get('priority') == 'high' else "   "
        print(f"  {priority} {emoji} {item['date']} | {item.get('theme', '')}")
    print(f"\n💾 저장: {cal_path}")


def run_report(client_id: str):
    """월간 성과 리포트 생성 + 카카오 발송 텍스트 출력"""
    from datetime import datetime
    now = datetime.now()
    
    print(f"\n📊 [{client_id}] {now.year}년 {now.month}월 성과 리포트 생성 중...")
    
    result = generate_monthly_report(client_id, month=now.month, year=now.year)
    
    print("\n─" * 50)
    print("📱 카카오 발송 텍스트 (복사해서 사용):")
    print("─" * 50)
    print(result["kakao_text"])
    print("─" * 50)
    print(f"\n🌐 HTML 상세 리포트: {result['html_path']}")


def main():
    parser = argparse.ArgumentParser(description="캠핏 SNS 마케팅 대행 서비스")
    parser.add_argument("--client", "-c", type=str, help="클라이언트 ID (예: 더빌리지)")
    parser.add_argument("--action", "-a", type=str, 
                        choices=["generate", "calendar", "report", "list"],
                        default="list", help="실행할 작업")
    
    args = parser.parse_args()
    
    print("=" * 55)
    print("🏕️  캠핏 SNS 마케팅 대행 서비스 v1.0")
    print("=" * 55)
    
    if args.action == "list":
        list_clients()
    elif args.action == "generate":
        if not args.client:
            print("❌ --client 옵션이 필요합니다.")
            sys.exit(1)
        run_generate(args.client)
    elif args.action == "calendar":
        if not args.client:
            print("❌ --client 옵션이 필요합니다.")
            sys.exit(1)
        run_calendar(args.client)
    elif args.action == "report":
        if not args.client:
            print("❌ --client 옵션이 필요합니다.")
            sys.exit(1)
        run_report(args.client)


if __name__ == "__main__":
    main()
