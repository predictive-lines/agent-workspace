# TOOLS.md - Local Notes

### GitHub

- **Org:** predictive-lines
- **Auth:** Fine-grained PAT stored in `~/.git-credentials`
- **Repos (cloned to ~/repos/):**
  - excel-fire-ai
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

- **Auth:** OAuth2 (Web app flow), tokens in `~/.config/google/tokens.json`, credentials in `~/.config/google/oauth_credentials.json`
- **Scopes:** `drive.readonly`, `spreadsheets` (read/write)
- **Refresh token:** stored — access token auto-refreshable via `POST https://oauth2.googleapis.com/token` with `grant_type=refresh_token`
- **Important:** Access token expires hourly; refresh before use

### QuickBooks Desktop (MCP)

- **Server:** `http://192.168.0.103:3000/sse` (SSE transport)
- **Company:** Excel Fire Protection Co., Inc.
- **EIN:** 46-0372828
- **Fiscal year:** October start
- **Helper script:** `python3 ~/repos/qb-query.py <tool_name> '<json_args>'`
- **Tools:** test_connection, get_gl_detail, get_customer_list, get_customer_detail, get_customer_transactions, get_vendor_transactions, get_journal_entries, get_deposits, get_job_addresses
- **Note:** SSE connection must stay open during calls; helper script handles this

### Cameras

_(none yet)_

### SSH

_(none yet)_

### TTS

_(none yet)_
