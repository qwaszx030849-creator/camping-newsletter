"""
Kakao Talk Sender
카카오톡 알림톡을 통해 뉴스레터를 발송합니다.

Note: 카카오 비즈메시지 API를 사용합니다.
https://developers.kakao.com/docs/latest/ko/message/common
"""
import requests
import json
from typing import List, Optional
from config import KAKAO_API_KEY


class KakaoSender:
    """
    카카오톡 메시지 발송 클래스
    
    사용하기 전에 다음이 필요합니다:
    1. 카카오 비즈니스 계정 
    2. 비즈메시지 API 키 발급
    3. 알림톡 템플릿 등록 및 승인
    """
    
    # 카카오 비즈메시지 API 엔드포인트
    API_URL = "https://kapi.kakao.com/v2/api/talk/memo/default/send"
    
    def __init__(self):
        self.api_key = KAKAO_API_KEY
        self.recipients: List[str] = []
        
    def load_recipients(self, filepath: str = "recipients.json") -> List[str]:
        """Load recipient phone numbers from file"""
        try:
            with open(filepath, 'r', encoding='utf-8') as f:
                data = json.load(f)
                self.recipients = data.get("recipients", [])
                return self.recipients
        except FileNotFoundError:
            print(f"Recipients file not found: {filepath}")
            return []
    
    def send_to_me(self, message: str) -> dict:
        """
        Send message to myself (for testing)
        Uses Kakao Talk API - requires OAuth token
        """
        if not self.api_key:
            return {
                "success": False,
                "error": "Kakao API key not configured",
                "message": "Please set KAKAO_API_KEY in .env file"
            }
        
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/x-www-form-urlencoded"
        }
        
        # Template object for text message
        template_object = {
            "object_type": "text",
            "text": message[:1000],  # Kakao has 1000 char limit
            "link": {
                "web_url": "https://camping-newsletter.vercel.app",
                "mobile_web_url": "https://camping-newsletter.vercel.app"
            },
            "button_title": "뉴스레터 모아보기"
        }
        
        data = {
            "template_object": json.dumps(template_object)
        }
        
        try:
            response = requests.post(self.API_URL, headers=headers, data=data)
            
            if response.status_code == 200:
                return {"success": True, "response": response.json()}
            else:
                return {
                    "success": False,
                    "error": f"API Error: {response.status_code}",
                    "response": response.text
                }
        except Exception as e:
            return {"success": False, "error": str(e)}
    
    def send_alimtalk(self, message: str, recipients: Optional[List[str]] = None) -> dict:
        """
        Send Alimtalk (비즈메시지) to multiple recipients
        
        Note: This requires:
        1. Registered business channel
        2. Approved message template
        3. Valid recipient phone numbers
        """
        # TODO: Implement when Kakao Business API is set up
        # This is a placeholder for the actual implementation
        
        return {
            "success": False,
            "error": "Alimtalk not yet configured",
            "message": "Please set up Kakao Business API first. See docs: https://business.kakao.com"
        }


def send_newsletter(message: str, test_mode: bool = True) -> dict:
    """
    Convenience function to send newsletter
    
    Args:
        message: Newsletter text content
        test_mode: If True, only sends to self for testing
        
    Returns:
        Send result dictionary
    """
    sender = KakaoSender()
    
    if test_mode:
        print("Sending newsletter in TEST MODE (to self only)")
        return sender.send_to_me(message)
    else:
        print("Sending newsletter to all recipients")
        return sender.send_alimtalk(message)


# Guide for setting up Kakao API
SETUP_GUIDE = """
============================================
카카오톡 알림톡 설정 가이드
============================================

1. 카카오 개발자 계정 생성
   https://developers.kakao.com

2. 애플리케이션 생성
   - 내 애플리케이션 > 애플리케이션 추가
   
3. 카카오 로그인 설정
   - 제품 설정 > 카카오 로그인 > 활성화
   - Redirect URI 설정

4. 동의 항목 설정
   - 카카오톡 메시지 전송 동의

5. 토큰 발급
   - REST API 키 또는 Access Token 획득

6. (비즈니스용) 카카오 비즈니스 등록
   https://business.kakao.com
   - 채널 생성
   - 알림톡 템플릿 등록

============================================
"""

if __name__ == "__main__":
    print(SETUP_GUIDE)
    
    # Test send
    test_message = """🏕️ 캠핑장 운영 뉴스레터
2026년 2월 2주차

테스트 메시지입니다.
"""
    
    result = send_newsletter(test_message, test_mode=True)
    print(f"Send result: {result}")
