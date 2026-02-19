# 캠핑장 뉴스레터 자동화 시스템

캠핑장 사장님들을 위한 주간 뉴스레터 자동화 시스템

## 설치 (Setup)

```bash
pip install -r requirements.txt
```

## 설정 (Configuration)

API 키를 포함한 `.env` 파일을 생성하세요:

```env
GEMINI_API_KEY=your_gemini_api_key
NAVER_CLIENT_ID=your_naver_client_id
NAVER_CLIENT_SECRET=your_naver_client_secret
KAKAO_API_KEY=your_kakao_api_key
```

## 사용법 (Usage)

```bash
python main.py
```

## 프로젝트 구조 (Project Structure)

```
camping-newsletter/
├── collectors/           # 콘텐츠 수집 모듈
├── ai_filter.py          # AI 필터링
├── newsletter_generator.py # 뉴스레터 생성
├── kakao_sender.py       # 카카오톡 발송
├── main.py               # 메인 실행 스크립트
├── config.py             # 설정
└── dashboard/            # Next.js 대시보드
```
