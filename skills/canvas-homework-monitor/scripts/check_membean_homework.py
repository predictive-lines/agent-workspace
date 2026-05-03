#!/usr/bin/env python3
"""Check a Membean student's weekly session progress.

Companion to ``check_canvas_homework.py``. Designed to be merged into the
overall homework digest:

- A Membean Canvas assignment counts as **complete for the week** as long as
  the student logs at least 15 cumulative minutes of training on at least
  3 distinct days during the Monday-Sunday window (per Justin).
- Once the weekly threshold is hit, downstream code can suppress any
  Membean-related Canvas items for that week.
- If the threshold has not been hit yet, we surface a status that says how
  many *more* days they still need and how many days remain in the week,
  so we can warn loudly when the runway is getting tight.

This script handles auth via Google SSO using Membean's "Sign in with Google"
button, with credentials pulled from Bitwarden via the ``_bitwarden`` helper.
First-run requires an interactive (``--init``) step where the user completes
the Google SSO + MFA flow once; the resulting Playwright storage state is
saved and reused by all subsequent headless runs.

Output shape mirrors ``check_canvas_homework.py`` (dataclass-based, JSON
serializable).
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from collections import defaultdict
from dataclasses import dataclass, field
from datetime import UTC, date, datetime, timedelta
from pathlib import Path
from typing import Any
from zoneinfo import ZoneInfo

from playwright.sync_api import TimeoutError as PlaywrightTimeoutError
from playwright.sync_api import sync_playwright

# Allow ``import _bitwarden`` when invoked from any CWD.
_HERE = Path(__file__).resolve().parent
if str(_HERE) not in sys.path:
    sys.path.insert(0, str(_HERE))

from _bitwarden import BitwardenError, get_login  # noqa: E402

DEFAULT_STATE_DIR = Path.home() / ".local" / "share" / "openclaw" / "canvas-homework-monitor"
DEFAULT_LOGIN_URL = "https://membean.com/login"
# /dashboard is the authenticated student landing page; the bare / URL is the
# marketing site, which Membean serves even to authenticated requests.
DEFAULT_DASHBOARD_URL = "https://membean.com/dashboard"
WEEKLY_MINUTES_PER_DAY = 15
WEEKLY_DAYS_REQUIRED = 3


class MembeanError(RuntimeError):
    pass


@dataclass
class DayStatus:
    iso_date: str
    minutes: float
    sessions: int
    hit_threshold: bool


@dataclass
class WeeklyStatus:
    student_name: str
    week_start: str  # Monday (YYYY-MM-DD)
    week_end: str    # Sunday
    days: list[DayStatus]
    days_hit: int
    days_remaining: int
    minutes_today: float
    today_iso: str
    week_complete: bool
    status: str               # "complete" | "on_track" | "warning" | "at_risk" | "impossible"
    headline: str             # short human description
    detail_lines: list[str] = field(default_factory=list)
    raw: dict[str, Any] = field(default_factory=dict)


# ---------------------------------------------------------------------------
# Config
# ---------------------------------------------------------------------------


def load_config(path: Path) -> dict[str, Any]:
    config = json.loads(path.read_text())
    config.setdefault("timezone", "America/New_York")
    config.setdefault("login_url", DEFAULT_LOGIN_URL)
    config.setdefault("dashboard_url", DEFAULT_DASHBOARD_URL)
    # Default browser_executable to None so Playwright uses its own bundled
    # Chromium. The snap-packaged /snap/bin/chromium does not launch cleanly
    # under Playwright in headed mode.
    config.setdefault("browser_executable", None)
    config.setdefault("headless", True)
    config.setdefault("weekly_minutes_per_day", WEEKLY_MINUTES_PER_DAY)
    config.setdefault("weekly_days_required", WEEKLY_DAYS_REQUIRED)
    student_slug = (config.get("student_name") or "student").lower().replace(" ", "-")
    config.setdefault(
        "dashboard_dump_path",
        str(DEFAULT_STATE_DIR / f"membean-{student_slug}-debug-dashboard.html"),
    )
    config.setdefault(
        "storage_state_path",
        str(DEFAULT_STATE_DIR / f"membean-{student_slug}-storage-state.json"),
    )
    config.setdefault(
        "captured_url_path",
        str(DEFAULT_STATE_DIR / f"membean-{student_slug}-captured-url.txt"),
    )
    return config


def expand_path(value: str | None) -> Path | None:
    if not value:
        return None
    return Path(value).expanduser()


# ---------------------------------------------------------------------------
# Login
# ---------------------------------------------------------------------------


def login_with_google(page, *, email: str, password: str, login_url: str) -> None:
    """Drive Membean's "Sign in with Google" flow.

    This is the brittle part: Google's auth screens change shape often
    (account picker vs fresh login, MFA prompts, school SSO interstitials,
    consent screens). We do a best-effort happy path and rely on the
    interactive ``--init`` flow when humans need to intervene.
    """

    page.goto(login_url, wait_until="domcontentloaded", timeout=60000)
    try:
        page.wait_for_load_state("networkidle", timeout=10000)
    except PlaywrightTimeoutError:
        pass

    # Membean usually labels the button "Sign in with Google" or shows a Google G icon.
    google_button = None
    candidates = [
        "button:has-text('Sign in with Google')",
        "a:has-text('Sign in with Google')",
        "button:has-text('Continue with Google')",
        "a:has-text('Continue with Google')",
        "[aria-label='Sign in with Google']",
        "img[alt*='Google' i]",
    ]
    for selector in candidates:
        loc = page.locator(selector).first
        try:
            if loc.is_visible(timeout=1500):
                google_button = loc
                break
        except Exception:
            continue
    if google_button is None:
        raise MembeanError(
            "Could not find a 'Sign in with Google' control on the Membean login page. "
            "Re-run with --init so a human can complete the flow once."
        )

    with page.expect_navigation(wait_until="domcontentloaded", timeout=30000):
        google_button.click()

    # Now we're on accounts.google.com (or a school SSO interstitial).
    _drive_google_login(page, email=email, password=password)

    # Wait until we land back on Membean.
    deadline = datetime.now(UTC) + timedelta(seconds=60)
    while datetime.now(UTC) < deadline:
        if "membean.com" in (page.url or ""):
            return
        page.wait_for_timeout(500)
    raise MembeanError(
        f"Did not return to membean.com after Google sign-in; last URL was {page.url!r}. "
        "Re-run with --init."
    )


def _drive_google_login(page, *, email: str, password: str) -> None:
    """Best-effort email + password fill. Bails out if MFA / SSO interstitial appears."""

    # Email step.
    email_field = None
    for sel in ["input[type='email']", "#identifierId", "input[name='identifier']"]:
        loc = page.locator(sel).first
        try:
            if loc.is_visible(timeout=4000):
                email_field = loc
                break
        except Exception:
            continue
    if email_field is None:
        raise MembeanError(
            "Could not find Google email field. Likely already signed in via account picker, "
            "or the school SSO is forcing a different flow. Re-run with --init."
        )
    email_field.fill(email)
    _click_first(
        page,
        ["#identifierNext button", "button:has-text('Next')", "input[type='submit']"],
    )

    # Password step.
    page.wait_for_timeout(800)
    pw_field = None
    for sel in ["input[type='password']", "input[name='Passwd']"]:
        loc = page.locator(sel).first
        try:
            if loc.is_visible(timeout=8000):
                pw_field = loc
                break
        except Exception:
            continue
    if pw_field is None:
        raise MembeanError(
            "Could not find Google password field. Likely a school SSO redirect or MFA. "
            "Re-run with --init."
        )
    pw_field.fill(password)
    _click_first(
        page,
        ["#passwordNext button", "button:has-text('Next')", "input[type='submit']"],
    )

    # If MFA / consent shows up we just bail; --init will let a human handle it.
    page.wait_for_timeout(2000)


def _click_first(page, selectors: list[str]) -> None:
    for sel in selectors:
        loc = page.locator(sel).first
        try:
            if loc.is_visible(timeout=1500):
                loc.click()
                return
        except Exception:
            continue


# ---------------------------------------------------------------------------
# Dashboard scraping (placeholder until we map the real DOM)
# ---------------------------------------------------------------------------


EXPECT_DESC_RE = re.compile(
    r"(?P<days>\d+)\s+days?\s+with\s+(?P<minutes>\d+)\+\s*minutes?\s+of\s+training",
    re.IGNORECASE,
)
EXPECT_DAYS_RE = re.compile(
    r"(?P<hit>\d+)\s*/\s*(?P<total>\d+)\s+days\s+trained\s+had\s+(?P<minutes>\d+)\+\s*min",
    re.IGNORECASE,
)
TOTAL_MINUTES_RE = re.compile(
    r"(?P<total>\d+)\s+total\s+minutes?\s+of\s+training", re.IGNORECASE
)
SESSION_HEADER_RE = re.compile(
    r'training-session-(?P<id>\d+)-title">(?P<label>[^<]+)</h3>'
)
SESSION_TIME_RE = re.compile(
    r'<time[^>]*datetime="(?P<dt>[^"]+)"'
)
SESSION_MINUTES_RE = re.compile(
    r'<span class="minutes-trained">(?P<m>\d+)\s*minutes?', re.IGNORECASE
)


def parse_dashboard(html: str) -> dict[str, Any]:
    """Pull weekly progress data from the Membean dashboard HTML.

    Returns a dict with keys:

    - ``goal_days`` (int): days the student is expected to train this week
    - ``goal_minutes_per_day`` (int): minutes per day required to count
    - ``days_hit_reported`` (int | None): days Membean says they have hit
    - ``total_minutes_reported`` (int | None): total minutes Membean reports
    - ``goal_reached_text`` (str | None): the green "Goal Reached!" line if present
    - ``sessions`` (list of dicts): per-session iso_date / minutes / id / label
    - ``minutes_by_day`` (dict[str, float]): aggregated per-day from listed sessions
    """

    desc = EXPECT_DESC_RE.search(html)
    days_block = EXPECT_DAYS_RE.search(html)
    total_block = TOTAL_MINUTES_RE.search(html)
    green = re.search(r'<p class="green-text">([^<]+)</p>', html)

    goal_days = int(desc.group("days")) if desc else 0
    goal_minutes_per_day = int(desc.group("minutes")) if desc else 0
    days_hit_reported = int(days_block.group("hit")) if days_block else None
    days_total_reported = int(days_block.group("total")) if days_block else None
    total_minutes_reported = int(total_block.group("total")) if total_block else None

    sessions: list[dict[str, Any]] = []
    for header in SESSION_HEADER_RE.finditer(html):
        sid = header.group("id")
        label = header.group("label").strip()
        chunk = html[header.end(): header.end() + 1500]
        first_time_match = SESSION_TIME_RE.search(chunk)
        minutes_match = SESSION_MINUTES_RE.search(chunk)
        iso_date: str | None = None
        if first_time_match:
            iso_full = first_time_match.group("dt")
            iso_date = iso_full[:10]
        sessions.append(
            {
                "id": sid,
                "label": label,
                "iso_date": iso_date,
                "minutes": int(minutes_match.group("m")) if minutes_match else 0,
            }
        )

    minutes_by_day: dict[str, float] = defaultdict(float)
    for s in sessions:
        if s["iso_date"]:
            minutes_by_day[s["iso_date"]] += float(s["minutes"])

    return {
        "goal_days": goal_days,
        "goal_minutes_per_day": goal_minutes_per_day,
        "days_hit_reported": days_hit_reported,
        "days_total_reported": days_total_reported,
        "total_minutes_reported": total_minutes_reported,
        "goal_reached_text": green.group(1).strip() if green else None,
        "sessions": sessions,
        "minutes_by_day": dict(minutes_by_day),
    }


def fetch_weekly_data(page, *, dashboard_url: str, dump_path: Path | None) -> dict[str, Any]:
    """Load Membean's student dashboard and parse weekly progress."""

    page.goto(dashboard_url, wait_until="domcontentloaded", timeout=60000)
    try:
        page.wait_for_load_state("networkidle", timeout=15000)
    except PlaywrightTimeoutError:
        pass

    html = page.content()
    if dump_path is not None:
        dump_path.parent.mkdir(parents=True, exist_ok=True)
        dump_path.write_text(html)

    parsed = parse_dashboard(html)
    parsed["raw_html_dumped_to"] = str(dump_path) if dump_path is not None else None
    parsed["url"] = page.url
    return parsed


