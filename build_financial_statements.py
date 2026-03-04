#!/usr/bin/env python3
"""Build Income Statement, Cash Flow Statement, and Balance Sheet sheets
in the Excel Fire Business Plan spreadsheet.

Architecture:
- Historical periods: SUMIFS from 'transaction details' with SDE adjustment
- Pro forma periods: SUMPRODUCT from 'Budget' with hidden monthly columns
- Period structure:
  B: FY2023 (Oct 22 - Sep 23)
  C: FY2024 (Oct 23 - Sep 24)
  D: FY2025 (Oct 24 - Sep 25)
  E: FY2026 Pre-Close (Oct 25 - Apr 26) - historical SDE-adjusted
  F: FY2026 Post-Close total (May 26 - Dec 26) - pro forma
  G: FY2027 total (Jan - Dec 27) - pro forma
  H: FY2028 total (Jan - Dec 28) - pro forma
  I: FY2029 total (Jan - Dec 29) - pro forma
  J-Q: FY2026 Post-Close monthly (8 cols, hidden)
  R-AC: FY2027 monthly (12 cols, hidden)
  AD-AO: FY2028 monthly (12 cols, hidden)
  AP-BA: FY2029 monthly (12 cols, hidden)
  BB: sentinel date column (hidden)
"""

import json
import requests
import sys
import time

SHEET_ID = "13KQXudrHd5F3p-NHrr_RTkSWuIAbhVuDp9GIDVNCetM"
TOKEN = open("/tmp/gtoken.txt").read().strip()
HEADERS = {"Authorization": f"Bearer {TOKEN}", "Content-Type": "application/json"}
BASE = f"https://sheets.googleapis.com/v4/spreadsheets/{SHEET_ID}"

def col_letter(idx):
    """Convert 0-based column index to letter(s). 0=A, 25=Z, 26=AA."""
    s = ""
    idx += 1
    while idx > 0:
        idx -= 1
        s = chr(65 + idx % 26) + s
        idx //= 26
    return s

# --- Column mapping ---
# Visible columns: A(0)=labels, B(1)-I(8)=period totals
# Hidden monthly: J(9)-Q(16)=FY26PC, R(17)-AC(28)=FY27, AD(29)-AO(40)=FY28, AP(41)-BA(52)=FY29, BB(53)=sentinel
COL_LABELS = 0  # A
COL_FY23 = 1    # B
COL_FY24 = 2    # C
COL_FY25 = 3    # D
COL_FY26_PRE = 4  # E
COL_FY26_POST = 5  # F (total)
COL_FY27 = 6     # G (total)
COL_FY28 = 7     # H (total)
COL_FY29 = 8     # I (total)

# Monthly hidden columns
COL_FY26PC_START = 9   # J = May 2026
COL_FY26PC_END = 16    # Q = Dec 2026
COL_FY27_START = 17    # R = Jan 2027
COL_FY27_END = 28      # AC = Dec 2027
COL_FY28_START = 29    # AD = Jan 2028
COL_FY28_END = 40      # AO = Dec 2028
COL_FY29_START = 41    # AP = Jan 2029
COL_FY29_END = 52      # BA = Dec 2029
COL_SENTINEL = 53       # BB = DATE(2030,1,1)

# Historical period date ranges (start_year, start_month, end_year, end_month)
# End is exclusive: "< DATE(end_y, end_m, 1)"
HIST_PERIODS = {
    COL_FY23: (2022, 10, 2023, 10),
    COL_FY24: (2023, 10, 2024, 10),
    COL_FY25: (2024, 10, 2025, 10),
    COL_FY26_PRE: (2025, 10, 2026, 5),
}

# Pro forma monthly columns: (start_col, end_col, total_col, mult_suffix)
# mult_suffix: "" = just G, "O" = G*O*S, "P" = G*P*S, "Q" = G*Q*S
PROFORMA_PERIODS = [
    (COL_FY26PC_START, COL_FY26PC_END, COL_FY26_POST, ""),
    (COL_FY27_START, COL_FY27_END, COL_FY27, "O"),
    (COL_FY28_START, COL_FY28_END, COL_FY28, "P"),
    (COL_FY29_START, COL_FY29_END, COL_FY29, "Q"),
]

