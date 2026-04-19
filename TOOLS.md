# TOOLS.md - Local Notes

## ⚠️ Two Different MCP Hosts — Don't Mix Them Up

Justin runs MCP connectors in **two separate environments**. A connector installed in one is NOT available in the other. Always check which environment you're in before telling Justin to go connect something.

### Claude Desktop (Cowork)
- **What it is:** The Claude Desktop app on Justin's Mac, using [Cowork](https://cowork.ai) as the MCP connector hub.
- **How you know you're there:** Tool names typically namespaced by the Cowork connector (e.g., Granola, Quo tools come through Cowork).
- **How Justin adds a connector:** Cowork UI → Connectors → sign in → authorize.
- **Currently connected via Cowork:** Granola, Quo, Notion (historically).

### OpenClaw (this environment)
- **What it is:** The OpenClaw agent running on the `open-claw` Linux host. You (the agent reading this) are here.
- **How MCP servers are configured:** `~/.openclaw/openclaw.json` under the `mcp.servers` key, managed via `openclaw mcp set|unset|list|show`.
- **Currently connected:** `outlook-write` (custom Microsoft 365 MCP from `~/repos/excel-fire-ai/mcp-servers/outlook/`).
- **Adding a new MCP server here requires:**
  1. The MCP server binary/package installed locally (pip, npm, etc.) OR a remote URL the server exposes.
  2. `openclaw mcp set <name> '<json-config>'` with `command`, `args`, optional `env`, optional `cwd` — or a remote-style config for SSE/HTTP transports.
  3. `openclaw gateway restart` so the agent picks up the new tools.
  4. Any secrets (API keys, OAuth tokens) stored as env vars or files the MCP server can read — never hardcoded.
- **⚠️ Granola and Quo are NOT currently wired into OpenClaw.** If Justin asks you to use them here, the connector has to be added on this side — Cowork's connection doesn't carry over. Both would require finding/building an MCP server package for each service, registering under `mcp.servers`, and handling their auth locally (likely OAuth flows with tokens written to `~/.config/<service>/`).

### Browser Control (OpenClaw → Chromium existing-session)

- **Working profile:** `chromium-user` (existing-session / chrome-mcp). This is the browser path that actually works for interactive control on this host.
- **Broken profile:** the legacy dedicated `openclaw` profile — `open`/`read`/`snapshot` work but any `act`/`click`/`type` hangs with `browser.request` timeout / `browserType.connectOverCDP` timeout. Do **not** use it for interaction.
- **Why:** OpenClaw migrated from the Chrome extension relay (`driver: "extension"`, removed `browser.relayBindHost`) to `driver: "existing-session"` via Chrome MCP attach. Requires Chrome/Chromium major >= 144 (`CHROME_MCP_MIN_MAJOR = 144`).
- **Browser on this host:** Chromium (Snap) on Ubuntu.
  - Actual user data dir: `/home/open-claw/snap/chromium/common/chromium`
  - Default `user` profile assumes Google Chrome at `/home/open-claw/.config/google-chrome/` and will fail with `Could not find DevToolsActivePort` — that's expected, use `chromium-user` instead.
- **Config (already in `~/.openclaw/openclaw.json` under `browser.profiles`):**
  ```json
  "chromium-user": {
    "driver": "existing-session",
    "userDataDir": "/home/open-claw/snap/chromium/common/chromium",
    "color": "#00AA00"
  }
  ```
- **Requirements before attach works:**
  1. Chromium is running (keep the window open).
  2. Remote debugging enabled in `chrome://inspect/#remote-debugging` (or `chromium://…`).
  3. First attach prompts Justin to approve the connection in Chromium — he must click accept.
  4. Gateway must be restarted after editing profile config: `openclaw gateway restart`.
- **Usage pattern from this side:** pass `profile: "chromium-user"` and `target: "host"` on `browser` tool calls. Snapshot with `refs: "aria"` + `snapshotFormat: "aria"` for stable refs across calls. Always keep the same `targetId` from the `open` response for subsequent `act` calls.
- **Sanity check sequence** (known to work): `browser.open https://example.com` → `browser.snapshot` → `browser.act kind=click ref=<Learn more>` — this full round-trip proves interactive control is live.
- **Profile mutation gotcha:** `openclaw browser create-profile` fails with `browser.request cannot mutate persistent browser profiles`. Edit `~/.openclaw/openclaw.json` directly and restart the gateway instead.
- **CLI flag gotcha:** `--browser-profile` goes **before** the subcommand: `openclaw browser --browser-profile chromium-user open https://…`.

### Quo (Phone / SMS / Call Transcripts)

