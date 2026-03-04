#!/usr/bin/env python3
"""BS fixes: zero First Bank/Petty Cash/Distributions post-close,
add Post-Close Checking, fix AR/AP formulas, swap row 36/37."""

import json

COLS = ['F', 'G', 'H', 'I']
NCOLS = ['G', 'H', 'I', 'J']  # next column for end date
IF_A = '\'Deal Terms\'!$B$24="Asset"'
ERR = '"ERROR: Stock sale not modeled"'

updates = []

# 1. Zero First Bank (row 6) post-close
for c in COLS:
    updates.append({"range": f"'Balance Sheet'!{c}6",
        "values": [[f'=IF({IF_A},0,{ERR})']]})

# 2. Zero Petty Cash (row 7) post-close
for c in COLS:
    updates.append({"range": f"'Balance Sheet'!{c}7",
        "values": [[f'=IF({IF_A},0,{ERR})']]})

# 3. Repurpose Undeposited Funds (row 8) as Post-Close Checking Account
updates.append({"range": "'Balance Sheet'!A8", "values": [["Post-Close Checking Account"]]})
for c in COLS:
    updates.append({"range": f"'Balance Sheet'!{c}8",
        "values": [[f'=IF({IF_A},\'Deal Terms\'!B21,{ERR})']]})

# 4. AR (row 11) = Revenue * ar_days / period_days
for c, nc in zip(COLS, NCOLS):
    formula = f'=IF({IF_A},\'Income Statement\'!{c}7*ar_days/({nc}$2-{c}$2),{ERR})'
    updates.append({"range": f"'Balance Sheet'!{c}11", "values": [[formula]]})

# 5. AP (row 43) = COGS * ap_days / period_days (positive = owed to suppliers)
for c, nc in zip(COLS, NCOLS):
    formula = f'=IF({IF_A},\'Income Statement\'!{c}34*ap_days/({nc}$2-{c}$2),{ERR})'
    updates.append({"range": f"'Balance Sheet'!{c}43", "values": [[formula]]})

# 6. Swap row 36 (Total) and row 37 (Goodwill)
# Row 36 becomes Goodwill, Row 37 becomes Total

# Get current row 37 formulas and put them in row 36
# Row 37 (Goodwill) historical: SUMIFS pattern, pro forma: IF(Asset, calculation)
# For simplicity, copy the exact formulas from row 37 to row 36

# Row 36 label -> Goodwill
updates.append({"range": "'Balance Sheet'!A36", "values": [["Goodwill & Intangible Assets"]]})

# Row 36 historical (B-E): use same SUMIFS as current row 37
for c in ['B', 'C', 'D', 'E']:
    nc = chr(ord(c)+1)
    formula = (f'=SUMIFS(\'transaction details\'!$T:$T,\'transaction details\'!$N:$N,$A36,'
               f'\'transaction details\'!$F:$F,"<"{nc}$2)-'
               f'SUMIFS(\'transaction details\'!$V:$V,\'transaction details\'!$N:$N,$A36,'
               f'\'transaction details\'!$F:$F,"<"{nc}$2)')
    updates.append({"range": f"'Balance Sheet'!{c}36", "values": [[formula]]})

# Row 36 pro forma (F-I): Goodwill = Purchase Price - tangible net assets, amortized
# Current formula from row 37: ('Deal Terms'!B18-E32-E16) - (('Deal Terms'!B18-E32-E16)/180 * months)
# F (FY2026PC): 8 months of amortization
updates.append({"range": "'Balance Sheet'!F36", "values": [
    [f'=IF({IF_A},(\'Deal Terms\'!B18-E32-E16)-((\'Deal Terms\'!B18-E32-E16)/180*8),{ERR})']]})
updates.append({"range": "'Balance Sheet'!G36", "values": [
    [f'=IF({IF_A},(\'Deal Terms\'!B18-E32-E16)-((\'Deal Terms\'!B18-E32-E16)/180*20),{ERR})']]})
updates.append({"range": "'Balance Sheet'!H36", "values": [
    [f'=IF({IF_A},(\'Deal Terms\'!B18-E32-E16)-((\'Deal Terms\'!B18-E32-E16)/180*32),{ERR})']]})
updates.append({"range": "'Balance Sheet'!I36", "values": [
    [f'=IF({IF_A},(\'Deal Terms\'!B18-E32-E16)-((\'Deal Terms\'!B18-E32-E16)/180*44),{ERR})']]})

# Row 37 label -> Total
updates.append({"range": "'Balance Sheet'!A37", "values": [["Total Other Noncurrent Assets"]]})

# Row 37 = row 35 + row 36 (sum of items above)
for c in ['B', 'C', 'D', 'E', 'F', 'G', 'H', 'I']:
    updates.append({"range": f"'Balance Sheet'!{c}37", "values": [[f'={c}35+{c}36']]})

# Row 38 (TOTAL ASSETS) = B27+B32+B37 (was B36, now B37 since Total moved)
for c in ['B', 'C', 'D', 'E', 'F', 'G', 'H', 'I']:
    updates.append({"range": f"'Balance Sheet'!{c}38", "values": [[f'={c}27+{c}32+{c}37']]})

# 7. Zero Distributions (row 78) post-close
for c in COLS:
    updates.append({"range": f"'Balance Sheet'!{c}78",
        "values": [[f'=IF({IF_A},0,{ERR})']]})

payload = {"valueInputOption": "USER_ENTERED", "data": updates}
print(json.dumps(payload))
print(f"\n# Total updates: {len(updates)}", file=__import__('sys').stderr)
