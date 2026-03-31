#!/usr/bin/env python3
"""
Extend Excel Fire cash bridge from FY2029 → FY2033.

Layout:
  EU = FY2030 annual total  |  EV-FG = Jan-Dec 2030 monthly
  FH = FY2031 annual total  |  FI-FT = Jan-Dec 2031 monthly
  FU = FY2032 annual total  |  FV-GG = Jan-Dec 2032 monthly
  GH = FY2033 annual total  |  GI-GT = Jan-Dec 2033 monthly
  GU = DATE(2034,1,1) terminator
"""
import json, re, time, urllib.request, urllib.parse, sys

def col_num(s):
    n = 0
    for c in s.upper(): n = n * 26 + (ord(c) - 64)
    return n

def col_letter(n):
    s = ""
    while n > 0:
        n, r = divmod(n - 1, 26)
        s = chr(65 + r) + s
    return s

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
CB_GID   = 685035795
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
            if e.code == 401 and attempt < 2:
                print("  [token refresh]"); TOKEN = get_token(); continue
            if e.code == 429 and attempt < 2:
                print("  [rate limit – sleeping 30s]"); time.sleep(30); continue
            print(f"  HTTP {e.code}: {err[:500]}"); raise

def get_col(col_str, max_row=191):
    url = (f'{BASE}?ranges={urllib.parse.quote(f"cash bridge!{col_str}1:{col_str}{max_row}")}'
           f'&fields=sheets.data.rowData.values.userEnteredValue')
    resp = api('GET', url)
    result = {}
    for s in resp.get('sheets', []):
        for d in s.get('data', []):
            for r_idx, row in enumerate(d.get('rowData', []), 1):
                for cell in row.get('values', []):
                    v = cell.get('userEnteredValue', {})
                    val = v.get('formulaValue', v.get('stringValue', v.get('numberValue', None)))
                    if val is not None and str(val).strip() != '':
                        result[r_idx] = val
    return result

print("Loading EI (monthly) template...")
ei = get_col('EI')
print(f"  {len(ei)} rows with content")

print("Loading EH (annual) template...")
eh = get_col('EH')
print(f"  {len(eh)} rows with content")

# FY layout
FY_CONFIG = [
    {'fy':'FY2030','year':2030,'annual':'EU','first':'EV','last':'FG','prev_last':'ET',
     'months':['EV','EW','EX','EY','EZ','FA','FB','FC','FD','FE','FF','FG']},
    {'fy':'FY2031','year':2031,'annual':'FH','first':'FI','last':'FT','prev_last':'FG',
     'months':['FI','FJ','FK','FL','FM','FN','FO','FP','FQ','FR','FS','FT']},
    {'fy':'FY2032','year':2032,'annual':'FU','first':'FV','last':'GG','prev_last':'FT',
     'months':['FV','FW','FX','FY','FZ','GA','GB','GC','GD','GE','GF','GG']},
    {'fy':'FY2033','year':2033,'annual':'GH','first':'GI','last':'GT','prev_last':'GG',
     'months':['GI','GJ','GK','GL','GM','GN','GO','GP','GQ','GR','GS','GT']},
]

def replace_col_refs(formula, replacements):
    """Replace col letter refs: optional $, col letters, followed by $ or digit."""
    f = str(formula)
    for old, new in sorted(replacements, key=lambda x: -len(x[0])):
        pat = r'(?<![A-Z])(\$?)' + re.escape(old) + r'(?=[$\d])'
        f = re.sub(pat, lambda m, n=new: m.group(1) + n, f)
    return f

def gen_monthly(row, tmpl_val, cur, prev, annual, year, month):
    if row == 2:
        return f'=DATE({year},{month},1)'
    f = str(tmpl_val)
    # Extend INDEX/MATCH ranges to GT so new months are findable
    for rn in ['2', '7', '34', '174', '175']:
        f = f.replace(f':$ET${rn}', f':$GT${rn}')
        f = f.replace(f':ET${rn}',  f':$GT${rn}')
    # Annual col ref: $EH$xxx → $EU$xxx (or FH/FU/GH)
    f = f.replace('$EH$', f'${annual}$')
    # Column substitutions (prev=EG, cur=EI, next=EJ)
    nxt = col_letter(col_num(cur) + 1)
    f = replace_col_refs(f, [('EG', prev), ('EI', cur), ('EJ', nxt)])
    return f

def gen_annual(row, tmpl_val, annual, first, last, fy):
    if row == 1: return fy
    if row == 2: return 'Total'
    f = str(tmpl_val)
    # SUM(EI{r}:ET{r}) → SUM(first{r}:last{r})
    f = re.sub(r'SUM\(EI(\d+):ET(\d+)\)',
               lambda m: f'SUM({first}{m.group(1)}:{last}{m.group(2)})', f)
    # Standalone ET{r} → last_monthly{r}
    f = replace_col_refs(f, [('ET', last)])
    # EH → annual col
    f = replace_col_refs(f, [('EH', annual)])
    return f

# ── build col_data dict ───────────────────────────────────────────────────────
col_data = {}