# Monthly date generation
def monthly_dates():
    """Generate (col_idx, year, month) for all hidden monthly columns."""
    dates = []
    # FY2026 Post-Close: May-Dec 2026
    for i, m in enumerate(range(5, 13)):
        dates.append((COL_FY26PC_START + i, 2026, m))
    # FY2027: Jan-Dec
    for i, m in enumerate(range(1, 13)):
        dates.append((COL_FY27_START + i, 2027, m))
    # FY2028: Jan-Dec
    for i, m in enumerate(range(1, 13)):
        dates.append((COL_FY28_START + i, 2028, m))
    # FY2029: Jan-Dec
    for i, m in enumerate(range(1, 13)):
        dates.append((COL_FY29_START + i, 2029, m))
    # Sentinel
    dates.append((COL_SENTINEL, 2030, 1))
    return dates

# --- Formula generators ---

def hist_sde_formula(row, col, sign="cr-dr"):
    """Generate historical SDE-adjusted SUMIFS formula.
    sign: 'cr-dr' for revenue/OIE/CF, 'dr-cr' for COGS/OpEx/depreciation add-back.
    """
    sy, sm, ey, em = HIST_PERIODS[col]
    r = row + 1  # 1-indexed
    
    if sign == "cr-dr":
        first, second = "$V:$V", "$T:$T"
    else:
        first, second = "$T:$T", "$V:$V"
    
    td = "'transaction details'"
    start = f'DATE({sy},{sm},1)'
    end = f'DATE({ey},{em},1)'
    
    base = (f"SUMIFS({td}!{first},{td}!$N:$N,$A{r},{td}!$F:$F,\">=\"&{start},{td}!$F:$F,\"<\"&{end})"
            f"-SUMIFS({td}!{second},{td}!$N:$N,$A{r},{td}!$F:$F,\">=\"&{start},{td}!$F:$F,\"<\"&{end})")
    
    sde = (f"SUMIFS({td}!{first},{td}!$N:$N,$A{r},{td}!$F:$F,\">=\"&{start},{td}!$F:$F,\"<\"&{end},{td}!$AA:$AA,1)"
           f"-SUMIFS({td}!{second},{td}!$N:$N,$A{r},{td}!$F:$F,\">=\"&{start},{td}!$F:$F,\"<\"&{end},{td}!$AA:$AA,1)")
    
    return f"=({base})-({sde})"


def proforma_monthly_formula(row, col, mult_suffix):
    """Generate SUMPRODUCT formula for a single pro forma month.
    row: 0-indexed row
    col: 0-indexed column
    mult_suffix: "" or "O" or "P" or "Q"
    """
    r = row + 1  # 1-indexed
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
    """SUM across monthly columns for a total column."""
    r = row + 1
    return f"=SUM({col_letter(col_start)}{r}:{col_letter(col_end)}{r})"


# --- Row definitions ---
# Each row is a dict with:
#   label: string
#   type: 'header' | 'account' | 'total' | 'subtotal' | 'blank' | 'ebitda'
#   sign: 'cr-dr' or 'dr-cr' (for account rows)
#   formula: for calculated rows, a lambda(row_1indexed, col_letter) -> formula string
#   total_refs: for total rows, list of row labels to sum

# We'll define the structure and generate formulas dynamically.

