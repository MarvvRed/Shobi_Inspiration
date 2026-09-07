import csv, json, re
from collections import defaultdict, Counter
from pathlib import Path
from urllib.parse import urlparse, unquote

DB=Path('database_complete.json')
CLEAN=Path('database_v2_clean.json')
AUDIT=Path('fragrantica-v2-identity-audit.csv')
CORPUS=Path('fragrantica-scraper-archive/legacy/original-local-scraper/perfume_urls.txt')

PLACEHOLDERS={'','unknown brand','unknown','n/a','na','none','null','-'}

MANUAL={
    '118-HAM':'Hamidi Oud & Perfumes','166-AZ':"The Perfumer's Story by Azzi",'171-DUP':'S.T. Dupont',
    '254-JOM':'Jo Malone London','287-JOM':'Jo Malone London','304-KIE':"Kiehl's",
    '307-LOC':"L'Occitane en Provence",'309-LOC':"L'Occitane en Provence",
    '325-PECK':"Pecksniff's",'327-PECK':"Pecksniff's",'523-DRC':'Dior','534-DRC':'Dior',
    '637-EST':'Estée Lauder','992-ZAD':'Zadig & Voltaire','993-ZAD':'Zadig & Voltaire',
    '994-ZAD':'Zadig & Voltaire','1118-FAB':'Brut Parfums Prestige',
    '2016-PARELM':"Parfums d'Elmar",'pid:2688':'Ajmal',
}

ALIASES={
    'Abercrombie Fitch':'Abercrombie & Fitch','Dolce Gabbana':'Dolce & Gabbana','Dolce&Gabbana':'Dolce & Gabbana',
    'DSQUARED²':'Dsquared2','DSQUARED2':'Dsquared2','Estee Lauder':'Estée Lauder',
    'Goldfield Banks Australia':'Goldfield & Banks Australia','maison-mataha':'Maison Mataha',
    'Penhaligon s':"Penhaligon's",'Victoria s Secret':"Victoria's Secret",'Victoria S Secret':"Victoria's Secret",
    'Zadig Voltaire':'Zadig & Voltaire',
}

def canonical(b):
    b=' '.join(str(b or '').split())
    return ALIASES.get(b,b)

def status_of(p):
    return str(p.get('fragrantica_status') or p.get('fragranticaStatus') or '').upper()

def official(p):
    return not status_of(p).startswith('RESOLVED_NO_FORCE')

def designer_slug(url):
    if not url: return ''
    parts=[p for p in urlparse(url).path.split('/') if p]
    if len(parts)>=3 and parts[0] in {'perfume','parfem'}: return unquote(parts[1])
    return ''

def display_slug(slug):
    s=unquote(slug).replace('-', ' ').strip()
    return ' '.join(w if (w.isupper() and len(w)<=4) else w.capitalize() for w in s.split())

def perfume_id(url):
    m=re.search(r'-(\d+)\.html(?:$|[?#])', str(url or ''))
    return m.group(1) if m else ''

def suffix(code):
    m=re.search(r'-([A-Za-z0-9]+)$', str(code or ''))
    return m.group(1).upper() if m else ''

by_code={}
slug_names=defaultdict(Counter)
with AUDIT.open(encoding='utf-8-sig', newline='') as f:
    for r in csv.DictReader(f):
        code=(r.get('shobi_code') or '').strip(); brand=canonical((r.get('fragrantica_brand') or '').strip()); url=(r.get('fragrantica_url') or '').strip()
        by_code[code]=(brand,url)
        sl=designer_slug(url)
        if sl and brand: slug_names[sl][brand]+=1
slug_brand={sl:c.most_common(1)[0][0] for sl,c in slug_names.items()}

id_urls=defaultdict(list)
for line in CORPUS.read_text(encoding='utf-8',errors='ignore').splitlines():
    u=line.strip(); fid=perfume_id(u)
    if fid: id_urls[fid].append(u)

def build_source(rows):
    source={}
    for p in rows:
        code=str(p.get('code') or '')
        if code in MANUAL:
            source[code]=MANUAL[code]; continue
        b,url=by_code.get(code,('',''))
        if b:
            source[code]=canonical(b); continue
        fid=str(p.get('fragranticaId') or p.get('fragrantica_id') or '').strip()
        urls=[url,str(p.get('fragrantica_url') or ''),str(p.get('fragranticaLocalUrl') or '')]+id_urls.get(fid,[])
        slugs={designer_slug(u) for u in urls if designer_slug(u)}
        if len(slugs)==1:
            sl=next(iter(slugs)); source[code]=canonical(slug_brand.get(sl) or display_slug(sl))
    suffix_brands=defaultdict(set)
    for p in rows:
        code=str(p.get('code') or '')
        if code in source and suffix(code): suffix_brands[suffix(code)].add(source[code])
    unanimous={s:next(iter(bs)) for s,bs in suffix_brands.items() if len(bs)==1}
    for p in rows:
        code=str(p.get('code') or '')
        if code not in source and suffix(code) in unanimous: source[code]=unanimous[suffix(code)]
    return source

def apply(path):
    rows=json.loads(path.read_text(encoding='utf-8')); source=build_source(rows); changed=0; missing_official=[]
    for p in rows:
        if not isinstance(p,dict): continue
        code=str(p.get('code') or ''); current=canonical(p.get('brand'))
        if current.lower() in PLACEHOLDERS:
            if code in source:
                p['brand']=source[code]; changed+=1
            elif official(p):
                missing_official.append(code)
        elif p.get('brand') != current:
            p['brand']=current; changed+=1
    if missing_official:
        raise SystemExit(f'{path}: unresolved OFFICIAL brand codes: {missing_official}')
    path.write_text(json.dumps(rows,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
    print(path,'changed',changed,'rows',len(rows),'official_missing',len(missing_official))

apply(DB)
apply(CLEAN)
