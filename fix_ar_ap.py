#!/usr/bin/env python3
"""Fix BS AR/AP to use last-N-months-of-revenue/COGS approach matching cash bridge logic."""
import json

B = "Budget!"
IF_A = "'Deal Terms'!$B$24=\"Asset\""
ERR = '"ERROR: Stock sale not modeled"'

# Revenue accounts for AR
REV_ACCTS = ["Contracts", "Service", "Inspections"]
rev_filter = "+".join(f'({B}$H$2:{B}$H$534="{a}")' for a in REV_ACCTS) + ">0"

# COGS accounts for AP (all accounts that appear in IS rows 10-33 AND in Budget)
COGS_ACCTS = [
    "Bond Costs", "Design - Direct", "Direct Materials", "Equipment Repair & Rental",
    "FICA Expense", "FICA Medical Expense", "FUTA Expense",
    "Ins - Work Comp", "Insurance - Auto", "Insurance - Package Policy", "Insurance - Work Comp.",
    "License & Permits", "Small Tools & Equipment", "Subcontractors", "Subsistence",
    "SUTA Expense", "Truck & Auto Expense", "Union Benefits", "Wages"
]
cogs_filter = "+".join(f'({B}$H$2:{B}$H$534="{a}")' for a in COGS_ACCTS) + ">0"

# Multiplier strings per column
MULTS = {
    'F': f'*{B}$S$2:{B}$S$534',
    'G': f'*{B}$O$2:{B}$O$534*{B}$S$2:{B}$S$534',
    'H': f'*{B}$P$2:{B}$P$534*{B}$S$2:{B}$S$534',
    'I': f'*{B}$Q$2:{B}$Q$534*{B}$S$2:{B}$S$534',
}

NCOLS = {'F': 'G', 'G': 'H', 'H': 'I', 'I': 'J'}

def month_match(target_month_expr):
    """Generate SUMPRODUCT conditions for a Budget entry firing in a specific month."""
    return (
        f'({B}$C$2:{B}$C$534<EDATE({target_month_expr},1))'  # start < next month
        f'*(IF({B}$D$2:{B}$D$534="",1,{B}$D$2:{B}$D$534>={target_month_expr}))'  # end >= month (if set)
        f'*(IF({B}$E$2:{B}$E$534<=0,'
        f'(YEAR({B}$C$2:{B}$C$534)=YEAR({target_month_expr}))*(MONTH({B}$C$2:{B}$C$534)=MONTH({target_month_expr})),'
        f'MOD(MONTH({target_month_expr})-MONTH({B}$C$2:{B}$C$534)+12,{B}$E$2:{B}$E$534)=0))'
    )

updates = []

for col, ncol in NCOLS.items():
    mult = MULTS[col]
    
    # AR: sum of last ROUND(ar_days/30) months of revenue
    target = f'EDATE({ncol}$2,-n)'
    mm = month_match(target)
    ar_inner = (f'SUM(MAP(SEQUENCE(ROUND(ar_days/30,0),1,1),LAMBDA(n,'
                f'SUMPRODUCT(({rev_filter})*{mm}*{B}$G$2:{B}$G$534{mult}))))')
    ar_formula = f'=IF({IF_A},{ar_inner},{ERR})'
    updates.append({'range': f"'Balance Sheet'!{col}11", 'values': [[ar_formula]]})
    
    # AP: sum of last ROUND(ap_days/30) months of COGS
    ap_inner = (f'SUM(MAP(SEQUENCE(ROUND(ap_days/30,0),1,1),LAMBDA(n,'
                f'SUMPRODUCT(({cogs_filter})*{mm}*{B}$G$2:{B}$G$534{mult}))))')
    ap_formula = f'=IF({IF_A},{ap_inner},{ERR})'
    updates.append({'range': f"'Balance Sheet'!{col}43", 'values': [[ap_formula]]})

payload = {'valueInputOption': 'USER_ENTERED', 'data': updates}
with open('/tmp/ar_ap_fix.json', 'w') as f:
    json.dump(payload, f)
print(f'{len(updates)} updates written')
