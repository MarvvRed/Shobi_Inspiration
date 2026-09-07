#!/usr/bin/env python3
import json,re
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
DBS=[ROOT/'database_v2_clean.json',ROOT/'database_complete.json'];URLS=ROOT/'fragrantica-scraper-archive/legacy/original-local-scraper/perfume_urls.txt';OUT=ROOT/'fragrantica-v2-reviewed-historical-residuals.md'
APPROVED={
 '2600-TMU':('714','Mugler','Angel Garden Of Stars Le Lys','historical local ID; Angel Lily clearly corresponds to Le Lys within Angel Garden of Stars'),
 '734-JIM':('10573','Jimmy Choo','Jimmy Choo','historical local ID; Shobi row only carries Eau de Parfum concentration for base Jimmy Choo'),
 '843-NRO':('72604','Narciso Rodriguez','Narciso Rodriguez For Her Pink Edition','reconciliation local-better candidate has full Pink identity and same brand'),
 '1034-BLG':('153','Bvlgari','Aqva Pour Homme','historical local base Aqva ID; Shobi says generic AQUA, not Edition Limitee'),
 '1080-DRC':('230','Dior','Dior Homme 2005','historical local ID for generic HOMME row; same Dior brand and base Homme identity'),
 '1092-DOL':('490','Dolce Gabbana','By','historical local ID; By Man Eau de Toilette maps to original By entry rather than The One'),
 '1094-DOL':('56358','Dolce Gabbana','K by Dolce Gabbana','same-brand historical local ID; K KING 2019 preserves K identity and launch year'),
 '1135-ARM':('416','Giorgio Armani','Emporio Armani Lui','same-brand historical local ID; LUI/IL/HE/EL are multilingual male labels matching Lui'),
 '1654-ACQ':('1681','Acqua di Parma','Acqua di Parma Colonia','same-brand historical local ID; Colonia 1916 identifies original Colonia and its launch year'),
 '2012-DOL':('78873','Dolce Gabbana','Q by Dolce Gabbana','same-brand historical local ID; Q QUEEN directly preserves Q identity'),
 '2017-DIE':('74965','Diesel','D by Diesel','same-brand historical local ID; one-letter D is the exact product identity'),
 '508-CHA':('15963','Chanel','Coco Noir','same-brand historical local ID; Shobi Coco Black is a direct Black/Noir label variant'),
 '651-ARM':('417','Giorgio Armani','Emporio Armani Lei','same-brand historical local ID; LEI/ELLE/SHE/ELLA are multilingual female labels matching Lei'),
 '677-GUC':('1150','Gucci','Gucci by Gucci Eau de Parfum','same-brand historical local ID; G by G is an explicit abbreviation of Gucci by Gucci'),
 '2185-DRC':('232','Dior','Eau Sauvage Extreme','same-brand local corpus exact core identity; Shobi Extrme Intense is a noisy label for Eau Sauvage Extreme'),
 '2609-TMFO':('15916','Tom Ford','Ombre de Hyacinth','same-brand historical and local candidate agree on distinctive Hyacinth identity'),
 '621-EST':('43639','Estee Lauder','Bronze Goddess Eau de Parfum','same-brand exact product identity in local corpus; concentration explicitly matches Eau de Parfum'),
 '1769-LTN':('40495','Louis Vuitton','Rose des Vents','same-brand historical local ID; Shobi label is notes-style Roses rather than a competing product title'),
 '717-ISS':('720','Issey Miyake','L eau d Issey','same-brand historical ID and current local top candidate agree; CLASSIC identifies the original L Eau d Issey'),
 '1014-AZZ':('829','Azzaro','Azzaro pour Homme','same-brand historical local ID; CLASSIC is the generic original Azzaro masculine fragrance'),
 '1998-LTN':('53947','Louis Vuitton','Afternoon Swim','same-brand historical local ID; Shobi description is the citrus unisex description associated with Afternoon Swim'),
 '502-CHA':('608','Chanel','Chanel N05 Vintage','same-brand historical local base No 5 identity; generic No 5 should not be forced to L Eau flanker'),
 '1021-BOG':('7795','Jacques Bogart','One Man Show','two local historical sources agree; Shobi explicitly says One Man Show Eau de Toilette'),
 '1116-ZEG':('28142','Ermenegildo Zegna','Uomo Absolute','two local historical sources agree; UOMO ABSOLUT and explicit Zegna label preserve identity'),
 '1118-FAB':('38206','Faberge','Brut 1964','two local historical sources agree; distinctive BRUT 1964 identity'),
 '1151-HAL':('3697','Halston','Z-14','two local historical sources agree; Shobi explicitly says Halston Z-14 Cologne'),
 '1184-JOO':('1251','Joop!','Joop! Homme','two local historical sources agree; JOOP - JOOP is the original Joop identity'),
 '1186-JOO':('42887','Joop!','Wow!','two local historical sources agree; explicit WOW - JOOP identity'),
 '1197-LAC':('670','Lacoste','Lacoste pour Homme','two local historical sources agree; LACOSTE HOMME directly identifies the masculine original'),
 '1201-LBI':('3002','Laura Biagiotti','Venezia Uomo','two local historical sources agree; exact distinctive Venezia Uomo identity'),
 '1236-PAL':('1695','Paloma Picasso','Minotaure','two local historical sources agree; exact distinctive Minotaure identity'),
 '1254-RCAV':('848','Roberto Cavalli','Just Cavalli Him','two local historical sources agree; JUST HIM plus explicit ROBERTO CAVALLI label'),
 '118-HAM':('27808','Hamidi Oud','Rehan','two local historical sources agree; explicit REHAN - HAMIDI OUD identity'),
 '171-DUP':('21459','Dupont','Souvenirs de Malles Oud Oriental','two local historical sources agree; exact distinctive Oud Oriental product title'),
 '172-SHALM':('47982','Shalimar','Moroccan Musk','two local historical sources agree; exact distinctive Moroccan Musk title'),
 '1743-LBI':('1185','Laura Biagiotti','Sotto Voce','two local historical sources agree; exact distinctive Sotto Voce identity'),
 '1756-LBI':('628','Laura Biagiotti','Roma','two local historical sources agree; explicit ROMA - LAURA BIAGIOTTI identity'),
 '1784-ESC':('64643','Escada','Summer Festival','two local historical sources agree; exact Summer Festival Eau de Toilette identity'),
 '1896-ESC':('70279','Escada','Cherry in Japan','two local historical sources agree; exact distinctive Cherry in Japan identity'),
 '1899-ZARK':('60665','Zarkoperfume','The Muse','two local historical sources agree; exact distinctive The Muse identity'),
 '1926-KOS':('53742','Kerosene','Unknown Pleasures No 4 Apres l Amour','two local historical sources agree on distinctive No. 4 Apres l Amour identity'),
 '133-MICA':('14409','M. Micallef','Ylang in Gold','Shobi-first: official Shobi code page identifies YLANG IN GOLD - M.MICALLEF; exact Fragrantica base entry, not Nectar flanker'),
 '166-AZ':('40007',"The Perfumer's Story by Azzi",'Sequoia Wood','Shobi-first: Shobi code and description identify Sequoia Wood by The Perfumer Story by Azzi; exact Fragrantica entry'),
 '184-YAS':('28237','Yas Perfumes','Huboob Yas','Shobi-first: HUBOOB with YAS code identifies Yas Perfumes Huboob; exact Fragrantica Yas entry, not Junaid Huboob'),
 '605-ESC':('53054','Escada','Miami Blossom','Shobi-first: official Shobi page identifies MIAMI BLOSSOM - ESCADA; exact Fragrantica 2019 EDT entry'),
 '606-ESC':('1365','Escada','Escada Margaretha Ley','Shobi-first: official Shobi page identifies MARGARETHA LEY (CLASSIC) - ESCADA; exact 1990 Fragrantica entry'),
 '608-ESC':('1887','Escada','Escada Moon Sparkle','Shobi-first: official Shobi code page and notes identify women Moon Sparkle; exact 2007 women entry, not pour Homme'),
 '639-FEN':('200','Fendi','Fendi','Shobi-first: official Shobi page identifies FENDI Woman; exact original 1985 women Fendi entry'),
 '640-FEN':('18706','Fendi',"L'Acquarossa",'Shobi-first: Shobi label is L ACQUA ROSSA without EDT/Elixir qualifier; exact base 2013 EDP entry'),
 '673-GRS':('1061','Gres','Cabotine','Shobi-first: official Shobi page identifies CABOTIN - GRES; exact original 1990 Cabotine entry, not later flankers'),
 '695-GUE':('26415','Guess','Guess Dare','Shobi-first: official Shobi page identifies DARE - GUESS; exact 2014 base Dare, not 2015 Limited Edition'),
 '696-GLA':('2068','Guy Laroche','Fidji Eau de Toilette','Shobi-first: official Shobi page explicitly identifies FIDJI EAU DE TOILETTE - GUY LAROCHE; exact EDT entry'),
 '727-JEN':('29758','Jennifer Lopez','JLuxe','Shobi-first: official Shobi page identifies JLUXE - JENNIFER LOPEZ; exact Fragrantica entry'),
 '728-JES':('719','Jesus Del Pozo','In Black','Shobi-first: Shobi code/identity resolves to Jesus Del Pozo In Black; exact Fragrantica entry, rejecting wrong-brand Byblos exact-name candidate'),
 '807-LOL':('456','Lolita Lempicka','Lolita Lempicka','Shobi-first: official Shobi page identifies LOLITA - LOLITA LEMPICKA; exact original 1997 signature entry, not EDT/later reformulations'),
 '808-LOL':('28177','Lolita Lempicka','Sweet','Shobi-first: Shobi code page notes candied cherry, cocoa, angelica, iris, musk and cashmere wood exactly identify Sweet 2014'),
 '816-MAX':('204','Max Mara','Max Mara','Shobi-first: official Shobi listing identifies MAX MARA; exact 2004 signature perfume'),
 '817-MIC':('31341','Michael Kors','24K Brilliant Gold','Shobi-first: official Shobi page identifies 24K BRILLIANT GOLD - KORS; exact 2015 Gold Collection entry'),
 '818-MIC':('32739','Michael Kors','Coral','Shobi-first: official Shobi listing identifies CORAL - KORS; exact 2015 Michael Kors Coral entry'),
 '819-MIC':('18161','Michael Kors','Sexy Amber','Shobi-first: official Shobi page identifies SEXY AMBER - KORS; exact 2013 entry'),
 '820-MIC':('27497','Michael Kors','Sexy Rio de Janeiro','Shobi-first: official Shobi page identifies SEXY RIO DE JANEIRO KORS and 2014 release; exact Fragrantica entry'),
 '821-MIC':('34276','Michael Kors','Sexy Sunset','Shobi-first: official Shobi page identifies SEXY SUNSET - KORS and 2015 release; exact Fragrantica entry'),
 '822-MIC':('46182','Michael Kors','Sexy Ruby','Shobi-first: official Shobi listing identifies SEXY RUBY - KORS; exact 2017 entry despite noisy residual label'),
 '823-MIC':('18160','Michael Kors','Sporty Citrus','Shobi-first: official Shobi page identifies SPORTY CITRUS - MICHAEL KORS and Honorine Blanc; exact 2013 entry'),
 '824-MIC':('31343','Michael Kors','White Luminous Gold','Shobi-first: official Shobi page identifies WHITE LUMINOUS GOLD - MICHAEL KORS, Gold Collection 2015; exact entry'),
}
def walk(o):
 if isinstance(o,list):
  for x in o:yield from walk(x)
 elif isinstance(o,dict):
  if isinstance(o.get('perfumes'),list):
   for p in o['perfumes']:
    if isinstance(p,dict):yield p
  elif 'code' in o or 'inspiredBy' in o:yield o
