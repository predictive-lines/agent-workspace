---
name: efp-financial-model
description: Work on the Excel Fire Protection financial model Google Sheet, including model formulas, helper/source tabs, Google Sheets Tables, named ranges, Budget/HR/Union Benefits logic, scenario inputs, and post-edit verification. Use whenever Justin asks to edit, debug, modernize, migrate, or audit the EFP workbook/model.
---

# EFP Financial Model

Use this skill for the Excel Fire Protection financial model workbook.

## Workbook

- Google Sheet ID: `13KQXudrHd5F3p-NHrr_RTkSWuIAbhVuDp9GIDVNCetM`
- Treat the workbook as production. Back up formulas/metadata before structural edits.
- Prefer Sheets API for deterministic writes. Browser/UI is a fallback only.

## Required safety pattern

Before structural changes:
1. Pull sheet metadata: sheets, tables, named ranges, row/column bounds.
2. Pull all formulas that may reference the target tab/ranges.
3. Save a JSON backup under `/tmp/...backup_<timestamp>.json` with tab formulas/display values, named ranges, tables, and planned formula replacements.
4. Do not delete named ranges until formula usage is verified as zero.

After changes:
1. Re-scan formulas for old references and `#REF!`.
2. Scan active model tabs for visible errors.
3. Verify Balance Sheet check row is all zero.
4. Pull back a formula sample and display-value sample from changed consumers.
5. Report backup path and exact verification results.

Active model tabs to verify unless context says otherwise:
- `Scenario Inputs`
- `KPIs`
- `C-Corp Cash Bridge`
- `Income Statement`
- `Cash Flow Statement`
- `Balance Sheet`
- `Budget`
- `Union Benefits`
- `Debt Service Schedule - SBA Express LOC`
- `Debt Service Schedule - SBA 7a`
- `Debt Service Schedule - Seller Note`
- `Human Resources`
- `defined_variables`

Known acceptable pre-existing errors: `defined_variables` has helper `#DIV/0!` values. Do not treat those alone as a failed migration.

## Tables are preferred for source/helper tabs

For database-like helper/source pages, prefer real Google Sheets Tables over proliferating named ranges.

Good candidates:
- `Union Benefits` → `UnionBenefits`
- `Human Resources` → `HumanResources`
- `Jobs Forecast` → `JobsForecast`
- `Site Economics` → `SiteEconomics`
- possibly `Scenario Inputs` → `ScenarioInputs`

Use structured references in model formulas, e.g.:

```none
=SUMIFS(UnionBenefits[Total Remittance/mo],UnionBenefits[Employee],$B33)
```

```none
=INDEX(HumanResources[Annual Amount],MATCH(person_id,HumanResources[Person ID],0))
```

Benefits confirmed in pilot:
- API can create real Sheets Tables with `AddTableRequest`.
- Formulas accept structured refs through the API.
- Off-page formulas can reference table columns.
- Column names with spaces and slashes work, e.g. `UnionBenefits[Total Remittance/mo]`.
- Table and column renames auto-update dependent formulas.

Important limitation:
- Appending rows by API below a table does **not** auto-expand the table. When writing rows via API, also update the table range with `UpdateTableRequest`.

## Table typing rule

Do not infer table column types purely from human labels. Preserve formula semantics.

Example from `UnionBenefits`:
- `Toggle` must stay numeric (`DOUBLE`), not `BOOLEAN`, because formulas use `1/0` math.
- `Period Key` must stay numeric (`DOUBLE`), not `TEXT`, because lookups match numeric period keys.

If type conversion corrupts values, restore original row values from backup and update table column types.

## Named range deletion warning

Deleting named ranges before checking formula usage is dangerous. Google Sheets may rewrite formulas to literal `#REF!`, which cannot be repaired by simply recreating the name.

Safe order:
1. Find all formula references to the named ranges.
2. Replace formulas with new refs.
3. Pull formulas back and verify old usage is zero.
4. Only then delete the named ranges.
5. Verify no `#REF!` formulas were introduced.

## Union Benefits conversion record

Completed on 2026-06-02:
- Removed 5 title/prose/section rows from `Union Benefits` so headers start at row 1.
- Created real table `UnionBenefits` over columns A:T.
- Converted 132 `Budget` formulas from `union_benefits_*` named ranges to structured table refs.
- Deleted old named ranges after usage scan returned zero:
  - `union_benefits_employee_name`
  - `union_benefits_monthly_total_remittance`
  - `union_benefits_effective_start_date`
  - `union_benefits_effective_end_date`
