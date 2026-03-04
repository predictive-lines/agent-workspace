#!/usr/bin/env python3
"""Refactor Cash Flow Statement: row 2 dates + annual formulas."""

import json, requests, sys, time

creds = json.load(open('/home/open-claw/.config/google/oauth_credentials.json'))
tokens = json.load(open('/home/open-claw/.config/google/tokens.json'))
r = requests.post('https://oauth2.googleapis.com/token', data={
    'client_id': creds['client_id'], 'client_secret': creds['client_secret'],
    'refresh_token': tokens['refresh_token'], 'grant_type': 'refresh_token'
})
TOKEN = r.json()['access_token']
open('/tmp/gtoken.txt', 'w').write(TOKEN)

SHEET_ID = "13KQXudrHd5F3p-NHrr_RTkSWuIAbhVuDp9GIDVNCetM"
HEADERS = {"Authorization": f"Bearer {TOKEN}", "Content-Type": "application/json"}
BASE = f"https://sheets.googleapis.com/v4/spreadsheets/{SHEET_ID}"
SN = "Cash Flow Statement"

# Capture current values
print("Capturing current CF values...")
resp = requests.get(f"{BASE}/values/'{SN}'!B1:I66", headers={"Authorization": f"Bearer {TOKEN}"})
old_vals = resp.json().get('values', [])

COLS = ['B', 'C', 'D', 'E', 'F', 'G', 'H', 'I']
NEXT = ['C', 'D', 'E', 'F', 'G', 'H', 'I', 'J']
ROW2 = {
    'B': '=DATE(2022,10,1)', 'C': '=DATE(2023,10,1)',
    'D': '=DATE(2024,10,1)', 'E': '=DATE(2025,10,1)',
    'F': '=first_post_close_month', 'G': '=DATE(2027,1,1)',
    'H': '=DATE(2028,1,1)', 'I': '=DATE(2029,1,1)',
    'J': '=DATE(2030,1,1)',
}

# CF row categories
# All historical use cr-dr (Credits - Debits - SDE)
BUDGET_ROWS = list(range(9, 26)) + list(range(29, 32)) + list(range(35, 50))
DS_ROWS = list(range(56, 64))

# Debt service schedule mapping: row -> (sheet_name, col, extra_check)
DS_MAP = {
    56: ("Debt Service Schedule - SBA 7a", "E", False),
    57: ("Debt Service Schedule - SBA 7a", "D", False),
    58: ("Debt Service Schedule - Seller Note", "E", False),
    59: ("Debt Service Schedule - Seller Note", "D", False),
    60: ("Debt Service Schedule - Seller Note 2", "E", False),
    61: ("Debt Service Schedule - Seller Note 2", "D", False),
    62: ("Debt Service Schedule - 2025 FORD F250", "E", True),  # 36-month cap
    63: ("Debt Service Schedule - 2025 FORD F250", "D", True),
}

MULT = {'F': '', 'G': '*Budget!$O$2:$O$534*Budget!$S$2:$S$534',
        'H': '*Budget!$P$2:$P$534*Budget!$S$2:$S$534',
        'I': '*Budget!$Q$2:$Q$534*Budget!$S$2:$S$534'}


def hist_formula(col, ncol, row):
    """Historical SUMIFS — all CF rows use cr-dr with SDE adjustment."""
    td = "'transaction details'!"
    def sf(c, extra=""):
        return (f"SUMIFS({td}{c}:{c},{td}$N:$N,$A{row},"
                f"{td}$F:$F,\">=\"&{col}$2,{td}$F:$F,\"<\"&{ncol}$2{extra})")
    return f"=({sf('$V')}-{sf('$T')})-({sf('$V', f',{td}$AA:$AA,1')}-{sf('$T', f',{td}$AA:$AA,1')})"


def budget_proforma(col, ncol, row, mult_str):
    """Annual SUMPRODUCT using MAP/LAMBDA/SEQUENCE."""
    B = "Budget!"
    mc = f"YEAR({ncol}$2)*12+MONTH({ncol}$2)-YEAR({col}$2)*12-MONTH({col}$2)"
    sp = (
        f"SUMPRODUCT("
        f"({B}$H$2:$H$534=$A{row})*"
        f"({B}$C$2:$C$534<EDATE({col}$2,n+1))*"
        f"(IF({B}$D$2:$D$534=\"\",1,{B}$D$2:$D$534>=EDATE({col}$2,n)))*"
        f"(IF({B}$E$2:$E$534<=0,"
        f"(YEAR({B}$C$2:$C$534)=YEAR(EDATE({col}$2,n)))*"
        f"(MONTH({B}$C$2:$C$534)=MONTH(EDATE({col}$2,n))),"
        f"MOD(MONTH(EDATE({col}$2,n))-MONTH({B}$C$2:$C$534)+12,{B}$E$2:$E$534)=0))*"
        f"{B}$G$2:$G$534{mult_str})"
    )
    return f"=SUM(MAP(SEQUENCE({mc},1,0),LAMBDA(n,{sp})))"


