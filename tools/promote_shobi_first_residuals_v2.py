#!/usr/bin/env python3
import json
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DBS = [ROOT / 'database_v2_clean.json', ROOT / 'database_complete.json']
URLS = ROOT / 'fragrantica-scraper-archive/legacy/original-local-scraper/perfume_urls.txt'
OUT = ROOT / 'fragrantica-v2-shobi-first-promotion.md'

# code: (Fragrantica ID, brand, exact target name, review rationale)
# Identity is established from Shobi first; Fragrantica is consulted only after that.
APPROVED = {
    '133-MICA': ('14409', 'M. Micallef', 'Ylang in Gold', 'Shobi identifies YLANG IN GOLD - M.MICALLEF; base entry, not Nectar flanker'),
    '166-AZ': ('40007', "The Perfumer's Story by Azzi", 'Sequoia Wood', 'Shobi identifies Sequoia Wood by The Perfumer Story by Azzi'),
    '184-YAS': ('28237', 'Yas Perfumes', 'Huboob Yas', 'Shobi identifies HUBOOB with YAS/Yas Perfumes identity'),
    '605-ESC': ('53054', 'Escada', 'Miami Blossom', 'Shobi identifies MIAMI BLOSSOM - ESCADA; rejects wrong-brand Blossom candidates'),
    '606-ESC': ('1365', 'Escada', 'Escada Margaretha Ley', 'Shobi identifies MARGARETHA LEY (CLASSIC) - ESCADA'),
    '608-ESC': ('1887', 'Escada', 'Escada Moon Sparkle', 'Shobi identifies women Moon Sparkle; not Moon Sparkle pour Homme'),
    '639-FEN': ('200', 'Fendi', 'Fendi', 'Shobi identifies FENDI Woman; original 1985 women entry'),
    '640-FEN': ('18706', 'Fendi', "L'Acquarossa", 'Shobi identifies L ACQUA ROSSA without EDT/Elixir qualifier; base EDP'),
    '673-GRS': ('1061', 'Gres', 'Cabotine', 'Shobi identifies CABOTIN - GRES; original Cabotine, not flanker'),
    '695-GUE': ('26415', 'Guess', 'Guess Dare', 'Shobi identifies DARE - GUESS; base 2014, not Limited Edition'),
    '696-GLA': ('2068', 'Guy Laroche', 'Fidji Eau de Toilette', 'Shobi explicitly identifies FIDJI EAU DE TOILETTE - GUY LAROCHE'),
    '727-JEN': ('29758', 'Jennifer Lopez', 'JLuxe', 'Shobi identifies JLUXE - JENNIFER LOPEZ'),
    '728-JES': ('719', 'Jesus Del Pozo', 'In Black', 'Shobi identity fixes Jesus Del Pozo; rejects wrong-brand Byblos exact-name candidate'),
    '807-LOL': ('456', 'Lolita Lempicka', 'Lolita Lempicka', 'Shobi identifies LOLITA - LOLITA LEMPICKA; original signature entry'),
    '808-LOL': ('28177', 'Lolita Lempicka', 'Sweet', 'Shobi Sweet notes identify Lolita Lempicka Sweet 2014'),
    '816-MAX': ('204', 'Max Mara', 'Max Mara', 'Shobi identifies MAX MARA; signature perfume'),
    '817-MIC': ('31341', 'Michael Kors', '24K Brilliant Gold', 'Shobi identifies 24K BRILLIANT GOLD - KORS'),
    '818-MIC': ('32739', 'Michael Kors', 'Coral', 'Shobi identifies CORAL - KORS'),
    '819-MIC': ('18161', 'Michael Kors', 'Sexy Amber', 'Shobi identifies SEXY AMBER - KORS'),
    '820-MIC': ('27497', 'Michael Kors', 'Sexy Rio de Janeiro', 'Shobi identifies SEXY RIO DE JANEIRO KORS; 2014 release'),
    '821-MIC': ('34276', 'Michael Kors', 'Sexy Sunset', 'Shobi identifies SEXY SUNSET - KORS; 2015 release'),
    '822-MIC': ('46182', 'Michael Kors', 'Sexy Ruby', 'Shobi identifies SEXY RUBY - KORS despite noisy residual label'),
    '823-MIC': ('18160', 'Michael Kors', 'Sporty Citrus', 'Shobi identifies SPORTY CITRUS - MICHAEL KORS'),
    '824-MIC': ('31343', 'Michael Kors', 'White Luminous Gold', 'Shobi identifies WHITE LUMINOUS GOLD - MICHAEL KORS'),
    '902-SALV': ('970', 'Salvador Dali', 'Dalissime', 'Shobi identifies DALISSIME - SALVADOR DALI; original 1994 entry'),
    '905-SFER': ('46832', 'Salvatore Ferragamo', 'Amo Ferragamo', 'Shobi identifies AMO - S.FERRAGAMO; base 2018, not Limited Edition/Flowerful'),
    '906-SFER': ('28117', 'Salvatore Ferragamo', 'Emozione', 'Shobi identifies EMOZIONE - S.FERRAGAMO; base 2015 entry'),
    '907-SFER': ('13639', 'Salvatore Ferragamo', 'Signorina', 'Shobi identifies SIGNORINA - FERRAGAMO; base 2011 entry'),
    '908-SFER': ('32646', 'Salvatore Ferragamo', 'Signorina Misteriosa', 'Shobi identifies SIGNORINA MISTERIOSA - FERRAGAMO; 2016 flanker'),
    '909-SFER': ('26777', 'Salvatore Ferragamo', 'White Mimosa', 'Shobi identifies TUSCAN SCENT WHITE MIMOSA - FERRAGAMO'),
    '910-SARJ': ('993', 'Sarah Jessica Parker', 'Lovely', 'Shobi identifies LOVELY - SARA JESSICA PARKER; original 2005 entry'),
    '911-SEPH': ('37955', 'Sephora', 'Fleur de Coton (Cotton Flower)', 'Shobi identifies FLEUR DE COTON / COTTON FLOWER - SEPHORA'),
    '912-SHIS': ('1499', 'Shiseido', 'Zen', 'Shobi identifies ZEN - SHISEIDO; 2007 Zen entry'),
    '1187-JOV': ('7524', 'Jovan', 'White Musk', 'Shobi identifies WHITE MUSK - JOVAN; women 1990 entry'),
    '1196-LAC': ('41265', 'Lacoste', 'Eau de Lacoste L.12.12 Magnetic Pour Lui', 'Shobi residual identity is L.12.12 MAGNETIC under Lacoste code; men Magnetic entry'),
    '1205-LOL': ('458', 'Lolita Lempicka', 'Au Masculin', 'Shobi residual identity is Au Masculin under Lolita Lempicka code; original 2000 entry'),
    '1224-APO': ('925', 'Nikos', 'Sculpture Homme', 'Shobi identifies SCULPTURE - NIKOS APOSTOLOPOULOS; original 1995 entry'),
    '1259-SHU': ('14746', 'Shulton Company', 'Old Spice Original', 'Shobi identifies OLD SPICE - SHULTON COMPANY and original 1938 identity'),
    '1926-KOS': ('53742', 'Thomas Kosmala', 'No. 4 Apres l Amour Eau de Parfum', 'Shobi-first correction: APRES L AMOUR - THOMAS KOSMALA; corrects old Kerosene metadata'),
    '1975-ZARK': ('25474', 'ZARKOPERFUME', 'Pink Molecule 090.09', 'Shobi identifies PINK MOLECULE 090.09 - ZARKOPERFUME; 2014 entry'),
    '1977-SHIS': ('65234', 'Shiseido', 'Ginza', 'Shobi residual explicitly says Ginza (2021) under Shiseido code; exact 2021 entry'),
    '1980-HIND': ('87692', 'Hind Al Oud', 'Emarati Musk', 'Shobi identifies EMARATI MUSK PARFUM - HIND AL OUD'),
    '1981-KHAL': ('22907', 'Khaltat', 'Gra', 'Shobi identifies GRA - KHALTAT'),
    '1985-WID': ('54883', 'WIDIAN', 'Gold II Sahara', 'Shobi identifies GOLD II SAHARA - WIDIAN; 2019 entry'),
    '1986-SOO': ('10016', 'SoOud', 'Nur', 'Shobi identifies NUR - SoOUD'),
    '1987-SON': ('4655', 'Sonia Rykiel', 'Le Parfum', 'Shobi identifies LE PARFUM - SONIA RYKIEL with no Extrait qualifier; base 1993 entry'),
    '1988-THEVE': ('32670', 'The Merchant of Venice', 'Arabesque', 'Shobi identifies ARABESQUE - THE MERCHANT OF VENICE; 2015 entry'),
    '1989-VERT': ('47923', 'Vertus', "Narcos'is", "Shobi residual NARCOS'IS under Vertus code; exact Vertus entry"),
}

