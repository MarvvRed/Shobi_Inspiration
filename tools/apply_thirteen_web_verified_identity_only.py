#!/usr/bin/env python3
import json,re
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
DB=ROOT/'database/catalog/database_complete.json'
VERIFIED={
'2160-ZAR':'https://www.fragrantica.com/perfume/Zara/Barbie-83741.html',
'1989-VERT':'https://www.fragrantica.com/perfume/Vertus/Narcos-is-47923.html',
'1483-DSQ':'https://www.fragrantica.com/perfume/DSQUARED2/Potion-12937.html',
'989-YZLO':'https://www.fragrantica.com/perfume/Yves-Saint-Laurent/Rive-Gauche-96.html',
'987-YZLO':'https://www.fragrantica.com/perfume/Yves-Saint-Laurent/Paris-94.html',
'692-GUR':'https://www.fragrantica.com/perfume/Guerlain/Samsara-Eau-de-Parfum-55.html',
'666-GIV':'https://www.fragrantica.com/perfume/Givenchy/Dahlia-Divin-25972.html',
'621-EST':'https://www.fragrantica.com/perfume/Estee-Lauder/Bronze-Goddess-2011-11538.html',
'880-PRA':'https://www.fragrantica.com/perfume/Prada/Infusion-d-Oeillet-31045.html',
'769-LART':'https://www.fragrantica.com/perfume/L-Artisan-Parfumeur/Premier-Figuier-1261.html',
'1141-GIV':'https://www.fragrantica.com/perfume/Givenchy/Pi-39.html',
'1118-FAB':'https://www.fragrantica.com/perfume/Faberge/Brut-38206.html',
'476-CAL':'https://www.fragrantica.com/perfume/Calvin-Klein/CK-One-Summer-2016-35568.html',
}
def fid(url):
 m=re.search(r'-(\d+)\.html(?:$|[?#])',url); return m.group(1) if m else ''
def current_url_fid(url):
 s=str(url or '')
 m=re.search(r'-(\d+)\.html(?:$|[?#])',s) or re.search(r'/p/(\d+)(?:/?$|[?#])',s)
 return m.group(1) if m else ''
rows=json.loads(DB.read_text(encoding='utf-8-sig')); by={str(r.get('code') or '').strip().upper():r for r in rows}; changed=[]
for c,url in VERIFIED.items():
 r=by.get(c)
 if not r: raise SystemExit(f'Missing {c}')
 expected=fid(url)
 if str(r.get('fragranticaId') or '')!=expected: raise SystemExit(f'FID drift {c}: {r.get("fragranticaId")} != {expected}')
 if current_url_fid(r.get('fragranticaUrl'))!=expected: raise SystemExit(f'URL drift {c}: {r.get("fragranticaUrl")}')
 if str(r.get('identityStatus') or '').strip().upper() not in {'CONFIRMED','VERIFIED','VALIDATED','OK'}: raise SystemExit(f'Identity status {c}')
 r['fragranticaVerificationSource']=url
 r['fragranticaVerificationReason']='WEB_DIRECT_FRAGRANTICA_PAGE_NAME_BRAND_ID_VERIFIED_2026-09-14'
 r['fragranticaVerificationFragranticaId']=expected
 changed.append({'code':c,'fid':expected,'source':url})
DB.write_text(json.dumps(rows,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
(ROOT/'database/audits/thirteen-web-verified-identity-only.json').write_text(json.dumps({'changed':len(changed),'rows':changed},ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
print(json.dumps({'changed':len(changed),'codes':[x['code'] for x in changed]},ensure_ascii=False))