def ds_proforma(col, ncol, row, sheet_name, ds_col, has_cap):
    """Annual debt service using MAP/LAMBDA/SEQUENCE with INDIRECT."""
    mc = f"YEAR({ncol}$2)*12+MONTH({ncol}$2)-YEAR({col}$2)*12-MONTH({col}$2)"
    
    period = f"(YEAR(EDATE({col}$2,n))-YEAR(proposed_close_date))*12+MONTH(EDATE({col}$2,n))-MONTH(proposed_close_date)"
    indirect = f"INDIRECT(\"'{sheet_name}'!{ds_col}\"&(4+{period}))"
    
    if has_cap:
        # F250 has 36-month cap
        inner = f"IF(EDATE({col}$2,n)<=proposed_close_date,0,IF((YEAR(EDATE({col}$2,n))-2025)*12+MONTH(EDATE({col}$2,n))-3>36,0,{indirect}))"
    else:
        inner = f"IF(EDATE({col}$2,n)<=proposed_close_date,0,{indirect})"
    
    return f"=SUM(MAP(SEQUENCE({mc},1,0),LAMBDA(n,{inner})))"


# Build updates
updates = []

# Row 2 dates
for col, formula in ROW2.items():
    updates.append({"range": f"'{SN}'!{col}2", "values": [[formula]]})
updates.append({"range": f"'{SN}'!A2", "values": [["Period Start"]]})

# Budget SUMPRODUCT rows (historical + pro forma)
for row in BUDGET_ROWS:
    for i, col in enumerate(COLS):
        ncol = NEXT[i]
        if col in ('B', 'C', 'D', 'E'):
            formula = hist_formula(col, ncol, row)
        else:
            formula = budget_proforma(col, ncol, row, MULT[col])
        updates.append({"range": f"'{SN}'!{col}{row}", "values": [[formula]]})

# Debt service rows (historical + pro forma)
for row in DS_ROWS:
    sheet_name, ds_col, has_cap = DS_MAP[row]
    for i, col in enumerate(COLS):
        ncol = NEXT[i]
        if col in ('B', 'C', 'D', 'E'):
            formula = hist_formula(col, ncol, row)
        else:
            formula = ds_proforma(col, ncol, row, sheet_name, ds_col, has_cap)
        updates.append({"range": f"'{SN}'!{col}{row}", "values": [[formula]]})

print(f"Generated {len(updates)} updates")

# Write
print("Writing to Google Sheets...")
for i in range(0, len(updates), 500):
    chunk = updates[i:i+500]
    resp = requests.post(f"{BASE}/values:batchUpdate", headers=HEADERS,
                        json={"valueInputOption": "USER_ENTERED", "data": chunk})
    if resp.status_code != 200:
        print(f"ERROR: {resp.status_code} - {resp.text[:500]}")
        sys.exit(1)
    print(f"  Chunk {i//500+1}: {len(chunk)} cells")

# Verify
time.sleep(5)
print("\nVerifying...")
resp = requests.get(f"{BASE}/values/'{SN}'!B1:I66", headers={"Authorization": f"Bearer {TOKEN}"})
new_vals = resp.json().get('values', [])

key_rows = {26: "CF FROM OPS", 32: "CF FROM INVEST", 50: "CF FROM FIN",
            52: "NET CHANGE", 64: "TOTAL DS", 66: "DSCR"}

mismatches = 0
print(f"\n{'Row':<6} {'Label':<18} {'Col':>4} {'Old':>14} {'New':>14} {'Diff':>10}")
print("-" * 66)

for ridx, label in key_rows.items():
    for ci, cn in enumerate(COLS):
        try:
            ov = str(old_vals[ridx-1][ci]).replace('$','').replace(',','').replace('x','')
            nv = str(new_vals[ridx-1][ci]).replace('$','').replace(',','').replace('x','')
            if ov == '' or nv == '': continue
            ov_f = float(ov)
            nv_f = float(nv)
            diff = nv_f - ov_f
            if abs(diff) >= 1.0:
                mismatches += 1
                print(f"R{ridx:<4} {label:<18} {cn:>4} {ov_f:>14,.0f} {nv_f:>14,.0f} {diff:>+10,.0f}")
        except:
            pass

if mismatches == 0:
    print("✓ ALL CF TOTALS MATCH!")
else:
    print(f"\n✗ {mismatches} mismatches")

print("\nDone.")
