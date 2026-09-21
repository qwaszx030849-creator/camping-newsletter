"""Explicit AI regeneration into a review draft, never delivery or live output."""
import json
import sys
from datetime import datetime
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from collectors.base import ContentItem
from main import collect_all_content, _load_previous_items, _remove_previously_used
from ai_filter import (_call_claude, _parse_json_response, _format_content_list,
                       _is_hard_rejected, prepare_replacement_candidates, GENERATION_STATUS)
from newsletter_generator import get_week_info, generate_newsletter_json
from editorial_policy import canonical_url, same_article

root = Path(__file__).resolve().parents[1]
week = get_week_info()
filename = f"newsletter_{week['year']}_{week['month']:02d}_week{week['week_of_month']}.json"
current = json.loads((root / "output" / filename).read_text(encoding="utf-8"))
fresh = collect_all_content()
pool = prepare_replacement_candidates(fresh, [], limit=100)
# Reconsider this week's verified sources as well as newly collected material.
for record in current["items"] + current.get("review_candidates", []):
    item = ContentItem(
        title=record.get("original_title", record["title"]), url=record["url"],
        source=record["source"], description=record["description"],
        category=record["category"], evidence_basis=record.get("evidence_basis", "search_excerpt"),
        published_date=datetime.fromisoformat(record["published_date"]) if record.get("published_date") else None,
    )
    if not _is_hard_rejected(item) and not any(same_article(item, x) for x in pool):
        pool.append(item)
used, previous = _load_previous_items()
pool = _remove_previously_used(pool, used, previous)
prompt = """캠핑장 5~10년 운영자에게 전달하는 운영 인사이트 자료의 편집자입니다.
아래 자료에서 본문 10개와 교체 후보 30개, 총 40개를 유용한 순서로 선별하세요.
첫 10개가 본문입니다. 경험 많은 운영자가 구체적으로 배울 수 있는 차이를 최우선합니다.
후기와 캠지기 사례 중심으로 체험, 이벤트, 동선, 매점, 청결, 입퇴실, 재방문, 시설관리, 반려견 등을 폭넓게 다룹니다.
할로윈과 다른 캠핑장 사례는 환영합니다. 지역명이 있다고 제외하지 마세요.
그래가/협찬/대행사/플랫폼 홍보/노지/파크골프/창업일반론/몰락 같은 자극적 글은 제외합니다.
공공뉴스, 정책, 날씨, 단순 시설 나열, 근거 없는 수익 주장, 질문만 있는 글은 배제합니다.
같은 캠핑장 최대 2개, 같은 운영 포인트는 본문에서 중복하지 마세요.
게시일과 방문시점은 다릅니다. 지난 할로윈 사례는 올해 행사 공지로 소개하면 안 됩니다.
검색 발췌의 단어만으로 성과나 인과관계를 만들어내지 마세요.
JSON 배열만 응답: [{"index":0,"category":"체험운영","reason":"구체적인 선정 이유"}]
자료:
""" + _format_content_list(pool)
response = _call_claude(prompt)
(root / "review/ai_selection_response.txt").write_text(response, encoding="utf-8")
def selection_rows(text):
    decoder = json.JSONDecoder()
    parsed_values = []
    for position, character in enumerate(text):
        if character not in "[{":
            continue
        try:
            parsed, _ = decoder.raw_decode(text[position:])
            parsed_values.append(parsed)
        except json.JSONDecodeError:
            continue
    def rows(value):
        if isinstance(value, bool):
            return []
        if isinstance(value, int):
            return [{"index": value}]
        if isinstance(value, list):
            return [row for child in value for row in rows(child)]
        if isinstance(value, dict):
            if "index" in value:
                return [value]
            return [row for child in value.values() if isinstance(child, (list, dict)) for row in rows(child)]
        return []
    return max((rows(value) for value in parsed_values), key=len, default=[])
selection = selection_rows(response)
chosen = []
reasons = {}
for row in selection:
    idx = row.get("index")
    if isinstance(idx, int) and 0 <= idx < len(pool):
        item = pool[idx]
        if not any(same_article(item, x) for x in chosen):
            item.category = row.get("category", item.category)
            item.summary = ""
            chosen.append(item)
            reasons[item.url] = row.get("reason", "")
