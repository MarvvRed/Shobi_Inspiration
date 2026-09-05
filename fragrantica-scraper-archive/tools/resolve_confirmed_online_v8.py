from __future__ import annotations

import csv, html, json, os, re, time, unicodedata
from collections import Counter
from difflib import SequenceMatcher
from pathlib import Path
from urllib.parse import quote_plus, unquote, urlparse
from urllib.request import Request, urlopen

ROOT=Path(__file__).resolve().parents[2]
MAP=ROOT/'data/shobi-fragrantica-mapping.csv'
REPORT=ROOT/'fragrantica-scraper-archive/corpus-match/shobi-fragrantica-corpus-match.csv'
AMBIG=ROOT/'fragrantica-scraper-archive/corpus-match/ambiguous.csv'
UNMATCH=ROOT/'fragrantica-scraper-archive/corpus-match/unmatched.csv'
SUMMARY_JSON=ROOT/'fragrantica-scraper-archive/corpus-match/summary.json'
CHECKPOINT=ROOT/'fragrantica-scraper-archive/corpus-match/online-resolution-v8.csv'
MAX_ROWS=int(os.environ.get('ONLINE_RESOLVE_MAX','220'))
TIMEOUT=float(os.environ.get('ONLINE_RESOLVE_TIMEOUT','6'))
DELAY=float(os.environ.get('ONLINE_RESOLVE_DELAY','0.10'))
UA='Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 Chrome/152 Safari/537.36'
QUAL={'intense','intensely','extrait','parfum','elixir','extreme','noir','rouge','sport','absolu','absolute','edition','limited','collector'}
FIELDS=['shobi_code','brand','perfume','result','fragrantica_id','fragrantica_url','candidate_brand','candidate_perfume','score','provider','note']

def norm(s):
    s=unquote((s or '').strip()).replace('&',' and ').replace('’',"'").replace('®','')
    s=unicodedata.normalize('NFKD',s);s=''.join(c for c in s if not unicodedata.combining(c)).lower().replace("'",' ')
    s=' '.join(re.sub(r'[^a-z0-9]+',' ',s).split())
    s=re.sub(r'\beau de parfum\b','edp',s);s=re.sub(r'\beau de toilette\b','edt',s);s=re.sub(r'\beau de cologne\b','edc',s)
    return s

def qset(s):return {t for t in norm(s).split() if t in QUAL}
def core_brand(s):return ' '.join(t for t in norm(s).split() if t not in {'by','parfum','parfums','perfume','perfumes','fragrance','fragrances','the','prive','prives','777'})
def read_csv(p):
    if not p.exists():return []
    with p.open('r',encoding='utf-8-sig',newline='') as f:return list(csv.DictReader(f))
def write_csv(p,rows,fields):
    with p.open('w',encoding='utf-8-sig',newline='') as f:
        w=csv.DictWriter(f,fieldnames=fields,extrasaction='ignore');w.writeheader();w.writerows(rows)
def fetch(url):
    req=Request(url,headers={'User-Agent':UA,'Accept':'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8','Accept-Language':'en-US,en;q=0.9'})
    with urlopen(req,timeout=TIMEOUT) as r:return r.read(2_500_000).decode('utf-8',errors='replace')
def extract(page):
    page=html.unescape(page).replace('\\/','/')
    urls=[]
    pats=[r'https?://(?:www\.)?fragrantica\.com/perfume/[^"\'<>\s&]+',r'href=["\']([^"\']*?/perfume/[^"\']+)["\']']
    for pi,pat in enumerate(pats):
        for m in re.finditer(pat,page,re.I):
            u=m.group(0) if pi==0 else m.group(1)
            u=unquote(u)
            if u.startswith('/'):u='https://www.fragrantica.com'+u
            mm=re.search(r'https?://(?:www\.)?fragrantica\.com/perfume/[^?#"\'<>\s&]+',u,re.I)
            if mm:
                v=mm.group(0).rstrip('.,);]')
                if v not in urls:urls.append(v)
    return urls[:30]
def parse(u):
    p=urlparse(u);parts=[unquote(x) for x in p.path.split('/') if x]
    if len(parts)<3 or parts[0].lower()!='perfume':return None
    m=re.match(r'(.+)-(\d+)\.html$',parts[-1],re.I)
    if not m:return None
    ps,fid=m.groups();return {'id':fid,'url':'https://www.fragrantica.com'+p.path,'brand':parts[1].replace('-',' '),'perfume':ps.replace('-',' ')}
def score(brand,perfume,c):
    b,b2=core_brand(brand),core_brand(c['brand']);p,p2=norm(perfume),norm(c['perfume'])
    bseq=SequenceMatcher(None,b,b2).ratio();pseq=SequenceMatcher(None,p,p2).ratio()
    bt,ct=set(b.split()),set(b2.split());pt,qt=set(p.split()),set(p2.split())
    bcov=len(bt&ct)/max(1,min(len(bt),len(ct)));pcov=len(pt&qt)/max(1,len(pt));rev=len(pt&qt)/max(1,len(qt))
    total=.30*max(bseq,bcov)+.42*pseq+.20*pcov+.08*rev
    return total,max(bseq,bcov),pseq,pcov
def provider_pages(brand,perfume):
    q=f'{brand} {perfume}'
    yield 'fragrantica-search','https://www.fragrantica.com/search/?query='+quote_plus(q)
    sq=f'site:fragrantica.com/perfume "{brand}" "{perfume}"'
    yield 'bing-rss','https://www.bing.com/search?format=rss&q='+quote_plus(sq)
    yield 'bing','https://www.bing.com/search?q='+quote_plus(sq)
