#!/usr/bin/env python3
from __future__ import annotations
import html
import re
from pathlib import Path
from urllib.request import Request, urlopen

DUMPS = [
    ('debug', 'https://raw.githubusercontent.com/david-estrera/fragrance_scraper/master/debug_perfume_page.html'),
    ('inspect', 'https://raw.githubusercontent.com/david-estrera/fragrance_scraper/master/inspect_perfume_page.html'),
]
OUT = Path('social-card-note-source-audit.md')
UA = 'Mozilla/5.0'

terms = [
    'ingredient', 'ingredients', 'note', 'notes', 'accord', 'vote', 'votes',
    'intensity', 'very strong', 'strong', 'moderate', 'weak',
    'Magnolia', 'Bergamot', 'Lemon', 'Citron', 'Jasmine', 'Tuberose',
]
patterns = [
    r'.{0,600}(?:ingredient|note)[^\n]{0,160}(?:vote|score|rating|intensity).{0,1800}',
    r'.{0,600}(?:vote|score|rating|intensity)[^\n]{0,160}(?:ingredient|note).{0,1800}',
    r'.{0,700}(?:ingredients?|notes?)[^\n]{0,2400}',
    r'.{0,700}(?:data-[a-z0-9_-]*(?:note|ingredient|vote|intensity)[a-z0-9_-]*)[^\n]{0,2200}',
    r'.{0,700}(?:class=["\'][^"\']*(?:note|ingredient|vote)[^"\']*["\'])[^\n]{0,2200}',
]

lines=['# Social-card note source audit','','Goal: find a structured source for the ordered ingredient ranking used by Fragrantica social cards.','']
for label,url in DUMPS:
    req=Request(url,headers={'User-Agent':UA})
    with urlopen(req,timeout=60) as r:
        raw=r.read(3_000_000).decode('utf-8',errors='replace')
    lines += [f'# Dump `{label}`','',f'- chars: **{len(raw)}**',f'- URL: `{url}`','']
    for term in terms:
        hits=[m.start() for m in re.finditer(re.escape(term),raw,re.I)]
        lines.append(f'- `{term}` hits: **{len(hits)}**')
    lines.append('')

    # Collect tag/class snippets around note-image assets, which are usually the cleanest route to names/order.
    asset_patterns=[r'fimgs\.net/mdimg/perfume-note[^"\'<> ]*', r'mdimg/perfume-note[^"\'<> ]*', r'/notes/[^"\'<> ]*']
    for ap in asset_patterns:
        hits=list(re.finditer(ap,raw,re.I))
        lines += [f'## Asset pattern `{ap}`',f'- hits: **{len(hits)}**']
        for m in hits[:20]:
            s=raw[max(0,m.start()-700):min(len(raw),m.end()+1100)]
            s=re.sub(r'\s+',' ',html.unescape(s)).replace('```','` ` `')
            lines += ['', '```text', s, '```']
        lines.append('')

    for i,pat in enumerate(patterns,1):
        found=[]
        for m in re.finditer(pat,raw,re.I|re.S):
            s=re.sub(r'\s+',' ',html.unescape(m.group(0))).replace('```','` ` `')
            if s not in found: found.append(s)
            if len(found)>=25: break
        lines += [f'## Pattern {i}',f'- matches: **{len(found)}**']
        for s in found:
            lines += ['', '```text', s, '```']
        lines.append('')

OUT.write_text('\n'.join(lines)+'\n',encoding='utf-8')
print('wrote',OUT)
