from docx import Document

SRC='efp_modernization_work/current-state-process-documentation-efp.verify-material-check.docx'
OUT='efp_modernization_work/current-state-process-documentation-efp.ar-cadence.docx'

doc=Document(SRC)
for p in doc.paragraphs:
    t=p.text.strip()
    if t.startswith('The Company maintains an informal physical tracking system for open invoices and billing milestones.'):
        p.text=(
            'The Company maintains an informal physical tracking system for open invoices, billing status, and job percent-complete estimates. An office whiteboard is used to list active jobs with the amounts owed and the percentage complete for each. For larger installation projects, job completion is evaluated by reference to milestones and field progress — for example rough-in status, finishing status, final completion, and retainage closeout — but invoices are generally prepared on a monthly cadence. The amount invoiced on a given billing date is the incremental change in percent complete since the prior billing date, rather than a one-time invoice triggered only when a milestone is reached. These percent-complete estimates and billing calculations are tracked by the office staff against the whiteboard and the physical project files rather than in QuickBooks as a formal work-in-process or percent-complete billing system.'
        )
    elif t.startswith('Billing on installation projects cannot begin until a signed contract has been received'):
        p.text=(
            'Billing on installation projects cannot begin until a signed contract has been received and the job has been entered on the office tracking board. For larger projects, the contract and schedule of values provide the billing framework, and job progress is assessed against milestones and field completion. The billing cadence itself is monthly: at each billing date, the office invoices the difference between the percent complete reflected on the prior billing date and the percent complete reflected on the current billing date. Retainage — typically 10% or 5%, as specified in the contract — is withheld from each progress billing.'
        )
    elif t.startswith('The dollar amount to bill on each draw is determined through a combination of two inputs:'):
        p.text=(
            'The dollar amount to bill in each monthly progress invoice is determined through a combination of inputs: the prior billed percent-complete, Keith’s current field assessment of percent complete, the milestones/progress visible from the field, and the payroll hours charged to the job (visible to the office through QuickBooks after Jamie processes timesheets). The office asks Keith for the current completion percentage, compares it against labor hours and contract value, calculates the incremental percent-complete movement since the prior billing date, and prepares the invoice accordingly. Payment is typically received approximately 25 days after invoice submission, though this varies by customer and by the speed of the project owner’s payment cycle.'
        )
    elif t.startswith('At project completion, a separate invoice is prepared to bill for all accumulated retainage.'):
        p.text=(
            'At project completion, a separate invoice is prepared to bill for all accumulated retainage. The tracking board — the physical whiteboard described elsewhere in this report — carries four data points per job: contract amount, amount billed per invoice/monthly draw, amount received, and remaining retainage. Each billing is numbered sequentially against the contract, and the final billing reflects 100% completion before retainage release.'
        )

doc.save(OUT)
print(OUT)