# Income Statement structure (matching cash bridge rows 3-87)
IS_ROWS = [
    {"label": "REVENUE", "type": "header"},
    {"label": "Contracts", "type": "account", "sign": "cr-dr"},
    {"label": "Inspections", "type": "account", "sign": "cr-dr"},
    {"label": "Service", "type": "account", "sign": "cr-dr"},
    {"label": "TOTAL REVENUE", "type": "total", "sum_range": (-3, -1)},  # sum 3 rows above through 1 above
    {"label": "", "type": "blank"},
    {"label": "COST OF GOODS SOLD", "type": "header"},
    {"label": "Bond Costs", "type": "account", "sign": "dr-cr"},
    {"label": "Design - Direct", "type": "account", "sign": "dr-cr"},
    {"label": "Direct Materials", "type": "account", "sign": "dr-cr"},
    {"label": "Discounts", "type": "account", "sign": "dr-cr"},
    {"label": "Employee Benefits", "type": "account", "sign": "dr-cr"},
    {"label": "Equipment Repair & Rental", "type": "account", "sign": "dr-cr"},
    {"label": "FICA Expense", "type": "account", "sign": "dr-cr"},
    {"label": "FICA Medical Expense", "type": "account", "sign": "dr-cr"},
    {"label": "FUTA Expense", "type": "account", "sign": "dr-cr"},
    {"label": "Insurance - Auto", "type": "account", "sign": "dr-cr"},
    {"label": "Insurance - Package Policy", "type": "account", "sign": "dr-cr"},
    {"label": "Insurance - Work Comp.", "type": "account", "sign": "dr-cr"},
    {"label": "License & Permits", "type": "account", "sign": "dr-cr"},
    {"label": "Plan Costs", "type": "account", "sign": "dr-cr"},
    {"label": "Sales Tax", "type": "account", "sign": "dr-cr"},
    {"label": "Small Tools & Equipment", "type": "account", "sign": "dr-cr"},
    {"label": "Subcontractors", "type": "account", "sign": "dr-cr"},
    {"label": "Subsistence", "type": "account", "sign": "dr-cr"},
    {"label": "SUTA Expense", "type": "account", "sign": "dr-cr"},
    {"label": "Truck & Auto Expense", "type": "account", "sign": "dr-cr"},
    {"label": "Wages", "type": "account", "sign": "dr-cr"},
    {"label": "Canceled Sevices", "type": "account", "sign": "dr-cr"},
    {"label": "Other Taxes", "type": "account", "sign": "dr-cr"},
    {"label": "Union Benefits", "type": "account", "sign": "dr-cr"},
    {"label": "TOTAL COGS", "type": "total", "sum_range": (-24, -1)},  # Bond Costs through Union Benefits
    {"label": "", "type": "blank"},
    {"label": "GROSS PROFIT", "type": "calc"},  # Revenue - COGS
    {"label": "", "type": "blank"},
    {"label": "OPERATING EXPENSES", "type": "header"},
    {"label": "Advertsing & Promotion", "type": "account", "sign": "dr-cr"},
    {"label": "Bad Debts", "type": "account", "sign": "dr-cr"},
    {"label": "Bank Charges", "type": "account", "sign": "dr-cr"},
    {"label": "Cash Over & Short", "type": "account", "sign": "dr-cr"},
    {"label": "Cellular Phones", "type": "account", "sign": "dr-cr"},
    {"label": "Donations", "type": "account", "sign": "dr-cr"},
    {"label": "Dues & Subscriptions", "type": "account", "sign": "dr-cr"},
    {"label": "Employee Advance", "type": "account", "sign": "dr-cr"},
    {"label": "Health Insurance", "type": "account", "sign": "dr-cr"},
    {"label": "Heat", "type": "account", "sign": "dr-cr"},
    {"label": "Interest Expense", "type": "account", "sign": "dr-cr"},
    {"label": "Meals Expense", "type": "account", "sign": "dr-cr"},
    {"label": "Miscellaneous", "type": "account", "sign": "dr-cr"},
    {"label": "Office Furniture & Equipment", "type": "account", "sign": "dr-cr"},
    {"label": "Office Rental", "type": "account", "sign": "dr-cr"},
    {"label": "Office Repair & Maintenance", "type": "account", "sign": "dr-cr"},
    {"label": "Office Supplies", "type": "account", "sign": "dr-cr"},
    {"label": "Officer Salary", "type": "account", "sign": "dr-cr"},
    {"label": "Seller Consulting", "type": "account", "sign": "dr-cr"},
    {"label": "Payroll Expenses", "type": "account", "sign": "dr-cr"},
    {"label": "Payroll Expenses - Other", "type": "account", "sign": "dr-cr"},
    {"label": "Penalties", "type": "account", "sign": "dr-cr"},
    {"label": "Pension Expense", "type": "account", "sign": "dr-cr"},
    {"label": "Professional Services - Acctg &", "type": "account", "sign": "dr-cr"},
    {"label": "Professional Services - Legal", "type": "account", "sign": "dr-cr"},
    {"label": "Provision for Depreciation", "type": "account", "sign": "dr-cr"},
    {"label": "Shop Equipment", "type": "account", "sign": "dr-cr"},
    {"label": "Shop Repairs", "type": "account", "sign": "dr-cr"},
    {"label": "Shop Supplies", "type": "account", "sign": "dr-cr"},
    {"label": "Telephone/Internet Cable", "type": "account", "sign": "dr-cr"},
    {"label": "Travel & Entertainment", "type": "account", "sign": "dr-cr"},
    {"label": "Travel-Gas", "type": "account", "sign": "dr-cr"},
    {"label": "Utilities", "type": "account", "sign": "dr-cr"},
    {"label": "TOTAL OPERATING EXPENSES", "type": "total", "sum_range": (-33, -1)},
    {"label": "", "type": "blank"},
    {"label": "OPERATING INCOME", "type": "calc"},  # Gross Profit - OpEx
    {"label": "", "type": "blank"},
    {"label": "EBITDA", "type": "calc"},  # Operating Income + Depreciation
    {"label": "", "type": "blank"},
    {"label": "OTHER INCOME/EXPENSE", "type": "header"},
    {"label": "FTE Tax", "type": "account", "sign": "cr-dr"},
    {"label": "Gain(Loss) on Sale", "type": "account", "sign": "cr-dr"},
    {"label": "Interest Income", "type": "account", "sign": "cr-dr"},
    {"label": "Investment Income", "type": "account", "sign": "cr-dr"},
    {"label": "Other Income", "type": "account", "sign": "cr-dr"},
    {"label": "Realized Gain(Loss) on invest", "type": "account", "sign": "cr-dr"},
    {"label": "TOTAL OTHER INCOME/EXPENSE", "type": "total", "sum_range": (-6, -1)},
    {"label": "", "type": "blank"},
    {"label": "NET INCOME", "type": "calc"},  # Operating Income + OIE
]

