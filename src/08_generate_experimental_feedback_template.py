from pathlib import Path
import pandas as pd

OUT = Path('outputs')
OUT.mkdir(exist_ok=True)


def main():
    plan_path = OUT / 'experimental_plan_first_round.csv'
    if not plan_path.exists():
        raise FileNotFoundError('Run experimental plan generation first')

    plan = pd.read_csv(plan_path)

    rows = []
    for _, row in plan.iterrows():
        rows.append({
            'experiment_id': row['experiment_id'],
            'formulation_id': row['formulation_id'],
            'materials': row['materials'],
            'protein_function_recovery': '',
            'dna_amplifiability_recovery': '',
            'membrane_particle_recovery': '',
            'cleanup_required': '',
            'post_cleanup_recovery_optional': '',
            'notes_optional': '',
        })

    out = pd.DataFrame(rows)
    out.to_csv(OUT / 'experimental_feedback_template.csv', index=False)
    print('Generated experimental_feedback_template.csv')


if __name__ == '__main__':
    main()
