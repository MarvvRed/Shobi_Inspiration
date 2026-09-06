import csv,json
from pathlib import Path
DB=Path('database_complete.json')
MASTER=Path('perfume-database/catalog/shobi-master-v1.csv')
TARGET={'2604-JILS','2773-RIT','2783-LTN','2786-LTN','2791-LTN','846-NRO'}
data=json.loads(DB.read_text(encoding='utf-8'))
existing={str(p.get('code') or '').strip().upper() for g in data for p in g.get('perfumes',[])}
with MASTER.open(encoding='utf-8-sig',newline='') as f: master={r['shobi_code'].strip().upper():r for r in csv.DictReader(f) if r['shobi_code'].strip().upper() in TARGET}
missing=TARGET-existing
if set(master)!=TARGET: raise SystemExit(f'master target missing: {TARGET-set(master)}')
# Do not invent identities for the three truncated LTN records: preserve master evidence exactly.
added=[]
for code in sorted(missing):
 r=master[code]
 # Prefer an existing brand bucket inferred from code/identity only for known exact brands; otherwise a Shobi bucket.
 known={'2604-JILS':'Jil Sander','2773-RIT':'Rituals','846-NRO':'Narciso Rodriguez'}
 brand=known.get(code,'Shobi')
 group=next((g for g in data if (g.get('brandInfo') or {}).get('name','').casefold()==brand.casefold()),None)
 if group is None:
  group={'brandInfo':{'name':brand},'perfumes':[]}; data.append(group)
 p={'code':code,'inspiredBy':r.get('inspired_by',''),'prestashopProductId':r.get('prestashop_product_id',''),'shobiUrl':r.get('url','')}
 group.setdefault('perfumes',[]).append(p); added.append((code,brand,r.get('inspired_by','')))
DB.write_text(json.dumps(data,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
print('added',len(added))
for x in added: print(x)