- **Where it lives:** **Both environments.**
  - OpenClaw: registered as `quo` under `mcp.servers`, server at `~/repos/armavita-quo-mcp/` (Node, stdio, AGPLv3). Auth via `QUO_API_KEY` loaded from `~/.config/quo/api_key` by `launch-openclaw.sh`.
  - Claude Desktop: also available via Cowork connector.
- **Inbox numbers:**
  - `+17348214271` — Predictive Lines (💼)
  - `+19069363100` — Excel Fire Protection / Marquette (🔥)
  - `+15172148100` — Personal Mid-Michigan (🏡, added 2026-04-17)
- **Tools (OpenClaw `quo__*`):** Messages (`send_text`, `list_messages`, `get_message`), Conversations (`list_conversations`), Contacts (`create_contact`, `list_contacts`, `get_contact`, `update_contact`, `delete_contact`, `get_contact_custom_fields`), Calls (`list_calls`, `get_call`, `get_call_recordings`, `get_call_summary`, `get_call_transcription`, `get_voicemail`), Phone numbers, Users, Webhooks.
- **Tools (Claude Desktop via Cowork):** fetch-messages, fetch-call-transcripts, send-message, create-contact, update-contact.
- **Note:** Use both inboxes when compiling weekly status reports. API key is a single Quo workspace key covering both numbers.
- **Auth rotation:** edit `~/.config/quo/api_key` (mode 0600), then `openclaw gateway restart`. No code change needed.

### Granola (Meeting Notes & Transcripts)

- **Where it lives:** **Claude Desktop (Cowork)** — NOT wired into OpenClaw yet.
- **Tools (Claude Desktop only):** list_meetings, get_meetings, get_meeting_transcript, query_granola_meetings, list_meeting_folders
- **Use:** Pull meeting summaries and transcripts for weekly status reports and action item tracking.
- **Important:** Granola *was* connected on Apr 14, 2026, but in the Cowork / Claude Desktop environment, not this OpenClaw host. Do not assume prior Granola access here just because memory says it was connected.
- **If you (OpenClaw agent) need Granola data:** either Justin pastes/exports it, or we add a Granola MCP server locally to OpenClaw.

### Microsoft 365 — Custom Outlook MCP

- **Where it lives:** **Both environments.**
  - OpenClaw: registered as `outlook-write` under `mcp.servers` in `~/.openclaw/openclaw.json`, runs from `~/repos/excel-fire-ai/mcp-servers/outlook/.venv/`. Tool names prefixed `outlook-write__*`.
  - Claude Desktop: also available via `github-custom-mcp` Cowork connector pulling the same source repo.
- **Current scope:** Microsoft To Do (tasks), SharePoint Lists, SharePoint Drive, Outlook mail/calendar/contacts, Teams, OneNote.
- **Tools (To Do):** todo_list_lists, todo_list_tasks, todo_create_task, todo_update_task, todo_complete_task, todo_delete_task, todo_create_list
- **Tools (SharePoint Lists):** lists_get_site, lists_list_lists, lists_get_list, lists_get_items, lists_create_item, lists_update_item, lists_delete_item, lists_create_list
- **Tools (SharePoint Drive):** drive_list_drives, drive_list_items, drive_search, drive_get_file_content, drive_get_file_metadata, drive_upload_file, drive_create_folder
- **Tools (Outlook mail/calendar/events):** Also available but not primary use case yet
- **Use:** To Do tasks and SharePoint Lists feed into weekly status reports. Part of Notion → M365 migration (see MEMORY.md).

### GitHub

- **Org:** predictive-lines
- **Auth:** Fine-grained PAT stored in `~/.git-credentials` (local git) and `~/github-mcp-token` (MCP bridge)
- **MCP bridge:** `~/mcp-bridge.sh` — restart after token rotation. Reads PAT from `~/github-mcp-token`.
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
  - **Meeting Notes** (`2847e702-d98c-80df-a583-000b5473f3d7`) — AI meeting capture / notes / transcript database
    - database_id: `2847e702-d98c-80b5-aea2-d31066fd0432`
    - Use `data_source_id` for queries and `database_id` when creating pages
    - Important: this is the main Notion meeting capture database Justin uses for in-person and virtual meetings

### Google Calendar

- **Auth:** Same OAuth2 as Drive/Sheets (calendar scope added 2026-03-01)
- **Calendars:**
  - `justin.miller@predictivelines.com` — primary
  - `miller-family-calendar@oneoaks.net` — Miller family calendar
  - `en.usa#holiday@group.v.calendar.google.com` — US holidays
- **API:** Google Calendar v3 (`calendar-json.googleapis.com`)
- **Behavior:** Always confirm before creating/modifying/deleting events

### Google Workspace — Two Credential Stores (by design)

There are **two parallel Google OAuth setups** on this host. They do NOT share credentials and are used by different code paths. Do not consolidate without migrating callers.

#### Store 1 — `google-workspace-mcp` MCP server (multi-account)

