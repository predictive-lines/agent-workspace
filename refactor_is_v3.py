#!/usr/bin/env python3
"""
Refactor IS v3: Use SUM(MAP(SEQUENCE(...), LAMBDA(..., SUMPRODUCT(...)))) 
to iterate over months within each period. This replicates the exact monthly 
SUMPRODUCT logic, guaranteed to match.
"""

import json, requests, sys, time

# ── Auth ──
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
SN = "Income Statement"

# ── Capture current values ──
print("Capturing current IS values...")
resp = requests.get(f"{BASE}/values/'{SN}'!B1:I87", headers={"Authorization": f"Bearer {TOKEN}"})
old_vals = resp.json().get('values', [])

COLS = ['B', 'C', 'D', 'E', 'F', 'G', 'H', 'I']
NEXT = ['C', 'D', 'E', 'F', 'G', 'H', 'I', 'J']

ROW2 = {
    'B': '=DATE(2022,10,1)', 'C': '=DATE(2023,10,1)',
    'D': '=DATE(2024,10,1)', 'E': '=DATE(2025,10,1)',
    'F': '=proposed_close_date', 'G': '=DATE(2027,1,1)',
    'H': '=DATE(2028,1,1)', 'I': '=DATE(2029,1,1)',
    'J': '=DATE(2030,1,1)',
}

REVENUE_ROWS = [4, 5, 6]
COGS_ROWS = list(range(10, 34))
OPEX_ROWS = list(range(39, 72))
OIE_ROWS = list(range(79, 85))
MULT = {'F': '', 'G': '*Budget!$O$2:$O$534*Budget!$S$2:$S$534',
        'H': '*Budget!$P$2:$P$534*Budget!$S$2:$S$534',
        'I': '*Budget!$Q$2:$Q$534*Budget!$S$2:$S$534'}


def hist_formula(col, ncol, row, sign):
    if sign == 'cr-dr':
        f, s = '$V', '$T'
    else:
        f, s = '$T', '$V'
    td = "'transaction details'!"
    def sf(c, extra=""):
        return (f"SUMIFS({td}{c}:{c},{td}$N:$N,$A{row},"
                f"{td}$F:$F,\">=\"&{col}$2,{td}$F:$F,\"<\"&{ncol}$2{extra})")
    return f"=({sf(f)}-{sf(s)})-({sf(f, f',{td}$AA:$AA,1')}-{sf(s, f',{td}$AA:$AA,1')})"


def proforma_formula(col, ncol, row, mult_str):
    """
    =SUM(MAP(SEQUENCE(months_in_period, 1, 0), LAMBDA(n,
      SUMPRODUCT(
        (Budget!$H=$A{row})*
        (Budget!$C<EDATE({col}$2,n+1))*
        (IF(Budget!$D="",1,Budget!$D>=EDATE({col}$2,n)))*
        (IF(Budget!$E<=0,
          (YEAR(Budget!$C)=YEAR(EDATE({col}$2,n)))*(MONTH(Budget!$C)=MONTH(EDATE({col}$2,n))),
          MOD(MONTH(EDATE({col}$2,n))-MONTH(Budget!$C)+12,Budget!$E)=0))*
        Budget!$G{mult_str}
      )
    )))
    """
    B = "Budget!"
    rng = "$2:$H$534"
    # Month count from row 2 dates
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


# ── Build updates ──
updates = []

# Row 2 dates
for col, formula in ROW2.items():
    updates.append({"range": f"'{SN}'!{col}2", "values": [[formula]]})
updates.append({"range": f"'{SN}'!A2", "values": [["Period Start"]]})

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

# Sample formula for inspection
sample = [u for u in updates if u['range'] == f"'{SN}'!G4"]
if sample:
    print(f"\nSample formula (G4 Revenue FY2027):")
    print(sample[0]['values'][0][0][:300])
    print(f"... ({len(sample[0]['values'][0][0])} chars)")

# ── Write ──
print("\nWriting to Google Sheets...")
for i in range(0, len(updates), 500):
    chunk = updates[i:i+500]
    resp = requests.post(f"{BASE}/values:batchUpdate", headers=HEADERS,
                        json={"valueInputOption": "USER_ENTERED", "data": chunk})
    if resp.status_code != 200:
        print(f"ERROR: {resp.status_code} - {resp.text[:500]}")
        sys.exit(1)
    print(f"  Chunk {i//500+1}: {len(chunk)} cells")

# ── Verify ──
time.sleep(5)  # Extra time for MAP/LAMBDA to calculate
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
    print("✓ ALL KEY TOTALS MATCH — IS refactor successful!")
else:
    print(f"\n✗ {mismatches} mismatches")
    
    # Show top diffs
    resp2 = requests.get(f"{BASE}/values/'{SN}'!A1:A87", headers={"Authorization": f"Bearer {TOKEN}"})
    labels = [r[0] if r else '' for r in resp2.json().get('values',[])]
    
    diffs = []
    for row in all_rows:
        for ci, cn in enumerate(COLS):
            if cn not in ('F','G','H','I'): continue
            try:
                ov = float(str(old_vals[row-1][ci]).replace('$','').replace(',',''))
                nv = float(str(new_vals[row-1][ci]).replace('$','').replace(',',''))
                d = nv - ov
                if abs(d) >= 50:
                    diffs.append((abs(d), row, cn, labels[row-1] if row-1<len(labels) else '', ov, nv, d))
            except:
                pass
    diffs.sort(reverse=True)
    for _, row, cn, lbl, ov, nv, d in diffs[:10]:
        print(f"  R{row} {lbl:35s} {cn}: {ov:>12,.0f} → {nv:>12,.0f} ({d:>+10,.0f})")

print("\nDone.")
