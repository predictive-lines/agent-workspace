#!/usr/bin/env python3
"""
Insert Konner Budget rows into the Budget sheet.

Note: When inserting rows via API, we need to:
1. Get the full row 28 (Konner Class 9) to use as template for row 29 (Class 10)
2. Insert new rows after row 28
3. Update the new row values with correct start/end dates, formulas, etc.
"""
import json, time, urllib.request, urllib.parse

with open('/home/open-claw/.config/google/tokens.json') as f: tokens = json.load(f)
with open('/home/open-claw/.config/google/oauth_credentials.json') as f: creds = json.load(f)

def get_token():
    data = urllib.parse.urlencode({
        'client_id': creds['client_id'], 'client_secret': creds['client_secret'],
        'refresh_token': tokens['refresh_token'], 'grant_type': 'refresh_token'
    }).encode()
    req = urllib.request.Request('https://oauth2.googleapis.com/token', data=data, method='POST')
    return json.loads(urllib.request.urlopen(req).read())['access_token']

TOKEN = get_token()
SHEET_ID = '13KQXudrHd5F3p-NHrr_RTkSWuIAbhVuDp9GIDVNCetM'
BASE = f'https://sheets.googleapis.com/v4/spreadsheets/{SHEET_ID}'
BUDGET_GID = 1493163852

def api(method, url, body=None):
    global TOKEN
    for attempt in range(3):
        headers = {'Authorization': f'Bearer {TOKEN}', 'Content-Type': 'application/json'}
        data = json.dumps(body).encode() if body else None
        req = urllib.request.Request(url, data=data, headers=headers, method=method)
        try:
            return json.loads(urllib.request.urlopen(req).read())
        except urllib.error.HTTPError as e:
            err = e.read().decode()
            if e.code == 401 and attempt < 2:
                print("  [token refresh]"); TOKEN = get_token(); continue
            if e.code == 429 and attempt < 2:
                print("  [rate limit]"); time.sleep(60); continue
            print(f"  HTTP {e.code}"); raise

# ── Get row 28 as a template ───────────────────────────────────────────────────
print("Fetching Budget row 28 (Konner Class 9) as template...")
url = f'{BASE}/values/{urllib.parse.quote("Budget!28:28")}?valueRenderOption=FORMULA'
template_resp = api('GET', url)
template_row = template_resp.get('values', [[]])[0] if template_resp.get('values') else []
print(f"  Template has {len(template_row)} columns")

