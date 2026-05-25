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

TEMPERATURE_STATES = ['4C', 'room_temperature', '37C']
PHASE_STATES = ['solution', 'hydrogel', 'glass_state', 'mineralized_state']


def classify_material(name: str):
    lower = name.lower()
    if any(k in lower for k in ['trehalose', 'sucrose', 'mannitol', 'sorbitol']):
        return 'glass_former'
    if any(k in lower for k in ['alginate', 'gelatin', 'hyaluronic']):
        return 'hydrogel'
    if any(k in lower for k in ['edta', 'citrate']):
        return 'chelator'
    if any(k in lower for k in ['glutathione', 'ascorbic']):
        return 'antioxidant'
    if any(k in lower for k in ['dmso', 'glycerol']):
        return 'cryoprotectant'
    if any(k in lower for k in ['silica', 'zif', 'calcium phosphate']):
        return 'mineralization'
    return 'other'


def compatibility_penalty(materials):
    mats = ' '.join(materials).lower()
    penalty = 0.0
    if 'edta' in mats and 'calcium' in mats:
        penalty += 0.4
    if 'formaldehyde' in mats and 'rna' in mats:
        penalty += 0.5
    if 'silica' in mats and 'lc-ms' in mats:
        penalty += 0.3
    return penalty


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
            for temp in TEMPERATURE_STATES:
                for phase in PHASE_STATES:
                    concentration_labels = [c[0] for c in CONCENTRATION_LEVELS[:r]]

                    preservation_prior = 0.45
                    assay_prior = 0.5
                    cleanup_prior = 0.35

                    classes = [classify_material(m) for m in combo]

                    if 'glass_former' in classes:
                        preservation_prior += 0.15
                    if 'antioxidant' in classes:
                        preservation_prior += 0.1
                    if 'hydrogel' in classes:
                        preservation_prior += 0.08
                    if 'mineralization' in classes:
                        preservation_prior += 0.12
                        cleanup_prior += 0.2

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
                        'materials': '|'.join(combo),
                        'num_components': r,
                        'component_classes': '|'.join(classes),
                        'concentration_levels': '|'.join(concentration_labels),
                        'temperature_state': temp,
                        'phase_state': phase,
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

    shortlist = (
        df[df['recommended_for_first_round']]
        .sort_values(
            ['preservation_likelihood_prior', 'assay_compatibility_prior'],
            ascending=False,
        )
        .head(64)
    )

    shortlist.to_csv(OUTPUT_DIR / 'recommended_first_round_formulations.csv', index=False)

    print(f'Generated {len(df)} virtual formulations')


if __name__ == '__main__':
    main()
