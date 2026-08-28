# Shobi Inspiration — Project Memory

> Persistent project context for continuing work across different ChatGPT conversations.
>
> **Rule:** update this file whenever an important project decision, completed step, structural change, failed approach, or next step changes.

## Project Goal

Build an English-language, international Shobi perfume inspiration website with a reliable Shobi product catalog and trustworthy perfume enrichment data.

The project should keep Shobi product data separate from perfume-reference/enrichment data so the provenance of information remains clear.

## Repository

- Repository: `MarvvRed/Shobi_Inspiration`
- Origin: cloned from `smellyCat-deep/shobi_inspiration` as an independent repository, not a GitHub fork.
- Original-project attribution has been added to `README.md`.
- Current application is a static frontend: HTML + CSS + JavaScript + JSON database.
- Project datasets are stored under `data/`.
- The authoritative Shobi Master currently lives at `data/shobi-master-v1.csv`.

## Current Repository Structure

Main files currently identified: `index.html`, `script.js`, `style.css`, `database_complete.json`, `README.md`, `LICENSE`, `PROJECT_MEMORY.md`, and the `data/` directory.

There is currently no backend required by the cloned application.

## Current Database

`database_complete.json` currently contains **303 brands** and **2,091 perfumes**.

The existing records include data such as Shobi/product code, inspired-by perfume, brand, category, description, scent type, olfactory family, notes, main accords, occasions, seasons, gender affinity, sillage, longevity, scent rating, and external reference link.

### Known Database Issues / Questions

- The provenance of many enrichment fields has **not yet been proven**.
- Many records contain Parfumo links, suggesting Parfumo was used as a reference, but this does not prove every field originated from Parfumo.
- All 2,091 records were found with `reviewCount = 0`, despite populated rating values.
- Four duplicate code values were identified: `-AL HAR`, `677-GUC`, `937-VAL`, `1868-VER`.
- One perfume (`924-TMU`, `INNOCENT (ANGEL)`) was identified without populated `mainAccords`.
- Some records have missing external links/category values.

## Shobi Master

The authoritative Shobi catalog dataset is stored at `data/shobi-master-v1.csv` and contains **2,343 Shobi products**.

Important fields include `prestashop_product_id`, `shobi_code`, `shobi_name`, `reference`, `reference_prefix`, `inspired_by`, `category`, `official_description`, `url`, and provenance/status fields.

The records are currently ordered by `prestashop_product_id` descending. The PrestaShop product ID is treated as a product identifier, not as a perfume property or ranking.

The Shobi Master has not yet replaced `database_complete.json`; catalog identity/mapping work is being completed first.

## Official Perfume Identification Logic

The first priority is to identify **which original perfume each Shobi Master record refers to with the highest possible certainty**. Enrichment fields such as main notes, gender, season, accords, longevity, sillage, etc. come only after identity has been established.

Official identification flow:

**Shobi record → candidate original perfume → cross-verification → identity status → Fragrantica availability/linkage**

A Fragrantica ID must **not** be assigned merely because a perfume name looks similar or because it is the first search result.

Evidence used for identification should include, where available:

1. `inspired_by` — the perfume name declared by Shobi.
2. Shobi code/prefix — often provides a strong clue to the original brand (for example `NISH`, `LEL`, `LUS`, etc.).
3. `official_description` — provides an independent olfactory/profile check against the candidate.
4. Candidate Fragrantica page, when one exists — perfume name, brand and relevant characteristics must be compatible with the Shobi evidence.
5. Other authoritative/reliable evidence may be used to establish identity when Fragrantica does not contain the perfume.

### Identity status and Fragrantica status are separate

Perfume identity is **independent of whether Fragrantica has a page for that perfume**. Fragrantica is a resource linked to an identified perfume; it does not define whether that perfume exists or whether its identity can be confirmed.

Use two separate statuses:

- `identity_status = CONFIRMED` — available evidence identifies the original perfume unambiguously.
- `identity_status = AMBIGUOUS` — multiple candidates remain plausible or evidence is insufficient.
- `fragrantica_status = FOUND` — the correctly identified perfume has a verified Fragrantica page/ID.
- `fragrantica_status = NOT_FOUND` — no verified Fragrantica page/ID has been found for the correctly identified perfume.