# Cash Flow Statement structure (matching cash bridge rows 89-150)
CF_ROWS = [
    {"label": "CASH FLOW STATEMENT (INDIRECT METHOD)", "type": "header"},
    {"label": "", "type": "blank"},
    {"label": "NET INCOME", "type": "ref_is"},  # References IS Net Income
    {"label": "", "type": "blank"},
    {"label": "ADJUSTMENTS TO RECONCILE NET INCOME TO CASH  (+) = source of cash  (-) = use of cash", "type": "header"},
    {"label": "Provision for Depreciation", "type": "depr_addback"},  # = IS Depreciation line
    {"label": "Accumulated Depreciation", "type": "account", "sign": "cr-dr"},
    {"label": "Accounts Receivable", "type": "account", "sign": "cr-dr"},
    {"label": "Retainage", "type": "account", "sign": "cr-dr"},
    {"label": "Accounts Payable", "type": "account", "sign": "cr-dr"},
    {"label": "Accrued Federal Payroll Taxes", "type": "account", "sign": "cr-dr"},
    {"label": "Accrued 401(k)", "type": "account", "sign": "cr-dr"},
    {"label": "Accrued Payroll", "type": "account", "sign": "cr-dr"},
    {"label": "Accrued Single Business Taxes", "type": "account", "sign": "cr-dr"},
    {"label": "Cost Over Billings & Earnings", "type": "account", "sign": "cr-dr"},
    {"label": "CY Billings Over and Under", "type": "account", "sign": "cr-dr"},
    {"label": "Inventory - Materials", "type": "account", "sign": "cr-dr"},
    {"label": "Payroll Liabilities", "type": "account", "sign": "cr-dr"},
    {"label": "SIT Payable", "type": "account", "sign": "cr-dr"},
    {"label": "MESC Payable", "type": "account", "sign": "cr-dr"},
    {"label": "FUTA Payable MI", "type": "account", "sign": "cr-dr"},
    {"label": "Union Dues Payable", "type": "account", "sign": "cr-dr"},
    {"label": "IRC Section 7519 Deposit", "type": "account", "sign": "cr-dr"},
    {"label": "CASH FROM OPERATIONS", "type": "calc"},  # NI + sum(adjustments)
    {"label": "", "type": "blank"},
    {"label": "INVESTING ACTIVITIES  (+) = proceeds  (-) = purchase", "type": "header"},
    {"label": "Vehicles", "type": "account", "sign": "cr-dr"},
    {"label": "Investments", "type": "account", "sign": "cr-dr"},
    {"label": "Security deposit-West Bend", "type": "account", "sign": "cr-dr"},
    {"label": "CASH FROM INVESTING", "type": "total", "sum_range": (-3, -1)},
    {"label": "", "type": "blank"},
    {"label": "FINANCING ACTIVITIES  (+) = borrowing/contribution  (-) = repayment/distribution", "type": "header"},
    {"label": "Capital Contrib/Personal Draw", "type": "account", "sign": "cr-dr"},
    {"label": "Distributions", "type": "account", "sign": "cr-dr"},
    {"label": "Additonal Paid in Capital", "type": "account", "sign": "cr-dr"},
    {"label": "Kevin Masich Loan #2", "type": "account", "sign": "cr-dr"},
    {"label": "Loan from Kim Masich", "type": "account", "sign": "cr-dr"},
    {"label": "Loan to Wright St. Mgt", "type": "account", "sign": "cr-dr"},
    {"label": "Loan to Wright St. Mgt - Other", "type": "account", "sign": "cr-dr"},
    {"label": "LOC 00020031666-00015  was 14", "type": "account", "sign": "cr-dr"},
    {"label": "Ford Credit 2025 F250", "type": "account", "sign": "cr-dr"},
    {"label": "Ford Credit 2023   f-150", "type": "account", "sign": "cr-dr"},
    {"label": "First Bank-2019 Ford F350-WorkT", "type": "account", "sign": "cr-dr"},
    {"label": "First Bank 2020 F350", "type": "account", "sign": "cr-dr"},
    {"label": "2019 Ford F-150 Keith's New TK", "type": "account", "sign": "cr-dr"},
    {"label": "Retained Earnings", "type": "account", "sign": "cr-dr"},
    {"label": "Opening Bal Equity", "type": "account", "sign": "cr-dr"},
    {"label": "CASH FROM FINANCING", "type": "total", "sum_range": (-15, -1)},
    {"label": "", "type": "blank"},
    {"label": "NET CHANGE IN CASH", "type": "calc"},  # Operations + Investing + Financing
    {"label": "", "type": "blank"},
    {"label": "DEBT SERVICE", "type": "header"},
    {"label": "", "type": "blank"},
    {"label": "SBA 7a Principal", "type": "account", "sign": "cr-dr"},
    {"label": "SBA 7a Interest", "type": "account", "sign": "cr-dr"},
    {"label": "Seller Note Principal", "type": "account", "sign": "cr-dr"},
    {"label": "Seller Note Interest", "type": "account", "sign": "cr-dr"},
    {"label": "Seller Note 2 Principal", "type": "account", "sign": "cr-dr"},
    {"label": "Seller Note 2 Interest", "type": "account", "sign": "cr-dr"},
    {"label": "2025 Ford F250 Principal", "type": "account", "sign": "cr-dr"},
    {"label": "2025 Ford F250 Interest", "type": "account", "sign": "cr-dr"},
    {"label": "Total Debt Service", "type": "total", "sum_range": (-8, -1)},
    {"label": "", "type": "blank"},
    {"label": "DSCR (Pro Forma for pre-close FYs)", "type": "calc"},  # Cash from Ops / Total Debt Service
]


