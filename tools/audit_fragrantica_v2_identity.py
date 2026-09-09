import csv,re
from difflib import SequenceMatcher
from pathlib import Path

IN=Path('fragrantica-v2-audit.csv')
OUT=Path('fragrantica-v2-identity-audit.csv')
REPORT=Path('fragrantica-v2-identity-audit.md')

def norm(s):
    s=(s or '').lower()
    s=s.replace('&',' and ')
    s=re.sub(r'\b(eau de parfum|eau de toilette|edp|edt|perfume|parfum|for women|for men|pour homme|pour femme|woman|women|man|men)\b',' ',s)
    s=re.sub(r'[^a-z0-9]+',' ',s)
    return ' '.join(s.split())

def token_set(s): return set(norm(s).split())
def score(a,b):
    na,nb=norm(a),norm(b)
    if not na or not nb: return 0.0
    seq=SequenceMatcher(None,na,nb).ratio()
    ta,tb=token_set(a),token_set(b)
    jac=len(ta&tb)/len(ta|tb) if ta|tb else 0
    contain=1.0 if na in nb or nb in na else 0.0
    return max(seq,(seq+jac)/2,contain)

with IN.open(encoding='utf-8-sig',newline='') as f: rows=list(csv.DictReader(f))
counts={'PASS':0,'REVIEW':0,'NOT_MAPPED':0}
out=[]
for r in rows:
    if r.get('classification')!='VERIFIED':
        cls='NOT_MAPPED'; sc=0.0
    elif r.get('match_type')=='WEB_VERIFIED_FRAGRANTICA':
        # These mappings were already manually/web verified. Some legacy rows
        # intentionally have blank Fragrantica brand/perfume metadata, so a
        # name-only gate would create a guaranteed false REVIEW with score 0.
        cls='PASS'; sc=1.0
    else:
        sc=score(r.get('shobi_inspired_by',''),r.get('fragrantica_perfume',''))
        # Conservative: exact/containment or strong fuzzy identity only.
        cls='PASS' if sc>=0.78 else 'REVIEW'
    counts[cls]+=1
    q=dict(r); q['identity_score']=f'{sc:.4f}'; q['identity_gate']=cls; out.append(q)
with OUT.open('w',encoding='utf-8-sig',newline='') as f:
    w=csv.DictWriter(f,fieldnames=out[0].keys()); w.writeheader(); w.writerows(out)
review=[r for r in out if r['identity_gate']=='REVIEW']
lines=['# Fragrantica v2 identity consistency audit','',f'- Total master rows: **{len(rows)}**',f'- Existing code-level VERIFIED: **{sum(1 for r in rows if r.get("classification")=="VERIFIED")}**',f'- Identity PASS: **{counts["PASS"]}**',f'- Identity REVIEW: **{counts["REVIEW"]}**',f'- Not mapped: **{counts["NOT_MAPPED"]}**','','PASS requires conservative name identity similarity >= 0.78 after normalization, or an existing WEB_VERIFIED_FRAGRANTICA mapping. Nothing is promoted by this audit.','','## Identity review queue','']
for r in review:
    lines.append(f"- `{r['shobi_code']}` — Shobi `{r['shobi_inspired_by']}` ↔ Fragrantica `{r['fragrantica_perfume']}` (ID {r['fragrantica_id']}, score {r['identity_score']})")
REPORT.write_text('\n'.join(lines)+'\n',encoding='utf-8')
print(counts)
