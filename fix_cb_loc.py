#!/usr/bin/env python3
"""
Fix Cash Bridge / LOC Waterfall discrepancies in Excel Fire Protection model.

Three fixes:
1. LOC date normalization: SUMPRODUCT date filters use 28th-of-month ($Bnn) instead of 1st-of-month
2. Multiplier fiscal year: Both LOC and CB switch Budget multiplier columns at Jan instead of Oct
3. Retainage: LOC is missing the retainage CF adjustment that CB includes

Auth: Google OAuth2 via ~/.config/google/
"""

import json, urllib.request, urllib.parse, re, sys, time

SHEET_ID = '13KQXudrHd5F3p-NHrr_RTkSWuIAbhVuDp9GIDVNCetM'
LOC_SHEET = 'Debt Service Schedule - SBA Express LOC'
CB_SHEET = 'cash bridge'

def load_tokens():
    with open('/home/open-claw/.config/google/tokens.json') as f:
        return json.load(f)

def refresh_token():
    with open('/home/open-claw/.config/google/oauth_credentials.json') as f:
        creds = json.load(f)
    tokens = load_tokens()
    data = urllib.parse.urlencode({
        'client_id': creds['client_id'],
        'client_secret': creds['client_secret'],
        'refresh_token': tokens['refresh_token'],
        'grant_type': 'refresh_token'
    }).encode()
    req = urllib.request.Request('https://oauth2.googleapis.com/token', data=data)
    resp = json.loads(urllib.request.urlopen(req).read())
    tokens['access_token'] = resp['access_token']
    with open('/home/open-claw/.config/google/tokens.json', 'w') as f:
        json.dump(tokens, f)
    return tokens['access_token']

def sheets_get(ranges, render='FORMULA'):
    token = load_tokens()['access_token']
    params = '&'.join(f'ranges={urllib.parse.quote(r)}' for r in ranges)
    url = f'https://sheets.googleapis.com/v4/spreadsheets/{SHEET_ID}/values:batchGet?{params}&valueRenderOption={render}'
    req = urllib.request.Request(url, headers={'Authorization': f'Bearer {token}'})
    return json.loads(urllib.request.urlopen(req).read())

def sheets_update(data):
    """batchUpdate values"""
    token = load_tokens()['access_token']
    url = f'https://sheets.googleapis.com/v4/spreadsheets/{SHEET_ID}/values:batchUpdate'
    body = json.dumps({
        'valueInputOption': 'USER_ENTERED',
        'data': data
    }).encode()
    req = urllib.request.Request(url, body, headers={
        'Authorization': f'Bearer {token}',
        'Content-Type': 'application/json'
    }, method='POST')
    return json.loads(urllib.request.urlopen(req).read())

def sheets_get_values(ranges, render='UNFORMATTED_VALUE'):
    return sheets_get(ranges, render)

# ============================================================
# FIX 1: LOC Date Normalization
# ============================================================
def fix_loc_date_normalization():
    """
    Replace 28th-of-month date refs in SUMPRODUCT with 1st-of-month.
    Columns C, D, E, G (Revenue, TotExp, COGS, Depreciation) for rows 5-52.
    """
    print("\n=== FIX 1: LOC Date Normalization ===")
    
    # Download formulas for columns C, D, E, G
    cols = ['C', 'D', 'E', 'G']
    ranges = [f"'{LOC_SHEET}'!{c}5:{c}52" for c in cols]
    resp = sheets_get(ranges)
    
    updates = []
    change_count = 0
    
    for ci, col in enumerate(cols):
        values = resp['valueRanges'][ci].get('values', [])
        new_values = []
        
        for ri, row in enumerate(values):
            cell = row[0] if row else ''
            if not cell or not cell.startswith('='):
                new_values.append([cell])
                continue
            
            original = cell
            formula = cell
            
            # Fix 1a: EDATE($Bnn,1) -> EDATE(DATE(YEAR($Bnn),MONTH($Bnn),1),1)
            # This is the upper bound for start date filter
            formula = re.sub(
                r'EDATE\(\$B(\d+),1\)',
                r'EDATE(DATE(YEAR($B\1),MONTH($B\1),1),1)',
                formula
            )
            
            # Fix 1b: Budget!$D$2:$D$722>=$Bnn -> Budget!$D$2:$D$722>=DATE(YEAR($Bnn),MONTH($Bnn),1)
            # This is the lower bound for end date filter
            formula = re.sub(
                r"(Budget!\$D\$2:\$D\$722>=)\$B(\d+)",
                r'\1DATE(YEAR($B\2),MONTH($B\2),1)',
                formula
            )
            
            if formula != original:
                change_count += 1
            new_values.append([formula])
        
        updates.append({
            'range': f"'{LOC_SHEET}'!{col}5:{col}52",
            'values': new_values
        })
    
    if updates:
        result = sheets_update(updates)
        print(f"  Updated {change_count} formulas across columns C, D, E, G")
        print(f"  API response: {result.get('totalUpdatedCells', 0)} cells updated")
    else:
        print("  No changes needed")
    
    return change_count

