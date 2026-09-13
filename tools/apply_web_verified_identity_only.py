#!/usr/bin/env python3
"""Apply identity provenance for the 20 identity-only rows verified from their exact Fragrantica pages.
The mapping is explicit; script refuses any code/URL/FID drift.
"""
import json,re
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
DB=ROOT/'database_complete.json'
rows=json.loads(DB.read_text(encoding='utf-8-sig'))
VERIFIED={
'2044-LORV':'https://www.fragrantica.com/perfume/Lorenzo-Villoresi/Teint-de-Neige-5079.html',
'1986-SOO':'https://www.fragrantica.com/perfume/SoOud/Nur-10016.html',
'1682-HER':'https://www.fragrantica.com/perfume/Hermes/24-Faubourg-27.html',
'1126-ARM':'https://www.fragrantica.com/perfume/Giorgio-Armani/Acqua-di-Gio-Profondo-59532.html',
'1046-CAL':'https://www.fragrantica.com/perfume/Calvin-Klein/CK-Everyone-Eau-de-Toilette-59021.html',
'495-CHA':'https://www.fragrantica.com/perfume/Chanel/Allure-Sensuelle-606.html',
'943-VER':'https://www.fragrantica.com/perfume/Versace/Bright-Crystal-632.html',
'926-TOM':'https://www.fragrantica.com/perfume/Tommy-Hilfiger/Tommy-Girl-3016.html',
'912-SHIS':'https://www.fragrantica.com/perfume/Shiseido/Zen-1499.html',
'850-NIN':'https://www.fragrantica.com/perfume/Nina-Ricci/L-Air-du-Temps-1014.html',
'778-LAN':'https://www.fragrantica.com/perfume/Lancome/Climat-180.html',
'751-KEN':'https://www.fragrantica.com/perfume/Kenzo/Jeu-d-Amour-25866.html',
'696-GLA':'https://www.fragrantica.com/perfume/guy-laroche/fidji-2068.html',
'515-CHL':'https://www.fragrantica.com/perfume/Chloe/Nomade-48434.html',
'441-BLG':'https://www.fragrantica.com/perfume/Bvlgari/Jasmin-Noir-3750.html',
'1284-YZLO':'https://www.fragrantica.com/perfume/Yves-Saint-Laurent/M7-1031.html',
'1270-VAN':'https://www.fragrantica.com/perfume/Van-Cleef-Arpels/Bois-Dore-44864.html',
'1247-RAL':'https://www.fragrantica.com/perfume/Ralph-Lauren/Polo-Red-18598.html',
'1149-GUR':'https://www.fragrantica.com/perfume/Guerlain/L-Homme-Ideal-25780.html',
'390-ACQ':'https://www.fragrantica.com/perfume/Acqua-di-Parma/Acqua-di-Parma-Blu-Mediterraneo-Mandorlo-di-Sicilia-1688.html',
}
def fid(url):
    m=re.search(r'-(\d+)\.html(?:$|[?#])',url); return m.group(1) if m else ''
by_code={str(r.get('code') or '').strip().upper():r for r in rows}
changed=[]
for code,url in VERIFIED.items():
    r=by_code.get(code)
    if not r: raise SystemExit(f'Missing code {code}')
    current=str(r.get('fragranticaUrl') or '').strip()
    current_fid=str(r.get('fragranticaId') or '').strip()
    if current!=url or current_fid!=fid(url):
        raise SystemExit(f'Identity drift {code}: {current} / {current_fid} != {url} / {fid(url)}')
    if str(r.get('identityStatus') or '').strip().upper() not in {'CONFIRMED','VERIFIED','VALIDATED','OK'}:
        raise SystemExit(f'Identity status not accepted for {code}')
    r['fragranticaVerificationSource']=url
    r['fragranticaVerificationReason']='WEB_DIRECT_FRAGRANTICA_PAGE_NAME_BRAND_ID_VERIFIED_2026-09-14'
    r['fragranticaVerificationFragranticaId']=current_fid
    changed.append({'code':code,'fragranticaId':current_fid,'source':url})
DB.write_text(json.dumps(rows,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
(ROOT/'web-verified-identity-only-fixes.json').write_text(json.dumps({'changed':len(changed),'rows':changed},ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
print('web_verified_identity_only',len(changed))
