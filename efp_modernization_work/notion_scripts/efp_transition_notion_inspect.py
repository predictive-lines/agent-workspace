import json, os, urllib.request
TOKEN=open(os.path.expanduser('~/.config/notion/api_key')).read().strip()
VER='2025-09-03'
TASK_DS='2847e702-d98c-8170-9008-000bc7d6d318'
ROOT='2ff7e702-d98c-80a9-bf01-d03635e5e5f4'

def req(method,path,payload=None):
    data=json.dumps(payload).encode() if payload is not None else None
    r=urllib.request.Request('https://api.notion.com/v1'+path,data=data,method=method)
    r.add_header('Authorization','Bearer '+TOKEN); r.add_header('Notion-Version',VER); r.add_header('Content-Type','application/json')
    with urllib.request.urlopen(r,timeout=30) as resp:
        return json.load(resp)

schema=req('GET',f'/data_sources/{TASK_DS}')
print('TASK SOURCE', schema.get('id'), schema.get('title'))
print('PROPS')
for k,v in schema['properties'].items(): print('-',k, v.get('type'), v.get(v.get('type'),{}))

# query likely EFP / Excel Fire / acquisition tasks
terms=['Excel Fire','EFP','Betty','Kevin','close','closing','purchase agreement','lender','personal financial statement','modernization']
seen={}
for term in terms:
    payload={'page_size':20,'filter':{'or':[
        {'property':'Task name','title':{'contains':term}},
        {'property':'Tags','multi_select':{'contains':term}}
    ]}}
    try:
        res=req('POST',f'/data_sources/{TASK_DS}/query',payload)
    except Exception as e:
        print('query fail',term,e); continue
    for p in res.get('results',[]):
        seen[p['id']]=p
print('MATCHES',len(seen))
for p in seen.values():
    props=p['properties']
    title=''.join(t['plain_text'] for t in props.get('Task name',{}).get('title',[]))
    status=props.get('Status',{}).get('status',{}).get('name') if props.get('Status',{}).get('status') else None
    pr=props.get('Priority',{}).get('select',{}).get('name') if props.get('Priority',{}).get('select') else None
    tags=[x['name'] for x in props.get('Tags',{}).get('multi_select',[])] if 'Tags' in props else []
    due=props.get('Due',{}).get('date')
    print(json.dumps({'id':p['id'],'title':title,'status':status,'priority':pr,'tags':tags,'due':due,'url':p.get('url')},ensure_ascii=False))