def find_row_by_label(rows, label, start_from=0):
    """Find the 0-indexed position of a row with the given label."""
    for i in range(start_from, len(rows)):
        if rows[i]["label"] == label:
            return i
    return None


def build_is_formulas(rows):
    """Build formula grid for Income Statement.
    Returns list of lists (row x col), 0-indexed.
    Each cell is either a string formula, a value, or None.
    """
    num_cols = COL_SENTINEL + 1  # Through sentinel
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
    
    # Row 1: Sub-headers / dates
    date_row = [None] * num_cols
    date_row[COL_LABELS] = "Account"
    date_row[COL_FY23] = "Oct 22 - Sep 23"
    date_row[COL_FY24] = "Oct 23 - Sep 24"
    date_row[COL_FY25] = "Oct 24 - Sep 25"
    date_row[COL_FY26_PRE] = "Oct 25 - Apr 26"
    date_row[COL_FY26_POST] = "May 26 - Dec 26"
    date_row[COL_FY27] = "Jan - Dec 27"
    date_row[COL_FY28] = "Jan - Dec 28"
    date_row[COL_FY29] = "Jan - Dec 29"
    # Monthly date formulas
    for col_idx, year, month in monthly_dates():
        date_row[col_idx] = f"=DATE({year},{month},1)"
    grid.append(date_row)
    
    # Track important row indices (0-indexed within data rows, offset by 2 for grid)
    total_revenue_idx = None
    total_cogs_idx = None
    gross_profit_idx = None
    total_opex_idx = None
    operating_income_idx = None
    ebitda_idx = None
    depreciation_idx = None
    total_oie_idx = None
    net_income_idx = None
    
    # Find key rows
    for i, row_def in enumerate(rows):
        if row_def["label"] == "TOTAL REVENUE":
            total_revenue_idx = i
        elif row_def["label"] == "TOTAL COGS":
            total_cogs_idx = i
        elif row_def["label"] == "GROSS PROFIT":
            gross_profit_idx = i
        elif row_def["label"] == "TOTAL OPERATING EXPENSES":
            total_opex_idx = i
        elif row_def["label"] == "OPERATING INCOME":
            operating_income_idx = i
        elif row_def["label"] == "EBITDA":
            ebitda_idx = i
        elif row_def["label"] == "Provision for Depreciation":
            depreciation_idx = i
        elif row_def["label"] == "TOTAL OTHER INCOME/EXPENSE":
            total_oie_idx = i
        elif row_def["label"] == "NET INCOME":
            net_income_idx = i
    
    # Build data rows
    for i, row_def in enumerate(rows):
        data_row = [None] * num_cols
        actual_row = i + 2  # 0-indexed grid row (header=0, subheader=1, data starts at 2)
        r = actual_row + 1  # 1-indexed for formulas
        
        data_row[COL_LABELS] = row_def["label"]
        
        if row_def["type"] == "header" or row_def["type"] == "blank":
            grid.append(data_row)
            continue
        
        if row_def["type"] == "account":
            sign = row_def["sign"]
            # Historical columns
            for col in [COL_FY23, COL_FY24, COL_FY25, COL_FY26_PRE]:
                data_row[col] = hist_sde_formula(actual_row, col, sign)
            
            # Pro forma monthly columns
            for start_col, end_col, total_col, mult in PROFORMA_PERIODS:
                for c in range(start_col, end_col + 1):
                    data_row[c] = proforma_monthly_formula(actual_row, c, mult)
                # Total column = SUM of monthly
                data_row[total_col] = sum_formula(actual_row, start_col, end_col)
            
            grid.append(data_row)
            continue
        
        if row_def["type"] == "total":
            sr = row_def["sum_range"]
            start_r = r + sr[0]
            end_r = r + sr[1]
            for col in range(1, num_cols):
                if col == COL_LABELS:
                    continue
                cl = col_letter(col)
                data_row[col] = f"=SUM({cl}{start_r}:{cl}{end_r})"
            grid.append(data_row)
            continue
        
        if row_def["type"] == "calc":
            label = row_def["label"]
            for col in range(1, num_cols):
                if col == COL_LABELS:
                    continue
                cl = col_letter(col)
                
                rev_r = total_revenue_idx + 2 + 1  # 1-indexed
                cogs_r = total_cogs_idx + 2 + 1
                gp_r = gross_profit_idx + 2 + 1
                opex_r = total_opex_idx + 2 + 1
                oi_r = operating_income_idx + 2 + 1
                depr_r = depreciation_idx + 2 + 1
                oie_r = total_oie_idx + 2 + 1
                
                if label == "GROSS PROFIT":
                    data_row[col] = f"={cl}{rev_r}-{cl}{cogs_r}"
                elif label == "OPERATING INCOME":
                    data_row[col] = f"={cl}{gp_r}-{cl}{opex_r}"
                elif label == "EBITDA":
                    data_row[col] = f"={cl}{oi_r}+{cl}{depr_r}"
                elif label == "NET INCOME":
                    data_row[col] = f"={cl}{oi_r}+{cl}{oie_r}"
            
            grid.append(data_row)
            continue
        
        # Fallback
        grid.append(data_row)
    
    return grid