# ============================================================
# FIX 2: Multiplier Fiscal Year Correction (both LOC and CB)
# ============================================================
def fix_loc_multiplier():
    """
    Fix LOC multiplier selection to use fiscal year (Oct boundary).
    Replace YEAR($Bnn)>=20XX with (YEAR($Bnn)+(MONTH($Bnn)>=10))>=20XX
    """
    print("\n=== FIX 2a: LOC Multiplier Fiscal Year ===")
    
    cols = ['C', 'D', 'E', 'G']
    ranges = [f"'{LOC_SHEET}'!{c}5:{c}52" for c in cols]
    resp = sheets_get(ranges)
    
    updates = []
    change_count = 0
    
    for ci, col in enumerate(cols):
        values = resp['valueRanges'][ci].get('values', [])
        new_values = []
        
        for ri, row in enumerate(values):
            cell = row[0] if row else ''
            if not cell or not cell.startswith('='):
                new_values.append([cell])
                continue
            
            original = cell
            formula = cell
            
            # Replace YEAR($Bnn)>=2029 with (YEAR($Bnn)+(MONTH($Bnn)>=10))>=2029
            formula = re.sub(
                r'YEAR\(\$B(\d+)\)>=(\d{4})',
                r'(YEAR($B\1)+(MONTH($B\1)>=10))>=\2',
                formula
            )
            
            if formula != original:
                change_count += 1
            new_values.append([formula])
        
        updates.append({
            'range': f"'{LOC_SHEET}'!{col}5:{col}52",
            'values': new_values
        })
    
    if updates:
        result = sheets_update(updates)
        print(f"  Updated {change_count} formulas")
        print(f"  API response: {result.get('totalUpdatedCells', 0)} cells updated")
    
    return change_count

