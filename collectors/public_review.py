"""Read public blog bodies before selecting; never access member-only content."""
from concurrent.futures import ThreadPoolExecutor
from dataclasses import replace
from urllib.parse import urlparse
import requests
from bs4 import BeautifulSoup

SPONSOR_TERMS = (
    "협찬", "체험단", "제공받", "제공 받", "원고료", "그래가", "그레가",
    "graega", "파트너스", "제휴 마케팅", "제휴마케팅", "수수료를 제공",
)
INSIGHT_TERMS = (
    "매너타임", "순찰", "청소", "개별", "온수", "울타리", "동선", "체험",
    "보물찾기", "사탕", "재방문", "응대", "사장님", "매점", "그늘",
    "불편", "단점", "사이트", "수압", "운영시간", "분리수거",
)


def enrich_public_reviews(items, limit=120):
    from ai_filter import _rule_based_score
    blogs = sorted(
        [item for item in items if urlparse(item.url).netloc in ("blog.naver.com", "m.blog.naver.com")],
        key=_rule_based_score, reverse=True,
    )[:limit]
    results = {}
    def read(item):
        try:
            url = item.url.replace("://blog.naver.com/", "://m.blog.naver.com/")
            response = requests.get(url, timeout=12)
            response.raise_for_status()
            body = BeautifulSoup(response.text, "html.parser").select_one(".se-main-container")
            if body is None:
                return item.url, item
            full_text = body.get_text(" ", strip=True).lower()
            if any(term in full_text for term in SPONSOR_TERMS):
                return item.url, None
            paragraphs = [" ".join(p.get_text(" ", strip=True).split()) for p in body.select("p")]
            evidence = []
            for paragraph in paragraphs:
                if not 20 <= len(paragraph) <= 220 or paragraph.startswith("#"):
                    continue
                if any(term in paragraph for term in INSIGHT_TERMS) and paragraph not in evidence:
                    evidence.append(paragraph)
                if sum(map(len, evidence)) >= 600:
                    break
            enriched = replace(item)
            if evidence:
                enriched.description = " / ".join(evidence)[:750]
            enriched.evidence_basis = "public_blog_body"
            return item.url, enriched
        except (requests.RequestException, ValueError):
            return item.url, item
    with ThreadPoolExecutor(max_workers=6) as executor:
        for url, item in executor.map(read, blogs):
            results[url] = item
    print(f"Public blog verification: {len(blogs)} checked, {sum(value is None for value in results.values())} sponsored posts excluded")
    return [results.get(item.url, item) for item in items if results.get(item.url, item) is not None]