def build_cf_formulas(cf_rows, is_sheet_name, is_rows):
    """Build formula grid for Cash Flow Statement."""
    num_cols = COL_SENTINEL + 1
    grid = []
    
    # Row 0: Headers (same as IS)
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
    
    # Row 1: dates
    date_row = [None] * num_cols
    date_row[COL_LABELS] = "Account"
    date_row[COL_FY23] = "Oct 22 - Sep 23"
    date_row[COL_FY24] = "Oct 23 - Sep 24"
    date_row[COL_FY25] = "Oct 24 - Sep 25"
    date_row[COL_FY26_PRE] = "Oct 25 - Apr 26"
    date_row[COL_FY26_POST] = "May 26 - Dec 26"
    date_row[COL_FY27] = "Jan - Dec 27"
    date_row[COL_FY28] = "Jan - Dec 28"
    date_row[COL_FY29] = "Jan - Dec 29"
    for col_idx, year, month in monthly_dates():
        date_row[col_idx] = f"=DATE({year},{month},1)"
    grid.append(date_row)
    
    # Find IS Net Income row (1-indexed in IS sheet)
    is_ni_row = None
    is_depr_row = None
    for i, rd in enumerate(is_rows):
        if rd["label"] == "NET INCOME":
            is_ni_row = i + 2 + 1  # grid offset + 1-indexed
        if rd["label"] == "Provision for Depreciation":
            is_depr_row = i + 2 + 1
    
    # Track CF key rows
    cf_ni_idx = None
    cash_from_ops_idx = None
    cash_from_inv_idx = None
    cash_from_fin_idx = None
    total_ds_idx = None
    adj_start_idx = None
    adj_end_idx = None
    
    for i, row_def in enumerate(cf_rows):
        if row_def["type"] == "ref_is":
            cf_ni_idx = i
        elif row_def["label"] == "CASH FROM OPERATIONS":
            cash_from_ops_idx = i
        elif row_def["label"] == "CASH FROM INVESTING":
            cash_from_inv_idx = i
        elif row_def["label"] == "CASH FROM FINANCING":
            cash_from_fin_idx = i
        elif row_def["label"] == "Total Debt Service":
            total_ds_idx = i
        elif row_def["label"] == "Provision for Depreciation" and row_def["type"] == "depr_addback":
            adj_start_idx = i  # first adjustment row
    
    # Find adjustment range (from depr_addback to row before CASH FROM OPERATIONS)
    adj_first = None
    adj_last = None
    for i, row_def in enumerate(cf_rows):
        if row_def["type"] in ("account", "depr_addback") and i > (cf_ni_idx or 0) and i < (cash_from_ops_idx or 999):
            if adj_first is None:
                adj_first = i
            adj_last = i
    
    for i, row_def in enumerate(cf_rows):
        data_row = [None] * num_cols
        actual_row = i + 2
        r = actual_row + 1
        
        data_row[COL_LABELS] = row_def["label"]
        
        if row_def["type"] in ("header", "blank"):
            grid.append(data_row)
            continue
        
        if row_def["type"] == "ref_is":
            # Reference IS Net Income
            for col in range(1, num_cols):
                if col == COL_LABELS:
                    continue
                cl = col_letter(col)
                data_row[col] = f"='{is_sheet_name}'!{cl}{is_ni_row}"
            grid.append(data_row)
            continue
        
        if row_def["type"] == "depr_addback":
            # Reference IS Provision for Depreciation (positive add-back)
            for col in range(1, num_cols):
                if col == COL_LABELS:
                    continue
                cl = col_letter(col)
                data_row[col] = f"='{is_sheet_name}'!{cl}{is_depr_row}"
            grid.append(data_row)
            continue
        
        if row_def["type"] == "account":
            sign = row_def["sign"]
            # Historical columns
            for col in [COL_FY23, COL_FY24, COL_FY25, COL_FY26_PRE]:
                data_row[col] = hist_sde_formula(actual_row, col, sign)
            # Pro forma monthly
            for start_col, end_col, total_col, mult in PROFORMA_PERIODS:
                for c in range(start_col, end_col + 1):
                    data_row[c] = proforma_monthly_formula(actual_row, c, mult)
                data_row[total_col] = sum_formula(actual_row, start_col, end_col)
            grid.append(data_row)
            continue
        
        if row_def["type"] == "total":
            sr = row_def["sum_range"]
            start_r = r + sr[0]
            end_r = r + sr[1]
            for col in range(1, num_cols):
                if col == COL_LABELS:
                    continue
                cl = col_letter(col)
                data_row[col] = f"=SUM({cl}{start_r}:{cl}{end_r})"
            grid.append(data_row)
            continue
        
        if row_def["type"] == "calc":
            label = row_def["label"]
            ni_r = cf_ni_idx + 2 + 1
            ops_adj_first_r = adj_first + 2 + 1
            ops_adj_last_r = adj_last + 2 + 1
            ops_r = cash_from_ops_idx + 2 + 1 if cash_from_ops_idx else 0
            inv_r = cash_from_inv_idx + 2 + 1 if cash_from_inv_idx else 0
            fin_r = cash_from_fin_idx + 2 + 1 if cash_from_fin_idx else 0
            ds_r = total_ds_idx + 2 + 1 if total_ds_idx else 0
            
            for col in range(1, num_cols):
                if col == COL_LABELS:
                    continue
                cl = col_letter(col)
                
                if label == "CASH FROM OPERATIONS":
                    data_row[col] = f"={cl}{ni_r}+SUM({cl}{ops_adj_first_r}:{cl}{ops_adj_last_r})"
                elif label == "NET CHANGE IN CASH":
                    data_row[col] = f"={cl}{ops_r}+{cl}{inv_r}+{cl}{fin_r}"
                elif label == "DSCR (Pro Forma for pre-close FYs)":
                    data_row[col] = f"=IF({cl}{ds_r}=0,\"\",{cl}{ops_r}/{cl}{ds_r})"
            
            grid.append(data_row)
            continue
        
        grid.append(data_row)
    
    return grid


