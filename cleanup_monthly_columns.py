#!/usr/bin/env python3
"""Clean up monthly columns across IS, CF, and BS sheets."""

import json, requests, sys, time

# Auth  
TOKEN = open('/tmp/gtoken.txt').read().strip()
SHEET_ID = "13KQXudrHd5F3p-NHrr_RTkSWuIAbhVuDp9GIDVNCetM"
HEADERS = {"Authorization": f"Bearer {TOKEN}", "Content-Type": "application/json"}
BASE = f"https://sheets.googleapis.com/v4/spreadsheets/{SHEET_ID}"

SHEETS = ["Income Statement", "Cash Flow Statement", "Balance Sheet"]

print("Cleaning up monthly columns across all three sheets...")

# Step 1: Clear J3 and below (keep J2 sentinel date)
print("\nStep 1: Clearing J3:J1000 on all sheets...")
for sheet_name in SHEETS:
    clear_range = f"'{sheet_name}'!J3:J1000"
    resp = requests.post(f"{BASE}/values/{clear_range}:clear", headers=HEADERS)
    if resp.status_code == 200:
        print(f"  ✓ Cleared {sheet_name}")
    else:
        print(f"  ✗ Error clearing {sheet_name}: {resp.status_code}")

# Step 2: Delete columns K through BC (columns 11-55)
print("\nStep 2: Deleting columns K:BC...")

# Get sheet IDs first
resp = requests.get(f"{BASE}?fields=sheets.properties", headers=HEADERS)
sheet_data = resp.json()
sheet_ids = {}
for sheet in sheet_data['sheets']:
    name = sheet['properties']['title']
    if name in SHEETS:
        sheet_ids[name] = sheet['properties']['sheetId']

# Delete columns K:BC (startIndex=10, endIndex=55 for 0-indexed)  
for sheet_name in SHEETS:
    if sheet_name not in sheet_ids:
        print(f"  ✗ Sheet '{sheet_name}' not found")
        continue
        
    delete_request = {
        "requests": [{
            "deleteDimension": {
                "range": {
                    "sheetId": sheet_ids[sheet_name],
                    "dimension": "COLUMNS", 
                    "startIndex": 10,  # Column K (0-indexed)
                    "endIndex": 55     # Through column BC
                }
            }
        }]
    }
    
    resp = requests.post(f"{BASE}:batchUpdate", headers=HEADERS, json=delete_request)
    if resp.status_code == 200:
        print(f"  ✓ Deleted columns K:BC from {sheet_name}")
    else:
        print(f"  ✗ Error deleting columns from {sheet_name}: {resp.status_code} - {resp.text[:200]}")

# Step 3: Verify the cleanup
print("\nStep 3: Verifying cleanup...")
time.sleep(3)

for sheet_name in SHEETS:
    # Check that J2 still exists and J3 is empty
    resp = requests.get(f"{BASE}/values/'{sheet_name}'!J1:L5", headers=HEADERS)
    if resp.status_code == 200:
        values = resp.json().get('values', [])
        j2_val = values[1][0] if len(values) > 1 and len(values[1]) > 0 else "EMPTY"
        j3_val = values[2][0] if len(values) > 2 and len(values[2]) > 0 else "EMPTY"
        col_count = len(values[0]) if values else 0
        print(f"  {sheet_name}: J2='{j2_val[:20]}...' J3='{j3_val}' Cols after J: {col_count-1}")
    else:
        print(f"  ✗ Error verifying {sheet_name}: {resp.status_code}")

print("\n✅ Monthly column cleanup complete!")
print("All three sheets now use annual formulas only, with J2 as the sentinel end date.")