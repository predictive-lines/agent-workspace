#!/usr/bin/env python3
"""Combined daily homework digest: Canvas + Membean.

Runs the Canvas checker against a single config (typically the DCDS parent
account) and any number of per-student Membean configs, then produces a
unified summary and JSON payload.

Membean integration rules (per Justin):

- Canvas items whose title contains "membean" (case-insensitive) are
  matched up with the corresponding student's Membean checker output.
- If that student's Membean weekly status is ``complete`` for the
  Monday-Sunday window, the Canvas Membean items are dropped from the
  actionable list (Canvas does not see the actual Membean session log,
  so its "missing"/"due" state lags reality).
- Otherwise, the Canvas Membean items are *kept* (so they stay visible)
  and the digest also surfaces the Membean weekly status block so the
  end-of-week warning (\"running out of days\") is loud.

Output mirrors the Canvas script's shape (``summary`` / ``new_summary``
strings, plus structured JSON), so this script can be a drop-in
replacement for cron jobs that previously called ``check_canvas_homework.py``.
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any
from zoneinfo import ZoneInfo

_HERE = Path(__file__).resolve().parent
if str(_HERE) not in sys.path:
    sys.path.insert(0, str(_HERE))

import check_canvas_homework as canvas_mod  # noqa: E402
import check_membean_homework as membean_mod  # noqa: E402


MEMBEAN_TITLE_TOKEN = "membean"


def _normalize_student_name(name: str) -> str:
    return (name or "").strip().lower()


def _matches_student(membean_payload: dict[str, Any], student_name: str) -> bool:
    """Does this Membean payload describe the given Canvas student name?"""
    target = _normalize_student_name(student_name)
    if not target:
        return False
    candidate = _normalize_student_name(membean_payload.get("student_name") or "")
    if not candidate:
        return False
    if candidate == target:
        return True
    # Soft-match on first or last name token so "Cora" / "Cora Miller" / "Coraline"
    # all line up sensibly. The Canvas account uses formal names; the Membean
    # configs may use shorter ones.
    target_tokens = set(target.replace("-", " ").split())
    candidate_tokens = set(candidate.replace("-", " ").split())
    if target_tokens & candidate_tokens:
        return True
    return False


def _is_membean_canvas_item(item: dict[str, Any]) -> bool:
    title = (item.get("title") or "").lower()
    course = (item.get("course_name") or "").lower()
    return MEMBEAN_TITLE_TOKEN in title or MEMBEAN_TITLE_TOKEN in course


def merge(
    *,
    canvas_payload: dict[str, Any],
    membean_payloads: list[dict[str, Any]],
) -> dict[str, Any]:
    """Apply Membean overrides to the Canvas payload and produce a merged digest."""

    # Index Membean payloads by normalized student-name string for quick lookup.
    membean_by_student: dict[str, dict[str, Any]] = {}
    for payload in membean_payloads:
        student = _normalize_student_name(payload.get("student_name") or "")
        if student:
            membean_by_student[student] = payload

    suppressed: list[dict[str, Any]] = []
    kept_items: list[dict[str, Any]] = []
    for item in canvas_payload.get("items") or []:
        if not _is_membean_canvas_item(item):
            kept_items.append(item)
            continue
        # Find a Membean payload for this student.
        match = next(
            (
                payload
                for payload in membean_payloads
                if _matches_student(payload, item.get("student_name") or "")
            ),
            None,
        )
        if match and match.get("status") == "complete":
            suppressed.append({**item, "_membean_status": "complete"})
            continue
        kept_items.append({**item, "_membean_status": (match or {}).get("status")})

    # Same treatment for the "new items" list so notification-style summaries
    # also drop already-completed Membean assignments.
    kept_new_items: list[dict[str, Any]] = []
    for item in canvas_payload.get("new_items") or []:
        if not _is_membean_canvas_item(item):
            kept_new_items.append(item)
            continue
        match = next(
            (
                payload
                for payload in membean_payloads
                if _matches_student(payload, item.get("student_name") or "")
            ),
            None,
        )
        if match and match.get("status") == "complete":
            continue
        kept_new_items.append(item)

    # Re-format the summaries using the Canvas formatter so behavior matches
    # the existing checker.
    tz = ZoneInfo(canvas_payload.get("timezone") or "America/New_York")
    label = canvas_payload.get("student_name") or "Students"

    canvas_items_objs = [_dict_to_status(item) for item in kept_items]
    canvas_new_items_objs = [_dict_to_status(item) for item in kept_new_items]
    canvas_grade_objs = [_dict_to_grade(g) for g in canvas_payload.get("grades") or []]

    summary_lines = [canvas_mod.format_summary(label, canvas_items_objs, tz)]
    new_summary_lines = [canvas_mod.format_summary(label, canvas_new_items_objs, tz)]

    membean_block = _format_membean_block(membean_payloads)
    if membean_block:
        summary_lines.append("")
        summary_lines.append(membean_block)
        new_summary_lines.append("")
        new_summary_lines.append(membean_block)

    grades_summary = canvas_mod.format_grades_summary(label, canvas_grade_objs)

    merged: dict[str, Any] = dict(canvas_payload)
    merged["items"] = kept_items
    merged["new_items"] = kept_new_items
    merged["count"] = len(kept_items)
    merged["new_count"] = len(kept_new_items)
    merged["membean"] = membean_payloads
    merged["membean_suppressed_canvas_items"] = suppressed
    merged["summary"] = "\n".join(summary_lines)
    merged["new_summary"] = "\n".join(new_summary_lines)
    merged["grades_summary"] = grades_summary
    return merged


def _dict_to_status(item: dict[str, Any]) -> canvas_mod.AssignmentStatus:
    return canvas_mod.AssignmentStatus(
        student_name=item.get("student_name") or "",
        course_name=item.get("course_name") or "",
        module_name=item.get("module_name") or "",
        title=item.get("title") or "",
        item_type=item.get("item_type") or "",
        status=item.get("status") or "",
        due_at=item.get("due_at"),
        html_url=item.get("html_url"),
        details=item.get("details") or {},
    )


def _dict_to_grade(grade: dict[str, Any]) -> canvas_mod.CourseGrade:
    return canvas_mod.CourseGrade(
        student_name=grade.get("student_name") or "",
        course_name=grade.get("course_name") or "",
        current_grade=grade.get("current_grade"),
        current_score=grade.get("current_score"),
        final_grade=grade.get("final_grade"),
        final_score=grade.get("final_score"),
        html_url=grade.get("html_url"),
    )


def _format_membean_block(membean_payloads: list[dict[str, Any]]) -> str:
    if not membean_payloads:
        return ""
    lines = ["Membean weekly status:"]
    # Order by student name for stable rendering.
    for payload in sorted(
        membean_payloads, key=lambda p: _normalize_student_name(p.get("student_name") or "")
    ):
        lines.append(f"- {payload.get('headline', '(no headline)')}")
    return "\n".join(lines)


def main() -> int:
    parser = argparse.ArgumentParser(
        description=(
            "Run the Canvas homework checker plus per-student Membean checkers "
            "and emit a single merged digest."
        )
    )
    parser.add_argument(
        "--canvas-config",
        required=True,
        help="Path to the Canvas JSON config (e.g. ~/.config/canvas-homework-monitor/dcds-parent.json).",
    )
    parser.add_argument(
        "--membean-config",
        action="append",
        default=[],
        help="Path to a per-student Membean JSON config. Pass multiple times for multiple students.",
    )
    parser.add_argument("--summary", action="store_true", help="Print only the text summary.")
    parser.add_argument(
        "--new-only",
        action="store_true",
        help="Print newly-actionable items, while continuing to surface open pre-due reminders until they are due or suppressed (Membean status still surfaces).",
    )
    args = parser.parse_args()

    canvas_path = Path(args.canvas_config).expanduser()
    membean_paths = [Path(p).expanduser() for p in args.membean_config]

    try:
        canvas_payload = canvas_mod.run(canvas_path)
    except Exception as exc:
        print(json.dumps({"error": f"canvas check failed: {exc}"}, indent=2), file=sys.stderr)
        return 1

    membean_payloads: list[dict[str, Any]] = []
    membean_errors: list[dict[str, Any]] = []
    for path in membean_paths:
        try:
            membean_payloads.append(membean_mod.run_check(path))
        except Exception as exc:
            membean_errors.append({"config": str(path), "error": str(exc)})

    merged = merge(canvas_payload=canvas_payload, membean_payloads=membean_payloads)
    if membean_errors:
        merged["membean_errors"] = membean_errors

    if args.summary:
        print(merged["new_summary"] if args.new_only else merged["summary"])
        if membean_errors:
            print()
            print("Membean errors:")
            for entry in membean_errors:
                print(f"  - {entry['config']}: {entry['error']}")
    else:
        print(json.dumps(merged, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
