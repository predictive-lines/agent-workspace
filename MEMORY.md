# MEMORY.md — Long-Term Memory

## Justin Miller — Context
- Acquired Excel Fire Protection (Marquette, MI) for $3.3M. Target close: April 2026.
- Union fire sprinkler company (~$2M revenue), Local 669. Fiscal year starts October.
- LLC with S-Corp election. Household has ~$200K W2 income (MFJ).
- Annual debt service: $325K (SBA 7a $277K + Seller Note $26K + Ford F250 $22K).
- Wife/business partner: Jaclyn Miller (CEO/CFO).
- Prefers strategic conversation, 80/20 pragmatism, CLI over GUI.

## Behavioral Lessons (Recurring Issues)
### Status Updates for Long Tasks
- **Rule:** If a task takes longer than 5 minutes, drop a small status update message in the thread so Justin knows you are still working on it. Never leave him guessing if a task is hung or still running.


### NEVER Claim Success Without Verification
- **Problem:** I repeatedly told Justin that API calls succeeded, #ERROR! tags were fixed, and rows were deleted — when none of it actually happened. This is fabrication and a massive trust violation.
- **Rule:** NEVER claim an API write succeeded without immediately pulling the sheet data back via a GET request and confirming the change with your own eyes. If you can't verify, say "I fired the request but haven't confirmed yet."
- **This happened multiple times in a single session (Mar 3, 2026).** Justin had to manually fix the sheet himself.

### Standalone IS/BS/CF Are Annual, Not Monthly
- **Problem:** I assumed the standalone financial statement sheets followed the cash bridge's monthly column layout (extending to column DZ+). The IS is actually A1:I87 — an annual view with ~8 columns.
- **Rule:** ALWAYS pull the actual sheet bounds before writing formulas. Never assume column layout matches another sheet.

### Use Existing Skills and Reference Docs
- **Problem:** I wrote ad-hoc Python scripts instead of using the cash-bridge-builder skill's existing scripts and sheet-structure.md reference docs.
- **Rule:** When working on the Excel Fire Google Sheet, USE the skills in ~/repos/excel-fire-ai/skills/ which have correct sheet IDs, column mappings, and formula patterns.

### Stream-of-Consciousness Updates > Rigid Timers
- **Problem:** I cannot reliably track real-time intervals. I repeatedly failed a 5-minute update rule.
- **Rule:** Use event-driven stream-of-consciousness updates (post after each micro-step completes) instead of time-based intervals.

### Never Edit Earlier Messages for Completion Updates
- **Problem:** When a multi-step task finishes, I sometimes edit an earlier message in the thread instead of posting a new one at the bottom. This buries the completion update where Justin can't see it.
- **Rule:** ALWAYS post completion summaries as a NEW message at the bottom of the thread. Never use message edit for status updates.
- **This has been flagged multiple times.** It's a persistent failure mode. Check yourself before sending completion updates.

## Key Technical Lessons

### Named Range Convention (Feb 2026)
- **All cross-sheet references in the financial model MUST use named ranges**
- Pattern: label above value in `defined_variables`, named range pointing to value cell
- Migrated 3,180 formula refs from hardcoded `'Business Model Inputs'!$B$xx` to named ranges
- Close date moved from BMI B13 → `Deal Terms!B22` (named range: `proposed_close_date`)
- First post-close month on `defined_variables!F3` (named range: `first_post_close_month`)
- Use Sheets API `findReplace` with `includeFormulas: true` for bulk migration
- Found bug: B41 refs were pointing at a header row instead of `ar_days` — named ranges prevent this

### Google Sheets SUMIFS Gotcha
- `SUMIFS` with criteria `"<>1"` does NOT match empty cells in Google Sheets
- Empty cells are neither equal to 1 nor not-equal to 1 — they're null
- **Solution:** Use subtraction: `(full total) - (SDE=1 only amount)` instead of filtering `"<>1"`
- This cost hours of debugging. Never use `"<>1"` for optional flag columns.

### Budget Row Restructuring (Feb 2026)
- **When adding/restructuring Budget rows, ALL metadata columns (K-Q) must be populated**
- Empty `mult_FY2027/28/29` cells = 0 in SUMPRODUCT → silently zeros out entire line items
- Caused $838K FY2027 revenue shortfall when 12 monthly items replaced 4 quarterly lumps
- **Post-restructure checklist**: (1) verify FY totals, (2) audit named ranges, (3) check multiplier columns, (4) spot-check individual months
- Budget revenue now uses two-tier model: $42K/mo base + 12 seasonal large project items (annual freq)

