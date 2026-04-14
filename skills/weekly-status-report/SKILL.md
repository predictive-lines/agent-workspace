---
name: weekly-status-report
description: >
  Compile a weekly status update report for Excel Fire Protection by pulling
  from all connected data sources — Granola meetings, Quo call transcripts,
  Slack, Google Calendar, Notion tasks, Microsoft To Do, SharePoint Lists,
  and GitHub activity. Use this skill whenever Justin asks for a "weekly
  report," "status update," "what did I do this week," "weekly recap," or
  anything about summarizing the past week's work. Also trigger when he says
  "weekly EFP update," "status report," or "recap for Jaclyn."
---

# Weekly Status Report — Excel Fire Protection

## Purpose

Produce a concise, delta-only weekly status update covering Monday through
Friday of the reporting week. The primary audience is Jaclyn Miller (CEO/CFO),
but the report should be professional enough to share with any leadership
stakeholder (lender, attorney, CPA, etc.).

**Key principle:** Only report what *changed* during the reporting week. Do not
restate standing status on items that haven't moved. If a source yields nothing
new for the week, omit that section entirely rather than writing "no updates."

## Delivery

Present the draft report in Cowork chat for Justin to review. After he approves
(or requests edits), offer to save it to Notion or export as .docx. Do not
auto-publish anywhere.

---

## Pre-Flight Connectivity Checks

Before collecting any data, run a quick connectivity test against connectors
that are known to have flaky auth. Currently this applies to **Quo** (phone
calls and SMS), but add others here if they develop the same pattern.

### Quo Pre-Flight

1. Make a minimal `fetch-messages` call to **either** Quo inbox (e.g.,
   `+17348214271` with `maxResults: 1`) — just enough to confirm auth works.
2. **If it succeeds:** proceed normally to Source Collection.
3. **If it fails with an auth error:**
   a. Immediately call `suggest_connectors` with the Quo connector UUID
      (`b73df510-3727-4001-9964-fb0acc49592e`) and keyword `["phone"]`.
      This surfaces a re-auth button directly in the chat.
   b. Tell Justin: "Quo needs re-authentication. I've surfaced the reconnect
      button above — please re-auth and let me know when it's done. I'll
      pause Quo collection but continue pulling from the other 9 sources
      in the meantime so we don't waste time."
   c. **Continue collecting all non-Quo sources immediately** (do not block).
   d. After all other sources are collected, **check back with Justin.** If
      he has re-authenticated by then, retry Quo and fold the data into the
      report before presenting the draft. If he hasn't re-authed yet, present
      the draft with a prominent `[Quo data missing — re-auth pending]` flag
      at the top and offer to re-pull and update once he reconnects.

This ensures the report is never silently missing phone data, and Justin can
fix the auth without leaving the chat.

---

## Source Collection

Collect data from the sources below **in this order**. The order is designed to
build context progressively — calendar gives you the skeleton of the week,
meetings and calls fill in the substance, tasks show what moved, and comms
round out the picture.

### 1. Google Calendar

**What to pull:** All events from Monday 00:00 ET through Friday 23:59 ET of
the reporting week on Justin's primary calendar
(`justin.miller@predictivelines.com`).

**Why:** The calendar is the structural backbone — it tells you which meetings
happened, who Justin met with, and what the week's rhythm looked like. This
context helps you interpret everything else.

**Tool:** `list_events` with `startTime` / `endTime` for the reporting week.

### 2. Granola (Meeting Notes & Transcripts)

**What to pull:** All meetings from the reporting week. Start with
`list_meetings` (time_range: custom, Mon–Fri), then `get_meetings` for
summaries, and `get_meeting_transcript` for any meetings that look substantive.

**Why:** Granola captures what was actually discussed and decided in meetings —
action items, commitments, key decisions. This is often the richest source of
"what changed."

**What to extract:** Decisions made, action items assigned, commitments given,
key discussion topics, names of external parties involved.

### 3. Quo — Call Transcripts & Messages

**What to pull:** Call transcripts and SMS/text messages from **both** inbox
numbers for the reporting week:
- `+17348214271` — Predictive Lines Business Line
- `+19069363100` — Justin Miller in Marquette

**Tools:**
- `fetch-call-transcripts` with `createdAfter` / `createdBefore` for each inbox
- `fetch-messages` with `createdAfter` / `createdBefore` for each inbox

**Why:** Phone calls and texts capture interactions that don't make it into
meetings — vendor follow-ups, lender conversations, field crew coordination,
customer inquiries.

**What to extract:** Who called/texted, topic summary, any commitments or
follow-ups promised. Skip robocalls, spam, and OTP codes.

### 4. Microsoft To Do (Tasks)

**What to pull:** Tasks completed or modified during the reporting week. Also
note any new tasks created.

**Tool:** `todo_list_lists` → `todo_list_tasks` for each list.

**Why:** Shows what got done and what got queued up.

**What to extract:** Completed tasks (with completion context if available), new
tasks added, tasks whose status changed.

### 5. SharePoint Lists

**What to pull:** Items created or modified during the reporting week across
active lists.

**Tools:** `lists_get_site` → `lists_list_lists` → `lists_get_items` with date
filters or `orderby` on `lastModifiedDateTime`.

**Why:** Operational databases (job tracking, billing, etc.) that are migrating
from Notion. Any movement here is reportable.

**What to extract:** New items, status changes, notable updates.

### 6. Gmail — justin.miller@predictivelines.com

**What to pull:** Email threads from the last 7 days. Focus on threads where
Justin sent or received substantive business correspondence — not newsletters,
automated notifications, or marketing.

