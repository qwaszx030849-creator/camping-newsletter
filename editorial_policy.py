"""Editorial rules shared by collection, selection and review."""
import json
import re
import calendar
from datetime import date, datetime, timedelta, timezone
from difflib import SequenceMatcher
from html import unescape
from urllib.parse import parse_qs, urlparse, urlunparse

TARGET_ITEMS = 10
TARGET_CANDIDATES = 30
MAX_ARTICLE_AGE_MONTHS = 3
INSIGHT_TAGS = ("운영", "시설", "이벤트", "고객경험", "안전/리스크", "시즌")

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


def insight_tags(item):
    """Infer safe fallback tags from the observed title and source excerpt."""
    text = f"{getattr(item, 'title', '')} {getattr(item, 'description', '')}".lower()
    rules = (
        ("이벤트", ("할로윈", "보물찾기", "체험", "프로그램", "영화", "행사", "만들기")),
        ("시설", ("화장실", "샤워", "개수대", "수영장", "사이트", "그늘", "온수", "매점")),
        ("고객경험", ("후기", "재방문", "친절", "응대", "좋았", "만족", "불편")),
        ("안전/리스크", ("환불", "예약취소", "오버부킹", "위생", "단속", "사고", "매너타임")),
        ("시즌", ("장마", "우천", "여름", "겨울", "성수기", "비수기", "가을", "봄")),
        ("운영", ("체크인", "입실", "퇴실", "청소", "운영", "관리", "동선", "분리수거")),
    )
    tags = [tag for tag, words in rules if any(word in text for word in words)]
    return tags[:4] or ["운영"]


def fallback_insight(item):
    """Return a clearly labelled structure when an AI response is unavailable."""
    tags = insight_tags(item)
    source = unescape(
        " ".join(
            part for part in (
                getattr(item, "description", ""),
                getattr(item, "summary", ""),
            )
            if part
        )
    )
    fragments = [
        re.sub(r"\s+", " ", fragment).strip(" /·")
        for fragment in re.split(r"[\n/]+|(?<=[.!?])\s+", source)
    ]
    fragments = [fragment for fragment in fragments if len(fragment) >= 12]
    observed = next(
        (
            fragment for fragment in fragments
            if any(word in fragment for word in (
                "화장실", "샤워", "개수대", "사이트", "온수", "청소",
                "체험", "행사", "매너타임", "체크인", "동선", "응대",
            ))
        ),
        fragments[0] if fragments else getattr(item, "title", "해당 사례"),
    )[:150]
    customer_signal = next(
        (
            fragment for fragment in fragments
            if any(word in fragment for word in (
                "좋", "만족", "편리", "추천", "깨끗", "친절", "불편", "아쉽",
            ))
        ),
        "원문에 구체적인 고객 반응이 없어 반응 미확인",
    )[:180]
    if "이벤트" in tags:
        apply = "참여 연령, 진행 시간, 담당 인력과 우천 대안을 정한 뒤 소규모 체험부터 시험합니다."
    elif "안전/리스크" in tags:
        apply = "안내 문구와 현장 점검 기준, 담당자 기록 방식을 먼저 정리합니다."
    elif "시설" in tags:
        apply = "시설별 청소·점검 주기와 이용 동선을 현장 기준으로 확인합니다."
    else:
        apply = "실제 인력·비용·동선 부담을 확인한 뒤 우리 캠핑장에 적용합니다."
    return {
        "tags": tags,
        "strength": f"{observed}라는 구체적인 {tags[0]} 운영 요소가 확인됩니다.",
        "customer_signal": customer_signal,
        "lesson": f"{observed}처럼 {tags[0]} 요소를 고객 경험과 현장 관리 기준으로 연결해 적용해 볼 수 있는 사례입니다.",
        "apply": apply,
    }


def normalize_insight(raw):
    """Normalize model output so the dashboard and Kakao text stay predictable."""
    if isinstance(raw, str):
        try:
            raw = json.loads(raw)
        except (TypeError, json.JSONDecodeError):
            return {}
    if not isinstance(raw, dict):
        return {}
    aliases = {
        "고객": "고객경험", "고객 반응": "고객경험", "안전": "안전/리스크",
        "리스크": "안전/리스크", "시즌운영": "시즌", "시설관리": "시설",
    }
    tags = []
    raw_tags = raw.get("tags", raw.get("keywords", []))
    if isinstance(raw_tags, str):
        raw_tags = re.split(r"[,·/ ]+", raw_tags)
    if isinstance(raw_tags, list):
        for tag in raw_tags:
            normalized = aliases.get(str(tag).strip(), str(tag).strip())
            if normalized in INSIGHT_TAGS and normalized not in tags:
                tags.append(normalized)
    def clean(value, limit):
        return " ".join(str(value or "").split()).strip()[:limit]
    return {
        "tags": tags[:4],
        "strength": clean(raw.get("strength", raw.get("key_strength")), 180),
        "customer_signal": clean(raw.get("customer_signal"), 220),
        "lesson": clean(raw.get("lesson", raw.get("why_learnable")), 260),
        "apply": clean(raw.get("apply", raw.get("application_checklist")), 260),
    }


def article_cutoff(as_of=None, max_age_months=MAX_ARTICLE_AGE_MONTHS):
    """Return the inclusive publication-date cutoff for an issue date."""
    if as_of is None:
        as_of = datetime.now(timezone(timedelta(hours=9)))
    issue_date = as_of.date() if isinstance(as_of, datetime) else as_of
    month_index = issue_date.year * 12 + issue_date.month - 1 - max_age_months
    year, month_index = divmod(month_index, 12)
    month = month_index + 1
    day = min(issue_date.day, calendar.monthrange(year, month)[1])
    return date(year, month, day)


def is_recent_article(item, as_of=None, max_age_months=MAX_ARTICLE_AGE_MONTHS):
    """Require a known publication date within the issue's last three months."""
    if not item.published_date:
        return False
    published = item.published_date.date() if isinstance(item.published_date, datetime) else item.published_date
    issue_date = as_of.date() if isinstance(as_of, datetime) else as_of
    if issue_date is None:
        issue_date = datetime.now(timezone(timedelta(hours=9))).date()
    return article_cutoff(issue_date, max_age_months) <= published <= issue_date


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
