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
    '246-JOM',   # Jo Malone Bronze Wood & Leather -> Bronze Wood Leather 52803
    '268-JOM',   # Jo Malone Myrrh & Tonka -> Myrrh Tonka 42027
    '276-JOM',   # Jo Malone Oud & Bergamot -> Oud Bergamot 12928
    '299-JOM',   # Jo Malone White Lilac & Rhubarb -> White Lilac Rhubarb 14134
    '302-JOM',   # Wisteria & Violet (London Rain) Jo Malone -> 22503
    '315-MNT',   # Montale Aoud Orange -> Orange Aoud 23365
    '407-BAT',   # Bath & Body Works Pink Amber & Morocco Orchid -> 25388
    '417-BOUR',  # Bourjois Soir de Paris / Evening in Paris -> 3604
    '438-BLG',   # Bvlgari Omnia Coral / Coral Omnia -> 14297
    '580-DON',   # DKNY Golden Delicious -> 10914
    '632-EST',   # Private Collection Jasmin White Moss Estee Lauder -> 6066
    '732-JIM',   # Shobi product currently labelled Jimmy Choo, exact source = Flash -> 17223
    '734-JIM',   # Jimmy Choo Eau de Parfum -> Jimmy Choo 10573
    '834-MOS',   # Moschino Cheap & Chic So Real / So Real Cheap Chic -> 46867
    '842-NRO',   # For Her Black EDP -> Narciso Rodriguez for Her EDP -> 14319
    '1023-BOT',  # Bottega Veneta Pour Homme Extreme -> 29351
    '1031-BRB',  # Burberry Brit Rhythm / Rhythm Brit -> 18903
    '1063-CER',  # Cerruti Pour Homme -> 1441
    '1164-HUG',  # Hugo Boss Elements -> Boss Elements -> 571
    '1204-LOE',  # Loewe Solo Cedro -> Solo Loewe Cedro 30321
    '1495-BRB',  # Burberry Her London Dream -> 60795
    '1542-JOM',  # Jo Malone English Oak & Redcurrant -> 46186
    '1655-JOM',  # Jo Malone Oat & Cornflower -> 48318
    '1731-VICT', # Victoria's Secret Tease Creme Cloud -> 68550
    '1754-HER',  # Hermes Hermessence Vanille Galante -> 5213
    '1802-JOM',  # Jo Malone Midnight Musk & Amber -> 63920
    '1826-JOM',  # Jo Malone Iris & White Musk -> 12926
    '1827-JOM',  # Jo Malone Tropical Cherimoya -> Tropical Cherimoya Cologne 49602
    '1919-PRA',  # Prada Paradoxe -> 75668
    '1942-LAN',  # Lancome Idole Nectar -> 74137
    '1978-ARM',  # Armani Stronger With You Intensely -> 52802
    '2095-VICT', # Victoria's Secret Strawberries & Champagne -> 8000
    '2122-GUR',  # Guerlain Rosa Rossa Harvest -> 79472
    '2142-PARF', # Parfums de Marly Pegasus Exclusif -> 63100
    '2185-DRC',  # Dior Eau Sauvage Extreme 2010 -> 72771
    '2278-BLG',  # Bvlgari Eau Parfumee au The Blanc -> 145
    '2344-LEL',  # Le Labo Mousse de Chene 30 Amsterdam -> 46295
    '2516-GUL',  # Jean Paul Gaultier Scandal Pour Homme Absolu -> 91053
    '2543-HUG',  # Boss The Scent For Him Magnetic -> 78424
    '2609-TMFO', # Tom Ford Opaline Hyacinth / Ombre de Hyacinth -> 15916
    '2627-LTN',  # Louis Vuitton Meteore -> 62251
    '2785-VAL',  # Valentino Born in Roma Extradose Donna -> 101384
    '2802-HER',  # Hermes Terre d'Hermes Intense -> 102772
    '2829-PARF', # Parfums de Marly Athenais -> 123716
    '2837-GUL',  # Jean Paul Gaultier Scandal Pour Homme Elixir -> 121453
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
        cls='PASS'; sc=1.0
    else:
        sc=score(r.get('shobi_inspired_by',''),r.get('fragrantica_perfume',''))
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
