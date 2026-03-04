
import json
from datetime import date, timedelta

def generate_entries():
    start_date = date(2026, 5, 1)
    
    with open('sba_amort.json') as f:
        sba_data = json.load(f)['values']
    
    with open('seller_note_amort.json') as f:
        seller_note_data = json.load(f)['values']

    new_rows = []

    # Process SBA Loan
    # Find the header row to locate the 'Interest Payment' column
    sba_header_row_index = -1
    for i, row in enumerate(sba_data):
        if "Interest Payment" in row:
            sba_header_row_index = i
            break
    
    if sba_header_row_index != -1:
        interest_col_index = sba_data[sba_header_row_index].index("Interest Payment")
        sba_amort_schedule = sba_data[sba_header_row_index+1:]

        for row in sba_amort_schedule:
            if not row or not row[0].strip().isdigit():
                continue # Skip empty rows or rows that don't start with a period number
            
            period = int(row[0])
            # The interest payment is negative, so we take the absolute value
            interest_payment = abs(float(row[interest_col_index].replace('$', '').replace(',', '').replace('-','')))
            
            # Calculate the date for this payment
            payment_date = start_date + timedelta(days=31 * (period - 1))
            payment_date = payment_date.replace(day=1) # Set to the first of the month

            new_rows.append([
                "SBA 7a Interest",
                "SBA",
                payment_date.strftime("%m/%d/%Y"),
                payment_date.strftime("%m/%d/%Y"),
                1,
                "monthly",
                interest_payment,
                "Interest Expense",
                "", "", "", "", "", "61600", "", "", ""
            ])

    # Process Seller Note
    seller_note_header_row_index = -1
    for i, row in enumerate(seller_note_data):
        if "Interest Payment" in row:
            seller_note_header_row_index = i
            break

    if seller_note_header_row_index != -1:
        interest_col_index = seller_note_data[seller_note_header_row_index].index("Interest Payment")
        seller_note_amort_schedule = seller_note_data[seller_note_header_row_index+1:]

        for row in seller_note_amort_schedule:
            if not row or not row[0].strip().isdigit():
                continue

            period = int(row[0])
            interest_payment = abs(float(row[interest_col_index].replace('$', '').replace(',', '').replace('-','')))
            
            payment_date = start_date + timedelta(days=31 * (period - 1))
            payment_date = payment_date.replace(day=1)

            new_rows.append([
                "Seller Note Interest",
                "Seller",
                payment_date.strftime("%m/%d/%Y"),
                payment_date.strftime("%m/%d/%Y"),
                1,
                "monthly",
                interest_payment,
                "Interest Expense",
                "", "", "", "", "", "61600", "", "", ""
            ])
            
    # Prepare the JSON payload for the Sheets API
    payload = {
        'values': new_rows
    }
    
    print(json.dumps(payload, indent=2))

if __name__ == "__main__":
    generate_entries()