# ---------------------------------------------------------------------------
# Weekly status math
# ---------------------------------------------------------------------------


def week_window(now_local: datetime) -> tuple[date, date]:
    """Return Monday-Sunday window containing ``now_local`` (date-only)."""
    today = now_local.date()
    monday = today - timedelta(days=today.weekday())  # Monday=0
    sunday = monday + timedelta(days=6)
    return monday, sunday


def compute_status(
    *,
    student_name: str,
    minutes_by_day: dict[str, float],
    now_local: datetime,
    minutes_per_day_threshold: int,
    days_required: int,
    days_hit_override: int | None = None,
    membean_says_complete: bool = False,
) -> WeeklyStatus:
    monday, sunday = week_window(now_local)
    today = now_local.date()

    days: list[DayStatus] = []
    for offset in range(7):
        day = monday + timedelta(days=offset)
        iso = day.isoformat()
        minutes = float(minutes_by_day.get(iso, 0.0))
        days.append(
            DayStatus(
                iso_date=iso,
                minutes=minutes,
                sessions=0,  # filled in once we wire real scrape
                hit_threshold=minutes >= minutes_per_day_threshold,
            )
        )

    derived_days_hit = sum(1 for d in days if d.hit_threshold)
    # Membean's own count is authoritative when available — the displayed
    # session list sometimes omits short or partial sessions that still
    # count toward the goal server-side.
    if days_hit_override is not None:
        days_hit = max(int(days_hit_override), derived_days_hit)
    elif membean_says_complete:
        days_hit = max(derived_days_hit, days_required)
    else:
        days_hit = derived_days_hit

    # Days that *could* still earn a hit: today (if not yet hit) + future days <= sunday.
    today_obj = next((d for d in days if d.iso_date == today.isoformat()), None)
    minutes_today = today_obj.minutes if today_obj else 0.0
    future_days = [d for d in days if date.fromisoformat(d.iso_date) >= today]
    days_remaining = sum(1 for d in future_days if not d.hit_threshold)
    needed = max(0, days_required - days_hit)

    if days_hit >= days_required:
        status = "complete"
        headline = f"{student_name}: Membean ✅ already complete for this week ({days_hit}/{days_required} days)."
    elif needed > days_remaining:
        status = "impossible"
        headline = (
            f"{student_name}: Membean ❌ no longer possible this week — needs {needed} more day(s), "
            f"only {days_remaining} day(s) left in the Mon-Sun window."
        )
    elif needed == days_remaining:
        status = "at_risk"
        headline = (
            f"{student_name}: Membean ⚠️ at risk — needs {needed} more day(s) and that is exactly "
            f"the days remaining (must log ≥{minutes_per_day_threshold} min today AND every remaining day)."
        )
    elif needed >= 2:
        status = "warning"
        headline = (
            f"{student_name}: Membean ⚠️ warning — still needs {needed} more day(s), {days_remaining} left."
        )
    else:
        status = "on_track"
        headline = (
            f"{student_name}: Membean on track — {days_hit}/{days_required} days complete, "
            f"{days_remaining} day(s) still available."
        )

    detail_lines: list[str] = []
    for d in days:
        marker = "✅" if d.hit_threshold else ("•" if date.fromisoformat(d.iso_date) <= today else "·")
        detail_lines.append(f"  {marker} {d.iso_date}: {d.minutes:.0f} min")

    return WeeklyStatus(
        student_name=student_name,
        week_start=monday.isoformat(),
        week_end=sunday.isoformat(),
        days=days,
        days_hit=days_hit,
        days_remaining=days_remaining,
        minutes_today=minutes_today,
        today_iso=today.isoformat(),
        week_complete=days_hit >= days_required,
        status=status,
        headline=headline,
        detail_lines=detail_lines,
    )


