#!/usr/bin/env python3
"""Find identity-only yellow rows whose exact Social Card visibly proves name + brand.
Read-only: no status/source changes.
"""
import csv, json, re, unicodedata
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]
DB=json.loads((ROOT/'database/catalog/database_complete.json').read_text(encoding='utf-8-sig'))
SITE=json.loads((ROOT/'database/catalog/catalog_site.json').read_text(encoding='utf-8-sig'))
GS=ROOT/'database/fragrantica'/'social-cards'/'gender-season.csv'

def norm(s):
    s=unicodedata.normalize('NFKD',str(s or '')).encode('ascii','ignore').decode().lower()
    s=s.replace('&',' and ')
    return ' '.join(re.findall(r'[a-z0-9]+',s))

STOP={'eau','de','du','des','la','le','les','the','by','for','pour','parfum','perfume','edp','edt','fragrance','fragrances','intense','spray'}
def toks(s): return [x for x in norm(s).split() if x not in STOP and len(x)>1]
def covered(need,hay): return bool(need) and all(t in hay for t in need)

with GS.open(encoding='utf-8-sig',newline='') as f:
    gs={str(x.get('shobi_code') or '').strip().upper():x for x in csv.DictReader(f)}

out=[]
for db,site in zip(DB,SITE):
    if str(site.get('validationStatus') or '').lower()!='yellow': continue
    failed=[k for k,v in (site.get('validationChecks') or {}).items() if not v]
    if failed!=['identity']: continue
    c=str(db.get('code') or '').strip().upper(); fid=str(db.get('fragranticaId') or '').strip()
    e=gs.get(c) or {}; ocr=norm(e.get('gender_ocr_text'))
    exact_id=bool(fid and str(e.get('fragrantica_id') or '').strip()==fid)
    card=str(e.get('local_path') or '').strip(); file_ok=bool(card and (ROOT/card).is_file())
    brand_tokens=toks(db.get('brand')); name_tokens=toks(db.get('inspiredBy'))
    brand_ok=covered(brand_tokens,ocr); name_ok=covered(name_tokens,ocr)
    b_hit=sum(t in ocr for t in brand_tokens); n_hit=sum(t in ocr for t in name_tokens)
    row={'code':c,'brand':db.get('brand'),'inspiredBy':db.get('inspiredBy'),'fragranticaId':fid,
      'fragranticaUrl':db.get('fragranticaUrl'),'card':card,'ocrText':e.get('gender_ocr_text'),
      'brandTokens':brand_tokens,'nameTokens':name_tokens,'brandHits':b_hit,'nameHits':n_hit,
      'exactId':exact_id,'fileExists':file_ok,'brandExactTokens':brand_ok,'nameExactTokens':name_ok,
      'strictProof':bool(exact_id and file_ok and brand_ok and name_ok)}
    out.append(row)

strict=[r for r in out if r['strictProof']]
remaining=[r for r in out if not r['strictProof']]
report={'identityOnlyRows':len(out),'strictSocialCardProof':len(strict),'strictCodes':[r['code'] for r in strict],'remainingRows':remaining,'rows':out}
(ROOT/'database/audits/identity-only-social-card-proof.json').write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
lines=['# Identity-only Social Card proof','',f'- Identity-only yellow rows: **{len(out)}**',f'- Strict exact-ID + local-card + all brand/name tokens visible: **{len(strict)}**','','## Strict proof rows','']
for r in strict: lines.append(f"- `{r['code']}` — {r['brand']} · {r['inspiredBy']} · FID {r['fragranticaId']} · `{r['card']}`")
lines += ['','## Remaining rows','']
for r in remaining:
    lines.append(f"- `{r['code']}` — {r['brand']} · {r['inspiredBy']} — FID **{r['fragranticaId']}** — {r['fragranticaUrl']} — brand {r['brandHits']}/{len(r['brandTokens'])}, name {r['nameHits']}/{len(r['nameTokens'])}")
(ROOT/'database/audits/identity-only-social-card-proof.md').write_text('\n'.join(lines)+'\n',encoding='utf-8')
print('identity_only',len(out),'strict_proof',len(strict),'remaining',len(remaining))
