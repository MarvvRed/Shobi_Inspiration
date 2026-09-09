import csv,re
from difflib import SequenceMatcher
from pathlib import Path

IN=Path('fragrantica-v2-audit.csv')
OUT=Path('fragrantica-v2-identity-audit.csv')
REPORT=Path('fragrantica-v2-identity-audit.md')

# REVIEW rows manually closed by checking the Shobi identity against the exact
# Fragrantica perfume/FID. This is deliberately identity-only: Main Notes stay
# frozen and these overrides do not promote NOT_MAPPED rows.
MANUAL_IDENTITY_PASS={
    '105-ARB',   # Prestige Classic Arabian Oud -> Arabian Prestige Classic 21602
    '302-JOM',   # Wisteria & Violet (London Rain) Jo Malone -> 22503
    '632-EST',   # Private Collection Jasmin White Moss Estee Lauder -> 6066
    '732-JIM',   # Shobi product currently labelled Jimmy Choo, exact source = Flash -> 17223
    '734-JIM',   # Jimmy Choo Eau de Parfum -> Jimmy Choo 10573
    '842-NRO',   # For Her Black EDP -> Narciso Rodriguez for Her EDP -> 14319
    '1023-BOT',  # Bottega Veneta Pour Homme Extreme -> 29351
    '1164-HUG',  # Hugo Boss Elements -> Boss Elements -> 571
    '1655-JOM',  # Jo Malone Oat & Cornflower -> 48318
    '1731-VICT', # Victoria's Secret Tease Creme Cloud -> 68550
    '2122-GUR',  # Guerlain Rosa Rossa Harvest -> 79472
    '2142-PARF', # Parfums de Marly Pegasus Exclusif -> 63100
    '2185-DRC',  # Dior Eau Sauvage Extreme 2010 -> 72771
    '2344-LEL',  # Le Labo Mousse de Chene 30 Amsterdam -> 46295
    '2609-TMFO', # Tom Ford Opaline Hyacinth / Ombre de Hyacinth -> 15916
}

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
    elif r.get('match_type')=='WEB_VERIFIED_FRAGRANTICA' or r.get('shobi_code') in MANUAL_IDENTITY_PASS:
        # WEB_VERIFIED rows were already checked earlier. MANUAL_IDENTITY_PASS
        # contains REVIEW cases explicitly closed against Shobi + exact FID.
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
lines=['# Fragrantica v2 identity consistency audit','',f'- Total master rows: **{len(rows)}**',f'- Existing code-level VERIFIED: **{sum(1 for r in rows if r.get("classification")=="VERIFIED")}**',f'- Identity PASS: **{counts["PASS"]}**',f'- Identity REVIEW: **{counts["REVIEW"]}**',f'- Not mapped: **{counts["NOT_MAPPED"]}**','','PASS requires conservative name identity similarity >= 0.78 after normalization, an existing WEB_VERIFIED_FRAGRANTICA mapping, or explicit manual identity verification against Shobi + exact Fragrantica FID. Nothing is promoted from NOT_MAPPED by this audit.','','## Identity review queue','']
for r in review:
    lines.append(f"- `{r['shobi_code']}` — Shobi `{r['shobi_inspired_by']}` ↔ Fragrantica `{r['fragrantica_perfume']}` (ID {r['fragrantica_id']}, score {r['identity_score']})")
REPORT.write_text('\n'.join(lines)+'\n',encoding='utf-8')
print(counts)
