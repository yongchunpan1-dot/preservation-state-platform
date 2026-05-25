import pandas as pd
from pathlib import Path

OUTPUT_DIR = Path('outputs')
OUTPUT_DIR.mkdir(exist_ok=True)

states = [
    ('trehalose_solution_low', 'glass-state stabilization'),
    ('trehalose_glass_matrix', 'glass-state stabilization'),
    ('alginate_sodium_solution', 'hydrogel precursor'),
    ('alginate_calcium_hydrogel', 'hydrogel encapsulation'),
    ('glyoxal_fixed_state', 'fixation-state preservation'),
    ('PFA_crosslinked_state', 'crosslinked preservation'),
    ('methanol_fixed_state', 'solvent fixation'),
    ('DMSO_low_temperature_live_state', 'cryopreservation'),
    ('ZIF8_mineral_shell_state', 'mineral encapsulation'),
    ('silica_mineralized_state', 'silicification')
]

rows = []

for idx, (entity, module) in enumerate(states):
    rows.append({
        'entity_id': f'PS_{idx:04d}',
        'canonical_name': entity,
        'material_family': module,
        'phase_state': 'engineered preservation state',
        'preservation_module': module,
        'reversibility_score_prior': 0.5,
        'preservation_likelihood_prior': 0.7,
        'assay_compatibility_prior': 0.5,
        'cleanup_burden_prior': 0.4,
        'experimental_status': 'computational_seed'
    })

core = pd.DataFrame(rows)
core.to_csv(OUTPUT_DIR / 'preservation_state_core_216.csv', index=False)

print('Generated preservation_state_core_216.csv')
