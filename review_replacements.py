"""
Replace or delete rejected newsletter items during editorial review.

Example:
    python review_replacements.py --file output/newsletter_2026_07_week3.json --exclude 5 8 9
    python review_replacements.py --file output/newsletter_2026_09_week1.json --delete 5 8
"""
import argparse
import json
from copy import deepcopy
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List



ROOT = Path(__file__).resolve().parent


def _load_json(path: Path) -> Dict[str, Any]:
    with path.open("r", encoding="utf-8") as f:
        return json.load(f)


def _write_json(path: Path, data: Dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)




def _generate_fallback_text(items: List[Dict[str, Any]], week_info: Dict[str, Any]) -> str:
    lines = [
        "🏕️ 캠핑장 운영 인사이트 노트",
        f"📅 {week_info.get('display', '')}",
        "",
        "주변 캠핑장의 운영 방식과 이용자 후기에서 뽑은 벤치마킹 메모입니다.",
        "오래 운영한 캠지기도 내 현장에 적용할 힌트만 빠르게 볼 수 있게 정리했습니다.",
        "",
        "ㅡㅡㅡㅡㅡㅡㅡㅡㅡㅡㅡㅡ",
    ]
    for index, item in enumerate(items, 1):
        lines.extend(
            [
                "",
                f"📌 {index}. {item.get('title', '')}",
                "",
                f"💬 {item.get('summary') or item.get('description', '')}",
                "",
                f"🔗 {item.get('url', '')}",
                "",
                "ㅡㅡㅡㅡㅡㅡㅡㅡㅡㅡㅡㅡ",
            ]
        )
    return "\n".join(lines) + "\n"


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


def edit_items(
    data: Dict[str, Any],
    excluded_numbers: List[int] | None = None,
    delete_numbers: List[int] | None = None,
    reason: str = "",
) -> Dict[str, Any]:
    items = deepcopy(data.get("items", []))
    candidates = deepcopy(data.get("review_candidates", []))
    excluded_numbers = excluded_numbers or []
    delete_numbers = delete_numbers or []
    if excluded_numbers and not candidates:
        raise ValueError("No review_candidates found. Regenerate this newsletter with the updated pipeline first.")

    excluded_indexes = sorted({n - 1 for n in excluded_numbers})
    delete_indexes = sorted({n - 1 for n in delete_numbers})
    invalid_indexes = [i for i in [*excluded_indexes, *delete_indexes] if i < 0 or i >= len(items)]
    if invalid_indexes:
        raise ValueError(f"Item numbers must be between 1 and {len(items)}.")

    active_urls = {
        item.get("url")
        for i, item in enumerate(items)
        if i not in excluded_indexes and i not in delete_indexes
    }
    candidate_cursor = 0
    replacements = []
    deletions = []

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

    for item_index in sorted(delete_indexes, reverse=True):
        removed = items.pop(item_index)
        deletions.append(
            {
                "slot": item_index + 1,
                "removed": {
                    "title": removed.get("title", ""),
                    "url": removed.get("url", ""),
                },
            }
        )

    updated = deepcopy(data)
    updated["items"] = items
    updated["items_count"] = len(items)
    if replacements and deletions:
        updated["review_status"] = "edited"
    elif replacements:
        updated["review_status"] = "replaced"
    else:
        updated["review_status"] = "deleted"
    updated["reviewed_at"] = datetime.now().isoformat()
    updated.setdefault("review_changes", []).append(
        {
            "reviewed_at": updated["reviewed_at"],
            "excluded_numbers": excluded_numbers,
            "deleted_numbers": delete_numbers,
            "reason": reason,
            "replacements": replacements,
            "deletions": sorted(deletions, key=lambda change: change["slot"]),
        }
    )
    used_urls = {item.get("url") for item in items}
    updated["review_candidates"] = [
        candidate for candidate in candidates[candidate_cursor:] if candidate.get("url") not in used_urls
    ]
    return updated


def replace_items(data: Dict[str, Any], excluded_numbers: List[int], reason: str = "") -> Dict[str, Any]:
    return edit_items(data, excluded_numbers=excluded_numbers, reason=reason)


def save_updated_newsletter(data: Dict[str, Any], source_path: Path) -> Dict[str, Path]:
    paths = _target_paths(data, source_path)
    for key in ["source", "output_json", "archive_json", "dashboard_archive_json", "dashboard_public_json"]:
        _write_json(paths[key], data)

    try:
        from collectors.base import ContentItem
        from newsletter_generator import generate_newsletter_text

        content_items = [
            ContentItem(
                title=item.get("title", ""),
                url=item.get("url", ""),
                source=item.get("source", ""),
                description=item.get("description", ""),
                summary=item.get("summary", ""),
                category=item.get("category", ""),
                score=float(item.get("score") or 0),
            )
            for item in data["items"]
        ]
        text = generate_newsletter_text(content_items, data["week_info"])
    except ModuleNotFoundError:
        text = _generate_fallback_text(data["items"], data["week_info"])
    paths["output_txt"].parent.mkdir(parents=True, exist_ok=True)
    paths["output_txt"].write_text(text, encoding="utf-8")
    return paths


def main() -> None:
    parser = argparse.ArgumentParser(description="Replace or delete rejected newsletter items.")
    parser.add_argument("--file", required=True, help="Newsletter JSON path.")
    parser.add_argument("--exclude", nargs="+", type=int, default=[], help="1-based item numbers to replace.")
    parser.add_argument("--delete", nargs="+", type=int, default=[], help="1-based item numbers to delete without replacement.")
    parser.add_argument("--reason", default="", help="Optional review memo.")
    args = parser.parse_args()
    if not args.exclude and not args.delete:
        parser.error("At least one of --exclude or --delete is required.")

    source_path = Path(args.file)
    if not source_path.is_absolute():
        source_path = ROOT / source_path

    data = _load_json(source_path)
    updated = edit_items(data, excluded_numbers=args.exclude, delete_numbers=args.delete, reason=args.reason)
    paths = save_updated_newsletter(updated, source_path)

    print("Updated newsletter review edits:")
    last_change = updated["review_changes"][-1]
    for change in last_change["replacements"]:
        print(f"  replace {change['slot']}. {change['removed']['title']} -> {change['replacement']['title']}")
    for change in last_change["deletions"]:
        print(f"  delete {change['slot']}. {change['removed']['title']}")
    print("Saved files:")
    for key, path in paths.items():
        print(f"  {key}: {path}")


if __name__ == "__main__":
    main()
