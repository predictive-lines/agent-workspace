# MEMORY.md — Long-Term Memory

## Justin Miller — Context
- Acquiring Excel Fire Protection (Marquette, MI) for $3M. Target close: May 15, 2026.
- Union fire sprinkler company (~$2M revenue), Local 669. Fiscal year starts October.
- Tax structure not yet finalized (S-Corp vs C-Corp). Household has ~$200K W2 income (MFJ).
- Annual debt service: $325K (SBA 7a $277K + Seller Note $26K + Ford F250 $22K).
- Wife/business partner: Jaclyn Miller (CEO/CFO).

## Key Folder Locations (request via `request_cowork_directory` if not mounted)
- **Excel Fire Protection deal room** (Google Drive, primary EFP folder):
  `~/Library/CloudStorage/GoogleDrive-justin.miller@predictivelines.com/My Drive/ETA/Excel Fire Protection`
  Contains: CIM, Signed LOI, Extend LOI, Purchase Agreement, SBA forms, Financial Reports, Tax Data, Lender Docs, Buyer Docs, Insurance & Bonding, HR, Lease, Pending Legal, Customer Data, Customer Work Orders, closing costs, Business Plan, Vendor Paperwork, Articles of Incorporation and Licenses, Compliance. This mount does NOT persist across sessions — request it by path at session start if the conversation touches deal docs, closing items, or EFP source materials.

## Behavioral Lessons
- **Verify writes:** NEVER claim an API write succeeded without pulling data back via GET. If unverifiable, say so.
- **Pull sheet bounds first:** ALWAYS check actual row/column layout before writing formulas. Never assume.
- **Use existing skills:** When working on the financial model or household finances, USE skills in `~/repos/excel-fire-ai/skills/` — they have correct sheet IDs, column mappings, and formula patterns.
- **Repo rename:** `predictive-lines/excel-fire-ai` → renamed to `predictive-lines/ai-skills` (Mar 15 2026). Local folder stays `~/repos/excel-fire-ai`, remote URL updated.
- **Event-driven updates:** Post after each micro-step completes instead of rigid time intervals.
- **Verify after API writes:** Always check row count/contents BEFORE retrying a write that appeared to time out. The API may have succeeded silently, causing duplicate rows.
- **Budget frequency column (E):** Debt service rows use `E=12` (annual). Check existing row patterns before adding new ones.
- **New messages for completion:** ALWAYS post completion summaries as a NEW message at bottom of thread. Never edit earlier messages for status updates.
- **Slack commands need provider key:** For Slack native slash commands, use `"slack"` in `commands.allowFrom`, not just `"*"`.
- **Browser control = `chromium-user` profile.** The legacy dedicated `openclaw` browser profile has broken interactive control on this host (read works, clicks/typing time out on CDP). Use the existing-session `chromium-user` profile (Chromium Snap user data dir at `/home/open-claw/snap/chromium/common/chromium`) with `target: "host"`, `profile: "chromium-user"`. Chromium must be running with remote debugging enabled, and Justin must approve the first attach prompt. Full usage notes live in TOOLS.md “Browser Control” section.

## Key Technical Lessons
- **EFP Site Economics table restructure (Jun 2 2026):** Split `Site Economics` into three real Google Sheets Tables: `Sites` (`A1:K5`), `SiteRevenueControls` (`A8:O32`), and `SiteOperatingDrivers` (`S1:AI93`). Collapsed generated Budget-output pad into direct `Budget!A729:N820` structured-ref formulas, migrated `Jobs Forecast` (1,370 cells) off flattened `Site Economics!A:O`, and cleared old duplicate blocks after whole-workbook ref scans. Site-wide active/start/end controls are now metadata/defaults only; operating costs follow driver-line `Include` + `Line Start/End Date`, revenue forecasts follow revenue-line `Active?` + `Start Date`, and KPI site activity derives from included/economic line items. Retired zero-use named ranges `site_economics_site_active_flag`, `site_economics_site_launch_date`, `site_economics_site_end_date`. Final verification: 0 direct `Site Economics!…` refs, 2,172 structured site-table refs, active tabs clean, BS check all zero. Gotcha: table header/metadata can get weird around adjacent/right-side tables and grouped rows; restore visible headers + `columnProperties`, ungroup for visual cleanup. Details/backups in `skills/efp-financial-model/SKILL.md`.
- **EFP Jobs Forecast structural refactor (Jun 2 2026):** In-place Tables conversion was unsafe: large generated output range `Jobs Forecast!A46:AC1240` caused Sheets API 500 and same-row side-by-side tables corrupted `columnProperties`; `DeleteTableRequest` also removed visible contents in that bad state, requiring backup restore. Final architecture after Justin's simplification: `JobsForecastDrivers` table over `Jobs Forecast!A4:W44`; generated Budget-shaped calculations live directly on `Budget!A821:AC1720` (visible fields `A:N`, hidden helper fields `O:AC`); `Jobs Forecast Output` helper tab was deleted after 0 refs. `Budget!A821:N1720` display diff vs backup = 0, 0 refs to deleted helper, 0 `#REF!`, BS check all zero. Use API-inferred table metadata only for this page; do not hand-supply `columnProperties`. Gotchas: old Budget→Output row mapping was not one continuous offset, and COGS rows referenced source revenue rows; replay using original Budget formulas as the row map. Details/backups in `skills/efp-financial-model/SKILL.md`.
- **EFP stale HR rows 2:9 cleanup (Jun 2 2026):** After HumanResources migration, audited remaining formulas against `Human Resources!2:9`. `defined_variables!A50:C53` and `Job Addresses!N:O` were orphaned/stale (no downstream refs/named ranges; Job Addresses outputs were `99999`/stale names). Cleared contents only, backed up to `/tmp/stale_hr_2_9_helpers_backup_20260602_182417.json`, verification clean.
- **EFP HumanResources table migration (Jun 2 2026):** Converted `Human Resources` to real table `HumanResources` over A1:W195. Migrated 1,607 formulas from direct/named HR refs to structured table refs (KPIs/Budget/Jobs Forecast/Union Benefits/defined_variables), deleted 13 old `hr_model_*` / `hr_roster_*` named ranges after zero-usage scan, verification clean with BS check all zero. Field typing lesson: `Include in Model` is true BOOLEAN; numeric/currency/date/text types preserved by semantic use. Follow-up audit found the remaining HR rows 2:9 helpers were stale/orphaned, not semantic; cleared `defined_variables!A50:C53` and `Job Addresses!N:O` after confirming no downstream refs/named ranges. Details in `skills/efp-financial-model/SKILL.md`.
- **EFP workbook Tables pattern (Jun 2 2026):** For database-like helper tabs in financial model `13KQXudrHd5F3p-NHrr_RTkSWuIAbhVuDp9GIDVNCetM`, prefer real Google Sheets Tables over proliferating named ranges. Confirmed API `AddTableRequest` works; structured refs work off-page; table/column renames auto-update formulas. API row appends do not auto-expand tables — use `UpdateTableRequest`. First production migration: `Union Benefits` → `UnionBenefits`; 132 Budget formulas moved from `union_benefits_*` named ranges; old names deleted after usage scan; verification clean. Preserve formula semantics in table types (`Toggle` and `Period Key` stayed numeric/DOUBLE). Durable skill: `skills/efp-financial-model/SKILL.md`.
- **Named ranges:** All cross-sheet refs in the financial model MUST use named ranges. Use Sheets API `findReplace` with `includeFormulas: true` for bulk migration.
- **SUMIFS empty cell bug:** `"<>1"` does NOT match empty cells. Use subtraction: `(full total) - (SDE=1 only)`.
- **Budget rows need ALL columns K-Q populated.** Empty multiplier = 0 in SUMPRODUCT → silently zeros out line items.
- **Sign conventions:** Revenue = Credits - Debits; COGS/Expense = Debits - Credits; CF adjustments = Credits - Debits (except depreciation = Debits - Credits).
- **Account name matching:** CB column A must match `transaction details` column N exactly. No annotations.