Therefore this is a valid successful result:

`identity_status = CONFIRMED`

`fragrantica_status = NOT_FOUND`

A missing Fragrantica ID must never downgrade an otherwise independently confirmed perfume identity, and an apparently plausible Fragrantica result must never be used to force an ambiguous identity into `CONFIRMED`.

When `identity_status = AMBIGUOUS`, no Fragrantica ID is assigned as the official mapping until the identity ambiguity is resolved.

The project explicitly prefers fewer verified matches over forcing all 2,343 records to have an ID. A wrong confident association is worse than an unresolved record.

### Identification validation tests

The method was first tested on the first 10 Shobi Master records (`prestashop_product_id` 5117 through 5108). All 10 could be identified without substantial ambiguity using the combined evidence available in the Master and the corresponding candidate.

A broader second test was then performed on the first 50 consecutive Master records (`prestashop_product_id` 5117 through 5067). All 50 original perfume identities were resolvable with sufficient certainty in that test; 49 had a verified Fragrantica ID, while one confirmed perfume did not yield a verified Fragrantica page/ID. This case established the need to separate identity status from Fragrantica availability.

These validation results are encouraging samples, not proof that all 2,343 records will be automatically resolvable. Ambiguous records must remain explicitly unresolved.

## Source Strategy

### Confirmed decision

**Fragrantica Social Card is the reference source chosen for the perfume data contained in the Social Card.**

This is a project source decision. It does not mean that Fragrantica's community-derived information is official manufacturer data.

No decision has been made about storing raw vote counts or about implementation/extraction methodology.

### Fragrantica perfume ID — central resource linkage

The important discovery is broader than one Social Card filename pattern: **the Fragrantica numeric perfume ID acts as the common identifier tying together Fragrantica resources belonging to the same perfume.**

Initial confirmed example, Kayali Vanilla | 28:

- Fragrantica perfume ID → `52616`
- Perfume page → `Vanilla-28-52616.html`
- Thumbnail/image resource example → `dark-m.52616.avif`
- English Social Card → `en-p_c_52616.jpeg`

Therefore, when an identified perfume has a verified Fragrantica page and its **Fragrantica ID is known**, that ID can be retained as the stable Fragrantica linkage value from which related Fragrantica resources can be associated or located according to their respective naming/URL conventions.

This is the architectural point to preserve: **perfume identity comes first; when Fragrantica contains that perfume, store/know its Fragrantica ID as the central linkage for Fragrantica resources.**

### Validation test

The relationship between perfume-page ID and English Social Card ID was tested on 10 different perfumes and succeeded **10/10**:

| Perfume | Fragrantica ID | Social Card with same ID |
| --- | ---: | --- |
| Dior Sauvage | `31861` | confirmed |
| Bleu de Chanel | `9099` | confirmed |
| YSL Black Opium | `25324` | confirmed |
| Baccarat Rouge 540 | `33519` | confirmed |
| Creed Aventus | `9828` | confirmed |
| La Vie Est Belle | `14982` | confirmed |
| Acqua di Giò | `410` | confirmed |
| Tom Ford Lost Cherry | `51411` | confirmed |
| Carolina Herrera Good Girl | `39681` | confirmed |
| Terre d'Hermès | `17` | confirmed |

The tested English Social Card convention is:

`https://fimgs.net/mdimg/perfume-social-cards/en-p_c_{FRAGRICA_ID}.jpeg`

The 10/10 test validates that specific page-ID → Social-Card-ID relationship across the tested sample. The broader project principle is that the **Fragrantica perfume ID itself is the central linkage identifier within Fragrantica**, not merely that one Social Card URL pattern exists.

Do not assume that every possible Fragrantica resource has the same exact filename structure. Each resource type/pattern should be verified independently, while the shared perfume ID remains the key association.

### Other sources still under consideration

- Parfumo
- Basenotes
- Official perfume-brand websites where appropriate
- Shobi itself for Shobi-specific product/catalog information

The finished project is intended to be **completely in English** and aimed at an **international audience**.

## Important Architectural Principle

Do not assume that a value in the existing `database_complete.json` is authoritative merely because it exists.

For future enrichment work, provenance should ideally be explicit so we can determine where each important field came from and when it was verified.

## Work Completed

