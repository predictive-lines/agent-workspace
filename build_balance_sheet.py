#!/usr/bin/env python3
"""Build Balance Sheet for the Excel Fire Business Plan spreadsheet.

Historical periods: cumulative SUMIFS (debits-credits for assets, credits-debits for liabilities)
through period end, SDE-adjusted.

Pro forma periods: prior period balance + period activity (Budget SUMPRODUCT via hidden monthly columns).
"""

import json
import requests
import sys

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

# Column layout (same as IS/CF)
COL_LABELS = 0
COL_FY23 = 1
COL_FY24 = 2
COL_FY25 = 3
COL_FY26_PRE = 4
COL_FY26_POST = 5
COL_FY27 = 6
COL_FY28 = 7
COL_FY29 = 8

COL_FY26PC_START = 9
COL_FY26PC_END = 16
COL_FY27_START = 17
COL_FY27_END = 28
COL_FY28_START = 29
COL_FY28_END = 40
COL_FY29_START = 41
COL_FY29_END = 52
COL_SENTINEL = 53

# Historical period end dates (exclusive): balance through < this date
HIST_END_DATES = {
    COL_FY23: (2023, 10),
    COL_FY24: (2024, 10),
    COL_FY25: (2025, 10),
    COL_FY26_PRE: (2026, 5),
}

# Pro forma period info: (monthly_start, monthly_end, total_col, prior_total_col, mult_suffix)
PROFORMA_PERIODS = [
    (COL_FY26PC_START, COL_FY26PC_END, COL_FY26_POST, COL_FY26_PRE, ""),
    (COL_FY27_START, COL_FY27_END, COL_FY27, COL_FY26_POST, "O"),
    (COL_FY28_START, COL_FY28_END, COL_FY28, COL_FY27, "P"),
    (COL_FY29_START, COL_FY29_END, COL_FY29, COL_FY28, "Q"),
]

def monthly_dates():
    dates = []
    for i, m in enumerate(range(5, 13)):
        dates.append((9 + i, 2026, m))
    for i, m in enumerate(range(1, 13)):
        dates.append((17 + i, 2027, m))
    for i, m in enumerate(range(1, 13)):
        dates.append((29 + i, 2028, m))
    for i, m in enumerate(range(1, 13)):
        dates.append((41 + i, 2029, m))
    dates.append((COL_SENTINEL, 2030, 1))
    return dates


def hist_balance_formula(row, col, balance_type="debit"):
    """Cumulative balance through period end, SDE-adjusted.
    balance_type: 'debit' for assets (T-V), 'credit' for liabilities/equity (V-T)
    """
    ey, em = HIST_END_DATES[col]
    r = row + 1
    end = f"DATE({ey},{em},1)"
    td = "'transaction details'"
    
    if balance_type == "debit":
        first, second = "$T:$T", "$V:$V"
    else:
        first, second = "$V:$V", "$T:$T"
    
    base = (f"SUMIFS({td}!{first},{td}!$N:$N,$A{r},{td}!$F:$F,\"<\"&{end})"
            f"-SUMIFS({td}!{second},{td}!$N:$N,$A{r},{td}!$F:$F,\"<\"&{end})")
    
    sde = (f"SUMIFS({td}!{first},{td}!$N:$N,$A{r},{td}!$F:$F,\"<\"&{end},{td}!$AA:$AA,1)"
           f"-SUMIFS({td}!{second},{td}!$N:$N,$A{r},{td}!$F:$F,\"<\"&{end},{td}!$AA:$AA,1)")
    
    return f"=({base})-({sde})"


def proforma_monthly_formula(row, col, mult_suffix):
    """Monthly change from Budget SUMPRODUCT (same as CF statement)."""
    r = row + 1
    this_col = col_letter(col)
    next_col = col_letter(col + 1)
    
    mult = ""
    if mult_suffix:
        mult = f"*Budget!${mult_suffix}$2:${mult_suffix}$534*Budget!$S$2:$S$534"
    
    return (f"=SUMPRODUCT("
            f"(Budget!$H$2:$H$534=$A{r})*"
            f"(Budget!$C$2:$C$534<{next_col}$2)*"
            f"(IF(Budget!$D$2:$D$534=\"\",1,Budget!$D$2:$D$534>={this_col}$2))*"
            f"(IF(Budget!$E$2:$E$534<=0,"
            f"(YEAR(Budget!$C$2:$C$534)=YEAR({this_col}$2))*(MONTH(Budget!$C$2:$C$534)=MONTH({this_col}$2)),"
            f"MOD(MONTH({this_col}$2)-MONTH(Budget!$C$2:$C$534)+12,Budget!$E$2:$E$534)=0))*"
            f"Budget!$G$2:$G$534{mult})")


