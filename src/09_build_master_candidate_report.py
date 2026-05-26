from pathlib import Path
import pandas as pd

OUT = Path('outputs')
OUT.mkdir(exist_ok=True)

FILES = {
    'Top Experimental Candidates': 'top_ranked_experimental_candidates.csv',
    'Entropy Suppression': 'top_entropy_suppression_candidates.csv',
    'State Locking': 'top_state_locking_candidates.csv',
    'Spatial Confinement': 'top_spatial_confinement_candidates.csv',
    'Molecular Mobility Suppression': 'top_molecular_mobility_suppression_candidates.csv',
    'Recoverable Preservation': 'top_recoverable_preservation_candidates.csv',
    'Temporal Fidelity': 'top_temporal_fidelity_candidates.csv',
    'Hybrid Entropy Architectures': 'top_hybrid_entropy_architectures.csv',
    'Experimental Plan': 'experimental_plan_first_round.csv',
    'Feedback Template': 'experimental_feedback_template.csv',
}


def clean_df(df):
    preferred = [
        'formulation_id',
        'materials',
        'component_classes',
        'overall_feasibility_score',
        'preservation_likelihood_prior',
        'assay_compatibility_prior',
        'cleanup_strategy',
        'recoverability_score',
        'sample_type',
        'storage_condition',
        'required_readouts',
        'cleanup_test_plan',
    ]
    keep = [c for c in preferred if c in df.columns]
    return df[keep].copy() if keep else df.copy()


def main():
    output_path = OUT / 'MASTER_PRESERVATION_CANDIDATE_REPORT.xlsx'

    with pd.ExcelWriter(output_path, engine='openpyxl') as writer:
        summary_rows = []

        for sheet_name, filename in FILES.items():
            path = OUT / filename
            if not path.exists():
                continue

            df = pd.read_csv(path)
            df = clean_df(df)
            df.to_excel(writer, sheet_name=sheet_name[:31], index=False)

            summary_rows.append({
                'section': sheet_name,
                'rows': len(df),
            })

        pd.DataFrame(summary_rows).to_excel(writer, sheet_name='Summary', index=False)

    # Remove noisy intermediate CSVs from the user-facing output set.
    removable = [
        'top_entropy_suppression_candidates.csv',
        'top_state_locking_candidates.csv',
        'top_spatial_confinement_candidates.csv',
        'top_molecular_mobility_suppression_candidates.csv',
        'top_recoverable_preservation_candidates.csv',
        'top_temporal_fidelity_candidates.csv',
        'top_hybrid_entropy_architectures.csv',
        'strategy_output_summary.csv',
    ]

    for fname in removable:
        f = OUT / fname
        if f.exists():
            try:
                f.unlink()
            except Exception:
                pass

    print(f'Generated consolidated workbook: {output_path}')


if __name__ == '__main__':
    main()