def create_sheet(name, grid):
    """Create a new sheet and populate it with the grid."""
    # Step 1: Add the sheet
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
    print(f"  Sheet created with ID {new_sheet_id}")
    
    # Step 2: Write all values/formulas
    print(f"  Writing {len(grid)} rows of data...")
    
    # Convert grid to values format
    values = []
    for row in grid:
        row_vals = []
        for cell in row:
            if cell is None:
                row_vals.append("")
            else:
                row_vals.append(cell)
        values.append(row_vals)
    
    range_str = f"'{name}'!A1:{col_letter(COL_SENTINEL)}{len(grid)}"
    resp = requests.put(
        f"{BASE}/values/{range_str}?valueInputOption=USER_ENTERED",
        headers=HEADERS,
        json={"range": range_str, "values": values}
    )
    resp.raise_for_status()
    print(f"  Values written: {resp.json().get('updatedCells', 0)} cells")
    
    # Step 3: Format and hide columns
    print(f"  Applying formatting...")
    format_requests = []
    
    # Hide monthly detail columns (J through BB)
    format_requests.append({
        "updateDimensionProperties": {
            "range": {
                "sheetId": new_sheet_id,
                "dimension": "COLUMNS",
                "startIndex": COL_FY26PC_START,  # J
                "endIndex": COL_SENTINEL + 1     # Through BB
            },
            "properties": {"hiddenByUser": True},
            "fields": "hiddenByUser"
        }
    })
    
    # Bold header rows (row 0 and 1)
    format_requests.append({
        "repeatCell": {
            "range": {
                "sheetId": new_sheet_id,
                "startRowIndex": 0,
                "endRowIndex": 2,
                "startColumnIndex": 0,
                "endColumnIndex": COL_FY29 + 1
            },
            "cell": {"userEnteredFormat": {"textFormat": {"bold": True}}},
            "fields": "userEnteredFormat.textFormat.bold"
        }
    })
    
    # Bold section headers and totals in column A
    for i, row in enumerate(grid):
        if i < 2:
            continue
        label = row[COL_LABELS] if row[COL_LABELS] else ""
        if label.isupper() or label.startswith("TOTAL") or label.startswith("DSCR"):
            format_requests.append({
                "repeatCell": {
                    "range": {
                        "sheetId": new_sheet_id,
                        "startRowIndex": i,
                        "endRowIndex": i + 1,
                        "startColumnIndex": 0,
                        "endColumnIndex": COL_FY29 + 1
                    },
                    "cell": {"userEnteredFormat": {"textFormat": {"bold": True}}},
                    "fields": "userEnteredFormat.textFormat.bold"
                }
            })
    
    # Number format for data cells (accounting format)
    format_requests.append({
        "repeatCell": {
            "range": {
                "sheetId": new_sheet_id,
                "startRowIndex": 2,
                "endRowIndex": len(grid),
                "startColumnIndex": 1,
                "endColumnIndex": COL_SENTINEL + 1
            },
            "cell": {"userEnteredFormat": {"numberFormat": {"type": "NUMBER", "pattern": "#,##0"}}},
            "fields": "userEnteredFormat.numberFormat"
        }
    })
    
    # Freeze first column and first 2 rows
    format_requests.append({
        "updateSheetProperties": {
            "properties": {
                "sheetId": new_sheet_id,
                "gridProperties": {
                    "frozenRowCount": 2,
                    "frozenColumnCount": 1
                }
            },
            "fields": "gridProperties.frozenRowCount,gridProperties.frozenColumnCount"
        }
    })
    
    # Set column A width
    format_requests.append({
        "updateDimensionProperties": {
            "range": {
                "sheetId": new_sheet_id,
                "dimension": "COLUMNS",
                "startIndex": 0,
                "endIndex": 1
            },
            "properties": {"pixelSize": 280},
            "fields": "pixelSize"
        }
    })
    
    resp = requests.post(f"{BASE}:batchUpdate", headers=HEADERS, json={"requests": format_requests})
    resp.raise_for_status()
    print(f"  Formatting applied.")
    
    return new_sheet_id


def main():
    if len(sys.argv) > 1 and sys.argv[1] == "--cf-only":
        # Just build CF
        print("Building Cash Flow Statement...")
        cf_grid = build_cf_formulas(CF_ROWS, "Income Statement", IS_ROWS)
        create_sheet("Cash Flow Statement", cf_grid)
        print("\nDone!")
        return
    
    # Build Income Statement
    print("Building Income Statement...")
    is_grid = build_is_formulas(IS_ROWS)
    create_sheet("Income Statement", is_grid)
    
    # Build Cash Flow Statement
    print("\nBuilding Cash Flow Statement...")
    cf_grid = build_cf_formulas(CF_ROWS, "Income Statement", IS_ROWS)
    create_sheet("Cash Flow Statement", cf_grid)
    
    print("\nAll sheets created successfully!")
    print("Note: Balance Sheet will be built separately as it requires different logic.")


if __name__ == "__main__":
    main()
