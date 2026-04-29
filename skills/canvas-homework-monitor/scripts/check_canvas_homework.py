#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import os
import re
import sys
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from pathlib import Path
from typing import Any
from urllib.parse import urljoin
from zoneinfo import ZoneInfo

from playwright.sync_api import TimeoutError as PlaywrightTimeoutError
from playwright.sync_api import sync_playwright


DEFAULT_STATE_PATH = Path.home() / ".local" / "share" / "openclaw" / "canvas-homework-monitor" / "storage-state.json"
DEFAULT_NOTIFICATION_STATE_PATH = Path.home() / ".local" / "share" / "openclaw" / "canvas-homework-monitor" / "actionable-state.json"
DEFAULT_SUPPRESSION_STATE_PATH = Path.home() / ".local" / "share" / "openclaw" / "canvas-homework-monitor" / "suppressed-items.json"
DEFAULT_ACTIONABLE_LOG_PATH = Path.home() / ".local" / "share" / "openclaw" / "canvas-homework-monitor" / "last-actionable-report.json"
LOGIN_USER_SELECTORS = [
    "input[name='pseudonym_session[unique_id]']",
    "#pseudonym_session_unique_id",
    "input[type='email']",
    "input[name='username']",
    "input[name='loginfmt']",
    "input[autocomplete='username']",
]
LOGIN_PASS_SELECTORS = [
    "input[name='pseudonym_session[password]']",
    "#pseudonym_session_password",
    "input[type='password']",
    "input[name='passwd']",
    "input[autocomplete='current-password']",
]
LOGIN_SUBMIT_SELECTORS = [
    "button[type='submit']",
    "input[type='submit']",
    "button:has-text('Log In')",
    "button:has-text('Sign In')",
    "button:has-text('Next')",
]


class CanvasError(RuntimeError):
    pass


@dataclass
class AssignmentStatus:
    student_name: str
    course_name: str
    module_name: str
    title: str
    item_type: str
    status: str
    due_at: str | None
    html_url: str | None
    details: dict[str, Any]


@dataclass
class CourseGrade:
    student_name: str
    course_name: str
    current_grade: str | None
    current_score: float | None
    final_grade: str | None
    final_score: float | None
    html_url: str | None


def expand_path(value: str | None) -> Path | None:
    if not value:
        return None
    return Path(value).expanduser()


def load_config(path: Path) -> dict[str, Any]:
    config = json.loads(path.read_text())
    config.setdefault("timezone", "America/New_York")
    config.setdefault("headless", True)
    config.setdefault("storage_state_path", str(DEFAULT_STATE_PATH))
    config.setdefault("notification_state_path", str(DEFAULT_NOTIFICATION_STATE_PATH))
    config.setdefault("suppression_state_path", str(DEFAULT_SUPPRESSION_STATE_PATH))
    config.setdefault("actionable_log_path", str(DEFAULT_ACTIONABLE_LOG_PATH))
    config.setdefault("lookahead_days", 2)
    config.setdefault("recent_past_days", 14)
    config.setdefault("course_name_allowlist", [])
    config.setdefault("course_name_blocklist", [])
    return config


def resolve_secret(config: dict[str, Any], key: str) -> str | None:
    value = config.get(key)
    if value:
        return value
    env_key = config.get(f"{key}_env")
    if env_key:
        return os.environ.get(env_key)
    return None


def find_first(page, selectors: list[str], timeout_ms: int = 1500):
    for selector in selectors:
        locator = page.locator(selector)
        try:
            if locator.first.is_visible(timeout=timeout_ms):
                return locator.first
        except Exception:
            continue
    return None


LINK_RE = re.compile(r'<([^>]+)>;\s*rel="([^"]+)"')


def parse_next_link(link_header: str | None) -> str | None:
    if not link_header:
        return None
    for url, rel in LINK_RE.findall(link_header):
        if rel == "next":
            return url
    return None


JS_FETCH = """
async ({ path, absoluteUrl }) => {
  const target = absoluteUrl || path;
  const resp = await fetch(target, { credentials: 'include' });
  const text = await resp.text();
  return {
    ok: resp.ok,
    status: resp.status,
    statusText: resp.statusText,
    text,
    link: resp.headers.get('link') || resp.headers.get('Link'),
    finalUrl: resp.url,
  };
}
"""


