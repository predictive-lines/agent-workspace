from docx import Document
SRC='efp_modernization_work/modernization-plan-efp.verify-qbo-payroll-transition.docx'
OUT='efp_modernization_work/modernization-plan-efp.banking-after-close.docx'
doc=Document(SRC)
patched=False
for p in doc.paragraphs:
    t=p.text.strip()
    if t.startswith('Sequence: To confirm during Kevin / Justin review'):
        p.text = ('Sequence: Treat as a close / immediate post-close control conversion. Confirm the closing-bank operating model, replace the legacy signature-stamp practice with named signers and documented authority thresholds, update online-banking administrator access, issue or cancel cards/check stock as needed, and align signer changes with the shareholders’/operating agreement authority tiers. This should be coordinated with the signing-to-close transition checklist, but durable spending authority and banking controls belong in the modernization plan after close.')
        patched=True
    elif t.startswith('Success Criteria: To define as a testable done condition'):
        p.text = ('Success Criteria: Kevin’s signature-stamp practice is no longer used; bank signers and online-banking administrators match the post-close authority model; cardholders, limits, check controls, and approval thresholds are documented; and Betty/current-office access is either removed, retained only for an approved transition role, or converted to named-role access with appropriate controls.')
    elif t.startswith('Milestones: To assign once the item is prioritized'):
        p.text = ('Milestones: Close week: confirm bank transition appointment and required signer documentation. Day 1 / first 30 days: update signers, online banking, cardholders, and approval limits. 0–90 days: test dual-control workflow for vendor payments, payroll funding, and unusual disbursements; reconcile controls against the shareholders’/operating agreement.')
    elif t.startswith('Open Questions: Confirm owner, priority'):
        p.text = ('Open Questions: Which bank account structure will be used at close; whether old accounts are retained or replaced; who will have online-banking admin rights; what dollar thresholds require Justin/Jaclyn/Kevin approval; how long, if at all, Betty retains any access during transition; and which controls are bank-configured versus internal policy.')
if not patched:
    raise SystemExit('Banking sequence block not found')
doc.save(OUT)
print(OUT)