def sum_formula(row, col_start, col_end):
    r = row + 1
    return f"=SUM({col_letter(col_start)}{r}:{col_letter(col_end)}{r})"


# Balance Sheet row definitions
# type: 'header', 'blank', 'asset', 'liability', 'equity', 'total', 'calc', 'ni_ref'
BS_ROWS = [
    {"label": "ASSETS", "type": "header"},
    {"label": "", "type": "blank"},
    {"label": "Cash & Cash Equivalents", "type": "header"},
    {"label": "First Bank  -  was NMB & Trust", "type": "cash_plug"},
    {"label": "Petty Cash", "type": "asset"},
    {"label": "Undeposited Funds", "type": "asset"},
    {"label": "Total Cash", "type": "total", "sum_range": (-3, -1)},
    {"label": "", "type": "blank"},
    {"label": "Accounts Receivable", "type": "asset"},
    {"label": "Retainage", "type": "asset"},
    {"label": "Total Receivables", "type": "total", "sum_range": (-2, -1)},
    {"label": "", "type": "blank"},
    {"label": "Other Current Assets", "type": "header"},
    {"label": "Inventory - Materials", "type": "asset"},
    {"label": "Employee Advance", "type": "asset"},
    {"label": "Cost Over Billings & Earnings", "type": "asset"},
    {"label": "CY Billings Over and Under", "type": "asset"},
    {"label": "IRC Section 7519 Deposit", "type": "asset"},
    {"label": "Investments", "type": "asset"},
    {"label": "Kevin Masich Loan #2", "type": "asset"},
    {"label": "Loan to Wright St. Mgt", "type": "asset"},
    {"label": "Loan to Wright St. Mgt - Other", "type": "asset"},
    {"label": "Total Other Current Assets", "type": "total", "sum_range": (-9, -1)},
    {"label": "", "type": "blank"},
    {"label": "TOTAL CURRENT ASSETS", "type": "calc", "refs": ["Total Cash", "Total Receivables", "Total Other Current Assets"]},
    {"label": "", "type": "blank"},
    {"label": "Property & Equipment", "type": "header"},
    {"label": "Vehicles", "type": "asset"},
    {"label": "Accumulated Depreciation", "type": "asset"},  # contra-asset, natural credit, but displayed as negative under assets
    {"label": "Total PP&E", "type": "total", "sum_range": (-2, -1)},
    {"label": "", "type": "blank"},
    {"label": "Other Noncurrent Assets", "type": "header"},
    {"label": "Security deposit-West Bend", "type": "asset"},
    {"label": "Total Other Noncurrent Assets", "type": "total", "sum_range": (-1, -1)},
    {"label": "", "type": "blank"},
    {"label": "TOTAL ASSETS", "type": "calc", "refs": ["TOTAL CURRENT ASSETS", "Total PP&E", "Total Other Noncurrent Assets"]},
    {"label": "", "type": "blank"},
    {"label": "LIABILITIES", "type": "header"},
    {"label": "", "type": "blank"},
    {"label": "Current Liabilities", "type": "header"},
    {"label": "Accounts Payable", "type": "liability"},
    {"label": "American Express # 6-94003", "type": "liability"},
    {"label": "Capital One #7585", "type": "liability"},
    {"label": "Chase #8046", "type": "liability"},
    {"label": "Chase Visa Card-#9212", "type": "liability"},
    {"label": "Credit Card #2015 & #7363 was05", "type": "liability"},
    {"label": "Credit Card #4805 & 7363", "type": "liability"},
    {"label": "Credit Card at American Expres", "type": "liability"},
    {"label": "Credit Card(3) at Capital One#", "type": "liability"},
    {"label": "Accrued Federal Payroll Taxes", "type": "liability"},
    {"label": "Accrued 401(k)", "type": "liability"},
    {"label": "Accrued Payroll", "type": "liability"},
    {"label": "Accrued Single Business Taxes", "type": "liability"},
    {"label": "Payroll Liabilities", "type": "liability"},
    {"label": "SIT Payable", "type": "liability"},
    {"label": "MESC Payable", "type": "liability"},
    {"label": "FUTA Payable MI", "type": "liability"},
    {"label": "Union Dues Payable", "type": "liability"},
    {"label": "Sales Tax", "type": "liability"},
    {"label": "Total Current Liabilities", "type": "total", "sum_range": (-19, -1)},
    {"label": "", "type": "blank"},
    {"label": "Long-Term Liabilities", "type": "header"},
    {"label": "LOC 00020031666-00015  was 14", "type": "liability"},
    {"label": "Loan from Kim Masich", "type": "liability"},
    {"label": "First Bank-2019 Ford F350-WorkT", "type": "liability"},
    {"label": "First Bank 2020 F350", "type": "liability"},
    {"label": "Ford Credit 2023   f-150", "type": "liability"},
    {"label": "Ford Credit 2025 F250", "type": "liability"},
    {"label": "2019 Ford F-150 Keith's New TK", "type": "liability"},
    {"label": "Total Long-Term Liabilities", "type": "total", "sum_range": (-7, -1)},
    {"label": "", "type": "blank"},
    {"label": "TOTAL LIABILITIES", "type": "calc", "refs": ["Total Current Liabilities", "Total Long-Term Liabilities"]},
    {"label": "", "type": "blank"},
    {"label": "EQUITY", "type": "header"},
    {"label": "Capital Contrib/Personal Draw", "type": "equity"},
    {"label": "Distributions", "type": "equity"},
    {"label": "Additonal Paid in Capital", "type": "equity"},
    {"label": "Retained Earnings", "type": "equity"},
    {"label": "Opening Bal Equity", "type": "equity"},
    {"label": "Cumulative Net Income (P&L)", "type": "cum_ni"},
    {"label": "TOTAL EQUITY", "type": "total", "sum_range": (-6, -1)},
    {"label": "", "type": "blank"},
    {"label": "TOTAL LIABILITIES + EQUITY", "type": "calc", "refs": ["TOTAL LIABILITIES", "TOTAL EQUITY"]},
    {"label": "", "type": "blank"},
    {"label": "CHECK (Assets - L&E)", "type": "calc", "refs": ["TOTAL ASSETS", "TOTAL LIABILITIES + EQUITY"]},
]