def api_get_all(page, base_url: str, path: str) -> list[dict[str, Any]]:
    results: list[dict[str, Any]] = []
    next_path: str | None = path
    while next_path:
        absolute = next_path.startswith("http://") or next_path.startswith("https://")
        payload = page.evaluate(JS_FETCH, {"path": next_path, "absoluteUrl": next_path if absolute else None})
        if not payload["ok"]:
            raise CanvasError(f"Canvas API request failed: {payload['status']} {payload['statusText']} for {next_path}")
        data = json.loads(payload["text"])
        if isinstance(data, list):
            results.extend(data)
        elif isinstance(data, dict):
            results.append(data)
        else:
            raise CanvasError(f"Unexpected API payload for {next_path}: {type(data).__name__}")
        next_link = parse_next_link(payload.get("link"))
        if next_link and next_link.startswith(base_url):
            next_path = next_link
        else:
            next_path = next_link
    return results


def login_if_needed(page, config: dict[str, Any], base_url: str) -> None:
    username = resolve_secret(config, "username")
    password = resolve_secret(config, "password")
    if not username or not password:
        raise CanvasError("Missing Canvas credentials. Set username/password directly in config or provide username_env/password_env.")

    page.goto(base_url, wait_until="domcontentloaded", timeout=60000)
    try:
        page.wait_for_load_state("networkidle", timeout=10000)
    except PlaywrightTimeoutError:
        pass

    # Already logged in?
    if page.evaluate(JS_FETCH, {"path": "/api/v1/users/self", "absoluteUrl": None})["status"] == 200:
        return

    user_field = find_first(page, LOGIN_USER_SELECTORS, timeout_ms=2000)
    if user_field is None:
        raise CanvasError("Could not find a username field on the Canvas login page. This school may require SSO/MFA that needs the attached-browser fallback.")

    user_field.fill(username)

    password_field = find_first(page, LOGIN_PASS_SELECTORS, timeout_ms=1500)
    if password_field is None:
        submit = find_first(page, LOGIN_SUBMIT_SELECTORS, timeout_ms=1500)
        if submit is not None:
            submit.click()
        page.wait_for_timeout(1000)
        password_field = find_first(page, LOGIN_PASS_SELECTORS, timeout_ms=5000)
    if password_field is None:
        raise CanvasError("Could not find a password field on the login flow. This likely needs the attached-browser fallback.")

    password_field.fill(password)
    submit = find_first(page, LOGIN_SUBMIT_SELECTORS, timeout_ms=2000)
    if submit is None:
        raise CanvasError("Could not find a login submit button.")
    submit.click()

    try:
        page.wait_for_load_state("networkidle", timeout=20000)
    except PlaywrightTimeoutError:
        pass

    auth_check = page.evaluate(JS_FETCH, {"path": "/api/v1/users/self", "absoluteUrl": None})
    if auth_check["status"] != 200:
        current_url = page.url
        raise CanvasError(f"Login did not complete successfully (status {auth_check['status']}). Current URL: {current_url}")


def fetch_courses(page, config: dict[str, Any]) -> list[dict[str, Any]]:
    courses = api_get_all(page, config["base_url"], "/api/v1/courses?enrollment_state=active&state[]=available&per_page=100")
    allowlist = [s.lower() for s in config.get("course_name_allowlist", []) if s]
    blocklist = [s.lower() for s in config.get("course_name_blocklist", []) if s]
    filtered = []
    for course in courses:
        name = (course.get("name") or "").strip()
        if not name:
            continue
        lower = name.lower()
        if allowlist and not any(token in lower for token in allowlist):
            continue
        if any(token in lower for token in blocklist):
            continue
        filtered.append(course)
    return filtered


def fetch_observees(page, base_url: str) -> dict[int, str]:
    observees = api_get_all(page, base_url, "/api/v1/users/self/observees?per_page=100")
    results: dict[int, str] = {}
    for observee in observees:
        observee_id = observee.get("id")
        if isinstance(observee_id, int):
            results[observee_id] = observee.get("short_name") or observee.get("name") or f"Student {observee_id}"
    return results