# Identified from Shobi, deliberately not forced onto a different perfume/brand.
NO_FORCE = {
    '130-LEL': ('Le Labo', 'Santal 26', 'home fragrance/home oil identity; do not substitute Santal 33'),
    '200-CIR': ('Cire Trudon', 'Ernesto / Che Guevara', 'home scent/candle identity; do not substitute a different perfume'),
    '222-DIP': ('Diptyque', 'Ambre', 'home fragrance identity; do not substitute a Diptyque perfume'),
    '223-DIP': ('Diptyque', 'Baies', 'candle/home fragrance identity; do not substitute a perfume'),
    '227-DIP': ('Diptyque', 'Feu de Bois / Wood Fire', 'candle/home fragrance identity; do not substitute a perfume'),
    '612-ESC': ('Escada', 'Turquoise', 'Shobi distinguishes Turquoise from separate Turquoise Summer; no safe exact perfume target yet'),
    '1251-ROM': ('Romane', 'Royal Blue', 'Shobi identity is Royal Blue - Romane; no safe same-brand Fragrantica target found'),
}

def walk(obj):
    if isinstance(obj, list):
        for item in obj:
            yield from walk(item)
    elif isinstance(obj, dict):
        if isinstance(obj.get('perfumes'), list):
            for perfume in obj['perfumes']:
                if isinstance(perfume, dict):
                    yield perfume
        elif 'code' in obj or 'inspiredBy' in obj:
            yield obj

