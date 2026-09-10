#!/usr/bin/env python3
import csv, re, time
from collections import Counter, defaultdict
from html import unescape
from pathlib import Path
from urllib.parse import urljoin
from urllib.request import Request, urlopen

BASE='https://leparfum.com.gr'
MASTER=Path('perfume-database/catalog/shobi-master-v2-2369.csv')
OUTCSV=Path('data/shobi-live-catalog-2026-09-10.csv')
REPORT=Path('data/shobi-live-vs-master-v2-2026-09-10.md')
CATEGORIES={
 'Fragrances For Women':'https://leparfum.com.gr/en/perfumes/fragrances-for-women?resultsPerPage=99999',
 'Fragrances For Men':'https://leparfum.com.gr/en/perfumes/fragrances-for-men?resultsPerPage=99999',
 'Elegants Fragrances':'https://leparfum.com.gr/en/perfumes/elegants-fragrances?resultsPerPage=99999',
 'Niche Perfumes':'https://leparfum.com.gr/en/perfumes/niche-perfumes?resultsPerPage=99999',
 'Luxury Perfumes':'https://leparfum.com.gr/en/perfumes/luxury-perfumes?resultsPerPage=99999',
}
CODE_RE=re.compile(r'(?<!\d)(\d{1,4}-[A-Z0-9]+(?:\s+(?:W|MP|N|LUX))?)(?![A-Z0-9])',re.I)
REF_RE=re.compile(r'\b(?:WP|MP|AR|EL|LUX)\d{3}\b',re.I)

def get(url):
 req=Request(url,headers={'User-Agent':'Mozilla/5.0 ShobiCatalogAudit/1.0','Accept-Language':'en-US,en;q=0.9'})
 with urlopen(req,timeout=90) as r: return r.read().decode('utf-8','replace')

def clean(s):
 s=re.sub(r'<[^>]+>',' ',s); s=unescape(s); return re.sub(r'\s+',' ',s).strip()

def canonical(code):
 code=re.sub(r'\s+',' ',code.upper().strip())
 # suffix W/MP/N/LUX is display metadata; canonical Shobi identity is numeric-prefix code.
 return code.split(' ')[0]

def parse_products(html,category):
 # PrestaShop product-miniature blocks; fallback to product links if theme markup differs.
 blocks=re.findall(r'<article\b[^>]*class="[^"]*product-miniature[^"]*"[^>]*>(.*?)</article>',html,re.I|re.S)
 if not blocks:
  blocks=re.findall(r'(<div\b[^>]*class="[^"]*product-miniature[^"]*"[^>]*>.*?</div>\s*</div>)',html,re.I|re.S)
 rows=[]
 for b in blocks:
  text=clean(b)
  cm=CODE_RE.search(text)
  if not cm: continue
  code=canonical(cm.group(1))
  rm=REF_RE.search(text)
  hrefs=re.findall(r'href=["\']([^"\']+)["\']',b,re.I)
  url=''
  for h in hrefs:
   if '/en/' in h or h.startswith('/'):
    url=urljoin(BASE,h); break
  rows.append({'shobi_code':code,'display_code':cm.group(1).upper(),'reference':rm.group(0).upper() if rm else '', 'category':category,'url':url})
 return rows

def main():
 all_rows=[]; diagnostics=[]
 for cat,url in CATEGORIES.items():
  html=get(url); rows=parse_products(html,cat)
  diagnostics.append((cat,len(rows),len(html)))
  all_rows.extend(rows); time.sleep(1)
 if not all_rows: raise SystemExit('ABORT: scraper extracted zero products')
 # Safety: current five-category catalog should be >2000 assignments; do not publish partial scrape.
 if len(all_rows)<2200: raise SystemExit(f'ABORT: suspiciously partial scrape: {len(all_rows)} category rows; diagnostics={diagnostics}')
 bycode=defaultdict(list)
 for r in all_rows: bycode[r['shobi_code']].append(r)
 live=set(bycode)
 with MASTER.open(encoding='utf-8-sig',newline='') as f: master_rows=list(csv.DictReader(f))
 master={canonical(r['shobi_code']) for r in master_rows if (r.get('shobi_code') or '').strip()}
 both=live&master; live_only=live-master; master_only=master-live
 OUTCSV.parent.mkdir(parents=True,exist_ok=True)
 with OUTCSV.open('w',encoding='utf-8-sig',newline='') as f:
  w=csv.DictWriter(f,fieldnames=['shobi_code','reference','categories','url','occurrences','comparison'])
  w.writeheader()
  for code in sorted(live,key=lambda x:(int(x.split('-',1)[0]) if x.split('-',1)[0].isdigit() else 10**9,x)):
   rs=bycode[code]; cats=' | '.join(dict.fromkeys(r['category'] for r in rs)); refs=' | '.join(dict.fromkeys(r['reference'] for r in rs if r['reference']))
   urls=' | '.join(dict.fromkeys(r['url'] for r in rs if r['url']))
   w.writerow({'shobi_code':code,'reference':refs,'categories':cats,'url':urls,'occurrences':len(rs),'comparison':'BOTH' if code in master else 'LIVE_ONLY'})
 dup={c:rs for c,rs in bycode.items() if len(rs)>1}
 lines=['# Shobi live catalog vs Master V2','', 'Audit date: 2026-09-10','', '## Result','',f'- Live category assignments scraped: **{len(all_rows)}**',f'- Live unique Shobi codes: **{len(live)}**',f'- Master V2 unique Shobi codes: **{len(master)}**',f'- Present in both: **{len(both)}**',f'- Live only: **{len(live_only)}**',f'- Master V2 only: **{len(master_only)}**',f'- Cross-category duplicate live codes: **{len(dup)}**','', '## Category scrape diagnostics','']
 lines += [f'- {c}: {n} extracted rows (HTML bytes/chars {sz})' for c,n,sz in diagnostics]
 lines += ['','## Live only','']+[f'- `{c}`' for c in sorted(live_only)]
 lines += ['','## Master V2 only','']+[f'- `{c}`' for c in sorted(master_only)]
 lines += ['','## Live duplicate/cross-category codes','']
 for c,rs in sorted(dup.items()): lines.append(f"- `{c}` — "+' | '.join(r['category'] for r in rs))
 REPORT.write_text('\n'.join(lines)+'\n',encoding='utf-8')
 print('\n'.join(lines[:20]))

if __name__=='__main__': main()
