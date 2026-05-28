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
FIRST_ROUND_TEST_CONDITION = '37C_3_days'

SILICA_SOURCE_TERMS = [
    'silicic acid',
]

STRATIFIED_SHORTLIST_TARGETS = {
    'molecular_mobility_suppression': 14,
    'chemical_reaction_rate_suppression': 14,
    'structural_state_locking': 14,
    'mineralized_state_locking': 14,
    'degradation_pathway_suppression_and_recoverability': 14,
    'hybrid_multi_module_formulations': 26,
}

MAX_PER_CANONICAL_SOURCE = 3
INTERNAL_SILICA_COLUMNS = [
    'canonical_material_identities',
    'silica_source_state_summary',
    'silica_source_roles',
    'contains_silica_source',
]


def is_silica_source(name: str):
    lower = str(name).lower()
    return any(k in lower for k in SILICA_SOURCE_TERMS)


def canonical_material_identity(name: str):
    lower = str(name).lower().strip()
    if is_silica_source(lower):
        return 'silicic_acid'
    if lower == 'silica':
        return 'silica_final_product_reference'
    return lower.replace(' ', '_')


def silica_source_state(name: str):
    lower = str(name).lower()
    if 'silicic acid' in lower:
        return 'silicic_acid'
    if lower.strip() == 'silica':
        return 'condensed_silica_state'
    return 'non_silica'


def classify_material(name: str):
    lower = str(name).lower()
    if any(k in lower for k in ['trehalose', 'sucrose', 'mannitol', 'sorbitol', 'dextran', 'raffinose', 'pullulan']):
        return 'vitrification_or_glass_forming'
    if any(k in lower for k in ['alginate', 'gelatin', 'hyaluronic', 'methylcellulose', 'polyvinylpyrrolidone']):
        return 'matrix_state_locking'
    if any(k in lower for k in ['edta', 'citrate']):
        return 'recoverability_or_chelation'
    if any(k in lower for k in ['glutathione', 'ascorbic', 'catalase', 'superoxide dismutase', 'n-acetylcysteine', 'tocopherol']):
        return 'reaction_rate_suppression'
    if any(k in lower for k in ['dmso', 'dimethyl sulfoxide', 'glycerol', 'hydroxyethyl starch', 'ectoine', 'hydroxyectoine', 'betaine', 'proline', 'glycine', 'taurine', 'arginine', 'lysine']):
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


def infer_phase_state(classes, entropy_modules):
    class_set = set(classes)
    module_set = set(entropy_modules)

    if 'matrix_state_locking' in class_set:
        return 'hydrogel_or_matrix_state'
    if 'silica_source_mineralization' in class_set or 'non_silica_mineralization' in class_set:
        return 'mineralized_state'
    if 'vitrification_or_glass_forming' in class_set:
        return 'glass_or_dry_state'
    if 'molecular_mobility_suppression' in module_set:
        return 'solution_or_viscous_state'
    return 'solution_state'


def dominant_module(entropy_modules):
    modules = list(entropy_modules)
    unique = list(dict.fromkeys(modules))

    if len(unique) >= 3:
        return 'hybrid_multi_module_formulations'

    counts = {}
    for module in modules:
        counts[module] = counts.get(module, 0) + 1

    ranked = sorted(counts.items(), key=lambda x: x[1], reverse=True)
    return ranked[0][0]


def silica_source_role(name: str):
    lower = str(name).lower()
    if 'silicic acid' in lower:
        return 'silicic_acid'
    if lower.strip() == 'silica':
        return 'condensed_silica_final_product_reference'
    return 'not_applicable'


def compatibility_penalty(materials):
    mats = ' '.join(materials).lower()
    penalty = 0.0
    if 'edta' in mats and 'calcium' in mats:
        penalty += 0.4
    return penalty


def make_material_key(materials):
    return '|'.join(sorted(materials))


def make_canonical_source_key(materials):
    return '|'.join(sorted(canonical_material_identity(m) for m in materials))


