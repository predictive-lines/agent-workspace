# TOOLS.md - Local Notes

### GitHub

- **Org:** predictive-lines
- **Auth:** Fine-grained PAT stored in `~/.git-credentials`
- **Repos (cloned to ~/repos/):**
  - excel-fire-ai (GitHub: predictive-lines/ai-skills — local folder kept as excel-fire-ai)
  - llm-experimentation
  - openCPQ
  - qb-mcp-server
- **Important:** Always `git pull` before reading repo content — other agents push updates

### Notion

- **Auth:** API key stored in `~/.config/notion/api_key`
- **Root page:** `ai-space` (id: `2ff7e702-d98c-80a9-bf01-d03635e5e5f4`)
- **Skill:** `~/.npm-global/lib/node_modules/openclaw/skills/notion/SKILL.md`
- **API version:** `2025-09-03`
- **Important:** In API v2025-09-03, databases return as `data_source` objects. Use `data_source_id` for queries, `database_id` for creating pages.
- **Databases (data_source_id):**
  - **Resources** (`44285caf-44a4-489b-b04e-4e4f7ba22f87`) — Articles, podcasts, bookmarks
    - Props: Name (title), Category (select: Personal/Work/Fitness/Family/Planning/Finance/Security/AI/etc.)
  - **Tasks** (`2847e702-d98c-8170-9008-000bc7d6d318`) — Personal task list / reminders
    - Props: Task name (title), Status (status: Paused/Not Started/Follow Up Tomorrow/In Progress PM/In Progress AM/Done/Archived), Priority (select: Low/Medium/High), Due (date), Assignee (people), Tags (multi_select), Required By (select), Sub-tasks/Parent-task/Blocks/Blocked By (relations), Completed on (date)

### Google Calendar

- **Auth:** Same OAuth2 as Drive/Sheets (calendar scope added 2026-03-01)
- **Calendars:**
  - `justin.miller@predictivelines.com` — primary
  - `miller-family-calendar@oneoaks.net` — Miller family calendar
  - `en.usa#holiday@group.v.calendar.google.com` — US holidays
- **API:** Google Calendar v3 (`calendar-json.googleapis.com`)
- **Behavior:** Always confirm before creating/modifying/deleting events

### Google Drive & Sheets

- **Auth:** OAuth2 (Web app flow)
- **Account 1 — `justin.miller@predictivelines.com`:**
  - Tokens: `~/.config/google/tokens.json`
  - Credentials: `~/.config/google/oauth_credentials.json`
  - Scopes: `drive.readonly`, `spreadsheets`, `gmail.readonly`, `gmail.send`, `calendar`
- **Account 2 — `millerjl@oneoaks.net`:**
  - Tokens: `~/.config/google/tokens-oneoaks.json`
  - Credentials: `~/.config/google/oauth_credentials-oneoaks.json`
  - Scopes: `drive.readonly`, `spreadsheets`
- **Refresh token:** stored in each tokens file — access token auto-refreshable via `POST https://oauth2.googleapis.com/token` with `grant_type=refresh_token`
- **Important:** Access token expires hourly; refresh before use

### QuickBooks Desktop (MCP)

- **Server:** `http://192.168.0.103:3000/sse` (SSE transport)
- **Company:** Excel Fire Protection Co., Inc.
- **EIN:** 46-0372828
- **Fiscal year:** October start
- **Helper script:** `python3 ~/repos/qb-query.py <tool_name> '<json_args>'`
- **Tools:** test_connection, get_gl_detail, get_customer_list, get_customer_detail, get_customer_transactions, get_vendor_transactions, get_journal_entries, get_deposits, get_job_addresses
- **Note:** SSE connection must stay open during calls; helper script handles this

### Kroger API

- **App:** miller-family-meal-planner (Production)
- **Auth:** OAuth2 credentials in `~/.config/kroger/credentials.json`
- **User tokens:** `~/.config/kroger/tokens.json` (after OAuth flow)
- **Brighton store ID:** `01800638` (9968 E Grand River Ave)
- **Scopes:** `cart.basic:write`, `product.compact`, `profile.compact`
- **Script:** `skills/meal-planner/scripts/kroger_api.py`
- **Note:** Use `--http1.1` with curl — Kroger API has HTTP/2 issues. The Python `requests` library works fine.

### Cameras

_(none yet)_

### SSH

_(none yet)_

### TTS

- **Provider:** Microsoft Edge TTS (free, no API key)
- **Voice:** `en-US-JennyNeural` (female)
- **Plugin:** `microsoft` must be enabled in `plugins.entries`
- **Config:** `messages.tts` in `openclaw.json` — `auto: "always"`, `provider: "microsoft"`
- **Note:** Gateway restart required after voice changes. `[[tts:voice=...]]` directives don't reliably override Microsoft provider — use config for voice changes.
- **RULE:** TTS is ONLY used during driving mode. Do NOT generate audio files for normal replies. Driving mode must be explicitly activated by Justin.
