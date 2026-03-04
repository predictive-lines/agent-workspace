#!/usr/bin/env python3
"""Add dynamic retainage Budget entries tied to Large Project Billing rows."""

import json, requests, time

TOKEN = open('/tmp/gtoken.txt').read().strip()
SHEET_ID = "13KQXudrHd5F3p-NHrr_RTkSWuIAbhVuDp9GIDVNCetM"
HEADERS = {"Authorization": f"Bearer {TOKEN}", "Content-Type": "application/json"}
BASE = f"https://sheets.googleapis.com/v4/spreadsheets/{SHEET_ID}"

# Large Project Billing rows in Budget (rows 3-14)
BILLING_ROWS = list(range(3, 15))  # 3..14
START_ROW = 109  # First empty row
LAG_MONTHS = 3

print("Adding retainage Budget entries...")
print(f"  Billing rows: {BILLING_ROWS}")
print(f"  Starting at row: {START_ROW}")
print(f"  Release lag: {LAG_MONTHS} months")

updates = []
row = START_ROW

for br in BILLING_ROWS:
    # --- Hold entry ---
    hold_row = [
        f'="Retainage Hold - "&A{br}',       # A: Description
        '',                                     # B: Vendor
        f'=C{br}',                             # C: Start Date (same as billing)
        '',                                     # D: End Date
        f'=E{br}',                             # E: Freq Months
        f'=F{br}',                             # F: Frequency text
        f'=G{br}*0.1',                        # G: Amount (10% of billing)
        'Retainage',                            # H: Account
        f'="10% retainage on "&A{br}',        # I: Notes
        f'=J{br}',                             # J: scalesWith
        'FALSE',                                # K: isFixed
        'TRUE',                                 # L: isNeed
        'FALSE',                                # M: needsAccrual
        '',                                     # N: account_number
        f'=O{br}',                             # O: mult_FY2027
        f'=P{br}',                             # P: mult_FY2028
        f'=Q{br}',                             # Q: mult_FY2029
        '',                                     # R: Hrs/Mo
        f'=S{br}',                             # S: Toggle
    ]
    updates.append({"range": f"Budget!A{row}:S{row}", "values": [hold_row]})
    row += 1

    # --- Release entry ---
    release_row = [
        f'="Retainage Release - "&A{br}',     # A: Description
        '',                                     # B: Vendor
        f'=EDATE(C{br},{LAG_MONTHS})',         # C: Start Date (lagged)
        '',                                     # D: End Date
        f'=E{br}',                             # E: Freq Months
        f'=F{br}',                             # F: Frequency text
        f'=-G{br}*0.1',                       # G: Amount (negative = release)
        'Retainage',                            # H: Account
        f'="Release of 10% retainage, {LAG_MONTHS}mo lag on "&A{br}',  # I: Notes
        f'=J{br}',                             # J: scalesWith
        'FALSE',                                # K: isFixed
        'TRUE',                                 # L: isNeed
        'FALSE',                                # M: needsAccrual
        '',                                     # N: account_number
        f'=O{br}',                             # O: mult_FY2027
        f'=P{br}',                             # P: mult_FY2028
        f'=Q{br}',                             # Q: mult_FY2029
        '',                                     # R: Hrs/Mo
        f'=S{br}',                             # S: Toggle
    ]
    updates.append({"range": f"Budget!A{row}:S{row}", "values": [release_row]})
    row += 1

print(f"  Generated {len(updates)} rows ({len(updates)//2} holds + {len(updates)//2} releases)")

# Write
resp = requests.post(f"{BASE}/values:batchUpdate", headers=HEADERS,
                    json={"valueInputOption": "USER_ENTERED", "data": updates})
if resp.status_code != 200:
    print(f"ERROR: {resp.status_code} - {resp.text[:500]}")
else:
    print(f"  Written successfully")

# Verify
time.sleep(3)
print("\nVerifying...")
resp = requests.get(f"{BASE}/values/Budget!A{START_ROW}:S{START_ROW+5}?valueRenderOption=FORMATTED_VALUE",
                   headers={"Authorization": f"Bearer {TOKEN}"})
sample = resp.json().get('values', [])
for i, row_data in enumerate(sample):
    a = row_data[0] if len(row_data) > 0 else ''
    c = row_data[2] if len(row_data) > 2 else ''
    g = row_data[6] if len(row_data) > 6 else ''
    h = row_data[7] if len(row_data) > 7 else ''
    print(f"  Row {START_ROW+i}: {a:45s} Start={c:12s} Amt={g:>12s} Acct={h}")

# Check impact on BS Retainage row
print("\nChecking BS Retainage impact...")
time.sleep(5)  # Extra time for MAP/LAMBDA recalc
resp = requests.get(f"{BASE}/values/'Balance Sheet'!B12:I12", headers={"Authorization": f"Bearer {TOKEN}"})
ret_vals = resp.json().get('values', [[]])[0]
print(f"  BS Retainage (row 12): {ret_vals}")

# Check balance
resp = requests.get(f"{BASE}/values/'Balance Sheet'!B87:I87", headers={"Authorization": f"Bearer {TOKEN}"})
check = resp.json().get('values', [[]])[0]
print(f"  BS CHECK: {check}")

print("\nDone!")