for cfg in FY_CONFIG:
    # Annual total column
    arows = {1: cfg['fy'], 2: 'Total'}
    for row, val in eh.items():
        if row <= 2: continue
        arows[row] = gen_annual(row, val, cfg['annual'], cfg['first'], cfg['last'], cfg['fy'])
    col_data[cfg['annual']] = arows

    # Monthly columns
    for i, mc in enumerate(cfg['months']):
        month_num = i + 1
        prev = cfg['prev_last'] if i == 0 else cfg['months'][i - 1]
        mrows = {2: f"=DATE({cfg['year']},{month_num},1)"}
        for row, val in ei.items():
            if row == 2: continue
            mrows[row] = gen_monthly(row, val, mc, prev, cfg['annual'], cfg['year'], month_num)
        col_data[mc] = mrows

# Terminator so Dec 2033 SUMPRODUCT has a valid upper-bound date
col_data['GU'] = {2: '=DATE(2034,1,1)'}

ordered_cols = sorted(col_data.keys(), key=col_num)
print(f"\nPrepared {len(ordered_cols)} columns: {ordered_cols[0]}..{ordered_cols[-1]}")

# ── spot-check a few cells ───────────────────────────────────────────────────
print("\nSpot-checks (first 3 sample substitutions):")
for sample_col, sample_row in [('EV', 4), ('FI', 87), ('GI', 142), ('EU', 4), ('FH', 160)]:
    if sample_col in col_data and sample_row in col_data[sample_col]:
        print(f"  {sample_col}{sample_row}: {str(col_data[sample_col][sample_row])[:120]}")

# ── add columns to sheet ─────────────────────────────────────────────────────
current_cols = 152          # EV is the current last column
target_cols  = col_num('GU')  # 203
to_add = target_cols - current_cols
print(f"\nAdding {to_add} columns to sheet (current={current_cols}, target={target_cols})...")
api('POST', f'{BASE}:batchUpdate', {
    'requests': [{'appendDimension': {
        'sheetId': CB_GID, 'dimension': 'COLUMNS', 'length': to_add
    }}]
})
print("  Done.")

# ── build value ranges ────────────────────────────────────────────────────────
MAX_ROW = 191
value_ranges = []
for col in ordered_cols:
    rows = col_data[col]
    dense = []
    for r in range(1, MAX_ROW + 1):
        v = rows.get(r, '')
        dense.append(['' if (v == '' or v is None) else str(v)])
    value_ranges.append({
        'range': f"'cash bridge'!{col}1:{col}{MAX_ROW}",
        'majorDimension': 'ROWS',
        'values': dense
    })

# ── write in batches ──────────────────────────────────────────────────────────
BATCH_SIZE = 25
total_cells = 0
batches = [value_ranges[i:i+BATCH_SIZE] for i in range(0, len(value_ranges), BATCH_SIZE)]
print(f"\nWriting {len(value_ranges)} column ranges in {len(batches)} batches...")

for idx, batch in enumerate(batches, 1):
    print(f"  Batch {idx}/{len(batches)}  ({len(batch)} cols)...", end=' ', flush=True)
    resp = api('POST', f'{BASE}/values:batchUpdate', {
        'valueInputOption': 'USER_ENTERED',
        'data': batch
    })
    cells = resp.get('totalUpdatedCells', 0)
    total_cells += cells
    print(f"{cells} cells")
    time.sleep(1.5)

print(f"\n✓ Complete.  Total cells updated: {total_cells}")
print("Columns written:")
print("  EU (FY2030 annual) | EV-FG (Jan-Dec 2030)")
print("  FH (FY2031 annual) | FI-FT (Jan-Dec 2031)")
print("  FU (FY2032 annual) | FV-GG (Jan-Dec 2032)")
print("  GH (FY2033 annual) | GI-GT (Jan-Dec 2033)")
print("  GU (2034 terminator)")

# ── quick sanity read-back ────────────────────────────────────────────────────
print("\nSanity check – reading row 1-2 from EU..GT...")
url = (f'{BASE}/values/{urllib.parse.quote("cash bridge!EU1:GT2")}'
       f'?valueRenderOption=FORMATTED_VALUE')
rows = api('GET', url).get('values', [])
print(f"  Row 1: {rows[0] if rows else '(empty)'}")
print(f"  Row 2: {rows[1] if len(rows)>1 else '(empty)'}")

# Read a key value cell to confirm formulas resolved (net income Dec 2030 = FG87)
url2 = f'{BASE}/values/{urllib.parse.quote("cash bridge!FG87")}?valueRenderOption=FORMATTED_VALUE'
val2 = api('GET', url2).get('values', [[]])[0]
print(f"\n  FG87 (Net Income Dec 2030): {val2}")
url3 = f'{BASE}/values/{urllib.parse.quote("cash bridge!EU87")}?valueRenderOption=FORMATTED_VALUE'
val3 = api('GET', url3).get('values', [[]])[0]
print(f"  EU87 (Net Income FY2030 annual): {val3}")
