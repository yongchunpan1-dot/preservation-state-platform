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
}


def clean_df(df):
    keep = [
        c for c in [
            'formulation_id',
            'materials',
            'component_classes',
            'overall_feasibility_score',
            'preservation_likelihood_prior',
            'assay_compatibility_prior',
            'cleanup_strategy',
            'recoverability_score',
        ] if c in df.columns
    ]
    return df[keep].copy()


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
                'file': filename,
                'n_rows': len(df),
            })

        pd.DataFrame(summary_rows).to_excel(writer, sheet_name='Summary', index=False)

    print(f'Generated unified report: {output_path}')


if __name__ == '__main__':
    main()
