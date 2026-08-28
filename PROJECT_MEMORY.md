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

## Current Repository Structure

Main files currently identified: `index.html`, `script.js`, `style.css`, `database_complete.json`, `README.md`, `LICENSE`, and `PROJECT_MEMORY.md`.

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

A separate **Shobi Master** dataset exists and is intended to become the authoritative source for the Shobi catalog rather than relying on the cloned repository's product list.

Previously established characteristics include approximately **2,343 products** and fields such as `prestashop_product_id`, `shobi_code`, `shobi_name`, `inspired_by`, `category`, `official_description`, `price_text`, `url`, and `signature_href`.

The Shobi Master has **not yet been substituted into this repository**.

## Source Strategy

### Confirmed decision

**Fragrantica Social Card is the reference source chosen for the perfume data contained in the Social Card.**

This is a project source decision. It does not mean that Fragrantica's community-derived information is official manufacturer data.

No decision has been made about storing raw vote counts or about implementation/extraction methodology.

### Fragrantica perfume ID — central resource linkage

The important discovery is broader than one Social Card filename pattern: **the Fragrantica numeric perfume ID acts as the common identifier tying together resources belonging to the same perfume.**

Initial confirmed example, Kayali Vanilla | 28:

- Fragrantica perfume ID → `52616`
- Perfume page → `Vanilla-28-52616.html`
- Thumbnail/image resource example → `dark-m.52616.avif`
- English Social Card → `en-p_c_52616.jpeg`

Therefore, once a Shobi inspiration is correctly matched to its Fragrantica perfume and its **Fragrantica ID is known**, that ID can be retained as the stable linkage value from which related Fragrantica resources can be associated or located according to their respective naming/URL conventions.

This is the architectural point to preserve: **store/know the perfume's Fragrantica ID first; individual Fragrantica resources are then linked back to that same perfume ID.**

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

`https://fimgs.net/mdimg/perfume-social-cards/en-p_c_{FRAGRANTICA_ID}.jpeg`

The 10/10 test validates that specific page-ID → Social-Card-ID relationship across the tested sample. The broader project principle is that the **Fragrantica perfume ID itself is the central linkage identifier**, not merely that one Social Card URL pattern exists.

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
- Fragrantica Social Card examined and selected as the reference source for the perfume data contained in it.
- Fragrantica perfume ID identified as the common linkage between a perfume and associated Fragrantica resources.
- Vanilla | 28 (`52616`) confirmed across page, thumbnail/image resource and Social Card.
- Fragrantica page-ID → English Social Card relationship validated successfully on 10/10 additional perfume examples.

## Decisions Made

- Work should proceed **step by step**, without jumping ahead into implementation before the current question/decision is settled.
- The project will be English-language and international.
- GitHub/project files act as persistent project memory rather than relying solely on one ChatGPT conversation.
- `PROJECT_MEMORY.md` is the current project handoff/state document.
- **Fragrantica Social Card is the project's reference source for the perfume data contained in the Social Card.**
- **The Fragrantica perfume ID is the central Fragrantica linkage identifier for a matched perfume and its associated resources.**
- The English Social Card convention `en-p_c_{FRAGRANTICA_ID}.jpeg` has been validated on a 10-perfume test with 10/10 success.

## Do Not Assume Yet

The following have **not** been decided yet:

- Parfumo's future role as a source.
- Basenotes' future role as a source.
- Exact source priority rules outside the confirmed Social Card decision.
- Exact replacement strategy for `database_complete.json`.
- Exact mapping between Shobi Master and existing enriched records.
- Which enrichment fields will ultimately be retained outside the confirmed Social Card source decision.
- Whether existing enrichment data will be reused, replaced, or independently verified.
- Whether raw Fragrantica vote counts will be stored.
- How Social Card data will technically be extracted or imported.

## Current Step

**Continue evaluating and defining perfume-data sources step by step.**

Confirmed so far: Fragrantica Social Card is the reference source for the perfume data it contains; more importantly, the **Fragrantica perfume ID is the central identifier linking a matched perfume to its associated Fragrantica resources**. The page-ID → English Social Card relationship has passed a 10/10 validation test.

Do not advance automatically into scraping, database conversion, workflows, or implementation until those decisions are explicitly made with the user.

## Next Step

Continue from the user's next source/data question without assuming implementation details.

---

### Continuation Instructions for a New Chat

When continuing this project in another ChatGPT conversation:

1. Read `PROJECT_MEMORY.md` first.
2. Inspect the current repository state when necessary rather than assuming this file is perfectly current.
3. Continue from **Current Step** / **Next Step**.
4. Do not redo completed work unless verification is needed.
5. Update this file after significant decisions or changes.