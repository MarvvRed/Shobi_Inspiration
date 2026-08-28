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

Main files currently identified:

- `index.html`
- `script.js`
- `style.css`
- `database_complete.json`
- `README.md`
- `LICENSE`
- `PROJECT_MEMORY.md` — this file

There is currently no backend required by the cloned application.

## Current Database

`database_complete.json` currently contains:

- **303 brands**
- **2,091 perfumes**

The existing records include data such as:

- Shobi/product code
- inspired-by perfume
- brand
- category
- description
- scent type
- olfactory family
- top / heart / base notes
- main accords
- occasions
- seasons
- gender affinity
- sillage
- longevity
- scent rating
- external reference link

### Known Database Issues / Questions

- The provenance of many enrichment fields has **not yet been proven**.
- Many records contain Parfumo links, suggesting Parfumo was used as a reference, but this does not prove every field originated from Parfumo.
- All 2,091 records were found with `reviewCount = 0`, despite populated rating values. This makes the rating provenance particularly questionable and requires verification.
- Four duplicate code values were identified during analysis:
  - `-AL HAR`
  - `677-GUC`
  - `937-VAL`
  - `1868-VER`
- One perfume (`924-TMU`, `INNOCENT (ANGEL)`) was identified without populated `mainAccords`.
- Some records have missing external links/category values.

## Shobi Master

A separate **Shobi Master** dataset exists and is intended to become the authoritative source for the Shobi catalog rather than relying on the cloned repository's product list.

Previously established characteristics of the Shobi Master include approximately **2,343 products** and fields such as:

- `prestashop_product_id`
- `shobi_code`
- `shobi_name`
- `inspired_by`
- `category`
- `official_description`
- `price_text`
- `url`
- `signature_href`

The Shobi Master has **not yet been substituted into this repository**.

## Source Strategy

### Confirmed decision

**Fragrantica Social Card is the reference source chosen for the perfume data contained in the Social Card.**

This is a project source decision. It does not mean that Fragrantica's community-derived information is official manufacturer data.

The Social Card was examined using Kayali Vanilla | 28 as an example. Fragrantica's related perfume views show community-based perfume information and a concise visual summary suitable for quickly understanding a fragrance.

Do not infer additional requirements from this decision. In particular, no decision has yet been made here about storing raw vote counts or about implementation/extraction methodology.

### Other sources still under consideration

- Parfumo
- Basenotes
- Official perfume-brand websites where appropriate
- Shobi itself for Shobi-specific product/catalog information

Important requirement: the finished project is intended to be **completely in English** and aimed at an **international audience**, so source selection should not depend on Italian-only websites.

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
- Question raised about whether the enrichment data is actually sourced from Parfumo or generated/derived.
- Initial international source candidates identified.
- Decision made to introduce persistent project memory in the repository.
- Fragrantica Social Card examined as a perfume-summary source.
- Fragrantica Social Card selected as the reference source for the perfume data contained in that card.

## Decisions Made

- Work should proceed **step by step**, without jumping ahead into implementation before the current question/decision is settled.
- The project will be English-language and international.
- GitHub/project files should act as persistent project memory rather than relying solely on one ChatGPT conversation retaining every detail.
- `PROJECT_MEMORY.md` should be maintained as the current project handoff/state document.
- **Fragrantica Social Card is the project's reference source for the perfume data contained in the Social Card.**

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

Confirmed so far: Fragrantica Social Card is the reference source for the perfume data it contains.

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