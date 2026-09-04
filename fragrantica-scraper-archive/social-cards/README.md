# Fragrantica Social Cards

Raccolta locale delle Social Card Fragrantica associate ai prodotti Shobi.

## Fonte

Per ogni `fragrantica_id` confermato viene usato lo schema:

`https://fimgs.net/mdimg/perfume-social-cards/en-p_c_{FRAGRANTICA_ID}.jpeg`

## File

- `fetch_social_cards.py` — downloader resumable.
- `images/` — Social Card scaricate.
- `manifest.csv` — una riga per ciascun prodotto del mapping Shobi.

## Regola di sicurezza

Una card viene scaricata solo quando la riga ha:

- `identity_status = CONFIRMED`
- `fragrantica_status = FOUND`
- `fragrantica_id` numerico

Le altre righe restano nel manifest con `card_status = NO_CONFIRMED_ID`, per evitare associazioni errate.

Il downloader verifica inoltre che il payload sia un JPEG valido prima di salvarlo.
