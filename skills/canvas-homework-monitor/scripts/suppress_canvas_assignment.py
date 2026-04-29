#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any

DEFAULT_LOG_PATH = Path.home() / ".local" / "share" / "openclaw" / "canvas-homework-monitor" / "last-actionable-report.json"
DEFAULT_SUPPRESSION_PATH = Path.home() / ".local" / "share" / "openclaw" / "canvas-homework-monitor" / "suppressed-items.json"


def load_json(path: Path, default: Any) -> Any:
    if not path.exists():
        return default
    try:
        return json.loads(path.read_text())
    except Exception as exc:
        raise SystemExit(f"Failed to read {path}: {exc}")


def save_json(path: Path, payload: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2))


def load_items(log_path: Path) -> list[dict[str, Any]]:
    payload = load_json(log_path, {"items": []})
    items = payload.get("items") or []
    if not isinstance(items, list):
        raise SystemExit(f"Unexpected log format in {log_path}")
    return items


def load_suppressed(path: Path) -> set[str]:
    payload = load_json(path, {"suppressed_keys": []})
    keys = payload.get("suppressed_keys") or []
    return {k for k in keys if isinstance(k, str)}


def save_suppressed(path: Path, keys: set[str]) -> None:
    save_json(path, {"suppressed_keys": sorted(keys)})


def item_label(item: dict[str, Any], idx: int) -> str:
    return (
        f"[{idx}] {item.get('student_name','?')} | {item.get('status','?')} | "
        f"{item.get('course_name','?')} | {item.get('title','?')} | "
        f"due {item.get('due_at','?')}"
    )


def find_matches(items: list[dict[str, Any]], query: str) -> list[tuple[int, dict[str, Any]]]:
    q = query.lower().strip()
    matches = []
    for i, item in enumerate(items, start=1):
        blob = " ".join(
            str(item.get(field, ""))
            for field in ["student_name", "status", "course_name", "module_name", "title", "due_at", "suppress_key"]
        ).lower()
        if q in blob:
            matches.append((i, item))
    return matches


def main() -> int:
    parser = argparse.ArgumentParser(description="Suppress Canvas homework items across future runs.")
    parser.add_argument("--log", default=str(DEFAULT_LOG_PATH), help="Path to actionable log JSON")
    parser.add_argument("--suppressed", default=str(DEFAULT_SUPPRESSION_PATH), help="Path to suppression JSON")
    parser.add_argument("--list", action="store_true", help="List actionable items from the current log")
    parser.add_argument("--show-suppressed", action="store_true", help="Show suppressed keys")
    parser.add_argument("--find", help="Search actionable items by text")
    parser.add_argument("--add-key", action="append", default=[], help="Suppress a specific suppress_key")
    parser.add_argument("--add-index", action="append", type=int, default=[], help="Suppress one or more item indexes from --list output")
    args = parser.parse_args()

    log_path = Path(args.log).expanduser()
    suppressed_path = Path(args.suppressed).expanduser()
    items = load_items(log_path)
    suppressed = load_suppressed(suppressed_path)

    changed = False

    if args.list:
        for i, item in enumerate(items, start=1):
            marker = "[suppressed] " if item.get("suppress_key") in suppressed else ""
            print(marker + item_label(item, i))

    if args.find:
        matches = find_matches(items, args.find)
        if not matches:
            print("No matches found.")
        else:
            for i, item in matches:
                marker = "[suppressed] " if item.get("suppress_key") in suppressed else ""
                print(marker + item_label(item, i))
                print(f"  suppress_key: {item.get('suppress_key')}")

    for key in args.add_key:
        if key and key not in suppressed:
            suppressed.add(key)
            changed = True
            print(f"Suppressed key: {key}")

    if args.add_index:
        for index in args.add_index:
            if index < 1 or index > len(items):
                raise SystemExit(f"Index out of range: {index}")
            key = items[index - 1].get("suppress_key")
            if not isinstance(key, str):
                raise SystemExit(f"Item {index} has no suppress_key")
            if key not in suppressed:
                suppressed.add(key)
                changed = True
                print(f"Suppressed item {index}: {items[index - 1].get('title')}")

    if changed:
        save_suppressed(suppressed_path, suppressed)
        print(f"Updated {suppressed_path}")

    if args.show_suppressed:
        for key in sorted(suppressed):
            print(key)

    if not any([args.list, args.show_suppressed, args.find, args.add_key, args.add_index]):
        parser.print_help()
        return 1

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
