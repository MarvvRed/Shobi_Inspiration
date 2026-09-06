import csv,json,re,unicodedata
from pathlib import Path

CSV=Path('fragrantica-v2-local-url-match.csv')
DIS=Path('fragrantica-v2-local-disambiguation.md')
URLS=Path('fragrantica-scraper-archive/legacy/original-local-scraper/perfume_urls.txt')
TARGETS=[Path('database_v2_clean.json'),Path('database_complete.json')]
REPORT=Path('fragrantica-v2-safe-promotion.md')

def norm(s):
    s=unicodedata.normalize('NFKD',str(s or '')).encode('ascii','ignore').decode().lower()
    return ' '.join(re.sub(r'[^a-z0-9]+',' ',s).split())

def walk(o):
    if isinstance(o,list):
        for x in o: yield from walk(x)
    elif isinstance(o,dict):
        if isinstance(o.get('perfumes'),list):
            for p in o['perfumes']:
                if isinstance(p,dict): yield p
        elif 'code' in o or 'inspiredBy' in o: yield o

selected={}
with CSV.open(encoding='utf-8-sig',newline='') as f:
    for r in csv.DictReader(f):
        if r.get('classification') not in {'STRONG_EXACT_BRAND','STRONG_UNIQUE'}: continue
        if not r.get('inferred_brand') or not r.get('cand1_id'): continue
        raw=r.get('shobi_name','')
        # Do not auto-promote when identity depended on removing a parenthetical qualifier.
        if '(' in raw or ')' in raw: continue
        exact=norm(r.get('match_name'))==norm(r.get('cand1_name'))
        try: seq=float(r.get('cand1_seq') or 0)
        except ValueError: seq=0
        # Exact within a coherent brand is safe; otherwise require very close spelling.
        if not exact and seq < 0.88: continue
        selected[r['shobi_code']]={
            'id':r['cand1_id'].strip(),'url':r.get('cand1_url','').strip(),
            'brand':r.get('cand1_brand','').strip(),'name':r.get('cand1_name','').strip(),
            'reason':'exact-brand' if exact else f'close-spelling-{seq:.4f}'
        }

# Add rows independently resolved by code-signature + perfume-name disambiguation.
if DIS.exists():
    text=DIS.read_text(encoding='utf-8')
    pat=re.compile(r"^- `([^`]+)` — .*? -> (.*?) / (.*?) — ID (\d+) — score ([0-9.]+), margin ([0-9.]+)",re.M)
    for code,brand,name,fid,score,margin in pat.findall(text):
        if float(score)>=0.90 and float(margin)>=0.08:
            selected[code]={'id':fid,'url':'','brand':brand,'name':name,'reason':f'code-name-disambiguated-{score}'}

# Recover exact local URL for every selected ID from the same repository-local corpus.
url_by_id={}
for line in URLS.read_text(encoding='utf-8',errors='ignore').splitlines():
    m=re.search(r'-(\d+)\.html(?:\?.*)?$',line.strip())
    if m and m.group(1) in {v['id'] for v in selected.values()}: url_by_id[m.group(1)]=line.strip()
for v in selected.values():
    if not v['url']: v['url']=url_by_id.get(v['id'],'')

stats=[]; promoted_codes=set(); skipped_verified=set()
for path in TARGETS:
    data=json.loads(path.read_text(encoding='utf-8-sig')); matched=changed=0
    for p in walk(data):
        code=str(p.get('code') or '').strip() or '[no-code]'; v=selected.get(code)
        if not v: continue
        matched+=1
        if str(p.get('fragranticaStatus') or '').startswith('VERIFIED_'):
            skipped_verified.add(code); continue
        p['fragranticaId']=v['id']
        p['fragranticaStatus']='VERIFIED_LOCAL_CORPUS_V2'
        p['fragranticaVerificationSource']='fragrantica-scraper-archive/legacy/original-local-scraper/perfume_urls.txt'
        p['fragranticaLocalUrl']=v['url']
        changed+=1; promoted_codes.add(code)
    path.write_text(json.dumps(data,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
    stats.append((str(path),matched,changed))

lines=['# Conservative v2 local-corpus promotion','',f'- Safe mappings selected: **{len(selected)}**',f'- Codes promoted in at least one target: **{len(promoted_codes)}**',f'- Already verified and left untouched: **{len(skipped_verified)}**']
for p,m,c in stats: lines.append(f'- `{p}`: matched **{m}**, changed **{c}**')
lines += ['','Policy: local corpus only; coherent brand required; exact name or >=0.88 sequence similarity; parenthetical-qualifier cases excluded; already verified rows never overwritten.','','## Selected mappings','']
for code,v in sorted(selected.items()): lines.append(f"- `{code}` -> {v['brand']} / {v['name']} — ID {v['id']} — {v['reason']}")
if skipped_verified:
    lines += ['','## Already verified / untouched','']+[f'- `{x}`' for x in sorted(skipped_verified)]
REPORT.write_text('\n'.join(lines)+'\n',encoding='utf-8')
print('selected',len(selected),'promoted',len(promoted_codes),'skipped_verified',len(skipped_verified),'stats',stats)
