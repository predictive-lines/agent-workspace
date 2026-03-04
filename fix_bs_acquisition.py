#!/usr/bin/env python3
"""
Fix Balance Sheet for Asset Sale acquisition structure.
- Post-close periods get fresh equity (buyer equity, cumulative NI)
- Historical equity accounts zeroed for post-close
- Goodwill = Purchase Price - Tangible Net Assets, amortized 15 years
- Working capital from cash bridge (already linked)
- Acquisition debt from amort schedules (already linked)
- Pre-existing vehicle loans zeroed (paid off at close in asset sale)
"""

import json
import requests

# Auth
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

def update_cell(cell, value):
    url = f"https://sheets.googleapis.com/v4/spreadsheets/{SHEET_ID}/values/'Balance Sheet'!{cell}?valueInputOption=USER_ENTERED"
    resp = requests.put(url, headers=HEADERS, json={"values": [[value]]})
    if resp.status_code != 200:
        print(f"ERROR {cell}: {resp.text[:200]}")
    return resp

def batch_update(updates):
    """Updates is list of (cell, value) tuples for Balance Sheet"""
    data = []
    for cell, value in updates:
        data.append({
            "range": f"'Balance Sheet'!{cell}",
            "values": [[value]]
        })
    url = f"https://sheets.googleapis.com/v4/spreadsheets/{SHEET_ID}/values:batchUpdate"
    body = {
        "valueInputOption": "USER_ENTERED",
        "data": data
    }
    resp = requests.post(url, headers=HEADERS, json=body)
    if resp.status_code != 200:
        print(f"BATCH ERROR: {resp.text[:500]}")
    else:
        print(f"Batch updated {len(updates)} cells")
    return resp

# Post-close columns: F=FY2026PC, G=FY2027, H=FY2028, I=FY2029
# Cash bridge December columns: DG=Dec26(SDE), DT=Dec27, EG=Dec28, ET=Dec29
# Deal Terms references
PP = "'Deal Terms'!B18"  # Purchase Price ($2,600,000)
EQUITY = "'Deal Terms'!B19"  # Buyer Equity ($350,000)
BUYER_COSTS = "'Deal Terms'!B20"  # Buyer Closing Costs ($15,000)
LENDER_COSTS = "'Deal Terms'!B22"  # Lender Closing Costs ($10,000)
DEAL_TYPE = "'Deal Terms'!B24"  # Asset or Stock
WC_BRIDGE = "'Deal Terms'!B21"  # Working Capital Bridge ($250,000)

updates = []

# ============================================================
# ROW 6: First Bank (Cash) - ALREADY LINKED to cash bridge
# F6-I6 already = cash bridge Running Cash Balance
# But FY2026 Post-Close at close starts with WC bridge cash
# The cash bridge handles this, so leave as-is
# ============================================================

# ============================================================  
# ROW 11: Accounts Receivable - ALREADY LINKED to cash bridge
# ============================================================

# ============================================================
# ROW 37: Goodwill & Intangible Assets
# Goodwill = Purchase Price - Tangible Net Assets at Close
# Tangible Net Assets = PP&E (row 32) + Inventory (row 16) from pre-close
# Amortize over 15 years (180 months)
# ============================================================

# For the pre-close column (E), goodwill doesn't exist
updates.append(("E37", 0))

# Goodwill at close = Purchase Price - (Pre-Close PP&E + Pre-Close Inventory)
# Use E32 (Total PP&E pre-close) + E16 (Inventory pre-close) as tangible book value
goodwill_at_close = f"={PP}-E32-E16"

# FY2026 Post-Close: goodwill minus partial year amortization (May-Dec = 8 months)
# Monthly amortization = goodwill / 180
updates.append(("F37", f"=({PP}-E32-E16)-(({PP}-E32-E16)/180*8)"))

# FY2027: goodwill minus 20 months (8 + 12)
updates.append(("G37", f"=({PP}-E32-E16)-(({PP}-E32-E16)/180*20)"))

# FY2028: goodwill minus 32 months (20 + 12) 
updates.append(("H37", f"=({PP}-E32-E16)-(({PP}-E32-E16)/180*32)"))

# FY2029: goodwill minus 44 months (32 + 12)
updates.append(("I37", f"=({PP}-E32-E16)-(({PP}-E32-E16)/180*44)"))

# ============================================================
# ROW 36: Total Other Noncurrent Assets (include goodwill)
# ============================================================
for col in ['F', 'G', 'H', 'I']:
    updates.append((f"{col}36", f"={col}35+{col}37"))