## Model Setup
- **Primary:** Opus (claude-opus-4-6) with `context1m: true`, **Fallbacks:** Sonnet → Haiku (auto)
- Sonnet also has `context1m: true` — both models get 1M context window
- Aliases go *under each model entry* as `"alias": "name"` in `openclaw.json`
- Gateway handles fallback transparently — check `/status` after suspicious behavior
- Switched primary from Sonnet→Opus on Mar 17. New sessions get Opus + 1M ctx.

## Financial Model State (Mar 11, 2026 — end of day)
- Three-statement model reconciled; APIC+GW fix applied (see prior entries for detail).
- **Deal Terms row layout (current):** B30=Enterprise Value (manual), B31=Buyer Equity, B33=WC Bridge, B35=SBA Fee formula, B41=Senior Loan formula, B43=SBA Amount, B46=SBA Payment, B48=SN1 Amount, B51=SN1 Payment, B53=SN2 Amount, B57=Forgivable toggle, B60=LOC Amount.
- **APIC formula (BS F80:I80):** `=B31-B32-B34` = $329K. Cash plug = B33 (WC Bridge) at close — algebraically proven.
- **Forgivable toggle (Deal Terms B57):** TRUE/FALSE. LOC column J: `IF($B$57, 0, MIN(0, SN2!E))`. Sheets auto-updates reference if rows shift.
- **Sources & Uses table (rows 16–26):** B19=Total Sources, B26=Total Uses. Conditional formatting flags mismatch red.
- **Health check threshold:** `< 0` (restored Mar 11 after scenario testing at -$10,000).
- **SBA Guarantee Fee (B35):** auto-calculates from B43 (loan). Paid from owner equity — NOT financed. B41 excludes B35 to avoid circular ref. Sources = Uses at close confirmed ✓.
- **Email sent to Marc (Mar 11):** 3 scenarios — S1 $2.3M/2.90x ($2,419K comp), S2 $2,710K/3.42x + $410K forgiveable ($2,892K comp), S3 $3M/3.78x + $700K forgiveable ($3,227K comp). All share $26,018/mo mandatory debt service.
- Skill docs: `predictive-lines/excel-fire-ai` commit `f7cdf15` (Mar 11 end of day).
- For detailed row maps and formulas, see `efp-financial-model` skill references.

## Household Finances (Tiller)
- **Sheet:** `1iVQLLvx5UC62zdcxlHM8s-UcMALCzLwr3EIcbPKuqvc` — Tiller Foundation Template 2026
- **Skill:** `~/repos/excel-fire-ai/skills/household-finances/` — covers Budget columns, account_balances_per_period formula logic, auth pattern
- **Key fix (Mar 15 2026):** account_balances_per_period formulas now gate on start date (`elapsed_start < 0 AND start > P$1` = suppress pre-load) and end date (`col_month >= end_month` = hard zero). Period formula also uses `elapsed < 0 AND start > P$1` for pre-start zero. End check uses `>=` and returns `0` not `prior`.
- **Cash Burn Down tab (May 13 2026):** Added `Cash Burn Down` sheet to Tiller workbook. Uses current `Accounts` balances + `Budget` scheduled cash flows + `Transactions` actuals to model 5-year monthly household runway. Funding sequence: `Working Capital` + `Accrual Accounts` assets first, then brokerage `xxxx1788`, then `Currently Available Tax Free Inheritance`. At build time: spending pools ≈ $43.6K, brokerage ≈ $414.3K, inheritance ≈ $616.8K; runway did not hit $0 in 5-year view (Dec 2030 ≈ $330K remaining). Important column mapping: `Transactions` has a leading blank column, so Amount is E and Month is I. Follow-up improvement: automate “checking dangerously low vs next 14 days of expenses” trigger; current model switches pools when spending pool hits $0.

