import json,re
from pathlib import Path

TARGETS=[Path('database_v2_clean.json'),Path('database_complete.json')]
URLS=Path('fragrantica-scraper-archive/legacy/original-local-scraper/perfume_urls.txt')
REPORT=Path('fragrantica-v2-reviewed-promotion.md')

# Manually reviewed only against repository-local perfume_urls.txt and current local matcher ranking.
APPROVED={
    '1649-GIV':('62491','Givenchy','L Interdit Eau de Parfum Intense','same brand; full meaningful-name coverage'),
    '1996-LTN':('59485','Louis Vuitton','Heures d Absence','2020 row; local candidate clearly beats 1927 variant'),
    '2278-BLG':('145','Bvlgari','Eau Parfumee au The Blanc','same brand; Eau de Cologne is generic qualifier'),
    '204-CRD':('9828','Creed','Aventus','same brand; clear truncated spelling Avent -> Aventus'),
    '2142-PARF':('63100','Parfums de Marly','Pegasus Exclusif','same brand; Exclusive -> Exclusif spelling variant'),
    '2313-DRC':('56324','Dior','Sauvage Parfum','same brand; Shobi explicitly says Sauvage Parfum 2019'),
}

def walk(o):
    if isinstance(o,list):
        for x in o: yield from walk(x)
    elif isinstance(o,dict):
        if isinstance(o.get('perfumes'),list):
            for p in o['perfumes']:
                if isinstance(p,dict): yield p
        elif 'code' in o or 'inspiredBy' in o: yield o

need={v[0] for v in APPROVED.values()}; url_by_id={}
for line in URLS.read_text(encoding='utf-8',errors='ignore').splitlines():
    m=re.search(r'-(\d+)\.html(?:\?.*)?$',line.strip())
    if m and m.group(1) in need:url_by_id[m.group(1)]=line.strip()

stats=[]; promoted=set(); skipped=set()
for path in TARGETS:
    data=json.loads(path.read_text(encoding='utf-8-sig')); matched=changed=0
    for p in walk(data):
        code=str(p.get('code') or '').strip() or '[no-code]'
        if code not in APPROVED:continue
        matched+=1
        if str(p.get('fragranticaStatus') or '').startswith('VERIFIED_'):
            skipped.add(code); continue
        fid,brand,name,reason=APPROVED[code]
        if fid not in url_by_id:continue
        p['fragranticaId']=fid
        p['fragranticaStatus']='VERIFIED_LOCAL_CORPUS_V2'
        p['fragranticaVerificationSource']='fragrantica-scraper-archive/legacy/original-local-scraper/perfume_urls.txt'
        p['fragranticaLocalUrl']=url_by_id[fid]
        changed+=1; promoted.add(code)
    path.write_text(json.dumps(data,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
    stats.append((str(path),matched,changed))

lines=['# Reviewed v2 local-corpus promotion','',f'- Approved mappings: **{len(APPROVED)}**',f'- Promoted: **{len(promoted)}**',f'- Already verified / untouched: **{len(skipped)}**']
for p,m,c in stats:lines.append(f'- `{p}`: matched **{m}**, changed **{c}**')
lines += ['','No web verification. Every ID must exist in repository-local `perfume_urls.txt`.','','## Approved','']
for code,(fid,brand,name,reason) in APPROVED.items():lines.append(f'- `{code}` -> {brand} / {name} — ID {fid} — {reason}')
REPORT.write_text('\n'.join(lines)+'\n',encoding='utf-8')
print('approved',len(APPROVED),'promoted',len(promoted),'skipped',len(skipped),'stats',stats)