def fix_cb_multiplier():
    """
    Fix CB multiplier: Oct-Dec columns use wrong Budget multiplier column.
    CB hardcodes $O, $P, $Q per column. Need to fix Oct-Dec of each FY.
    """
    print("\n=== FIX 2b: CB Multiplier Fiscal Year ===")
    
    # First, get the date row to find all columns and their fiscal years
    resp = sheets_get([f"'{CB_SHEET}'!A2:EU2"], 'FORMATTED_VALUE')
    dates = resp['valueRanges'][0].get('values', [[]])[0]
    
    def col_letter(idx):
        if idx < 26: return chr(65+idx)
        return chr(64 + idx//26) + chr(65 + idx%26)
    
    # Identify columns that need fixing: Oct, Nov, Dec of each year post-close
    fix_cols = {}  # col_letter -> (current_mult, correct_mult)
    for i, d in enumerate(dates):
        if not d or '/' not in str(d) or 'Total' in str(d):
            continue
        parts = d.split('/')
        if len(parts) != 3:
            continue
        month, day, year = int(parts[0]), int(parts[1]), int(parts[2])
        
        # Determine fiscal year: if month >= 10, FY = year + 1
        if month >= 10:
            fy = year + 1
        else:
            fy = year
        
        # Determine correct multiplier column
        if fy >= 2029:
            correct = '$Q'
        elif fy >= 2028:
            correct = '$P'
        else:
            correct = '$O'
        
        # Determine what CB currently uses (calendar year based)
        if year >= 2029:
            current = '$Q'
        elif year >= 2028:
            current = '$P'
        else:
            current = '$O'
        
        if current != correct:
            col = col_letter(i)
            fix_cols[col] = (current, correct)
    
    if not fix_cols:
        print("  No CB columns need multiplier fix")
        return 0
    
    print(f"  Found {len(fix_cols)} columns needing multiplier fix:")
    for col, (curr, corr) in sorted(fix_cols.items()):
        print(f"    {col}: Budget!{curr} -> Budget!{corr}")
    
    # Now fix each column. CB SUMPRODUCT rows: 4-6 (revenue), 10-33 (COGS),
    # 39-71 (OpEx), 79-84 (Other I/E), 92-111 (CF adjustments), 121-135 (financing)
    # Actually, all SUMPRODUCT rows reference Budget multiplier.
    # Let's get all formulas for these columns and fix the multiplier reference.
    
    # Get formulas for all rows 4-135 for each fix column
    total_changes = 0
    
    # Process in batches (API limit)
    col_list = sorted(fix_cols.keys())
    batch_size = 10  # columns per batch
    
    for batch_start in range(0, len(col_list), batch_size):
        batch_cols = col_list[batch_start:batch_start + batch_size]
        ranges = [f"'{CB_SHEET}'!{c}4:{c}190" for c in batch_cols]
        resp = sheets_get(ranges)
        
        updates = []
        for ci, col in enumerate(batch_cols):
            curr_mult, corr_mult = fix_cols[col]
            values = resp['valueRanges'][ci].get('values', [])
            new_values = []
            col_changes = 0
            
            for ri, row in enumerate(values):
                cell = row[0] if row else ''
                if not cell or not cell.startswith('='):
                    new_values.append([cell])
                    continue
                
                original = cell
                # Replace Budget!$O with Budget!$P (or $P->$Q etc.)
                # Be precise: only replace in the multiplier position
                # Pattern: Budget!$O$2:$O$722
                formula = cell.replace(
                    f'Budget!{curr_mult}$2:{curr_mult}$722',
                    f'Budget!{corr_mult}$2:{corr_mult}$722'
                )
                
                if formula != original:
                    col_changes += 1
                new_values.append([formula])
            
            if col_changes > 0:
                updates.append({
                    'range': f"'{CB_SHEET}'!{col}4:{col}190",
                    'values': new_values
                })
                total_changes += col_changes
                print(f"    Column {col}: {col_changes} formulas fixed")
        
        if updates:
            result = sheets_update(updates)
            print(f"    Batch API: {result.get('totalUpdatedCells', 0)} cells updated")
    
    print(f"  Total CB multiplier fixes: {total_changes}")
    return total_changes

# ============================================================
# FIX 3: Add Retainage to LOC Net Cash Before LOC
# ============================================================
def fix_loc_retainage():
    """
    Add Retainage SUMPRODUCT to LOC's Net Cash Before LOC formula (column M).
    Currently M = F+G+H+I+J+K+L. Change to M = F+G+H+I+J+K+L+[retainage].
    
    The retainage SUMPRODUCT matches CB row 97 pattern but normalized to 1st-of-month.
    """
    print("\n=== FIX 3: Add Retainage to LOC ===")
    
    # Get current M column formulas
    resp = sheets_get([f"'{LOC_SHEET}'!M5:M52"])
    values = resp['valueRanges'][0].get('values', [])
    
    # Build the retainage SUMPRODUCT template
    # Based on CB row 97: SUMPRODUCT((Budget!$H="Retainage")*(date filters)*(period match)*$G*$O*$S)
    # But with 1st-of-month normalization and fiscal year multiplier
    retainage_template = (
        'SUMPRODUCT('
        '(Budget!$H$2:$H$722="Retainage")'
        '*(Budget!$C$2:$C$722<EDATE(DATE(YEAR($B{row}),MONTH($B{row}),1),1))'
        '*(IF(Budget!$D$2:$D$722="",1,Budget!$D$2:$D$722>=DATE(YEAR($B{row}),MONTH($B{row}),1)))'
        '*(IF(Budget!$E$2:$E$722<=0,'
        '(YEAR(Budget!$C$2:$C$722)=YEAR($B{row}))*(MONTH(Budget!$C$2:$C$722)=MONTH($B{row})),'
        'MOD(MONTH($B{row})-MONTH(Budget!$C$2:$C$722)+12,Budget!$E$2:$E$722)=0))'
        '*Budget!$G$2:$G$722'
        '*IF((YEAR($B{row})+(MONTH($B{row})>=10))>=2029,Budget!$Q$2:$Q$722,'
        'IF((YEAR($B{row})+(MONTH($B{row})>=10))>=2028,Budget!$P$2:$P$722,Budget!$O$2:$O$722))'
        '*Budget!$S$2:$S$722'
        ')'
    )
    
    updates = []
    change_count = 0
    new_values = []
    
    for ri, row_data in enumerate(values):
        cell = row_data[0] if row_data else ''
        sheet_row = ri + 5  # rows 5-52
        
        if not cell or not cell.startswith('='):
            new_values.append([cell])
            continue
        
        # Current formula: =F{row}+G{row}+H{row}+I{row}+J{row}+K{row}+L{row}
        # New formula: add retainage SUMPRODUCT
        retainage = retainage_template.format(row=sheet_row)
        new_formula = cell + '+' + retainage
        
        new_values.append([new_formula])
        change_count += 1
    
    if new_values:
        result = sheets_update([{
            'range': f"'{LOC_SHEET}'!M5:M52",
            'values': new_values
        }])
        print(f"  Updated {change_count} Net Cash Before LOC formulas with Retainage")
        print(f"  API response: {result.get('totalUpdatedCells', 0)} cells updated")
    
    return change_count

# ============================================================
# VERIFICATION
# ============================================================
def verify_results():
    """Compare CB Running Cash vs LOC Ending Cash for key periods."""
    print("\n=== VERIFICATION ===")
    
    # Get CB date row to find column mapping
    resp = sheets_get_values([f"'{CB_SHEET}'!A2:EU2"], 'FORMATTED_VALUE')
    dates = resp['valueRanges'][0].get('values', [[]])[0]
    
    def col_letter(idx):
        if idx < 26: return chr(65+idx)
        return chr(64 + idx//26) + chr(65 + idx%26)
    
    # Map months to CB columns
    cb_cols_map = {}
    for i, d in enumerate(dates):
        if not d or '/' not in str(d) or 'Total' in str(d):
            continue
        cb_cols_map[d] = col_letter(i)
    
    # Pull CB Running Cash (row 185) for FY2027 months
    fy27_months = ['10/1/2026','11/1/2026','12/1/2026','1/1/2027','2/1/2027','3/1/2027',
                   '4/1/2027','5/1/2027','6/1/2027','7/1/2027','8/1/2027','9/1/2027']
    
    cb_ranges = []
    cb_labels = []
    for m in fy27_months:
        if m in cb_cols_map:
            col = cb_cols_map[m]
            cb_ranges.append(f"'{CB_SHEET}'!{col}185")
            cb_labels.append(m)
    
    # Pull LOC Ending Cash (column Q, rows 10-21 for Oct26-Sep27)
    loc_range = f"'{LOC_SHEET}'!Q10:Q21"
    
    all_ranges = cb_ranges + [loc_range]
    resp = sheets_get_values(all_ranges, 'UNFORMATTED_VALUE')
    
    cb_values = []
    for i in range(len(cb_ranges)):
        vals = resp['valueRanges'][i].get('values', [[0]])
        cb_values.append(vals[0][0] if vals and vals[0] else 0)
    
    loc_values_raw = resp['valueRanges'][-1].get('values', [])
    loc_values = [r[0] if r else 0 for r in loc_values_raw]
    
    print(f"\n{'Month':>12} | {'CB RunCash':>12} | {'LOC EndCash':>12} | {'Diff':>10} | {'% Diff':>8}")
    print("-" * 65)
    
    max_pct = 0
    for i, m in enumerate(cb_labels):
        cb_v = cb_values[i] if i < len(cb_values) else 0
        loc_v = loc_values[i] if i < len(loc_values) else 0
        diff = cb_v - loc_v
        
        # Avoid division by zero
        if abs(cb_v) > 100:
            pct = abs(diff / cb_v) * 100
        elif abs(loc_v) > 100:
            pct = abs(diff / loc_v) * 100
        else:
            pct = 0
        
        max_pct = max(max_pct, pct)
        
        print(f"{m:>12} | {cb_v:>12,.0f} | {loc_v:>12,.0f} | {diff:>10,.0f} | {pct:>7.1f}%")
    
    print(f"\nMax percentage difference: {max_pct:.1f}%")
    return max_pct

# ============================================================
# MAIN
# ============================================================
if __name__ == '__main__':
    print("Excel Fire Protection - Financial Model Formula Fix")
    print("=" * 55)
    
    # Refresh token
    print("\nRefreshing OAuth token...")
    refresh_token()
    print("  Token refreshed")
    
    # Pre-fix verification
    print("\n--- PRE-FIX STATE ---")
    pre_max = verify_results()
    
    # Apply fixes
    fix_loc_date_normalization()
    
    # Need to re-read formulas after fix 1 since they changed
    time.sleep(1)  # Let Sheets propagate
    
    fix_loc_multiplier()
    time.sleep(1)
    
    fix_cb_multiplier()
    time.sleep(1)
    
    fix_loc_retainage()
    time.sleep(2)  # Extra time for propagation
    
    # Post-fix verification
    print("\n--- POST-FIX STATE ---")
    post_max = verify_results()
    
    print(f"\n{'='*55}")
    print(f"SUMMARY: Max diff went from {pre_max:.1f}% to {post_max:.1f}%")
    if post_max < 5:
        print("✅ All periods within 5% tolerance!")
    else:
        print("⚠️  Some periods still exceed 5% - further investigation needed")