def build_assignment_map(page, base_url: str, course_id: int) -> dict[int, dict[str, Any]]:
    assignments = api_get_all(
        page,
        base_url,
        f"/api/v1/courses/{course_id}/assignments?include[]=submission&order_by=due_at&per_page=100",
    )
    return {int(a["id"]): a for a in assignments if isinstance(a.get("id"), int)}


def fetch_modules(page, base_url: str, course_id: int) -> list[dict[str, Any]]:
    modules = api_get_all(
        page,
        base_url,
        f"/api/v1/courses/{course_id}/modules?include[]=items&include[]=content_details&per_page=100",
    )
    for module in modules:
        if module.get("items") is None and module.get("items_url"):
            items_url = module["items_url"]
            sep = "&" if "?" in items_url else "?"
            module["items"] = api_get_all(page, base_url, f"{items_url}{sep}include[]=content_details&per_page=100")
    return modules


def fetch_course_grades(page, base_url: str, course_id: int) -> dict[int, CourseGrade]:
    enrollments = api_get_all(
        page,
        base_url,
        f"/api/v1/courses/{course_id}/enrollments?type[]=StudentEnrollment&per_page=100",
    )
    grades: dict[int, CourseGrade] = {}
    for enrollment in enrollments:
        user_id = enrollment.get("user_id")
        if not isinstance(user_id, int):
            continue
        grade_info = enrollment.get("grades") or {}
        user = enrollment.get("user") or {}
        grades[user_id] = CourseGrade(
            student_name=user.get("short_name") or user.get("name") or f"Student {user_id}",
            course_name="",
            current_grade=grade_info.get("current_grade"),
            current_score=grade_info.get("current_score"),
            final_grade=grade_info.get("final_grade"),
            final_score=grade_info.get("final_score"),
            html_url=grade_info.get("html_url"),
        )
    return grades


def build_submission_map(page, base_url: str, course_id: int) -> dict[int, dict[int, dict[str, Any]]]:
    grouped_submissions = api_get_all(
        page,
        base_url,
        f"/api/v1/courses/{course_id}/students/submissions?student_ids[]=all&grouped=true&per_page=100",
    )
    by_student: dict[int, dict[int, dict[str, Any]]] = {}
    for group in grouped_submissions:
        user_id = group.get("user_id")
        if not isinstance(user_id, int):
            continue
        submissions: dict[int, dict[str, Any]] = {}
        for submission in group.get("submissions") or []:
            assignment_id = submission.get("assignment_id")
            if isinstance(assignment_id, int):
                submissions[assignment_id] = submission
        by_student[user_id] = submissions
    return by_student


def parse_dt(value: str | None) -> datetime | None:
    if not value:
        return None
    if value.endswith("Z"):
        value = value[:-1] + "+00:00"
    return datetime.fromisoformat(value).astimezone(UTC)


COMPLETED_STATES = {"graded", "submitted", "pending_review", "complete"}


