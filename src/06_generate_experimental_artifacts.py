from pathlib import Path

import pandas as pd

OUTPUT_DIR = Path('outputs')
OUTPUT_DIR.mkdir(exist_ok=True)

FIRST_ROUND_SHORTLIST = 'recommended_first_round_formulations.csv'
EXPECTED_FIRST_ROUND_N = 64


def load_candidate_table():
    path = OUTPUT_DIR / FIRST_ROUND_SHORTLIST
    if not path.exists():
        raise FileNotFoundError(
            f'{FIRST_ROUND_SHORTLIST} was not found. Run src/04_generate_virtual_formulation_universe.py before generating experimental artifacts.'
        )
    df = pd.read_csv(path)
    if df.empty:
        raise ValueError(f'{FIRST_ROUND_SHORTLIST} is empty; cannot generate feedback template.')
    return df, FIRST_ROUND_SHORTLIST


def generate_feedback_template(df, source_file):
    preferred = [
        'formulation_id',
        'material_key',
        'materials',
        'component_classes',
        'entropy_control_modules',
        'dominant_entropy_module',
        'shortlist_sampling_strategy',
        'temperature_state',
        'first_round_test_condition',
        'preservation_likelihood_prior',
        'assay_compatibility_prior',
        'cleanup_burden_prior',
        'interaction_penalty',
        'recommended_for_first_round',
    ]

    cols = [c for c in preferred if c in df.columns]
    out = df[cols].copy()

    out.insert(0, 'experimental_batch_id', '')
    out.insert(1, 'first_round_candidate_index', range(1, len(out) + 1))

    out['tested_concentration'] = ''
    out['sample_type'] = 'EV_protein_DNA_or_plasma_sample'
    out['storage_temperature'] = '37C'
    out['storage_duration'] = '3_days'

    # Minimal experimentally grounded preservation readouts.
    out['NTA_particle_recovery_relative_to_control'] = ''
    out['HRP_activity_percent_of_control'] = ''
    out['PCR_or_qPCR_signal_relative_to_control'] = ''
    out['sample_cleanliness'] = ''
    out['experimental_notes'] = ''

    out['source_candidate_table'] = source_file
    out['template_consistency_note'] = (
        'This feedback template is generated directly from '
        'recommended_first_round_formulations.csv; rows should match '
        'the first-round shortlist one-to-one.'
    )

    out.to_csv(OUTPUT_DIR / 'experimental_feedback_template.csv', index=False)



def generate_design_summary(df, source_file):
    modules = []
    if 'entropy_control_modules' in df.columns:
        seen = set()
        for cell in df['entropy_control_modules'].dropna().astype(str):
            for module in cell.split('|'):
                if module:
                    seen.add(module)
        modules = sorted(seen)

    bucket_counts = {}
    if 'shortlist_sampling_strategy' in df.columns:
        bucket_counts = df['shortlist_sampling_strategy'].value_counts().to_dict()

    dominant_counts = {}
    if 'dominant_entropy_module' in df.columns:
        dominant_counts = df['dominant_entropy_module'].value_counts().to_dict()

    lines = []
    lines.append('# Experimental Design Summary')
    lines.append('')
    lines.append(f'Source candidate table: {source_file}')
    lines.append(f'Candidate formulations exported: {len(df)}')
    lines.append(f'Expected first-round target: {EXPECTED_FIRST_ROUND_N}')
    lines.append('')

    lines.append('## Consistency rule')
    lines.append('')
    lines.append(
        'The experimental feedback template is generated directly from '
        'recommended_first_round_formulations.csv. Each row in '
        'experimental_feedback_template.csv should map one-to-one '
        'to a first-round candidate formulation.'
    )
    lines.append('')

    lines.append('## Preservation-state framework')
    lines.append('')
    lines.append(
        'The first-round shortlist is organized around anti-entropy '
        'preservation modules rather than around any single material '
        'class. The framework explores molecular mobility suppression, '
        'chemical reaction-rate suppression, structural state locking, '
        'mineralized state locking, and degradation-pathway suppression '
        'and recoverability.'
    )
    lines.append('')

    lines.append('## Shortlist sampling strategy counts')
    lines.append('')
    if bucket_counts:
        for key, value in bucket_counts.items():
            lines.append(f'- {key}: {value}')
    else:
        lines.append('- No shortlist_sampling_strategy field detected.')
    lines.append('')

    lines.append('## Dominant entropy-module counts')
    lines.append('')
    if dominant_counts:
        for key, value in dominant_counts.items():
            lines.append(f'- {key}: {value}')
    else:
        lines.append('- No dominant_entropy_module field detected.')
    lines.append('')

    lines.append('## Entropy-control modules detected')
    lines.append('')
    if modules:
        for module in modules:
            lines.append(f'- {module}')
    else:
        lines.append('- No explicit entropy-control module field detected.')
    lines.append('')

    lines.append('## First-round experimental feedback readouts')
    lines.append('')
    lines.append('- NTA_particle_recovery_relative_to_control: overall EV or particle preservation relative to untreated control')
    lines.append('- HRP_activity_percent_of_control: protein or enzyme functional retention relative to untreated control')
    lines.append('- PCR_or_qPCR_signal_relative_to_control: nucleic-acid preservation relative to untreated control')
    lines.append('- sample_cleanliness: simple clean/usable/precipitated assessment after preservation and recovery')
    lines.append('- experimental_notes')

    (OUTPUT_DIR / 'experimental_design_summary.md').write_text(
        '\n'.join(lines),
        encoding='utf-8'
    )



def main():
    df, source_file = load_candidate_table()
    generate_feedback_template(df, source_file)
    generate_design_summary(df, source_file)
    print(
        'Generated experimental_design_summary.md and '
        'experimental_feedback_template.csv from '
        'recommended_first_round_formulations.csv'
    )


if __name__ == '__main__':
    main()
