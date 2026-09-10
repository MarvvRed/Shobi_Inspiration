#!/usr/bin/env python3
import csv, re, time, random
from collections import defaultdict
from html import unescape
from pathlib import Path
from urllib.parse import urljoin, urlencode
from urllib.request import Request, build_opener
from urllib.error import HTTPError, URLError
import http.client

BASE='https://leparfum.com.gr'
MASTER=Path('perfume-database/catalog/shobi-master-v2-2369.csv')
OUTCSV=Path('data/shobi-live-catalog-2026-09-10.csv')
REPORT=Path('data/shobi-live-vs-master-v2-2026-09-10.md')
CATEGORIES={
 'Fragrances For Women':'https://leparfum.com.gr/en/fragrances-for-women',
 'Fragrances For Men':'https://leparfum.com.gr/en/fragrances-for-men',
 'Elegants Fragrances':'https://leparfum.com.gr/en/elegants-fragrances',
 'Niche Perfumes':'https://leparfum.com.gr/en/niche-perfumes',
 'Luxury Perfumes':'https://leparfum.com.gr/en/luxury-perfumes',
}
PAGE_SIZE=24
MAX_PAGES=80
CODE_RE=re.compile(r'(?<!\d)(\d{1,4}-[A-Z0-9]+(?:\s+(?:W|M|MP|N|EL|L|LUX|AR))?)(?![A-Z0-9])',re.I)
REF_RE=re.compile(r'\b(?:WP|MP|AR|EL|LUX)\d{3}\b',re.I)
OPENER=build_opener()
HEADERS={
 'User-Agent':'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/140.0 Safari/537.36',
 'Accept':'text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,*/*;q=0.8',
 'Accept-Language':'en-US,en;q=0.9',
 'Cache-Control':'no-cache','Pragma':'no-cache','Connection':'close',
}

def get(url, attempts=6):
 last=None
 for i in range(attempts):
  try:
   req=Request(url,headers=HEADERS)
   with OPENER.open(req,timeout=60) as r:
    data=r.read()
    if not data: raise RuntimeError('empty response')
    return data.decode('utf-8','replace')
  except (HTTPError,URLError,http.client.RemoteDisconnected,TimeoutError,ConnectionResetError,RuntimeError) as e:
   last=e; wait=min(30,2**i)+random.uniform(.4,1.4)
   print(f'WARN request failed attempt {i+1}/{attempts}: {url}: {e}; retry in {wait:.1f}s',flush=True)
   time.sleep(wait)
 raise RuntimeError(f'GET failed after {attempts} attempts: {url}: {last}')

def clean(s):
 s=re.sub(r'<[^>]+>',' ',s); s=unescape(s); return re.sub(r'\s+',' ',s).strip()

def canonical(code):
 return re.sub(r'\s+',' ',code.upper().strip()).split(' ')[0]

def parse_products(html,category):
 blocks=re.findall(r'<article\b[^>]*class=["\'][^"\']*product-miniature[^"\']*["\'][^>]*>(.*?)</article>',html,re.I|re.S)
 if not blocks:
  blocks=re.findall(r'<div\b[^>]*class=["\'][^"\']*(?:product-miniature|js-product-miniature)[^"\']*["\'][^>]*>(.*?)(?=<div\b[^>]*class=["\'][^"\']*(?:product-miniature|js-product-miniature)|\Z)',html,re.I|re.S)
 rows=[]
 for b in blocks:
  text=clean(b); cm=CODE_RE.search(text)
  if not cm: continue
  code=canonical(cm.group(1)); rm=REF_RE.search(text)
  hrefs=re.findall(r'href=["\']([^"\']+)["\']',b,re.I); url=''
  for h in hrefs:
   if '/en/' in h or h.startswith('/'):
    url=urljoin(BASE,h); break
  rows.append({'shobi_code':code,'display_code':cm.group(1).upper(),'reference':rm.group(0).upper() if rm else '', 'category':category,'url':url})
 if rows:
  return list({(r['shobi_code'],r['url']):r for r in rows}.values())
 # Last-resort parser: official category pages expose product codes in visible text even if theme markup changes.
 text=clean(html); found=[]; seen=set()
 for cm in CODE_RE.finditer(text):
  code=canonical(cm.group(1))
  if code in seen: continue
  seen.add(code)
  window=text[cm.start():cm.start()+500]; rm=REF_RE.search(window)
  found.append({'shobi_code':code,'display_code':cm.group(1).upper(),'reference':rm.group(0).upper() if rm else '', 'category':category,'url':''})
 return found

