#!/usr/bin/env python3
import json,re
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1];DB=ROOT/'database/catalog/database_complete.json'
VERIFIED={
'236-IND':'https://www.fragrantica.com/perfume/Indigo-Wild/Zum-Mist-Frankincense-Myrrh-42046.html',
'235-HOLL':'https://www.fragrantica.com/perfume/Hollister/Socal-4307.html',
'525-DRC':'https://www.fragrantica.com/perfume/Dior/Dune-221.html',
'487-CRT':'https://www.fragrantica.com/perfume/Cartier/Baiser-Vole-12878.html',
'421-BRB':'https://www.fragrantica.com/perfume/Burberry/Body-13014.html',
}
def fid(u):
 m=re.search(r'-(\d+)\.html(?:$|[?#])',u);return m.group(1) if m else ''
def urlfid(u):
 s=str(u or '');m=re.search(r'-(\d+)\.html(?:$|[?#])',s) or re.search(r'/p/(\d+)',s);return m.group(1) if m else ''
rows=json.loads(DB.read_text(encoding='utf-8-sig'));by={str(x.get('code') or '').strip().upper():x for x in rows};out=[]
for c,u in VERIFIED.items():
 r=by.get(c);f=fid(u)
 if not r or str(r.get('fragranticaId') or '')!=f or urlfid(r.get('fragranticaUrl'))!=f:raise SystemExit(f'drift {c}')
 if str(r.get('identityStatus') or '').upper()!='CONFIRMED':raise SystemExit(f'identity status {c}')
 r['fragranticaVerificationSource']=u;r['fragranticaVerificationReason']='WEB_DIRECT_FRAGRANTICA_PAGE_NAME_BRAND_ID_VERIFIED_2026-09-14';r['fragranticaVerificationFragranticaId']=f;out.append({'code':c,'fid':f,'source':u})
DB.write_text(json.dumps(rows,ensure_ascii=False,indent=2)+'\n',encoding='utf-8');(ROOT/'database/audits/five-known-fid-identity-proofs.json').write_text(json.dumps({'changed':len(out),'rows':out},ensure_ascii=False,indent=2)+'\n',encoding='utf-8');print(json.dumps({'changed':len(out)},ensure_ascii=False))