need = {value[0] for value in APPROVED.values()}
urls = {}
for raw in URLS.read_text(encoding='utf-8', errors='ignore').splitlines():
    line = raw.strip()
    match = re.search(r'-(\d+)\.html(?:\?.*)?$', line)
    if match and match.group(1) in need:
        urls[match.group(1)] = line

promoted = set()
already_verified = set()
missing_from_corpus = set()
changed = {}

for path in DBS:
    data = json.loads(path.read_text(encoding='utf-8-sig'))
    count = 0
    for perfume in walk(data):
        code = str(perfume.get('code') or '').strip()
        if code not in APPROVED:
            continue
        fid, brand, name, rationale = APPROVED[code]
        if fid not in urls:
            missing_from_corpus.add(code)
            continue
        current_status = str(perfume.get('fragranticaStatus') or '')
        current_id = str(perfume.get('fragranticaId') or '')
        if current_status.startswith('VERIFIED_') and current_id == fid:
            already_verified.add(code)
            continue
        if current_status.startswith('VERIFIED_') and current_id and current_id != fid:
            # Never silently overwrite a conflicting verified mapping.
            continue
        perfume['fragranticaId'] = fid
        perfume['fragranticaStatus'] = 'VERIFIED_LOCAL_CORPUS_V2'
        perfume['fragranticaLocalUrl'] = urls[fid]
        perfume['fragranticaVerificationSource'] = 'Shobi-first reviewed identity + local Fragrantica corpus'
        count += 1
        promoted.add(code)
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
    changed[path.name] = count

lines = [
    '# Shobi-first residual promotion',
    '',
    f'- Reviewed exact identities with Fragrantica target: **{len(APPROVED)}**',
    f'- Target IDs present in local corpus: **{sum(1 for c,v in APPROVED.items() if v[0] in urls)}**',
    f'- Target IDs missing from local corpus: **{sum(1 for c,v in APPROVED.items() if v[0] not in urls)}**',
    f'- Promoted this run: **{len(promoted)}**',
    f'- Already verified with same ID: **{len(already_verified)}**',
    f'- Identified but deliberately not forced: **{len(NO_FORCE)}**',
]
for name, count in changed.items():
    lines.append(f'- {name}: **{count}** rows changed')
lines += ['', '## Promoted / exact targets', '']
for code, (fid, brand, name, rationale) in APPROVED.items():
    corpus = 'IN_CORPUS' if fid in urls else 'MISSING_FROM_CORPUS'
    lines.append(f'- `{code}` -> {brand} / {name} — ID {fid} — {corpus} — {rationale}')
lines += ['', '## Identified but not forced', '']
for code, (brand, name, reason) in NO_FORCE.items():
    lines.append(f'- `{code}` -> {brand} / {name} — NO_FORCE — {reason}')
OUT.write_text('\n'.join(lines) + '\n', encoding='utf-8')

print('reviewed', len(APPROVED))
print('in_corpus', sum(1 for c,v in APPROVED.items() if v[0] in urls))
print('missing_from_corpus', sum(1 for c,v in APPROVED.items() if v[0] not in urls))
print('promoted', len(promoted))
print('already_verified', len(already_verified))
print('no_force', len(NO_FORCE))
print('changed', changed)
