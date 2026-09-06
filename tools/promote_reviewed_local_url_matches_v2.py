import json,re
from pathlib import Path

TARGETS=[Path('database_v2_clean.json'),Path('database_complete.json')]
URLS=Path('fragrantica-scraper-archive/legacy/original-local-scraper/perfume_urls.txt')
REPORT=Path('fragrantica-v2-reviewed-promotion.md')

# Manually reviewed only against repository-local perfume_urls.txt and current local matcher ranking.
APPROVED={
    '1649-GIV':('62491','Givenchy','L Interdit Eau de Parfum Intense','same brand; full meaningful-name coverage'),
    '1996-LTN':('59485','Louis Vuitton','Heures d Absence','2020 row; local candidate clearly beats 1927 variant'),
    '2278-BLG':('145','Bvlgari','Eau Parfumee au The Blanc','same brand; Eau de Cologne is generic qualifier'),
    '204-CRD':('9828','Creed','Aventus','same brand; clear truncated spelling Avent -> Aventus'),
    '2142-PARF':('63100','Parfums de Marly','Pegasus Exclusif','same brand; Exclusive -> Exclusif spelling variant'),
    '2313-DRC':('56324','Dior','Sauvage Parfum','same brand; Shobi explicitly says Sauvage Parfum 2019'),
    '404-BAL':('7247','Balenciaga','Balenciaga Paris','same brand; Shobi BALE PARIS is a clear truncated Balenciaga Paris label'),
    '1037-BLG':('9403','Bvlgari','Bvlgari Man','same brand; BVL MAN is an unambiguous abbreviated label for Bvlgari Man'),
    '1141-GIV':('39','Givenchy','Pi','same brand; Shobi P is a one-character truncation and local alternatives are Pi variants'),
    '1502-CHA':('62194','Chanel','Coco Mademoiselle L Eau Privee','same brand; noisy Shobi prefix plus COCON MADEM typo preserves the full distinctive L EAU PRIVEE identity'),
    '1978-ARM':('52802','Giorgio Armani','Emporio Armani Stronger With You Intensely','same brand; exact distinctive STRONGER WITH YOU INTENSENLY target; correct local candidate is cand3, not Limited Edition'),
    '2122-GUR':('79472','Guerlain','Rosa Rossa Harvest','same brand; Shobi explicitly contains HARVEST ROSA ROSSA; correct local candidate is Rosa Rossa Harvest, not base/Forte variants'),
    '2344-LEL':('46295','Le Labo','Mousse de Chene 30 Amsterdam','same brand; exact distinctive Mousse de Chene 30 identity with corpus city qualifier'),
    '2173-ANFAD':('23000','Anfasic','Sukar','corrected suffix-brand review: exact SUKAR under Anfasic; previous code-signature brand hint was false'),
    '828-MIY':('724','Issey Miyake','L Eau Bleue d Issey Pour Homme','same-brand local candidate; Shobi L EAU BLEUE uniquely preserves the distinctive Eau Bleue identity'),
    '841-NRO':('42580','Narciso Rodriguez','Narciso Rodriguez Fleur Musc for Her','same-brand local candidate; exact distinctive Fleur Musc for Her words despite lower generic-token matcher ranking'),
    '2018-ARM':('75126','Giorgio Armani','Armani Code Parfum','verified Armani suffix; Shobi CODE PARFUM maps directly to the same-brand local Armani Code Parfum candidate'),
    '1081-DRC':('22860','Dior','Dior Homme Eau for Men','same-brand local candidate; Shobi HOMME EAU directly distinguishes Dior Homme Eau from Parfum, Cologne and base Homme variants'),
    '1110-DSQ':('18592','DSQUARED2','Potion Royal Black','verified DSQUARED2 suffix; Shobi BLACK POTION preserves the two distinctive identity words of the same-brand Potion Royal Black candidate'),
}

