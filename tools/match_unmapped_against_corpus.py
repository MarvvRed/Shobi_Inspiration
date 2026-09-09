#!/usr/bin/env python3
import csv,re,unicodedata
from pathlib import Path
from urllib.parse import urlparse

ROOT=Path(__file__).resolve().parents[1]
QUEUE=ROOT/'fragrantica-v2-unmapped.csv'
CORPUS=ROOT/'fragrantica-scraper-archive'/'perfume_urls.txt'
OUT=ROOT/'fragrantica-v2-corpus-candidates.csv'
SUMMARY=ROOT/'fragrantica-v2-corpus-candidates-summary.txt'

# Code suffix -> expected Fragrantica brand slug fragments. Deliberately conservative.
BRANDS={
'LEL':['le-labo'],'YAS':['junaid-perfumes','syed-junaid-alam'],'AL HAR':['al-haramain'],'CIR':['cire-trudon','trudon'],
'CLIV':['clive-christian'],'DIP':['diptyque'],'JOM':['jo-malone-london','jo-malone'],'MIL':['miller-harris'],'MOL':['molton-brown'],
'THCO':['the-white-company'],'TMFO':['tom-ford'],'YAN':['yankee-candle'],'BRB':['burberry'],'CAC':['cacharel'],'CRT':['cartier'],
'DOL':['dolce-gabbana'],'PRA':['prada'],'ROG':['roger-gallet'],'ADO':['adolfo-dominguez'],'ANT':['antonio-banderas'],
'CAL':['calvin-klein'],'DRC':['dior','christian-dior'],'LAC':['lacoste'],'MOS':['moschino'],'TRU':['trussardi'],'DAV':['davidoff'],
'BOD':['the-body-shop'],'AFN':['afnan'],'SWI':['victorinox-swiss-army','swiss-army'],'KIL':['by-kilian','kilian'],
'GIV':['givenchy'],'LTN':['louis-vuitton'],'MARC':['marc-antoine-barrois'],'FRE':['frederic-malle'],'ARM':['giorgio-armani','emporio-armani','armani'],
'KYLJE':['kylie-jenner','kylie-cosmetics'],'HUG':['hugo-boss'],'VICT':['victoria-s-secret']}

def norm(s):
 s=unicodedata.normalize('NFKD',s or '').encode('ascii','ignore').decode().lower()
 s=s.replace('&',' and ')
 return ' '.join(re.findall(r'[a-z0-9]+',s))

def tokens(s): return [x for x in norm(s).split() if len(x)>1]
def suffix(code):
 c=(code or '').strip()
 if c.startswith('ALH'): return 'AL HAR'
 return c.split('-',1)[1] if '-' in c else ''
def parse_url(u):
 path=urlparse(u.strip()).path.strip('/').split('/')
 if len(path)<3 or path[0]!='perfume': return None
 brand=norm(path[1]); leaf=path[-1]
 m=re.search(r'-(\d+)\.html$',leaf)
 if not m:return None
 fid=int(m.group(1)); name=norm(re.sub(r'-\d+\.html$','',leaf).replace('-',' '))
 return brand,name,fid,u.strip()

urls=[]
for line in CORPUS.read_text(encoding='utf-8-sig',errors='ignore').splitlines():
 p=parse_url(line)
 if p: urls.append(p)

rows=list(csv.DictReader(QUEUE.open(encoding='utf-8-sig',newline='')))
out=[]
counts={'UNIQUE_EXACT':0,'MULTIPLE_EXACT':0,'BRAND_TOKEN_MATCH':0,'NO_MATCH':0}
for r in rows:
 code=r.get('shobi_code',''); q=r.get('shobi_inspired_by',''); qt=tokens(q); qn=' '.join(qt)
 bs=BRANDS.get(suffix(code),[])
 brand_pool=[x for x in urls if not bs or any(norm(b) in x[0] or x[0] in norm(b) for b in bs)]
 exact=[x for x in brand_pool if x[1]==qn]
 if exact:
  cand=exact; status='UNIQUE_EXACT' if len(exact)==1 else 'MULTIPLE_EXACT'
 else:
  # Strict token containment only; no fuzzy edit-distance guessing.
  cand=[x for x in brand_pool if qt and all(t in x[1].split() for t in qt)]
  status='BRAND_TOKEN_MATCH' if cand else 'NO_MATCH'
 counts[status]+=1
 if not cand:
  out.append({**r,'corpus_status':status,'candidate_count':0,'candidate_fids':'','candidate_urls':''})
 else:
  out.append({**r,'corpus_status':status,'candidate_count':len(cand),'candidate_fids':'|'.join(str(x[2]) for x in cand),'candidate_urls':'|'.join(x[3] for x in cand)})

fields=list(rows[0].keys())+['corpus_status','candidate_count','candidate_fids','candidate_urls']
with OUT.open('w',encoding='utf-8-sig',newline='') as f:
 w=csv.DictWriter(f,fieldnames=fields);w.writeheader();w.writerows(out)
SUMMARY.write_text('\n'.join([f'TOTAL={len(rows)}']+[f'{k}={v}' for k,v in counts.items()])+'\n',encoding='utf-8')
print(SUMMARY.read_text())