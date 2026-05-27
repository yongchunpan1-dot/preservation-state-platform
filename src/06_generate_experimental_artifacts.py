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
        'canonical_source_key',
        'materials',
        'canonical_material_identities',
        'silica_source_state_summary',
        'component_classes',
        'entropy_control_modules',
        'dominant_entropy_module',
        'shortlist_sampling_strategy',
        'silica_source_roles',
        'contains_silica_source',
        'phase_state',
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
    out['sample_type'] = 'EV_protein_DNA_cell_or_plasma_sample'
    out['storage_temperature'] = '37C'
    out['storage_duration'] = '3_days'
    out['membrane_or_EV_integrity_score'] = ''
    out['protein_activity_or_marker_recovery_score'] = ''
    out['nucleic_acid_amplifiability_score'] = ''
    out['cell_or_biomarker_state_score'] = ''
    out['assay_interference_observed'] = ''
    out['cleanup_recovery_observed'] = ''
    out['visible_precipitate_or_gel'] = ''
    out['experimental_notes'] = ''
    out['source_candidate_table'] = source_file
    out['template_consistency_note'] = 'This feedback template is generated directly from recommended_first_round_formulations.csv; rows should match the first-round shortlist one-to-one.'
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

    silica_count = 0
    if 'canonical_material_identities' in df.columns:
        silica_count = df['canonical_material_identities'].astype(str).str.contains('silica_source', case=False, na=False).sum()

    lines = []
    lines.append('# Experimental Design Summary')
    lines.append('')
    lines.append(f'Source candidate table: {source_file}')
    lines.append(f'Candidate formulations exported: {len(df)}')
    lines.append(f'Expected first-round target: {EXPECTED_FIRST_ROUND_N}')
    lines.append('')
    lines.append('## Consistency rule')
    lines.append('')
    lines.append('The experimental feedback template is generated directly from recommended_first_round_formulations.csv. Each row in experimental_feedback_template.csv should map one-to-one to a first-round candidate formulation.')
    lines.append('')
    lines.append('## Purpose')
    lines.append('')
    lines.append('This file summarizes the first-round experimental validation plan for the preservation-state platform. The default accelerated screening condition is 37C for 3 days.')
    lines.append('')
    lines.append('## Preservation-state logic')
    lines.append('')
    lines.append('The output is organized around anti-entropy preservation modules, including molecular mobility suppression, chemical reaction-rate suppression, structural state locking, mineralized state locking, and recoverability.')
    lines.append('')
    lines.append('## Silica-source convention')
    lines.append('')
    lines.append('TMOS, soluble silicates, silicic acid, and orthosilicic acid are grouped as silica_source for canonical preservation-state grouping. Condensed silica is retained as a final-product reference state.')
    lines.append('')
    lines.append(f'Rows containing silica_source chemistry: {silica_count}')
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
    lines.append('## Feedback readouts')
    lines.append('')
    lines.append('- membrane_or_EV_integrity_score')
    lines.append('- protein_activity_or_marker_recovery_score')
    lines.append('- nucleic_acid_amplifiability_score')
    lines.append('- cell_or_biomarker_state_score')
    lines.append('- assay_interference_observed')
    lines.append('- cleanup_recovery_observed')
    lines.append('- visible_precipitate_or_gel')
    lines.append('- experimental_notes')

    (OUTPUT_DIR / 'experimental_design_summary.md').write_text('\n'.join(lines), encoding='utf-8')


def main():
    df, source_file = load_candidate_table()
    generate_feedback_template(df, source_file)
    generate_design_summary(df, source_file)
    print('Generated experimental_design_summary.md and experimental_feedback_template.csv from recommended_first_round_formulations.csv')


if __name__ == '__main__':
    main()
