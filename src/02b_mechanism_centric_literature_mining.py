"""Mechanism-centric preservation literature mining.

This module searches preservation literature using entropy-suppression operators
rather than only material names.

Primary sources:
- Europe PMC API
- PubMed-compatible query structure
- Google-Scholar-style keyword expansion seeds
- Semantic mechanism grouping

The goal is not merely to collect preservation additives, but to identify
preservation-state engineering mechanisms.
"""

from pathlib import Path
import json
import requests
import pandas as pd

OUTPUT_DIR = Path('outputs')
OUTPUT_DIR.mkdir(exist_ok=True)

EUROPE_PMC_URL = 'https://www.ebi.ac.uk/europepmc/webservices/rest/search'

MECHANISM_QUERIES = {
    'molecular_mobility_suppression': [
        'vitrification biological preservation',
        'glass transition biomolecular stabilization',
        'trehalose vitrification preservation',
        'molecular crowding preservation',
    ],
    'water_activity_reduction': [
        'water activity biomolecular stabilization',
        'lyophilization biological samples',
        'ambient preservation low water activity',
    ],
    'reaction_rate_suppression': [
        'oxidative suppression preservation chemistry',
        'metal chelation biomolecular stabilization',
        'antioxidant preservation biological samples',
    ],
    'enzymatic_entropy_control': [
        'RNase inhibition preservation',
        'protease inhibition biobanking',
        'enzyme suppression ambient preservation',
    ],
    'physical_confinement': [
        'hydrogel encapsulation biomolecule stabilization',
        'hydrogel preservation extracellular vesicles',
        'matrix confinement biological preservation',
    ],
    'mineralization_state_locking': [
        'biosilicification biological preservation',
        'silicic acid preservation biomolecules',
        'TMOS biological stabilization',
        'biomineralization preservation chemistry',
        'silica shell biomolecular stabilization',
    ],
    'recoverability_control': [
        'reversible preservation chemistry',
        'recoverable biomolecular preservation',
        'cleanup compatible preservation workflow',
    ],
}

CURATED_HIGH_PRIORITY_DOIS = [
    '10.1021/acsnano.1c08103',
    '10.1073/pnas.2322418121',
    '10.1073/pnas.2408273121',
]


def query_europe_pmc(query, page_size=10):
    params = {
        'query': query,
        'format': 'json',
        'pageSize': page_size,
    }
    try:
        r = requests.get(EUROPE_PMC_URL, params=params, timeout=30)
        if r.status_code == 200:
            return r.json()
    except Exception:
        return None
    return None


def extract_records(operator_name, query, payload):
    rows = []
    if payload is None:
        return rows
    results = payload.get('resultList', {}).get('result', [])
    for item in results:
        rows.append({
            'entropy_operator': operator_name,
            'query': query,
            'title': item.get('title'),
            'journal': item.get('journalTitle'),
            'year': item.get('pubYear'),
            'doi': item.get('doi'),
            'pmid': item.get('pmid'),
            'authors': item.get('authorString'),
            'source': 'EuropePMC',
            'mechanism_centric_search': True,
        })
    return rows


def main():
    all_rows = []

    for operator, queries in MECHANISM_QUERIES.items():
        for query in queries:
            payload = query_europe_pmc(query)
            all_rows.extend(extract_records(operator, query, payload))

    literature_df = pd.DataFrame(all_rows)
    literature_df.to_csv(OUTPUT_DIR / 'mechanism_centric_literature.csv', index=False)

    curated = pd.DataFrame({
        'high_priority_doi': CURATED_HIGH_PRIORITY_DOIS,
        'module': 'mineralization_state_locking',
        'priority_reason': 'high-impact silicification/mineralization preservation evidence',
    })
    curated.to_csv(OUTPUT_DIR / 'curated_high_priority_preservation_papers.csv', index=False)

    ontology = {
        'conceptual_shift': 'Search preservation mechanisms rather than only material names.',
        'core_framework': 'entropy-suppression engineering',
        'search_mode': 'mechanism-centric literature mining',
    }

    (OUTPUT_DIR / 'literature_mining_ontology.json').write_text(
        json.dumps(ontology, indent=2),
        encoding='utf-8',
    )

    print(f'Collected {len(literature_df)} literature records')


if __name__ == '__main__':
    main()
