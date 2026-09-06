import csv,json
from pathlib import Path

IDENT=Path('fragrantica-v2-identity-audit.csv')
WEB=Path('data/fragrantica-v2-web-verified.csv')
TARGETS=[Path('database_complete.json'),Path('database_v2_clean.json')]
REPORT=Path('fragrantica-v2-promotion.md')

verified={}
with IDENT.open(encoding='utf-8-sig',newline='') as f:
    for r in csv.DictReader(f):
        if r.get('identity_gate')=='PASS' and r.get('fragrantica_id'):
            verified[r['shobi_code']]={
                'id':str(r['fragrantica_id']).strip(),
                'status':'VERIFIED_ARCHIVE_IDENTITY_V2',
                'source':'fragrantica-v2-identity-audit.csv'
            }
with WEB.open(encoding='utf-8-sig',newline='') as f:
    for r in csv.DictReader(f):
        if r.get('status')=='VERIFIED_WEB_V2' and r.get('fragrantica_id'):
            verified[r['shobi_code']]={
                'id':str(r['fragrantica_id']).strip(),
                'status':'VERIFIED_WEB_V2',
                'source':r.get('verification_source','')
            }

def walk(obj):
    if isinstance(obj,list):
        for x in obj: yield from walk(x)
    elif isinstance(obj,dict):
        if 'perfumes' in obj and isinstance(obj['perfumes'],list):
            for p in obj['perfumes']:
                if isinstance(p,dict): yield p
        elif 'code' in obj or 'id' in obj:
            yield obj

stats=[]
for path in TARGETS:
    data=json.loads(path.read_text(encoding='utf-8-sig'))
    changed=0; matched=0
    for p in walk(data):
        code=str(p.get('code') or '').strip()
        if code in verified:
            matched+=1
            v=verified[code]
            before=(p.get('fragranticaId'),p.get('fragranticaStatus'))
            p['fragranticaId']=v['id']
            p['fragranticaStatus']=v['status']
            p['fragranticaVerificationSource']=v['source']
            if before!=(p.get('fragranticaId'),p.get('fragranticaStatus')): changed+=1
    path.write_text(json.dumps(data,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
    stats.append((str(path),matched,changed))

archive_count=sum(1 for v in verified.values() if v['status']=='VERIFIED_ARCHIVE_IDENTITY_V2')
web_count=sum(1 for v in verified.values() if v['status']=='VERIFIED_WEB_V2')
lines=['# Fragrantica v2 verified promotion','',f'- Archive exact-code + identity PASS promoted: **{archive_count}**',f'- Direct web-verified residual mappings promoted: **{web_count}**',f'- Total verified code mappings available: **{len(verified)}**','']
for path,matched,changed in stats:
    lines.append(f'- `{path}`: matched **{matched}**, changed **{changed}**')
lines += ['','No gender, season, notes or image data is copied by this promotion. Only verified Fragrantica IDs/status/evidence are written.']
REPORT.write_text('\n'.join(lines)+'\n',encoding='utf-8')
print('archive',archive_count,'web',web_count,'total',len(verified),'stats',stats)
