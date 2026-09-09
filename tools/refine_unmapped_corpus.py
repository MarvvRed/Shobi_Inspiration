#!/usr/bin/env python3
import csv,re,unicodedata
from pathlib import Path
from urllib.parse import urlparse
from difflib import SequenceMatcher
ROOT=Path(__file__).resolve().parents[1]
SRC=ROOT/'fragrantica-v2-corpus-candidates.csv'
CORPUS=ROOT/'fragrantica-scraper-archive'/'perfume_urls.txt'
OUT=ROOT/'fragrantica-v2-refined-unresolved.csv'
SUM=ROOT/'fragrantica-v2-refined-summary.txt'
HOME_CODES={'222-DIP','223-DIP','227-DIP','228-DIP','230-DIP','379-YAN','380-YAN','381-YAN','382-YAN','383-YAN','1550-YAN','2586-DIP','2701-DIP','335-THCO','336-THCO'}
ALIASES={'FAHRENEIT':'FAHRENHEIT','SWEET ALMON MACARRON':'SWEET ALMOND MACAROON','ATTRAPE REVES':'ATTRAPE REVES','L INTERDIT INTENSE':'L INTERDIT EAU DE PARFUM INTENSE','SWISS ARMY VICTORINOX':'SWISS ARMY','SAUVAGE PARFUM 2019':'SAUVAGE PARFUM','Dioriviera Eau de Parfum':'DIORIVIERA','Lipstick Rose Eau de Parfum':'LIPSTICK ROSE'}
BRAND_HINT={'DRC':['dior'],'PRA':['prada'],'DOL':['dolce gabbana'],'LAC':['lacoste'],'BOD':['body shop'],'SWI':['victorinox','swiss army'],'FRE':['frederic malle'],'ROG':['roger gallet'],'GFE':['gianfranco ferre','ferre'],'AL HAR':['al haramain'],'CLIV':['clive christian'],'HUG':['hugo boss'],'VICT':['victoria secret'],'LTN':['louis vuitton'],'AFN':['afnan']}
def n(s):
 s=unicodedata.normalize('NFKD',s or '').encode('ascii','ignore').decode().lower().replace('&',' and ')
 return ' '.join(re.findall(r'[a-z0-9]+',s))
def suffix(c):
 c=(c or '').strip()
 if c.startswith('ALH'): return 'AL HAR'
 return c.split('-',1)[1] if '-' in c else ''
def pu(u):
 p=urlparse(u.strip()).path.strip('/').split('/')
 if len(p)<3 or p[0]!='perfume':return None
 m=re.search(r'-(\d+)\.html$',p[-1]);
 if not m:return None
 return n(p[1].replace('-',' ')),n(re.sub(r'-\d+\.html$','',p[-1]).replace('-',' ')),int(m.group(1)),u.strip()
urls=[x for x in (pu(l) for l in CORPUS.read_text(encoding='utf-8-sig',errors='ignore').splitlines()) if x]
rows=list(csv.DictReader(SRC.open(encoding='utf-8-sig',newline='')))
# only rows not already strong automatic candidates
rows=[r for r in rows if r['corpus_status'] in {'NO_MATCH','MULTIPLE_EXACT'}]
out=[]; counts={'HOME_NO_PERFUME':0,'REFINED_STRONG':0,'REFINED_REVIEW':0,'STILL_NO_MATCH':0}
for r in rows:
 code=r['shobi_code']; q=r['shobi_inspired_by']
 if code in HOME_CODES:
  st='HOME_NO_PERFUME'; cand=[]
 else:
  qq=n(ALIASES.get(q,q)); hints=[n(x) for x in BRAND_HINT.get(suffix(code),[])]
  pool=[x for x in urls if not hints or any(h in x[0] or x[0] in h for h in hints)]
  scored=[]
  for x in pool:
   score=SequenceMatcher(None,qq,x[1]).ratio()
   # strong containment bonus; fuzzy is review-only, never auto-applied
   if qq in x[1] or x[1] in qq: score=max(score,.94)
   if score>=.72: scored.append((score,x))
  scored.sort(reverse=True,key=lambda z:z[0]); cand=scored[:5]
  if cand and cand[0][0]>=.93 and (len(cand)==1 or cand[0][0]-cand[1][0]>=.08): st='REFINED_STRONG'
  elif cand: st='REFINED_REVIEW'
  else: st='STILL_NO_MATCH'
 counts[st]+=1
 out.append({**r,'refined_status':st,'refined_candidates':'|'.join(f'{x[1][2]}:{x[0]:.3f}' for x in cand),'refined_urls':'|'.join(x[1][3] for x in cand)})
fields=list(out[0].keys())
with OUT.open('w',encoding='utf-8-sig',newline='') as f:
 w=csv.DictWriter(f,fieldnames=fields);w.writeheader();w.writerows(out)
SUM.write_text('\n'.join([f'INPUT={len(rows)}']+[f'{k}={v}' for k,v in counts.items()])+'\n',encoding='utf-8')
print(SUM.read_text())