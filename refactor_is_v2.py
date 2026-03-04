#!/usr/bin/env python3
"""
Refactor Income Statement v2:
Fixed: occurrence count now computes overlap between Budget item dates and period dates.
"""

import json, requests, sys, time

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
SN = "Income Statement"

# ── Capture current values ────────────────────────────────────────────
print("Capturing current IS values...")
resp = requests.get(f"{BASE}/values/'{SN}'!B1:I87", headers={"Authorization": f"Bearer {TOKEN}"})
old_vals = resp.json().get('values', [])

# ── Column mapping ────────────────────────────────────────────────────
COLS = ['B', 'C', 'D', 'E', 'F', 'G', 'H', 'I']
NEXT = ['C', 'D', 'E', 'F', 'G', 'H', 'I', 'J']

ROW2 = {
    'B': '=DATE(2022,10,1)', 'C': '=DATE(2023,10,1)',
    'D': '=DATE(2024,10,1)', 'E': '=DATE(2025,10,1)',
    'F': '=proposed_close_date', 'G': '=DATE(2027,1,1)',
    'H': '=DATE(2028,1,1)', 'I': '=DATE(2029,1,1)',
    'J': '=DATE(2030,1,1)',
}

# Row categories
REVENUE_ROWS = [4, 5, 6]
COGS_ROWS = list(range(10, 34))
OPEX_ROWS = list(range(39, 72))
OIE_ROWS = list(range(79, 85))

# Multiplier columns per pro forma period
MULT = {'F': None, 'G': 'O', 'H': 'P', 'I': 'Q'}

# ── Formula generators ────────────────────────────────────────────────

def hist_formula(col, ncol, row, sign):
    """Historical SUMIFS with SDE adjustment."""
    if sign == 'cr-dr':
        f, s = '$V', '$T'
    else:
        f, s = '$T', '$V'
    td = "'transaction details'!"
    def sumifs(dr_cr, extra=""):
        return (f"SUMIFS({td}{dr_cr}:{dr_cr},{td}$N:$N,$A{row},"
                f"{td}$F:$F,\">=\"&{col}$2,{td}$F:$F,\"<\"&{ncol}$2{extra})")
    return f"=({sumifs(f)}-{sumifs(s)})-({sumifs(f, f',{td}$AA:$AA,1')}-{sumifs(s, f',{td}$AA:$AA,1')})"


def proforma_formula(col, ncol, row, mult_col):
    """Annual SUMPRODUCT with correct overlap-based occurrence count."""
    B = "Budget!"
    
    # Budget end date as exclusive month (1st of month after D)
    # If D is empty, use period end as effective end
    be = f"IF({B}$D$2:$D$534=\"\",{ncol}$2,DATE(YEAR({B}$D$2:$D$534),MONTH({B}$D$2:$D$534)+1,1))"
    
    # For E=1 (monthly): count overlap months between [MAX(C,ps), MIN(be,pe))
    overlap_months = (
        f"MAX(0,"
        f"YEAR(MIN({be},{ncol}$2))*12+MONTH(MIN({be},{ncol}$2))"
        f"-YEAR(MAX({B}$C$2:$C$534,{col}$2))*12-MONTH(MAX({B}$C$2:$C$534,{col}$2))"
        f")"
    )
    
    # For E=12 (annual): fires once if start month falls in period
    annual_fires = (
        f"((MONTH({B}$C$2:$C$534)>=MONTH({col}$2))"
        f"+((MONTH({B}$C$2:$C$534)<MONTH({ncol}$2))"
        f"*(YEAR({ncol}$2)>YEAR({col}$2)))>0)*1"
    )
    
    # For E=0 (one-time): fires if start date in period
    onetime = f"({B}$C$2:$C$534>={col}$2)*({B}$C$2:$C$534<{ncol}$2)"
    
    # Occurrence count
    occ = (
        f"IF({B}$E$2:$E$534<=0,{onetime},"
        f"IF({B}$E$2:$E$534=1,{overlap_months},"
        f"{annual_fires}))"
    )
    
    # Build SUMPRODUCT
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


# ── Build updates ─────────────────────────────────────────────────────
updates = []

# Row 2 dates + label
for col, formula in ROW2.items():
    updates.append({"range": f"'{SN}'!{col}2", "values": [[formula]]})
