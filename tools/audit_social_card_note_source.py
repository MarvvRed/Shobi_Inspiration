#!/usr/bin/env python3
from __future__ import annotations
import html
import re
from pathlib import Path
from urllib.request import Request, urlopen

# Diagnostic: identify the structured source that preserves social-card note order.
URL = 'https://www.fragrantica.com/perfume/Yves-Saint-Laurent/MYSLF-Eau-de-Parfum-84094.html'
OUT = Path('social-card-note-source-audit.md')
UA = 'Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 Chrome/126 Safari/537.36'
req = Request(URL, headers={'User-Agent': UA, 'Accept-Language':'en-US,en;q=0.9'})
with urlopen(req, timeout=30) as r:
    raw = r.read(5_000_000).decode('utf-8', errors='replace')

terms = ['Orange Blossom','Bergamot','Ambrofix','Patchouli','notes','ingredients','accord','vote']
lines = ['# Social-card note source audit','',f'- URL: `{URL}`',f'- HTML bytes: **{len(raw.encode("utf-8"))}**','']
for term in terms:
    lines += [f'## `{term}`']
    hits = [m.start() for m in re.finditer(re.escape(term), raw, re.I)]
    lines.append(f'- hits: **{len(hits)}**')
    for pos in hits[:8]:
        snippet = raw[max(0,pos-500):min(len(raw),pos+900)]
        snippet = re.sub(r'\s+', ' ', html.unescape(snippet))
        snippet = snippet.replace('```','` ` `')
        lines += ['', '```text', snippet, '```']
    lines.append('')

patterns = [
    r'.{0,400}(?:notes|ingredients|noteVotes|ingredientsVotes|accords).{0,1400}',
    r'.{0,400}84094.{0,1400}',
]
for i,pat in enumerate(patterns,1):
    lines += [f'## Pattern {i}']
    found=[]
    for m in re.finditer(pat, raw, re.I|re.S):
        s=re.sub(r'\s+',' ',html.unescape(m.group(0)))
        if s not in found: found.append(s)
        if len(found)>=12: break
    lines.append(f'- matches: **{len(found)}**')
    for s in found:
        lines += ['', '```text', s.replace('```','` ` `'), '```']
    lines.append('')
OUT.write_text('\n'.join(lines)+'\n',encoding='utf-8')
print('wrote', OUT, 'html chars', len(raw))
