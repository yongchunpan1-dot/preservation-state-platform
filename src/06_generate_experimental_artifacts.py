from pathlib import Path

import pandas as pd

OUTPUT_DIR = Path('outputs')
OUTPUT_DIR.mkdir(exist_ok=True)


def load_candidate_table():
    candidates = [
        'top_ranked_experimental_candidates.csv',
        'recommended_first_round_formulations.csv',
        'deep_learning_recommended_formulations.csv',
    ]
    for filename in candidates:
        path = OUTPUT_DIR / filename
        if path.exists():
            return pd.read_csv(path), filename
    raise FileNotFoundError('No candidate formulation table found.')


def generate_feedback_template(df, source_file):
    preferred = [
        'formulation_id',
        'material_key',
        'canonical_source_key',
        'materials',
        'canonical_material_identities',
        'component_classes',
        'entropy_control_modules',
        'silica_source_roles',
        'phase_state',
        'temperature_state',
        'first_round_test_condition',
        'preservation_likelihood_prior',
        'assay_compatibility_prior',
        'cleanup_burden_prior',
        'overall_feasibility_score',
        'cleanup_strategy',
    ]
    cols = [c for c in preferred if c in df.columns]
    out = df[cols].head(64).copy()
    out.insert(0, 'experimental_batch_id', '')
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

    silica_count = 0
    if 'canonical_material_identities' in df.columns:
        silica_count = df['canonical_material_identities'].astype(str).str.contains('silica_source', case=False, na=False).sum()

    lines = []
    lines.append('# Experimental Design Summary')
    lines.append('')
    lines.append(f'Source candidate table: {source_file}')
    lines.append(f'Candidate formulations exported: {min(len(df), 64)}')
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
    print('Generated experimental_design_summary.md and experimental_feedback_template.csv')


if __name__ == '__main__':
    main()
