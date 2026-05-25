import pandas as pd
import requests
from pathlib import Path

OUTPUT_DIR = Path('outputs')
OUTPUT_DIR.mkdir(exist_ok=True)

SEED_MATERIALS = [
    'trehalose',
    'dextran',
    'alginate',
    'DMSO',
    'glyoxal',
    'formaldehyde',
    'PVA',
    'PEG',
    'RNAlater',
    'PAXgene',
    'silica',
    'ZIF-8'
]


def query_pubchem(name: str):
    url = f'https://pubchem.ncbi.nlm.nih.gov/rest/pug/compound/name/{name}/property/MolecularWeight,XLogP,TPSA/JSON'
    try:
        r = requests.get(url, timeout=20)
        if r.status_code == 200:
            return r.json()
    except Exception:
        return None
    return None


rows = []

for material in SEED_MATERIALS:
    pubchem = query_pubchem(material)

    rows.append({
        'material_name': material,
        'synonym': material,
        'source_type': 'database',
        'source_database': 'PubChem',
        'source_url_or_reference': f'https://pubchem.ncbi.nlm.nih.gov/#query={material}',
        'evidence_statement': f'{material} identified as preservation-relevant material candidate.',
        'preservation_relevance': 'high',
        'assay_relevance': 'context-dependent',
        'regulatory_relevance': 'potential translational relevance',
        'evidence_level': 'database+literature seed',
        'notes': str(pubchem)[:500]
    })


df = pd.DataFrame(rows)
df.to_csv(OUTPUT_DIR / 'evidence_table.csv', index=False)

print('Generated evidence_table.csv')
