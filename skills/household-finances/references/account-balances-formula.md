# account_balances_per_period Formula Reference

Sheet: `account_balances_per_period` (gid: 258301931)  
Data rows: 2–36 (35 items)  
Columns: A=Description, B=Category, C=Group, D=Starting Balance, E–P=period columns (Jan–Dec of the display year)

The sheet is an annual view — column headers change each year (e.g., all Jan–Dec 2026). When the user copies the sheet for a new year, they update the header dates. The formulas reference `E$1` (first period) and `P$1` (last period) as anchors.

## Design: Sinking Fund Accrual

Each row tracks a sinking-fund balance for a budgeted item:
- Each month **accrues** `amt/freq` toward the next payment
- When the payment month arrives (`MOD(elapsed, freq) = 1`), the full `amt` is added back (payment fires)
- The balance cascades: each period references the prior period as `prior`

`elapsed = (YEAR(col$1)×12 + MONTH(col$1)) - (YEAR(start)×12 + MONTH(start))`

Payment fires at `elapsed = 1, 4, 7, ...` (i.e., every `freq` months, offset by 1 from start).

## Starting Balance Formula (Column D)

```
=IFERROR(LET(
  idx, MATCH($A{r}, Budget!$A:$A, 0),
  freq, INDEX(Budget!$E:$E, idx),
  amt,  INDEX(Budget!$F:$F, idx),
  start, INDEX(Budget!$C:$C, idx),
  start_month, MONTH(start),
  elapsed_start, (YEAR(E$1)*12+MONTH(E$1))-(YEAR(start)*12+MONTH(start)),
  IF(OR(freq<=1, AND(elapsed_start<0, start>P$1)), 0,
    amt/freq*-1*MOD(freq-start_month, freq))
), 0)
```

### Starting Balance Logic

| Condition | Result | Why |
|-----------|--------|-----|
| `freq <= 1` | $0 | Monthly items don't accrue |
| `elapsed_start < 0` AND `start > P$1` | $0 | Item starts after the entire display window — suppress pre-load |
| Otherwise | `amt/freq × -1 × MOD(freq - start_month, freq)` | Back-calculate how many months of pre-accrual needed so the balance hits the full amount by the first payment |

**Key insight on the pre-load:** `MOD(freq - start_month, freq)` gives the number of months between the start of the display and the next payment. Multiplying by the monthly accrual gives the pre-load needed to reach the full amount. For example: Federal Taxes, start=Jan (month 1), freq=3 → `MOD(3-1,3)=2` months × `$5,333` = `$10,666` pre-load → January then adds one more accrual → `$16,000` peak before the Feb payment.

**`elapsed_start = 0`** (item starts in the exact same month as E$1, e.g., new item added for the current year): pre-load fires normally. This is intentional — the item needs to be pre-loaded so the balance is ready for the first payment within the year.

## Period Column Formula (Columns E–P)

```
=IFERROR(LET(
  idx,   MATCH($A{r}, Budget!$A:$A, 0),
  freq,  INDEX(Budget!$E:$E, idx),
  amt,   INDEX(Budget!$F:$F, idx),
  start, INDEX(Budget!$C:$C, idx),
  end,   INDEX(Budget!$D:$D, idx),
  elapsed, (YEAR({COL}$1)*12+MONTH({COL}$1))-(YEAR(start)*12+MONTH(start)),
  IF(AND(elapsed<0, start>P$1), 0,
    IF(AND(end<>"", ISNUMBER(end),
          (YEAR({COL}$1)*12+MONTH({COL}$1)) >= (YEAR(end)*12+MONTH(end))),
      0,
      SUM(amt/freq*-1, IF(MOD(elapsed,freq)=1, amt, 0), {PRIOR})
    )
  )
), 0)
```

Where `{COL}` = current column letter (E, F, …P), `{PRIOR}` = prior column + row (e.g., `D27` for Jan of row 27).

### Period Formula Logic

| Condition | Result |
|-----------|--------|
| `elapsed < 0` AND `start > P$1` | `0` — item hasn't started yet and its start is beyond the display window |
| `col_month >= end_month` (and end is set) | `0` — item is done; hard zero from end month onwards |
| Otherwise | `SUM(monthly_accrual, payment_if_due, prior_balance)` |

**Why year-month arithmetic instead of date comparison:** Using `YEAR(col)*12+MONTH(col)` avoids day-of-month issues (e.g., col header = Jan 1, end date = Jan 12 → Jan 1 < Jan 12 but they're the same month).

**Why `>=` for end check (not `>`):** The end month itself should return $0 — the item is complete. `>` would allow the end month to still accrue, leaving a residual balance.

**Why return `0` on end (not freeze `prior`):** After an item ends, the balance should be $0 (done), not frozen at whatever it was. The cascade of `0` → `0` → `0` works because each cell's `{PRIOR}` references the zeroed-out cell.

## Applying Formula Updates via API

To update all 35 rows × 13 columns (D2:P36):

```python
# Fetch with formula values
url = f'https://sheets.googleapis.com/v4/spreadsheets/{SHEET_ID}/values/account_balances_per_period!D2:P36?valueRenderOption=FORMULA'
req = urllib.request.Request(url, headers={'Authorization': f'Bearer {access_token}'})
formulas = json.loads(urllib.request.urlopen(req).read()).get('values', [])

# Modify formulas in Python, then write back
write_url = f'https://sheets.googleapis.com/v4/spreadsheets/{SHEET_ID}/values/account_balances_per_period!D2:P36?valueInputOption=USER_ENTERED'
body = json.dumps({'range': 'account_balances_per_period!D2:P36', 'majorDimension': 'ROWS', 'values': updated}).encode()
write_req = urllib.request.Request(write_url, data=body, method='PUT',
    headers={'Authorization': f'Bearer {access_token}', 'Content-Type': 'application/json'})
json.loads(urllib.request.urlopen(write_req).read())
```

## Common Pitfalls

- **`"<>1"` on empty cells**: Don't use `SUMIFS(..., col, "<>1")` — empty cells don't match. Use subtraction: `(full total) - (SDE=1 only)`.
- **Column letter helper**: `chr(ord('D') + col_idx)` maps 0→D, 1→E, …12→P.
- **P$1 as last-column anchor**: The period formulas use `P$1` (last visible column) to detect whether a future-start item is beyond the display window. If the sheet is extended beyond column P, update `P$1` references.
- **`start > P$1` guard purpose**: Only suppresses pre-load/pre-start for items whose start is entirely outside the display window. Items starting in the same month as E$1 (elapsed=0) are NOT gated — they need their pre-load.