## Financial Model Fixes (Apr 3, 2026) — Depreciation Overhaul
- **Bug 3 — Stepped-up basis:** BS F30 (Vehicles) = 73,248.39 (FMV), BS F31 (Accum Depr) = `MAX(-F30, 0-IS!F64)` = -30,000. Asset sale = no inherited depreciation history.
- **Bug 1 — BS Accum Depr accumulation:** BS G31:M31 all use `=MAX(-col30, prior31-'Income Statement'!col64)`. Was broken: J31-M31 just copied prior period.
- **Bug 2 — PP&E floor at $0:** MAX guard prevents Accum Depr from exceeding gross asset value. Total PP&E: $73,248 → $43,248 → $13,248 → $0 → $0...
- **IS depreciation cap:** Each IS F64:M64 SUMPRODUCT wrapped in `MIN(SUMPRODUCT, 'Balance Sheet'!prior_col32)`. Depreciation stops when PP&E = 0.
- **Cash bridge depreciation cap:** Same fix on CB row 63 December cells (CQ/DT/EG/ET/FG/FT/GG/GT) — each `MIN(SUMPRODUCT, 'Balance Sheet'!prior_col32)`. CB row 92 (CF add-back) auto-references row 63.
- **Row 32 (Total PP&E) J-M:** Changed from copy-prior to `=SUM(col30:col31)`.
- **Sign convention (stepped-up basis):** Vehicles = +73,248 (positive), Accum Depr starts 0 → goes negative. MAX guard = `MAX(-Vehicles, prior - depreciation)`.
- **IS/CB agreement verified:** Both show $30K/$30K/$13,248/$0/$0/$0/$0/$0. BS CHECK = $0 all periods.

## Financial Model Fixes (Mar 25, 2026)
- **LOC schedule retainage sign**: M column was `+IF(YEAR>=2027, SUMPRODUCT(...))` — should be `-IF(...)`. Retainage holds reduce cash.
- **LOC schedule depreciation multiplier**: G column was hardcoded `$O$` (FY2027 multiplier). Fixed to dynamic `IF(YEAR>=2029, Q, IF(YEAR>=2028, P, O))`.
- **CFS duplicate row**: Had two "Accumulated Depreciation" rows (11 and 12) — deleted row 12.
- **Budget COGS seasonality**: Replaced 3 flat monthly DM/Subs entries with 24 seasonal entries (freq=12, proportional to monthly revenue share). New DM rows 40-51, Subs rows 52-63. Annual totals unchanged.
- **AP days**: Changed from 30 → 60 (Business Model Inputs B100, named range `ap_days`). AR stays at 90 (B99).
- **CB tax fix**: FY2026 NI sum range was `$CJ$87:$CQ$87` (included pre-close May) → fixed to `$CK$87:$CQ$87`.
- **Max shortfall after all fixes**: -$34K (Aug 2028) with $250K LOC. Recommended $300-325K. Justin to confirm.
- **Row deletion lesson**: Always verify row contents immediately before deleting — 0-indexed math is error-prone when rows shift.

## Field Crew Communication Architecture — Path C Decision (Apr 18, 2026)
- **Architecture chosen:** Notion (canonical backend) + Quo (field crew comms bridge) + OpenClaw (glue). Rejected Path A (full SharePoint migration) and Path B (Notion backend + custom web UIs).
- **Core loop:** morning job-assignment text from Notion→Quo→crew; daytime MMS photos optional; evening voice call→Quo transcript→OpenClaw parses→structured Notion update.
- **Why:** field crews confirmed not tech-forward. Native SMS/phone calls only. Zero per-seat licensing for field. Notion heavy-user seats only (~4 × $24/mo).
- **Phase plan:** Phase 1 = morning outbound pilot with one crew member + one job type (candidate: Keith). Phase 2 = evening voice inbound w/ TaskFlow parsing. Phase 3 = scale or retreat. Full spec in Notion: ai-space > Human Readable Reports > "Field Crew Communication Architecture — Phase Plan" (page id: `3477e702-d98c-8121-acbf-dd81a1848f35`).
- **SharePoint migration PAUSED:** don't delete existing SP Lists (Jobs, Customers, Vendors, etc.) but don't build more. Retire after Phase 1–2 validate. SharePoint retains long-term role only for document libraries with printable reports.
- **Company Cam deferred:** Phase 3+ decision, not Phase 1. Try Quo MMS first.
- **OpenClaw is the developer** for this build — ongoing maintenance obligation acknowledged.

## Notion Meeting Notes Access (Apr 18, 2026)
- **Notion AI Meetings captures are accessible via the existing `open-claw` Notion integration** — no MCP server, no Otter, no Granola tunnel needed.
- **Data source:** `Meeting Notes` (id: `2847e702-d98c-80df-a583-000b5473f3d7`, database_id: `2847e702-d98c-80b5-aea2-d31066fd0432`).
- **Columns:** Meeting name (title), Date, Attendees (rich_text), Summary (rich_text), Created by.
- **Page body structure:** Notion stores AI Meetings content as a special `transcription` block containing three named child blocks:
  - `summary_block_id` → AI-generated action items (heading_3 + to_do blocks with speaker-attributed tasks)
  - `notes_block_id` → Agenda + manual notes sections
  - `transcript_block_id` → Full verbatim transcript as paragraph blocks
- **Access pattern:** `GET /v1/blocks/{page_id}/children` returns the transcription block with `children: {summary_block_id, notes_block_id, transcript_block_id}` pointers. Follow each pointer with `GET /v1/blocks/{block_id}/children` to extract content.
- **Pricing:** Notion Business @ $24/user/mo bundles AI Meetings. Only Justin needs a seat for meeting capture (Jaclyn optional). Otter would have been $30/mo for meetings only with an unofficial MCP and a password-sharing auth model — worse on every dimension.
- **Cancelled/rolled back Apr 18:** Otter trial account, `otter-mcp` repo clone, `~/.config/otter/credentials`, and OpenClaw `otter` MCP registration all torn down after discovering Notion already solved this.
- **Security note:** Justin pasted an Otter password in Slack thread during the trial setup. Password file was shredded; Justin advised to rotate/disable the Otter local password since the MS SSO account is the primary auth path.
- **Open question:** Meeting Notes DB may contain personal meetings (e.g., OBGYN scheduling, family calls) alongside business. Justin to decide whether to segregate private meetings into a separate DB or accept full-scope access for the integration.

