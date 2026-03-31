# Budget Sheet Reference

Sheet name: `Budget`  
Data range: rows 2–182 (as of Mar 2026; may grow)

## Column Layout

| Col | Field | Notes |
|-----|-------|-------|
| A | Description | Primary lookup key — must match exactly in MATCH() calls |
| B | Vendor | Optional vendor name |
| C | Start Date | First accrual/payment month |
| D | End Date | Last active month (blank = indefinite) |
| E | FrequencyCount | Months between payments: 1=monthly, 3=quarterly, 12=annual |
| F | Amount | Negative = expense, positive = income |
| G | Account/Category | Must match Categories!A exactly |
| H | Notes | Free text |
| I | isFixed | TRUE/FALSE |
| J | isNeed | TRUE/FALSE |
| K | needsAccrual | TRUE/FALSE — drives inclusion in account_balances_per_period |

## Key Semantics

- **Start Date**: The first month the item becomes active. For new items, this is when accrual begins. For ongoing items (like mortgage), it's the original start.
- **End Date**: The month AT WHICH the item stops (inclusive — the end month itself is the last month that shows $0, freezing the balance). Blank = never ends.
- **Frequency**: How often the payment fires in the formula. The formula fires a payment when `MOD(elapsed, freq) = 1`, meaning 1 month after the start date (and every `freq` months thereafter).

## Notable Entries

| Description | Budget Row | Notes |
|-------------|-----------|-------|
| Federal Taxes | 131 | start=1/12/2026, end=2/1/2026, freq=3, amt=-$16,000. Quarterly estimated taxes, offset by +1 month so balance peaks in Jan before payment |
| State of MI Taxes | 155 | start=1/12/2026, end=2/1/2026, freq=3, amt=-$3,700. Same structure as Federal Taxes |
| food from chef | 83 | end=3/15/2026 — ends when chef arrangement ends |
| Peloton monthly Sub | 38 | end=3/30/2026 — cancelled Mar 2026 |
| Ffern perfume | 179 | start=1/15/2026, end=3/30/2026 |

## End Date Behavior

When `end` is set:
- Months where `(year×12 + month) >= (end_year×12 + end_month)` → balance returns **$0** (hard zero, not a freeze)
- This means the **end month itself** zeroes out — the item is considered complete
- Months after end also show $0 via the cascading prior balance

## Finding a Budget Row by Description

```python
url = f'https://sheets.googleapis.com/v4/spreadsheets/{SHEET_ID}/values/Budget!A:D'
req = urllib.request.Request(url, headers={'Authorization': f'Bearer {access_token}'})
rows = json.loads(urllib.request.urlopen(req).read()).get('values', [])
match = next((i+1 for i, r in enumerate(rows) if r and r[0] == 'Federal Taxes'), None)
```