# ---------------------------------------------------------------------------
# Run modes
# ---------------------------------------------------------------------------


def _ensure_state_dir(state_path: Path) -> None:
    state_path.parent.mkdir(parents=True, exist_ok=True)


def run_init(config_path: Path) -> int:
    config = load_config(config_path)
    state_path = expand_path(config["storage_state_path"])
    if state_path is None:
        raise MembeanError("storage_state_path is required")
    _ensure_state_dir(state_path)

    bw_item = config.get("bw_item")
    if not bw_item:
        raise MembeanError("Config must set 'bw_item' (e.g. 'DCDS - Cora').")
    creds = get_login(bw_item)
    if not creds.username or not creds.password:
        raise MembeanError(f"Bitwarden item {bw_item!r} is missing username or password.")

    print(f"Opening headed Chromium for {config.get('student_name', 'student')}.")
    print("Complete the Google SSO + Membean sign-in in the window that opens.")
    print("When you are FULLY signed in and looking at the Membean dashboard,")
    print("come back here and press Enter to capture session state.")

    launch_kwargs: dict[str, Any] = {
        "headless": False,
        # Force X11 so a missing/closed Wayland socket (common when running
        # via SSH or X-forwarding) doesn't kill the launch.
        "args": ["--no-sandbox", "--ozone-platform=x11"],
    }
    if config.get("browser_executable"):
        launch_kwargs["executable_path"] = config["browser_executable"]

    with sync_playwright() as p:
        browser = p.chromium.launch(**launch_kwargs)
        context = browser.new_context()
        page = context.new_page()
        page.goto(config["login_url"], wait_until="domcontentloaded", timeout=60000)

        # Manual checkpoint: don't try to auto-detect the dashboard URL.
        # Sign-in passes through Google + a school SSO + maybe MFA, and the
        # browser ends up bouncing through several membean.com URLs before
        # the dashboard truly loads. Asking the human to confirm is far
        # more reliable than URL pattern matching.
        try:
            input(
                f"\n>>> Sign in as {config.get('student_name', 'student')!r} and "
                f"reach the Membean dashboard, then press Enter here to save state... "
            )
        except EOFError:
            context.close()
            browser.close()
            raise MembeanError(
                "--init requires an interactive terminal so you can confirm sign-in."
            )

        # Membean's Google sign-in spawns extra tabs/popups, so the original
        # ``page`` reference can be left behind on /login while the dashboard
        # loads in a different tab. Look across every page in the context
        # and prefer a non-login membean.com URL.
        candidate_pages = list(context.pages)
        dashboard_page = None
        for p in candidate_pages:
            try:
                u = p.url or ""
            except Exception:
                continue
            if "membean.com" in u and "/login" not in u:
                dashboard_page = p
                break
        if dashboard_page is None:
            # Fall back to whichever page is currently focused.
            dashboard_page = page

        url_at_capture = (dashboard_page.url or "").strip() or config["dashboard_url"]

        # Save state regardless of which tab is the dashboard — cookies live on
        # the context, not the page.
        context.storage_state(path=str(state_path))

        # Save the actual URL the human reached so check runs go straight there
        # instead of guessing.
        captured_url_path = expand_path(config.get("captured_url_path"))
        if captured_url_path is not None and "membean.com" in url_at_capture and "/login" not in url_at_capture:
            captured_url_path.parent.mkdir(parents=True, exist_ok=True)
            captured_url_path.write_text(url_at_capture + "\n")

        # Grab a baseline dashboard dump so we can iterate on the scrape.
        dump_path = expand_path(config.get("dashboard_dump_path"))
        if dump_path is not None:
            dump_path.parent.mkdir(parents=True, exist_ok=True)
            try:
                dump_path.write_text(dashboard_page.content())
                print(f"Saved dashboard HTML dump to {dump_path}")
            except Exception as exc:
                print(f"(could not capture dashboard HTML: {exc})")

        context.close()
        browser.close()

    print(f"Saved Playwright storage state to {state_path}")
    print(f"Captured dashboard URL: {url_at_capture}")
    return 0


