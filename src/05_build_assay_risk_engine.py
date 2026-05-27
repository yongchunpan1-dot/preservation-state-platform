from pathlib import Path
import json

import pandas as pd

try:
    import yaml
except ImportError:  # Keep the pipeline runnable even if PyYAML is unavailable.
    yaml = None

OUTPUT_DIR = Path('outputs')
OUTPUT_DIR.mkdir(exist_ok=True)

ASSAY_RULES = {
    'PCR': {
        'high_risk_terms': ['formaldehyde', 'glyoxal'],
        'moderate_risk_terms': [
            'hydrogel',
            'gelatin',
            'silica-forming precursor',
            'silica_forming_precursor',
            'silicic acid',
            'silicate',
            'tmos',
        ],
    },
    'LCMS': {
        'high_risk_terms': ['peg', 'detergent'],
        'moderate_risk_terms': [
            'alginate',
            'gelatin',
            'silica-forming precursor',
            'silica_forming_precursor',
            'silicic acid',
            'silicate',
            'tmos',
        ],
    },
    'scRNAseq': {
        'high_risk_terms': ['formaldehyde', 'methanol'],
        'moderate_risk_terms': ['hydrogel', 'silica-forming precursor', 'silica_forming_precursor'],
    },
    'ELISA': {
        'high_risk_terms': ['crosslink'],
        'moderate_risk_terms': ['mineral', 'silica-forming precursor', 'silica_forming_precursor'],
    },
}

CLEANUP_RULES = {
    'silica-forming precursor': 'silica_dissolution_or_buffer_exchange',
    'silica_forming_precursor': 'silica_dissolution_or_buffer_exchange',
    'tetramethyl orthosilicate': 'silica_dissolution_or_buffer_exchange',
    'tmos': 'silica_dissolution_or_buffer_exchange',
    'silicic acid': 'silica_dissolution_or_buffer_exchange',
    'orthosilicic acid': 'silica_dissolution_or_buffer_exchange',
    'sodium silicate': 'silica_dissolution_or_buffer_exchange',
    'silicate': 'silica_dissolution_or_buffer_exchange',
    'silica': 'silica_dissolution_or_buffer_exchange',
    'calcium phosphate': 'acid_or_edta_release',
    'alginate': 'chelator_release',
    'peg': 'sp3_or_precipitation_cleanup',
    'gelatin': 'protease_or_denaturing_cleanup',
}


def compute_assay_risk(material_string, assay_name):
    rules = ASSAY_RULES[assay_name]
    text = str(material_string).lower()
    risk = 0.1
    for term in rules['moderate_risk_terms']:
        if term in text:
            risk += 0.2
    for term in rules['high_risk_terms']:
        if term in text:
            risk += 0.45
    return min(risk, 1.0)


def infer_cleanup_strategy(material_string):
    text = str(material_string).lower()
    strategies = []
    for key, value in CLEANUP_RULES.items():
        if key in text:
            strategies.append(value)
    if not strategies:
        strategies.append('standard_buffer_exchange')
    return '|'.join(sorted(set(strategies)))


def choose_unique_material_candidates(scored, n=48):
    # Keep the full state-resolved table for modeling, but make the experimental
    # shortlist actionable by collapsing temperature/phase variants of the same
    # material combination.
    if 'material_key' not in scored.columns:
        scored['material_key'] = scored['materials'].apply(lambda x: '|'.join(sorted(str(x).split('|'))))

    ranked = scored.sort_values(
        ['overall_feasibility_score', 'preservation_likelihood_prior', 'assay_compatibility_prior'],
        ascending=False,
    )
    unique = ranked.drop_duplicates(subset=['material_key']).head(n).copy()
    unique['experimental_temperature'] = '37C'
    unique['experimental_storage_time'] = '3_days'
    unique['note'] = 'Unique material combination; temperature/phase variants are retained only in preservation_universe_virtual.csv.'
    return unique


def write_rules_file():
    payload = {'assay_rules': ASSAY_RULES, 'cleanup_rules': CLEANUP_RULES}
    yaml_path = OUTPUT_DIR / 'assay_risk_rules.yaml'
    json_path = OUTPUT_DIR / 'assay_risk_rules.json'
    if yaml is not None:
        with open(yaml_path, 'w') as f:
            yaml.safe_dump(payload, f, sort_keys=False)
    else:
        json_path.write_text(json.dumps(payload, indent=2), encoding='utf-8')


def main():
    universe_path = OUTPUT_DIR / 'preservation_universe_virtual.csv'
    if not universe_path.exists():
        raise FileNotFoundError('Run virtual universe generation first.')

    universe = pd.read_csv(universe_path)
    required_columns = ['materials', 'cleanup_burden_prior', 'preservation_likelihood_prior', 'assay_compatibility_prior']
    missing = [c for c in required_columns if c not in universe.columns]
    if missing:
        raise ValueError(f'preservation_universe_virtual.csv is missing required columns: {missing}')

    rows = []
    for _, row in universe.iterrows():
        materials = row['materials']
        out = row.to_dict()
        for assay in ASSAY_RULES:
            out[f'{assay}_risk_score'] = compute_assay_risk(materials, assay)
        out['cleanup_strategy'] = infer_cleanup_strategy(materials)
        out['recoverability_score'] = max(0, 1 - row['cleanup_burden_prior'])
        rows.append(out)

    scored = pd.DataFrame(rows)
    scored['overall_feasibility_score'] = (
        scored['preservation_likelihood_prior']
        + scored['assay_compatibility_prior']
        + scored['recoverability_score']
        - scored['cleanup_burden_prior']
        - scored[['PCR_risk_score', 'LCMS_risk_score', 'scRNAseq_risk_score']].mean(axis=1)
    )

    scored.to_csv(OUTPUT_DIR / 'formulation_assay_compatibility.csv', index=False)
    write_rules_file()

    top = choose_unique_material_candidates(scored, n=48)
    top.to_csv(OUTPUT_DIR / 'top_ranked_experimental_candidates.csv', index=False)

    print('Generated full assay compatibility matrix and deduplicated experimental candidates')


if __name__ == '__main__':
    main()
