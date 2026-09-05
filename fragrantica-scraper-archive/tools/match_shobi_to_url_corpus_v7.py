from __future__ import annotations

import csv, json, re, runpy, unicodedata
from collections import Counter, defaultdict
from difflib import SequenceMatcher
from pathlib import Path
from urllib.parse import unquote

HERE=Path(__file__).resolve().parent
ROOT=HERE.parents[1]
V6=HERE/'match_shobi_to_url_corpus_v6.py'
MAP=ROOT/'data/shobi-fragrantica-mapping.csv'
URLS=ROOT/'fragrantica-scraper-archive/legacy/original-local-scraper/perfume_urls.txt'
OUT=ROOT/'fragrantica-scraper-archive/corpus-match'
REPORT=OUT/'shobi-fragrantica-corpus-match.csv'; AMBIG=OUT/'ambiguous.csv'; UNMATCH=OUT/'unmatched.csv'; SUMMARY_JSON=OUT/'summary.json'; SUMMARY=OUT/'summary.md'

runpy.run_path(str(V6),run_name='__main__')

GENERIC={'by','parfum','parfums','perfume','perfumes','fragrance','fragrances','parfumeur','parfumerie','createur','the'}
QUAL={'intense','intensely','extrait','parfum','elixir','extreme','noir','rouge','sport','absolu','absolute','edition','limited','collector','edp','edt','edc'}

def norm(s):
    s=unquote((s or '').strip()).replace('&',' and ').replace('’',"'").replace('®','')
    s=unicodedata.normalize('NFKD',s); s=''.join(c for c in s if not unicodedata.combining(c)).lower().replace("'",' ')
    s=' '.join(re.sub(r'[^a-z0-9]+',' ',s).split())
    s=re.sub(r'\beau de parfum\b','edp',s); s=re.sub(r'\beau de toilette\b','edt',s); s=re.sub(r'\beau de cologne\b','edc',s)
    return s

def bcore(s):return ' '.join(t for t in norm(s).split() if t not in GENERIC)
def qset(s):return {t for t in norm(s).split() if t in QUAL}
def no_conc(s):return ' '.join(t for t in norm(s).split() if t not in {'edp','edt','edc'})
def read(p):
    with p.open('r',encoding='utf-8-sig',newline='') as f:return list(csv.DictReader(f))
def write(p,rows,fields):
    with p.open('w',encoding='utf-8-sig',newline='') as f:
        w=csv.DictWriter(f,fieldnames=fields,extrasaction='ignore');w.writeheader();w.writerows(rows)

def parse(u):
    m=re.match(r'^https?://(?:www\.)?fragrantica\.com/perfume/([^/]+)/(.+)-(\d+)\.html$',u.strip(),re.I)
    if not m:return None
    bs,ps,fid=m.groups(); b=unquote(bs).replace('-',' '); p=unquote(ps).replace('-',' ')
    return {'brand':b,'perfume':p,'bn':norm(b),'bc':bcore(b),'pn':norm(p),'id':fid,'url':u.strip()}

def uniq(rs):
    vals=list({(r['bn'],r['pn'],r['id']):r for r in rs}.values());return vals[0] if len(vals)==1 else None

mapping={r.get('shobi_code','').strip():r for r in read(MAP) if r.get('shobi_code','').strip()}
corpus=[]
with URLS.open('r',encoding='utf-8-sig',errors='replace') as f:
    for raw in f:
        r=parse(raw.strip())
        if r:corpus.append(r)
brands=defaultdict(list); brand_names=defaultdict(Counter)
for r in corpus:
    brands[r['bn']].append(r);brand_names[r['bn']][r['brand']]+=1

# Resolve mapping-brand spellings to corpus brands once.
brand_resolution={}
map_brands={norm(r.get('original_brand','')):r.get('original_brand','') for r in mapping.values() if r.get('original_brand','')}
for mbn,display in map_brands.items():
    if mbn in brands:brand_resolution[mbn]=mbn;continue
    mc=bcore(display); scored=[]
    for bn,rs in brands.items():
        bc=rs[0]['bc']
        if not mc or not bc:continue
        ratio=SequenceMatcher(None,mc,bc).ratio()
        # token containment is especially useful for brands like Stéphane Humbert Lucas vs ...777
        sm,sb=set(mc.split()),set(bc.split()); overlap=len(sm&sb)/max(1,min(len(sm),len(sb)))
        if ratio>=.83 or (overlap==1 and min(len(sm),len(sb))>=1):scored.append((max(ratio,overlap*.97),bn))
    scored.sort(reverse=True)
    if scored:
        top=scored[0][0];second=scored[1][0] if len(scored)>1 else 0
        if top>=.86 and top-second>=.04:brand_resolution[mbn]=scored[0][1]