- Fixed table type issue by setting:
  - `Toggle` = `DOUBLE`
  - `Period Key` = `DOUBLE`
- Verification passed:
  - `Union Benefits`: 0 errors
  - Budget/statements/KPIs/C-Corp bridge/SBA Express LOC: 0 errors
  - BS check row: all zero
  - only pre-existing `defined_variables` helper `#DIV/0!` values remained
- Backup path from migration: `/tmp/union_benefits_table_migration_backup_20260602_175651.json`

Representative migrated Budget formula:

```none
=IFERROR(INDEX(FILTER(UnionBenefits[Total Remittance/mo],UnionBenefits[Employee]=$B37,UnionBenefits[Start Date]<=$C37,UnionBenefits[End Date]>=$C37),1),0)
```

## Human Resources conversion record

Completed on 2026-06-02:
- Created real table `HumanResources` over `Human Resources!A1:W195`.
- Kept row 1 headers; no row deletion was needed.
- Used conservative field typing:
  - `Rate`, `Annual Quantity`, `Latitude`, `Longitude` = `DOUBLE`
  - `Annual Amount` = `CURRENCY`
  - `Start Date`, `End Date` = `DATE`
  - `Include in Model` = `BOOLEAN`
  - text/ID/address/source fields = `TEXT`
- Migrated 1,607 formulas to structured refs:
  - KPIs: 484
  - Budget: 196
  - Jobs Forecast: 70
  - Union Benefits: 855
  - defined_variables: 2
- Deleted 13 old HR named ranges only after usage scan returned zero:
  - `hr_model_*`
  - `hr_roster_*`
- Verification passed:
  - `Human Resources`, `Union Benefits`, `Jobs Forecast`, Budget, KPIs, statements, bridge, debt schedules, and Scenario Inputs: 0 errors
  - BS check row: all zero
  - only pre-existing `defined_variables` helper `#DIV/0!` values remained
- Backups:
  - `/tmp/human_resources_table_migration_backup_20260602_181116.json`
  - `/tmp/human_resources_formula_migration_backup_20260602_181509.json`

Post-migration stale helper cleanup:
- Initial migration left 933 narrow direct refs for semantic review, mostly `Human Resources!B$2:B$9` in `Job Addresses` and `defined_variables` labor-utilization helpers.
- Follow-up audit found they were stale/orphaned, not active model inputs:
  - `defined_variables!A52:B52` displayed `0 / 0`.
  - no formulas referenced `defined_variables!A50:C53`.
  - no named ranges intersected that block.
  - `Job Addresses!N:O` had 930 formulas using HR rows 2:9, but no formulas referenced `Job Addresses!N:O`.
  - outputs were nonsensical (`99999` distances / stale employee names).
- Cleared contents, not rows/columns, from `defined_variables!A50:C53` and `Job Addresses!N:O` on 2026-06-02.
- Backup: `/tmp/stale_hr_2_9_helpers_backup_20260602_182417.json`.
- Verification after clear: 0 formulas still referenced HR rows 2:9, 0 refs to cleared ranges, active tabs clean, BS check all zero.

General rule:
- Whole-column refs and exact table-data refs like `Human Resources!V2:V195` are good conversion candidates.
- Narrow bespoke ranges need semantic review before conversion or deletion. If orphaned and stale, clear contents rather than deleting rows/columns.

Representative migrated formulas:

```none
=IFERROR(AVERAGE(FILTER(HumanResources[Annual Amount],ISNUMBER(SEARCH("Journeyman",HumanResources[Role])),HumanResources[Include in Model]=TRUE,HumanResources[Start Date]<=EDATE(C$57,12)-1,((LEN(HumanResources[End Date])=0)+(HumanResources[End Date]>=C$57)))),0)
```

```none
=COUNTIFS(HumanResources[Capacity Unit],"MARQ-SPRINKLER-JM",HumanResources[Include in Model],TRUE,HumanResources[Start Date],"<="&DATE(2026,12,31))-COUNTIFS(HumanResources[Capacity Unit],"MARQ-SPRINKLER-JM",HumanResources[Include in Model],TRUE,HumanResources[End Date],"<>",HumanResources[End Date],"<"&DATE(2026,12,31))
```

## Site Economics restructuring record

Completed on 2026-06-02:
- Split `Site Economics` into three real Google Sheets Tables, each containing all sites:
  - `Sites` over `Site Economics!A1:K5`
  - `SiteRevenueControls` over `Site Economics!A8:O32`
  - `SiteOperatingDrivers` over `Site Economics!S1:AI93`
