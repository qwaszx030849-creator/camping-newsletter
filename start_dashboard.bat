@echo off
chcp 65001 > nul
echo ============================================
echo  🏕️  캠핑장 뉴스레터 대시보드 시작
echo ============================================
echo.

echo [1/3] 최신 뉴스레터 동기화 중...
cd /d "c:\Users\PW1234\Desktop\업무\camping-newsletter"
git pull origin main
echo.

echo [2/3] 대시보드 서버 시작 중...
cd /d "c:\Users\PW1234\Desktop\업무\camping-newsletter\dashboard"
echo.

echo [3/3] 브라우저에서 http://localhost:3000 접속하세요!
echo.
echo 서버를 종료하려면 이 창에서 Ctrl+C를 누르세요.
echo ============================================
npm run dev