for attempt in range(2):
    if len(chosen) >= 40:
        break
    remaining = [x for x in pool if not any(same_article(x, y) for y in chosen)]
    needed = 40 - len(chosen)
    supplement_prompt = f"""캠핑장 운영 인사이트 뉴스레터의 교체 후보를 정확히 {needed}개 추가 선별하세요.
앞선 선별분과 겹치지 않는 나머지 자료입니다. 캠퍼 후기와 캠지기 운영 사례에서 구체적인 운영 포인트가 있는 것을 골라주세요.
그래가, 협찬, 플랫폼 홍보, 파크골프, 정부/날씨 단신, 질문만 있는 글은 제외합니다.
같은 테마라도 다른 캠핑장의 다른 운영 사례는 허용합니다. 측정되지 않은 성과는 추측하지 마세요.
JSON 배열만 반환: [{{"index":0,"category":"시설관리","reason":"선정 이유"}}]
자료:
""" + _format_content_list(remaining)
    supplement = selection_rows(_call_claude(supplement_prompt))
    for row in supplement:
        idx = row.get("index")
        if isinstance(idx, int) and 0 <= idx < len(remaining):
            item = remaining[idx]
            if not any(same_article(item, x) for x in chosen):
                item.category = row.get("category", item.category)
                item.summary = ""
                chosen.append(item)
                reasons[item.url] = row.get("reason", "")
    print(f"AI supplement {attempt + 1}: {len(chosen)} selected", flush=True)
assert len(chosen) >= 40, f"Only {len(chosen)} selected; draft not published"
chosen = chosen[:40]
for offset in range(0, 40, 5):
    batch = chosen[offset:offset + 5]
    prompt = """캠핑장 운영자를 위한 2~3문장의 운영 인사이트를 각 자료에 작성하세요.
JSON 배열만 응답: [{"index":0,"summary":"..."}]
규칙:
1. 첫 문장에는 자료에서 확인되는 구체적인 사실/경험을 씁니다. 두 번째부터 '운영 적용:'으로 실행 제안을 구분합니다.
2. 매출/예약률/재방문 증가 등 측정되지 않은 성과나 인과관계를 절대 단정하지 않습니다.
3. 수치·가격·시간은 자료에 명시된 경우에만 사용하고 방문 당시 사례임을 밝힙니다.
4. 최신 행사 공지가 아닌 과거 사례는 현재 시행 중이라고 쓰지 않습니다.
5. 검색 발췌가 근거일 때는 '후기 발췌에서는'으로 한계를 명시합니다.
6. 제목을 반복하거나 청결/친절을 강조하라는 일반론만 쓰지 않습니다.
7. 법적 의무, 안전 기준이나 수익성을 근거 없이 확정하지 않습니다.
8. 사실은 있는 만큼만 쓰고 적용 제안은 검토할 선택지로 서술합니다.
""" + "\n".join(f"[{i}] 근거 범위: {x.evidence_basis}" for i,x in enumerate(batch)) + "\n" + _format_content_list(batch)
    summaries = selection_rows(_call_claude(prompt))
    seen = set()
    for row in summaries:
        idx, summary = row.get("index"), row.get("summary", "")
        if isinstance(idx,int) and 0 <= idx < len(batch) and isinstance(summary,str) and len(summary) > 60:
            batch[idx].summary = summary
            seen.add(idx)
    assert len(seen) == len(batch), "Incomplete AI summaries"
assert GENERATION_STATUS["mode"] == "ai" and GENERATION_STATUS["error"] is None
data = generate_newsletter_json(chosen[:10], week, chosen[10:])
for section in ("items", "review_candidates"):
    for item in data[section]:
        item["selection_reason"] = reasons[item["url"]]
data["quality"]["fresh_collection_count"] = len(fresh)
data["quality"]["ai_review_pool_count"] = len(pool)
data["quality"]["ai_summary_count"] = len(chosen)
draft = root / "review" / ("ai_" + filename)
draft.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
print("AI_REGENERATION_PASSED", len(fresh), len(pool), len(chosen), draft.name)