- Table implementation note: for `AddTableRequest` / `UpdateTableRequest`, column property indexes behave as table-relative in returned metadata. If headers look strange after creating adjacent/off-to-the-right tables, restore both visible header cells and table `columnProperties`, then force formulas using structured refs to re-parse. Row grouping on the source page can make visual debugging harder; ungroup before final visual cleanup if needed.
- Moved the generated Budget-output logic out of `Site Economics!A152:P243` and directly into `Budget!A729:N820`.
  - Backed up before write: `/tmp/site_economics_budget_output_move_backup_20260602_184909.json`.
  - Verified Budget display output before/after: 0 diffs.
  - Cleared old generated output pad `Site Economics!A150:P243` after confirming no named ranges or external refs intersected it.
  - Backup before clear: `/tmp/site_economics_output_pad_clear_backup_20260602_185131.json`.
- Added line-level operating-driver timing columns to the driver data before final table creation:
  - `Line Start Date`
  - `Line End Date`
  - populated all 92 operating driver rows from the prior generated Budget timing.
  - Backup: `/tmp/site_economics_line_level_timing_backup_20260602_185517.json`.
- Updated Budget operating cost rows so:
  - start/end dates read `SiteOperatingDrivers[Line Start Date]` / `[Line End Date]` via structured refs
  - toggle reads only each driver row's `Include` flag
  - no site-wide Active? gate remains in `Budget!A729:N820`
- Updated `KPIs!C8:M8` target vehicle logic so site activity is derived from included operating-driver line items active by year-end, not from site-wide active/launch/end fields.
  - Backup: `/tmp/kpi_site_activity_line_item_logic_backup_20260602_185824.json`.
  - Final target vehicle counts after table repair: `3,3,3,3,3,5,6,6,6,7,8` for 2026-2036.
- Migrated `Jobs Forecast` from direct flattened `Site Economics!A:O` lookups to structured refs:
  - 1,370 cells updated.
  - 0 remaining direct `Jobs Forecast` refs to `Site Economics!…`.
  - Backup: `/tmp/jobs_forecast_site_tables_migration_backup_20260602_192437.json`.
  - Modeling change: revenue forecast rows now follow the revenue control line's own `Active?`/`Start Date`; the old site-wide Active? toggle is not a hard gate.
- Cleared the old duplicate flattened operating-driver block `Site Economics!A35:Q127` after whole-workbook scan found 0 direct refs to `Site Economics!…` and 0 site named ranges.
  - Backup: `/tmp/old_site_operating_block_clear_backup_20260602_192949.json`.
- Justin manually cleared orphaned leftover header cells `L1:R1` and `P8:R8` contents only (no rows/columns deleted). Final verification confirmed those cells are blank and all table ranges remain intact.
- Retired stale named ranges after formula usage scan returned zero:
  - `site_economics_site_active_flag`
  - `site_economics_site_launch_date`
  - `site_economics_site_end_date`
  - Backup before retirement: `/tmp/site_economics_retire_site_wide_controls_backup_20260602_190011.json`.
- Final verification passed:
  - `Site Economics`, `Budget`, `KPIs`, `Jobs Forecast`, `Union Benefits`, `Human Resources`, statements, bridge, and Scenario Inputs: 0 errors
  - BS check row: all zero
  - 0 direct refs to `Site Economics!…` remain
  - 2,172 structured site-table refs remain (`Budget`: 1,297; `Jobs Forecast`: 854; `KPIs`: 11; `Union Benefits`: 10)
  - only pre-existing `defined_variables` helper `#DIV/0!` values remained

Important modeling rule from this restructure:
- Site-wide active/start/end controls are metadata/default planning fields only, not authoritative economic gates.
- Operating cost timing lives on the driver line (`Line Start Date`, `Line End Date`).
- Revenue forecast timing/gating lives on the revenue control line (`Active?`, `Start Date`).
- Site activity for model-wide logic should be derived from included/economic line items with timing: start <= period and (end blank or end >= period).

## Scenario Inputs retirement record

Completed on 2026-06-02:
- Deleted the `Scenario Inputs` sheet after relocating all assumptions and repointing named ranges.
- Backup before migration: `/tmp/scenario_inputs_relocation_backup_20260602_195130.json`.
- Debt-specific assumptions now live as hardcoded values in the top input rows of the consuming debt schedule tabs:
  - `Debt Service Schedule - SBA 7a!B2:E2`: loan amount, interest rate, term months, monthly payment.
  - `Debt Service Schedule - Seller Note!B2:E2`: note amount, interest rate, term months, monthly payment.
  - `Debt Service Schedule - SBA Express LOC!B2:C2`: LOC limit and interest rate.