## Platform Migration — Notion → Microsoft 365 (Apr 14, 2026)
- **Direction:** Full migration from Notion to M365 stack. Notion retained temporarily during transition only.
- **Task management:** Microsoft To Do, managed via custom Outlook MCP (`ai-team/excel-fire-ai/mcp-servers/outlook/`, `github-custom-mcp` connector in Cowork).
- **Operational databases (job tracker, billing, COs, inspections, vendors):** Migrated to SharePoint Lists (Apr 14, 2026). All 5 lists created with full column schemas on dedicated EFP site.
- **Living documents (policies, processes, KB):** SharePoint site + document library. Printable formatting is critical for field crew — Notion's print output was a dealbreaker.
- **Document archival (contracts, calcs, plans, invoices):** Evaluating consolidation into SharePoint + retention policies (see below). Paperless-ngx MVP may become redundant if SharePoint handles full lifecycle.
- **Meeting capture:** Evaluating **Granola** ($14/user/month) — macOS + iOS local audio capture for phone calls and in-person meetings. Testing started Apr 14, 2026. Only Justin (+ maybe Jaclyn) need licenses vs. Notion requiring per-seat for all viewers. iOS 18 native call recording covers phone calls for free; Granola adds in-person meeting capture + AI minutes.
- **Document retention options:**
  - **MS Purview:** Correct tool (auto-apply retention labels, disposition review), but requires Business Premium or E3 licensing — not included in Business Basic/Standard.
  - **SharePoint library-level retention:** Basic information management policies available on all plans. Less sophisticated but workable for a small company with clear folder structure.
  - **Paperless-ngx:** Still viable as free self-hosted option. Custom Claude classifier is unique value-add. Could be replicated via Power Automate + Claude API if consolidating to SharePoint.
- **SharePoint storage:** 1TB base + 10GB/user. ~1.1TB at 10 users. Estimated 50-100GB/year for EFP docs — 10+ year runway. Not a concern.
- **License economics (draft):** Notion 8 seats × $24 = $192/mo. M365 (already paid) + Granola 2 seats × $14 = $28/mo net new. Delta: ~$164/mo ($2K/yr savings).
- **Claude as primary UI:** Goal is to manage To Do tasks, Lists data, and SharePoint docs through Cowork conversation rather than switching between app UIs.
- **Custom MCP status (Apr 14, 2026):** All modules built and deployed via consolidated Caddy + ngrok bridge:
  - Mail, Calendar, To Do, Contacts, Teams — original modules, working
  - OneNote — 7 tools (notebooks/sections/pages CRUD), working
  - SharePoint Lists — 8 tools (site discovery, list/item CRUD), working
  - Drive/Files — 7 tools (drive discovery, file CRUD, search), working
  - Connector UUID: `mcp__f8b788a1-6e53-4af3-bbb6-544f02c6fa19`
  - Auth scopes: User.Read, Mail.Send, Mail.ReadWrite, Calendars.ReadWrite, Tasks.ReadWrite, Contacts.ReadWrite, Chat.ReadWrite, ChatMessage.Send, ChannelMessage.Send, Notes.ReadWrite, Sites.ReadWrite.All, Sites.Manage.All
- **Granola MCP connector:** Connected Apr 14, 2026. UUID: `mcp__46f98651-5ea3-4b3c-bf18-e7a9f06f8331`. Read access to meetings, summaries, transcripts. Test meeting captured successfully.
- **Document classifier plan:** Cowork scheduled task replaces Paperless-ngx classifier. Reads new unclassified docs from SharePoint library via drive MCP tools, classifies using Claude (no separate API call), writes metadata back via lists MCP tools. Eliminates custom FastAPI container + separate Anthropic API billing.
- **Granola → OneNote pipeline (planned):** Pull meeting notes from Granola MCP, push to OneNote via onenote MCP. Consolidates searchable notes in one place.
- **Rehydration prompt for job tracking migration:** `ai-team/agent-workspace/rehydration-sharepoint-job-tracking.md` — full schemas for all 4 Notion databases, column type mappings, migration plan, and open questions for Justin.

## SharePoint Lists — EFP Job Tracking (Created Apr 14, 2026)
- **Site:** Excel Fire Protection — `predictivelines.sharepoint.com/sites/ExcelFireProtection`
- **Site ID:** `predictivelines.sharepoint.com,bd30c4c0-309c-4b98-95ce-451ac7a512f9,4ed57ca4-1a8f-432d-9c7b-34e4002454fb`
- **Lists:**
  - **Installation Jobs** — ID: `e99a4f2a-efd7-4f6d-b00d-8f3fa8ec659b` — 64 custom columns (15 text, 9 URL-as-text, 15 number, 17 date, 7 choice + 1 multi-select-as-choice, Title)
  - **Inspection Jobs** — ID: `f8806888-1214-4100-8e93-bbc77dfdba38` — 31 custom columns (12 text, 4 URL-as-text, 4 number, 3 date, 2 boolean, 6 choice)
  - **Billing Log** — ID: `34326b35-5dc1-4c76-a3cc-a1a0014c480a` — 15 custom columns (5 text, 1 URL-as-text, 4 number, 2 date, 1 boolean, 2 choice)
  - **Change Orders** — ID: `4bf08c6b-f2ff-4f96-819e-c9c6cf85a7e1` — 19 custom columns (5 text, 3 URL-as-text, 6 number, 3 date, 1 boolean, 1 choice)
  - **Vendors** — ID: `f29f0ae0-1d78-4696-84ce-4e897abea69e` — 12 custom columns (6 text, 1 date, 3 boolean, 2 choice)
