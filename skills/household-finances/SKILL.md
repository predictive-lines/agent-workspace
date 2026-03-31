---
name: household-finances
description: "Work with the Miller household Tiller Finance Google Sheet. Use when reading, writing, or fixing formulas in the household budget spreadsheet — including the Budget page, Categories page, account_balances_per_period page, and account_balances_per_group page. Covers sheet structure, formula logic, Google Sheets API auth, and how the accrual/sinking-fund/end-date system works."
---

# Household Finances

Tiller Foundation Template managing the Miller household budget.

**Sheet ID:** `1iVQLLvx5UC62zdcxlHM8s-UcMALCzLwr3EIcbPKuqvc`  
**Auth:** Google OAuth2 — `~/.config/google/tokens.json` + `~/.config/google/oauth_credentials.json` (refresh before use)

## Key Sheet Tabs

| Tab | gid | Purpose |
|-----|-----|---------|
| Transactions | 1256593101 | Raw transaction feed from Tiller |
| Budget | 2068187917 | Budget line items (start date, end date, freq, amount) |
| Categories | 1366405697 | Category → Group mappings |
| account_balances_per_period | 258301931 | Sinking-fund running balances by month |
| account_balances_per_group | 1432880137 | Same balances grouped by category group |
| Balance History | 1531277441 | Account balance snapshots |
| Monthly Budget | 308020674 | Tiller's built-in monthly view |

## Reference Files

| File | Load when... |
|------|-------------|
| `references/budget-sheet.md` | Reading/writing Budget rows, understanding columns, start/end date semantics |
| `references/account-balances-formula.md` | Debugging or updating formulas on `account_balances_per_period`; understanding the accrual/payment/end-date logic |

## Quick Auth Pattern

```python
import json, urllib.request, urllib.parse

with open('/home/open-claw/.config/google/tokens.json') as f:
    tokens = json.load(f)
with open('/home/open-claw/.config/google/oauth_credentials.json') as f:
    creds = json.load(f)

cred = creds.get('web') or creds.get('installed') or creds
data = urllib.parse.urlencode({
    'client_id': cred['client_id'],
    'client_secret': cred['client_secret'],
    'refresh_token': tokens['refresh_token'],
    'grant_type': 'refresh_token'
}).encode()
req = urllib.request.Request('https://oauth2.googleapis.com/token', data=data, method='POST')
access_token = json.loads(urllib.request.urlopen(req).read())['access_token']
```
