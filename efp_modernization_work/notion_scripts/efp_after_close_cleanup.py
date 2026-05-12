import json, os, urllib.request, urllib.error
TOKEN=open(os.path.expanduser('~/.config/notion/api_key')).read().strip(); VER='2025-09-03'
DS='0349d6f1-82c7-48eb-8acf-42ac7ce35064'

def req(m,p,payload=None):
    data=json.dumps(payload).encode() if payload is not None else None
    r=urllib.request.Request('https://api.notion.com/v1'+p,data=data,method=m)
    r.add_header('Authorization','Bearer '+TOKEN); r.add_header('Notion-Version',VER); r.add_header('Content-Type','application/json')
    try:
        with urllib.request.urlopen(r,timeout=30) as resp: return json.load(resp)
    except urllib.error.HTTPError as e:
        raise RuntimeError(f'{m} {p} -> {e.code}: {e.read().decode()}')

payload={'page_size':100,'filter':{'property':'Phase','select':{'equals':'After Close'}}}
res=req('POST',f'/data_sources/{DS}/query',payload)
print(json.dumps({'count':len(res.get('results',[]))},indent=2))
items=[]
for p in res.get('results',[]):
    props=p['properties']
    def title(name): return ''.join(x.get('plain_text','') for x in props.get(name,{}).get('title',[]))
    def sel(name):
        v=props.get(name,{}).get('select')
        return v.get('name') if v else None
    def rt(name): return ''.join(x.get('plain_text','') for x in props.get(name,{}).get('rich_text',[]))
    items.append({'id':p['id'],'url':p.get('url'),'task':title('Name'),'status':sel('Status'),'phase':sel('Phase'),'workstream':sel('Workstream'),'source_type':sel('Source Type'),'source_url':props.get('Source URL',{}).get('url'),'notes':rt('Notes')})
print(json.dumps(items,indent=2,ensure_ascii=False))