- **Column naming:** CamelCase internal names (e.g., `JobNumber`, `SiteAddress`, `BillingStatus`). Title field = built-in SharePoint Title column.
- **Notion title → SharePoint Title mapping:** Job Name, Inspection Name, Invoice Description, CO Description, Vendor Name → all use `Title` field.
- **URL columns:** Created as text (not hyperlink) — Graph API `hyperlinkOrPicture` column type not tested. Can be changed to hyperlink in SP UI later.
- **Multi-select:** SystemType created as single-select choice for now. SharePoint choice columns support multi-select via UI toggle but Graph API `allowMultipleValues` flag not tested at creation time.
- **Lookup columns (cross-list):** Not yet created. Billing Log and Change Orders have `InstallationJob` as text field placeholder. Lookup columns can be added via Graph API `POST /columns` with `lookup` type definition pointing to Installation Jobs list.
- **Notion source databases (schema only, no data):** Installation Jobs (`collection://1520bbc9-8b95-4f65-ae79-dd9af8b0149c`), Inspection Jobs (`collection://ec4151a2-461f-43da-b6c4-6d08c04ea3ae`), Billing Log (`collection://fff66844-83ec-4a79-82e5-18f29f95aaa1`), Change Orders (`collection://8dd7cd0a-0f47-45e5-a02d-d42b612bd235`), Vendors (`collection://bc0a6838-c250-4e35-8f71-493dac676ce9`).
- **Permission lesson:** `Sites.ReadWrite.All` allows item CRUD but NOT list/column creation. Need `Sites.Manage.All` for structural changes (creating lists, adding columns). Added to MCP auth scopes Apr 14, 2026.
- **Deferred to v1.1:** Calculated columns (% Complete Default, Net Due, Days Since Submitted), gate logic, status transition rules, lookup columns for cross-list relations.

## Decisions & Preferences
- Default to New Construction when web search inconclusive for revenue classification
- RoughCountry.com = SDE=0, Calder Capital = Adj=1 (not SDE)
- All airfare, Mexico/Hawaii charges, jewelry stores = SDE=1
- Truck expenses = legit business, not SDE
- Safeway on Direct Materials = misclassified meals, SDE=0
- Travel & Entertainment account = ALL SDE=1 (CPA reclassified full balance to owner draws)
- Year-end T&E reclassification JEs = SDE=1 + Adj=1
- Donations, Pension Expense, Officer Salary accounts = always SDE=1
- FY2026 partial year: only Oct–Jan shown (4 months)

## Location Preferences
- **Default to Michigan** for vague location-based questions unless there's a specific reason to assume otherwise (e.g., Justin mentions a city/state, or context is clearly elsewhere).
- Green Oak Village Place = Brighton, MI (not Arlington, TX).

## Communication Preferences
- **Always thread replies on Slack.** Use `[[reply_to_current]]` or `threadId`.
- **Content delivery default:** Show content in-app first (Cowork chat). After revisions are finalized, write to Notion (primary) or occasionally .docx. Don't default to generating .docx files upfront.
- **Reset context after closing a thread.** Don't carry stale context forward.

## Household Cash Flow Map (Tiller Sheet5)
- **Sheet5 gid**: `1651006235` (tab still named "Sheet5" — Justin to rename manually)
- **Tiller Budget projected tuition rows**: 183=Cora 2027-28, 184=Eve 2027-28, 185=Cora 2028-29, 186=Eve 2028-29, 187=Cora 2029-30, 188=Eve 2029-30 — all at current amounts ($4,091.62 Cora / $3,635.45 Eve), labeled "Projected — update when school confirms rate"
- **Education 2029 updated**: Sheet5 AP18:BB18 reflects 2029-30 school year tuition starting June 2029. Annual 2029 Education = -$97,729.74 (was $9,600 placeholder)
- **Business Plan BP Budget payroll split (Mar 2026)**: Row 76 = Justin Miller Officer Salary (start=proposed_close_date, amt=HR!H14/12); Row 77 = Jaclyn Miller Officer Salary (start=HR!I15=1/1/2028, amt=HR!H15/12). Both sheets (cash bridge + IS) pick up the split automatically via SUMPRODUCT.
- **Sheet5 DATA LINKS row (55)**: C55=Justin salary, D55=Jaclyn salary, E55-H55=CFS FY2026PC-FY2029, I55-L55=CFS FY2030-FY2033 (all via IMPORTRANGE from BP model)
- **Sheet5 Row 41**: Annual CFS pulls reference $E$55-$L$55 for respective FY totals
- **Auth**: Tiller must be accessed via predictivelines account (NOT oneoaks), despite being millerjl@oneoaks.net sheet

## Cash Bridge Extension (Mar 17, 2026)
- Extended through FY2033: EU-GT (53 cols), GU=DATE(2034,1,1) terminator
- All formulas templated from EI (monthly) and EH (annual)
- Revenue flat FY2030+ (Budget!$Q multiplier only)

## Payroll & Konner Transition (Mar 17, 2026)
- Payroll Calculations extended BE-CZ (Jan 2030 - Dec 2033) with FUTA/SUTA corrected
- Konner Lefebvre: Class 10 (Jan-Jun 2030, Budget row 29) → 4th local JM (Jul 2030+, Budget row 30)
- Rows 31-38: Konner individual benefit rows (Class 10 + JM periods)
- Aggregate benefit rows 89-92 ended 12/31/2029; new aggregates appended at 165-168 (3 JMs + Admin + Officer)

## Headcount & Staff Growth Model (Mar 26, 2026)
- **Completed:**
  - BMI Staff Growth Plan (rows 122-129): Apprentice 1 (3/15/2026), JM Hire 3 (7/1/2028), Apprentice 3 (7/1/2028)
  - PC Headcount Matrix (rows 134-145): Dynamic formulas count people per class per month based on start dates + 6-month class progression
  - PC Aggregate Cost (rows 148-152): Monthly totals for Wages, Union Benefits, FICA SS/Medicare, WC
  - Budget rows 200-294: 95 new rows for field staff
    - Apprentice 1: 11 wage rows (Class 1-10 + JM) + 35 benefit rows (FICA/Medicare/WC per class, plus Union Benefits 2030+)
    - JM Hire 3: 5 rows (wage + all benefits)
    - Apprentice 3: 11 wage rows + 34 benefit rows
  - All rows use formulas referencing PC rates (not hardcoded), so CBA changes auto-flow
  - Toggle column (S) set to 1 for all new rows to enable SUMPRODUCT in IS
- **Toggle column (S):** MUST be set to 1 for new Budget rows — IS cols G-I multiply by `$S$`. Empty = 0 → row is ignored.
- **Double-count fix:** Aggregate rows (19-20, 72-73, 90, 110-113, 186-189) had `×3` coefficient including Konner as JM, but Konner had individual apprentice rows too. Fixed all to `×2` (Keith + Branden only).
- **Final result:** Model **Healthy**, max shortfall $0, BS CHECK $0. NI: FY26 +$27K, CY27 +$42K (fixed double-count), CY28 -$102K, CY29 -$256K (new hires absorbed by 40% rev growth).