# Name-keyed approval is used only for a genuinely code-less catalog row.
APPROVED_BY_NAME={
    'danat al duniya eau de parfum':('45398','Ajmal','Danat Al Duniya','code-less row; exact normalized local name, score 1.0000, clear margin over Daanat spelling variant'),
}

def walk(o):
    if isinstance(o,list):
        for x in o: yield from walk(x)
    elif isinstance(o,dict):
        if isinstance(o.get('perfumes'),list):
            for p in o['perfumes']:
                if isinstance(p,dict): yield p
        elif 'code' in o or 'inspiredBy' in o: yield o

def norm_name(v):
    return ' '.join(re.sub(r'[^a-z0-9]+',' ',str(v or '').lower()).split())

need={v[0] for v in APPROVED.values()} | {v[0] for v in APPROVED_BY_NAME.values()}
url_by_id={}
for line in URLS.read_text(encoding='utf-8',errors='ignore').splitlines():
    m=re.search(r'-(\d+)\.html(?:\?.*)?$',line.strip())
    if m and m.group(1) in need:url_by_id[m.group(1)]=line.strip()

stats=[]; promoted=set(); skipped=set(); unmatched_name_approvals=set(APPROVED_BY_NAME)
for path in TARGETS:
    data=json.loads(path.read_text(encoding='utf-8-sig')); matched=changed=0
    for p in walk(data):
        code=str(p.get('code') or '').strip()
        key=code if code in APPROVED else ''
        approval=None; label=''
        if key:
            approval=APPROVED[key]; label=key
        elif not code:
            perfume_name=norm_name(p.get('inspiredBy') or p.get('perfume') or p.get('name'))
            if perfume_name in APPROVED_BY_NAME:
                approval=APPROVED_BY_NAME[perfume_name]; label=f'[no-code:{perfume_name}]'; unmatched_name_approvals.discard(perfume_name)
        if not approval: continue
        matched+=1
        if str(p.get('fragranticaStatus') or '').startswith('VERIFIED_'):
            skipped.add(label); continue
        fid,brand,name,reason=approval
        if fid not in url_by_id: continue
        p['fragranticaId']=fid
        p['fragranticaStatus']='VERIFIED_LOCAL_CORPUS_V2'
        p['fragranticaVerificationSource']='fragrantica-scraper-archive/legacy/original-local-scraper/perfume_urls.txt'
        p['fragranticaLocalUrl']=url_by_id[fid]
        changed+=1; promoted.add(label)
    path.write_text(json.dumps(data,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
    stats.append((str(path),matched,changed))

lines=['# Reviewed v2 local-corpus promotion','',f'- Approved code mappings: **{len(APPROVED)}**',f'- Approved code-less name mappings: **{len(APPROVED_BY_NAME)}**',f'- Promoted this run: **{len(promoted)}**',f'- Already verified / untouched: **{len(skipped)}**']
for p,m,c in stats:lines.append(f'- `{p}`: matched **{m}**, changed **{c}**')
lines += ['','No web verification. Every ID must exist in repository-local `perfume_urls.txt`.','','## Approved by code','']
for code,(fid,brand,name,reason) in APPROVED.items():lines.append(f'- `{code}` -> {brand} / {name} — ID {fid} — {reason}')
lines += ['','## Approved code-less row','']
for name_key,(fid,brand,name,reason) in APPROVED_BY_NAME.items():lines.append(f'- `{name_key}` -> {brand} / {name} — ID {fid} — {reason}')
if unmatched_name_approvals:
    lines += ['','## Warning','',f"- Unmatched code-less approvals: {', '.join(sorted(unmatched_name_approvals))}"]
REPORT.write_text('\n'.join(lines)+'\n',encoding='utf-8')
print('approved_codes',len(APPROVED),'approved_names',len(APPROVED_BY_NAME),'promoted',len(promoted),'skipped',len(skipped),'stats',stats,'unmatched_names',sorted(unmatched_name_approvals))
