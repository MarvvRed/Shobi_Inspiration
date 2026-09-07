#!/usr/bin/env python3
from __future__ import annotations
import html
import re
import time
from pathlib import Path
from selenium import webdriver
from selenium.webdriver.chrome.options import Options

URL = 'https://www.fragrantica.com/perfume/Yves-Saint-Laurent/MYSLF-Eau-de-Parfum-84094.html'
OUT = Path('social-card-note-source-audit.md')

opts = Options()
opts.add_argument('--headless=new')
opts.add_argument('--no-sandbox')
opts.add_argument('--disable-dev-shm-usage')
opts.add_argument('--disable-gpu')
opts.add_argument('--window-size=1400,2200')
opts.add_argument('--lang=en-US')
opts.add_argument('--user-agent=Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/126 Safari/537.36')

driver = webdriver.Chrome(options=opts)
driver.set_page_load_timeout(60)
try:
    driver.get(URL)
    time.sleep(8)
    raw = driver.page_source
    body = driver.execute_script('return document.body ? document.body.innerText : ""') or ''
finally:
    driver.quit()

lines = ['# Social-card note source audit','',f'- URL: `{URL}`',f'- rendered HTML chars: **{len(raw)}**',f'- body text chars: **{len(body)}**','']
lines += ['## Page state','',f'- Cloudflare challenge: **{"yes" if "Just a moment" in raw else "no"}**',f'- Contains MYSLF: **{"yes" if "MYSLF" in raw else "no"}**','']

terms = ['Orange Blossom','Bergamot','Ambrofix','Patchouli','ingredient','ingredients','note','notes','vote','votes']
for term in terms:
    lines += [f'## `{term}`']
    for source_name, source in [('HTML',raw),('TEXT',body)]:
        hits=[m.start() for m in re.finditer(re.escape(term),source,re.I)]
        lines.append(f'- {source_name} hits: **{len(hits)}**')
        for pos in hits[:6]:
            snippet=source[max(0,pos-500):min(len(source),pos+1000)]
            snippet=re.sub(r'\s+',' ',html.unescape(snippet)).replace('```','` ` `')
            lines += ['', '```text', snippet, '```']
    lines.append('')

# Dump compact contexts for likely JS variables / data attributes containing note intensity data.
patterns=[
    r'.{0,500}(?:ingredient[^<>{}\n]{0,80}(?:vote|score|rating|intensity)|(?:vote|score|rating|intensity)[^<>{}\n]{0,80}ingredient).{0,1800}',
    r'.{0,500}(?:note[^<>{}\n]{0,80}(?:vote|score|rating|intensity)|(?:vote|score|rating|intensity)[^<>{}\n]{0,80}note).{0,1800}',
    r'.{0,500}(?:Orange Blossom|Ambrofix).{0,2200}',
]
for i,pat in enumerate(patterns,1):
    lines += [f'## Pattern {i}']
    found=[]
    for m in re.finditer(pat,raw,re.I|re.S):
        s=re.sub(r'\s+',' ',html.unescape(m.group(0))).replace('```','` ` `')
        if s not in found: found.append(s)
        if len(found)>=15: break
    lines.append(f'- matches: **{len(found)}**')
    for s in found:
        lines += ['', '```text', s, '```']
    lines.append('')

OUT.write_text('\n'.join(lines)+'\n',encoding='utf-8')
print('wrote',OUT,'html',len(raw),'text',len(body))
