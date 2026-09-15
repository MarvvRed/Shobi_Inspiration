#!/usr/bin/env python3
import hashlib,json,re,unicodedata
from collections import Counter,defaultdict
from pathlib import Path
from PIL import Image
ROOT=Path(__file__).resolve().parents[1]
DIR=ROOT/'database'/'assets'/'note-icons'
IDX=DIR/'index.json'; DB=ROOT/'database/catalog/database_complete.json'; MAP=ROOT/'database'/'assets'/'note-icons'/'map.js'
OUTJ=ROOT/'database/audits/public-note-icons-audit.json'; OUTM=ROOT/'database/audits/public-note-icons-audit.md'
def norm(s):
 s=unicodedata.normalize('NFKD',str(s or '')).encode('ascii','ignore').decode().lower()
 return ' '.join(re.findall(r'[a-z0-9]+',s))
index=json.loads(IDX.read_text(encoding='utf-8'))
records={int(x['id']):x for x in index}
failed=[x for x in index if x.get('status')!='ok']
actual=sorted(DIR.glob('*.jpg'))
corrupt=[]; dims=Counter(); hashes=defaultdict(list); tiny=[]
for p in actual:
 try:
  if p.stat().st_size<100: tiny.append({'file':p.name,'bytes':p.stat().st_size})
  hashes[hashlib.sha256(p.read_bytes()).hexdigest()].append(p.name)
  with Image.open(p) as im:
   im.verify()
  with Image.open(p) as im:
   dims[f'{im.width}x{im.height}']+=1
 except Exception as e: corrupt.append({'file':p.name,'error':str(e)})
duplicates=[v for v in hashes.values() if len(v)>1]
missing_index_files=[x for x in index if x.get('status')=='ok' and (not x.get('file') or not (DIR/x['file']).is_file())]
extra_files=sorted(p.name for p in actual if p.name not in {x.get('file') for x in index if x.get('file')})
# New Fragrantica coverage by normalized canonical slug
new_by_norm=defaultdict(list)
for x in index:new_by_norm[norm(x.get('slug'))].append(x)
rows=json.loads(DB.read_text(encoding='utf-8-sig'))
used=Counter()
for r in rows:
 for n in (r.get('fragranticaSocialCardNotes') or []): used[str(n).strip()]+=1
used_missing_new=[]
for note,count in sorted(used.items()):
 if norm(note) not in new_by_norm: used_missing_new.append({'note':note,'count':count})
# Existing map health
prefix='window.FRAGRANTICA_NOTE_ICON_MAP='
txt=MAP.read_text(encoding='utf-8').strip(); old=json.loads(txt[len(prefix):].rstrip(';')) if txt.startswith(prefix) else {}
old_missing_files=[{'note':k,'path':v} for k,v in old.items() if not (ROOT/v).is_file()]
old_not_in_new=[k for k in old if norm(k) not in new_by_norm]
new_matches_old=sum(1 for k in old if norm(k) in new_by_norm)
report={
 'indexRecords':len(index),'downloadedIndex':sum(x.get('status')=='ok' for x in index),'failed':failed,
 'actualJpgFiles':len(actual),'missingIndexedFiles':missing_index_files,'extraJpgFiles':extra_files,
 'corruptImages':corrupt,'tinyImages':tiny,'dimensionCounts':dict(dims),'duplicateContentGroups':duplicates,
 'databaseUniqueUsedNotes':len(used),'databaseNoteOccurrences':sum(used.values()),'usedNotesMissingFromNewFragranticaIndex':used_missing_new,
 'existingMapKeys':len(old),'existingMapMissingFiles':old_missing_files,'existingMapKeysMatchedByNewIndex':new_matches_old,'existingMapKeysNotMatchedByNewIndex':old_not_in_new,
}
OUTJ.write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
lines=['# Public note icons audit','',f'- Fragrantica index records: **{len(index)}**',f'- Downloaded according to index: **{report["downloadedIndex"]}**',f'- Failed downloads: **{len(failed)}**',f'- JPG files actually present: **{len(actual)}**',f'- Missing files for successful index records: **{len(missing_index_files)}**',f'- Extra JPG files not in index: **{len(extra_files)}**',f'- Corrupt/unreadable images: **{len(corrupt)}**',f'- Tiny (<100 byte) images: **{len(tiny)}**',f'- Byte-identical duplicate groups: **{len(duplicates)}**','',f'- Unique notes currently used by catalog: **{len(used)}**',f'- Total note occurrences in catalog: **{sum(used.values())}**',f'- Used catalog notes not matched by new Fragrantica index: **{len(used_missing_new)}**','',f'- Existing `note-icons/map.js` keys: **{len(old)}**',f'- Existing mapped paths missing on disk: **{len(old_missing_files)}**',f'- Existing map keys matched by new Fragrantica index: **{new_matches_old}/{len(old)}**','']
if failed:
 lines+=['## Failed download']+[f'- ID {x.get("id")}: **{x.get("slug")}** — {x.get("status")}' for x in failed]+['']
lines+=['## Image dimensions']+[f'- {k}: {v}' for k,v in dims.most_common()]+['']
if used_missing_new:
 lines+=['## Catalog notes not matched by the new Fragrantica index']+[f'- {x["note"]} ({x["count"]} uses)' for x in used_missing_new]+['']
if corrupt: lines+=['## Corrupt images']+[f'- {x["file"]}: {x["error"]}' for x in corrupt]+['']
if duplicates:
 lines+=['## Byte-identical duplicate groups']
 for g in duplicates: lines.append('- '+', '.join(g))
 lines.append('')
OUTM.write_text('\n'.join(lines)+'\n',encoding='utf-8')
print(json.dumps({k:report[k] for k in ['indexRecords','downloadedIndex','actualJpgFiles']},ensure_ascii=False))
