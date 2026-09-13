#!/usr/bin/env python3
"""Diagnose yellow rows and distinguish missing proof from existing proof labels.
Read-only: writes compact diagnostic reports only.
"""
import csv, json, re
from collections import Counter, defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DB = json.loads((ROOT / "database_complete.json").read_text(encoding="utf-8-sig"))
SITE = json.loads((ROOT / "catalog_site.json").read_text(encoding="utf-8-sig"))
GENDER_SEASON = ROOT / "fragrantica-scraper-archive" / "social-cards" / "gender-season.csv"
VALIDATED_NOTES = ROOT / "social-card-main-notes-validated.json"
RAW_NOTES = ROOT / "social-card-main-notes.json"
IMAGE_MAP = ROOT / "perfume-images" / "map.js"

YES = {"VERIFIED","VALIDATED","CONFIRMED","OK","MATCH_CORRETTO","MATCH CORRETTO","VALIDATED_OCR","VALIDATED_MANUAL","VALIDATED_SOCIAL_CARD"}
def ok(v): return str(v or "").strip().upper() in YES
def uid(u):
    s=str(u or '').strip()
    for p in (r"-(\d+)\.html(?:$|[?#])", r"/p/(\d+)(?:/?$|[?#])"):
        m=re.search(p,s,re.I)
        if m:return m.group(1)
    return ''
def code(r): return str(r.get('code') or '').strip().upper()
def norm_gender(v):
    s=str(v or '').strip().lower()
    return {'female':'feminine','woman':'feminine','women':'feminine','male':'masculine','man':'masculine','men':'masculine','unisex':'unisex'}.get(s,s)

# Preserve row identity, including blank/duplicate codes, by aligning DB and site by position.
rows=[]
for db,site in zip(DB,SITE):
    if str(site.get('validationStatus') or '').lower()=='yellow': rows.append(db)

validated={code(x):x for x in json.loads(VALIDATED_NOTES.read_text(encoding='utf-8'))}
raw={code(x):x for x in json.loads(RAW_NOTES.read_text(encoding='utf-8'))}
prefix='window.PERFUME_IMAGE_MAP='
t=IMAGE_MAP.read_text(encoding='utf-8').strip(); image_map=json.loads(t[len(prefix):].rstrip(';'))
with GENDER_SEASON.open(encoding='utf-8-sig',newline='') as f:
    gs={str(x.get('shobi_code') or '').strip().upper():x for x in csv.DictReader(f)}

freq={k:Counter() for k in ('identityStatus','identitySource','genderStatus','socialCardStatus')}
patterns=Counter(); samples=defaultdict(list)
for r in rows:
    c=code(r); fid=str(r.get('fragranticaId') or '').strip(); url=str(r.get('fragranticaUrl') or '').strip(); notes=r.get('fragranticaSocialCardNotes') or []
    va=r.get('validationAudit') or {}; checks=va.get('checks') or {}
    freq['identityStatus'][str(r.get('identityStatus') or '<EMPTY>')]+=1
    freq['identitySource'][str(r.get('fragranticaVerificationSource') or '<EMPTY>')]+=1
    freq['genderStatus'][str(r.get('genderStatus') or '<EMPTY>')]+=1
    freq['socialCardStatus'][str(r.get('fragranticaSocialCardStatus') or '<EMPTY>')]+=1
    exact_url=bool(fid and url and uid(url)==fid)
    has_src=bool(str(r.get('fragranticaVerificationSource') or '').strip())
    current_gender=norm_gender(r.get('gender') or r.get('genderAffinity'))
    has_gender=bool(current_gender)
    v=validated.get(c) or {}; rw=raw.get(c) or {}; g=gs.get(c) or {}
    validated_same=bool(v and v.get('validated') is True and str(v.get('fragranticaId') or '')==fid and (ROOT/str(v.get('card') or '')).is_file())
    raw_same=bool(rw and str(rw.get('fragranticaId') or '')==fid and rw.get('card') and (ROOT/str(rw.get('card') or '')).is_file())
    gs_same=bool(g and str(g.get('fragrantica_id') or '').strip()==fid and str(g.get('main_season') or '').strip())
    csv_gender=norm_gender(g.get('gender')) if g and str(g.get('fragrantica_id') or '').strip()==fid else ''
    gender_csv_match=bool(current_gender and csv_gender and current_gender==csv_gender)
    mapped=image_map.get(c,''); expected_img=f'perfume-images/{fid}.avif' if fid else ''
    image_map_same=bool(fid and mapped==expected_img and (ROOT/expected_img).is_file())
    expected_file_exists=bool(fid and (ROOT/expected_img).is_file())

    tests={
      'identity_label_only': (not checks.get('identity',False)) and has_src and not ok(r.get('identityStatus')),
      'gender_label_only': (not checks.get('gender',False)) and has_gender and not ok(r.get('genderStatus')),
      'identity_has_exact_chain': (not checks.get('identity',False)) and exact_url and has_src and validated_same and image_map_same,
      'gender_exact_card_exists': (not checks.get('gender',False)) and has_gender and (validated_same or raw_same),
      'gender_csv_exact_match': (not checks.get('gender',False)) and gender_csv_match,
      'social_validated_same_id': (not checks.get('socialCard',False)) and validated_same,
      'social_raw_same_id': (not checks.get('socialCard',False)) and raw_same,
      'season_exact_csv_exists': (not checks.get('season',False)) and gs_same,
      'image_map_exact': (not checks.get('image',False)) and image_map_same,
      'image_file_exists_unmapped': (not checks.get('image',False)) and expected_file_exists and not image_map_same,
    }
    for name,yes in tests.items():
        if yes:
            patterns[name]+=1
            if len(samples[name])<20:samples[name].append(c or '<EMPTY>')

out={'yellowRows':len(rows),'frequencies':{k:dict(v.most_common()) for k,v in freq.items()},'patterns':dict(patterns),'samples':dict(samples)}
(ROOT/'validation-recoverability-report.json').write_text(json.dumps(out,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
lines=['# Validation recoverability report','',f'- Yellow rows inspected: **{len(rows)}**','','## Existing-evidence patterns','']
for k,v in patterns.most_common(): lines.append(f'- `{k}`: **{v}** — samples: {", ".join(samples[k][:12])}')
for title,key in [('Identity status','identityStatus'),('Identity source','identitySource'),('Gender status','genderStatus'),('Social-card status','socialCardStatus')]:
    lines += ['',f'## {title}','']
    for k,v in freq[key].most_common(): lines.append(f'- `{k}`: **{v}**')
(ROOT/'validation-recoverability-report.md').write_text('\n'.join(lines)+'\n',encoding='utf-8')
print(json.dumps(out,ensure_ascii=False))