- Global/deal assumptions now live in `defined_variables!A99:C110`:
  - deal structure, enterprise value, buyer equity injection, buyer/lender closing costs, working capital bridge, target close date, retired seller-note-2 leftovers, and `total_monthly_debt_service`.
  - `total_monthly_debt_service` is intentionally a helper formula summing `sba_7a_monthly_payment + seller_note_monthly_payment`; the debt inputs themselves are hardcoded.
- Salary cleanup immediately after Scenario Inputs retirement:
  - `keith_annual_salary` was removed from `defined_variables`, its named range was deleted, and the salary value was hardcoded on `Human Resources!D102`.
  - Backup before cleanup: `/tmp/remove_keith_salary_backup_20260602_195543.json`.
  - Verification: 0 formulas reference `keith_annual_salary`, 0 `#REF!` hits, BS check all zero.
- Repointed 25 named ranges away from `Scenario Inputs` to their new homes, preserving formula readability/compatibility:
  - debt names and aliases point to debt schedule input cells (e.g. `sba_7a_loan_amount`, `monthly_senior_loan_payment`, `monthly_seller_note_payment`).
  - close-date aliases (`scenario_target_close_date`, `target_close_date`, `proposed_close_date`) point to `defined_variables!C107`.
- Final verification:
  - `Scenario Inputs` sheet no longer exists.
  - 0 direct formulas reference `Scenario Inputs`.
  - 0 `#REF!` formula hits.
  - BS check row all zero.
  - Display-error scan only showed pre-existing source-text values beginning with `#` plus known `defined_variables` helper `#DIV/0!` rows.

## Jobs Forecast table-conversion audit / limitation

Attempted on 2026-06-02 after Site Economics + Scenario Inputs cleanup:
- Read-only audit found `Jobs Forecast` is three logical blocks on one sheet:
  - visible revenue driver block: `Jobs Forecast!A4:W44`
  - generated Budget output block: `Jobs Forecast!A46:AC1240`
  - capacity calibration block: `Jobs Forecast!AE4:AT14`
- Existing consumers are heavily row-aligned:
  - `Budget` has 12,600 simple direct mirror refs to `Jobs Forecast!A:N` across generated output rows.
  - `Jobs Forecast` has 294 internal generated COGS refs in the lower output block.
- Backup before attempting table metadata changes: `/tmp/jobs_forecast_table_creation_backup_20260602_200314.json`.
- Do **not** repeat the naive in-place table conversion path:
  - `AddTableRequest` for the full generated output range `A46:AC1240` returned Sheets API HTTP 500.
  - Creating side-by-side/same-header-row tables (`JobsForecastDrivers` over `A4:W44` and `JobsForecastCapacity` over `AE4:AT14`) corrupted returned table `columnProperties` for the driver table.
  - `DeleteTableRequest` behaved destructively for this page/table state: it removed visible range contents, not just table metadata. Restore from the backup immediately if this happens.
- Final state after backing out:
  - all bad table metadata removed; `Jobs Forecast` has no real Tables.
  - `Jobs Forecast!A1:AT1240` restored from backup.
  - Verification: `Jobs Forecast` and `Budget` samples restored, 0 `#REF!` formula hits, BS check row all zero, only known `defined_variables` helper `#DIV/0!` rows remain.
- Recommended future approach:
  - Treat `Jobs Forecast` as requiring a structural redesign, not a same-sheet table conversion.
  - Keep the visible revenue driver/control block on `Jobs Forecast`.
  - Move generated Budget output to a separate helper tab, e.g. `Jobs Forecast Output`, before converting it to a table.
  - Put capacity calibration on its own row block/sheet before creating a table, or leave it as a normal helper block with existing named ranges.
  - Only after blocks are separated should formulas be migrated to structured refs.

## Jobs Forecast structural refactor record

