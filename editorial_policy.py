"""Editorial rules shared by collection, selection and review."""
import re
from difflib import SequenceMatcher
from html import unescape
from urllib.parse import parse_qs, urlparse, urlunparse

TARGET_ITEMS = 10
TARGET_CANDIDATES = 30

REVIEW_QUERIES = [
    "캠핑장 재방문 후기", "캠핑장 또 가고 싶은",
    "캠핑장 화장실 깨끗 후기", "캠핑장 개별 샤워실 후기",
    "캠핑장 개수대 온수 후기", "캠핑장 사이트 간격 후기",
    "캠핑장 매너타임 관리 후기", "캠핑장 사장님 응대 후기",
    "캠핑장 아이 체험 후기", "캠핑장 영화 상영 후기",
    "캠핑장 보물찾기 후기", "캠핑장 만들기 체험 후기",
    "캠핑장 반려견 울타리 후기", "캠핑장 개별 화장실 후기",
    "캠핑장 우천 실내 놀이 후기", "캠핑장 그늘 사이트 후기",
    "캠지기 청소 관리", "캠지기 시설 보수", "캠핑장 분리수거 운영",
    "캠핑장 장박 운영 후기", "캠핑장 평일 재방문",
    "캠핑장 매점 운영 후기", "캠핑장 체크인 안내 후기",
]
SEASON_QUERIES = {
    "spring": ["캠핑장 봄 체험 후기", "캠핑장 어린이날 행사 후기"],
    "summer": ["캠핑장 수영장 관리 후기", "캠핑장 물놀이 체험 후기", "캠핑장 우천 동선 후기"],
    "autumn": ["캠핑장 할로윈 후기", "캠핑장 추석 체험", "캠핑장 가을 이벤트 후기", "캠핑장 밤 줍기 후기"],
    "winter": ["캠핑장 겨울 온수 후기", "캠핑장 동파 관리", "캠핑장 크리스마스 체험 후기"],
}


def review_queries(month):
    season = "spring" if month in (3, 4, 5) else "summer" if month in (6, 7, 8) else "autumn" if month in (9, 10, 11) else "winter"
    return REVIEW_QUERIES + SEASON_QUERIES[season]


def canonical_url(url):
    parsed = urlparse(url)
    host = parsed.netloc.lower().removeprefix("m.")
    query = parse_qs(parsed.query)
    if host == "blog.naver.com" and query.get("blogId") and query.get("logNo"):
        return "https://blog.naver.com/" + query["blogId"][0] + "/" + query["logNo"][0]
    return urlunparse(("https", host, parsed.path.rstrip("/"), "", parsed.query, ""))


def publisher_key(item):
    parsed = urlparse(canonical_url(item.url))
    parts = parsed.path.strip("/").split("/")
    if parsed.netloc in ("blog.naver.com", "cafe.naver.com"):
        return parsed.netloc + "/" + parts[0]
    return parsed.netloc


def same_article(item, other):
    if canonical_url(item.url) == canonical_url(other.url):
        return True
    def clean(title):
        return re.sub(r"[^가-힣a-z0-9]", "", unescape(title).lower())
    left, right = clean(item.title), clean(other.title)
    # Shared amenities do not make two different campground reviews duplicates.
    return min(len(left), len(right)) >= 12 and SequenceMatcher(None, left, right).ratio() >= 0.90


def evidence_summary(item):
    """Keep source evidence and editorial suggestions explicitly separate."""
    excerpt = " ".join(unescape(item.description or "").split()).strip()
    excerpt = excerpt[:320]
    text = item.title + " " + excerpt
    hints = [
        (("할로윈", "보물찾기", "영화", "체험", "프로그램", "슬리퍼"), "참여 연령, 진행 시간, 담당 인력과 우천 대안을 정리해 소규모 체험부터 시험해 볼 수 있습니다."),
        (("매너타임", "소음", "조용"), "예약 전 안내와 현장 순찰 기준이 일치하는지 확인하고 조용한 구역과 활동 구역의 배치를 검토할 수 있습니다."),
        (("화장실", "샤워", "개수대", "청결", "깨끗", "청소"), "혼잡 시간대 청소 주기와 온수·소모품 점검 항목을 나누어 관리할 수 있습니다."),
        (("반려견", "애견", "울타리"), "울타리 틈, 출입 동선과 비동반 고객 구역을 점검해 반려견 동반 운영 기준을 구체화할 수 있습니다."),
        (("수영장", "물놀이", "온수풀"), "운영 시간, 정비 시간과 보호자 동반 기준을 예약 안내에 함께 제시할 수 있습니다."),
        (("잔디", "사이트", "간격", "동선"), "텐트 설치 후 통행 공간과 이웃 사이트 간섭을 점검하고 구역별 특성을 예약 사진에 반영할 수 있습니다."),
        (("응대", "친절", "재방문"), "고객이 만족한 접점을 체크인·체류 중·퇴실로 나눠 직원 응대 기준에 반영할 수 있습니다."),
        (("조명", "보수", "정비", "분리수거"), "반복 작업의 주기와 소요 시간을 기록하고 자체 점검과 전문 작업의 경계를 정리할 수 있습니다."),
        (("장박", "평일", "비수기"), "운영 기간별 관리 부담과 포함 서비스를 구분해 장기 이용 조건을 검토할 수 있습니다."),
    ]
    suggestion = next((hint for words, hint in hints if any(word in text for word in words)), "원문에서 확인되는 운영 방식과 고객 반응을 구분해 내 캠핑장에 적용할 조건을 검토할 수 있습니다.")
    return f"확인된 자료 발췌: {excerpt}\n운영 적용 제안: {suggestion}"
