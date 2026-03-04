#!/usr/bin/env python3
"""
Refactor Income Statement:
1. Set row 2 to start dates (end date = next col's row 2)
2. Replace historical formulas with date-parameterized SUMIFS
3. Replace pro forma =SUM(monthly) with direct annual SUMPRODUCT
4. Add sentinel date in J2
"""

import json, requests, sys

# ── Auth ──────────────────────────────────────────────────────────────
creds = json.load(open('/home/open-claw/.config/google/oauth_credentials.json'))
tokens = json.load(open('/home/open-claw/.config/google/tokens.json'))
r = requests.post('https://oauth2.googleapis.com/token', data={
    'client_id': creds['client_id'],
    'client_secret': creds['client_secret'],
    'refresh_token': tokens['refresh_token'],
    'grant_type': 'refresh_token'
})
TOKEN = r.json()['access_token']
open('/tmp/gtoken.txt', 'w').write(TOKEN)

SHEET_ID = "13KQXudrHd5F3p-NHrr_RTkSWuIAbhVuDp9GIDVNCetM"
HEADERS = {"Authorization": f"Bearer {TOKEN}", "Content-Type": "application/json"}
BASE = f"https://sheets.googleapis.com/v4/spreadsheets/{SHEET_ID}"
SHEET_NAME = "Income Statement"

# ── Capture current values for verification ───────────────────────────
print("Capturing current IS values for verification...")
resp = requests.get(
    f"{BASE}/values/'{SHEET_NAME}'!B1:I87",
    headers={"Authorization": f"Bearer {TOKEN}"}
)
current_values = resp.json().get('values', [])
print(f"  Got {len(current_values)} rows of current values")

# ── Column mapping ────────────────────────────────────────────────────
COLS = ['B', 'C', 'D', 'E', 'F', 'G', 'H', 'I']
NEXT = ['C', 'D', 'E', 'F', 'G', 'H', 'I', 'J']

# Period start dates for row 2
ROW2 = {
    'B': '=DATE(2022,10,1)',
    'C': '=DATE(2023,10,1)',
    'D': '=DATE(2024,10,1)',
    'E': '=DATE(2025,10,1)',
    'F': '=proposed_close_date',
    'G': '=DATE(2027,1,1)',
    'H': '=DATE(2028,1,1)',
    'I': '=DATE(2029,1,1)',
    'J': '=DATE(2030,1,1)',  # sentinel
}

# Row categories
REVENUE_ROWS = [4, 5, 6]           # Credits - Debits
COGS_ROWS = list(range(10, 34))    # 10-33, Debits - Credits
OPEX_ROWS = list(range(39, 72))    # 39-71, Debits - Credits
OIE_ROWS = list(range(79, 85))     # 79-84, Credits - Debits

# Totals/calc rows (keep unchanged)
TOTAL_ROWS = [7, 34, 36, 72, 74, 76, 85, 87]

# Multiplier columns per pro forma period
# FY2026PC (F): no multiplier, FY2027 (G): O, FY2028 (H): P, FY2029 (I): Q
MULT = {'F': None, 'G': 'O', 'H': 'P', 'I': 'Q'}

# ── Formula generators ────────────────────────────────────────────────

def hist_formula(col, ncol, row, sign):
    """Historical SUMIFS with SDE adjustment, parameterized by row 2 dates."""
    if sign == 'cr-dr':  # Revenue, OIE
        f, s = '$V', '$T'
    else:  # COGS, OpEx
        f, s = '$T', '$V'
    
    td = "'transaction details'!"
    base = (
        f"SUMIFS({td}{f}:{f},{td}$N:$N,$A{row},"
        f"{td}$F:$F,\">=\"&{col}$2,{td}$F:$F,\"<\"&{ncol}$2)"
    )
    base2 = (
        f"SUMIFS({td}{s}:{s},{td}$N:$N,$A{row},"
        f"{td}$F:$F,\">=\"&{col}$2,{td}$F:$F,\"<\"&{ncol}$2)"
    )
    sde_f = (
        f"SUMIFS({td}{f}:{f},{td}$N:$N,$A{row},"
        f"{td}$F:$F,\">=\"&{col}$2,{td}$F:$F,\"<\"&{ncol}$2,"
        f"{td}$AA:$AA,1)"
    )
    sde_s = (
        f"SUMIFS({td}{s}:{s},{td}$N:$N,$A{row},"
        f"{td}$F:$F,\">=\"&{col}$2,{td}$F:$F,\"<\"&{ncol}$2,"
        f"{td}$AA:$AA,1)"
    )
    return f"=({base}-{base2})-({sde_f}-{sde_s})"


def proforma_formula(col, ncol, row, mult_col):
    """Annual SUMPRODUCT from Budget sheet."""
    B = "Budget!"
    rng = "$2:$H$534"  # using $H for account col
    
    # Occurrence count logic
    occ = (
        f"IF({B}$E$2:$E$534<=0,"
        # One-time: fires if start date in period
        f"({B}$C$2:$C$534>={col}$2)*({B}$C$2:$C$534<{ncol}$2),"
        f"IF({B}$E$2:$E$534=1,"
        # Monthly: count months in period
        f"YEAR({ncol}$2)*12+MONTH({ncol}$2)-YEAR({col}$2)*12-MONTH({col}$2),"
        # Annual (E=12): fires once if start month in period
        f"((MONTH({B}$C$2:$C$534)>=MONTH({col}$2))"
        f"+((MONTH({B}$C$2:$C$534)<MONTH({ncol}$2))"
        f"*(YEAR({ncol}$2)>YEAR({col}$2)))>0)*1"
        f"))"
    )
    
    # Base SUMPRODUCT
    parts = [
        f"({B}$H$2:$H$534=$A{row})",
        f"({B}$C$2:$C$534<{ncol}$2)",
        f"(IF({B}$D$2:$D$534=\"\",1,{B}$D$2:$D$534>={col}$2))",
        f"{B}$G$2:$G$534",
        f"({occ})",
    ]
    
    if mult_col:
        parts.append(f"{B}${mult_col}$2:${mult_col}$534")
        parts.append(f"{B}$S$2:$S$534")
    
    return "=SUMPRODUCT(" + "*".join(parts) + ")"


