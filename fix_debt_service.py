#!/usr/bin/env python3
"""Fix debt service formulas on Cash Flow Statement.
Replace SUMPRODUCT (which returns $0) with INDIRECT references to debt service schedule sheets.
"""

import json
import requests

SHEET_ID = "13KQXudrHd5F3p-NHrr_RTkSWuIAbhVuDp9GIDVNCetM"
TOKEN = open("/tmp/gtoken.txt").read().strip()
HEADERS = {"Authorization": f"Bearer {TOKEN}", "Content-Type": "application/json"}
BASE = f"https://sheets.googleapis.com/v4/spreadsheets/{SHEET_ID}"

def col_letter(idx):
    s = ""
    idx += 1
    while idx > 0:
        idx -= 1
        s = chr(65 + idx % 26) + s
        idx //= 26
    return s

# CF Statement debt service rows (1-indexed)
DEBT_ROWS = {
    56: ("Debt Service Schedule - SBA 7a", "E"),         # SBA 7a Principal
    57: ("Debt Service Schedule - SBA 7a", "D"),         # SBA 7a Interest
    58: ("Debt Service Schedule - Seller Note", "E"),    # Seller Note Principal
    59: ("Debt Service Schedule - Seller Note", "D"),    # Seller Note Interest
    60: ("Debt Service Schedule - Seller Note 2", "E"),  # Seller Note 2 Principal
    61: ("Debt Service Schedule - Seller Note 2", "D"),  # Seller Note 2 Interest
    62: ("Debt Service Schedule - 2025 FORD F250", "E"), # F250 Principal
    63: ("Debt Service Schedule - 2025 FORD F250", "D"), # F250 Interest
}

# Hidden monthly column ranges (0-indexed)
# FY2026 Post-Close: cols 9-16 (J-Q), May-Dec 2026
# FY2027: cols 17-28 (R-AC), Jan-Dec 2027
# FY2028: cols 29-40 (AD-AO), Jan-Dec 2028
# FY2029: cols 41-52 (AP-BA), Jan-Dec 2029
MONTHLY_COLS = list(range(9, 53))  # J through BA

def make_formula(row, col_idx, schedule_sheet, schedule_col):
    """Build INDIRECT formula for a debt service monthly cell."""
    cl = col_letter(col_idx)
    
    # Month offset calculation: months after proposed close
    offset = f"((YEAR({cl}$2)-YEAR(proposed_close_date))*12+MONTH({cl}$2)-MONTH(proposed_close_date))"
    
    # Base formula with pre-close check
    base = f"IF({cl}$2<=proposed_close_date,0,INDIRECT(\"'{schedule_sheet}'!{schedule_col}\"&(4+{offset})))"
    
    # F250 has a 36-month term limit
    if "F250" in schedule_sheet:
        term_check = f"(YEAR({cl}$2)-2025)*12+MONTH({cl}$2)-3"
        return f"=IF({cl}$2<=proposed_close_date,0,IF({term_check}>36,0,INDIRECT(\"'{schedule_sheet}'!{schedule_col}\"&(4+{offset}))))"
    
    return f"={base}"


def main():
    # Build the update values for all debt service monthly cells
    updates = []
    
    for row_1idx, (schedule_sheet, schedule_col) in DEBT_ROWS.items():
        for col_idx in MONTHLY_COLS:
            cl = col_letter(col_idx)
            formula = make_formula(row_1idx, col_idx, schedule_sheet, schedule_col)
            cell = f"'Cash Flow Statement'!{cl}{row_1idx}"
            updates.append({
                "range": cell,
                "values": [[formula]]
            })
    
    print(f"Updating {len(updates)} cells...")
    
    # Batch update in chunks (API limit)
    chunk_size = 100
    for i in range(0, len(updates), chunk_size):
        chunk = updates[i:i+chunk_size]
        resp = requests.post(
            f"{BASE}/values:batchUpdate",
            headers=HEADERS,
            json={
                "valueInputOption": "USER_ENTERED",
                "data": chunk
            }
        )
        resp.raise_for_status()
        print(f"  Chunk {i//chunk_size + 1}: {resp.json().get('totalUpdatedCells', 0)} cells")
    
    # Verify
    print("\nVerifying debt service values...")
    resp = requests.get(
        f"{BASE}/values/'Cash%20Flow%20Statement'!A56:I64",
        headers={"Authorization": f"Bearer {TOKEN}"}
    )
    resp.raise_for_status()
    for i, row in enumerate(resp.json().get("values", []), 56):
        label = row[0] if row else ""
        vals = [row[j] if len(row) > j else "" for j in range(1, 9)]
        print(f"  Row {i}: {label:30s} {' | '.join(f'{v:>12s}' for v in vals)}")


if __name__ == "__main__":
    main()