- **Binary:** `/home/open-claw/repos/google-workspace-mcp-live/dist/cli.js` (v2.3.6)
- **Registered under MCP name:** `google-workspace` in `~/.openclaw/openclaw.json`
- **Config root:** `~/.google-mcp/`
- **Accounts registry:** `~/.google-mcp/accounts.json` (per-account `credentialsPath` + `tokenPath`)
- **Tokens dir:** `~/.google-mcp/tokens/<accountName>.json` (format: `{type:'authorized_user', client_id, client_secret, refresh_token}`)
- **Global fallback credentials:** `~/.google-mcp/credentials.json` (work OAuth client, used when an account has no per-account credentialsPath)
- **CLI:**
  - `node .../cli.js accounts list`
  - `node .../cli.js accounts add <name> -c <path> [--no-open]`
  - `node .../cli.js accounts test-permissions [name]`
  - `node .../cli.js accounts remove <name>`

**Account: `predictivelines`** (work, `justin.miller@predictivelines.com`)
- GCP project: `open-claw-integration-488119` (Internal / predictivelines.com org)
- OAuth client: `734807837733-769npl2q9iej7isqrvqo6c07jacjscoj.apps.googleusercontent.com` (Desktop)
- Uses global `~/.google-mcp/credentials.json` (no per-account override)
- Token: `~/.google-mcp/tokens/predictivelines.json`
- Enabled APIs: Gmail, Calendar, People, Drive, Sheets (Docs/Slides/Forms disabled)

**Account: `oneoaks-personal`** (personal, `millerjl@oneoaks.net`)
- GCP project: `open-claw-personal-493814` (External / Testing on oneoaks.net org, test user = millerjl@oneoaks.net)
- OAuth client: `126015338489-fvlh5pba2faa99rrh1g7va2cetap8gma.apps.googleusercontent.com` (Desktop, "OpenClaw Personal (Desktop)")
- Per-account credentials: `~/.config/google-personal/oauth_credentials.json` (mode 600, dir 700)
- Token: `~/.google-mcp/tokens/oneoaks-personal.json`
- Enabled APIs: Gmail, Calendar, People, Drive, Sheets (Docs/Slides/Forms disabled)

**Scopes requested by the server (both accounts, hardcoded in MCP):** `drive`, `documents`, `spreadsheets`, `presentations`, `forms.body`, `forms.responses.readonly`, `gmail.modify`, `gmail.settings.basic`, `calendar`, `contacts`, `contacts.other.readonly`, `directory.readonly`. APIs not enabled in GCP return 403 at runtime but don't block the OAuth flow.

**Known bug (v2.3.6, non-fatal):** `accounts add --credentials <path>` writes the token file with the *global* client_id/secret instead of the per-account one, because it saves the token before updating `accounts.json`. Auth still works at runtime (the OAuth2Client is rebuilt with the correct per-account credentials on every load; `client_id`/`client_secret` in the token file are dead fields after initial issuance). Can fix cosmetically by rewriting `~/.google-mcp/tokens/<name>.json` to carry the correct client_id/secret.

**OAuth flow with a headless agent:** Use `--no-open`, capture the auth URL from stdout, `browser.navigate` into the Chromium `chromium-user` tab that's already signed into the target Google account, click Allow. The `browser` tool reports "browser navigation blocked by policy" on the `http://localhost:3000/?code=...` callback, but the HTTP request DID reach the MCP's callback server — verify by polling the background process for `Account "<name>" added successfully!`.

#### Store 2 — standalone Python scripts (single-account)

- **Credentials dir:** `~/.config/google/`
- Used by: `cash-bridge-builder`, `model-summary-report`, `fix_distance_formulas*.py`, `build_bmi_sheets.py`, `build_proforma.py`, `build_budget.py`, Tiller helpers, etc.
- Different OAuth clients than Store 1; scripts refresh access tokens by POSTing to `https://oauth2.googleapis.com/token` with the refresh_token.
- **Account 1 (work):** `~/.config/google/oauth_credentials.json` + `~/.config/google/tokens.json` — client `734807837733-o9mh46lb0de2b3eefb3h5ub59oe64imh` — scopes `drive.readonly`, `spreadsheets`, `gmail.readonly`, `gmail.send`, `calendar`
- **Account 2 (oneoaks):** `~/.config/google/oauth_credentials-oneoaks.json` + `~/.config/google/tokens-oneoaks.json` — client `729004136322-eqh0o220vpk18cq7bmsr3md2ibfhbbnt` — scopes `drive.readonly`, `spreadsheets`
- **Refresh token:** stored in each tokens file — access token auto-refreshable; expires hourly

**Rule:** Leave Store 2 alone unless explicitly migrating a caller. Grep `~/repos/` for `~/.config/google/` before touching anything in there.

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