**Tool:** `search_threads` with query `newer_than:7d` (Gmail MCP). For threads
that look substantive, use `get_thread` to pull full content.

**Why:** Email captures formal correspondence with lenders, attorneys, insurers,
vendors, customers, and partners that may not appear in any other source. A
lender update, a signed document, an insurance quote — these often only live in
email.

**What to extract:** Key correspondences (who, topic, outcome/status), documents
sent or received, commitments made, decisions confirmed. Skip OTP codes,
marketing, automated alerts, and social media notifications.

**Filtering guidance:** Use additional query operators to reduce noise:
- `from:me newer_than:7d` — what Justin sent (high signal)
- `is:important newer_than:7d` — Gmail's priority inbox picks
- Exclude common noise: `-from:noreply -from:notifications -category:promotions
  -category:social -category:updates newer_than:7d`

### 7. Notion Tasks

**What to pull:** Tasks with status changes during the reporting week from the
Tasks database (data_source_id: `2847e702-d98c-8170-9008-000bc7d6d318`).

**Tool:** Notion search or query with date filters on `last_edited_time`.

**Why:** During the M365 migration, tasks may still live in Notion. Check both
systems until migration is complete. Once Justin confirms Notion tasks are fully
migrated, this source can be removed.

**What to extract:** Tasks completed, status changes, new tasks.

### 8. Notion Meeting Notes

**What to pull:** Meeting notes created or edited during the reporting week.

**Tool:** `notion-query-meeting-notes` with a date filter on `created_time` for
the Mon–Fri reporting window. For meetings that look substantive, use
`notion-fetch` to pull the full page content.

**Why:** While evaluating migration options (Granola vs. Notion vs. other),
meeting notes may still be captured in Notion. Check both Granola and Notion
Meeting Notes until the migration path is settled. There will likely be overlap
— deduplicate by matching on date + attendees + topic.

**What to extract:** Decisions made, action items, key discussion points. Same
extraction goals as Granola — the two sources are complementary during the
transition.

### 9. Slack

**What to pull:** Messages from key channels during the reporting week. At
minimum check #open-claw. Ask Justin if there are other channels to scan.

**Tool:** `slack_search_public` with date filters, or `slack_read_channel` for
specific channels.

**Why:** Async decisions, updates posted by the Claude bot, and team
communication. **Note:** This source is only relevant when Justin is actively
using the OpenClaw CLI agent, which posts updates and receives commands via
#open-claw. While he's primarily using the Claude Desktop app / Cowork, this
channel will be mostly quiet — skip it if there's no meaningful activity rather
than reporting on bot noise.

**What to extract:** Decisions, announcements, notable threads.

### 10. GitHub Activity

**What to pull:** Commits, PRs, and issues from the reporting week across
`predictive-lines` repos (primarily `ai-skills` and `agent-workspace`).

**Tool:** `list_commits` with date filtering, `list_pull_requests`,
`list_issues`.

**Why:** Tracks infrastructure and tooling progress — skills built, MCP servers
updated, model changes.

**What to extract:** What was built/fixed/shipped, PR summaries, new issues
opened.

---

## Report Format

Structure the report as clean markdown with the following template. Only include
sections where there's actual content for the week — skip empty sections.

```markdown
# Excel Fire Protection — Weekly Status Update
**Week of [Month Day] – [Month Day], [Year]**
Prepared by: Justin Miller

## Acquisition & Deal Progress
[Movement on closing, legal, lender, SBA, purchase agreement, etc.]

## Operations & Field Work
[Job status changes, inspections, crew activity, customer interactions]

## Financial & Accounting
[Model updates, QuickBooks activity, billing, AR/AP, budget work]

## Technology & Infrastructure
[IT setup, Paperless-ngx, MCP development, skills, SharePoint migration]

## Business Development
[New leads, estimates, customer outreach, sister company progress]

## Administrative & HR
[Hiring, compliance, policies, insurance, bonding]

## Key Decisions Made
[Bullet list of decisions with brief context]

## Action Items & Follow-Ups
[Bullet list of open commitments with owner and deadline if known]

## Next Week Outlook
[Brief look-ahead based on calendar and open items]
```

### Writing Style

- **Concise and factual.** Each item should be 1–2 sentences max. Lead with
  what changed, then brief context if needed.
- **Use names.** Reference people by name (e.g., "Called Julie Olson at Embers
  RE: stock sale restructure") rather than vague descriptions.
- **Group related items.** If three calls were all about the same topic, roll
  them into one bullet.
- **Professional but not stiff.** This is an internal leadership document, not a
  board report. Clear, direct language.
- **No filler.** If a section would only say "no changes this week," omit it.

---

## Edge Cases & Notes

- **Short weeks / holidays:** If Monday is a holiday, adjust the window to
  Tuesday–Friday. Note the shortened week at the top.
- **Quo auth failure:** If Quo returns auth errors, note it in the report as
  "[Quo transcripts unavailable — connector needs re-authentication]" and
  proceed with other sources.
- **Source unavailable:** If any source is down or returns errors, note it
  briefly and continue. Don't let one broken source block the whole report.
- **Duplicate events:** The same topic may appear in Calendar, Granola, and Quo
  (e.g., a phone call shows up on calendar, Granola captured the meeting, and
  Quo has the transcript). Deduplicate — report the event once with the richest
  context available.
- **Sensitive content:** Omit OTP codes, passwords, spam calls, and personal
  family items that aren't business-related. If a personal call is borderline
  relevant (e.g., a family calendar event that blocked a business meeting), note
  the conflict without details.
