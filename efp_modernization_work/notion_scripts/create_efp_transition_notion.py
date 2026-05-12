import json, os, time, urllib.request, urllib.error
TOKEN=open(os.path.expanduser('~/.config/notion/api_key')).read().strip()
VER='2025-09-03'
ROOT='2ff7e702-d98c-80a9-bf01-d03635e5e5f4'
TASK_DS='2847e702-d98c-8170-9008-000bc7d6d318'
TITLE='EFP Signing-to-Close Transition'

def req(method,path,payload=None):
    data=json.dumps(payload).encode('utf-8') if payload is not None else None
    r=urllib.request.Request('https://api.notion.com/v1'+path,data=data,method=method)
    r.add_header('Authorization','Bearer '+TOKEN)
    r.add_header('Notion-Version',VER)
    r.add_header('Content-Type','application/json')
    try:
        with urllib.request.urlopen(r,timeout=60) as resp:
            return json.load(resp)
    except urllib.error.HTTPError as e:
        body=e.read().decode('utf-8','replace')
        raise RuntimeError(f'{method} {path} -> {e.code}: {body}')

def rich(s): return [{'type':'text','text':{'content':s}}] if s else []
def title_prop(s): return {'title':[{'type':'text','text':{'content':s}}]}
def rt_prop(s): return {'rich_text':rich(s)}
def sel(name): return {'select': {'name': name}} if name else {'select': None}
def date_prop(s): return {'date': {'start': s}} if s else {'date': None}
def url_prop(s): return {'url': s} if s else {'url': None}

def find_existing_page():
    res=req('POST','/search',{'query':TITLE,'page_size':10})
    for item in res.get('results',[]):
        if item.get('object')=='page':
            pt=item.get('properties',{}).get('title',{}).get('title') or item.get('properties',{}).get('Name',{}).get('title')
            name=''.join(x.get('plain_text','') for x in pt or [])
            if name==TITLE:
                return item
    return None

existing=find_existing_page()
if existing:
    page=existing
    print('existing page', page['id'], page.get('url'))
else:
    page=req('POST','/pages',{
        'parent': {'page_id': ROOT},
        'properties': {'title': title_prop(TITLE)['title']},
        'children': [
            {'object':'block','type':'paragraph','paragraph':{'rich_text':rich('Purpose: capture work that can be completed between purchase-agreement signature and close without disturbing the due-diligence project or the modernization roadmap.')}},
            {'object':'block','type':'paragraph','paragraph':{'rich_text':rich('Rule of thumb: include access, continuity, handoff, and day-one readiness tasks. Exclude broad post-close modernization unless the work can realistically be completed before close or directly reduces day-one operating risk.')}},
            {'object':'block','type':'bulleted_list_item','bulleted_list_item':{'rich_text':rich('Do not store raw passwords here. Use this project to inventory systems, owners, URLs, recovery paths, and handoff status; transfer credentials through a password manager/admin-invite/reset process.')}},
            {'object':'block','type':'bulleted_list_item','bulleted_list_item':{'rich_text':rich('Existing tasks copied here are non-destructive duplicates with source links back to the original task.')}}
        ]
    })
    print('created page', page['id'], page.get('url'))

# Check for existing inline transition data source on this page
children=req('GET',f"/blocks/{page['id']}/children?page_size=100")
ds=None
for b in children.get('results',[]):
    if b.get('type')=='child_database' and b.get('child_database',{}).get('title')=='Transition Task List':
        ds={'id': b['id']}
        break

