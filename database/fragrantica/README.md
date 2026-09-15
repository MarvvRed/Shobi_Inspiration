# Fragrantica Scraper Archive

Archivio separato del lavoro Fragrantica usato nel progetto Shobi.

Questa cartella serve a conservare gli strumenti e la memoria operativa del vecchio workflow senza mescolarli al sito corrente.

## Contenuto

- `tools/shobi_fragrantica_direct_resolver.py` — ricerca diretta su Fragrantica con fallback ai provider HTML.
- `tools/shobi_online_resolver.py` — resolver conservativo Shobi → Fragrantica.
- `tools/shobi_firefox_search_batch.py` — raccolta candidati Fragrantica tramite Firefox/Selenium.
- `legacy/LOCAL_SCRAPER_HISTORY.md` — ricostruzione del vecchio ambiente locale e dell'indice URL.

## Vecchio scraper locale

Nel precedente ambiente Windows era stato usato un clone/tool separato in `C:\fragrance_scraper` con:

- `fragrantica_url_scraper.py`
- `perfume_urls.txt`
- raccolta già caricata di circa **21.158 URL Fragrantica**
- scansione pagine designer con limite operativo fino a circa 22.000 profumi.

Il 5 settembre 2026 è stato recuperato e salvato senza modifiche l'archivio URL originale: [perfume_urls.txt](legacy/original-local-scraper/perfume_urls.txt), con **55.964 righe**. Provenienza e checksum sono nel [README dell'archivio](legacy/original-local-scraper/README.md). Lo script originale non è ancora stato importato.

## Regola

Questo archivio è di riferimento. Il codice principale del sito continua a vivere fuori da questa cartella.
