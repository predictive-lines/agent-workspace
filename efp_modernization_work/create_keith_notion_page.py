import json
import os
from pathlib import Path
import requests

NOTION_VERSION = "2025-09-03"
PARENT_PAGE_ID = "3017e702d98c806790cbec175da62dce"  # Human Readable Reports
TITLE = "Keith Lefebvre — Current Roles & Responsibilities (Draft)"

key = Path.home().joinpath('.config/notion/api_key').read_text().strip()
headers = {
    "Authorization": f"Bearer {key}",
    "Notion-Version": NOTION_VERSION,
    "Content-Type": "application/json",
}

def rt(text):
    return [{"type": "text", "text": {"content": text[:2000]}}]

def block(block_type, text):
    return {"object": "block", "type": block_type, block_type: {"rich_text": rt(text)}}

def bullet(text):
    return block("bulleted_list_item", text)

def heading(level, text):
    return block(f"heading_{level}", text)

sections = [
    ("Context", [
        "Draft working document for decomposing Keith Lefebvre’s current role into explicit responsibilities. Built from the May 2026 current-state documentation, gap analysis, modernization roadmap, and site-visit planning notes.",
        "Working thesis: Keith is not one job. He is at least four roles compressed into one person: field superintendent, project manager/dispatcher, inspector/ITM lead, and technical code/AHJ knowledge holder. Replacing him with only a sprinkler fitter likely will not replace the operating capacity he currently provides.",
    ]),
    ("Field leadership & crew supervision", [
        "Acts as Excel Fire’s day-to-day field lead for sprinkler installation, service, repair, and inspection work.",
        "Assigns field crews each morning based on active jobs, available personnel, truck capacity, customer access windows, trade sequencing, and inspection appointments.",
        "Balances field capacity across roughly three field personnel / two active trucks, with the operational goal of keeping three trucks manned when staffing and workload allow.",
        "Provides practical labor-planning judgment, including rule-of-thumb productivity assumptions such as heads installed per journeyman per day.",
        "Serves as the office’s primary source of truth for whether a job has started, how far it has progressed, and what needs to happen next.",
    ]),
    ("Project management / scheduling", [
        "Functions as de facto project manager for active installation work.",
        "Coordinates job sequencing, field readiness, customer access, GC communication, and trade coordination, especially with fire alarm contractors.",
        "Manages scheduling friction around alarm contractors, AHJ inspection windows, customer availability, and field labor constraints.",
        "Provides percentage-of-completion estimates to the office for progress billing and draw invoices.",
        "Supports AIA billing / lien waiver workflows by giving the office the field-status inputs needed to bill accurately.",
        "Pushes back on incorrect lien waiver or back-charge amounts when field conditions do not support the customer/GC position.",
    ]),
    ("Inspection services / NFPA-25 delivery", [
        "Sole employee currently performing independent NFPA-25 inspections.",
        "Performs annual, semi-annual, quarterly, and five-year inspections on water-based fire protection systems.",
        "Produces or owns the final inspection report output; apprentices may assist physically but do not independently inspect.",
        "Handles inspection scheduling after front-desk intake, contacting site contacts and fitting inspections into his weekly field plan.",
        "Holds the working knowledge for recurring inspection facilities and their quirks, including the hospital complex / Siemens teaming arrangement.",
        "Carries facility-specific inspection knowledge that is not fully captured in Krissy’s spreadsheet or paper inspection forms.",
    ]),
    ("AHJ / rough-in / final inspection coordination", [
        "Primary field lead for rough-in and final AHJ inspections on new-construction installation projects.",
        "Coordinates with Michigan Bureau of Construction Codes / state inspector process, including Phil Myron’s UP inspection schedule and lead times.",
        "Prepares for rough-in/final inspections through personal walk-downs and readiness checks.",
        "Ensures required inspection artifacts are ready: hydraulic calculation sticker, test material sheets, installed material documentation, and related design artifacts.",
        "Coordinates design-subcontractor deliverables with what must physically be present on site for inspection.",
        "Holds the practical knowledge of why inspections pass/fail; no formal re-trip root-cause log currently replaces his memory.",
    ]),
    ("Repair / service workflow", [
        "Receives repair and service calls routed from the office.",
        "Gathers scope information and determines whether the issue can be handled as a smaller field repair or needs a larger written work order.",
        "Performs or directs smaller repairs from the field.",
        "Provides verbal or written work-order information to support billing after the fact.",
        "For larger repairs, prepares or drives the written work order that becomes the billing basis.",
        "Coordinates material needs with the office and/or ETNA purchasing path.",
    ]),
    ("Estimating / bid support", [
        "Alongside Kevin, can prepare estimates and bids.",
        "Participates in bid/no-bid judgment, especially where field complexity, compliance burden, or constructability matter.",
        "Uses and sanity-checks the two current estimating methods: dollars per square foot and dollars per sprinkler head.",
        "Drafts scope/pricing by hand from plans when needed, relying on memory rather than a written estimating guide.",
        "Provides field-execution judgment that informs labor assumptions, constructability, and whether the bid feels right.",
    ]),
    ("Design coordination / technical documentation", [
        "Acts as primary in-house design coordinator even though sprinkler design is subcontracted.",
        "Coordinates with Craig Johnson and, where applicable, other design subcontractors such as Jeff Prange.",
        "For very small/simple jobs, can produce basic plans showing head specifications and pipe layout.",
        "Understands when design requirements, state plan review, or engineer-stamp expectations may affect otherwise simple work.",
        "Bridges the gap between design documents, field installation, and what the AHJ expects to see.",
    ]),
    ("QA/QC and field readiness", [
        "Performs the informal QC function currently embedded in field operations.",
        "Walks jobs before AHJ rough-in/final inspections and checks whether the work is ready.",
        "Verifies repair/service work informally, either personally or through the responsible field crew.",
        "Identifies and resolves deficiencies before turnover where possible.",
        "Holds much of the Company’s practical knowledge about common failure modes, rework causes, and what creates inspection re-trips.",
    ]),
    ("Customer / GC / subcontractor coordination", [
        "Communicates directly with customers, GCs, site contacts, alarm contractors, design subcontractors, and inspectors by phone.",
        "Handles callbacks personally from the road based on the paper callback pile prepared by the office.",
        "Maintains part of the Company’s recurring field relationship capital, especially for inspection/service customers and active job contacts.",
        "Helps manage subcontractor underperformance or trade-coordination issues case by case, without a formal subcontractor-management framework.",
        "Carries some customer-specific procedural knowledge that is not visible in QuickBooks or a CRM.",
    ]),
    ("Compliance / code knowledge holder", [
        "Applies NFPA 13, NFPA 25, Michigan Building Code, and Michigan Bureau of Construction Codes requirements from personal working knowledge.",
        "Holds AHJ-specific and county/fire-marshal procedural knowledge that is not maintained in a master register.",
        "Knows the practical implications of state-level plan review, inspection lead times, and local code-enforcement expectations.",
        "Supports mine/customer-specific work where site rules, safety training, or access requirements affect deployment.",
    ]),
    ("Operational risk / succession implication", [
        "Keith’s current role combines field superintendent, project manager, scheduler, inspector, design coordinator, AHJ liaison, QC lead, and technical mentor.",
        "A single replacement hire is unlikely to cover all of that unless they are unusually senior and inspection-qualified.",
        "Possible path: hire a senior operations / inspection lead and split administrative/project-management support into the office.",
        "Possible path: promote/cross-train internally for parts of the role while hiring externally for NFPA-25 / inspection capability.",
        "Possible path: intentionally split Keith’s work into two positions: field superintendent + inspection/ITM lead.",
    ]),
    ("Clarifying questions for Keith", [
        "What decisions do you make every morning before crews leave?",
        "What jobs/customers can only you handle today?",
        "Which inspections would fail or stall if you were out for two weeks?",
        "What do you check before calling for rough-in/final inspection?",
        "What does Konner already know how to do independently, and what is he not close to owning?",
        "Which parts of your job could Krissy/the office take over with the right form or checklist?",
        "Which parts require a licensed/certified sprinkler person no matter how good the admin process is?",
    ]),
]

children = [
    block("paragraph", "Draft status: working page for Justin to edit during onsite discovery. Not intended as a final job posting yet."),
]
for title, bullets in sections:
    children.append(heading(2, title))
    for item in bullets:
        children.append(bullet(item))

payload = {
    "parent": {"page_id": PARENT_PAGE_ID},
    "properties": {"title": [{"type": "text", "text": {"content": TITLE}}]},
    "children": children[:100],
}

resp = requests.post("https://api.notion.com/v1/pages", headers=headers, json=payload, timeout=30)
if resp.status_code >= 400:
    print(resp.status_code, resp.text)
    resp.raise_for_status()
page = resp.json()
print(json.dumps({"id": page["id"], "url": page["url"], "title": TITLE}, indent=2))

# Verify page content is readable.
verify = requests.get(f"https://api.notion.com/v1/blocks/{page['id']}/children?page_size=100", headers=headers, timeout=30)
verify.raise_for_status()
blocks = verify.json().get("results", [])
print(json.dumps({"verified_blocks": len(blocks), "has_content": len(blocks) >= 10}, indent=2))
