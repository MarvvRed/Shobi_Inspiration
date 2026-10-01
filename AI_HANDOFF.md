# AI handoff — Shobi Inspiration

**Repository:** `MarvvRed/Shobi_Inspiration`  
**Live site:** https://marvvred.github.io/Shobi_Inspiration/  
**Last verified:** 2026-10-02 (Europe/Rome)

This file is the mandatory starting point for any AI working on this repository. Read it fully before inspecting, editing, running workflows, or proposing a publication.

## Prompt to use with another AI

```text
You are continuing the repository MarvvRed/Shobi_Inspiration.

Before doing anything, read AI_HANDOFF.md in full, then read the files listed in its “Read first” section. Treat main and those files as the source of truth.

Non-negotiable audit rule:
- GREEN only when the entire exact chain is proven: official Shobi product → exact original name/brand → exact Fragrantica identity/FID/direct URL → Social Card for the same FID → visible Main Notes in the identical order → verified local icon for every note → correct gender → correct main season.
- YELLOW when any proof is missing or insufficient.
- RED only for an actual contradiction.
Never infer notes, never reorder them, never force a promotion to green.

Work only on the requested target or unresolved cases. Do not reopen certified records, do not run a global audit for a small task, do not rerun historical failed workflows, and do not overwrite database/canonical/shobi-universal-v1.json.

Before editing, report the exact files and evidence you will use. After editing, run the narrowest relevant validation, inspect the result, then publish only the required files. Preserve all unrelated working-tree changes.
```

## Read first

1. `OFFICIAL_DATABASE.md`
2. `PROJECT_MEMORY.md`
3. `database/catalog/final-perfume-catalog-certification.json`
4. `database/audits/current-yellow-breakdown.json`
5. `database/catalog/recent-additions.json`
6. For note/order work only: `database/fragrantica/social-cards/records/social-card-ordered-image-audit.json`

For implementation details, inspect the specific relevant script in `tools/`; do not guess the generator pipeline.

## Current certified state

| Scope | Total | Green | Yellow | Red |
| --- | ---: | ---: | ---: | ---: |
| Operational source catalog | 2,274 | 2,268 | 6 | 0 |
| Public perfume-only catalog | 2,249 | 2,243 | 6 | 0 |

The public catalog has 25 fewer rows because only independently certified same-original duplicate listings were collapsed. It is not a data loss.

### The six real yellow records

They are intentionally yellow. Do not promote them without new primary evidence.

- `2816-MOOD` — no exact Fragrantica identity/FID/card.
- `2085-CLIV` — no exact Fragrantica identity/FID/card.
- `118-HAM` — legacy Fragrantica image has no readable note card.
- `325-PECK` — legacy Fragrantica image has no readable note card.
- `235-HOLL` — legacy Fragrantica image has no readable note card.
- `1251-ROM` — legacy Fragrantica image has no readable note card; identity also remains insufficient.

## Non-negotiable catalog scope

Keep only Shobi products inspired by real wearable perfumes.

Exclude home fragrance, candles, car/home deodorants, room sprays, diffusers, incense, laundry products, body/hair mists, body-care/amenity items, accessories, and Shobi-created/non-demonstrable originals. Exclude MIX/blend records from the public perfume catalog.

Do not introduce duplicates. A duplicate can be collapsed only with documented same-original proof.

## Certification rules in detail

A green record must pass all of these for the same perfume identity:

1. Live official Shobi product page, code and product ID.
2. Exact original perfume name and brand.
3. Exact Fragrantica FID and direct URL.
4. Fragrantica Social Card for that same FID and correct product image.
5. Main Notes visibly read from that card, with identical order.
6. Each displayed note has the correct local Fragrantica icon.
7. Gender is tied to the exact Fragrantica identity/card evidence.
8. Main season is derived from the longest Fragrantica season bar.

For OCR/card recovery, use only strict exact evidence: repeated concordant reads, at least one real crop, and no competing note sequence. A weak, partial, guessed, pyramid, or legacy-source reading stays yellow.

## Protected data and working rules

- **Never overwrite:** `database/canonical/shobi-universal-v1.json`. It is the universal immutable recovery database.
- Preserve `Main Notes` unless the task supplies stronger exact Social Card evidence.
- Do not touch unrelated files or delete historical evidence.
- Keep source data, audit records, generated public catalog, and site UI consistent.
- Prefer narrow targeted scripts and validations. Do not re-audit all perfumes for a scoped correction.
- Check GitHub Actions logs before re-running anything; historical failed runs are not a task by themselves.
- Any publication must end with a successful Pages deployment check.

## Recent official Shobi additions

On 2026-09-30, 21 official wearable perfumes were added and are all certified green:

`2850-ETLR`, `2851-LOUM`, `2852-MAN`, `2853-MEM`, `2855-AMG`, `2856-TMFO`, `2857-KAY`, `2858-CRIVEL`, `2859-DRC`, `2860-OBVI`, `2861-AKR`, `2862-GIA`, `2863-FRAG`, `2864-GISS`, `2865-IN`, `2866-KAY`, `2867-LAT`, `2868-LEL`, `2869-MARG`, `2870-MAN`, `2871-NARO`.

Their identity evidence is in:
- `database/audits/new-official-shobi-perfumes-2026-09-30.json`
- `database/audits/new-official-shobi-gender-evidence-2026-09-30.json`

## Recent additions UI

The “Aggiunti di recente” filter and the `NUOVO` card badge read from `database/catalog/recent-additions.json`.

- Window: **21 calendar days** from `addedDate`.
- Current batch date: 2026-09-30.
- It is visible through 2026-10-20.
- From 2026-10-21, those products automatically leave the filter and the filter is hidden.
- Keep filter and badge tied to the same expiry rule. Do not add separate static code lists.

Relevant UI files:
- `fragrantica-image-link.js` — recent badge/filter and image link behaviour.
- `script.js` — filtering, cards, search and sorting.
- `validation-tracker.js` — green/yellow/red tracker and audit popup.
- `index.html` and `style.css` — layout and styles.

## Handoff procedure

1. State the target and read the relevant evidence.
2. Identify the smallest set of files to change.
3. Make no assumption from a label, URL slug, or OCR fragment.
4. Validate the changed target before publishing.
5. Confirm generated catalog counts/statuses and Pages deployment.
6. Update this file whenever a change alters the certified state, a protected rule, the pipeline, or the UI behaviour described above.
