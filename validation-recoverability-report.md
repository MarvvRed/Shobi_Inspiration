# Validation recoverability report

- Yellow rows inspected: **266**

## Existing-evidence patterns

- `gender_label_only`: **155** — samples: 2816-MOOD, 490-CRT, 2552-SOR, 2483-CLEA, 2482-CLEA, 2439-ZEG, 2427-CLEA, 2351-LOU, 2313-DRC, 2301-DIP, 2250-ARBAS, 2160-ZAR
- `gender_csv_exact_match`: **143** — samples: 490-CRT, 2552-SOR, 2483-CLEA, 2482-CLEA, 2439-ZEG, 2427-CLEA, 2351-LOU, 2301-DIP, 2250-ARBAS, 2160-ZAR, 2193-LTN, 2190-ROJ
- `gender_exact_card_exists`: **136** — samples: 490-CRT, 2483-CLEA, 2482-CLEA, 2439-ZEG, 2427-CLEA, 2351-LOU, 2313-DRC, 2301-DIP, 2250-ARBAS, 2160-ZAR, 2193-LTN, 2190-ROJ
- `social_raw_same_id`: **77** — samples: 2533-RAL, 2514-DRC, 2513-PAC, 2439-ZEG, 2427-CLEA, 2351-LOU, 2313-DRC, 2282-DRC, 2250-ARBAS, 2224-ARM, 2160-ZAR, 2133-FRE
- `social_validated_same_id`: **21** — samples: 2533-RAL, 2514-DRC, 2513-PAC, 2313-DRC, 2133-FRE, 2106-MARC, 1950-SWISA, 1767-LTN, 1504-DON, 843-NRO, 734-JIM, 718-ISS
- `image_file_exists_unmapped`: **9** — samples: 2514-DRC, 2313-DRC, 2282-DRC, 2133-FRE, 2106-MARC, 1950-SWISA, 1767-LTN, 1644-DRC, 1076-DRC

## Identity status

- `CONFIRMED`: **262**
- `AMBIGUOUS`: **4**

## Identity source

- `<EMPTY>`: **180**
- `fragrantica-v2-identity-audit.csv`: **78**
- `https://www.fragrantica.com/perfume/Dior/Sauvage-Eau-Forte-95863.html`: **1**
- `https://www.fragrantica.com/perfume/Dior/Dioriviera-81847.html`: **1**
- `https://www.fragrantica.com/perfume/Orto-Parisi/Cuoium-69923.html`: **1**
- `https://www.fragrantica.com/perfume/Frederic-Malle/Lipstick-Rose-2799.html`: **1**
- `https://www.fragrantica.com/perfume/Narciso-Rodriguez/Pure-Musc-For-Her-53441.html`: **1**
- `https://www.fragrantica.com/perfume/Jimmy-Choo/Stars-27431.html`: **1**
- `https://www.fragrantica.com/perfume/Jimmy-Choo/Jimmy-Choo-10573.html`: **1**
- `https://www.fragrantica.com/perfume/Calvin-Klein/CK-be-275.html`: **1**

## Gender status

- `<EMPTY>`: **186**
- `VALIDATED_SOCIAL_CARD`: **80**

## Social-card status

- `<EMPTY>`: **184**
- `VALIDATED_OCR`: **51**
- `VALIDATED_MANUAL`: **29**
- `SOCIAL_CARD_UNAVAILABLE`: **2**