## Headcount Model Architecture (Mar 26, 2026 — earlier notes)
- **Problem:** Excel Fire needs flexible staffing model where adding a hire (to BMI) automatically scales wages/benefits through Budget → IS/BS/CFS
- **Solution:** Headcount-driven model with coefficient multipliers per class level
  - **BMI Staff Growth Plan (rows 122-127):** One row per person: Name, Role (JM/Apprentice), Start Date, Starting Class (apprentices only)
  - **Payroll Calculations Headcount Matrix (rows 134-145):** For each month (F-CZ), counts people at each role/class using formulas
    - JM count = COUNTIFS(role=JM, started) + SUMPRODUCT(role=Apprentice, started, class>10)
    - Class N count = SUMPRODUCT(role=Apprentice, started, class=N) where class = 1+INT(months_since_start/6)
  - **Payroll Calculations Aggregate Cost (rows 148-152):** Monthly totals for Wages, Benefits, FICA, Medicare, WC
    - Each cell = SUM(headcount_JM × rate_JM + headcount_C1 × rate_C1 + ... + headcount_C10 × rate_C10)
- **Budget restructure (pending):** Replace per-person rows with period-based rows × Qty coefficient
  - E.g., `Apprentice Class 3` start 7/1/26 end 12/31/26 Qty=1; start 1/1/27 Qty=2 (new hire enters Class 3)
  - Modify SUMPRODUCT in IS/CB/LOC to include `× Budget!$T` (Qty column)
- **Verified:** May 2026 (2 JM + 1 C1 + 1 C2), Jul 2026 (Konner → C3), Jan 2027 (2 JM + 1 C2 + 1 C4) — all correct
- **Next:** Budget row restructure + SUMPRODUCT updates (pending user decision on scope)

## CFS Debt Principal Fix (Mar 17, 2026)
- **CFS row 53 cols J-M**: Fixed Budget column reference ($I$→$H$) — was looking in Notes instead of Account
- **Budget rows 177-184**: Added SBA 7a + Seller Note principal for FY2030-2033
- Seller Note: 60-month loan, pays off Apr 2031 — FY2031+ rows = $0
- **Verified clean**: CFS rows 53/57 all clean. Debt Principal: FY30=-$218K, FY31=-$163K (SN payoff), FY32=-$175K, FY33=-$188K
- **Budget debt rows now at 169-176** (shifted after deleting duplicate batch)
- **Tiller Yearly Budget tab is volatile**: Row numbers shift when categories change. Sheet5 expense formulas now use dynamic INDEX/MATCH (fixed Mar 17). BUSINESS uses FILTER(...,2) for 2nd occurrence.
- **Tiller Sheet5 row 12**: Must include rows 7-11 (not 7-10). Row 11 = 529 Disbursement.
- **Cash Bridge December columns**: Must skip annual total columns (containing "Total" text) when referencing next-month date. FY2030-2032 Decembers fixed Mar 17 (FG→FI, FT→FV, GG→GI).
- **Cash Bridge row 2 dates FY2030-2032**: Were formatted as currency, fixed to M/d/yyyy.
- **Seller Note schedules**: Both SN and SN2 now have IF(balance<=0, 0, formula) guards past row 64 (60-month payoff). No more #NUM! or negative balances.
- **Budget debt rows now at 169-176** (SBA 7a + Seller Note principal FY2030-2033, freq=12/annual)

## HR Compliance & Functions Guide (Apr 8, 2026)
- **Published to Notion:** Human Readable Reports > "HR Compliance & Functions Guide" (page id: 33c7e702-d98c-817a-bc7f-c1587f46cad5)
- **Scope:** Federal, Michigan state, and local (Marquette) HR regulatory requirements + practical HR functions for a small union construction business.
- **Key findings:** Local 669 CBA offloads wages/benefits/pensions/training to union; employer retains payroll tax, MIOSHA safety, workers' comp, I-9, ESTA, and full HR for non-union staff. Marquette has no city income tax. Title VII/ADA likely apply (15+ threshold). FMLA/ACA do not (under 50). Sister company must maintain strict separation to avoid NLRB single-employer risk.
- **Data Retention Policy updated:** Added I-9 (IRCA) and ESTA sick time rows to Section 4.3 of the Notion Data Retention Policy (page id: 3047e702-d98c-81df-9af9-c85fee600394).
- **Also generated:** `ai-team/hr-compliance-guide-excel-fire.docx` (superseded by Notion version).

## Sister Company — Fire Extinguisher Inspection & Service (Apr 8, 2026)
- **Concept:** Separate LLC (non-union) for portable fire extinguisher inspection, recharge, and hydrostatic testing. Shared back office with Excel Fire. Potential to bundle fire alarm inspections.
- **Market opportunity:** Zero providers in Marquette area. Previous provider (Lammi) was acquired by Summit Fire Protection (PE roll-up) and stopped offering local extinguisher service. Excel Fire gets ~1 call/day asking for the service with no one to refer to.
- **Pricing strategy:** 10-15% above highest market rate — still cheaper than customers replacing extinguishers they can't get inspected. ~$678/visit at 15 units avg.
- **Breakeven:** ~144 accounts/year (~2.9/week), ~58% conversion on Excel Fire inbound leads. Year 1 base case nets ~$13K; Year 2 ~$73K; Year 3 ~$123K.
- **Startup cost:** ~$47K (used AWD Transit van ~$22K, recharge/hydro equipment ~$16K, inventory/tools/licensing ~$9K).
- **Licensing:** MI has no state-specific fire extinguisher service license. ICC/NAFED Certified Portable Fire Extinguisher Technician exam (100 Q, open-book) is the industry credential. Fire alarm work requires separate MI FAST license (NICET II + 4,000 hrs).
- **Structure:** Sister LLC to avoid Local 669 CBA jurisdictional issues. Separate EIN, payroll, insurance. Shared back office, CRM, phone system with Excel Fire for warm handoffs.
- **Breakeven model:** `ai-team/fire-extinguisher-breakeven-model.xlsx` — 3 tabs (Assumptions, 3-Year Projection, Scenarios).
- **Lead — Travis (last name TBD):** Former Lammi alarm tech, may have extinguisher experience. Both Keith and Kevin previously tried to recruit him; he reportedly switched careers to work at a fish hatchery (or similar). Worth reaching out — if he has MI FAST license from Lammi days, that's a huge head start on the alarm bundling side. Extinguisher ICC/NAFED cert would be quick to add. Get contact info from Excel Fire office staff.