def run_check(config_path: Path) -> dict[str, Any]:
    config = load_config(config_path)
    tz = ZoneInfo(config["timezone"])
    state_path = expand_path(config["storage_state_path"])
    if state_path is None or not state_path.exists():
        raise MembeanError(
            f"No Playwright storage state at {state_path}. "
            f"Run with --init first to complete the one-time interactive sign-in."
        )

    bw_item = config.get("bw_item")
    if not bw_item:
        raise MembeanError("Config must set 'bw_item' (e.g. 'DCDS - Cora').")
    try:
        creds = get_login(bw_item)
    except BitwardenError as exc:
        raise MembeanError(f"Bitwarden lookup failed for {bw_item!r}: {exc}") from exc
    if not creds.username or not creds.password:
        raise MembeanError(f"Bitwarden item {bw_item!r} is missing username or password.")

    # Prefer the URL we captured during --init when one is available; otherwise
    # fall back to the configured/default dashboard URL.
    dashboard_url = config["dashboard_url"]
    captured_url_path = expand_path(config.get("captured_url_path"))
    if captured_url_path is not None and captured_url_path.exists():
        candidate = captured_url_path.read_text().strip()
        if candidate:
            dashboard_url = candidate

    now_local = datetime.now(tz)

    launch_kwargs: dict[str, Any] = {
        "headless": bool(config.get("headless", True)),
        # Force X11 so headed runs (and headless under odd display configs)
        "args": ["--no-sandbox", "--ozone-platform=x11"],
    }
    if config.get("browser_executable"):
        launch_kwargs["executable_path"] = config["browser_executable"]

    with sync_playwright() as p:
        browser = p.chromium.launch(**launch_kwargs)
        context = browser.new_context(storage_state=str(state_path))
        page = context.new_page()
        try:
            try:
                page.goto(dashboard_url, wait_until="domcontentloaded", timeout=60000)
            except PlaywrightTimeoutError:
                pass

            current = page.url or ""
            if "membean.com" not in current or "/login" in current:
                # Session expired. Try the headless Google flow as a recovery.
                login_with_google(
                    page,
                    email=creds.username or "",
                    password=creds.password or "",
                    login_url=config["login_url"],
                )
                page.goto(dashboard_url, wait_until="domcontentloaded", timeout=60000)
                context.storage_state(path=str(state_path))

            data = fetch_weekly_data(
                page,
                dashboard_url=dashboard_url,
                dump_path=expand_path(config.get("dashboard_dump_path")),
            )
        finally:
            context.close()
            browser.close()

    minutes_by_day = data.get("minutes_by_day") or {}
    # Prefer Membean's own per-day threshold/goal-days numbers when they are
    # present and look sane; fall back to config defaults otherwise. This
    # lets the script adapt automatically if the school changes the assignment.
    threshold = int(
        data.get("goal_minutes_per_day")
        or config.get("weekly_minutes_per_day", WEEKLY_MINUTES_PER_DAY)
    )
    required = int(
        data.get("goal_days") or config.get("weekly_days_required", WEEKLY_DAYS_REQUIRED)
    )
    weekly = compute_status(
        student_name=config.get("student_name", "Student"),
        minutes_by_day=minutes_by_day,
        now_local=now_local,
        minutes_per_day_threshold=threshold,
        days_required=required,
        days_hit_override=data.get("days_hit_reported"),
        membean_says_complete=data.get("goal_reached_text") is not None,
    )
    weekly.raw = data

    return _serialize_weekly(weekly)