def classify_item(
    *,
    student_name: str,
    course_name: str,
    module_name: str,
    item: dict[str, Any],
    submission: dict[str, Any] | None,
    now_utc: datetime,
    tz: ZoneInfo,
    lookahead_days: int,
    recent_past_days: int,
) -> AssignmentStatus | None:
    item_type = item.get("type") or "Unknown"
    if item_type in {"SubHeader", "ExternalUrl", "ExternalTool", "File", "Page"}:
        return None

    content_details = item.get("content_details") or {}
    due_at = content_details.get("due_at")
    due_dt = parse_dt(due_at)
    submission = submission or {}
    completion = item.get("completion_requirement") or {}
    completed = completion.get("completed")
    submitted_at = parse_dt(submission.get("submitted_at"))
    workflow_state = (submission.get("workflow_state") or "").lower()
    excused = bool(submission.get("excused"))
    missing = bool(submission.get("missing")) or submission.get("late_policy_status") == "missing"
    late = bool(submission.get("late")) or submission.get("late_policy_status") == "late"
    locked = bool(content_details.get("locked_for_user"))

    if excused:
        return None

    overdue_unsubmitted = bool(
        due_dt and due_dt < now_utc and not submitted_at and workflow_state not in COMPLETED_STATES
    )
    recent_due_window = bool(
        due_dt
        and due_dt < now_utc
        and due_dt >= now_utc.replace(microsecond=0) - timedelta(days=recent_past_days)
    )
    recent_overdue_incomplete = bool(
        recent_due_window and not submitted_at and workflow_state not in COMPLETED_STATES
    )
    due_today_incomplete = bool(
        due_dt
        and due_dt.astimezone(tz).date() == now_utc.astimezone(tz).date()
        and (completed is False or workflow_state not in COMPLETED_STATES)
    )
    due_soon_incomplete = bool(
        due_dt
        and due_dt >= now_utc
        and due_dt <= now_utc.replace(microsecond=0) + timedelta(days=lookahead_days)
        and (completed is False or workflow_state not in COMPLETED_STATES)
    )

    if missing and recent_due_window:
        status = "missing"
    elif late and recent_due_window:
        status = "late"
    elif recent_overdue_incomplete and completed is not True and not locked:
        status = "overdue incomplete"
    elif due_today_incomplete and completed is not True and not locked:
        status = "due today"
    elif due_soon_incomplete and completed is not True and not locked:
        status = f"due within {lookahead_days} days"
    else:
        return None

    html_url = item.get("html_url")
    if html_url and html_url.startswith("/"):
        html_url = urljoin(item.get("url") or "", html_url)

    return AssignmentStatus(
        student_name=student_name,
        course_name=course_name,
        module_name=module_name,
        title=item.get("title") or "Untitled item",
        item_type=item_type,
        status=status,
        due_at=due_at,
        html_url=html_url,
        details={
            "content_id": item.get("content_id"),
            "module_item_id": item.get("id"),
            "workflow_state": workflow_state or None,
            "completed": completed,
            "submitted_at": submission.get("submitted_at"),
            "missing": missing,
            "late": late,
            "overdue_unsubmitted": overdue_unsubmitted,
            "locked_for_user": locked,
        },
    )


def dedupe_statuses(items: list[AssignmentStatus]) -> list[AssignmentStatus]:
    seen: set[tuple[str, str, str]] = set()
    deduped: list[AssignmentStatus] = []
    for item in items:
        key = (item.student_name, item.course_name, item.title, item.status)
        if key in seen:
            continue
        seen.add(key)
        deduped.append(item)
    return deduped


def format_summary(label: str, items: list[AssignmentStatus], tz: ZoneInfo) -> str:
    if not items:
        return f"{label}: no missing, late, overdue, or due-today incomplete Canvas work found."

    lines = [f"{label} — actionable Canvas work for tonight:"]
    current_student = None
    current_course = None
    for item in items:
        if item.student_name != current_student:
            current_student = item.student_name
            current_course = None
            lines.append("")
            lines.append(f"{current_student}")
        if item.course_name != current_course:
            current_course = item.course_name
            lines.append("")
            lines.append(f"{current_course}")
        due_part = ""
        if item.due_at:
            due_dt = parse_dt(item.due_at)
            if due_dt:
                due_local = due_dt.astimezone(tz)
                due_part = f" — due {due_local.strftime('%a %-m/%-d %-I:%M%p')}"
        link_part = f" — {item.html_url}" if item.html_url else ""
        lines.append(f"- [{item.status}] {item.title}{due_part}{link_part}")
    return "\n".join(lines)


def format_grade(value_grade: str | None, value_score: float | None) -> str:
    prefix = "🔴 " if value_score is not None and value_score < 80 else ""
    if value_grade and value_score is not None:
        return f"{prefix}{value_grade} ({value_score:.2f}%)"
    if value_grade:
        return f"{prefix}{value_grade}"
    if value_score is not None:
        return f"{prefix}{value_score:.2f}%"
    return "n/a"


def format_grades_summary(label: str, grades: list[CourseGrade]) -> str:
    if not grades:
        return f"{label} — current grades:\n\nNo course grades available."

    lines = [f"{label} — current grades:"]
    current_student = None
    for grade in grades:
        if grade.student_name != current_student:
            current_student = grade.student_name
            lines.append("")
            lines.append(f"{current_student}")
        lines.append(f"- {grade.course_name}: {format_grade(grade.current_grade, grade.current_score)}")
    return "\n".join(lines)