## IT & Operations Infrastructure (Apr 8, 2026)

### Digital Records Management Policy (EFP-DRM-002)
- **Published to Notion:** Human Readable Reports > "Digital Records Management Policy" (page id: 33c7e702-d98c-8120-a9a2-f6f41e27646d)
- **Local file:** `ai-team/data-classification-and-retention-policy.md`
- **Key decisions:** 4-tier data classification (Restricted→Bitwarden, Confidential, Internal, Public). Paperless-ngx as document management interface. S3 backend with lifecycle policies mapped to 7 retention tiers (1yr through life-of-system + permanent). Content scanning safeguards for misclassification. Offsite DR via S3 Cross-Region Replication (us-east-2 → us-west-2). Daily reports tagged `daily-report` + `job:XXXX-XXXX` + `retain-7yr` + `internal` via Raken auto-email → Paperless-ngx auto-tagging.

### Site Infrastructure Standard — EFP Location Kit
- **Published to Notion:** Human Readable Reports > "Site Infrastructure Standard — EFP Location Kit" (page id: 33c7e702-d98c-81c4-a9bb-f67e91334093)
- **BOM:** ~$2,130/site. Ubiquiti Cloud Gateway Ultra (networking/WiFi/PoE/WireGuard VPN), UniFi G5 Turret camera + UniFi G4 Doorbell, Yale Assure Lock 2 (Zigbee) + NFC tag stickers, LiftMaster 87504 + ratgdo garage door, Beelink SER7 Docker host, Aqara Zigbee sensors (SONOFF dongle), Emporia Vue power monitor, Ecowitt weather station, UPS.
- **Lock swap (Apr 10 2026):** Schlage Encode Plus → Yale Assure Lock 2 (Zigbee). Schlage was cloud-dependent for HA and didn't provide per-PIN-slot attribution. Yale via ZHA gives fully local operation + code-slot logging. NFC phone-tap unlock via NTAG215 stickers + HA Companion App automations on company phones.
- **Doorbell camera added (Apr 10 2026):** UniFi G4 Doorbell ($199). Records to same Protect instance as security camera. Two-way audio for visitor intercom.
- **Docker stack:** Paperless-ngx, Vaultwarden, Home Assistant, PostgreSQL. WireGuard VPN native on Ubiquiti router (no Tailscale needed). Config repo: `efp-site-config/` with docker-compose.yml + per-site .env files.
- **Expansion path:** Frigate NVR with Google Coral TPU for AI camera detection.

### IT Policies (EFP-ITP-004)
- **Published to Notion:** Human Readable Reports > "IT Policies — Excel Fire Protection" (page id: 33e7e702-d98c-81de-b1f3-f9df5c3f1a3b)
- **Scope:** 6 parts — Acceptable Use, Information Security, Access Control & User Management, Incident Response, Policy Administration, Physical Access.
- **Key resolved decisions (Apr 10 2026):**
  - Email: M365 (already in place)
  - Field crew devices: Company phones for journeymen (CBA requirement for work functions). Apprentices on personal devices. Revisit at 6mo.
  - IT backup: Jaclyn (day-to-day) + MSP friends network (break-fix)
  - Cyber insurance: Being quoted by Gauthier Insurance
  - Smart lock: Yale Zigbee + NFC tags (see SIS-003 note above)
  - Doorbell: UniFi G4 Doorbell
- **Additional resolved decisions (Apr 10 2026, batch 2):**
  - VLANs: Approved 5-VLAN layout (Management/Corporate/IoT/Guest-BYOD/Camera)
  - Bitwarden: Mandatory for all employees with system access
  - Camera audio: Enable on ALL cameras (turret + doorbell). Remote warehouse monitoring. Post signage.
  - LUKS encryption: Yes, with TPM auto-unlock required (unmanned warehouse must survive unattended reboot). Fallback: FIDO2 key in chassis, or skip LUKS if neither works.
- **Open decisions (5 remaining):** Endpoint protection (pending Gauthier cyber insurance terms), security training formality, foreman Paperless access level, WiFi auth model, sister company IT scope.
- **Physical access model:** 4-layer — NFC tag tap (company phone + HA), keypad PIN (Yale/Keymaster), temporary PIN (visitors), physical key (GM only). All events logged to HA, exported monthly to Paperless-ngx.

### Job Lifecycle & Database Design — v1 LIVE (Apr 11, 2026)
- **Proposal page:** "Job Lifecycle & Database Design Proposal" (page id: 33c7e702-d98c-81f3-8b0c-c9c72d5c3715)
- **Local file:** `ai-team/job-lifecycle-proposal.md` (790 lines, comprehensive)
- **Hub page:** "EFP Job Tracking" (page id: 33f7e702-d98c-814b-937c-e7f1e24c11a6) under ai-space
- **4 databases LIVE:**
  1. **Installation Jobs** — DB: `4c26094652b8490d9ec366197d9315bc`, DS: `1520bbc9-8b95-4f65-ae79-dd9af8b0149c`. 21-status flow + 7-value Billing Status. ~60 properties (core info, classification, design sub, billing/financial, 12 milestone dates, 11 document link URLs, Raken/Paperless integration). Views: Pipeline (board), Active Jobs, Revenue Tracker, Design Tracker, Service/Repair.
  2. **Inspection Jobs** — DB: `fff4c91514c64b3e8748bf94435f67e7`, DS: `ec4151a2-461f-43da-b6c4-6d08c04ea3ae`. 9-status flow. Deficiency tracking with severity, repair job link. Inspect Point integration. Views: Pipeline (board), This Month (calendar), Deficiencies Open.
  3. **Billing Log** — DB: `d7fd5f94ac39487daef51873b07c2cd1`, DS: `fff66844-83ec-4a79-82e5-18f29f95aaa1`. Per-invoice tracking (Progress, Final, Retainage, CO, Stored Materials). Lien release per draw. Views: Unpaid Invoices, By Job.
  4. **Change Orders** — DB: `76ead8e2ca2f42619c400f3004227f77`, DS: `8dd7cd0a-0f47-45e5-a02d-d42b612bd235`. 11-status CO lifecycle. Signed CO Link = strictest hard gate. Views: Open COs, Awaiting Signature, By Job, Revenue Impact.
