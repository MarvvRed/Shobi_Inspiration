from pathlib import Path
import csv, json

ROOT = Path(__file__).resolve().parents[1]
MANIFEST = ROOT / 'perfume-images' / 'manifest.csv'
MAP_JS = ROOT / 'perfume-images' / 'map.js'
INDEX = ROOT / 'index.html'

# Build code -> local image path map from the archived Fragrantica images.
image_map = {}
with MANIFEST.open(encoding='utf-8-sig', newline='') as f:
    for row in csv.DictReader(f):
        code = (row.get('shobi_code') or '').strip().upper()
        fid = (row.get('fragrantica_id') or '').strip()
        status = (row.get('status') or '').strip().upper()
        if code and fid.isdigit() and status in {'DOWNLOADED', 'EXISTS'}:
            image_map[code] = f'perfume-images/{fid}.avif'

MAP_JS.write_text(
    'window.PERFUME_IMAGE_MAP=' + json.dumps(image_map, ensure_ascii=False, separators=(',', ':')) + ';\n',
    encoding='utf-8'
)

html = INDEX.read_text(encoding='utf-8')

# Load the local image map before the V2-card enhancement script.
needle = '<script src="script.js"></script>\n<script>(()=>{'
replacement = '<script src="script.js"></script>\n<script src="perfume-images/map.js"></script>\n<script>(()=>{'
if needle in html and 'perfume-images/map.js' not in html:
    html = html.replace(needle, replacement, 1)

# Give applyV2Card the matching perfume row so it can resolve the archived image.
html = html.replace(
    "const applyV2Card=card=>{if(!card||card.classList.contains('v2-test-card'))return;",
    "const applyV2Card=(card,perfume)=>{if(!card||card.classList.contains('v2-test-card'))return;",
    1,
)

# Replace the hard-coded bottle with the local image for that Shobi code; keep current bottle as fallback.
html = html.replace(
    "image.src='https://fimgs.net/mdimg/perfume-thumbs/dark-375x500.52616.avif';image.alt='Perfume bottle placeholder';image.loading='lazy';",
    "const perfumeCode=String((perfume&&perfume.item?perfume.item.code:perfume?.code)||'').trim().toUpperCase();image.src=(window.PERFUME_IMAGE_MAP&&window.PERFUME_IMAGE_MAP[perfumeCode])||'perfume-images/52616.avif';image.alt='Perfume bottle';image.loading='lazy';image.onerror=()=>{image.onerror=null;image.src='perfume-images/52616.avif';};",
    1,
)

html = html.replace(
    "const applyV2Cards=()=>document.querySelectorAll('#resultsContainer > div').forEach(applyV2Card);",
    "const applyV2Cards=(perfumes=[])=>document.querySelectorAll('#resultsContainer > div').forEach((card,index)=>applyV2Card(card,perfumes[index]));",
    1,
)

html = html.replace(
    "applyV2Cards();};const normalizeNoteName=",
    "applyV2Cards(perfumes);};const normalizeNoteName=",
    1,
)

INDEX.write_text(html, encoding='utf-8')
print(f'image_map_entries={len(image_map)}')
