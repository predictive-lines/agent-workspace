# Canvas homework monitor setup

## 1. Private config

Keep the live config outside the workspace so it does not get injected into normal prompts.

Recommended path:

```bash
mkdir -p ~/.config/canvas-homework-monitor
cp ~/.openclaw/workspace/skills/canvas-homework-monitor/references/config-template.json \
  ~/.config/canvas-homework-monitor/dcds-parent.json
```

Then edit `~/.config/canvas-homework-monitor/dcds-parent.json` with the real Canvas base URL.

## 2. Credentials

Set credentials in the shell environment that launches OpenClaw, or store them in a private sourced file.

Example private file:

```bash
mkdir -p ~/.config/canvas-homework-monitor
cat > ~/.config/canvas-homework-monitor/env.sh <<'SH'
export CANVAS_HOMEWORK_USERNAME='coraline-login'
export CANVAS_HOMEWORK_PASSWORD='replace-me'
SH
chmod 600 ~/.config/canvas-homework-monitor/env.sh
```

If OpenClaw needs those vars persistently, load that file from the launcher/service unit rather than from a workspace file.

## 3. Smoke test the scraper

```bash
source ~/.config/canvas-homework-monitor/env.sh
python3 ~/.openclaw/workspace/skills/canvas-homework-monitor/scripts/check_canvas_homework.py \
  --config ~/.config/canvas-homework-monitor/dcds-parent.json \
  --summary
```

Expected outcomes:

- Success: prints a short homework digest.
- Failure with login-field error: the school probably uses SSO/MFA and the skill should fall back to the attached `chromium-user` browser path.

For scheduled runs, prefer the delta mode so Justin only gets *new* actionable items:

```bash
python3 ~/.openclaw/workspace/skills/canvas-homework-monitor/scripts/check_canvas_homework.py \
  --config ~/.config/canvas-homework-monitor/dcds-parent.json \
  --summary --new-only
```

The default DCDS tuning is:

- upcoming work due in the next `2` days
- overdue/missing/late work only if the due date was within the last `14` days

To suppress a known false-positive or teacher-lag assignment across future runs:

1. find its `suppress_key` in `~/.local/share/openclaw/canvas-homework-monitor/last-actionable-report.json`
2. add that key to `~/.local/share/openclaw/canvas-homework-monitor/suppressed-items.json`

Example suppression file:

```json
{
  "suppressed_keys": [
    "Cora Miller|ALGEBRA 1 - MMA8RT - Nash + Haataja - 25/26|485846|due within 2 days|2026-05-01T03:59:59Z"
  ]
}
```

Helper commands instead of hand-editing JSON:

```bash
python3 ~/.openclaw/workspace/skills/canvas-homework-monitor/scripts/suppress_canvas_assignment.py --list
python3 ~/.openclaw/workspace/skills/canvas-homework-monitor/scripts/suppress_canvas_assignment.py --find "POV Sketch"
python3 ~/.openclaw/workspace/skills/canvas-homework-monitor/scripts/suppress_canvas_assignment.py --add-index 8
python3 ~/.openclaw/workspace/skills/canvas-homework-monitor/scripts/suppress_canvas_assignment.py --show-suppressed
```

The `--list` output is numbered from the current actionable log, so `--add-index <n>` is usually the fastest path after a fresh report.

## 4. Daily cron job

Use an isolated cron run so the job gets a clean turn every day.

Template:

```bash
openclaw cron add \
  --name "DCDS Canvas homework check" \
  --cron "30 16 * * 1-5" \
  --tz "America/New_York" \
  --session isolated \
  --message "Use the canvas-homework-monitor skill. Run the DCDS parent-account Canvas homework check and notify only when there are new missing, late, overdue, or due-today incomplete assignments. Group the message by student, then by course, and include assignment name, due time, status, and direct Canvas link." \
  --announce \
  --channel slack \
  --to "channel:C0AUCS0TF6W"
```

Adjust the cron expression to match the real check time. If you want direct messages instead, swap the `--to` target back to `user:JUSTIN_SLACK_USER_ID`. If you want failures to land in the same channel, set the job's failure-alert target to that same channel too.

## 5. Manual rerun / inspection

```bash
openclaw cron list
openclaw cron run <job-id>
openclaw cron runs --id <job-id> --limit 20
```
