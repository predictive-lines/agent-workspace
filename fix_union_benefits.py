#!/usr/bin/env python3
"""
Fix union benefits + FICA/WC aggregate rows for Konner's JM transition.

Changes:
1. End Budget rows 89-92 (union benefits/FICA/WC aggregates) at 12/31/2029
2. Append new aggregate rows from 1/1/2030 covering 3 local JMs only (Konner separate)
3. Fill Budget rows 31-38 with Konner's individual Class 10 / JM benefit rows

Column layout in Payroll Calculations:
  BE = Jan 2030  (Class 10 period rates)
  BK = Jul 2030  (JM period rates)

Payroll Calc rows used:
  20=JM union   30=Class10 union   (both = $3976.27, same amount)
  36=JM FICA SS  46=Class10 FICA SS
  52=JM Medicare 62=Class10 Medicare
  100=JM WC      110=Class10 WC
  47=Admin FICA  48=Officer FICA    63=Admin Medicare  64=Officer Medicare
  111=Admin WC   112=Officer WC
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
BASE     = f'https://sheets.googleapis.com/v4/spreadsheets/{SHEET_ID}'

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
            if e.code == 401 and attempt < 2: TOKEN = get_token(); continue
            if e.code == 429 and attempt < 2: time.sleep(60); continue
            print(f"  HTTP {e.code}: {err[:300]}"); raise

def get(r, render='FORMULA'):
    url = f'{BASE}/values/{urllib.parse.quote(r)}?valueRenderOption={render}'
    req = urllib.request.Request(url, headers={'Authorization': f'Bearer {TOKEN}'})
    return json.loads(urllib.request.urlopen(req).read()).get('values', [])

# ── Step 1: verify rows 29-30 look correct, spot row 89-92 current state ─────
print("=== Current state: rows 29-30 (Konner wages) ===")
rows = get("'Budget'!A29:H30")
for i, r in enumerate(rows, 29):
    print(f"  Row {i}: {r[0] if r else ''} | G={r[6] if len(r)>6 else ''}")

print("\n=== Current state: rows 89-92 (aggregate benefits) ===")
rows = get("'Budget'!A89:H92")
for i, r in enumerate(rows, 89):
    print(f"  Row {i}: {r[0] if r else ''}")
    if len(r) > 3: print(f"    end={r[3]}")
    if len(r) > 6: print(f"    G={r[6]}")

# ── Step 2: Fix rows 29-30 formulas first ─────────────────────────────────────
# Row 29 used VLOOKUP(9,...) — should be 10. Fix G29 and also fix R29 col if needed.
# Row 30 used C20 and R20 — should be C30 and $R$19.

print("\n─── Fixing rows 29 and 30 formula issues ───")
fixes = [
    {
        'range': "'Budget'!G29",
        'values': [['=VLOOKUP(10,defined_variables!$A$64:$B$73,2,FALSE)*LOOKUP(C29,defined_variables!$A$56:$A$60,defined_variables!$C$56:$C$60)*2080*cost_labor_utilization/12']]
    },
    {
        'range': "'Budget'!G30",
        'values': [['=1*LOOKUP(C30,defined_variables!$A$56:$A$60,defined_variables!$B$56:$B$60)*$R$19']]
    },
]
resp = api('POST', f'{BASE}/values:batchUpdate', {
    'valueInputOption': 'USER_ENTERED',
    'data': fixes
})
print(f"  Fixed {resp.get('totalUpdatedCells',0)} cells in rows 29-30")
time.sleep(1)

# ── Step 3: End aggregate rows 89-92 at 12/31/2029 ────────────────────────────
print("\n─── Ending aggregate benefit rows 89-92 at 12/31/2029 ───")
resp = api('POST', f'{BASE}/values:batchUpdate', {
    'valueInputOption': 'USER_ENTERED',
    'data': [
        {'range': "'Budget'!D89", 'values': [['=DATE(2029,12,31)']]},
        {'range': "'Budget'!D90", 'values': [['=DATE(2029,12,31)']]},
        {'range': "'Budget'!D91", 'values': [['=DATE(2029,12,31)']]},
        {'range': "'Budget'!D92", 'values': [['=DATE(2029,12,31)']]},
    ]
})
print(f"  Set end dates: {resp.get('totalUpdatedCells',0)} cells")
time.sleep(1)

# ── Step 4: Fill rows 31-38 with Konner individual benefit rows ──────────────
# Structure: A, B, C, D, E, F, G, H, I(notes), J(group), K(False), L(True=toggle),
#            M, N(blank), O,P,Q(multiplier=1), R(hrs/blank), S(1)

def benefit_row(desc, start_formula, end_formula, g_formula, acct):
    return [
        desc, '',
        start_formula, end_formula,
        1, 'Every 1 months',
        g_formula,
        acct,
        '', 'Journeymen + Apprentices',
        'FALSE', 'TRUE',
        '', '',
        '1', '1', '1',
        '', '1'
    ]

konner_rows = [
    # Row 31-34: Class 10  (Jan-Jun 2030)
    benefit_row('Konner Union Benefits (Class 10)', '=DATE(2030,1,1)', '=DATE(2030,6,30)',
                "='Payroll Calculations'!BE30", 'Union Benefits'),
    benefit_row('Konner FICA SS (Class 10)',        '=DATE(2030,1,1)', '=DATE(2030,6,30)',
                "='Payroll Calculations'!BE46", 'FICA Expense'),
    benefit_row('Konner Medicare (Class 10)',        '=DATE(2030,1,1)', '=DATE(2030,6,30)',
                "='Payroll Calculations'!BE62", 'FICA Medical Expense'),
    benefit_row('Konner Workers Comp (Class 10)',    '=DATE(2030,1,1)', '=DATE(2030,6,30)',
                "='Payroll Calculations'!BE110", 'Insurance - Work Comp.'),
    # Row 35-38: JM  (Jul 2030+)
    benefit_row('Konner Union Benefits (JM)',        '=DATE(2030,7,1)', '',
                "='Payroll Calculations'!BK20", 'Union Benefits'),
    benefit_row('Konner FICA SS (JM)',               '=DATE(2030,7,1)', '',
                "='Payroll Calculations'!BK36", 'FICA Expense'),
    benefit_row('Konner Medicare (JM)',              '=DATE(2030,7,1)', '',
                "='Payroll Calculations'!BK52", 'FICA Medical Expense'),
    benefit_row('Konner Workers Comp (JM)',          '=DATE(2030,7,1)', '',
                "='Payroll Calculations'!BK100", 'Insurance - Work Comp.'),
]

print("\n─── Writing Konner benefit rows 31-38 ───")
value_ranges = []
for i, row_data in enumerate(konner_rows):
    row_num = 31 + i
    value_ranges.append({
        'range': f"'Budget'!A{row_num}:S{row_num}",
        'values': [row_data]
    })

resp = api('POST', f'{BASE}/values:batchUpdate', {
    'valueInputOption': 'USER_ENTERED',
    'data': value_ranges
})
print(f"  Wrote {resp.get('totalUpdatedCells',0)} cells across rows 31-38")
time.sleep(1)

# ── Step 5: Append 2030+ aggregate rows (3 local JMs only, no Konner) ─────────
# Find last row in Budget first
all_a = get("'Budget'!A:A", render='FORMATTED_VALUE')
last_row = len(all_a)
print(f"\n─── Budget last row: {last_row}. Appending 2030+ aggregate rows ───")

def agg_row(desc, start_f, g_formula, acct):
    return [desc, '', start_f, '', 1, 'Every 1 months',
            g_formula, acct,
            '', 'Journeymen + Apprentices',
            'FALSE', 'TRUE',
            '', '', '1', '1', '1', '', '1']

new_agg_rows = [
    agg_row('Union Benefits (3 JMs, 2030+)',   '=DATE(2030,1,1)',
            "='Payroll Calculations'!BK20*3",  'Union Benefits'),
    agg_row('FICA Employer SS (3 JMs, 2030+)', '=DATE(2030,1,1)',
            "='Payroll Calculations'!BK36*3+'Payroll Calculations'!BK47+'Payroll Calculations'!BK48",
            'FICA Expense'),
    agg_row('FICA Medicare (3 JMs, 2030+)',    '=DATE(2030,1,1)',
            "='Payroll Calculations'!BK52*3+'Payroll Calculations'!BK63+'Payroll Calculations'!BK64",
            'FICA Medical Expense'),
    agg_row('Workers Comp (3 JMs, 2030+)',     '=DATE(2030,1,1)',
            "='Payroll Calculations'!BK100*3+'Payroll Calculations'!BK111+'Payroll Calculations'!BK112",
            'Insurance - Work Comp.'),
]

agg_ranges = []
for i, row_data in enumerate(new_agg_rows):
    row_num = last_row + 1 + i
    agg_ranges.append({
        'range': f"'Budget'!A{row_num}:S{row_num}",
        'values': [row_data]
    })

resp = api('POST', f'{BASE}/values:batchUpdate', {
    'valueInputOption': 'USER_ENTERED',
    'data': agg_ranges
})
print(f"  Appended {resp.get('totalUpdatedCells',0)} cells for 2030+ aggregates")
time.sleep(2)

# ── Step 6: Verify IS union benefits now correctly reflects 4 people ──────────
print("\n─── Verification: IS Union Benefits row 33, FY2027-2033 ───")
vals = get("'Income Statement'!G33:M33", render='FORMATTED_VALUE')
headers = get("'Income Statement'!G1:M1", render='FORMATTED_VALUE')
if vals and headers:
    for h, v in zip(headers[0], vals[0]):
        print(f"  {h}: {v}")

print("\n─── Verification: IS Wages row 30, FY2027-2033 ───")
vals = get("'Income Statement'!G30:M30", render='FORMATTED_VALUE')
if vals:
    for h, v in zip(headers[0], vals[0]):
        print(f"  {h}: {v}")