def _serialize_weekly(weekly: WeeklyStatus) -> dict[str, Any]:
    return {
        "student_name": weekly.student_name,
        "week_start": weekly.week_start,
        "week_end": weekly.week_end,
        "today_iso": weekly.today_iso,
        "minutes_today": weekly.minutes_today,
        "days_hit": weekly.days_hit,
        "days_remaining": weekly.days_remaining,
        "week_complete": weekly.week_complete,
        "status": weekly.status,
        "headline": weekly.headline,
        "days": [
            {
                "iso_date": d.iso_date,
                "minutes": d.minutes,
                "sessions": d.sessions,
                "hit_threshold": d.hit_threshold,
            }
            for d in weekly.days
        ],
        "detail_lines": weekly.detail_lines,
        "raw": weekly.raw,
    }


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Check a Membean student's weekly session progress."
    )
    parser.add_argument("--config", required=True, help="Path to the JSON config file")
    parser.add_argument(
        "--init",
        action="store_true",
        help="Run the one-time interactive sign-in (headed Chromium) and save Playwright storage state.",
    )
    parser.add_argument("--summary", action="store_true", help="Print a short text summary instead of full JSON.")
    args = parser.parse_args()

    config_path = Path(args.config).expanduser()
    try:
        if args.init:
            return run_init(config_path)
        payload = run_check(config_path)
    except Exception as exc:
        print(json.dumps({"error": str(exc)}, indent=2), file=sys.stderr)
        return 1

    if args.summary:
        print(payload["headline"])
        for line in payload.get("detail_lines", []):
            print(line)
    else:
        print(json.dumps(payload, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
