import json, os, time, urllib.request, urllib.error
TOKEN=open(os.path.expanduser('~/.config/notion/api_key')).read().strip(); VER='2025-09-03'
DS='0349d6f1-82c7-48eb-8acf-42ac7ce35064'
DB='90eeb004-a9e9-49e9-b560-b19dba6f018b'
KEITH_URL='https://www.notion.so/Keith-Lefebvre-Current-Roles-Responsibilities-Draft-35e7e702d98c8180a8eaf00bbb9643cb'
MOD_URL='https://docs.google.com/document/d/1tSR_bMRJrHkF6-0gSQOKBu1z4b22yHOO/edit'

def req(m,p,payload=None):
    data=json.dumps(payload).encode('utf-8') if payload is not None else None
    r=urllib.request.Request('https://api.notion.com/v1'+p,data=data,method=m)
    r.add_header('Authorization','Bearer '+TOKEN); r.add_header('Notion-Version',VER); r.add_header('Content-Type','application/json')
    try:
        with urllib.request.urlopen(r,timeout=30) as resp: return json.load(resp)
    except urllib.error.HTTPError as e:
        raise RuntimeError(f'{m} {p} -> {e.code}: {e.read().decode()}')

def title(s): return {'title':[{'type':'text','text':{'content':s}}]}
def rt(s): return {'rich_text':[{'type':'text','text':{'content':s}}] if s else []}
def sel(s): return {'select': {'name': s}} if s else {'select': None}
def url(s): return {'url': s} if s else {'url': None}

existing=req('POST',f'/data_sources/{DS}/query',{'page_size':100})
existing_titles={''.join(x.get('plain_text','') for x in p['properties'].get('Name',{}).get('title',[])) for p in existing.get('results',[])}

items=[
    {
        'Name':'Nail down staffing plan, including Keith role coverage',
        'Status':'Candidate','Phase':'PA Signed → Close','Workstream':'Operations','Priority':'High','Owner':'Justin','Source Type':'New transition task','Source URL':KEITH_URL,
        'Trigger':'Purchase agreement signed / Kevin and Keith available for transition conversations; can start earlier if they are willing.',
        'Latest Safe Date':'Before close if possible; at minimum before Betty/Kevin/Keith post-close role assumptions are finalized.',
        'Notes':'Use the Keith roles/responsibilities page as the working source. Confirm which of Keith’s current roles remain with Keith, move to Kevin/Justin/Krissy/office process, require a new hire, or need outside support. Include field superintendent, PM/dispatch, inspection/ITM, AHJ coordination, QA/QC, repair/service, design coordination, and customer/GC relationship coverage. Also capture the sales-side questions Justin added at the end of the Keith page for Kevin discussion.'
    },
    {
        'Name':'Formalize estimating process with Kevin and Keith',
        'Status':'Candidate','Phase':'PA Signed → Close','Workstream':'Operations','Priority':'High','Owner':'Justin','Source Type':'Pulled from modernization plan','Source URL':MOD_URL,
        'Trigger':'Kevin and Keith available for working sessions; target between PA signature and close if they will engage.',
        'Latest Safe Date':'Before close if possible; otherwise first 30 days post-close. Do not wait until Kevin/Keith availability becomes constrained.',
        'Notes':'Transition version of the modernization item: capture enough of the estimating method that Justin can understand bid/no-bid, material/labor buildup, Schedule 40/material suitability heuristics, dollars-per-head / dollars-per-square-foot shortcuts, GC/customer assumptions, margin/overhead rules, and what requires Kevin vs Keith judgment. Success criterion remains: a documented process that can be followed without Kevin or Keith assistance, or at least a clear list of judgment points requiring their input.'
    }
]
created=[]; skipped=[]
for it in items:
    if it['Name'] in existing_titles:
        skipped.append(it['Name']); continue
    props={
        'Name': title(it['Name']), 'Status': sel(it['Status']), 'Phase': sel(it['Phase']), 'Workstream': sel(it['Workstream']),
        'Priority': sel(it['Priority']), 'Owner': sel(it['Owner']), 'Source Type': sel(it['Source Type']), 'Source URL': url(it['Source URL']),
        'Trigger': rt(it['Trigger']), 'Latest Safe Date': rt(it['Latest Safe Date']), 'Notes': rt(it['Notes'])
    }
    page=req('POST','/pages',{'parent':{'database_id':DB},'properties':props})
    created.append({'title':it['Name'],'id':page['id'],'url':page.get('url')})
    time.sleep(0.35)
print(json.dumps({'created':created,'skipped_existing':skipped},indent=2))
