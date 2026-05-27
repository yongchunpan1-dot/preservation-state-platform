from pathlib import Path
import json
import re
from urllib.parse import urlencode
from urllib.request import urlopen, Request

import pandas as pd
from bs4 import BeautifulSoup

OUTPUT_DIR = Path('outputs')
EVIDENCE_PATH = OUTPUT_DIR / 'evidence_table.csv'
META_PATH = OUTPUT_DIR / 'live_literature_discovery_metadata.json'

DISCOVERY_QUERIES = [
    'extracellular vesicle preservation lyoprotectant',
    'extracellular vesicle storage stabilizer',
    'protein stabilization excipient lyophilization',
    'nucleic acid stabilization preservation reagent',
]

CANDIDATE_TERMS = [
    'arginine', 'lysine', 'glycine', 'proline', 'betaine', 'ectoine',
    'hydroxyectoine', 'taurine', 'raffinose', 'pullulan',
    'polyvinylpyrrolidone', 'methylcellulose', 'polysorbate 20',
    'polysorbate 80', 'albumin', 'catalase', 'superoxide dismutase',
    'N-acetylcysteine', 'tocopherol', 'magnesium chloride',
    'calcium chloride',
]


def read_url(url, timeout=12):
    try:
        req = Request(url, headers={'User-Agent': 'preservation-state-platform'})
        with urlopen(req, timeout=timeout) as response:
            return response.read().decode('utf-8', errors='ignore')
    except Exception:
        return ''


def search_pubmed_ids(query, retmax=5):
    params = urlencode({'db': 'pubmed', 'term': query, 'retmode': 'json', 'retmax': retmax})
    text = read_url('https://eutils.ncbi.nlm.nih.gov/entrez/eutils/esearch.fcgi?' + params)
    if not text:
        return []
    try:
        data = json.loads(text)
        return data.get('esearchresult', {}).get('idlist', [])
    except Exception:
        return []


def fetch_pubmed_text(pmids):
    if not pmids:
        return ''
    params = urlencode({'db': 'pubmed', 'id': ','.join(pmids), 'retmode': 'xml'})
    xml_text = read_url('https://eutils.ncbi.nlm.nih.gov/entrez/eutils/efetch.fcgi?' + params)
    if not xml_text:
        return ''
    return BeautifulSoup(xml_text, 'lxml').get_text(' ', strip=True).lower()


def discover_terms():
    found = {}
    for query in DISCOVERY_QUERIES:
        pmids = search_pubmed_ids(query)
        text = fetch_pubmed_text(pmids)
        if not text:
            continue
        for term in CANDIDATE_TERMS:
            pattern = r'\b' + re.escape(term.lower()) + r'\b'
            if re.search(pattern, text):
                found.setdefault(term, set()).update(pmids[:3])
    return {term: sorted(ids) for term, ids in sorted(found.items())}


def make_rows(discovered, existing_terms):
    rows = []
    for term, pmids in discovered.items():
        if term.lower() in existing_terms:
            continue
        rows.append({
            'evidence_id': '',
            'material_name': term,
            'synonym': term,
            'source_type': 'live_literature_discovery',
            'source_database': 'PubMed controlled vocabulary scan',
            'source_url_or_reference': '; '.join('PMID:' + p for p in pmids),
            'evidence_statement': f'Controlled PubMed scan detected {term} in preservation-related abstracts.',
            'preservation_relevance': 'literature-associated preservation candidate requiring curation',
            'assay_relevance': 'requires experimental verification in first-round preservation assays',
            'regulatory_relevance': 'not a regulatory assertion',
            'evidence_level': 'L3_live_literature_text_match',
            'notes': json.dumps({'pmids': pmids}, ensure_ascii=False),
        })
    return rows


def main():
    if not EVIDENCE_PATH.exists():
        raise FileNotFoundError('Run src/01_build_evidence_table.py first.')

    evidence = pd.read_csv(EVIDENCE_PATH)
    existing_terms = set(evidence['material_name'].dropna().astype(str).str.lower())
    discovered = discover_terms()
    new_rows = make_rows(discovered, existing_terms)

    if new_rows:
        evidence = pd.concat([evidence, pd.DataFrame(new_rows)], ignore_index=True)
        evidence['evidence_id'] = [f'EVID:{i:05d}' for i in range(len(evidence))]
        evidence.to_csv(EVIDENCE_PATH, index=False)

    metadata = {
        'discovery_mode': 'controlled_pubmed_vocabulary_scan',
        'queries': DISCOVERY_QUERIES,
        'candidate_terms': CANDIDATE_TERMS,
        'terms_detected': sorted(discovered.keys()),
        'new_terms_added': [row['material_name'] for row in new_rows],
        'evidence_table_rows_after_update': int(len(evidence)),
        'note': 'Detected materials are candidates for curation; this step does not validate performance or safety.',
    }
    META_PATH.write_text(json.dumps(metadata, indent=2), encoding='utf-8')
    print(f'Live literature discovery added {len(new_rows)} new candidate(s).')


if __name__ == '__main__':
    main()