- **Cross-database relations:** Installation Jobs ↔ Customers (dual), Inspection Jobs ↔ Customers (dual), Billing Log → Installation Jobs (dual "Billing Log"), Change Orders → Installation Jobs (dual "Change Orders").
- **Deferred to v1.1:** Formula fields (% Complete Default, % Complete Effective, Job Closed, Risk Flag, Gate Blocked, Net Due on Billing Log, Days Since Submitted on COs). These require Notion formula syntax testing.
- **Migration plan:** 4 phases (create DBs ✅ → migrate active jobs → retire old DB → calibrate % Complete defaults after 10-15 jobs)
- **Still pending:** 14 review questions for Justin, Jaclyn, Keith & Kevin.
- **Delivered earlier:** Workflow diagram (PNG) + Word document: `ai-team/job-lifecycle-workflow.docx`.

## Paperless-ngx MVP Bootstrap (Apr 9, 2026)
- **Trigger:** Justin + Krissy starting to scan all EFP active jobs + estimates. Needs document management stand-up *now*, not after full site kit deploys.
- **MVP hardware:** Broken-screen laptop at Justin's house as Docker host (headless, Ubuntu Server 24.04, `HandleLidSwitch=ignore`). Existing in-office ScanSnap covers scanning (working well). External USB SSD for local backup. Full Beelink SER7 + Cloud Gateway + cameras/locks/sensors deferred — all orthogonal to doc-mgmt MVP.
- **Software stack (6 containers):** paperless-ngx, postgres:16, redis, gotenberg (office→PDF), tika (metadata), claude-classifier (custom FastAPI, suggest-not-apply). Consume folder exposed via Samba as `\\paperless\consume` with subfolders per scan profile (active/estimates/archive/daily-reports) → paperless workflows auto-tag by source path.
- **Locked taxonomy decisions:**
  - **Job naming (updated Apr 12 2026):** Address-based slugs — canonical slug is `<street-number>-<street-name>-<street-suffix>` in lowercase kebab-case (e.g., `job:1234-fraternity-row`). Rationale: field crew already defaults to addresses on paperwork and daily reports; addresses appear verbatim on permits/invoices/correspondence making classifier matching more reliable; eliminates the translation layer between field and office naming. Office nicknames (e.g., "omega house") are now aliases, not the canonical identifier. Conflict resolution: append `-2` serial suffix only when a duplicate address actually occurs. Edge cases: shop work uses descriptive slugs (`efp-shop`), multi-building uses building suffix (`500-washington-st-bldg-b`). Old convention was short human-readable slugs — migrated.
  - **Unsorted bucket:** `job:unsorted` tag for ambiguous docs at scan time; Krissy triages during downtime.
  - **15 document types:** Estimate, Proposal, Contract, Drawing/Submittal, Hydraulic Calculations, Permit, Change Order, Invoice, Receipt, Lien Waiver, Daily Report, Inspection Report, Correspondence, Business Card, Other.
  - **Storage path:** `{job}/{document_type}` (human-browsable even if paperless is later retired).
  - **Retention:** Tags only for MVP (`retain-1yr`, `retain-7yr`, `retain-10yr`, `retain-life`). S3 lifecycle enforcement comes after model is proven.
  - **Barcode batch splitting:** Enabled from day 1. Separator sheets printed from a PDF in the repo.
  - **Email ingestion:** Deferred.
  - **AI classification:** Claude API, suggest-not-apply mode. Routes OCR text only (not PDFs). Classifier proposes document type + correspondent + job + title; Krissy approves. Key lives at `ai-team/.config/anthropic/api_key`, provisioned under predictivelines account until EFP has its own.
  - **Backups:** Nightly `pg_dump` + `rsync` media to external USB SSD. Weekly automated restore test to scratch container. Configured *from day 1* — document retention is a legal compliance requirement, untested backups don't count.
- **Repo:** `predictive-lines/efp-site-config` (new, Option A — front-loads the future site-config structure). `paperless-bootstrap/` is the first subdirectory inside it.
- **Gap flagged in EFP-SIS-003:** Site Infrastructure Standard BOM does not include a scanner. Needs update to list ScanSnap iX1600 (office-grade) and a simple Brother/Canon MFP (satellite-site grade) as acceptable options, plus cross-ref to paperless-bootstrap.

## Google Workspace MCP — Two Accounts (Apr 19, 2026)
- MCP server: `google-workspace` at `~/repos/google-workspace-mcp-live/` (v2.3.6, multi-account support).
- Config store: `~/.google-mcp/accounts.json`, tokens at `~/.google-mcp/tokens/<name>.json`.
- **Account `predictivelines`** (work, `justin.miller@predictivelines.com`) — GCP `open-claw-integration-488119`. Uses global `~/.google-mcp/credentials.json`.
- **Account `oneoaks-personal`** (personal, `millerjl@oneoaks.net`) — GCP `open-claw-personal-493814` (External/Testing, external app because oneoaks wanted cross-domain). Per-account creds at `~/.config/google-personal/oauth_credentials.json`.
- Both accounts: Gmail/Calendar/People/Drive/Sheets enabled. Docs/Slides/Forms deliberately off until needed (minimal-scope principle).
- **Do NOT touch `~/.config/google/`** — separate credentials used by standalone Python scripts (cash-bridge-builder, Tiller helpers, etc.); different OAuth clients entirely.
- Known bug in v2.3.6: `accounts add -c` writes token file with global client_id/secret instead of per-account; harmless at runtime but fix cosmetically with `node -e "..."` rewrite. Full detail in TOOLS.md under "Google Workspace".
