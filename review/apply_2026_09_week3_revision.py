"""Apply this week's source-checked editorial revision, without sending messages."""
import json
import sys
from datetime import datetime
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from collectors.base import ContentItem
from collectors.public_review import enrich_public_reviews
from editorial_policy import canonical_url
from main import _load_previous_items
from newsletter_generator import save_newsletter
from ai_filter import GENERATION_STATUS

root = Path(__file__).resolve().parents[1]
records = json.loads((root / "review/2026_09_week3_selection.json").read_text(encoding="utf-8"))
pool = []
for record in records:
    pool.append(ContentItem(
        title=record["original_title"], url=record["url"], source=record["source"],
        description=record["description"],
        published_date=datetime.fromisoformat(record["published_date"]) if record.get("published_date") else None,
        category=record["category"],
    ))
verified = {item.url: item for item in enrich_public_reviews(pool)}
assert len(verified) == len(pool), "Sponsored or unavailable selection requires replacement"
used, _ = _load_previous_items()
assert not {canonical_url(item.url) for item in pool} & used, "Previously exposed article"
items, candidates = [], []
for record in records:
    item = verified[record["url"]]
    item.title, item.summary = record["title"], record["summary"]
    (items if record["section"] == "items" else candidates).append(item)
assert len(items) == 10 and len(candidates) == 30
assert len({item.url for item in items + candidates}) == 40
for item in items + candidates:
    if "blog.naver.com/" in item.url:
        assert item.evidence_basis == "public_blog_body", item.url
GENERATION_STATUS.update(mode="editorial_review", error=None)
result = save_newsletter(items, review_candidates=candidates)
edition = result["json_content"]
edition["review_status"] = "reviewed"
edition["user_review_pending"] = True
edition["quality"]["automatic_generation_error"] = "invalid_api_key"
edition["quality"]["source_review"] = {
    "public_blog_body": sum(item.evidence_basis == "public_blog_body" for item in items + candidates),
    "search_excerpt": sum(item.evidence_basis == "search_excerpt" for item in items + candidates),
}
for section in ("items", "review_candidates"):
    for item in edition[section]:
        item["original_title"] = next(r["original_title"] for r in records if r["url"] == item["url"])
filename = Path(result["json_path"]).name
paths = [
    Path(result["json_path"]), Path(result["archive_path"]),
    root / "dashboard/data/archive/2026/09" / filename,
    root / "dashboard/public/data" / filename,
]
for path in paths:
    path.write_text(json.dumps(edition, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
print(json.dumps({"items":len(items), "candidates":len(candidates), "verification":edition["quality"]["source_review"]}, ensure_ascii=False))
