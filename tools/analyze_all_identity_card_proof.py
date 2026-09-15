#!/usr/bin/env python3
import csv,json,re,unicodedata
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
DB=json.loads((ROOT/'database/catalog/database_complete.json').read_text(encoding='utf-8-sig'))
SITE=json.loads((ROOT/'database/catalog/catalog_site.json').read_text(encoding='utf-8-sig'))
GS=ROOT/'database/fragrantica'/'social-cards'/'gender-season.csv'

def norm(s):
 s=unicodedata.normalize('NFKD',str(s or '')).encode('ascii','ignore').decode().lower().replace('&',' and ')
 return ' '.join(re.findall(r'[a-z0-9]+',s))
STOP={'eau','de','du','des','la','le','les','the','by','for','pour','parfum','perfume','edp','edt','fragrance','fragrances','intense','spray'}
def toks(s):return [x for x in norm(s).split() if x not in STOP and len(x)>1]
def covered(need,hay):return bool(need) and all(t in hay for t in need)
def code(v):return str(v or '').strip().upper()
with GS.open(encoding='utf-8-sig',newline='') as f:gs={code(x.get('shobi_code')):x for x in csv.DictReader(f)}
rows=[]
for db,site in zip(DB,SITE):
 if str(site.get('validationStatus') or '').lower()!='yellow':continue
 checks=site.get('validationChecks') or {}
 if checks.get('identity',False):continue
 c=code(db.get('code'));fid=str(db.get('fragranticaId') or '').strip();e=gs.get(c) or {};ocr=norm(e.get('gender_ocr_text'));card=str(e.get('local_path') or '').strip()
 bt=toks(db.get('brand'));nt=toks(db.get('inspiredBy'))
 exact=bool(fid and str(e.get('fragrantica_id') or '').strip()==fid and card and (ROOT/card).is_file())
 bo=covered(bt,ocr);no=covered(nt,ocr)
 rows.append({'code':c,'brand':db.get('brand'),'inspiredBy':db.get('inspiredBy'),'fid':fid,'card':card,'ocr':e.get('gender_ocr_text'),'exactIdFile':exact,'brandTokens':bt,'nameTokens':nt,'brandHits':sum(t in ocr for t in bt),'nameHits':sum(t in ocr for t in nt),'strictProof':bool(exact and bo and no)})
strict=[r for r in rows if r['strictProof']]
out={'identityFailures':len(rows),'strictCardProof':len(strict),'strictCodes':[r['code'] for r in strict],'rows':rows}
(ROOT/'database/audits/all-identity-card-proof.json').write_text(json.dumps(out,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
lines=['# All remaining identity Social Card proof','',f'- Identity failures: **{len(rows)}**',f'- Strict exact-card proofs: **{len(strict)}**','','## Proven rows','']
for r in strict:lines.append(f"- `{r['code']}` — {r['brand']} · {r['inspiredBy']} · FID {r['fid']} · `{r['card']}`")
(ROOT/'database/audits/all-identity-card-proof.md').write_text('\n'.join(lines)+'\n',encoding='utf-8')
print('identity',len(rows),'strict',len(strict))
