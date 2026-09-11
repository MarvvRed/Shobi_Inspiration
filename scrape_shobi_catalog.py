ELLO CHE STAI FACENDO<![CDATA[
# Rimuovi il CDATA e i tag HTML/XML
import requests
from bs4 import BeautifulSoup
import pandas as pd

# URL del sito
url = 'https://leparfum.com.gr/en/perfumes'

# Effettua la richiesta HTTP
headers = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36"
}
max_retries = 5
for attempt in range(max_retries):
    try:
        response = requests.get(url, headers=headers, timeout=30)
        break
    except (requests.exceptions.RequestException) as e:
        if attempt == max_retries - 1:
            raise
        print(f"Attempt {attempt + 1} failed: {e}. Retrying...")
        import time
        wait_time = min(2 ** attempt, 30)
        print(f"Waiting for {wait_time} seconds before retrying...")
        time.sleep(wait_time)

# Parsea la risposta HTML
soup = BeautifulSoup(response.text, 'html.parser')

# Estrai i dati dei profumi
perfumes = []
for perfume in soup.find_all('div', class_='product-item'):
    name = perfume.find('h2', class_='product-name').text.strip()
    brand = perfume.find('span', class_='product-brand').text.strip()
    code = perfume.find('span', class_='product-code').text.strip()
    perfumes.append({'name': name, 'brand': brand, 'code': code})

# Converte i dati in un DataFrame di Pandas
df = pd.DataFrame(perfumes)

# Salva i dati in un file CSV
df.to_csv('shobi_perfume_catalog.csv', index=False)
# Rimuovi il CDATA e i tag HTML/XML
]]>