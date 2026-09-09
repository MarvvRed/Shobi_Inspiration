#!/usr/bin/env python3
import csv,re,unicodedata
from pathlib import Path
from urllib.parse import urlparse
ROOT=Path(__file__).resolve().parents[1]
CORP=ROOT/'fragrantica-scraper-archive/perfume_urls.txt'
OUT=ROOT/'fragrantica-final-eight-candidates.csv'
Q={
'570-DOL':('dolce gabbana',[]),
'612-ESC':('escada',['turquoise']),
'904-SALV':('salvador dali',[]),
'1251-ROM':('romeo gigli',[]),
'1526-AL HAR':('al haramain',['mukhallat al emirates']),
'1955-LAP':('la prairie',['cellular energizing']),
'2178-MON':('moncler',['pour homme']),
'2552-SOR':('sora dora',[]),
'334-SHI':('shirley may',[]),
}
def n(s):
 s=unicodedata.normalize('NFKD',s or '').encode('ascii','ignore').decode().lower()
 return ' '.join(re.findall(r'[a-z0-9]+',s))
urls=[]
for u in CORP.read_text(encoding='utf-8-sig',errors='ignore').splitlines():
 p=urlparse(u.strip()).path.strip('/').split('/')
 if len(p)<3 or p[0]!='perfume':continue
 m=re.search(r'-(\d+)\.html$',p[-1])
 if not m:continue
 urls.append((n(p[1].replace('-',' ')),n(re.sub(r'-\d+\.html$','',p[-1]).replace('-',' ')),int(m.group(1)),u.strip()))
out=[]
for code,(brand,terms) in Q.items():
 b=n(brand); ts=[n(x) for x in terms]
 cand=[x for x in urls if (b in x[0] or x[0] in b) and all(t in x[1] for t in ts)]
 for x in cand:out.append({'shobi_code':code,'brand_query':brand,'name_query':'|'.join(terms),'candidate_brand':x[0],'candidate_name':x[1],'fid':x[2],'url':x[3]})
 if not cand:out.append({'shobi_code':code,'brand_query':brand,'name_query':'|'.join(terms),'candidate_brand':'','candidate_name':'','fid':'','url':''})
with OUT.open('w',encoding='utf-8-sig',newline='') as f:
 w=csv.DictWriter(f,fieldnames=out[0].keys());w.writeheader();w.writerows(out)
print('rows',len(out))