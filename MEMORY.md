# MEMORY.md — Long-Term Memory

## Justin Miller — Context
- Acquired Excel Fire Protection (Marquette, MI) for $3.3M. Target close: April 2026.
- Union fire sprinkler company (~$2M revenue), Local 669. Fiscal year starts October.
- LLC with S-Corp election. Household has ~$200K W2 income (MFJ).
- Annual debt service: $325K (SBA 7a $277K + Seller Note $26K + Ford F250 $22K).
- Wife/business partner: Jaclyn Miller (CEO/CFO).

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

## Key Technical Lessons
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

## Financial Model Fixes (Mar 25, 2026)
- **LOC schedule retainage sign**: M column was `+IF(YEAR>=2027, SUMPRODUCT(...))` — should be `-IF(...)`. Retainage holds reduce cash.
- **LOC schedule depreciation multiplier**: G column was hardcoded `$O$` (FY2027 multiplier). Fixed to dynamic `IF(YEAR>=2029, Q, IF(YEAR>=2028, P, O))`.
- **CFS duplicate row**: Had two "Accumulated Depreciation" rows (11 and 12) — deleted row 12.
- **Budget COGS seasonality**: Replaced 3 flat monthly DM/Subs entries with 24 seasonal entries (freq=12, proportional to monthly revenue share). New DM rows 40-51, Subs rows 52-63. Annual totals unchanged.
- **AP days**: Changed from 30 → 60 (Business Model Inputs B100, named range `ap_days`). AR stays at 90 (B99).
- **CB tax fix**: FY2026 NI sum range was `$CJ$87:$CQ$87` (included pre-close May) → fixed to `$CK$87:$CQ$87`.
- **Max shortfall after all fixes**: -$34K (Aug 2028) with $250K LOC. Recommended $300-325K. Justin to confirm.
- **Row deletion lesson**: Always verify row contents immediately before deleting — 0-indexed math is error-prone when rows shift.

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
