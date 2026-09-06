import csv,json
from pathlib import Path

SRC=Path('fragrantica-v2-local-id-reconciliation.csv')
TARGETS=[Path('database_complete.json'),Path('database_v2_clean.json')]
REPORT=Path('fragrantica-v2-local-promotion.md')

confirmed={}
with SRC.open(encoding='utf-8-sig',newline='') as f:
    for r in csv.DictReader(f):
        if r.get('classification')=='HIST_ID_CONFIRMED_LOCAL' and r.get('historical_id'):
            confirmed[r['shobi_code']]={
                'id':r['historical_id'].strip(),
                'url':r.get('historical_local_url','').strip(),
                'name':r.get('historical_local_name','').strip(),
                'brand':r.get('historical_local_brand','').strip(),
            }

def walk(o):
    if isinstance(o,list):
        for x in o: yield from walk(x)
    elif isinstance(o,dict):
        if 'perfumes' in o and isinstance(o['perfumes'],list):
            for p in o['perfumes']:
                if isinstance(p,dict): yield p
        elif 'code' in o or 'inspiredBy' in o: yield o

stats=[]
for path in TARGETS:
    data=json.loads(path.read_text(encoding='utf-8-sig'))
    matched=changed=0
    for p in walk(data):
        code=str(p.get('code') or '').strip() or '[no-code]'
        v=confirmed.get(code)
        if not v: continue
        matched+=1
        before=(p.get('fragranticaId'),p.get('fragranticaStatus'))
        p['fragranticaId']=v['id']
        p['fragranticaStatus']='VERIFIED_LOCAL_CORPUS_V2'
        p['fragranticaVerificationSource']='fragrantica-scraper-archive/legacy/original-local-scraper/perfume_urls.txt'
        p['fragranticaLocalUrl']=v['url']
        if before!=(p.get('fragranticaId'),p.get('fragranticaStatus')): changed+=1
    path.write_text(json.dumps(data,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
    stats.append((str(path),matched,changed))

lines=['# Fragrantica v2 local-corpus promotion','',f'- Confirmed mappings promoted: **{len(confirmed)}**']
for p,m,c in stats: lines.append(f'- `{p}`: matched **{m}**, changed **{c}**')
lines += ['','Source: repository-local `perfume_urls.txt`. No web verification is used in this promotion.']
REPORT.write_text('\n'.join(lines)+'\n',encoding='utf-8')
print('confirmed',len(confirmed),'stats',stats)