- Independent repository created from the original project.
- Original-project attribution added to README.
- Existing frontend architecture reviewed.
- Existing `database_complete.json` inspected and counted.
- Basic database quality checks performed.
- Existing enrichment fields identified.
- Initial international source candidates identified.
- Persistent project memory introduced.
- `data/` directory created for project datasets.
- Shobi Master placed at `data/shobi-master-v1.csv` as the authoritative Shobi catalog dataset.
- Fragrantica Social Card examined and selected as the reference source for the perfume data contained in it.
- Fragrantica perfume ID identified as the common linkage between a perfume and associated Fragrantica resources when a Fragrantica page exists.
- Vanilla | 28 (`52616`) confirmed across page, thumbnail/image resource and Social Card.
- Fragrantica page-ID → English Social Card relationship validated successfully on 10/10 additional perfume examples.
- Official Shobi → original perfume identification logic defined.
- Identification method tested on the first 50 consecutive Shobi Master records.
- Identity status formally separated from Fragrantica availability status.

## Decisions Made

- Work should proceed **step by step**, without jumping ahead into implementation before the current question/decision is settled.
- The project will be English-language and international.
- GitHub/project files act as persistent project memory rather than relying solely on one ChatGPT conversation.
- `PROJECT_MEMORY.md` is the current project handoff/state document.
- `data/shobi-master-v1.csv` is the authoritative Shobi Master dataset for the current project.
- **Perfume identity must be established before enrichment data is collected.**
- **No Fragrantica ID may be assigned solely from name similarity or a first-result match.**
- **Identification uses cross-verification of Shobi evidence and the candidate perfume.**
- **Perfume identity and Fragrantica availability are independent statuses.**
- **`identity_status` uses `CONFIRMED` / `AMBIGUOUS`.**
- **`fragrantica_status` uses `FOUND` / `NOT_FOUND`.**
- **A perfume may legitimately be `identity_status = CONFIRMED` and `fragrantica_status = NOT_FOUND`.**
- **Fragrantica is a linked resource, not the authority that determines whether a perfume identity exists.**
- **Unresolved or genuinely ambiguous identities remain `AMBIGUOUS`; no official Fragrantica ID is assigned until resolved.**
- **Fragrantica Social Card is the project's reference source for the perfume data contained in the Social Card when available.**
- **The Fragrantica perfume ID is the central Fragrantica linkage identifier for a matched perfume and its associated Fragrantica resources.**
- The English Social Card convention `en-p_c_{FRAGRANTICA_ID}.jpeg` has been validated on a 10-perfume test with 10/10 success.

## Do Not Assume Yet

The following have **not** been decided yet:

- Parfumo's future role as a source.
- Basenotes' future role as a source.
- Exact source priority rules outside the confirmed Social Card decision.
- Exact replacement strategy for `database_complete.json`.
- Which enrichment fields will ultimately be retained outside the confirmed Social Card source decision.
- Whether existing enrichment data will be reused, replaced, or independently verified.
- Whether raw Fragrantica vote counts will be stored.
- How Social Card data will technically be extracted or imported.
- What proportion of all 2,343 Shobi records can ultimately be confirmed automatically versus requiring manual review.

## Current Step

**Identify the original perfume represented by each Shobi Master record before collecting enrichment data.**

The official result model is:

`Shobi record → candidate original perfume → cross-verification → identity_status → Fragrantica lookup/status`

Possible successful example:

`identity_status = CONFIRMED`

`fragrantica_status = NOT_FOUND`

Do not force either perfume identity or a Fragrantica ID when evidence is insufficient.

## Next Step

Continue validating/scaling the identification method across the Shobi Master while preserving the independent `identity_status` and `fragrantica_status` fields.

Do not advance automatically into notes, gender, seasons, accords, Social Card extraction, database conversion, or other enrichment until perfume identity work is sufficiently established and the user explicitly decides to proceed.

---

### Continuation Instructions for a New Chat

When continuing this project in another ChatGPT conversation:

1. Read `PROJECT_MEMORY.md` first.
2. Inspect the current repository state when necessary rather than assuming this file is perfectly current.
3. Continue from **Current Step** / **Next Step**.
4. Do not redo completed work unless verification is needed.
5. Update this file after significant decisions or changes.