need={v[0] for v in APPROVED.values()};urls={}
for line in URLS.read_text(encoding='utf-8',errors='ignore').splitlines():
 m=re.search(r'-(\d+)\.html(?:\?.*)?$',line.strip())
 if m and m.group(1) in need:urls[m.group(1)]=line.strip()
changed={};promoted=set();skipped=set()
for path in DBS:
 data=json.loads(path.read_text(encoding='utf-8-sig'));n=0
 for p in walk(data):
  c=str(p.get('code') or '').strip()
  if c not in APPROVED:continue
  if str(p.get('fragranticaStatus') or '').startswith('VERIFIED_'):skipped.add(c);continue
  fid,b,nm,r=APPROVED[c]
  if fid not in urls:continue
  p['fragranticaId']=fid;p['fragranticaStatus']='VERIFIED_LOCAL_CORPUS_V2';p['fragranticaLocalUrl']=urls[fid];p['fragranticaVerificationSource']='reviewed historical/local residual mapping';n+=1;promoted.add(c)
 path.write_text(json.dumps(data,ensure_ascii=False,indent=2)+'\n',encoding='utf-8');changed[path.name]=n
lines=['# Reviewed historical residual promotion','',f'- Approved: **{len(APPROVED)}**',f'- Promoted this run: **{len(promoted)}**',f'- Already verified: **{len(skipped)}**']+[f'- {k}: **{v}** changed' for k,v in changed.items()]+['','## Mappings','']
for c,(fid,b,nm,r) in APPROVED.items():lines.append(f'- `{c}` -> {b} / {nm} — ID {fid} — {r}')
OUT.write_text('\n'.join(lines)+'\n',encoding='utf-8');print('approved',len(APPROVED),'promoted',len(promoted),'changed',changed,'skipped',len(skipped))
