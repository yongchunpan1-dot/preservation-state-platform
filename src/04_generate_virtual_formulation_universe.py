from itertools import combinations
from pathlib import Path

import numpy as np
import pandas as pd

OUTPUT_DIR = Path('outputs')
OUTPUT_DIR.mkdir(exist_ok=True)

CONCENTRATION_LEVELS = [
    ('low', 0.1),
    ('medium', 0.5),
    ('high', 1.0),
]

# Temperature is a testing condition, not a formulation identity.
# The virtual universe still records temperature variants for modeling,
# but first-round experimental shortlists are deduplicated by materials.
TEMPERATURE_STATES = ['4C', 'room_temperature', '37C']
PHASE_STATES = ['solution', 'hydrogel', 'glass_state', 'mineralized_state']
FIRST_ROUND_TEST_CONDITION = '37C_3_days'


def classify_material(name: str):
    lower = name.lower()
    if any(k in lower for k in ['trehalose', 'sucrose', 'mannitol', 'sorbitol']):
        return 'glass_former'
    if any(k in lower for k in ['alginate', 'gelatin', 'hyaluronic']):
        return 'state_locking_matrix'
    if any(k in lower for k in ['edta', 'citrate']):
        return 'recoverability_or_chelation'
    if any(k in lower for k in ['glutathione', 'ascorbic']):
        return 'reaction_rate_suppression'
    if any(k in lower for k in ['dmso', 'glycerol']):
        return 'mobility_suppression'
    if any(k in lower for k in ['silica', 'silicic acid', 'orthosilicic', 'tmos', 'sodium silicate', 'zif', 'calcium phosphate']):
        return 'state_locking_mineral'
    return 'other'


def compatibility_penalty(materials):
    mats = ' '.join(materials).lower()
    penalty = 0.0
    if 'edta' in mats and 'calcium' in mats:
        penalty += 0.4
    return penalty


def make_material_key(materials):
    return '|'.join(sorted(materials))


def main():
    descriptor_path = OUTPUT_DIR / 'descriptor_table.csv'
    if not descriptor_path.exists():
        raise FileNotFoundError('Run descriptor generation first.')

    descriptors = pd.read_csv(descriptor_path)
    materials = sorted(descriptors['material_name'].dropna().unique())

    rows = []
    formulation_counter = 0

    for r in [1, 2, 3]:
        for combo in combinations(materials, r):
            material_key = make_material_key(combo)
            for temp in TEMPERATURE_STATES:
                for phase in PHASE_STATES:
                    concentration_labels = [c[0] for c in CONCENTRATION_LEVELS[:r]]

                    preservation_prior = 0.45
                    assay_prior = 0.5
                    cleanup_prior = 0.35

                    classes = [classify_material(m) for m in combo]

                    if 'glass_former' in classes or 'mobility_suppression' in classes:
                        preservation_prior += 0.15
                    if 'reaction_rate_suppression' in classes:
                        preservation_prior += 0.1
                    if 'state_locking_matrix' in classes:
                        preservation_prior += 0.08
                        cleanup_prior += 0.08
                    if 'state_locking_mineral' in classes:
                        preservation_prior += 0.12
                        cleanup_prior += 0.2
                    if 'recoverability_or_chelation' in classes:
                        assay_prior += 0.05

                    penalty = compatibility_penalty(combo)
                    assay_prior -= penalty

                    if phase == 'glass_state':
                        preservation_prior += 0.1
                    if phase == 'hydrogel':
                        preservation_prior += 0.05
                        cleanup_prior += 0.08
                    if phase == 'mineralized_state':
                        preservation_prior += 0.12
                        cleanup_prior += 0.22

                    if temp == '37C':
                        preservation_prior -= 0.08

                    formulation_counter += 1

                    rows.append({
                        'formulation_id': f'FORM_{formulation_counter:06d}',
                        'material_key': material_key,
                        'materials': '|'.join(combo),
                        'num_components': r,
                        'component_classes': '|'.join(classes),
                        'concentration_levels': '|'.join(concentration_labels),
                        'temperature_state': temp,
                        'phase_state': phase,
                        'first_round_test_condition': FIRST_ROUND_TEST_CONDITION,
                        'preservation_likelihood_prior': np.clip(preservation_prior, 0, 1),
                        'assay_compatibility_prior': np.clip(assay_prior, 0, 1),
                        'cleanup_burden_prior': np.clip(cleanup_prior, 0, 1),
                        'regulatory_status_prior': 0.5,
                        'interaction_penalty': penalty,
                        'recommended_for_first_round': penalty < 0.35,
                    })

    df = pd.DataFrame(rows)
    df.to_csv(OUTPUT_DIR / 'preservation_universe_virtual.csv', index=False)
    df.to_parquet(OUTPUT_DIR / 'preservation_universe_virtual.parquet', index=False)

    ranked = df[df['recommended_for_first_round']].sort_values(
        ['preservation_likelihood_prior', 'assay_compatibility_prior'],
        ascending=False,
    )

    # Deduplicate material combinations for experimental actionability.
    # Temperature and phase variants are modeling states, not separate first-round formulations.
    shortlist = ranked.drop_duplicates(subset=['material_key']).head(64)
    shortlist.to_csv(OUTPUT_DIR / 'recommended_first_round_formulations.csv', index=False)

    print(f'Generated {len(df)} virtual formulation states')
    print(f'Generated {len(shortlist)} deduplicated first-round formulation candidates')


if __name__ == '__main__':
    main()
