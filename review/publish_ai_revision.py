"""Publish a reviewed AI draft to existing newsletter outputs; no messages sent."""
import json
import sys
from datetime import datetime
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from collectors.base import ContentItem
from newsletter_generator import generate_newsletter_text
from editorial_policy import canonical_url
from main import _load_previous_items

root = Path(__file__).resolve().parents[1]
draft = root / "review/ai_newsletter_2026_09_week3.json"
data = json.loads(draft.read_text(encoding="utf-8"))
assert data["items_count"] == len(data["items"]) == 10
assert len(data["review_candidates"]) >= 30
assert data["quality"]["summary_generation"] == {"mode": "ai", "error": None}
all_items = data["items"] + data["review_candidates"]
assert len({canonical_url(x["url"]) for x in all_items}) == len(all_items)
used, _ = _load_previous_items()
assert not {canonical_url(x["url"]) for x in all_items} & used
assert all(len(x["summary"]) >= 60 and not x["summary"].startswith("확인된 자료 발췌:") for x in all_items)
data["review_status"] = "reviewed"
data["user_review_pending"] = True
data["quality"]["editorial_review_completed"] = True
data["quality"]["source_review"] = {
    kind: sum(x.get("evidence_basis") == kind for x in all_items)
    for kind in ("public_blog_body", "search_excerpt")
}
name = draft.name.removeprefix("ai_")
w = data["week_info"]
for directory in ("output", f"archive/{w['year']}/{w['month']:02d}",
                  f"dashboard/data/archive/{w['year']}/{w['month']:02d}", "dashboard/public/data"):
    (root / directory / name).write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
items = [ContentItem(title=x["title"], url=x["url"], source=x["source"],
                     description=x["description"], summary=x["summary"], category=x["category"]) for x in data["items"]]
(root / "output" / name.replace(".json", ".txt")).write_text(generate_newsletter_text(items, w), encoding="utf-8")
print(json.dumps({"items": len(items), "candidates":len(data["review_candidates"]), "quality":data["quality"]}, ensure_ascii=False))