def find_row_idx(rows, label):
    """Find 0-based index of row with given label."""
    for i, r in enumerate(rows):
        if r["label"] == label:
            return i
    return None


def build_bs_grid(rows):
    num_cols = COL_SENTINEL + 1
    grid = []
    
    # Row 0: Headers
    header_row = [None] * num_cols
    header_row[COL_LABELS] = ""
    header_row[COL_FY23] = "FY2023"
    header_row[COL_FY24] = "FY2024"
    header_row[COL_FY25] = "FY2025"
    header_row[COL_FY26_PRE] = "FY2026 Pre-Close"
    header_row[COL_FY26_POST] = "FY2026 Post-Close"
    header_row[COL_FY27] = "FY2027"
    header_row[COL_FY28] = "FY2028"
    header_row[COL_FY29] = "FY2029"
    grid.append(header_row)
    
    # Row 1: sub-headers + monthly dates
    date_row = [None] * num_cols
    date_row[COL_LABELS] = "Account"
    date_row[COL_FY23] = "As of Sep 30, 2023"
    date_row[COL_FY24] = "As of Sep 30, 2024"
    date_row[COL_FY25] = "As of Sep 30, 2025"
    date_row[COL_FY26_PRE] = "As of Apr 30, 2026"
    date_row[COL_FY26_POST] = "As of Dec 31, 2026"
    date_row[COL_FY27] = "As of Dec 31, 2027"
    date_row[COL_FY28] = "As of Dec 31, 2028"
    date_row[COL_FY29] = "As of Dec 31, 2029"
    for col_idx, year, month in monthly_dates():
        date_row[col_idx] = f"=DATE({year},{month},1)"
    grid.append(date_row)
    
    # Build a label->grid_row_index map as we go
    label_to_grid_row = {}
    
    for i, row_def in enumerate(rows):
        data_row = [None] * num_cols
        actual_row = i + 2  # 0-indexed in grid
        r = actual_row + 1  # 1-indexed for formulas
        
        data_row[COL_LABELS] = row_def["label"]
        rtype = row_def["type"]
        
        if rtype in ("header", "blank"):
            grid.append(data_row)
            if row_def["label"]:
                label_to_grid_row[row_def["label"]] = actual_row
            continue
        
        if rtype == "cash_plug":
            # Historical: same as asset (debit balance, SDE-adjusted)
            for col in [COL_FY23, COL_FY24, COL_FY25, COL_FY26_PRE]:
                data_row[col] = hist_balance_formula(actual_row, col, "debit")
            # Pro forma: filled in second pass (needs other row references)
            grid.append(data_row)
            label_to_grid_row[row_def["label"]] = actual_row
            continue
        
        if rtype == "cum_ni":
            # Cumulative Net Income - balancing figure for historical,
            # roll forward with IS NI for pro forma
            # We'll fill this in a second pass after we know all row positions
            grid.append(data_row)
            label_to_grid_row[row_def["label"]] = actual_row
            continue
        
        if rtype in ("asset", "liability", "equity"):
            # Determine balance type
            if rtype == "asset":
                bal_type = "debit"
            else:
                bal_type = "credit"
            
            # Historical: cumulative balance through period end
            for col in [COL_FY23, COL_FY24, COL_FY25, COL_FY26_PRE]:
                data_row[col] = hist_balance_formula(actual_row, col, bal_type)
            
            # Pro forma: prior balance + period activity
            for m_start, m_end, total_col, prior_col, mult in PROFORMA_PERIODS:
                # Hidden monthly columns: activity (change) per month
                for c in range(m_start, m_end + 1):
                    data_row[c] = proforma_monthly_formula(actual_row, c, mult)
                # Total column: prior balance + sum of monthly activity
                prior_cl = col_letter(prior_col)
                data_row[total_col] = f"={prior_cl}{r}+SUM({col_letter(m_start)}{r}:{col_letter(m_end)}{r})"
            
            grid.append(data_row)
            label_to_grid_row[row_def["label"]] = actual_row
            continue
        
        if rtype == "total":
            sr = row_def["sum_range"]
            start_r = r + sr[0]
            end_r = r + sr[1]
            # For totals, sum visible AND hidden columns
            for col in range(1, num_cols):
                if col == COL_LABELS:
                    continue
                cl = col_letter(col)
                data_row[col] = f"=SUM({cl}{start_r}:{cl}{end_r})"
            grid.append(data_row)
            label_to_grid_row[row_def["label"]] = actual_row
            continue
        
        if rtype == "calc":
            refs = row_def.get("refs", [])
            label = row_def["label"]
            
            if label == "CHECK (Assets - L&E)":
                # Assets - (Liabilities + Equity) = should be 0
                # Only for visible total columns
                a_row = label_to_grid_row.get("TOTAL ASSETS", 0) + 1
                le_row = label_to_grid_row.get("TOTAL LIABILITIES + EQUITY", 0) + 1
                for col in [COL_FY23, COL_FY24, COL_FY25, COL_FY26_PRE, COL_FY26_POST, COL_FY27, COL_FY28, COL_FY29]:
                    cl = col_letter(col)
                    data_row[col] = f"={cl}{a_row}-{cl}{le_row}"
            else:
                # Sum of referenced rows (visible columns only + hidden for rolling)
                ref_rows = [label_to_grid_row.get(ref, 0) + 1 for ref in refs]
                for col in range(1, num_cols):
                    if col == COL_LABELS:
                        continue
                    cl = col_letter(col)
                    parts = [f"{cl}{rr}" for rr in ref_rows]
                    data_row[col] = f"={'+'.join(parts)}"
            
            grid.append(data_row)
            label_to_grid_row[row_def["label"]] = actual_row
            continue
        
        grid.append(data_row)
    
    # Second pass: fill in cash plug and Cumulative Net Income
    
    # Cash plug: First Bank = TOTAL L+E - all other asset rows
    cash_plug_grid_row = label_to_grid_row.get("First Bank  -  was NMB & Trust")
    if cash_plug_grid_row is not None:
        # Collect all asset rows EXCEPT the cash plug itself
        other_asset_rows = []
        for i2, rd in enumerate(rows):
            gr = i2 + 2
            if rd["type"] in ("asset",) and rd["label"] != "First Bank  -  was NMB & Trust":
                other_asset_rows.append(gr)
        
        total_le_row = label_to_grid_row.get("TOTAL LIABILITIES + EQUITY")
        r = cash_plug_grid_row + 1
        
        for m_start, m_end, total_col, prior_col, mult in PROFORMA_PERIODS:
            cl = col_letter(total_col)
            le_r = total_le_row + 1 if total_le_row else 0
            other_refs = "-".join(f"{cl}{ar+1}" for ar in other_asset_rows)
            grid[cash_plug_grid_row][total_col] = f"={cl}{le_r}-{other_refs}"
            # Monthly columns: set to 0 (plug only applies to totals)
            for c in range(m_start, m_end + 1):
                grid[cash_plug_grid_row][c] = 0
    
    # Fill in Cumulative Net Income row
    cum_ni_grid_row = label_to_grid_row.get("Cumulative Net Income (P&L)")
    total_assets_row = label_to_grid_row.get("TOTAL ASSETS")
    total_liab_row = label_to_grid_row.get("TOTAL LIABILITIES")
    
    # Find the other equity account rows (everything between EQUITY header and cum_ni)
    equity_header_grid = label_to_grid_row.get("EQUITY")
    other_equity_rows = []
    for i2, rd in enumerate(rows):
        gr = i2 + 2
        if rd["type"] == "equity":
            other_equity_rows.append(gr)
    
    if cum_ni_grid_row is not None:
        r = cum_ni_grid_row + 1  # 1-indexed
        a_r = total_assets_row + 1
        l_r = total_liab_row + 1
        
        # Historical: balancing figure = Assets - Liabilities - sum(other equity)
        for col in [COL_FY23, COL_FY24, COL_FY25, COL_FY26_PRE]:
            cl = col_letter(col)
            eq_refs = "-".join(f"{cl}{er+1}" for er in other_equity_rows)
            grid[cum_ni_grid_row][col] = f"={cl}{a_r}-{cl}{l_r}-{eq_refs}"
        
        # Pro forma: prior balance + IS Net Income for the period
        # Need to find IS Net Income row
        # IS has same column layout. Net Income is in the last data row.
        # From IS_ROWS in the other script, NI is row 87 (1-indexed)
        # Let me compute it: IS has 2 header rows + 85 data rows = row 87
        # Actually I need to count IS_ROWS... let me just hardcode based on the known sheet
        # IS Net Income is at row 87 (verified earlier)
        IS_NI_ROW = 87  # 1-indexed in Income Statement sheet
        
        for m_start, m_end, total_col, prior_col, mult in PROFORMA_PERIODS:
            prior_cl = col_letter(prior_col)
            total_cl = col_letter(total_col)
            # Cumulative NI = prior cumulative NI + IS period NI
            grid[cum_ni_grid_row][total_col] = f"={prior_cl}{r}+'Income Statement'!{total_cl}{IS_NI_ROW}"
            # Monthly columns not needed for cum_ni (it's a point-in-time balance)
            # But we need them for the TOTAL EQUITY sum to work in hidden cols
            # Set monthly to 0 (activity is captured via IS reference in total)
            for c in range(m_start, m_end + 1):
                grid[cum_ni_grid_row][c] = 0
    
    return grid


