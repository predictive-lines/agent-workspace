#!/usr/bin/env python3
"""Fix missing Budget multiplier ($O) and toggle ($S) in CB SUMPRODUCT formulas.

Affects: Post-close columns CJ-CQ and CZ-DG, rows with SUMPRODUCT missing $O$2:$O$722.
Pattern: Append *Budget!$O$2:$O$722*Budget!$S$2:$S$722 before the closing paren(s).
"""

import json, urllib.request, urllib.parse, re, sys

SHEET_ID = '13KQXudrHd5F3p-NHrr_RTkSWuIAbhVuDp9GIDVNCetM'
TOKEN_PATH = '/home/open-claw/.config/google/tokens.json'

def load_token():
    with open(TOKEN_PATH) as f:
        return json.load(f)['access_token']

def col_to_idx(col_str):
    """Convert column letter(s) to 0-based index: A=0, Z=25, AA=26, CJ=87"""
    result = 0
    for c in col_str:
        result = result * 26 + (ord(c) - ord('A') + 1)
    return result - 1

def idx_to_col(idx):
    """Convert 0-based index to column letter(s)"""
    result = ''
    idx += 1
    while idx > 0:
        idx, rem = divmod(idx - 1, 26)
        result = chr(65 + rem) + result
    return result

# Target columns (0-based indices)
POST_CLOSE_COLS = [col_to_idx(c) for c in ['CJ','CK','CL','CM','CN','CO','CP','CQ']]
FULL_FY_COLS = [col_to_idx(c) for c in ['CZ','DA','DB','DC','DD','DE','DF','DG']]
ALL_COLS = POST_CLOSE_COLS + FULL_FY_COLS

# Rows to check (4-190, all potential SUMPRODUCT rows)
ROW_START = 4
ROW_END = 190

SUFFIX = '*Budget!$O$2:$O$722*Budget!$S$2:$S$722'

def fetch_formulas(token, col_idx):
    """Fetch formulas for a single column, rows ROW_START:ROW_END"""
    col = idx_to_col(col_idx)
    rng = f"'cash bridge'!{col}{ROW_START}:{col}{ROW_END}"
    url = f'https://sheets.googleapis.com/v4/spreadsheets/{SHEET_ID}/values/{urllib.parse.quote(rng)}?valueRenderOption=FORMULA'
    req = urllib.request.Request(url, headers={'Authorization': f'Bearer {token}'})
    resp = json.loads(urllib.request.urlopen(req).read())
    return resp.get('values', [])

def fix_formula(formula):
    """Insert multiplier+toggle before the closing paren(s) of the SUMPRODUCT.
    
    Two patterns:
    1. Pure SUMPRODUCT: ...Budget!$G$2:$G$722)  →  ...Budget!$G$2:$G$722*...$O...*...$S...)
    2. IF-wrapped:      ...Budget!$G$2:$G$722)) →  ...Budget!$G$2:$G$722*...$O...*...$S...))
    """
    if 'SUMPRODUCT' not in formula:
        return None
    if '$O$2:$O$722' in formula:
        return None  # already has multiplier
    
    # Find the pattern: Budget!$G$2:$G$722 followed by closing parens
    # The SUMPRODUCT ends with *Budget!$G$2:$G$722) or ))
    pattern = r'(\*Budget!\$G\$2:\$G\$722)(\)+)$'
    match = re.search(pattern, formula)
    if not match:
        return None
    
    # Insert suffix before the closing parens
    insert_pos = match.start(2)
    new_formula = formula[:insert_pos] + SUFFIX + formula[insert_pos:]
    return new_formula

# Main
token = load_token()
updates = []  # (range, new_formula)
fixed_count = 0
checked = 0

for col_idx in ALL_COLS:
    col = idx_to_col(col_idx)
    rows = fetch_formulas(token, col_idx)
    
    for i, row in enumerate(rows):
        r = ROW_START + i
        if not row:
            continue
        formula = row[0]
        checked += 1
        
        new_formula = fix_formula(formula)
        if new_formula:
            cell = f"'cash bridge'!{col}{r}"
            updates.append({'range': cell, 'values': [[new_formula]]})
            fixed_count += 1

print(f"Checked {checked} formulas across {len(ALL_COLS)} columns")
print(f"Found {fixed_count} formulas to fix")

if not updates:
    print("Nothing to fix!")
    sys.exit(0)

# Show sample fixes
print("\nSample fixes:")
for u in updates[:3]:
    f = u['values'][0][0]
    print(f"  {u['range']}: ...{f[-90:]}")

# Write in batches of 500
BATCH_SIZE = 500
total_written = 0
for batch_start in range(0, len(updates), BATCH_SIZE):
    batch = updates[batch_start:batch_start + BATCH_SIZE]
    body = json.dumps({
        'valueInputOption': 'USER_ENTERED',
        'data': batch
    }).encode()
    url = f'https://sheets.googleapis.com/v4/spreadsheets/{SHEET_ID}/values:batchUpdate'
    req = urllib.request.Request(url, data=body, headers={
        'Authorization': f'Bearer {token}',
        'Content-Type': 'application/json'
    })
    resp = json.loads(urllib.request.urlopen(req).read())
    written = resp.get('totalUpdatedCells', 0)
    total_written += written
    print(f"  Batch {batch_start//BATCH_SIZE + 1}: wrote {written} cells")

print(f"\nTotal: {total_written} formulas updated")