Completed on 2026-06-02 after the unsafe in-place conversion was backed out:
- Created helper tab `Jobs Forecast Output` and moved the generated Budget output block there at the same row coordinates: `Jobs Forecast Output!A46:AC1240`.
- Cleared the old generated block on `Jobs Forecast!A46:AC1240` and left a pointer note at `Jobs Forecast!A46`.
- Repointed `Budget!A821:N1720` from `Jobs Forecast!A47:N946`-style mirror formulas to `Jobs Forecast Output` equivalents. Formula updates: 12,600. Budget display diff vs pre-move backup: 0.
- Updated Budget note text in `Budget!H41:H64` from “Jobs Forecast generated variable COGS rows” to “Jobs Forecast Output generated variable COGS rows.”
- Created real Google Sheets Tables using API-inferred column metadata only (do **not** hand-supply `columnProperties`; that caused corrupted metadata earlier):
  - `JobsForecastDrivers` over `Jobs Forecast!A4:W44`.
  - `JobsForecastOutput` over `Jobs Forecast Output!A46:AC1240`.
- Migrated `Jobs Forecast Output` formulas off the local mirrored driver ranges (`$A$5:$W$44`) and onto `JobsForecastDrivers[...]` structured references. Formula changes: 11,292 formulas, 32,520 range replacements. Output display diff: 0; Budget display diff: 0.
- Cleared now-unneeded `Jobs Forecast Output!A4:W44` driver mirror and left a note at `Jobs Forecast Output!A4`.
- Capacity calibration remains on `Jobs Forecast!AE4:AT14` as a normal helper block with existing named ranges (`jobs_forecast_capacity_unit`, `jobs_forecast_required_mature_headcount`). Do not table it side-by-side with the driver block unless moved/separated first.
- Backups from the refactor:
  - `/tmp/jobs_forecast_structural_refactor_backup_20260602_201907.json`
  - `/tmp/jobs_forecast_output_cleanup_backup_20260602_202251.json`
  - `/tmp/jobs_drivers_table_safe_create_backup_20260602_202457.json`
  - `/tmp/jobs_output_table_safe_create_backup_20260602_202543.json`
  - `/tmp/jobs_output_structured_refs_backup_20260602_202705.json`
- Final verification:
  - `JobsForecastDrivers` and `JobsForecastOutput` table metadata headers match visible headers.
  - `Budget` has 12,600 formulas pointing to `Jobs Forecast Output` and 0 old direct formula refs to `Jobs Forecast`.
  - `Jobs Forecast Output` has 11,292 formulas using `JobsForecastDrivers[...]` and 0 old local `$A$5:$W$44` driver-range hits.
  - 0 `#REF!` formula hits.
  - Balance Sheet check row all zero.
  - Only known `defined_variables` helper `#DIV/0!` rows remain.

Follow-up simplification the same evening:
- Justin correctly noted that `Jobs Forecast Output` was just Budget-formatted generated data, so the intermediate tab was unnecessary.
- Moved the generated calculation block directly into `Budget!A821:AC1720`:
  - visible Budget fields remain in `A:N`.
  - helper calculation fields live in hidden `Budget!O:AC`.
  - formulas still use the `JobsForecastDrivers[...]` table for the driver assumptions.
- Deleted the `Jobs Forecast Output` sheet after confirming 0 formulas referenced it.
- Important migration detail: the old Budget → Output mapping was not a single continuous offset. Revenue rows mapped to output rows `47:182`, generated COGS rows mapped to output rows `947:1240`, then later rows mapped back to output rows `477:946`. Use the original Budget formulas as the row map if this ever needs rollback/replay.
- Another formula detail: COGS rows reference their source revenue rows. When moving to Budget, rewrite local output-row refs to their mapped Budget rows, but preserve documentation-only `ROW($Axx)` labels if exact visible text matters.
- Edge-case inactive KFS generated COGS rows referenced source revenue rows that were not visible Budget rows; final visible metadata for `Budget!H:I1229:I1250` was patched from backup values to preserve exact display.
- Backup before this simplification: `/tmp/move_jobs_output_to_budget_backup_20260602_210002.json`.
- Final verification after deleting the helper tab:
  - `Jobs Forecast Output` absent.
  - `Budget!A821:N1720` display diff vs backup = 0.
  - 0 formula refs to `Jobs Forecast Output`.
  - 0 `#REF!` formula hits.
  - Balance Sheet check row all zero.
  - Only known source-text `#...` values and `defined_variables` helper `#DIV/0!` display as errors.

## Preferred next migration approach

For other helper tabs:
1. Inspect formulas and usage first.
2. Make row 1 the header if needed, but expect row deletion to mutate formulas; verify the source tab itself after cleanup.
3. Create the table with conservative column types.
4. Migrate consumer formulas in bounded batches.
5. Keep old named ranges until no formula references remain.
6. Leave narrow finite direct references alone unless their semantics are understood.
7. Verify source table + consumer tabs + BS check.
