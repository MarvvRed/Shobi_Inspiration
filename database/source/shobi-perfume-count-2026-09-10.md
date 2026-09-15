# Shobi official EN — wearable perfume count audit

**Audit date:** 2026-09-10
**Official source:** https://leparfum.com.gr/en/perfumes
**Language/catalog:** English (EN)

## Live official EN category counters

- Fragrances For Women: 855
- Fragrances For Men: 382
- Elegants Fragrances: 448
- Niche Perfumes: 612
- Luxury Perfumes: 40

Raw category-counter sum: **2,337**

Excluded from the working perfume universe:
- third-party perfume brands sold by the store
- home fragrances / room fragrances
- car fragrances / air fresheners
- candles / diffusers
- accessories / cosmetics
- Layered Perfumes (8), treated separately because they are combinations rather than standalone source perfume identities
- Musk (5), treated separately from the standard Shobi inspired-perfume identity catalog

## Full audit of shobi-master-v1.csv

The complete uploaded `shobi-master-v1.csv` contains:

- Total rows: **2,343**
- Unique non-empty Shobi codes across all categories: **2,311**
- Rows in the five wearable-perfume categories above: **2,304**
- Unique non-empty Shobi codes in those five categories: **2,285**
- Rows without `shobi_code` in those five categories: **15**
- Cross-category duplicate Shobi codes in those five categories: **4 codes / 8 rows**

Duplicate codes found:
- `1068-CHA` — Women + Men
- `1270-VAN` — Women + Men
- `390-ACQ` — Women + Men
- `777-LAL` — Women + Men

Master category counts:
- Fragrances For Women: 853 rows / 852 unique non-empty codes / 1 missing code
- Fragrances For Men: 381 rows / 377 unique non-empty codes / 4 missing codes
- Elegants Fragrances: 446 rows / 445 unique non-empty codes / 1 missing code
- Niche Perfumes: 584 rows / 575 unique non-empty codes / 9 missing codes
- Luxury Perfumes: 40 rows / 40 unique non-empty codes / 0 missing codes

## Live vs master difference

Compared with the current official EN counters, the master has **33 fewer category rows** in total:

- Women: +2 live
- Men: +1 live
- Elegants: +2 live
- Niche: +28 live
- Luxury: +0 live

Therefore **2,337 is still a live category-row baseline, not yet a certified unique-code total**. The existing master proves that duplicate codes and missing codes can occur, so certification requires enumerating the current live product codes rather than summing category counters.