# ── Build all updates ─────────────────────────────────────────────────
updates = []

# Row 2: dates
for col, formula in ROW2.items():
    updates.append({
        "range": f"'{SHEET_NAME}'!{col}2",
        "values": [[formula]]
    })
# Keep A2 label
updates.append({
    "range": f"'{SHEET_NAME}'!A2",
    "values": [["Period Start"]]
})

# All data rows
all_data_rows = REVENUE_ROWS + COGS_ROWS + OPEX_ROWS + OIE_ROWS

for row in all_data_rows:
    # Determine sign type
    if row in REVENUE_ROWS or row in OIE_ROWS:
        sign = 'cr-dr'
    else:
        sign = 'dr-cr'
    
    for i, col in enumerate(COLS):
        ncol = NEXT[i]
        
        if col in ('B', 'C', 'D', 'E'):
            # Historical: SUMIFS with row 2 dates
            formula = hist_formula(col, ncol, row, sign)
        else:
            # Pro forma: annual SUMPRODUCT
            formula = proforma_formula(col, ncol, row, MULT[col])
        
        updates.append({
            "range": f"'{SHEET_NAME}'!{col}{row}",
            "values": [[formula]]
        })

print(f"Generated {len(updates)} cell updates")

# ── Send batch update ─────────────────────────────────────────────────
print("Writing formulas to Google Sheets...")

# Split into chunks of 500 to avoid API limits
chunk_size = 500
for chunk_start in range(0, len(updates), chunk_size):
    chunk = updates[chunk_start:chunk_start + chunk_size]
    resp = requests.post(
        f"{BASE}/values:batchUpdate",
        headers=HEADERS,
        json={
            "valueInputOption": "USER_ENTERED",
            "data": chunk
        }
    )
    if resp.status_code != 200:
        print(f"ERROR: {resp.status_code} - {resp.text[:500]}")
        sys.exit(1)
    print(f"  Wrote chunk {chunk_start//chunk_size + 1}: {len(chunk)} cells")

# ── Verify values match ──────────────────────────────────────────────
import time
time.sleep(3)  # Let Sheets recalculate

print("\nVerifying values match...")
resp = requests.get(
    f"{BASE}/values/'{SHEET_NAME}'!B1:I87",
    headers={"Authorization": f"Bearer {TOKEN}"}
)
new_values = resp.json().get('values', [])

# Compare key totals
key_rows = {
    7: "TOTAL REVENUE",
    34: "TOTAL COGS",
    36: "GROSS PROFIT",
    72: "TOTAL OPEX",
    74: "OPERATING INCOME",
    76: "EBITDA",
    85: "TOTAL OIE",
    87: "NET INCOME",
}

print(f"\n{'Row':<6} {'Label':<25} {'Col':>5} {'Old':>15} {'New':>15} {'Match':>6}")
print("-" * 75)

mismatches = 0
for row_idx, label in key_rows.items():
    for col_idx, col_name in enumerate(COLS):
        old_val = current_values[row_idx - 1][col_idx] if row_idx - 1 < len(current_values) and col_idx < len(current_values[row_idx - 1]) else ""
        new_val = new_values[row_idx - 1][col_idx] if row_idx - 1 < len(new_values) and col_idx < len(new_values[row_idx - 1]) else ""
        
        # Parse as numbers for comparison
        try:
            old_num = float(str(old_val).replace('$', '').replace(',', ''))
        except:
            old_num = None
        try:
            new_num = float(str(new_val).replace('$', '').replace(',', ''))
        except:
            new_num = None
        
        if old_num is not None and new_num is not None:
            match = abs(old_num - new_num) < 1.0  # within $1
            if not match:
                mismatches += 1
                print(f"R{row_idx:<4} {label:<25} {col_name:>5} {old_num:>15,.2f} {new_num:>15,.2f} {'✗':>6}")
        elif str(old_val) != str(new_val):
            mismatches += 1
            print(f"R{row_idx:<4} {label:<25} {col_name:>5} {str(old_val):>15} {str(new_val):>15} {'✗':>6}")

if mismatches == 0:
    print("\n✓ ALL KEY TOTALS MATCH — IS refactor successful!")
else:
    print(f"\n✗ {mismatches} MISMATCHES found — review needed")
    
    # Show detailed comparison for mismatched rows
    for row_idx, label in key_rows.items():
        for col_idx, col_name in enumerate(COLS):
            old_val = current_values[row_idx - 1][col_idx] if row_idx - 1 < len(current_values) and col_idx < len(current_values[row_idx - 1]) else ""
            new_val = new_values[row_idx - 1][col_idx] if row_idx - 1 < len(new_values) and col_idx < len(new_values[row_idx - 1]) else ""
            try:
                old_num = float(str(old_val).replace('$', '').replace(',', ''))
                new_num = float(str(new_val).replace('$', '').replace(',', ''))
                diff = new_num - old_num
                if abs(diff) >= 1.0:
                    print(f"  DETAIL: {label} {col_name}: old={old_num:,.2f} new={new_num:,.2f} diff={diff:,.2f}")
            except:
                pass

print("\nDone.")