def select_diverse_rows(subset, target_n, module_name, global_seen):
    selected = []
    canonical_counts = {}
    silica_state_counts = {}

    for _, row in subset.iterrows():
        key = row['canonical_source_key']

        if key in global_seen:
            continue

        canonical_counts.setdefault(key, 0)
        if canonical_counts[key] >= MAX_PER_CANONICAL_SOURCE:
            continue

        silica_state = row.get('silica_source_state_summary', 'non_silica')
        silica_state_counts.setdefault(silica_state, 0)

        if silica_state != 'non_silica' and silica_state_counts[silica_state] >= 3:
            continue

        selected.append(row)
        global_seen.add(key)
        canonical_counts[key] += 1

        if silica_state != 'non_silica':
            silica_state_counts[silica_state] += 1

        if len(selected) >= target_n:
            break

    if not selected:
        return None

    frame = pd.DataFrame(selected).copy()
    frame['shortlist_sampling_strategy'] = module_name
    return frame


def build_mechanism_stratified_shortlist(ranked_df, total_target=96):
    shortlisted_frames = []
    global_seen = set()

    deduped = ranked_df.drop_duplicates(subset=['material_key']).copy()

    for module_name, target_n in STRATIFIED_SHORTLIST_TARGETS.items():
        subset = deduped[deduped['dominant_entropy_module'] == module_name]

        subset = subset.sort_values(
            ['preservation_likelihood_prior', 'assay_compatibility_prior'],
            ascending=False,
        )

        frame = select_diverse_rows(subset, target_n, module_name, global_seen)

        if frame is not None:
            shortlisted_frames.append(frame)

    if shortlisted_frames:
        shortlist = pd.concat(shortlisted_frames, ignore_index=True)
    else:
        shortlist = deduped.head(total_target).copy()
        shortlist['shortlist_sampling_strategy'] = 'fallback_global_ranking'

    shortlist = shortlist.head(total_target)
    return shortlist


def hide_internal_silica_columns(df):
    return df.drop(columns=[c for c in INTERNAL_SILICA_COLUMNS if c in df.columns])


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
            silica_states = [silica_source_state(m) for m in combo]
            concentration_labels = [c[0] for c in CONCENTRATION_LEVELS[:r]]

            classes = [classify_material(m) for m in combo]
            entropy_modules = [entropy_control_module(c) for c in classes]
            silica_roles = [silica_source_role(m) for m in combo]
            dominant_entropy = dominant_module(entropy_modules)
            phase_state = infer_phase_state(classes, entropy_modules)

            preservation_prior = 0.45
            assay_prior = 0.5
            cleanup_prior = 0.35

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

            if phase_state == 'glass_or_dry_state':
                preservation_prior += 0.08
            elif phase_state == 'hydrogel_or_matrix_state':
                preservation_prior += 0.05
                cleanup_prior += 0.08
            elif phase_state == 'mineralized_state':
                preservation_prior += 0.10
                cleanup_prior += 0.18

            formulation_counter += 1

            rows.append({
                'formulation_id': f'FORM_{formulation_counter:06d}',
                'material_key': material_key,
                'canonical_source_key': canonical_source_key,
                'materials': '|'.join(combo),
                'canonical_material_identities': '|'.join(canonical_material_identity(m) for m in combo),
                'silica_source_state_summary': '|'.join(sorted(set(silica_states))),
                'num_components': r,
                'component_classes': '|'.join(classes),
                'entropy_control_modules': '|'.join(entropy_modules),
                'dominant_entropy_module': dominant_entropy,
                'silica_source_roles': '|'.join(silica_roles),
                'contains_silica_source': any(canonical_material_identity(m) == 'silicic_acid' for m in combo),
                'concentration_levels': '|'.join(concentration_labels),
                'temperature_state': '37C',
                'phase_state': phase_state,
                'first_round_test_condition': FIRST_ROUND_TEST_CONDITION,
                'preservation_likelihood_prior': np.clip(preservation_prior - 0.08, 0, 1),
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

    shortlist_internal = build_mechanism_stratified_shortlist(ranked, total_target=96)
    shortlist_internal.to_csv(OUTPUT_DIR / 'recommended_first_round_formulations_internal_metadata.csv', index=False)

    shortlist = hide_internal_silica_columns(shortlist_internal)
    shortlist.to_csv(OUTPUT_DIR / 'recommended_first_round_formulations.csv', index=False)

    print(f'Generated {len(df)} virtual formulation states')
    print(f'Generated {len(shortlist)} mechanism-centered first-round candidates')


if __name__ == '__main__':
    main()
