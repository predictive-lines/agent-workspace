---
name: canvas-homework-monitor
description: >
  Check a student's Canvas LMS courses for upcoming or recently overdue incomplete work and report the actionable items to Justin. Use when Justin wants to build, run, debug, or schedule Coraline homework monitoring; when a cron job should do the daily Canvas sweep; or when Canvas login/scraping needs to fall back from headless automation to the attached Chromium browser.
---

# canvas-homework-monitor

Use this skill to run a daily Canvas homework check and wire it into OpenClaw cron.

## Default approach

Prefer the deterministic headless script first:

```bash
python3 ~/.openclaw/workspace/skills/canvas-homework-monitor/scripts/check_canvas_homework.py \
  --config ~/.config/canvas-homework-monitor/coraline.json
```

The script:

- logs into Canvas with Playwright using private credentials
- reuses a saved browser storage-state file between runs
- supports both direct student logins and parent/observer accounts
- fetches active courses, modules, and observer submission state through Canvas's own authenticated API
- flags work that is `missing`, `late`, `overdue incomplete` from the last 14 days, `due today`, or `due within 2 days`
- captures current course grades when Canvas exposes them to the observer account
- returns JSON plus a human-readable summary
- tracks prior actionable items so cron can alert only on *new* homework issues
- writes a local actionable-items log with stable `suppress_key` values so specific assignments can be muted across future runs

## Workflow

### 1. Confirm config and secrets

Read `references/setup.md` if the config file or cron job has not been created yet.

Live config should stay outside the workspace at:

- `~/.config/canvas-homework-monitor/<student-or-school>.json`
- credentials in env vars referenced by that config

Use `references/config-template.json` as the starting point.

### 2. Run the headless check

Run the script with `--summary` for a quick read or default JSON when you need structured output.
Use `--new-only --summary` for cron-style notification runs.

Examples:

```bash
python3 ~/.openclaw/workspace/skills/canvas-homework-monitor/scripts/check_canvas_homework.py \
  --config ~/.config/canvas-homework-monitor/coraline.json \
  --summary
```

```bash
python3 ~/.openclaw/workspace/skills/canvas-homework-monitor/scripts/check_canvas_homework.py \
  --config ~/.config/canvas-homework-monitor/dcds-parent.json \
  --summary --new-only
```

```bash
python3 ~/.openclaw/workspace/skills/canvas-homework-monitor/scripts/check_canvas_homework.py \
  --config ~/.config/canvas-homework-monitor/coraline.json
```

If the script succeeds, send Justin a concise digest with:

- class / course name
- assignment name
- status (`missing`, `late`, `overdue incomplete`, `due today`, or `due within 2 days`)
- due time when available
- direct Canvas link

Also include a separate current-grades block grouped by student when grade data is available.

For local review/debugging, inspect:

- `~/.local/share/openclaw/canvas-homework-monitor/last-actionable-report.json`

Each actionable item includes a `suppress_key`. Add any key that should be muted day-to-day to:

- `~/.local/share/openclaw/canvas-homework-monitor/suppressed-items.json`

Helper script:

```bash
python3 ~/.openclaw/workspace/skills/canvas-homework-monitor/scripts/suppress_canvas_assignment.py --list
python3 ~/.openclaw/workspace/skills/canvas-homework-monitor/scripts/suppress_canvas_assignment.py --find "POV Sketch"
python3 ~/.openclaw/workspace/skills/canvas-homework-monitor/scripts/suppress_canvas_assignment.py --add-index 8
```

If nothing is actionable, keep the reply short.

### 3. Fall back only if headless fails

If the script errors because the login flow uses SSO, MFA, or weird interstitials, switch to the attached browser path.

Rules for fallback:

- use the `browser` tool with `profile: "chromium-user"`, `target: "host"`
- keep the same `targetId` across the flow
- use `refs: "aria"` and `snapshotFormat: "aria"`
- if the flow is more than a trivial click path, load the `browser-automation` skill before continuing

Goal of the fallback is not to manually scrape forever. Use it to understand the login flow, get selectors right, or prove that a storage-state session can be established, then bring the deterministic script back into service.

### 4. Schedule it with cron

Use an isolated cron job, not heartbeat. The job prompt should explicitly mention this skill and tell the agent to send Justin a message only when there is *new* actionable work.

Use the command pattern in `references/setup.md`.

## Reporting standard

When reporting results to Justin, format compactly by student, then course. Example shape:

```text
DCDS kids — actionable Canvas work for tonight:

Cora Miller

Algebra
- [missing] Module 8 Practice — due Tue 4/29 11:59PM — https://...

Genevieve Miller

English
- [late] Vocabulary Quiz 12 — due Mon 4/28 3:00PM — https://...
```

## Safety / privacy

- never put live credentials in the workspace skill files
- keep the live config in `~/.config/canvas-homework-monitor/`
- prefer env vars for username/password
- if the school requires interactive approval or MFA that cannot be automated safely, stop and ask Justin rather than hacking around it

## Files

- `scripts/check_canvas_homework.py` — headless Canvas login + API-based homework detection
- `scripts/suppress_canvas_assignment.py` — helper to list/search/suppress specific actionable assignments
- `references/config-template.json` — private-config starting point
- `references/setup.md` — smoke test + cron wiring notes
