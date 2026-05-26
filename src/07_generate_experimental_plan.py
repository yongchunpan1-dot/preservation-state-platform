from pathlib import Path
import pandas as pd

OUT = Path('outputs')
OUT.mkdir(exist_ok=True)

SAMPLE_TYPE = 'HRP_DNA_EV_spiked_serum'
STORAGE_CONDITION = '37C_3_days'
CORE_READOUTS = 'HRP_activity|PCR_amplifiability|NTA_particle_recovery'

# Science-level first-round design: broad, stratified, and mechanism-covering.
# The final number may be lower after deduplication, but the target is ~80-120
# unique formulations for Round 1.
PER_STRATEGY_N = 18
HYBRID_N = 24
GLOBAL_TOP_N = 24

STRATEGY_FILES = {
    'overall_top': 'top_ranked_experimental_candidates.csv',
    'entropy_suppression': 'top_entropy_suppression_candidates.csv',
    'state_locking': 'top_state_locking_candidates.csv',
    'spatial_confinement': 'top_spatial_confinement_candidates.csv',
    'molecular_mobility_suppression': 'top_molecular_mobility_suppression_candidates.csv',
    'recoverable_preservation': 'top_recoverable_preservation_candidates.csv',
    'temporal_fidelity': 'top_temporal_fidelity_candidates.csv',
    'hybrid_entropy_architecture': 'top_hybrid_entropy_architectures.csv',
}


def material_key(materials):
    return '|'.join(sorted(str(materials).split('|')))


def infer_protocol_note(materials):
    text = str(materials).lower()
    notes = []
    if any(k in text for k in ['silica', 'silicic acid', 'tmos', 'sodium silicate', 'calcium phosphate', 'zif-8']):
        notes.append('mineral-locking subtype of structural state locking; turbidity/pellet is acceptable if information is recoverable')
    if any(k in text for k in ['alginate', 'gelatin', 'hyaluronic']):
        notes.append('hydrogel/matrix confinement subtype; assess direct and post-release readouts')
    if any(k in text for k in ['formaldehyde', 'glyoxal', 'methanol']):
        notes.append('covalent/solvent state-locking subtype; prioritize assay-readable recovery')
    if any(k in text for k in ['edta', 'citrate']):
        notes.append('recoverability/chelation component; monitor HRP enzyme inhibition risk')
    return '; '.join(notes) if notes else 'standard preservation candidate'


def infer_cleanup_required(materials):
    text = str(materials).lower()
    if any(k in text for k in ['silica', 'silicic acid', 'tmos', 'sodium silicate', 'calcium phosphate', 'zif-8']):
        return 'test_both_direct_and_post_cleanup'
    if any(k in text for k in ['alginate', 'gelatin', 'hyaluronic']):
        return 'test_both_direct_and_post_release'
    if any(k in text for k in ['formaldehyde', 'glyoxal']):
        return 'cleanup_or_reversal_likely_required'
    return 'direct_readout_first'


def load_strategy_candidates():
    rows = []
    for strategy, fname in STRATEGY_FILES.items():
        path = OUT / fname
        if not path.exists():
            continue
        df = pd.read_csv(path)
        if df.empty or 'materials' not in df.columns:
            continue
        n = GLOBAL_TOP_N if strategy == 'overall_top' else HYBRID_N if strategy == 'hybrid_entropy_architecture' else PER_STRATEGY_N
        df = df.head(n).copy()
        df['selection_source_strategy'] = strategy
        rows.append(df)
    if not rows:
        raise FileNotFoundError('No strategy candidate files found. Run ranking steps first.')
    return pd.concat(rows, ignore_index=True)


def assign_round_priority(row):
    src = str(row.get('selection_source_strategy', ''))
    if 'overall_top' in src or 'temporal_fidelity' in src or 'hybrid_entropy_architecture' in src:
        return 'Round1_core'
    return 'Round1_strategy_coverage'


def main():
    candidates = load_strategy_candidates()
    candidates['material_key_for_dedup'] = candidates['materials'].apply(material_key)

    grouped_rows = []
    for _, group in candidates.groupby('material_key_for_dedup', sort=False):
        first = group.iloc[0].copy()
        first['selection_source_strategy'] = '|'.join(sorted(group['selection_source_strategy'].astype(str).unique()))
        grouped_rows.append(first)

    df = pd.DataFrame(grouped_rows)

    rows = []
    for i, row in df.iterrows():
        materials = row.get('materials', '')
        rows.append({
            'experiment_id': f'EXP1_{i+1:03d}',
            'round_priority': assign_round_priority(row),
            'selection_source_strategy': row.get('selection_source_strategy', 'not_specified'),
            'formulation_id': row.get('formulation_id', f'FORM_{i+1:06d}'),
            'materials': materials,
            'component_classes': row.get('component_classes', ''),
            'phase_state_model_prior': row.get('phase_state', 'not_specified'),
            'temperature_state_model_prior': row.get('temperature_state', 'not_specified'),
            'concentration_levels': row.get('concentration_levels', 'screening_level'),
            'sample_type': SAMPLE_TYPE,
            'storage_condition': STORAGE_CONDITION,
            'required_readouts': CORE_READOUTS,
            'protein_readout': 'HRP_activity_recovery',
            'dna_readout': 'PCR_amplifiability_recovery',
            'membrane_readout': 'NTA_particle_recovery',
            'cleanup_test_plan': infer_cleanup_required(materials),
            'controls': 'fresh_control|untreated_37C_control|4C_control|material_blank|assay_blank',
            'experimental_note': infer_protocol_note(materials),
            'model_overall_feasibility_score': row.get('overall_feasibility_score', None),
        })

    plan = pd.DataFrame(rows)
    plan.to_csv(OUT / 'experimental_plan_first_round.csv', index=False)

    design_summary = pd.DataFrame([
        {'parameter': 'target_round1_unique_formulations', 'value': '80-120'},
        {'parameter': 'per_strategy_requested', 'value': PER_STRATEGY_N},
        {'parameter': 'hybrid_requested', 'value': HYBRID_N},
        {'parameter': 'overall_top_requested', 'value': GLOBAL_TOP_N},
        {'parameter': 'actual_unique_formulations', 'value': len(plan)},
        {'parameter': 'primary_readouts', 'value': CORE_READOUTS},
        {'parameter': 'sample_model', 'value': SAMPLE_TYPE},
        {'parameter': 'stress_condition', 'value': STORAGE_CONDITION},
    ])
    design_summary.to_csv(OUT / 'experimental_design_summary.csv', index=False)

    print(f'Generated Science-level stratified experimental_plan_first_round.csv with {len(plan)} unique formulations')


if __name__ == '__main__':
    main()
