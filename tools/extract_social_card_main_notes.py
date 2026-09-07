#!/usr/bin/env python3
from __future__ import annotations
import json, re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DB = ROOT / 'database_complete.json'
CARD_DIR_CANDIDATES = [
    ROOT / 'fragrantica-social-cards',
    ROOT / 'fragrantica-social-card-archive',
    ROOT / 'social-cards',
    ROOT / 'archive' / 'fragrantica-social-cards',
]

ID_RE = re.compile(r'(\d{2,7})')


def find_card_dirs():
    found=[]
    for p in CARD_DIR_CANDIDATES:
        if p.exists(): found.append(p)
    if not found:
        for p in ROOT.rglob('*'):
            if p.is_dir() and 'social' in p.name.lower() and 'card' in p.name.lower():
                found.append(p)
    return found


def flatten_records(data):
    if isinstance(data, list) and data and isinstance(data[0], dict) and isinstance(data[0].get('perfumes'), list):
        out=[]
        for b in data:
            out.extend(b.get('perfumes', []))
        return out
    return data if isinstance(data, list) else []


def official(p):
    s=str(p.get('fragrantica_status') or p.get('fragranticaStatus') or '').upper()
    return not s.startswith('RESOLVED_NO_FORCE')


def frag_id(p):
    for k in ('fragranticaId','fragrantica_id','fragranticaID'):
        v=p.get(k)
        if v not in (None,''):
            try: return int(str(v))
            except: pass
    for k in ('fragrantica_url','fragranticaLocalUrl','fragranticaUrl'):
        v=p.get(k)
        if v:
            m=re.search(r'-(\d+)\.html', str(v))
            if m: return int(m.group(1))
    return None


def main():
    data=json.loads(DB.read_text(encoding='utf-8'))
    recs=[p for p in flatten_records(data) if official(p)]
    ids={frag_id(p):p for p in recs if frag_id(p)}
    card_dirs=find_card_dirs()
    print('official',len(recs),'with_id',len(ids),'card_dirs', [str(p.relative_to(ROOT)) for p in card_dirs])
    cards=[]
    for d in card_dirs:
        for p in d.rglob('*'):
            if p.is_file() and p.suffix.lower() in {'.jpg','.jpeg','.png','.webp'}:
                cards.append(p)
    matched=0
    sample=[]
    for p in cards:
        nums=[int(x) for x in ID_RE.findall(p.stem)]
        fid=next((n for n in nums if n in ids),None)
        if fid:
            matched+=1
            if len(sample)<20: sample.append((fid,str(p.relative_to(ROOT))))
    print('cards',len(cards),'matched_ids',matched)
    print('sample')
    for x in sample: print(*x)
    report={
        'official_records': len(recs),
        'records_with_fragrantica_id': len(ids),
        'card_dirs': [str(p.relative_to(ROOT)) for p in card_dirs],
        'card_files': len(cards),
        'matched_card_files': matched,
        'sample': sample,
    }
    (ROOT/'social-card-main-notes-preflight.json').write_text(json.dumps(report,indent=2,ensure_ascii=False)+'\n',encoding='utf-8')

if __name__=='__main__': main()