updates.append({"range": f"'{SN}'!A2", "values": [["Period Start"]]})

# All data rows
all_rows = REVENUE_ROWS + COGS_ROWS + OPEX_ROWS + OIE_ROWS
for row in all_rows:
    sign = 'cr-dr' if (row in REVENUE_ROWS or row in OIE_ROWS) else 'dr-cr'
    for i, col in enumerate(COLS):
        ncol = NEXT[i]
        if col in ('B', 'C', 'D', 'E'):
            formula = hist_formula(col, ncol, row, sign)
        else:
            formula = proforma_formula(col, ncol, row, MULT[col])
        updates.append({"range": f"'{SN}'!{col}{row}", "values": [[formula]]})

print(f"Generated {len(updates)} updates")

# ── Write to Sheets ──────────────────────────────────────────────────
print("Writing to Google Sheets...")
for i in range(0, len(updates), 500):
    chunk = updates[i:i+500]
    resp = requests.post(f"{BASE}/values:batchUpdate", headers=HEADERS,
                        json={"valueInputOption": "USER_ENTERED", "data": chunk})
    if resp.status_code != 200:
        print(f"ERROR: {resp.status_code} - {resp.text[:500]}")
        sys.exit(1)
    print(f"  Chunk {i//500+1}: {len(chunk)} cells")

# ── Verify ────────────────────────────────────────────────────────────
time.sleep(3)
print("\nVerifying...")
resp = requests.get(f"{BASE}/values/'{SN}'!B1:I87", headers={"Authorization": f"Bearer {TOKEN}"})
new_vals = resp.json().get('values', [])

key_rows = {7: "TOTAL REVENUE", 34: "TOTAL COGS", 36: "GROSS PROFIT",
            72: "TOTAL OPEX", 74: "OPERATING INCOME", 87: "NET INCOME"}

mismatches = 0
print(f"\n{'Row':<6} {'Label':<22} {'Col':>4} {'Old':>14} {'New':>14} {'Diff':>10}")
print("-" * 70)

for ridx, label in key_rows.items():
    for ci, cn in enumerate(COLS):
        try:
            ov = float(str(old_vals[ridx-1][ci]).replace('$','').replace(',',''))
            nv = float(str(new_vals[ridx-1][ci]).replace('$','').replace(',',''))
            diff = nv - ov
            if abs(diff) >= 1.0:
                mismatches += 1
                print(f"R{ridx:<4} {label:<22} {cn:>4} {ov:>14,.0f} {nv:>14,.0f} {diff:>+10,.0f}")
        except:
            pass

if mismatches == 0:
    print("✓ ALL KEY TOTALS MATCH!")
else:
    print(f"\n✗ {mismatches} mismatches")
    # Show individual line items with biggest diffs for debugging
    print("\nLargest line-item diffs (col G = FY2027):")
    for row in all_rows:
        try:
            ov = float(str(old_vals[row-1][5]).replace('$','').replace(',',''))  # col G = index 5
            nv = float(str(new_vals[row-1][5]).replace('$','').replace(',',''))
            diff = nv - ov
            if abs(diff) >= 100:
                label = old_vals[row-1][0] if len(old_vals[row-1]) > 0 else f"Row{row}"
                # Get label from A column
                pass
        except:
            pass
    
    # Better: read A column labels
    resp2 = requests.get(f"{BASE}/values/'{SN}'!A1:A87", headers={"Authorization": f"Bearer {TOKEN}"})
    labels = [r[0] if r else '' for r in resp2.json().get('values',[])]
    
    diffs = []
    for row in all_rows:
        for ci, cn in enumerate(COLS):
            if cn not in ('F','G','H','I'): continue
            try:
                ov = float(str(old_vals[row-1][ci]).replace('$','').replace(',',''))
                nv = float(str(new_vals[row-1][ci]).replace('$','').replace(',',''))
                diff = nv - ov
                if abs(diff) >= 50:
                    diffs.append((abs(diff), row, cn, labels[row-1] if row-1 < len(labels) else '', ov, nv, diff))
            except:
                pass
    
    diffs.sort(reverse=True)
    print(f"\nTop 15 line-item diffs:")
    for _, row, cn, label, ov, nv, diff in diffs[:15]:
        print(f"  R{row} {label:35s} {cn}: {ov:>12,.0f} → {nv:>12,.0f} ({diff:>+10,.0f})")
