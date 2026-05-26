from pathlib import Path
import pandas as pd

OUT = Path('outputs')
OUT.mkdir(exist_ok=True)

SAMPLE_TYPE = 'HRP_DNA_EV_spiked_serum'
STORAGE_CONDITION = '37C_3_days'
CORE_READOUTS = 'HRP_activity|PCR_amplifiability|NTA_particle_recovery'


def infer_protocol_note(materials):
    text = str(materials).lower()
    notes = []
    if any(k in text for k in ['silica', 'silicic acid', 'tmos', 'sodium silicate']):
        notes.append('silicate/mineralization module; turbidity or pellet formation is acceptable if information is recoverable')
    if any(k in text for k in ['alginate', 'gelatin', 'hyaluronic']):
        notes.append('physical confinement module; assess direct and post-release readouts')
    if any(k in text for k in ['formaldehyde', 'glyoxal', 'methanol']):
        notes.append('state-locking/fixation module; prioritize post-cleanup assay readability')
    if any(k in text for k in ['edta', 'citrate']):
        notes.append('recoverability/chelation module; monitor enzyme inhibition risk')
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


def main():
    src = OUT / 'top_ranked_experimental_candidates.csv'
    if not src.exists():
        src = OUT / 'recommended_first_round_formulations.csv'
    if not src.exists():
        raise FileNotFoundError('Run ranking pipeline first')

    df = pd.read_csv(src).head(24)
    rows = []
    for i, row in df.iterrows():
        materials = row.get('materials', '')
        rows.append({
            'experiment_id': f'EXP1_{i+1:03d}',
            'formulation_id': row.get('formulation_id', f'FORM_{i+1:06d}'),
            'materials': materials,
            'phase_state': row.get('phase_state', 'not_specified'),
            'temperature_state': row.get('temperature_state', '37C'),
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
    print('Generated experimental_plan_first_round.csv')


if __name__ == '__main__':
    main()
