from docx import Document

SRC='efp_modernization_work/modernization-plan-efp.verify-inspection-invoicing.docx'
OUT='efp_modernization_work/modernization-plan-efp.qbo-payroll-transition.docx'

doc=Document(SRC)

inserted=False
for i,p in enumerate(doc.paragraphs):
    if p.text.strip().startswith('Status: Scheduled — QuickBooks Desktop → QuickBooks Online with QuickBooks Payroll migration'):
        p.text = (
            'Status: Scheduled — QuickBooks Desktop → QuickBooks Online with QuickBooks Payroll migration, paired with a digital timecard submission path. '
            'Phase 1 may be as simple as emailed/texted photos of handwritten timesheets; later phases can evaluate QBO Time, Workyard, busybusy, ExakTime, or another field-labor system depending on union payroll, certified payroll, job-costing, and crew-adoption requirements. '
            'As a transition-control item, the migration should explicitly map which payroll taxes, filings, and remittances QuickBooks Payroll will own; which agency accounts and authorizations must be connected; and which obligations remain outside the payroll provider.'
        )
    if p.text.strip().startswith('Sequence: Do not wait for the final payroll platform to improve capture.'):
        p.text = (
            'Sequence: Do not wait for the final payroll platform to improve capture. First standardize submission timing and required fields; then align the durable tool decision with the QBO/payroll migration and job-costing design. '
            'Before or during setup, confirm federal and Michigan withholding, employer payroll taxes, Michigan UIA, quarterly payroll tax filings, year-end W-2 processing, union Local 669 fringe-benefit remittances, certified payroll reporting, workers’ compensation payroll reporting/audits, and any job/classification reporting requirements. '
            'The deliverable should be a responsibility matrix showing whether each item is handled by QuickBooks Payroll, AT&C, Betty/current office staff during transition, Justin/Jaclyn, the union/fringe administrator, or another outside advisor.'
        )
    if p.text.strip().startswith('Success Criteria: Time is submitted on schedule'):
        p.text = (
            'Success Criteria: Time is submitted on schedule, legible, retained, and attributable by employee/job/work type; payroll can be processed without chasing paper; certified payroll and job-costing data can be produced from the same source of truth or a controlled reconciliation; and payroll compliance ownership is explicit enough that no federal/state withholding, FICA, FUTA, Michigan UIA, union fringe, certified-payroll, or workers’ compensation reporting obligation depends on undocumented office memory.'
        )
        inserted=True

if not inserted:
    raise SystemExit('Did not find Finding #8 success criteria block to patch')

doc.save(OUT)
print(OUT)