def resolve(brand,perfume):
    links=[];used=[]
    for provider,url in provider_pages(brand,perfume):
        try:
            found=extract(fetch(url));used.append(f'{provider}:{len(found)}')
            for u in found:
                if u not in links:links.append(u)
            if len(links)>=8:break
        except Exception as e:used.append(f'{provider}:ERR:{type(e).__name__}')
        time.sleep(DELAY)
    scored=[]
    for u in links:
        c=parse(u)
        if not c:continue
        s,bs,ps,pc=score(brand,perfume,c);c.update(score=s,bscore=bs,pseq=ps,pcov=pc);scored.append(c)
    scored.sort(key=lambda x:x['score'],reverse=True)
    if not scored:return None,'|'.join(used),'no candidates'
    best=scored[0];second=scored[1]['score'] if len(scored)>1 else 0;margin=best['score']-second
    exact=norm(perfume)==norm(best['perfume'])
    qualifiers_ok=qset(perfume)==qset(best['perfume'])
    ok=best['bscore']>=.78 and qualifiers_ok and ((exact and best['score']>=.80) or (best['pseq']>=.91 and best['pcov']>=.75 and best['score']>=.84 and (margin>=.045 or best['score']>=.94)))
    if ok:return best,'|'.join(used),f'accepted margin={margin:.3f}'
    return None,'|'.join(used),f"weak best={best['score']:.3f} brand={best['bscore']:.3f} name={best['pseq']:.3f} cov={best['pcov']:.3f} second={second:.3f}"

mapping={r.get('shobi_code','').strip():r for r in read_csv(MAP) if r.get('shobi_code','').strip()}
report=read_csv(REPORT);fields=list(report[0].keys()) if report else []
checkpoint=read_csv(CHECKPOINT);bycode={r.get('shobi_code','').strip():r for r in checkpoint if r.get('shobi_code','').strip()}
# Merge already-found checkpoint results first, because v7 reconstructs report from scratch every run.
for row in report:
    if row.get('status')=='FOUND':continue
    cp=bycode.get((row.get('shobi_code') or '').strip())
    if cp and cp.get('result')=='FOUND':
        row.update(status='FOUND',match_type='CONFIRMED_IDENTITY_ONLINE',score=cp.get('score',''),candidate_count='1',fragrantica_brand=cp.get('candidate_brand',''),fragrantica_perfume=cp.get('candidate_perfume',''),fragrantica_id=cp.get('fragrantica_id',''),fragrantica_url=cp.get('fragrantica_url',''),note='Confirmed identity resolved online against Fragrantica')

attempted=found=0
for row in report:
    if row.get('status')=='FOUND':continue
    code=(row.get('shobi_code') or '').strip();m=mapping.get(code)
    if not m or (m.get('identity_status') or '').strip().upper()!='CONFIRMED':continue
    if code in bycode:continue
    if attempted>=MAX_ROWS:break
    brand=(m.get('original_brand') or '').strip();perfume=(m.get('original_perfume') or m.get('inspired_by') or '').strip()
    if not brand or not perfume:continue
    attempted+=1
    try:best,providers,note=resolve(brand,perfume)
    except Exception as e:best=None;providers='';note=f'{type(e).__name__}: {e}'
    cp={'shobi_code':code,'brand':brand,'perfume':perfume,'result':'FOUND' if best else 'UNRESOLVED','fragrantica_id':best['id'] if best else '','fragrantica_url':best['url'] if best else '','candidate_brand':best['brand'] if best else '','candidate_perfume':best['perfume'] if best else '','score':f"{best['score']:.4f}" if best else '','provider':providers,'note':note}
    checkpoint.append(cp);bycode[code]=cp
    if best:
        found+=1;row.update(status='FOUND',match_type='CONFIRMED_IDENTITY_ONLINE',score=cp['score'],candidate_count='1',fragrantica_brand=best['brand'],fragrantica_perfume=best['perfume'],fragrantica_id=best['id'],fragrantica_url=best['url'],note='Confirmed identity resolved online against Fragrantica')
    if attempted%10==0:
        write_csv(CHECKPOINT,checkpoint,FIELDS);print(f'online v8 {attempted}/{MAX_ROWS}, found={found}',flush=True)
    time.sleep(DELAY)
write_csv(CHECKPOINT,checkpoint,FIELDS)
write_csv(REPORT,report,fields);write_csv(AMBIG,[r for r in report if r.get('status')=='AMBIGUOUS'],fields);write_csv(UNMATCH,[r for r in report if r.get('status') in {'NOT_FOUND','MAPPED_NOT_IN_CORPUS'}],fields)
summary=json.loads(SUMMARY_JSON.read_text(encoding='utf-8'));sc=Counter(r.get('status') or '' for r in report);tc=Counter(r.get('match_type') or 'NONE' for r in report)
summary['online_v8_checkpoint_rows']=len(checkpoint);summary['online_v8_found_total']=sum(1 for r in checkpoint if r.get('result')=='FOUND');summary['online_v8_attempted_this_run']=attempted;summary['online_v8_found_this_run']=found
summary['status_counts']=dict(sc);summary['match_type_counts']=dict(tc);summary['found_total']=sc.get('FOUND',0);summary['ambiguous_total']=sc.get('AMBIGUOUS',0);summary['not_found_total']=sc.get('NOT_FOUND',0);summary['mapped_not_in_corpus_total']=sc.get('MAPPED_NOT_IN_CORPUS',0)
SUMMARY_JSON.write_text(json.dumps(summary,indent=2,ensure_ascii=False)+'\n',encoding='utf-8')
print(json.dumps({'attempted':attempted,'found':found,'final_found':summary['found_total'],'unresolved':len(report)-summary['found_total']},indent=2),flush=True)
