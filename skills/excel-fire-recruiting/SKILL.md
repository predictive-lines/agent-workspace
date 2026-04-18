---
name: excel-fire-recruiting
description: >
  Review HireScore applicants for an Excel Fire Protection hiring cycle and draft individualized
  interview-invitation emails as Outlook drafts from justin.miller@predictivelines.com. Use when
  Justin shares a HireScore cycle URL such as app.hirescore.com/cycles/7239/detail, or phrases like
  "review candidates for cycle X", "draft interview invites for this cycle", "look at HireScore
  applicants", "send HireScore candidates a call invite". Covers: HireScore login + cookie
  banner, per-applicant Screen-dialog extraction (scores, education, experience, expertise),
  and drafting warm, specific interview-invite emails via the outlook-write MCP.
  DO NOT send — always save as draft for Justin's review.
---

# excel-fire-recruiting

Turn a HireScore cycle URL into individually-personalized Outlook interview-invite drafts, one
per candidate, signed as "Justin Miller / Excel Fire Protection".

## Scope

- Input: a HireScore cycle URL (e.g. `https://app.hirescore.com/cycles/7239/detail`).
- Output: one Outlook draft per candidate (never sent), plus a short Slack-thread summary per
  candidate: name, scores, 1–2 sentence take, draft id, webLink.

## Hard constraints

- **Never send.** Use `outlook-write__outlook_create_draft` only. Do not call
  `outlook_send_mail` or `outlook_send_draft`. Always report the `id` + `webLink`.
- **Browser profile = `chromium-user`.** Pass `target: "host"`, `profile: "chromium-user"`.
  Keep the same `targetId` from the first `browser.open` across every follow-up call. Use
  `refs: "aria"` + `snapshotFormat: "aria"` for stable refs. The legacy `openclaw` profile is
  broken for clicks/typing on this host — do not use it. See workspace `TOOLS.md` → "Browser
  Control" for full context.
- **Secrets stay out of files.** HireScore password lives in Justin's Bitwarden. If the
  browser is not already authenticated, prompt Justin interactively — never hardcode, never
  write credentials to disk.
- **From address:** `justin.miller@predictivelines.com` (the Outlook MCP is already
  authenticated as Justin; `create_draft` uses /me).
- **Signature:** `Justin Miller / Excel Fire Protection`.

## Workflow

### 1. Open the cycle page

```
browser.open url=CYCLE_URL target=host profile=chromium-user
# keep the returned targetId for every subsequent call
browser.snapshot targetId=TARGET_ID refs=aria snapshotFormat=aria
```

Check the snapshot for the user button (top-right of the sidebar):

- If `button "Justin Miller"` is present → already logged in, skip to step 3.
- Otherwise the page redirected to the login screen (URL contains `/login?next=/cycles/`); go to step 2.

### 2. Log in (only if needed)

1. Accept the cookie banner if present (button name usually `Accept` / `Accept all` /
   `I accept`).
2. Fill the `Email` / `Username` textbox with `justin.miller@predictivelines.com`.
3. Ask Justin for the HireScore password (do not cache it). Fill the `Password` textbox.
4. Click the `Sign In` / `Log in` button.
5. Wait for URL to settle on the cycle detail page.

### 3. Enumerate applicants

On the cycle detail page the applicant table rows are one logical row per candidate. For each
row capture:

- Name — `statictext` with the person's full name (row anchor).
- City/State — the first `statictext` after the name in the row.
- Apply Date — the next `statictext` (MM/DD/YYYY).
- Online Application % — a `link` whose `name` is the numeric percentile.
- BVI % — next `link` (numeric percentile).
- Baseline % — next `statictext` (numeric percentile).

Then open the Screen dialog for each candidate:

```
browser.act kind=click ref=NAME_REF     # clicking the candidate's name opens the Screen modal
browser.snapshot targetId=TARGET_ID refs=aria snapshotFormat=aria maxChars=30000
```

The dialog exposes a `role: dialog` node whose `description` attribute is the full flattened
applicant profile (address, email, phone, education, experience, expertise ratings, position,
submission date). Use `scripts/parse_screen_dialog.py` to turn that description text into a
structured record. After extraction, close the dialog:

```
browser.act kind=press key=Escape
```

### 4. Build a per-candidate take

For each candidate synthesize a 1–2 sentence internal "take" from the extracted data. It is
*not* sent to the candidate — it is for the Slack-thread summary only. Aim it at Justin:
how their background maps to the Journeyman Sprinkler Fitter role, any standout (or concerning)
signals from scores + expertise ratings.

### 5. Draft the email

Use `outlook-write__outlook_create_draft` with:

