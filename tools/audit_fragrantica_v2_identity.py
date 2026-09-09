import csv,re
from difflib import SequenceMatcher
from pathlib import Path

IN=Path('fragrantica-v2-audit.csv')
OUT=Path('fragrantica-v2-identity-audit.csv')
REPORT=Path('fragrantica-v2-identity-audit.md')
UNMAPPED=Path('fragrantica-v2-unmapped.csv')

# REVIEW rows manually closed by checking the Shobi identity against the exact
# Fragrantica perfume/FID. This is deliberately identity-only: Main Notes stay
# frozen and these overrides do not promote NOT_MAPPED rows.
MANUAL_IDENTITY_PASS={
    '105-ARB','246-JOM','268-JOM','276-JOM','299-JOM','302-JOM','315-MNT','407-BAT','417-BOUR','438-BLG','580-DON','632-EST','732-JIM','734-JIM','834-MOS','842-NRO','1023-BOT','1031-BRB','1063-CER','1164-HUG','1204-LOE','1495-BRB','1542-JOM','1655-JOM','1731-VICT','1754-HER','1802-JOM','1826-JOM','1827-JOM','1919-PRA','1942-LAN','1978-ARM','2095-VICT','2122-GUR','2142-PARF','2185-DRC','2278-BLG','2344-LEL','2516-GUL','2543-HUG','2609-TMFO','2627-LTN','2785-VAL','2802-HER','2829-PARF','2837-GUL',
}

def norm(s):
    s=(s or '').lower().replace('&',' and ')
    s=re.sub(r'\b(eau de parfum|eau de toilette|edp|edt|perfume|parfum|for women|for men|pour homme|pour femme|woman|women|man|men)\b',' ',s)
    s=re.sub(r'[^a-z0-9]+',' ',s)
    return ' '.join(s.split())
def token_set(s): return set(norm(s).split())
def score(a,b):
    na,nb=norm(a),norm(b)
    if not na or not nb: return 0.0
    seq=SequenceMatcher(None,na,nb).ratio(); ta,tb=token_set(a),token_set(b)
    jac=len(ta&tb)/len(ta|tb) if ta|tb else 0; contain=1.0 if na in nb or nb in na else 0.0
    return max(seq,(seq+jac)/2,contain)

with IN.open(encoding='utf-8-sig',newline='') as f: rows=list(csv.DictReader(f))
counts={'PASS':0,'REVIEW':0,'NOT_MAPPED':0}; out=[]
for r in rows:
    if r.get('classification')!='VERIFIED': cls='NOT_MAPPED'; sc=0.0
    elif r.get('match_type')=='WEB_VERIFIED_FRAGRANTICA' or r.get('shobi_code') in MANUAL_IDENTITY_PASS: cls='PASS'; sc=1.0
    else:
        sc=score(r.get('shobi_inspired_by',''),r.get('fragrantica_perfume','')); cls='PASS' if sc>=0.78 else 'REVIEW'
    counts[cls]+=1; q=dict(r); q['identity_score']=f'{sc:.4f}'; q['identity_gate']=cls; out.append(q)
with OUT.open('w',encoding='utf-8-sig',newline='') as f:
    w=csv.DictWriter(f,fieldnames=out[0].keys()); w.writeheader(); w.writerows(out)
unmapped=[r for r in out if r['identity_gate']=='NOT_MAPPED']
with UNMAPPED.open('w',encoding='utf-8-sig',newline='') as f:
    fields=['shobi_code','prestashop_product_id','shobi_inspired_by','classification','reason','match_type']
    w=csv.DictWriter(f,fieldnames=fields,extrasaction='ignore'); w.writeheader(); w.writerows(unmapped)
review=[r for r in out if r['identity_gate']=='REVIEW']
lines=['# Fragrantica v2 identity consistency audit','',f'- Total master rows: **{len(rows)}**',f'- Existing code-level VERIFIED: **{sum(1 for r in rows if r.get("classification")=="VERIFIED")}**',f'- Identity PASS: **{counts["PASS"]}**',f'- Identity REVIEW: **{counts["REVIEW"]}**',f'- Not mapped: **{counts["NOT_MAPPED"]}**','','PASS requires conservative name identity similarity >= 0.78 after normalization, an existing WEB_VERIFIED_FRAGRANTICA mapping, or explicit manual identity verification against Shobi + exact Fragrantica FID. Nothing is promoted from NOT_MAPPED by this audit.','','## Identity review queue','']
for r in review: lines.append(f"- `{r['shobi_code']}` — Shobi `{r['shobi_inspired_by']}` ↔ Fragrantica `{r['fragrantica_perfume']}` (ID {r['fragrantica_id']}, score {r['identity_score']})")
REPORT.write_text('\n'.join(lines)+'\n',encoding='utf-8')
print(counts, 'unmapped export', len(unmapped))
