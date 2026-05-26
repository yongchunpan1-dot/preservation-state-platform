"""Build the first-principles entropy-suppression ontology.

Preservation is represented as suppression of biological state drift.
Materials are implementations of entropy-suppression operators, not the primary
ontology layer. Mineralization/biomineralization is treated as one subtype of
structural-spatial state locking, not as an independent top-level principle.
"""
from pathlib import Path
import pandas as pd

OUTPUT_DIR = Path('outputs')
OUTPUT_DIR.mkdir(exist_ok=True)

OPERATORS = [
    {
        'operator_id': 'ESO_001',
        'operator_name': 'molecular_mobility_suppression',
        'entropy_axis': 'molecular_motion',
        'mechanism_definition': 'Reduce translational, rotational, and conformational freedom to slow state drift.',
        'state_drift_target': 'diffusion, unfolding, aggregation, membrane remodeling',
        'operator_subtypes': 'glass_state|vitrification|freezing|crowding',
        'representative_implementations': 'trehalose_glass|sucrose_glass|freezing|vitrification|polymer_crowding',
        'reversibility_prior': 0.75,
        'assay_readability_prior': 0.75,
        'temporal_fidelity_prior': 0.80,
    },
    {
        'operator_id': 'ESO_002',
        'operator_name': 'water_activity_reduction',
        'entropy_axis': 'hydration_dynamics',
        'mechanism_definition': 'Lower water activity to reduce hydrolysis, enzymatic catalysis, and molecular mobility.',
        'state_drift_target': 'hydrolysis, enzyme activity, membrane hydration changes',
        'operator_subtypes': 'drying|lyophilization|osmotic_control|sugar_glass',
        'representative_implementations': 'drying|lyophilization|sugar_glass|salt_osmolyte_control',
        'reversibility_prior': 0.70,
        'assay_readability_prior': 0.70,
        'temporal_fidelity_prior': 0.78,
    },
    {
        'operator_id': 'ESO_003',
        'operator_name': 'reaction_rate_suppression',
        'entropy_axis': 'chemical_reactivity',
        'mechanism_definition': 'Suppress spontaneous chemical reactions through temperature, pH, redox, and ionic control.',
        'state_drift_target': 'oxidation, hydrolysis, Maillard-like chemistry, pH drift',
        'operator_subtypes': 'temperature_control|pH_control|redox_control|metal_chelation',
        'representative_implementations': 'low_temperature|pH_buffering|antioxidants|metal_chelation',
        'reversibility_prior': 0.85,
        'assay_readability_prior': 0.80,
        'temporal_fidelity_prior': 0.76,
    },
    {
        'operator_id': 'ESO_004',
        'operator_name': 'enzymatic_entropy_control',
        'entropy_axis': 'biochemical_catalysis',
        'mechanism_definition': 'Reduce enzymatic degradation of nucleic acids, proteins, lipids, and metabolites.',
        'state_drift_target': 'RNase, DNase, protease, phosphatase, lipase activity',
        'operator_subtypes': 'nuclease_inhibition|protease_inhibition|lipase_inhibition|phosphatase_inhibition',
        'representative_implementations': 'EDTA|protease_inhibitors|RNase_inhibitors|phosphatase_inhibitors',
        'reversibility_prior': 0.88,
        'assay_readability_prior': 0.72,
        'temporal_fidelity_prior': 0.74,
    },
    {
        'operator_id': 'ESO_005',
        'operator_name': 'structural_spatial_state_locking',
        'entropy_axis': 'structural_and_spatial_degrees_of_freedom',
        'mechanism_definition': 'Restrict structural and spatial degrees of freedom through covalent, polymeric, hydrogel, mineral, or hybrid locking while preserving recoverable information.',
        'state_drift_target': 'morphology loss, spatial rearrangement, antigen diffusion, vesicle collapse, molecular leakage',
        'operator_subtypes': 'covalent_locking|hydrogel_confinement|mineral_locking|hybrid_shell_locking',
        'representative_implementations': 'formaldehyde|PFA|glyoxal|alginate_hydrogel|gelatin_matrix|hyaluronic_acid_gel|silicic_acid|orthosilicic_acid|TMOS_derived_silica|sodium_silicate|silica_shell|calcium_phosphate|ZIF8',
        'reversibility_prior': 0.50,
        'assay_readability_prior': 0.55,
        'temporal_fidelity_prior': 0.86,
    },
    {
        'operator_id': 'ESO_006',
        'operator_name': 'interface_stabilization',
        'entropy_axis': 'interfacial_energy',
        'mechanism_definition': 'Reduce interfacial stress, adsorption, air-water damage, and membrane/interface destabilization.',
        'state_drift_target': 'protein adsorption, vesicle rupture, membrane fusion, aggregation',
        'operator_subtypes': 'surfactant_interface_control|polymer_interface_shielding|protein_carrier_stabilization',
        'representative_implementations': 'poloxamer|PEG|albumin|surfactant_low_dose',
        'reversibility_prior': 0.80,
        'assay_readability_prior': 0.58,
        'temporal_fidelity_prior': 0.70,
    },
    {
        'operator_id': 'ESO_007',
        'operator_name': 'microbial_and_bioburden_control',
        'entropy_axis': 'external_biological_growth',
        'mechanism_definition': 'Suppress microbial growth and exogenous biological activity during storage.',
        'state_drift_target': 'contamination, metabolite drift, microbial enzyme release',
        'operator_subtypes': 'sterility|antimicrobial_hold|filtration|growth_suppression',
        'representative_implementations': 'antimicrobial_hold|sterility|azide_low_dose|filtration',
        'reversibility_prior': 0.70,
        'assay_readability_prior': 0.55,
        'temporal_fidelity_prior': 0.60,
    },
    {
        'operator_id': 'ESO_008',
        'operator_name': 'recoverability_control',
        'entropy_axis': 'information_retrieval',
        'mechanism_definition': 'Enable reversal, cleanup, release, or assay-readable recovery after preservation.',
        'state_drift_target': 'irreversible locking, assay masking, extraction failure, residual interference',
        'operator_subtypes': 'degelation|de_crosslinking|mineral_etching|buffer_exchange|assay_cleanup',
        'representative_implementations': 'EDTA_degelation|citrate_release|acid_etching|buffer_exchange|SEC|SPRI|detergent_removal',
        'reversibility_prior': 0.92,
        'assay_readability_prior': 0.85,
        'temporal_fidelity_prior': 0.65,
    },
]


def main():
    df = pd.DataFrame(OPERATORS)
    df.to_csv(OUTPUT_DIR / 'entropy_operator_table.csv', index=False)
    print(f'Generated entropy_operator_table.csv with {len(df)} entropy-suppression operators')


if __name__ == '__main__':
    main()
