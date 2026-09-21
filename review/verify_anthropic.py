"""Exercise real selection and summarization without writing or sending an edition."""
import hashlib
import json
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from collectors.base import ContentItem
from ai_filter import filter_content, GENERATION_STATUS, ANTHROPIC_API_KEY

root = Path(__file__).resolve().parents[1]
path = root / "output/newsletter_2026_09_week3.json"
before = hashlib.sha256(path.read_bytes()).hexdigest()
edition = json.loads(path.read_text(encoding="utf-8"))
assert ANTHROPIC_API_KEY, "ANTHROPIC_API_KEY is missing"
pool = [
    ContentItem(title=item.get("original_title", item["title"]), url=item["url"],
                source=item["source"], description=item["description"], category=item["category"])
    for item in edition["items"][:3]
]
result = filter_content(pool, count=2)
assert len(result) == 2, "Selection did not return two items"
assert GENERATION_STATUS["mode"] == "ai" and GENERATION_STATUS["error"] is None, "API fell back; authentication or generation is not healthy"
for item in result:
    assert len(item.summary.strip()) >= 30, "Summary missing"
    assert item.summary.strip() != item.description.strip(), "Description was copied instead of summarized"
    assert not item.summary.startswith("확인된 자료 발췌:"), "Fallback summary"
assert hashlib.sha256(path.read_bytes()).hexdigest() == before, "Edition was modified"
print("API_CHECK_PASSED: real AI selection and summaries; edition unchanged; no delivery.")
for item in result:
    print(json.dumps({"title": item.title, "summary": item.summary}, ensure_ascii=False))
