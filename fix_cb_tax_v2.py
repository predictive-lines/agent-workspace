#!/usr/bin/env python3
"""Fix CB estimated tax to use CB-internal NI sum instead of IS reference.

Replace 'Income Statement'!$F$89 with SUM of post-close NI from CB's own row 87.
- CJ-CQ section: passthrough = SUM($CJ$87:$CQ$87)
- CZ-DG section: passthrough = SUM($CZ$87:$DG$87)
- CY2027+ already uses $DH$160/4 (self-contained) — no change needed.
"""

import json, urllib.request, urllib.parse

SHEET_ID = '13KQXudrHd5F3p-NHrr_RTkSWuIAbhVuDp9GIDVNCetM'
TOKEN_PATH = '/home/open-claw/.config/google/tokens.json'

def load_token():
    with open(TOKEN_PATH) as f:
        return json.load(f)['access_token']

def make_tax_formula(col_ref, ni_sum_range):
    """Build estimated tax formula using CB-internal NI sum as passthrough."""
    return (
        f"=IF(OR(MONTH({col_ref})=1,MONTH({col_ref})=4,MONTH({col_ref})=6,MONTH({col_ref})=9),"
        f"MAX(0,LET("
        f"passthru,SUM({ni_sum_range}),"
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

updates = []

# CJ-CQ (post-close section): use CB's own post-close NI
for col in ['CJ','CK','CL','CM','CN','CO','CP','CQ']:
    formula = make_tax_formula(f"{col}$2", "$CJ$87:$CQ$87")
    updates.append({'range': f"'cash bridge'!{col}160", 'values': [[formula]]})

# CZ-DG (full FY section, post-close months): use that section's post-close NI
for col in ['CZ','DA','DB','DC','DD','DE','DF','DG']:
    formula = make_tax_formula(f"{col}$2", "$CZ$87:$DG$87")
    updates.append({'range': f"'cash bridge'!{col}160", 'values': [[formula]]})

print(f"Updating {len(updates)} cells")
print(f"\nSample (CK160): passthru = SUM($CJ$87:$CQ$87)")
print(f"Sample (DA160): passthru = SUM($CZ$87:$DG$87)")

token = load_token()
body = json.dumps({'valueInputOption': 'USER_ENTERED', 'data': updates}).encode()
url = f'https://sheets.googleapis.com/v4/spreadsheets/{SHEET_ID}/values:batchUpdate'
req = urllib.request.Request(url, data=body, headers={
    'Authorization': f'Bearer {token}',
    'Content-Type': 'application/json'
})
resp = json.loads(urllib.request.urlopen(req).read())
print(f"Updated {resp.get('totalUpdatedCells', 0)} cells")

# Verify
import time; time.sleep(2)
verify_ranges = ["'cash bridge'!CK160", "'cash bridge'!DA160"]
params = '&'.join(f'ranges={urllib.parse.quote(r)}' for r in verify_ranges)
vurl = f'https://sheets.googleapis.com/v4/spreadsheets/{SHEET_ID}/values:batchGet?{params}&valueRenderOption=UNFORMATTED_VALUE'
vresp = json.loads(urllib.request.urlopen(urllib.request.Request(vurl, headers={'Authorization': f'Bearer {token}'})).read())

for vr in vresp['valueRanges']:
    v = vr.get('values',[[0]])[0][0]
    print(f"  {vr['range']}: {v:,.2f}")

# Also verify no IS references remain
furl = f'https://sheets.googleapis.com/v4/spreadsheets/{SHEET_ID}/values/%27cash%20bridge%27!CK160?valueRenderOption=FORMULA'
fresp = json.loads(urllib.request.urlopen(urllib.request.Request(furl, headers={'Authorization': f'Bearer {token}'})).read())
f = fresp.get('values',[['']])[0][0]
has_is = 'Income Statement' in f
print(f"\nIS reference in CK160: {'⚠️ YES' if has_is else '✅ NONE'}")
print(f"Uses SUM($CJ$87:$CQ$87): {'✅' if '$CJ$87:$CQ$87' in f else '⚠️ NO'}")