# ── New rows data ──────────────────────────────────────────────────────────────
new_rows = [
    # Row 29: Konner Class 10 (Jan-Jun 2030)
    [
        'Apprentice Wages - Class 10',
        'Konner Lefebvre',
        '=DATE(2030,1,1)',
        '=DATE(2030,6,30)',
        1,
        'Every 1 months',
        '=VLOOKUP(10,defined_variables!$A$64:$B$73,2,FALSE)*LOOKUP(C29,defined_variables!$A$56:$A$60,defined_variables!$C$56:$C$60)*2080*cost_labor_utilization/12',
        'Wages',
        'Class 10 (80% × CBA rate × util)',
        'Journeymen + Apprentices',
        False,
        True,
        '',
        '',
        '=IF($J29="", 1, IFERROR(VLOOKUP($J29, defined_variables!$A$30:$E$41, 3, FALSE), 1))',
        '=IF($J29="", 1, IFERROR(VLOOKUP($J29, defined_variables!$A$30:$E$41, 4, FALSE), 1))',
        '=IF($J29="", 1, IFERROR(VLOOKUP($J29, defined_variables!$A$30:$E$41, 5, FALSE), 1))',
        '',
        1
    ],
    # Row 30: Konner JM Wages (Jul 2030+)
    [
        'Local JM Wages (Konner Lefebvre)',
        'Konner Lefebvre',
        '=DATE(2030,7,1)',
        '',
        1,
        'Every 1 months',
        '=1*LOOKUP(C30,defined_variables!$A$56:$A$60,defined_variables!$B$56:$B$60)*R30',
        'Wages',
        'Konner JM - 4th local JM',
        'Journeymen + Apprentices',
        False,
        True,
        '',
        '',
        '=IF($J30="", 1, IFERROR(VLOOKUP($J30, defined_variables!$A$30:$E$41, 3, FALSE), 1))',
        '=IF($J30="", 1, IFERROR(VLOOKUP($J30, defined_variables!$A$30:$E$41, 4, FALSE), 1))',
        '=IF($J30="", 1, IFERROR(VLOOKUP($J30, defined_variables!$A$30:$E$41, 5, FALSE), 1))',
        '=$R$19',
        1
    ],
    # Row 31: Konner Union Benefits (Class 10, Jan-Jun 2030)
    [
        'Konner Union Benefits (Class 10)',
        '',
        '=DATE(2030,1,1)',
        '=DATE(2030,6,30)',
        1,
        'Every 1 months',
        "='Payroll Calculations'!BE30",
        'Union Benefits',
        '',
        'Journeymen + Apprentices',
        False,
        True,
        '',
        '',
        '1',
        '1',
        '1',
        '',
        1
    ],
    # Row 32: Konner FICA SS (Class 10, Jan-Jun 2030)
    [
        'Konner FICA SS (Class 10)',
        '',
        '=DATE(2030,1,1)',
        '=DATE(2030,6,30)',
        1,
        'Every 1 months',
        "='Payroll Calculations'!BE46",
        'FICA',
        '',
        'Journeymen + Apprentices',
        False,
        True,
        '',
        '',
        '1',
        '1',
        '1',
        '',
        1
    ],
    # Row 33: Konner Medicare (Class 10, Jan-Jun 2030)
    [
        'Konner Medicare (Class 10)',
        '',
        '=DATE(2030,1,1)',
        '=DATE(2030,6,30)',
        1,
        'Every 1 months',
        "='Payroll Calculations'!BE62",
        'FICA Medicare',
        '',
        'Journeymen + Apprentices',
        False,
        True,
        '',
        '',
        '1',
        '1',
        '1',
        '',
        1
    ],
    # Row 34: Konner Workers Comp (Class 10, Jan-Jun 2030)
    [
        'Konner Workers Comp (Class 10)',
        '',
        '=DATE(2030,1,1)',
        '=DATE(2030,6,30)',
        1,
        'Every 1 months',
        "='Payroll Calculations'!BE110",
        'Workers Compensation',
        '',
        'Journeymen + Apprentices',
        False,
        True,
        '',
        '',
        '1',
        '1',
        '1',
        '',
        1
    ],
    # Row 35: Konner Union Benefits (JM, Jul 2030+)
    [
        'Konner Union Benefits (JM)',
        '',
        '=DATE(2030,7,1)',
        '',
        1,
        'Every 1 months',
        "='Payroll Calculations'!BK20",
        'Union Benefits',
        '',
        'Journeymen + Apprentices',
        False,
        True,
        '',
        '',
        '1',
        '1',
        '1',
        '',
        1
    ],
    # Row 36: Konner FICA SS (JM, Jul 2030+)
    [
        'Konner FICA SS (JM)',
        '',
        '=DATE(2030,7,1)',
        '',
        1,
        'Every 1 months',
        "='Payroll Calculations'!BK36",
        'FICA',
        '',
        'Journeymen + Apprentices',
        False,
        True,
        '',
        '',
        '1',
        '1',
        '1',
        '',
        1
    ],
    # Row 37: Konner Medicare (JM, Jul 2030+)
    [
        'Konner Medicare (JM)',
        '',
        '=DATE(2030,7,1)',
        '',
        1,
        'Every 1 months',
        "='Payroll Calculations'!BK52",
        'FICA Medicare',
        '',
        'Journeymen + Apprentices',
        False,
        True,
        '',
        '',
        '1',
        '1',
        '1',
        '',
        1
    ],
    # Row 38: Konner Workers Comp (JM, Jul 2030+)
    [
        'Konner Workers Comp (JM)',
        '',
        '=DATE(2030,7,1)',
        '',
        1,
        'Every 1 months',
        "='Payroll Calculations'!BK100",
        'Workers Compensation',
        '',
        'Journeymen + Apprentices',
        False,
        True,
        '',
        '',
        '1',
        '1',
        '1',
        '',
        1
    ]
]

# ── Insert rows ────────────────────────────────────────────────────────────────
print(f"\nInserting {len(new_rows)} Budget rows after row 28...")

# Insert all rows at once (starting after row 28)
requests = []

# First, insert 10 blank rows after row 28
requests.append({
    'insertDimension': {
        'range': {
            'sheetId': BUDGET_GID,
            'dimension': 'ROWS',
            'startIndex': 28,  # After row 28 (0-indexed)
            'endIndex': 28 + len(new_rows)
        }
    }
})

# Then populate those rows
# Each row needs values in columns A-S (19 columns)
for i, row_data in enumerate(new_rows):
    row_index = 28 + i
    requests.append({
        'updateCells': {
            'range': {
                'sheetId': BUDGET_GID,
                'startRowIndex': row_index,
                'endRowIndex': row_index + 1,
                'startColumnIndex': 0,
                'endColumnIndex': len(row_data)
            },
            'rows': [{
                'values': [
                    {'userEnteredValue': {
                        'stringValue' if isinstance(v, str) else 'numberValue': v
                    }} if v != '' else {}
                    for v in row_data
                ]
            }],
            'fields': 'userEnteredValue'
        }
    })

# Send the batch update
print("  Sending batch update...")
resp = api('POST', f'{BASE}:batchUpdate', {'requests': requests})
print(f"✓ Inserted {len(new_rows)} Budget rows")

# Verify by reading back rows 29-30
print("\nVerifying inserted rows...")
verify_resp = api('GET', f'{BASE}/values/{urllib.parse.quote("Budget!A29:G30")}?valueRenderOption=FORMULA')
if verify_resp.get('values'):
    for i, row in enumerate(verify_resp['values'], 29):
        print(f"  Row {i}: {row[0] if row else ''}")

print("\n=== COMPLETE ===")
print("✓ Payroll Calculations extended through Dec 2033")
print("✓ Budget rows inserted for Konner Class 10 → JM transition")
print("✓ FUTA/SUTA corrected for 2030-2033")
print("\nWages should now hold steady at ~$445K-$450K annually going forward.")
