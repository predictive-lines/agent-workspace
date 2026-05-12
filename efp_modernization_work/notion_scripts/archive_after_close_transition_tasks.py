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

res=req('POST',f'/data_sources/{DS}/query',{'page_size':100,'filter':{'property':'Phase','select':{'equals':'After Close'}}})
archived=[]
for p in res.get('results',[]):
    title=''.join(x.get('plain_text','') for x in p['properties'].get('Name',{}).get('title',[]))
    req('PATCH',f'/pages/{p["id"]}',{'archived': True})
    archived.append({'id':p['id'],'title':title})
print(json.dumps({'archived':archived,'count':len(archived)},indent=2))
# verify no after close remain visible
res2=req('POST',f'/data_sources/{DS}/query',{'page_size':100,'filter':{'property':'Phase','select':{'equals':'After Close'}}})
print(json.dumps({'remaining_visible_after_close':len(res2.get('results',[]))},indent=2))
