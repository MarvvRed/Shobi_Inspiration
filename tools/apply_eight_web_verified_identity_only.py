#!/usr/bin/env python3
import json,re
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
DB=ROOT/'database/catalog/database_complete.json'
VERIFIED={
'2351-LOU':'https://www.fragrantica.com/perfume/Christian-Louboutin/Bikini-Questa-Sera-40982.html',
'2104-CHA':'https://www.fragrantica.com/perfume/Chanel/1957-Eau-de-Parfum-52483.html',
'667-GIV':'https://www.fragrantica.com/perfume/Givenchy/Dahlia-Noir-12146.html',
'533-DRC':'https://www.fragrantica.com/perfume/Dior/Midnight-Poison-1282.html',
'520-CHO':'https://www.fragrantica.com/perfume/Chopard/Wish-353.html',
'493-CER':'https://www.fragrantica.com/perfume/Cerruti/1881-327.html',
'1156-HER':'https://www.fragrantica.com/perfume/Hermes/Terre-d-Hermes-17.html',
'1136-ARM':'https://www.fragrantica.com/perfume/Giorgio-Armani/Emporio-Armani-Stronger-With-You-45258.html',
}
def fid(url):
    m=re.search(r'-(\d+)\.html(?:$|[?#])',url); return m.group(1) if m else ''
rows=json.loads(DB.read_text(encoding='utf-8-sig')); by={str(r.get('code') or '').strip().upper():r for r in rows}; changed=[]
for c,url in VERIFIED.items():
    r=by.get(c)
    if not r: raise SystemExit(f'Missing {c}')
    if str(r.get('fragranticaId') or '')!=fid(url): raise SystemExit(f'FID drift {c}')
    current=str(r.get('fragranticaUrl') or '').strip()
    current_id=fid(current) or (re.search(r'/p/(\d+)',current).group(1) if re.search(r'/p/(\d+)',current) else '')
    if current_id!=fid(url): raise SystemExit(f'URL drift {c}: {current}')
    if str(r.get('identityStatus') or '').strip().upper() not in {'CONFIRMED','VERIFIED','VALIDATED','OK'}: raise SystemExit(f'Identity status {c}')
    r['fragranticaVerificationSource']=url
    r['fragranticaVerificationReason']='WEB_DIRECT_FRAGRANTICA_PAGE_NAME_BRAND_ID_VERIFIED_2026-09-14'
    r['fragranticaVerificationFragranticaId']=fid(url)
    changed.append({'code':c,'fid':fid(url),'source':url})
DB.write_text(json.dumps(rows,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
(ROOT/'database/audits/eight-web-verified-identity-only.json').write_text(json.dumps({'changed':len(changed),'rows':changed},ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
print(json.dumps({'changed':len(changed),'codes':[x['code'] for x in changed]},ensure_ascii=False))