if not ds:
    payload={
        'parent': {'type':'page_id','page_id': page['id']},
        'title': [{'type':'text','text':{'content':'Transition Task List'}}],
        'is_inline': True,
        'properties': {
            'Task': {'title': {}},
            'Status': {'select': {'options': [
                {'name':'Candidate','color':'gray'}, {'name':'Next','color':'blue'}, {'name':'Waiting on PA Signature','color':'yellow'}, {'name':'Waiting on Seller','color':'orange'}, {'name':'In Progress','color':'purple'}, {'name':'Done','color':'green'}, {'name':'Defer to Modernization','color':'pink'}]}},
            'Phase': {'select': {'options': [
                {'name':'PA Signed → Close','color':'blue'}, {'name':'Day 1 Readiness','color':'red'}, {'name':'Close Week','color':'orange'}, {'name':'Before PA Signature','color':'gray'}]}},
            'Workstream': {'select': {'options': [
                {'name':'Access / IT','color':'purple'}, {'name':'Finance / Banking','color':'green'}, {'name':'Payroll / HR','color':'yellow'}, {'name':'Operations','color':'blue'}, {'name':'Compliance / Licensing','color':'red'}, {'name':'Customers / Vendors','color':'orange'}, {'name':'Knowledge Transfer','color':'brown'}, {'name':'Deal Mechanics','color':'gray'}]}},
            'Priority': {'select': {'options': [{'name':'High','color':'red'}, {'name':'Medium','color':'yellow'}, {'name':'Low','color':'green'}]}},
            'Trigger': {'rich_text': {}},
            'Latest Safe Date': {'rich_text': {}},
            'Owner': {'select': {'options': [{'name':'Justin','color':'blue'}, {'name':'Jaclyn','color':'pink'}, {'name':'Kevin','color':'orange'}, {'name':'Betty','color':'purple'}, {'name':'Keith','color':'brown'}, {'name':'AT&C','color':'gray'}, {'name':'Vendor / Advisor','color':'green'}]}},
            'Source Type': {'select': {'options': [{'name':'Copied existing Notion task','color':'blue'}, {'name':'Pulled from modernization plan','color':'green'}, {'name':'New transition task','color':'purple'}]}},
            'Source URL': {'url': {}},
            'Notes': {'rich_text': {}},
        }
    }
    
    # API 2025-09-03 requires Create Database API for new databases, then query via returned data source id.
    db_payload = dict(payload)
    db_payload.pop('is_inline', None)
    db=req('POST','/databases',db_payload)
    ds_id = db.get('data_sources',[{}])[0].get('id') or db.get('id')
    ds={'id': ds_id, 'database_id': db.get('id')}
    print('created database', db.get('id'), 'data source', ds_id)
else:
    print('existing data source/block', ds['id'])

# If child_database block id is not a data source id under new API, search by title for DS under page.
# Try query; if fails, search.
data_source_id=ds['id']
database_id=ds.get('database_id')
try:
    qtest=req('POST',f'/data_sources/{data_source_id}/query',{'page_size':1})
except Exception:
    search=req('POST','/search',{'query':'Transition Task List','page_size':10})
    for item in search.get('results',[]):
        if item.get('object')=='data_source':
            title=''.join(x.get('plain_text','') for x in item.get('title',[]))
            if title=='Transition Task List':
                data_source_id=item['id']; database_id=item.get('parent',{}).get('database_id'); break
print('data_source_id', data_source_id, 'database_id', database_id)

# Avoid duplicates if rerun: pull existing titles.
current=req('POST',f'/data_sources/{data_source_id}/query',{'page_size':100})
existing_titles=set()
for p in current.get('results',[]):
    prop=p['properties'].get('Name',{})
    existing_titles.add(''.join(x.get('plain_text','') for x in prop.get('title',[])))