def scrape_category(category,base_url):
 out=[]; seen=set()
 for page in range(1,MAX_PAGES+1):
  url=f'{base_url}?'+urlencode({'page':page,'resultsPerPage':PAGE_SIZE})
  rows=parse_products(get(url),category)
  fresh=[r for r in rows if r['shobi_code'] not in seen]
  print(f'{category}: page {page}: parsed={len(rows)} fresh={len(fresh)}',flush=True)
  if not rows: break
  for r in fresh: seen.add(r['shobi_code']); out.append(r)
  if not fresh or len(rows)<PAGE_SIZE: break
  time.sleep(random.uniform(.8,1.5))
 return out

def main():
 all_rows=[]; diagnostics=[]
 for cat,url in CATEGORIES.items():
  rows=scrape_category(cat,url); diagnostics.append((cat,len(rows))); all_rows.extend(rows); time.sleep(random.uniform(1,2))
 if not all_rows: raise SystemExit('ABORT: scraper extracted zero products')
 if len(all_rows)<2200: raise SystemExit(f'ABORT: suspiciously partial scrape: {len(all_rows)} category rows; diagnostics={diagnostics}')
 bycode=defaultdict(list)
 for r in all_rows: bycode[r['shobi_code']].append(r)
 live=set(bycode)
 with MASTER.open(encoding='utf-8-sig',newline='') as f: master_rows=list(csv.DictReader(f))
 master={canonical(r['shobi_code']) for r in master_rows if (r.get('shobi_code') or '').strip()}
 both=live&master; live_only=live-master; master_only=master-live
 OUTCSV.parent.mkdir(parents=True,exist_ok=True)
 with OUTCSV.open('w',encoding='utf-8-sig',newline='') as f:
  w=csv.DictWriter(f,fieldnames=['shobi_code','reference','categories','url','occurrences','comparison']); w.writeheader()
  for code in sorted(live,key=lambda x:(int(x.split('-',1)[0]) if x.split('-',1)[0].isdigit() else 10**9,x)):
   rs=bycode[code]; cats=' | '.join(dict.fromkeys(r['category'] for r in rs)); refs=' | '.join(dict.fromkeys(r['reference'] for r in rs if r['reference'])); urls=' | '.join(dict.fromkeys(r['url'] for r in rs if r['url']))
   w.writerow({'shobi_code':code,'reference':refs,'categories':cats,'url':urls,'occurrences':len(rs),'comparison':'BOTH' if code in master else 'LIVE_ONLY'})
 dup={c:rs for c,rs in bycode.items() if len(rs)>1}
 sortcodes=lambda s: sorted(s,key=lambda x:(int(x.split('-',1)[0]) if x.split('-',1)[0].isdigit() else 10**9,x))
 lines=['# Shobi live catalog vs Master V2','','Audit date: 2026-09-10','','## Result','',f'- Live category assignments scraped: **{len(all_rows)}**',f'- Live unique Shobi codes: **{len(live)}**',f'- Master V2 unique Shobi codes: **{len(master)}**',f'- Present in both: **{len(both)}**',f'- Live only: **{len(live_only)}**',f'- Master V2 only: **{len(master_only)}**',f'- Cross-category duplicate live codes: **{len(dup)}**','','## Category scrape diagnostics','']
 lines += [f'- {c}: {n} extracted rows' for c,n in diagnostics]
 lines += ['','## Live only','']+[f'- `{c}`' for c in sortcodes(live_only)]
 lines += ['','## Master V2 only','']+[f'- `{c}`' for c in sortcodes(master_only)]
 lines += ['','## Live duplicate/cross-category codes','']
 for c in sortcodes(dup): lines.append(f"- `{c}` — "+' | '.join(r['category'] for r in dup[c]))
 REPORT.write_text('\n'.join(lines)+'\n',encoding='utf-8')
 print('\n'.join(lines[:25]))

if __name__=='__main__': main()
