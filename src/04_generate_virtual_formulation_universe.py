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

SILICA_SOURCE_TERMS = [
    'silica-forming precursor',
    'silica_forming_precursor',
    'silicic acid',
    'orthosilicic acid',
    'silicate',
    'sodium silicate',
    'tetramethyl orthosilicate',
    'tmos',
    'teos',
]

STRATIFIED_SHORTLIST_TARGETS = {
    'molecular_mobility_suppression': 10,
    'chemical_reaction_rate_suppression': 10,
    'structural_state_locking': 10,
    'mineralized_state_locking': 10,
    'degradation_pathway_suppression_and_recoverability': 10,
    'hybrid_multi_module_formulations': 20,
}


def is_silica_source(name: str):
    lower = str(name).lower()
    return any(k in lower for k in SILICA_SOURCE_TERMS)


def canonical_material_identity(name: str):
    lower = str(name).lower().strip()
    if is_silica_source(lower):
        return 'silica_source'
    if lower == 'silica':
        return 'silica_final_product_reference'
    return lower.replace(' ', '_')


def classify_material(name: str):
    lower = str(name).lower()
    if any(k in lower for k in ['trehalose', 'sucrose', 'mannitol', 'sorbitol', 'dextran']):
        return 'vitrification_or_glass_forming'
    if any(k in lower for k in ['alginate', 'gelatin', 'hyaluronic']):
        return 'matrix_state_locking'
    if any(k in lower for k in ['edta', 'citrate']):
        return 'recoverability_or_chelation'
    if any(k in lower for k in ['glutathione', 'ascorbic']):
        return 'reaction_rate_suppression'
    if any(k in lower for k in ['dmso', 'glycerol', 'hydroxyethyl starch']):
        return 'mobility_suppression'
    if is_silica_source(lower):
        return 'silica_source_mineralization'
    if lower.strip() == 'silica':
        return 'silica_final_product_reference'
    if any(k in lower for k in ['zif', 'calcium phosphate']):
        return 'non_silica_mineralization'
    return 'other'


def entropy_control_module(material_class: str):
    mapping = {
        'vitrification_or_glass_forming': 'molecular_mobility_suppression',
        'mobility_suppression': 'molecular_mobility_suppression',
        'reaction_rate_suppression': 'chemical_reaction_rate_suppression',
        'matrix_state_locking': 'structural_state_locking',
        'silica_source_mineralization': 'mineralized_state_locking',
        'silica_final_product_reference': 'mineralized_state_locking_reference',
        'non_silica_mineralization': 'mineralized_state_locking',
        'recoverability_or_chelation': 'degradation_pathway_suppression_and_recoverability',
        'other': 'unassigned_entropy_control_module',
    }
    return mapping.get(material_class, 'unassigned_entropy_control_module')


def silica_source_role(name: str):
    lower = str(name).lower()
    if 'tetramethyl orthosilicate' in lower or 'tmos' in lower or 'teos' in lower:
        return 'hydrolyzable_alkoxysilane_silica_source'
    if 'sodium silicate' in lower or ('silicate' in lower and 'silicic' not in lower):
        return 'aqueous_silicate_silica_source'
    if 'silicic acid' in lower or 'orthosilicic acid' in lower:
        return 'monomeric_or_oligomeric_silicic_acid_source_state'
    if lower.strip() == 'silica':
        return 'condensed_silica_final_product_reference'
    return 'not_applicable'


def compatibility_penalty(materials):
    mats = ' '.join(materials).lower()
    penalty = 0.0
    if 'edta' in mats and 'calcium' in mats:
        penalty += 0.4
    if ('tmos' in mats or 'tetramethyl orthosilicate' in mats) and any(k in mats for k in ['enzyme', 'catalase']):
        penalty += 0.15
    return penalty


def make_material_key(materials):
    return '|'.join(sorted(materials))


def make_canonical_source_key(materials):
    return '|'.join(sorted(canonical_material_identity(m) for m in materials))


