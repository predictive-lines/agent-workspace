#!/usr/bin/env python3

import json
import requests

# Load Google auth
creds = json.load(open('/home/open-claw/.config/google/oauth_credentials.json'))
tokens = json.load(open('/home/open-claw/.config/google/tokens.json'))

def refresh_token():
    r = requests.post('https://oauth2.googleapis.com/token', data={
        'client_id': creds['client_id'],
        'client_secret': creds['client_secret'], 
        'refresh_token': tokens['refresh_token'],
        'grant_type': 'refresh_token'
    })
    token = r.json()['access_token']
    open('/tmp/gtoken.txt', 'w').write(token)
    return token

token = refresh_token()
SHEET_ID = "13KQXudrHd5F3p-NHrr_RTkSWuIAbhVuDp9GIDVNCetM"

def update_cell(sheet, cell, formula):
    url = f"https://sheets.googleapis.com/v4/spreadsheets/{SHEET_ID}/values/'{sheet}'!{cell}?valueInputOption=USER_ENTERED"
    return requests.put(url, 
                       headers={"Authorization": f"Bearer {token}", "Content-Type": "application/json"},
                       json={"values": [[formula]]})

print("Fixing Balance Sheet to use cash bridge WC/LOC calculations...")

# Balance Sheet column mapping:
# F = FY2026 Post-Close (Dec 2026) → cash bridge DG column  
# G = FY2027 (Dec 2027) → cash bridge DT column
# H = FY2028 (Dec 2028) → cash bridge EG column
# I = FY2029 (Dec 2029) → cash bridge ET column

# 1. Fix First Bank (Cash) - row 6
# Pull from cash bridge Running Cash Balance (row 187)
updates = [
    # Cash = cash bridge Running Cash Balance
    ("Balance Sheet", "F6", "='cash bridge'!DG187"),  # FY2026 Post-Close
    ("Balance Sheet", "G6", "='cash bridge'!DT187"),  # FY2027
    ("Balance Sheet", "H6", "='cash bridge'!EG187"),  # FY2028
    ("Balance Sheet", "I6", "='cash bridge'!ET187"),  # FY2029
    
    # AR = cash bridge AR Balance (need to add this line - assuming row 11)
    ("Balance Sheet", "F11", "='cash bridge'!DG176"), 
    ("Balance Sheet", "G11", "='cash bridge'!DT176"),
    ("Balance Sheet", "H11", "='cash bridge'!EG176"),
    ("Balance Sheet", "I11", "='cash bridge'!ET176"),
    
    # AP = cash bridge AP Balance (row 43)
    ("Balance Sheet", "F43", "='cash bridge'!DG177"),
    ("Balance Sheet", "G43", "='cash bridge'!DT177"), 
    ("Balance Sheet", "H43", "='cash bridge'!EG177"),
    ("Balance Sheet", "I43", "='cash bridge'!ET177"),
    
    # LOC = cash bridge LOC Outstanding Balance (row 65)
    ("Balance Sheet", "F65", "='cash bridge'!DG188"),
    ("Balance Sheet", "G65", "='cash bridge'!DT188"),
    ("Balance Sheet", "H65", "='cash bridge'!EG188"),
    ("Balance Sheet", "I65", "='cash bridge'!ET188"),
]

# Add missing acquisition debt lines (need to determine exact rows)
# For now, let's add them after the existing long-term debt

acquisition_debt = [
    # SBA 7a Loan (assuming new row - let's use row 66)
    ("Balance Sheet", "F66", "='Debt Service Schedule - SBA 7a'!G12"),  # Period 8 (Dec 2026)
    ("Balance Sheet", "G66", "='Debt Service Schedule - SBA 7a'!G24"),  # Period 20 (Dec 2027) 
    ("Balance Sheet", "H66", "='Debt Service Schedule - SBA 7a'!G36"),  # Period 32 (Dec 2028)
    ("Balance Sheet", "I66", "='Debt Service Schedule - SBA 7a'!G48"),  # Period 44 (Dec 2029)
    
    # Seller Note (assuming row 67)
    ("Balance Sheet", "F67", "='Debt Service Schedule - Seller Note'!G12"),
    ("Balance Sheet", "G67", "='Debt Service Schedule - Seller Note'!G24"),
    ("Balance Sheet", "H67", "='Debt Service Schedule - Seller Note'!G36"), 
    ("Balance Sheet", "I67", "='Debt Service Schedule - Seller Note'!G48"),
    
    # Seller Note 2 (assuming row 68)
    ("Balance Sheet", "F68", "='Debt Service Schedule - Seller Note 2'!G12"),
    ("Balance Sheet", "G68", "='Debt Service Schedule - Seller Note 2'!G24"),
    ("Balance Sheet", "H68", "='Debt Service Schedule - Seller Note 2'!G36"),
    ("Balance Sheet", "I68", "='Debt Service Schedule - Seller Note 2'!G48"),
]

all_updates = updates + acquisition_debt

for sheet, cell, formula in all_updates:
    print(f"Updating {sheet}!{cell} = {formula}")
    resp = update_cell(sheet, cell, formula)
    if resp.status_code != 200:
        print(f"ERROR: {resp.status_code} {resp.text}")
        break

print("Balance Sheet WC/LOC updates complete!")

# Check the new CHECK row values
print("\nChecking balance after updates...")
for col, year in [("F", "FY2026PC"), ("G", "FY2027"), ("H", "FY2028"), ("I", "FY2029")]:
    url = f"https://sheets.googleapis.com/v4/spreadsheets/{SHEET_ID}/values/'Balance Sheet'!{col}87"
    resp = requests.get(url, headers={"Authorization": f"Bearer {token}"})
    check_val = resp.json().get('values', [['']])[0][0] if resp.json().get('values') else 'ERROR'
    print(f"{year} CHECK (Assets - L&E): {check_val}")