items=[
    dict(task='Collect / transfer Betty-controlled logins and recovery paths', status='Waiting on PA Signature', phase='PA Signed → Close', workstream='Access / IT', priority='High', trigger='Purchase agreement signed; earlier only if Kevin/Betty are willing', latest='Before close; ideally 1–2 weeks before Betty’s last active day', owner='Betty', source_type='Copied existing Notion task', source_url='https://www.notion.so/Collect-Logins-from-Betty-35e7e702d98c80c8adedca693a3809f1', notes='Do not store raw passwords in Notion. Inventory systems, URLs, account owners, 2FA/recovery paths; transfer via password manager/admin invite/reset.'),
    dict(task='Create successor admin access for core systems', status='Candidate', phase='PA Signed → Close', workstream='Access / IT', priority='High', trigger='After system inventory and seller cooperation', latest='Before close', owner='Justin', source_type='New transition task', source_url='', notes='QB Desktop, M365, payroll/tax portals, bank, insurance, vendor portals, utilities, website/domain if applicable.'),
    dict(task='Move 2FA and account recovery paths off Betty-personal channels', status='Candidate', phase='PA Signed → Close', workstream='Access / IT', priority='High', trigger='After inventory identifies Betty-linked phone/email/recovery paths', latest='Before Betty retirement / before close where possible', owner='Justin', source_type='New transition task', source_url='', notes='Prefer shared admin/recovery mailbox and named successor admins. Coordinate with AT&C for M365/QB/desktop infrastructure.'),
    dict(task='Give operations mailbox read-only access to Kevin mailboxes', status='Candidate', phase='PA Signed → Close', workstream='Access / IT', priority='Medium', trigger='After PA signed and Kevin agrees to transition access', latest='Before close if email history is needed for continuity', owner='AT&C', source_type='Copied existing Notion task', source_url='https://www.notion.so/Give-operations-xlfire-net-read-only-access-to-kvm-xlfire-net-kevin-xlfire-net-34a7e702d98c8040a215c93186e343b5', notes='Copied because this is access/continuity, not broad modernization.'),
    dict(task='Betty knowledge-transfer checklist and sessions', status='Candidate', phase='PA Signed → Close', workstream='Knowledge Transfer', priority='High', trigger='PA signed / Betty willing to schedule transition time', latest='Before Betty retirement; first session ASAP after PA signature', owner='Betty', source_type='New transition task', source_url='', notes='Cover weekly cash routines, invoices, payroll handoff, vendor payments, union/fringe benefits, bank deposits, customer billing quirks, filing cabinets, recurring bills, and who knows what.'),
    dict(task='Closing-day operating checklist', status='Candidate', phase='Day 1 Readiness', workstream='Operations', priority='High', trigger='Once close date is scheduled', latest='Complete 3–5 business days before close', owner='Justin', source_type='New transition task', source_url='', notes='Who can invoice, run payroll, pay vendors, answer phones, access email, schedule work, open QB, contact AT&C, contact bank, and handle emergencies on Day 1.'),
    dict(task='Schedule close date and working backwards transition milestones', status='Not Started', phase='PA Signed → Close', workstream='Deal Mechanics', priority='High', trigger='After lender selected and PA ready/signing', latest='Immediately after PA signature', owner='Justin', source_type='Copied existing Notion task', source_url='https://www.notion.so/Schedule-Close-Date-28d7e702d98c8036b288d6cf519b0426', notes='Non-destructive copy; original diligence/deal task left untouched.'),
    dict(task='Banking transition: signer changes, spending authority, cards, online banking', status='Candidate', phase='PA Signed → Close', workstream='Finance / Banking', priority='High', trigger='PA signed and bank/lender path selected', latest='Before close or on closing-day checklist with bank appointment scheduled', owner='Justin', source_type='New transition task', source_url='', notes='Tie to signature-stamp sunset and operating/shareholder agreement authority tiers.'),
    dict(task='Payroll and tax portal access transition', status='Candidate', phase='PA Signed → Close', workstream='Payroll / HR', priority='High', trigger='PA signed; before first payroll under new ownership', latest='Before first post-close payroll; preferably before close', owner='Betty', source_type='Pulled from modernization plan', source_url='https://docs.google.com/document/d/1tSR_bMRJrHkF6-0gSQOKBu1z4b22yHOO/edit', notes='This is not the full QBO/payroll modernization. It is continuity access for existing payroll/tax process so the first payroll cannot fail.'),
    dict(task='Personnel file audit: I-9, W-4, MI-W4, safety/training/cert records', status='Candidate', phase='PA Signed → Close', workstream='Payroll / HR', priority='High', trigger='Can be done now if access is available; otherwise PA signed', latest='Before close if missing documents need remediation plan', owner='Justin', source_type='Pulled from modernization plan', source_url='https://docs.google.com/document/d/1tSR_bMRJrHkF6-0gSQOKBu1z4b22yHOO/edit', notes='Keep this as verification/remediation planning. Do not overstate missing forms until audit is complete.'),
    dict(task='BFS/S-0440 qualifying-person continuity plan', status='Candidate', phase='PA Signed → Close', workstream='Compliance / Licensing', priority='High', trigger='PA signed; Kevin willing to coordinate licensing succession', latest='Before any Kevin role change / before close if Kevin’s post-close role is uncertain', owner='Justin', source_type='Pulled from modernization plan', source_url='https://docs.google.com/document/d/1tSR_bMRJrHkF6-0gSQOKBu1z4b22yHOO/edit', notes='EFP certificate valid through Sep 2028 with Kevin as qualifying person; transition plan should avoid sole qualifying-person disruption.'),
    dict(task='Vendor account handoff list', status='Candidate', phase='PA Signed → Close', workstream='Customers / Vendors', priority='Medium', trigger='PA signed; Betty/Kevin willing to share account/vendor details', latest='Before close where recurring bills or critical suppliers are involved', owner='Betty', source_type='New transition task', source_url='', notes='Include ETNA, insurance, utilities, union/fringe benefits, IT/AT&C, vehicle/fuel, phone/internet, rent/landlord, major customers/national accounts.'),
    dict(task='Customer / GC ownership-transition communication plan', status='Candidate', phase='Close Week', workstream='Customers / Vendors', priority='Medium', trigger='Close date known and Kevin approves messaging', latest='Before public/customer announcement', owner='Justin', source_type='New transition task', source_url='', notes='Prepare who is told, when, and by whom. Separate internal crew message from key customer/GC/vendor messages.'),
    dict(task='First billing cycle readiness check', status='Candidate', phase='Day 1 Readiness', workstream='Finance / Banking', priority='High', trigger='Before close once access and Krissy/Betty process are mapped', latest='Before first post-close invoice run', owner='Justin', source_type='Pulled from modernization plan', source_url='https://docs.google.com/document/d/1tSR_bMRJrHkF6-0gSQOKBu1z4b22yHOO/edit', notes='Continuity version only: ensure invoices can be generated/sent, AIA billing can continue, inspection invoices can be transmitted, and collections follow-up owner is known.'),
    dict(task='Process walkthroughs for order-to-cash / procure-to-pay / close-to-report', status='Candidate', phase='PA Signed → Close', workstream='Knowledge Transfer', priority='Medium', trigger='PA signed; Betty/Krissy/Kevin willing to walk process live', latest='Before close if possible; otherwise early 0–30', owner='Justin', source_type='Copied existing Notion task', source_url='https://www.notion.so/Process-walkthroughs-order-to-cash-procure-to-pay-close-to-report-4055f442bdf144b8a5070c3ffd087997', notes='Include only the transition/continuity walkthrough here; detailed SOP cleanup can stay in modernization.'),
]

created=0; skipped=0
for it in items:
    if it['task'] in existing_titles:
        skipped+=1; continue
    props={
        'Name': title_prop(it['task']),
        'Status': sel(it['status']),
        'Phase': sel(it['phase']),
        'Workstream': sel(it['workstream']),
        'Priority': sel(it['priority']),
        'Trigger': rt_prop(it['trigger']),
        'Latest Safe Date': rt_prop(it['latest']),
        'Owner': sel(it['owner']),
        'Source Type': sel(it['source_type']),
        'Source URL': url_prop(it['source_url']),
        'Notes': rt_prop(it['notes']),
    }
    req('POST','/pages',{'parent': {'database_id': database_id}, 'properties': props})
    created+=1
    time.sleep(0.35)
print(json.dumps({'page_id':page['id'],'page_url':page.get('url'),'data_source_id':data_source_id,'created':created,'skipped_existing':skipped},indent=2))