# ============================================================
# ROW 43: Accounts Payable - ALREADY LINKED to cash bridge
# ============================================================

# ============================================================
# ROW 65: LOC - ALREADY LINKED to cash bridge
# ============================================================

# ============================================================
# ROWS 66-68: Acquisition debt - ALREADY LINKED to amort schedules
# Labels already set
# ============================================================

# ============================================================
# ROWS 69-71: Pre-existing vehicle loans
# In an asset sale, these are paid off by the seller
# Zero them out for ALL post-close periods
# ============================================================
for row in [69, 70, 71]:
    for col in ['F', 'G', 'H', 'I']:
        updates.append((f"{col}{row}", 0))

# Also zero out row 66's old label — wait, I already overwrote it with SBA 7a
# But row 67 was "First Bank-2019 Ford F350-WorkT" and now says "Seller Note"  
# And row 68 was "First Bank 2020 F350" and now says "Seller Note 2"
# The labels are already correct from yesterday's work.

# But I also need to fix the pre-close values for rows 66-68
# Pre-close: no acquisition debt yet
updates.append(("E66", 0))  # SBA 7a pre-close = 0
updates.append(("E67", 0))  # Seller Note pre-close = 0
updates.append(("E68", 0))  # Seller Note 2 pre-close = 0

# And fix historical columns (B, C, D) for acquisition debt = 0
for col in ['B', 'C', 'D']:
    updates.append((f"{col}66", 0))
    updates.append((f"{col}67", 0))
    updates.append((f"{col}68", 0))
    updates.append((f"{col}37", 0))  # No goodwill in historical periods

# ============================================================
# EQUITY SECTION - Asset Sale means fresh start
# ============================================================

# Row 77: Capital Contrib/Personal Draw → 0 for post-close
# Row 78: Distributions → 0 for post-close (new entity has no distributions yet)
# Row 79: Additional Paid-in Capital → Buyer Equity from Deal Terms B19
# Row 80: Retained Earnings → 0 for post-close (fresh start)
# Row 81: Opening Bal Equity → 0 for post-close (fresh start)
# Row 82: Cumulative Net Income → running total of post-close NI

for row in [77, 78, 80, 81]:
    for col in ['F', 'G', 'H', 'I']:
        updates.append((f"{col}{row}", 0))

# Additional Paid-in Capital = Buyer Equity - Closing Costs
for col in ['F', 'G', 'H', 'I']:
    updates.append((f"{col}79", f"={EQUITY}-{BUYER_COSTS}-{LENDER_COSTS}"))

# Cumulative Net Income:
# FY2026 Post-Close: just this period's NI from IS
updates.append(("F82", "='Income Statement'!F87"))
# FY2027: prior cumulative + this year's NI
updates.append(("G82", "=F82+'Income Statement'!G87"))
# FY2028: prior cumulative + this year's NI
updates.append(("H82", "=G82+'Income Statement'!H87"))
# FY2029: prior cumulative + this year's NI
updates.append(("I82", "=H82+'Income Statement'!I87"))

# ============================================================
# Execute all updates
# ============================================================
print(f"Total updates: {len(updates)}")
batch_update(updates)

# ============================================================
# Verify CHECK row
# ============================================================
print("\n--- Balance Check ---")
for col, year in [("E", "PreClose"), ("F", "FY2026PC"), ("G", "FY2027"), ("H", "FY2028"), ("I", "FY2029")]:
    url = f"https://sheets.googleapis.com/v4/spreadsheets/{SHEET_ID}/values/'Balance Sheet'!{col}87"
    resp = requests.get(url, headers={"Authorization": f"Bearer {TOKEN}"})
    val = resp.json().get('values', [['']])[0][0] if resp.json().get('values') else 'N/A'
    
    # Also get totals
    url2 = f"https://sheets.googleapis.com/v4/spreadsheets/{SHEET_ID}/values/'Balance Sheet'!{col}38"
    resp2 = requests.get(url2, headers={"Authorization": f"Bearer {TOKEN}"})
    assets = resp2.json().get('values', [['']])[0][0] if resp2.json().get('values') else 'N/A'
    
    url3 = f"https://sheets.googleapis.com/v4/spreadsheets/{SHEET_ID}/values/'Balance Sheet'!{col}85"
    resp3 = requests.get(url3, headers={"Authorization": f"Bearer {TOKEN}"})
    le = resp3.json().get('values', [['']])[0][0] if resp3.json().get('values') else 'N/A'
    
    print(f"{year}: Assets={assets}, L+E={le}, CHECK={val}")
