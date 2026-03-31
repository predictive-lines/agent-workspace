#!/usr/bin/env python3
"""Fix CB estimated tax formulas for post-close FY2026 columns.

Problem: CJ-CQ reference $CB$160/4 (full FY2026 incl. pre-close NI = $100K/yr)
         CZ-DG reference $CR$160/4 (SDE-adjusted FY2026 = $110K/yr)
         LOC dynamically computes from IS post-close NI = $71K/yr

Fix: Replace static references with the same LET formula the LOC uses,
     adapted for CB sign convention (positive = tax burden to subtract).
     Uses IS!$F$89 for FY2026 passthrough via CHOOSE(YEAR-2025,...).
"""

import json, urllib.request, urllib.parse

SHEET_ID = '13KQXudrHd5F3p-NHrr_RTkSWuIAbhVuDp9GIDVNCetM'
TOKEN_PATH = '/home/open-claw/.config/google/tokens.json'

def load_token():
    with open(TOKEN_PATH) as f:
        return json.load(f)['access_token']

def make_tax_formula(col_ref):
    """Build the estimated tax formula for a given column reference (e.g. 'CK$2')"""
    return (
        f"=IF(OR(MONTH({col_ref})=1,MONTH({col_ref})=4,MONTH({col_ref})=6,MONTH({col_ref})=9),"
        f"MAX(0,LET("
        f"passthru,CHOOSE(MIN(YEAR({col_ref})-2025,4),"
        f"'Income Statement'!$F$89,'Income Statement'!$G$89,"
        f"'Income Statement'!$H$89,'Income Statement'!$I$89),"
        f"qbi,passthru*0.2,"
        f"wages,200000,"
        f"stdded,30000,"
        f"taxinc,MAX(wages+passthru-qbi-stdded,0),"
        f"wtax,MAX(wages-stdded,0),"
        f"fedtax,MIN(taxinc,23200)*0.1+MAX(MIN(taxinc,94300)-23200,0)*0.12"
        f"+MAX(MIN(taxinc,201050)-94300,0)*0.22+MAX(MIN(taxinc,383900)-201050,0)*0.24"
        f"+MAX(MIN(taxinc,487450)-383900,0)*0.32+MAX(MIN(taxinc,731200)-487450,0)*0.35"
        f"+MAX(taxinc-731200,0)*0.37,"
        f"wfed,MIN(wtax,23200)*0.1+MAX(MIN(wtax,94300)-23200,0)*0.12"
        f"+MAX(MIN(wtax,201050)-94300,0)*0.22+MAX(MIN(wtax,383900)-201050,0)*0.24"
        f"+MAX(MIN(wtax,487450)-383900,0)*0.32+MAX(MIN(wtax,731200)-487450,0)*0.35"
        f"+MAX(wtax-731200,0)*0.37,"
        f"statetax,passthru*0.0425,"
        f"fedtax-wfed+statetax))/4,0)"
    )

# Columns to fix (post-close FY2026)
POST_CLOSE_COLS = ['CJ','CK','CL','CM','CN','CO','CP','CQ']  # Post-close section
FULL_FY_COLS = ['CZ','DA','DB','DC','DD','DE','DF','DG']  # Full FY section (post-close months)

updates = []
for col in POST_CLOSE_COLS + FULL_FY_COLS:
    formula = make_tax_formula(f"{col}$2")
    cell = f"'cash bridge'!{col}160"
    updates.append({'range': cell, 'values': [[formula]]})

print(f"Updating {len(updates)} cells (row 160 across {len(POST_CLOSE_COLS + FULL_FY_COLS)} columns)")
print(f"\nSample formula for CK:")
print(make_tax_formula("CK$2"))

# Write
token = load_token()
body = json.dumps({
    'valueInputOption': 'USER_ENTERED',
    'data': updates
}).encode()
url = f'https://sheets.googleapis.com/v4/spreadsheets/{SHEET_ID}/values:batchUpdate'
req = urllib.request.Request(url, data=body, headers={
    'Authorization': f'Bearer {token}',
    'Content-Type': 'application/json'
})
resp = json.loads(urllib.request.urlopen(req).read())
print(f"\nUpdated {resp.get('totalUpdatedCells', 0)} cells")

# Verify: check CK160 value matches LOC K6 (absolute value)
import time; time.sleep(2)
verify_url = f'https://sheets.googleapis.com/v4/spreadsheets/{SHEET_ID}/values/%27cash%20bridge%27!CK160?valueRenderOption=UNFORMATTED_VALUE'
req2 = urllib.request.Request(verify_url, headers={'Authorization': f'Bearer {token}'})
resp2 = json.loads(urllib.request.urlopen(req2).read())
v = resp2.get('values', [[0]])[0][0]
print(f"\nCB CK160 (Jun 2026 EstTax) = {v:,.2f}")
print(f"LOC K6 (Jun 2026 Tax)     = 17,864.84 (absolute)")
print(f"Match: {'✅' if abs(v - 17864.84) < 1 else '⚠️'}")
