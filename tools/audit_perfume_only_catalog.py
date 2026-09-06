import json,re
from collections import Counter
P='database_complete.json'
D=json.load(open(P,encoding='utf-8'))
rows=[]
for g in D:
    brand=(g.get('brandInfo') or {}).get('name','')
    for p in g.get('perfumes',[]): rows.append({'brand':brand,**p})
# Deliberately broad exclusion vocabulary. Candidates are reported, not auto-deleted.
terms={
'home':['home fragrance','home fragrances','room spray','air freshener','diffuser','reed diffuser','candle','wax melt','burner','incense','bamboo','car perfume','aroma oil','aroma oils','bukhoo','bukhoor'],
'body_cosmetic':['body lotion','body butter','body cream','shower gel','bath bomb','face mist','hair oil','massage oil','beard oil','essential oil','base oil'],
'accessory':['perfume bottle','bottle empty','atomizer','accessor']}
fields=['perfume','inspiredBy','category','shobiUrl','code','reference']
candidates=[]
for r in rows:
    text=' | '.join(str(r.get(k,'') or '') for k in fields).lower()
    hits=[]
    for typ,words in terms.items():
        for w in words:
            if w in text: hits.append((typ,w))
    if hits: candidates.append((r,hits))
# Category/URL structural classification: Shobi perfume catalog URLs/categories.
perfume_url_markers=['/fragrances-for-women/','/fragrances-for-men/','/niche-perfumes/','/elegants-fragrances/','/arabian-perfumes/','/luxury-perfumes/','/musk/','/layered-perfumes/','/al-haramain-oriental-perfumes/','/paris-corner/','/lattafa/']
nonperf_url_markers=['/home-fragrances/','/scented-candles/','/air-fresheners/','/home-reed-diffusers/','/perfume-bottles/','/wax-melts/','/burner-oils/','/incense','/body-care/']
nonperf_urls=[]; perfume_urls=[]; unknown_urls=[]
for r in rows:
    u=str(r.get('shobiUrl','') or '').lower()
    if any(x in u for x in nonperf_url_markers): nonperf_urls.append(r)
    elif any(x in u for x in perfume_url_markers): perfume_urls.append(r)
    else: unknown_urls.append(r)
out=[]
out += ['# Perfume-only catalog audit','',f'- Rows: **{len(rows)}**',f'- Explicit non-perfume keyword candidates: **{len(candidates)}**',f'- Explicit non-perfume Shobi URL-category rows: **{len(nonperf_urls)}**',f'- Recognized perfume-category URL rows: **{len(perfume_urls)}**',f'- Other/legacy/no-category URL rows requiring source-based interpretation: **{len(unknown_urls)}**','']
out += ['## Explicit non-perfume URL-category rows']
for r in nonperf_urls: out.append(f"- {r.get('code','')} | {r['brand']} | {r.get('perfume','')} | {r.get('shobiUrl','')}")
out += ['','## Keyword candidates (manual review; product pages may offer home/body variants of a perfume)']
for r,h in candidates: out.append(f"- {r.get('code','')} | {r['brand']} | {r.get('perfume','')} | hits={h} | {r.get('shobiUrl','')}")
out += ['','## Unknown/legacy URL forms']
for r in unknown_urls: out.append(f"- {r.get('code','')} | {r['brand']} | {r.get('perfume','')} | {r.get('shobiUrl','')}")
open('catalog-perfume-only-audit.md','w',encoding='utf-8').write('\n'.join(out)+'\n')
print('rows',len(rows),'keyword_candidates',len(candidates),'nonperf_urls',len(nonperf_urls),'perfume_urls',len(perfume_urls),'unknown_urls',len(unknown_urls))