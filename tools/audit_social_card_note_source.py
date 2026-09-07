#!/usr/bin/env python3
from __future__ import annotations
import html
from pathlib import Path
from urllib.request import Request, urlopen

DUMPS = [
    ('debug', 'https://raw.githubusercontent.com/david-estrera/fragrance_scraper/master/debug_perfume_page.html'),
    ('inspect', 'https://raw.githubusercontent.com/david-estrera/fragrance_scraper/master/inspect_perfume_page.html'),
]
OUT = Path('social-card-note-source-audit.md')
UA = 'Mozilla/5.0'
TERMS = [
    'ingredient','ingredients','note','notes','accord','vote','votes','intensity',
    'Magnolia','Bergamot','Lemon','Citron','Jasmine','Tuberose','Rose','Patchouli','Vanilla','Vetiver',
    'perfume-note','data-note','data-ingredient','data-vote','data-intensity'
]

def clean(s: str) -> str:
    return ' '.join(html.unescape(s).replace('\n',' ').replace('\r',' ').split()).replace('```','` ` `')

def positions(hay: str, needle: str):
    low=hay.lower(); n=needle.lower(); start=0
    while True:
        p=low.find(n,start)
        if p<0: return
        yield p
        start=p+len(n)

lines=['# Social-card note source audit','','Fast literal-context scan of rendered Fragrantica HTML dumps.','']
for label,url in DUMPS:
    req=Request(url,headers={'User-Agent':UA})
    with urlopen(req,timeout=60) as r:
        raw=r.read(3_000_000).decode('utf-8',errors='replace')
    lines += [f'# Dump `{label}`','',f'- chars: **{len(raw)}**',f'- URL: `{url}`','']
    for term in TERMS:
        ps=list(positions(raw,term))
        lines += [f'## `{term}`',f'- hits: **{len(ps)}**']
        for p in ps[:12]:
            lines += ['', '```text', clean(raw[max(0,p-800):min(len(raw),p+1800)]), '```']
        lines.append('')
OUT.write_text('\n'.join(lines)+'\n',encoding='utf-8')
print('wrote',OUT)
