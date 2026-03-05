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
- **Use existing skills:** When working on the financial model, USE skills in `~/repos/excel-fire-ai/skills/` — they have correct sheet IDs, column mappings, and formula patterns.
- **Event-driven updates:** Post after each micro-step completes instead of rigid time intervals.
- **New messages for completion:** ALWAYS post completion summaries as a NEW message at bottom of thread. Never edit earlier messages for status updates.
- **Slack commands need provider key:** For Slack native slash commands, use `"slack"` in `commands.allowFrom`, not just `"*"`.

## Key Technical Lessons
- **Named ranges:** All cross-sheet refs in the financial model MUST use named ranges. Use Sheets API `findReplace` with `includeFormulas: true` for bulk migration.
- **SUMIFS empty cell bug:** `"<>1"` does NOT match empty cells. Use subtraction: `(full total) - (SDE=1 only)`.
- **Budget rows need ALL columns K-Q populated.** Empty multiplier = 0 in SUMPRODUCT → silently zeros out line items.
- **Sign conventions:** Revenue = Credits - Debits; COGS/Expense = Debits - Credits; CF adjustments = Credits - Debits (except depreciation = Debits - Credits).
- **Account name matching:** CB column A must match `transaction details` column N exactly. No annotations.

## Model Setup
- **Primary:** Opus (claude-opus-4-6), **Fallbacks:** Sonnet → Haiku (auto)
- Aliases go *under each model entry* as `"alias": "name"` in `openclaw.json`
- Gateway handles fallback transparently — check `/status` after suspicious behavior

## Financial Model State (Mar 5, 2026)
- Three-statement model fully reconciled (CF NET CHANGE = BS ΔCash for FY2027-29).
- Interest Expense moved from OpEx to Other I/E on IS, CB, and LOC (Mar 4).
- GW Amortization added to IS, CB, CF, and LOC (Mar 4).
- Budget rows 36-37 DISABLED (Ford F250 + upfitting — Ford paid off in asset sale).
- Deal Terms Health Check currently shows "No Deal".
- For detailed row maps and formulas, see `efp-financial-model` skill references.

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

## Communication Preferences
- **Always thread replies on Slack.** Use `[[reply_to_current]]` or `threadId`.
- **Reset context after closing a thread.** Don't carry stale context forward.
