import json, os, time, urllib.request, urllib.error
TOKEN=open(os.path.expanduser('~/.config/notion/api_key')).read().strip()
VER='2025-09-03'
TASK_TITLE='Personnel file audit: I-9, W-4, MI-W4, safety/training/cert records'


def req(method,path,payload=None):
    data=json.dumps(payload).encode('utf-8') if payload is not None else None
    r=urllib.request.Request('https://api.notion.com/v1'+path,data=data,method=method)
    r.add_header('Authorization','Bearer '+TOKEN)
    r.add_header('Notion-Version',VER)
    r.add_header('Content-Type','application/json')
    try:
        with urllib.request.urlopen(r,timeout=60) as resp:
            if resp.status == 204:
                return {}
            return json.load(resp)
    except urllib.error.HTTPError as e:
        body=e.read().decode('utf-8','replace')
        raise RuntimeError(f'{method} {path} -> {e.code}: {body}')

def rt(s):
    # Split rich_text chunks to satisfy Notion's 2000-char text content limit.
    out=[]
    for i in range(0, len(s), 1900):
        out.append({'type':'text','text':{'content':s[i:i+1900]}})
    return out

def title_text(prop):
    return ''.join(x.get('plain_text','') for x in prop.get('title',[]))

# Find Transition Task List data source
search=req('POST','/search',{'query':'Transition Task List','page_size':20})
ds_id=None
for item in search.get('results',[]):
    if item.get('object')=='data_source':
        title=''.join(x.get('plain_text','') for x in item.get('title',[]))
        if title=='Transition Task List':
            ds_id=item['id']
            break
if not ds_id:
    raise SystemExit('Transition Task List data source not found')

# Query for the personnel audit task.
q=req('POST',f'/data_sources/{ds_id}/query',{
    'page_size':100,
    'filter': {'property':'Name','title':{'equals':TASK_TITLE}}
})
if not q.get('results'):
    # fallback: broad query and substring match
    q=req('POST',f'/data_sources/{ds_id}/query',{'page_size':100})
    matches=[]
    for p in q.get('results',[]):
        name=title_text(p.get('properties',{}).get('Name',{}))
        if 'Personnel file audit' in name:
            matches.append(p)
    if not matches:
        raise SystemExit('Personnel file audit task not found')
    page=matches[0]
else:
    page=q['results'][0]

page_id=page['id']
summary=(
    'May 12 personnel-file inspection update: Justin reviewed available personnel folders. '
    'Newer-hire files appear materially complete: Connor/Konner has W-4, MI-W4, and I-9; '
    'Chrissy/Krissy has W-4, MI-W4, and a 2024 I-9; Josh Carr has W-4, MI-W4, and I-9. '
    'Betty has a 2020 W-4 but I-9 still needs confirmation. Bud has a 2012 W-4 and likely MI-W4, '
    'but his file is cluttered with unemployment-claim materials and an I-9 was not located. '
    'Keith has a W-4, a blank MI-W4, and no I-9 located. W-2s were found for Keith, Bud, Chrissy/Krissy, '
    'and Chris Musselman, but W-2s do not substitute for I-9/W-4/MI-W4 onboarding documents. '
    'I-9s generally do not require routine renewal for U.S. citizens/permanent-work-authorized employees; '
    'the transition risk is missing/not-located legacy forms, not old but valid I-9s.'
)
action=(
    'Action: ask Betty specifically for Keith and Bud’s I-9s before close — preferably before PA signature if she is willing — '
    'and confirm whether Betty’s own I-9 is on file. If a current employee’s I-9 truly cannot be located, complete a current Form I-9 '
    'with honest dates and keep an audit note; do not backdate. Have Keith complete a current MI-W4 rather than relying on the blank form.'
)
notes=summary+'\n\n'+action

props={
    'Status': {'select': {'name': 'In Progress'}},
    'Phase': {'select': {'name': 'Before PA Signature'}},
    'Trigger': {'rich_text': rt('Already partially inspected May 12. Next step is seller/Betty follow-up for legacy forms before PA signature if possible; otherwise immediately after PA signature.')},
    'Latest Safe Date': {'rich_text': rt('Ask Betty before PA signature if possible; absolute latest before close so missing I-9s can be remediated honestly.')},
    'Notes': {'rich_text': rt(notes)},
}
req('PATCH',f'/pages/{page_id}',{'properties': props})

children=[
    {'object':'block','type':'heading_3','heading_3':{'rich_text':rt('May 12 personnel-file inspection update')}},
    {'object':'block','type':'paragraph','paragraph':{'rich_text':rt(summary)}},
    {'object':'block','type':'to_do','to_do':{'rich_text':rt('Ask Betty for Keith and Bud’s I-9s before close — preferably before PA signature if she is willing.'),'checked':False}},
    {'object':'block','type':'to_do','to_do':{'rich_text':rt('Confirm whether Betty’s own I-9 is on file.'),'checked':False}},
    {'object':'block','type':'paragraph','paragraph':{'rich_text':rt('Cleanup note: if a current employee I-9 truly cannot be located, complete a current Form I-9 with honest dates and retain an audit note; do not backdate. Keith should complete a current MI-W4 rather than relying on a blank form.')}}
]
req('PATCH',f'/blocks/{page_id}/children',{'children':children})

time.sleep(0.35)
verify=req('GET',f'/pages/{page_id}')
verify_props=verify.get('properties',{})
blocks=req('GET',f'/blocks/{page_id}/children?page_size=100')
texts=[]
for b in blocks.get('results',[]):
    typ=b.get('type')
    data=b.get(typ,{})
    if 'rich_text' in data:
        t=''.join(x.get('plain_text','') for x in data.get('rich_text',[]))
        if 'May 12 personnel-file inspection update' in t or 'Keith and Bud' in t or 'Betty' in t:
            texts.append(t)
print(json.dumps({
    'updated_page_id': page_id,
    'url': verify.get('url'),
    'status': verify_props.get('Status',{}).get('select',{}).get('name'),
    'phase': verify_props.get('Phase',{}).get('select',{}).get('name'),
    'latest_safe_date': ''.join(x.get('plain_text','') for x in verify_props.get('Latest Safe Date',{}).get('rich_text',[])),
    'found_verification_texts': texts[-5:]
}, indent=2))