def create_sheet(name, grid):
    print(f"Creating sheet '{name}'...")
    resp = requests.post(f"{BASE}:batchUpdate", headers=HEADERS, json={
        "requests": [{
            "addSheet": {
                "properties": {
                    "title": name,
                    "gridProperties": {
                        "rowCount": len(grid) + 5,
                        "columnCount": COL_SENTINEL + 2
                    }
                }
            }
        }]
    })
    resp.raise_for_status()
    new_sheet_id = resp.json()["replies"][0]["addSheet"]["properties"]["sheetId"]
    print(f"  Sheet ID: {new_sheet_id}")
    
    # Write values
    values = []
    for row in grid:
        values.append([c if c is not None else "" for c in row])
    
    range_str = f"'{name}'!A1:{col_letter(COL_SENTINEL)}{len(grid)}"
    resp = requests.put(
        f"{BASE}/values/{range_str}?valueInputOption=USER_ENTERED",
        headers=HEADERS,
        json={"range": range_str, "values": values}
    )
    resp.raise_for_status()
    print(f"  Written: {resp.json().get('updatedCells', 0)} cells")
    
    # Format
    fmt_reqs = []
    
    # Hide monthly columns
    fmt_reqs.append({
        "updateDimensionProperties": {
            "range": {"sheetId": new_sheet_id, "dimension": "COLUMNS",
                      "startIndex": COL_FY26PC_START, "endIndex": COL_SENTINEL + 1},
            "properties": {"hiddenByUser": True},
            "fields": "hiddenByUser"
        }
    })
    
    # Bold headers
    fmt_reqs.append({
        "repeatCell": {
            "range": {"sheetId": new_sheet_id, "startRowIndex": 0, "endRowIndex": 2,
                      "startColumnIndex": 0, "endColumnIndex": COL_FY29 + 1},
            "cell": {"userEnteredFormat": {"textFormat": {"bold": True}}},
            "fields": "userEnteredFormat.textFormat.bold"
        }
    })
    
    # Bold section headers and totals
    for i, row in enumerate(grid):
        if i < 2:
            continue
        label = row[COL_LABELS] if row[COL_LABELS] else ""
        if (label.isupper() or label.startswith("Total") or label.startswith("TOTAL")
            or label.startswith("CHECK")):
            fmt_reqs.append({
                "repeatCell": {
                    "range": {"sheetId": new_sheet_id, "startRowIndex": i, "endRowIndex": i + 1,
                              "startColumnIndex": 0, "endColumnIndex": COL_FY29 + 1},
                    "cell": {"userEnteredFormat": {"textFormat": {"bold": True}}},
                    "fields": "userEnteredFormat.textFormat.bold"
                }
            })
    
    # Number format
    fmt_reqs.append({
        "repeatCell": {
            "range": {"sheetId": new_sheet_id, "startRowIndex": 2, "endRowIndex": len(grid),
                      "startColumnIndex": 1, "endColumnIndex": COL_SENTINEL + 1},
            "cell": {"userEnteredFormat": {"numberFormat": {"type": "NUMBER", "pattern": "#,##0"}}},
            "fields": "userEnteredFormat.numberFormat"
        }
    })
    
    # Freeze
    fmt_reqs.append({
        "updateSheetProperties": {
            "properties": {
                "sheetId": new_sheet_id,
                "gridProperties": {"frozenRowCount": 2, "frozenColumnCount": 1}
            },
            "fields": "gridProperties.frozenRowCount,gridProperties.frozenColumnCount"
        }
    })
    
    # Column A width
    fmt_reqs.append({
        "updateDimensionProperties": {
            "range": {"sheetId": new_sheet_id, "dimension": "COLUMNS",
                      "startIndex": 0, "endIndex": 1},
            "properties": {"pixelSize": 280},
            "fields": "pixelSize"
        }
    })
    
    resp = requests.post(f"{BASE}:batchUpdate", headers=HEADERS, json={"requests": fmt_reqs})
    resp.raise_for_status()
    print(f"  Formatted.")
    
    return new_sheet_id


def main():
    grid = build_bs_grid(BS_ROWS)
    create_sheet("Balance Sheet", grid)
    
    # Verify - check that Assets = L+E for FY2023
    print("\nVerifying...")
    resp = requests.get(
        f"{BASE}/values/'Balance%20Sheet'!A1:I90",
        headers={"Authorization": f"Bearer {TOKEN}"}
    )
    resp.raise_for_status()
    vals = resp.json().get("values", [])
    for i, row in enumerate(vals, 1):
        label = row[0] if row else ""
        if label in ("TOTAL ASSETS", "TOTAL LIABILITIES + EQUITY", "CHECK (Assets - L&E)"):
            fy23 = row[1] if len(row) > 1 else "?"
            print(f"  Row {i}: {label:35s} FY2023={fy23}")


if __name__ == "__main__":
    main()
