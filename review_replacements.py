"""
Replace rejected newsletter items with pre-collected review candidates.

Example:
    python review_replacements.py --file output/newsletter_2026_07_week3.json --exclude 5 8 9
"""
import argparse
import json
from copy import deepcopy
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List

from collectors.base import ContentItem
from newsletter_generator import generate_newsletter_text


ROOT = Path(__file__).resolve().parent


def _load_json(path: Path) -> Dict[str, Any]:
    with path.open("r", encoding="utf-8") as f:
        return json.load(f)


def _write_json(path: Path, data: Dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)


def _item_from_dict(data: Dict[str, Any]) -> ContentItem:
    return ContentItem(
        title=data.get("title", ""),
        url=data.get("url", ""),
        source=data.get("source", ""),
        description=data.get("description", ""),
        summary=data.get("summary", ""),
        category=data.get("category", ""),
        score=float(data.get("score") or 0),
    )


def _target_paths(data: Dict[str, Any], source_path: Path) -> Dict[str, Path]:
    week = data["week_info"]
    base = f"newsletter_{week['year']}_{int(week['month']):02d}_week{week['week_of_month']}"
    return {
        "source": source_path,
        "output_json": ROOT / "output" / f"{base}.json",
        "output_txt": ROOT / "output" / f"{base}.txt",
        "archive_json": ROOT / "archive" / str(week["year"]) / f"{int(week['month']):02d}" / f"{base}.json",
        "dashboard_archive_json": ROOT / "dashboard" / "data" / "archive" / str(week["year"]) / f"{int(week['month']):02d}" / f"{base}.json",
        "dashboard_public_json": ROOT / "dashboard" / "public" / "data" / f"{base}.json",
    }


def replace_items(data: Dict[str, Any], excluded_numbers: List[int], reason: str = "") -> Dict[str, Any]:
    items = deepcopy(data.get("items", []))
    candidates = deepcopy(data.get("review_candidates", []))
    if not candidates:
        raise ValueError("No review_candidates found. Regenerate this newsletter with the updated pipeline first.")

    excluded_indexes = sorted({n - 1 for n in excluded_numbers})
    if any(i < 0 or i >= len(items) for i in excluded_indexes):
        raise ValueError(f"Exclude numbers must be between 1 and {len(items)}.")

    active_urls = {item.get("url") for i, item in enumerate(items) if i not in excluded_indexes}
    candidate_cursor = 0
    replacements = []

    for item_index in excluded_indexes:
        replacement = None
        while candidate_cursor < len(candidates):
            candidate = candidates[candidate_cursor]
            candidate_cursor += 1
            url = candidate.get("url")
            if not url or url in active_urls:
                continue
            replacement = candidate
            break

        if replacement is None:
            raise ValueError("Not enough replacement candidates to fill all excluded slots.")

        removed = items[item_index]
        items[item_index] = replacement
        active_urls.add(replacement.get("url"))
        replacements.append(
            {
                "slot": item_index + 1,
                "removed": {
                    "title": removed.get("title", ""),
                    "url": removed.get("url", ""),
                },
                "replacement": {
                    "title": replacement.get("title", ""),
                    "url": replacement.get("url", ""),
                },
            }
        )

    updated = deepcopy(data)
    updated["items"] = items
    updated["items_count"] = len(items)
    updated["review_status"] = "replaced"
    updated["reviewed_at"] = datetime.now().isoformat()
    updated.setdefault("review_changes", []).append(
        {
            "reviewed_at": updated["reviewed_at"],
            "excluded_numbers": excluded_numbers,
            "reason": reason,
            "replacements": replacements,
        }
    )
    used_urls = {item.get("url") for item in items}
    updated["review_candidates"] = [
        candidate for candidate in candidates[candidate_cursor:] if candidate.get("url") not in used_urls
    ]
    return updated


def save_updated_newsletter(data: Dict[str, Any], source_path: Path) -> Dict[str, Path]:
    paths = _target_paths(data, source_path)
    for key in ["source", "output_json", "archive_json", "dashboard_archive_json", "dashboard_public_json"]:
        _write_json(paths[key], data)

    text = generate_newsletter_text([_item_from_dict(item) for item in data["items"]], data["week_info"])
    paths["output_txt"].parent.mkdir(parents=True, exist_ok=True)
    paths["output_txt"].write_text(text, encoding="utf-8")
    return paths


def main() -> None:
    parser = argparse.ArgumentParser(description="Replace rejected newsletter items.")
    parser.add_argument("--file", required=True, help="Newsletter JSON path.")
    parser.add_argument("--exclude", nargs="+", type=int, required=True, help="1-based item numbers to remove.")
    parser.add_argument("--reason", default="", help="Optional review memo.")
    args = parser.parse_args()

    source_path = Path(args.file)
    if not source_path.is_absolute():
        source_path = ROOT / source_path

    data = _load_json(source_path)
    updated = replace_items(data, args.exclude, args.reason)
    paths = save_updated_newsletter(updated, source_path)

    print("Updated newsletter review replacements:")
    for change in updated["review_changes"][-1]["replacements"]:
        print(f"  {change['slot']}. {change['removed']['title']} -> {change['replacement']['title']}")
    print("Saved files:")
    for key, path in paths.items():
        print(f"  {key}: {path}")


if __name__ == "__main__":
    main()
