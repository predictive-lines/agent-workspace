import json, os, urllib.request, urllib.error
TOKEN=open(os.path.expanduser('~/.config/notion/api_key')).read().strip(); VER='2025-09-03'
PAGE='35e7e702-d98c-81b3-9fd9-de314b16bf4e'
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
def rt(s): return {'rich_text':[{'type':'text','text':{'content':s}}]}
def sel(s): return {'select': {'name': s}}
def url(s): return {'url': s}

new_title='Flesh out revenue operating model with Kevin and Keith'
trigger='Kevin and Keith available for working sessions; target between PA signature and close if they will engage.'
latest='Before close if possible; otherwise first 30 days post-close. Do not wait until Kevin/Keith availability becomes constrained.'
notes=(
    'This is broader than estimating. Use Kevin + Keith sessions to document how revenue is generated, priced, scheduled, billed, and supported operationally. '
    'Cover: lead/source and bid/no-bid judgment; estimating methods and heuristics; material/labor buildup; Schedule 40/material suitability rules; dollars-per-head / dollars-per-square-foot shortcuts; GC/customer assumptions; margin/overhead rules; change-order judgment; how Kevin decides when and how much to invoice, including percent-complete / WIP / monthly billing cadence; what information Keith provides for billing readiness; and what team structure is needed to support roughly $3M revenue without overloading Kevin/Keith/Betty/Krissy. '
    'Output should be a revenue-process map and open-question list, not just an estimating SOP.'
)
res=req('PATCH',f'/pages/{PAGE}',{'properties':{
    'Name': title(new_title),
    'Workstream': sel('Operations'),
    'Priority': sel('High'),
    'Owner': sel('Justin'),
    'Source Type': sel('Pulled from modernization plan'),
    'Source URL': url(MOD_URL),
    'Trigger': rt(trigger),
    'Latest Safe Date': rt(latest),
    'Notes': rt(notes),
}})
print(json.dumps({'id':res['id'],'url':res.get('url'),'title':new_title},indent=2))
# verify
p=req('GET',f'/pages/{PAGE}')
props=p['properties']
print('verified title:', ''.join(x['plain_text'] for x in props['Name']['title']))
print('notes:', ''.join(x['plain_text'] for x in props['Notes']['rich_text'])[:500])