rows=read(REPORT);fields=list(rows[0].keys()) if rows else []
rescued=0;methods=Counter(); unresolved_confirmed=0
for row in rows:
    if row.get('status')=='FOUND':continue
    m=mapping.get((row.get('shobi_code') or '').strip())
    if not m or (m.get('identity_status') or '').strip().upper()!='CONFIRMED':continue
    unresolved_confirmed+=1
    brand=(m.get('original_brand') or '').strip(); perfume=(m.get('original_perfume') or m.get('inspired_by') or '').strip()
    bn=brand_resolution.get(norm(brand),''); pn=norm(perfume)
    if not bn or not pn:continue
    pool=brands[bn]
    chosen=None;method='';score='';candidates=[]
    # exact normalized title
    candidates=[x for x in pool if x['pn']==pn]
    chosen=uniq(candidates)
    if chosen:method='CONFIRMED_IDENTITY_EXACT_CORPUS';score='1.0000'
    # exact after EDP/EDT concentration omission only when unique
    if not chosen:
        candidates=[x for x in pool if no_conc(x['pn'])==no_conc(pn)]
        chosen=uniq(candidates)
        if chosen:method='CONFIRMED_IDENTITY_CONCENTRATION_CORPUS';score='0.9950'
    # same-token title regardless order, preserving meaningful qualifiers
    if not chosen:
        candidates=[x for x in pool if set(x['pn'].split())==set(pn.split()) and qset(x['pn'])==qset(pn)]
        chosen=uniq(candidates)
        if chosen:method='CONFIRMED_IDENTITY_TOKEN_CORPUS';score='0.9900'
    # conservative fuzzy within already confirmed brand and identity
    if not chosen:
        scored=[]
        for x in pool:
            if qset(x['pn'])!=qset(pn):continue
            rr=SequenceMatcher(None,pn,x['pn']).ratio()
            if rr>=.87:scored.append((rr,x))
        scored.sort(key=lambda z:z[0],reverse=True)
        if scored:
            top=scored[0][0];second=scored[1][0] if len(scored)>1 else 0
            near=[z for z in scored if top-z[0]<.04]
            if top>=.90 and len(near)==1 and top-second>=.04:
                chosen=scored[0][1];method='CONFIRMED_IDENTITY_SAFE_FUZZY_CORPUS';score=f'{top:.4f}';candidates=[z[1] for z in scored]
    if chosen:
        row['status']='FOUND';row['match_type']=method;row['score']=score;row['candidate_count']=str(max(1,len(candidates)))
        row['fragrantica_brand']=chosen['brand'];row['fragrantica_perfume']=chosen['perfume'];row['fragrantica_id']=chosen['id'];row['fragrantica_url']=chosen['url']
        row['note']='Confirmed Shobi original identity matched against archived Fragrantica URL corpus'
        rescued+=1;methods[method]+=1

write(REPORT,rows,fields);write(AMBIG,[r for r in rows if r.get('status')=='AMBIGUOUS'],fields);write(UNMATCH,[r for r in rows if r.get('status') in {'NOT_FOUND','MAPPED_NOT_IN_CORPUS'}],fields)
summary=json.loads(SUMMARY_JSON.read_text(encoding='utf-8'));sc=Counter(r.get('status') or '' for r in rows);tc=Counter(r.get('match_type') or 'NONE' for r in rows)
summary['confirmed_identity_unresolved_before_v7']=unresolved_confirmed;summary['rescued_confirmed_identities_from_corpus_v7']=rescued;summary['v7_rescue_methods']=dict(methods);summary['resolved_mapping_brand_aliases']=len(brand_resolution)
summary['status_counts']=dict(sc);summary['match_type_counts']=dict(tc);summary['found_total']=sc.get('FOUND',0);summary['ambiguous_total']=sc.get('AMBIGUOUS',0);summary['not_found_total']=sc.get('NOT_FOUND',0);summary['mapped_not_in_corpus_total']=sc.get('MAPPED_NOT_IN_CORPUS',0)
SUMMARY_JSON.write_text(json.dumps(summary,indent=2,ensure_ascii=False)+'\n',encoding='utf-8');SUMMARY.write_text(f"# Shobi ↔ Fragrantica resolution\n\nFOUND: **{summary['found_total']}**\n\nAMBIGUOUS: **{summary['ambiguous_total']}**\n\nNOT_FOUND: **{summary['not_found_total']}**\n\nMAPPED_NOT_IN_CORPUS: **{summary['mapped_not_in_corpus_total']}**\n",encoding='utf-8')
print(json.dumps(summary,indent=2,ensure_ascii=False))