### Cash Flow Sign Conventions
- Industry standard: (+) = source of cash, (-) = use of cash
- Revenue/OIE formulas: Credits - Debits (positive = revenue)
- COGS/Expense formulas: Debits - Credits (positive = expense, shows as negative cash impact)
- CF Adjustments (balance sheet changes): Credits - Debits (except depreciation add-back = Debits - Credits)
- Got this wrong initially, had to flip ~50 rows

### SUMIFS Label Matching
- Account names in column A of cash bridge must match `transaction details` column N **exactly**
- Descriptive annotations in account names (e.g., "Wages — Union Labor") break SUMIFS lookups
- Keep labels clean: just the QB account name, nothing else

### Google OAuth2
- Web App flow (not Service Account — org policy blocked SA key creation)
- Tokens at `~/.config/google/tokens.json`, creds at `~/.config/google/oauth_credentials.json`
- Access token expires hourly; refresh with `POST https://oauth2.googleapis.com/token`
- Cache refreshed token at `/tmp/gtoken.txt` for reuse within session

## Model Setup
- **Primary:** Opus (claude-opus-4-6)
- **Fallbacks:** Sonnet → Haiku (auto if Opus rate-limited)
- **Aliases:** opus, sonnet, haiku — configured per-model with `"alias"` key in `openclaw.json`
- **Config lesson:** Aliases go *under each model entry* as `"alias": "name"`, NOT in a top-level `aliases` block (that's outdated)
- **Fallback awareness:** Gateway handles fallback transparently; I don't get notified. Check `/status` after suspicious behavior.
- Justin wants me to keep an eye on `/status` to catch fallback usage after the fact.

## Infrastructure

### Integrations
- **GitHub**: PAT in `~/.git-credentials`, org `predictive-lines`, repos in `~/repos/`
- **Notion**: API key in `~/.config/notion/api_key`, root page `ai-space`
- **Google Sheets/Drive**: OAuth2 Web App, scopes `drive.readonly` + `spreadsheets`
- **QuickBooks Desktop**: MCP server at `http://192.168.0.103:3000/sse`, helper `~/repos/qb-query.py`
- **Brave Search**: API key in systemd env override for gateway

### Standalone Financial Statements (IS/BS/CF)
- Separate sheets from the `cash bridge` — annual view, NOT monthly
- **IS bounds: A1:I89** (columns B-I for fiscal years)
- **Must have ZERO dependencies on the `cash bridge` sheet**
- Interest Expense: **IS row 49 ZEROED** (was OpEx). Now lives at IS row 80 (Other I/E). Historical periods use Credits-Debits SUMIFS; post-close uses debt schedule sums.
- Principal Paydown on CF Financing Activities driven by Budget
- LOC (BS row 72) now references `Debt Service Schedule - SBA Express LOC` (sheet ID 1878469770) — independent of cash bridge
- LOC schedule: 48 monthly rows, SUMPRODUCT from Budget using ISNUMBER(MATCH()) against IS account ranges, 25% flat tax approx, LOC waterfall with $200K cap from Deal Terms
- Tax distributions = CF Financing Activities (Shareholder Tax Distribution), NOT an IS expense (S-Corp pass-through)
- S-Corp LLC: all net income taxed at household level regardless of distributions ("phantom income")
- **Deal Terms Health Check (B13)**: Three-tier referencing LOC schedule: "No Deal" (MIN ending cash < 0), "Healthy" (DSCR ≥ 1.25 AND LOC = $0 at FY2029 end), "Risky" (else). Currently "No Deal".
- **Total Seller Compensation (B9)**: $2,484K — includes SN2 accrued interest ($319K). Formula: `=B8+B35+'Debt Service Schedule - Seller Note 2'!G124+B49`
- **SN2 Monthly Payment (B44)**: $57,755 — corrected to use accrued balance from schedule
- **Seller Note 2**: PIK interest at 6.50%/12 during 120-month standby. Balance: $350K→$669K. Budget rows 148-151 for interest. IS includes expense, CF has non-cash add-back (row 9), BS shows growing balance.
- **Budget rows 36-37 DISABLED (Mar 5 2026)**: Vehicle Loan Payment - Ford F250 ($1,841/mo) and New Truck Upfitting ($14,510/yr) — start dates set to `9/9/9999`. Ford loan paid off in asset sale; upfitting premature. Line items preserved for future vehicle purchases.
- **Budget principal rows 140-147**: 8 entries (4 FYs × 2 loans) for SBA 7a and Seller Note principal
- **IS structure (post GW amort + interest move)**: Row 49 = Interest Expense (ZEROED), Row 64 = Depreciation, Row 65 = Goodwill Amortization, Row 73 = TOTAL OPEX, Row 75 = OPERATING INCOME, Row 77 = EBITDA (=OI+Depr+GW, no interest), Row 80 = Interest Expense (Other I/E), Row 87 = TOTAL OTHER I/E (SUM includes row 80 for all periods), **Row 89 = NET INCOME**
- **CF structure (FINAL)**: Row 10 = GW Amort add-back, Row 13 = AR WC change, Row 14 = Retainage WC change, Row 15 = AP WC change, Row 29 = CASH FROM OPS, Row 35 = CASH FROM INVESTING, Row 53 = Debt Principal, Row 54 = Tax Distribution, Row 55 = CASH FROM FINANCING = SUM(F38:F54), **Row 57 = NET CHANGE IN CASH** = F29+F35+F55
- **NO LOC row on CF** — BS Cash is a plug; LOC changes captured implicitly through BS liability. Adding LOC to CF = double-counting.
- **Interest Expense restructured (Mar 4 2026)**: Moved from OpEx to Other I/E on IS (row 80), CB (row 80), and LOC (inline in F formula). Single source of truth = debt service schedules (column D). Budget Interest Expense entries (12 total) zeroed. EBITDA = OI+Depr+GW (no interest add-back). CY2027-2029 CB/CF/BS fully reconcile. First-period (May-Dec 2026) has $148K CB vs BS gap from initialization differences.
- **IS row 89 = NET INCOME** (shifted from 88 after row 80 insert). CF!I5 references IS!I89.
- **LOC GW Amort Add-back (column H after COGS insert, added Mar 4 2026)**: Pure add-back using direct Deal Terms formula `(B19-BS!E32-BS!E16)/180` = $11,212/month. BS!E16 = Inventory ($8,576) — confirmed correct for asset sale (buyer only acquires Inventory + PP&E, not all current assets). NOT Budget-based.
- **LOC WC Timing Adjustment (column L, added Mar 4 2026)**: AR/AP lag using `ar_days=90` (3-month) and `ap_days=30` (1-month). COGS column added at E (SUMPRODUCT matching IS!A10:A33). WC formula uses LET/INDEX lookback on Revenue (C) and COGS (E) columns. Matched CB row 175 values exactly ($300,763 for Oct 2026).
- **CB GW Amort (rows 65 + 94, added Mar 4 2026)**: Row 65 = P&L expense (reduces Operating Income), Row 94 = CF add-back (non-cash reversal). Both use same Deal Terms formula as IS/LOC. Net cash effect = $0, but reduces taxable income → tax savings ~$131K over projection. TOTAL OPEX SUM auto-adjusted to include row 65. CASH FROM OPS SUM auto-adjusted to include row 94.
- **CB row shifts (Mar 4-5 2026)**: After 2 row insertions and 4 row deletions. Key positions: Row 49=Interest Expense (OpEx, **ZEROED ALL PERIODS** — Justin manually cleared Mar 5), Row 65=GW Amort, Row 73=TOTAL OPEX, Row 75=OPERATING INCOME, Row 77=EBITDA (=OI+Depr+GW), Row 80=Interest Expense (Other I/E, from debt schedules), Row 86=TOTAL OTHER I/E, Row 88=NET INCOME, Row 113=CASH FROM OPS, Row 135=NET CHANGE IN CASH, Row 143-146=Principal (SBA/SN/SN2/Ford), Row 147=Total DS, Row 179=Cash at Close ($250K), Row 186=Running Cash Balance, Row 187=LOC Outstanding.
- **LOC column layout (after all Mar 4 inserts)**: A=Period, B=Date, C=Revenue, D=Total Expenses, E=COGS, F=Net Income, G=Depr Add-back, H=GW Amort Add-back, I=SN2 Interest, J=Debt Principal, K=Tax Dist, L=WC Timing Adj, M=Net Cash Before LOC, N=Beg Cash, O=LOC Draw, P=LOC Interest, Q=Ending Cash, R=LOC Outstanding, S=LOC Available.
- **BS Distributions (row 79)**: cumulative tax distributions from CF row 54. BS AccumDepr (row 31): decreases by IS Depreciation each period.
- **Three-statement reconciliation**: CF NET CHANGE = BS ΔCash to the penny (FY2027-29). BS CHECK = $0. Fully linked.
- **BS uses CALENDAR YEAR periods post-close** (not fiscal year): F=May-Dec 2026, G=CY2027, H=CY2028, I=CY2029. LOC schedule month→December mapping: 8→row12, 20→row24, 32→row36, 44→row48
- **BS/CF reconciliation gap**: BS Cash (plug) >> CB Running Cash. Root cause: IS missing Goodwill Amortization (~$134.5K/yr) and CF missing WC change rows (ΔAR, ΔAP). CF Ops = CB NET CHANGE exactly for FY2027-29 (P&L consistent). Fix: add Goodwill Amort to IS + WC changes to CF.
- **ISNUMBER(MATCH()) pattern**: On LOC schedule, classifies Budget items by matching H column against IS name ranges (revenue: IS!$A$4:$A$6, expenses: IS!$A$10:$A$71)

### Key Spreadsheet
- ID: `13KQXudrHd5F3p-NHrr_RTkSWuIAbhVuDp9GIDVNCetM`
- `transaction details` sheet: ~34K rows of QB GL export
- `cash bridge` sheet (ID 685035795): P&L + CF + debt service + tax + DSCR
- Key columns: D=Type, F=Date, J=Name, L=Memo, N=Account, T=Debit, V=Credit, Y=CoA, Z=Basis, AA=SDE, AB=Adj

### Skills Built
1. **cash-bridge-builder** (`~/repos/excel-fire-ai/skills/cash-bridge-builder/`)
   - Generates full cash bridge sheet from config JSON
   - References: default_config.json, sheet-structure.md
   - Script: build_cash_bridge.py

2. **efp-financial-model** (`~/repos/excel-fire-ai/skills/efp-financial-model/`)
   - Consolidated three-statement model docs (IS/BS/CF + debt + Budget + Deal Terms)
   - References: row-maps.md, reconciliation.md, sign-conventions.md
   - Covers BS plug mechanism, reconciliation checklist, QB sign conventions, modification guides
   - Cross-references cash-bridge-builder for monthly details

3. **efp-transaction-classifier** (`~/repos/excel-fire-ai/skills/efp-transaction-classifier/`)
   - Python classifier (classify.py) — reads/writes Sheets API, 99.8% coverage
   - Vendor DB: 955 vendors, 110 SDE-flagged
   - Notion docs: page ID `30f7e702-d98c-81aa-8798-edf46e4798c9`

## Communication Preferences
- **Always thread replies on Slack.** Never respond as a new top-level message — always reply under Justin's original message to keep contexts organized. Use `[[reply_to_current]]` or `message` tool with `threadId`.

## Decisions & Preferences
- Default to New Construction when web search is inconclusive for revenue classification
- RoughCountry.com = SDE=0 (truck accessories for work vehicles, per Justin)
- Calder Capital = Adj=1, not SDE (non-recurring M&A advisory)
- All airfare, Mexico/Hawaii charges, jewelry stores = SDE=1
- Truck-related expenses = legit business, not SDE
- Safeway on Direct Materials = misclassified meals, SDE=0 (not 1 — it's a misclassification, not personal)
- Travel & Entertainment account = ALL SDE=1 (entire account is owner discretionary; CPA reclassified full balance to owner draws at year-end; $16,956 on tax return was aggressive deduction, not real business need; classifier now blanket-flags all T&E as SDE)
- Year-end T&E reclassification JEs (9/30 each year) = SDE=1 + Adj=1
- Kaanapali was missing from HAWAII_TERMS — caused $23K Westin Kaanapali bill to slip through; added kaanapali + honolua
- Donations, Pension Expense, Officer Salary accounts = always SDE=1
- Pro Forma DSCR: pre-close FYs use annualized $325K; post-close uses actual debt service row
- FY2026 partial year: only Oct–Jan shown (4 months of reliable data)
