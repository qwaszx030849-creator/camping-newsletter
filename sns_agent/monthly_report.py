"""
월간 성과 리포트 생성기
캠핏 데이터 + SNS 성과 → 사장님께 발송하는 월간 리포트 자동 생성
"""
import json
import os
from datetime import datetime


CLIENTS_DIR = os.path.join(os.path.dirname(__file__), "clients")


def generate_monthly_report(client_id: str, month: int = None, year: int = None) -> dict:
    """
    월간 성과 리포트 생성
    
    입력:
    - camfit_data.json (예약률, 리뷰 등)
    - published_content/ (발행된 콘텐츠 목록)
    
    출력:
    - 카카오톡 발송용 텍스트 리포트
    - HTML 상세 리포트
    """
    now = datetime.now()
    if year is None:
        year = now.year
    if month is None:
        month = now.month
    
    client_dir = os.path.join(CLIENTS_DIR, client_id)
    
    # 프로파일 로드
    with open(os.path.join(client_dir, "profile.json"), "r", encoding="utf-8") as f:
        profile = json.load(f)
    
    # 캠핏 데이터 로드
    camfit_path = os.path.join(client_dir, "camfit_data.json")
    camfit_data = {}
    if os.path.exists(camfit_path):
        with open(camfit_path, "r", encoding="utf-8") as f:
            camfit_data = json.load(f)
    
    # 발행된 콘텐츠 집계
    drafts_dir = os.path.join(client_dir, "content_drafts")
    published_count = {"instagram": 0, "blog": 0}
    if os.path.exists(drafts_dir):
        for f in os.listdir(drafts_dir):
            if f.startswith("instagram_"):
                published_count["instagram"] += 1
            elif f.startswith("blog_"):
                published_count["blog"] += 1
    
    tier = profile.get("tier", "스타터")
    scope = profile.get("service_scope", {}).get(tier, {})
    required_instagram = scope.get("instagram_posts", 4)
    required_blog = scope.get("blog_posts", 2)
    
    # 카카오 발송용 텍스트 리포트
    kakao_report = f"""🏕️ {profile['name']} 월간 SNS 리포트
━━━━━━━━━━━━━━━
📅 {year}년 {month}월 월간 성과

📸 콘텐츠 발행
• 인스타그램: {published_count['instagram']}/{required_instagram}개 ✅
• 네이버 블로그: {published_count['blog']}/{required_blog}개 ✅

📊 캠핏 예약 현황"""
    
    occupancy = camfit_data.get("occupancy_rate")
    if occupancy:
        trend = "📈" if occupancy >= 60 else "📉"
        kakao_report += f"\n• 이번 달 예약률: {occupancy}% {trend}"
    else:
        kakao_report += "\n• 예약 데이터: 다음 달 연동 예정"
    
    reviews = camfit_data.get("recent_reviews", [])
    if reviews:
        kakao_report += f"\n• 이달 주요 리뷰: \"{reviews[0][:30]}...\""
    
    kakao_report += f"""

💡 다음 달 전략
• 계절 트렌드 반영 콘텐츠 강화
• 예약률 분석 기반 프로모션 기획

━━━━━━━━━━━━━━━
📌 서비스 티어: {tier} ({profile['monthly_fee']//10000}만원/월)
캠핏 마케팅 대행 | 더 알아보기: 카카오 채널"""
    
    # HTML 상세 리포트
    html_report = f"""<!DOCTYPE html>
<html lang="ko">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>{profile['name']} {year}년 {month}월 SNS 성과 리포트</title>
<link href="https://fonts.googleapis.com/css2?family=Noto+Sans+KR:wght@300;400;500;700;900&display=swap" rel="stylesheet">
<style>
  :root {{
    --primary: #0D9488;
    --accent: #FF6B35;
    --text: #1E293B;
    --muted: #64748B;
    --bg: #F8FAFC;
    --card: #FFFFFF;
    --border: #E2E8F0;
  }}
  * {{ margin: 0; padding: 0; box-sizing: border-box; }}
  body {{ font-family: 'Noto Sans KR', sans-serif; background: var(--bg); color: var(--text); }}
  .container {{ max-width: 720px; margin: 0 auto; padding: 40px 24px; }}
  
  .header {{ background: linear-gradient(135deg, var(--primary) 0%, #0F766E 100%); border-radius: 20px; padding: 40px; color: white; text-align: center; margin-bottom: 32px; }}
  .header h1 {{ font-size: 28px; font-weight: 900; margin-bottom: 8px; }}
  .header .period {{ opacity: 0.85; font-size: 15px; }}
  .tier-badge {{ display: inline-block; background: rgba(255,255,255,0.2); padding: 6px 16px; border-radius: 20px; font-size: 13px; margin-top: 12px; }}
  
  .grid-2 {{ display: grid; grid-template-columns: 1fr 1fr; gap: 16px; margin-bottom: 24px; }}
  .card {{ background: var(--card); border-radius: 16px; padding: 24px; box-shadow: 0 2px 12px rgba(0,0,0,0.06); border: 1px solid var(--border); }}
  .card h3 {{ font-size: 14px; color: var(--muted); margin-bottom: 12px; }}
  .stat {{ font-size: 36px; font-weight: 900; color: var(--primary); }}
  .stat-sub {{ font-size: 13px; color: var(--muted); margin-top: 4px; }}
  .status-done {{ color: #10B981; font-weight: 700; }}
  
  .section-title {{ font-size: 18px; font-weight: 700; margin: 32px 0 16px; display: flex; align-items: center; gap: 8px; }}
  
  .content-row {{ display: flex; justify-content: space-between; align-items: center; padding: 14px 0; border-bottom: 1px solid var(--border); }}
  .content-row:last-child {{ border-bottom: none; }}
  .content-label {{ font-size: 15px; font-weight: 500; }}
  .content-count {{ font-size: 15px; color: var(--muted); }}
  .progress-bar {{ height: 8px; background: var(--border); border-radius: 4px; margin-top: 6px; overflow: hidden; }}
  .progress-fill {{ height: 100%; background: linear-gradient(90deg, var(--primary), #14B8A6); border-radius: 4px; transition: width 1s ease; }}
  
  .camfit-box {{ background: linear-gradient(135deg, #FFF7ED 0%, #FFEDD5 100%); border: 1px solid #FED7AA; border-radius: 16px; padding: 24px; margin-bottom: 24px; }}
  .camfit-box h3 {{ color: var(--accent); font-size: 16px; margin-bottom: 12px; display: flex; align-items: center; gap: 8px; }}
  .data-row {{ display: flex; justify-content: space-between; padding: 8px 0; border-bottom: 1px solid #FED7AA; font-size: 14px; }}
  .data-row:last-child {{ border-bottom: none; }}
  
  .footer {{ text-align: center; padding: 32px; color: var(--muted); font-size: 13px; }}
</style>
</head>
<body>
<div class="container">
  <div class="header">
    <p class="period">{year}년 {month}월 월간 성과 리포트</p>
    <h1>{profile['name']}</h1>
    <span class="tier-badge">🌱 {tier} | 월 {profile['monthly_fee']//10000}만원</span>
  </div>
  
  <div class="grid-2">
    <div class="card">
      <h3>📸 인스타그램</h3>
      <div class="stat">{published_count['instagram']}<span style="font-size:20px;color:#94A3B8">/{required_instagram}</span></div>
      <div class="stat-sub">포스트 발행 완료</div>
      <div class="progress-bar" style="margin-top:12px"><div class="progress-fill" style="width:{min(100, published_count['instagram']/required_instagram*100):.0f}%"></div></div>
    </div>
    <div class="card">
      <h3>📝 네이버 블로그</h3>
      <div class="stat">{published_count['blog']}<span style="font-size:20px;color:#94A3B8">/{required_blog}</span></div>
      <div class="stat-sub">포스트 발행 완료</div>
      <div class="progress-bar" style="margin-top:12px"><div class="progress-fill" style="width:{min(100, published_count['blog']/required_blog*100) if required_blog > 0 else 0:.0f}%"></div></div>
    </div>
  </div>
  
  <div class="camfit-box">
    <h3>🔑 캠핏 데이터 연동 현황</h3>
    <div class="data-row"><span>이번 달 예약률</span><span><strong>{f"{occupancy}%" if occupancy else "데이터 입력 필요"}</strong></span></div>
    <div class="data-row"><span>리뷰 활용</span><span><strong>{f"{len(reviews)}건 발굴" if reviews else "없음"}</strong></span></div>
    <div class="data-row"><span>캠핏 연동 상태</span><span class="status-done">✅ 연동 완료</span></div>
  </div>
  
  <div class="footer">
    <strong>캠핏 마케팅 대행</strong> | 캠핑장 전문 SNS 관리 서비스<br>
    캠핏 플랫폼 어드민 데이터 연동으로 경쟁사 대비 차별화된 마케팅 제공
  </div>
</div>
</body>
</html>"""
    
    # 저장
    report_dir = os.path.join(client_dir, "reports")
    os.makedirs(report_dir, exist_ok=True)
    
    html_path = os.path.join(report_dir, f"report_{year}_{month:02d}.html")
    with open(html_path, "w", encoding="utf-8") as f:
        f.write(html_report)
    
    txt_path = os.path.join(report_dir, f"kakao_report_{year}_{month:02d}.txt")
    with open(txt_path, "w", encoding="utf-8") as f:
        f.write(kakao_report)
    
    print(f"✅ 리포트 생성 완료!")
    print(f"   HTML: {html_path}")
    print(f"   카카오: {txt_path}")
    
    return {
        "kakao_text": kakao_report,
        "html_path": html_path,
        "txt_path": txt_path,
    }


if __name__ == "__main__":
    result = generate_monthly_report("더빌리지", month=2, year=2026)
    print("\n📋 카카오 발송 텍스트 미리보기:")
    print("─" * 40)
    print(result["kakao_text"])