def status_key(item: AssignmentStatus) -> str:
    content_id = item.details.get("content_id")
    return "|".join(
        [
            item.student_name,
            item.course_name,
            str(content_id) if content_id is not None else item.title,
            item.status,
            item.due_at or "",
        ]
    )


def load_notification_keys(path: Path) -> set[str]:
    if not path.exists():
        return set()
    try:
        payload = json.loads(path.read_text())
    except Exception:
        return set()
    keys = payload.get("keys") or []
    return {key for key in keys if isinstance(key, str)}


def save_notification_keys(path: Path, items: list[AssignmentStatus], checked_at: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    payload = {
        "checked_at": checked_at,
        "keys": sorted(status_key(item) for item in items),
    }
    path.write_text(json.dumps(payload, indent=2))


def load_suppressed_keys(path: Path) -> set[str]:
    if not path.exists():
        return set()
    try:
        payload = json.loads(path.read_text())
    except Exception:
        return set()
    keys = payload.get("suppressed_keys") or []
    return {key for key in keys if isinstance(key, str)}


def save_actionable_log(path: Path, checked_at: str, items: list[AssignmentStatus]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    payload = {
        "checked_at": checked_at,
        "items": [
            {
                "suppress_key": status_key(item),
                "student_name": item.student_name,
                "course_name": item.course_name,
                "module_name": item.module_name,
                "title": item.title,
                "item_type": item.item_type,
                "status": item.status,
                "due_at": item.due_at,
                "html_url": item.html_url,
                "details": item.details,
            }
            for item in items
        ],
    }
    path.write_text(json.dumps(payload, indent=2))


def run(config_path: Path) -> dict[str, Any]:
    config = load_config(config_path)
    base_url = config["base_url"].rstrip("/")
    tz = ZoneInfo(config.get("timezone", "America/New_York"))
    state_path = expand_path(config.get("storage_state_path")) or DEFAULT_STATE_PATH
    notification_state_path = expand_path(config.get("notification_state_path")) or DEFAULT_NOTIFICATION_STATE_PATH
    suppression_state_path = expand_path(config.get("suppression_state_path")) or DEFAULT_SUPPRESSION_STATE_PATH
    actionable_log_path = expand_path(config.get("actionable_log_path")) or DEFAULT_ACTIONABLE_LOG_PATH
    state_path.parent.mkdir(parents=True, exist_ok=True)

    now_utc = datetime.now(UTC)
    with sync_playwright() as p:
        browser = p.chromium.launch(
            headless=bool(config.get("headless", True)),
            executable_path=config.get("browser_executable") or "/snap/bin/chromium",
            args=["--no-sandbox"],
        )
        context_kwargs: dict[str, Any] = {}
        if state_path.exists():
            context_kwargs["storage_state"] = str(state_path)
        context = browser.new_context(**context_kwargs)
        page = context.new_page()
        try:
            login_if_needed(page, config, base_url)
            context.storage_state(path=str(state_path))
            observees = fetch_observees(page, base_url)
            courses = fetch_courses(page, config)
            actionable: list[AssignmentStatus] = []
            course_grades: list[CourseGrade] = []
            warnings: list[str] = []
            for course in courses:
                course_id = course.get("id")
                if not isinstance(course_id, int):
                    continue
                course_name = course.get("name") or f"Course {course_id}"
                enrollments = course.get("enrollments") or []
                associated_user_ids = [
                    enrollment.get("associated_user_id")
                    for enrollment in enrollments
                    if isinstance(enrollment.get("associated_user_id"), int)
                ]
                try:
                    modules = fetch_modules(page, base_url, course_id)
                    submissions_by_student = build_submission_map(page, base_url, course_id)
                    grades_by_student = fetch_course_grades(page, base_url, course_id)
                except CanvasError as exc:
                    warnings.append(f"{course_name}: {exc}")
                    continue

                candidate_user_ids = associated_user_ids or list(submissions_by_student.keys())
                if not candidate_user_ids and len(observees) == 1:
                    candidate_user_ids = list(observees.keys())

                for user_id in candidate_user_ids:
                    grade = grades_by_student.get(user_id)
                    if grade:
                        grade.course_name = course_name
                        if not any(g.student_name == grade.student_name and g.course_name == grade.course_name for g in course_grades):
                            course_grades.append(grade)

                for module in modules:
                    module_name = module.get("name") or "Module"
                    for item in module.get("items") or []:
                        content_id = item.get("content_id")
                        if not isinstance(content_id, int):
                            continue
                        for user_id in candidate_user_ids:
                            student_name = observees.get(user_id, f"Student {user_id}")
                            submission = (submissions_by_student.get(user_id) or {}).get(content_id)
                            classified = classify_item(
                                student_name=student_name,
                                course_name=course_name,
                                module_name=module_name,
                                item=item,
                                submission=submission,
                                now_utc=now_utc,
                                tz=tz,
                                lookahead_days=int(config.get("lookahead_days", 2)),
                                recent_past_days=int(config.get("recent_past_days", 14)),
                            )
                            if classified:
                                actionable.append(classified)
        finally:
            context.close()
            browser.close()

    actionable = sorted(
        dedupe_statuses(actionable),
        key=lambda x: (
            x.student_name.lower(),
            x.course_name.lower(),
            parse_dt(x.due_at) or datetime.max.replace(tzinfo=UTC),
            x.title.lower(),
        ),
    )
    suppressed_keys = load_suppressed_keys(suppression_state_path)
    actionable = [item for item in actionable if status_key(item) not in suppressed_keys]
    previous_notification_keys = load_notification_keys(notification_state_path)
    new_actionable = [item for item in actionable if status_key(item) not in previous_notification_keys]
    save_notification_keys(notification_state_path, actionable, now_utc.isoformat())
    save_actionable_log(actionable_log_path, now_utc.isoformat(), actionable)
    course_grades = sorted(course_grades, key=lambda x: (x.student_name.lower(), x.course_name.lower()))
    payload = {
        "student_name": config.get("student_name", "Student"),
        "observees": observees,
        "base_url": base_url,
        "checked_at": now_utc.isoformat(),
        "timezone": str(tz),
        "count": len(actionable),
        "new_count": len(new_actionable),
        "suppressed_count": len(suppressed_keys),
        "warnings": warnings,
        "grades": [
            {
                "student_name": grade.student_name,
                "course_name": grade.course_name,
                "current_grade": grade.current_grade,
                "current_score": grade.current_score,
                "final_grade": grade.final_grade,
                "final_score": grade.final_score,
                "html_url": grade.html_url,
            }
            for grade in course_grades
        ],
        "items": [
            {
                "suppress_key": status_key(item),
                "student_name": item.student_name,
                "course_name": item.course_name,
                "module_name": item.module_name,
                "title": item.title,
                "item_type": item.item_type,
                "status": item.status,
                "due_at": item.due_at,
                "html_url": item.html_url,
                "details": item.details,
            }
            for item in actionable
        ],
        "new_items": [
            {
                "suppress_key": status_key(item),
                "student_name": item.student_name,
                "course_name": item.course_name,
                "module_name": item.module_name,
                "title": item.title,
                "item_type": item.item_type,
                "status": item.status,
                "due_at": item.due_at,
                "html_url": item.html_url,
                "details": item.details,
            }
            for item in new_actionable
        ],
        "grades_summary": format_grades_summary(config.get("student_name", "Student"), course_grades),
        "summary": format_summary(config.get("student_name", "Student"), actionable, tz),
        "new_summary": format_summary(config.get("student_name", "Student"), new_actionable, tz),
    }
    return payload


def main() -> int:
    parser = argparse.ArgumentParser(description="Check Canvas modules for missing or incomplete homework.")
    parser.add_argument("--config", required=True, help="Path to the JSON config file")
    parser.add_argument("--json", action="store_true", help="Print full JSON payload (default)")
    parser.add_argument("--summary", action="store_true", help="Print only the summary text")
    parser.add_argument("--new-only", action="store_true", help="Print only newly-actionable items since the last run")
    args = parser.parse_args()

    try:
        payload = run(Path(args.config).expanduser())
    except Exception as exc:
        print(json.dumps({"error": str(exc)}, indent=2), file=sys.stderr)
        return 1

    if args.summary:
        print(payload["new_summary"] if args.new_only else payload["summary"])
    else:
        print(json.dumps(payload, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