- `to: [candidate_email]`
- `subject`: `Excel Fire Protection — quick intro call?`
- `body_type: "html"`
- `body`: short, warm, under ~160 words, using the template in
  `references/email-template.md`. Reference exactly *one* specific thing from their
  background (a company, a skill, their location, or an expertise rating) — do not stuff the
  email with everything you know about them.

Do not send. The tool returns `{ id, webLink, subject, conversationId }` — keep these for
the summary.

### 6. Report back

Post one Slack-thread message with a per-candidate block:

```
NAME — OA xx% / BVI xx% / Baseline xx%
One- or two-sentence take aimed at Justin
Draft: DRAFT_WEBLINK
```

Close with a one-line reminder that nothing was sent.

## Safety & etiquette

- Never email candidates who don't have a valid email in the Screen dialog — report the
  missing-email case instead of drafting.
- If the candidate explicitly opted out of outreach anywhere in the Screen text, skip them
  and flag for Justin.
- If the cycle has more than ~15 candidates, pause after extracting the list and confirm with
  Justin before drafting all of them (avoid burst-creating dozens of drafts).
- Always leave the browser on the cycle detail page when finished.

## Tailored interview question sets (optional)

If the user asks for an interview question set for a specific HireScore candidate (or for the
whole cycle), read `references/interview-questions.md` and pick questions tailored to that
candidate's Screen dialog data plus the *interview stage* the user is prepping for.

**By stage** (see the "Proposed 4-stage interview process" section of the reference file):

- **Stage 1 — 30-min phone screen (Justin solo):** 8–10 questions. Weight: Kevin's work-
  history block (§1) + 2–3 `[Recruit]` STAR questions + `[Kevin]` "why UP" + 1–2 from §4
  Company Cam. Skip §6 Trade questions at this stage unless the candidate claims deep
  expertise you want to probe.
- **Stage 2 — 45-min Zoom (Justin + Kevin + Keith):** 10–12 questions. Weight: 5–7 from
  §6 `[Trade]` (matched to the candidate's `expertise_raw` self-ratings), 2–3 `[Recruit]`
  teamwork/decision-making, 1–2 role-specific scenarios from the technical screen section.
- **Stage 3 — working day:** no scripted questions; use the crew debrief form at end of day.
- **Stage 4 — references:** use the reference call script at the end of the reference file.

**Heuristics for tailoring picks:**

- Pull at least one question from each of the 5 signal categories (work ethic, honesty, UP
  growth mindset, openness to tech / Company Cam, willingness to relocate).
- Use the candidate's `expertise_raw` self-ratings to pick `[Trade]` and `[Role]` questions:
  any skill they rated ≤3/5 is worth probing, any skill they rated 5/5 is worth
  pressure-testing. E.g. self-rated 5/5 on dry systems → ask the trip-test walkthrough
  and the air-supply / nitrogen generator question.
- Use `experience_raw` to pick one experience-specific hook (e.g. if they were a foreman,
  lean into crew-leadership / training questions from §7).
- If the candidate's city/state is outside Michigan, include the relocate block. If
  they're already in the UP or Michigan, drop the "have you been to the UP" opener and
  instead ask about long-tenure intent.
- NEVER pick from the red-flag list. If a caller suggests a red-flag-style question,
  redirect to the safe alternative listed in the same file.

After generating the set, post it back to the user grouped by signal category so they can
scan during the call, and tag each question with its source tag (`[Kevin]`, `[EEOC]`,
`[Role]`, `[Trade]`, `[Recruit]`) so the user knows where it came from.

## Files

- `references/email-template.md` — the draft-email pattern (tone, structure, signature,
  placeholder rules).
- `references/hirescore-dom-notes.md` — DOM anchors + `dialog.description` parsing hints,
  captured from cycle 7239. Read when selectors misbehave or HireScore ships a UI change.
- `references/interview-questions.md` — HR-safe behavioral question bank for the JM Sprinkler
  Fitter role, organized by the 5 signals Justin wants to read, plus a trade-knowledge
  screen, a general trades-recruiting behavioral block, a proposed 4-stage interview
  process (phone screen → Zoom → paid working day → references + offer), and a
  protected-category red-flag list with EEOC-safe alternatives. Source tags on every
  question: `[Kevin]` for Kevin Masich's suggestions (with Quo call-id citations),
  `[EEOC]` for EEOC/SHRM-derived, `[Role]` for role-scenario-specific, `[Trade]` for
  sprinkler-industry craft questions, `[Recruit]` for general trades-recruiting behavioral
  STAR questions.
- `scripts/parse_screen_dialog.py` — turn the Screen dialog's flattened text into a structured
  `{name, email, phone, city, state, education[], experience[], expertise{}, submitted_on,
  position}` dict. Importable as `parse(text)` or runnable as a CLI that reads stdin.
