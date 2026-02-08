"""
카카오 Access Token 발급 스크립트

이 스크립트를 실행하면 브라우저에서 카카오 로그인 후 
Access Token을 발급받을 수 있습니다.
"""
import webbrowser
import http.server
import socketserver
import urllib.parse as urlparse

# 카카오 앱 설정
REST_API_KEY = "2a2ac573f1229ba1cc0dc6c9374fb65c"
REDIRECT_URI = "http://localhost:3000"

# 1단계: 인가 코드 받기 URL
auth_url = f"https://kauth.kakao.com/oauth/authorize?client_id={REST_API_KEY}&redirect_uri={REDIRECT_URI}&response_type=code&scope=talk_message"

print("=" * 50)
print("🔐 카카오 Access Token 발급")
print("=" * 50)
print()
print("1. 브라우저가 열립니다. 카카오 로그인해주세요.")
print("2. 로그인 후 동의하면 이 창에 'code=' 가 포함된 URL이 표시됩니다.")
print("3. 해당 코드를 복사해서 아래에 입력해주세요.")
print()

# 브라우저 열기
webbrowser.open(auth_url)

print(f"브라우저가 자동으로 열리지 않으면 아래 URL을 직접 방문하세요:")
print(auth_url)
print()

# 사용자에게 코드 입력 받기
auth_code = input("리다이렉트된 URL에서 'code=' 뒤의 값을 입력하세요: ").strip()

if auth_code:
    print()
    print("=" * 50)
    print("2단계: Access Token 발급 중...")
    print("=" * 50)
    
    import requests
    
    token_url = "https://kauth.kakao.com/oauth/token"
    data = {
        "grant_type": "authorization_code",
        "client_id": REST_API_KEY,
        "redirect_uri": REDIRECT_URI,
        "code": auth_code
    }
    
    response = requests.post(token_url, data=data)
    
    if response.status_code == 200:
        tokens = response.json()
        access_token = tokens.get("access_token")
        refresh_token = tokens.get("refresh_token")
        
        print()
        print("✅ 토큰 발급 성공!")
        print()
        print("=" * 50)
        print("📌 아래 값들을 안전하게 저장하세요:")
        print("=" * 50)
        print()
        print(f"ACCESS_TOKEN: {access_token}")
        print()
        print(f"REFRESH_TOKEN: {refresh_token}")
        print()
        print("=" * 50)
        print()
        print("이 Access Token을 .env 파일의 KAKAO_API_KEY에 넣으세요.")
        print("그리고 GitHub Secrets에도 KAKAO_ACCESS_TOKEN으로 추가하세요.")
        
        # .env 파일 업데이트
        update = input("\n.env 파일에 자동으로 저장할까요? (y/n): ").strip().lower()
        if update == 'y':
            with open('.env', 'r', encoding='utf-8') as f:
                content = f.read()
            
            if 'KAKAO_API_KEY=' in content:
                import re
                content = re.sub(r'KAKAO_API_KEY=.*', f'KAKAO_API_KEY={access_token}', content)
            else:
                content += f"\nKAKAO_API_KEY={access_token}\n"
            
            if 'KAKAO_REFRESH_TOKEN=' not in content:
                content += f"KAKAO_REFRESH_TOKEN={refresh_token}\n"
            else:
                content = re.sub(r'KAKAO_REFRESH_TOKEN=.*', f'KAKAO_REFRESH_TOKEN={refresh_token}', content)
            
            with open('.env', 'w', encoding='utf-8') as f:
                f.write(content)
            
            print("✅ .env 파일 업데이트 완료!")
    else:
        print(f"❌ 토큰 발급 실패: {response.text}")
else:
    print("코드가 입력되지 않았습니다.")