def build_mechanism_stratified_shortlist(ranked_df, total_target=64):
    shortlisted_frames = []
    already_selected = set()

    deduped = ranked_df.drop_duplicates(subset=['canonical_source_key']).copy()

    for module_name, target_n in STRATIFIED_SHORTLIST_TARGETS.items():
        if module_name == 'hybrid_multi_module_formulations':
            subset = deduped[
                deduped['entropy_control_modules']
                .astype(str)
                .apply(lambda x: len(set(x.split('|'))) >= 3)
            ]
        else:
            subset = deduped[
                deduped['entropy_control_modules']
                .astype(str)
                .str.contains(module_name, na=False)
            ]

        subset = subset.sort_values(
            ['preservation_likelihood_prior', 'assay_compatibility_prior'],
            ascending=False,
        )

        selected_rows = []
        for _, row in subset.iterrows():
            key = row['canonical_source_key']
            if key in already_selected:
                continue
            selected_rows.append(row)
            already_selected.add(key)
            if len(selected_rows) >= target_n:
                break

        if selected_rows:
            frame = pd.DataFrame(selected_rows).copy()
            frame['shortlist_sampling_strategy'] = module_name
            shortlisted_frames.append(frame)

    if shortlisted_frames:
        shortlist = pd.concat(shortlisted_frames, ignore_index=True)
    else:
        shortlist = deduped.head(total_target).copy()
        shortlist['shortlist_sampling_strategy'] = 'fallback_global_ranking'

    shortlist = shortlist.sort_values(
        ['preservation_likelihood_prior', 'assay_compatibility_prior'],
        ascending=False,
    ).head(total_target)

    return shortlist


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
            canonical_source_key = make_canonical_source_key(combo)
            for temp in TEMPERATURE_STATES:
                for phase in PHASE_STATES:
                    concentration_labels = [c[0] for c in CONCENTRATION_LEVELS[:r]]

                    preservation_prior = 0.45
                    assay_prior = 0.5
                    cleanup_prior = 0.35

                    classes = [classify_material(m) for m in combo]
                    entropy_modules = [entropy_control_module(c) for c in classes]
                    silica_roles = [silica_source_role(m) for m in combo]

                    if any(c in classes for c in ['vitrification_or_glass_forming', 'mobility_suppression']):
                        preservation_prior += 0.15
                    if 'reaction_rate_suppression' in classes:
                        preservation_prior += 0.1
                    if 'matrix_state_locking' in classes:
                        preservation_prior += 0.08
                        cleanup_prior += 0.08
                    if 'silica_source_mineralization' in classes:
                        preservation_prior += 0.13
                        cleanup_prior += 0.18
                    if 'non_silica_mineralization' in classes:
                        preservation_prior += 0.12
                        cleanup_prior += 0.2
                    if 'recoverability_or_chelation' in classes:
                        assay_prior += 0.05

                    unique_entropy_modules = set(entropy_modules)
                    if len(unique_entropy_modules) >= 2:
                        preservation_prior += 0.04
                    if len(unique_entropy_modules) >= 3:
                        preservation_prior += 0.04

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
                        'canonical_source_key': canonical_source_key,
                        'materials': '|'.join(combo),
                        'canonical_material_identities': '|'.join(canonical_material_identity(m) for m in combo),
                        'num_components': r,
                        'component_classes': '|'.join(classes),
                        'entropy_control_modules': '|'.join(entropy_modules),
                        'silica_source_roles': '|'.join(silica_roles),
                        'contains_silica_source': any(canonical_material_identity(m) == 'silica_source' for m in combo),
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

    shortlist = build_mechanism_stratified_shortlist(ranked, total_target=64)
    shortlist.to_csv(OUTPUT_DIR / 'recommended_first_round_formulations.csv', index=False)

    print(f'Generated {len(df)} virtual formulation states')
    print(f'Generated {len(shortlist)} mechanism-stratified first-round candidates')


if __name__ == '__main__':
    main()
