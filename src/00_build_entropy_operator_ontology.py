"""Build the first-principles entropy-suppression ontology.

This module reframes preservation chemistry from a material list into a set of
state-drift / entropy-suppression operators. Materials are treated as
implementations of operators, not as the primary ontology layer.
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
        'representative_implementations': 'EDTA|protease_inhibitors|RNase_inhibitors|phosphatase_inhibitors',
        'reversibility_prior': 0.88,
        'assay_readability_prior': 0.72,
        'temporal_fidelity_prior': 0.74,
    },
    {
        'operator_id': 'ESO_005',
        'operator_name': 'covalent_state_locking',
        'entropy_axis': 'structural_degrees_of_freedom',
        'mechanism_definition': 'Chemically lock macromolecular and spatial structures through covalent crosslinking.',
        'state_drift_target': 'morphology loss, spatial rearrangement, antigen diffusion',
        'representative_implementations': 'formaldehyde|PFA|glyoxal|crosslinking_fixatives',
        'reversibility_prior': 0.30,
        'assay_readability_prior': 0.55,
        'temporal_fidelity_prior': 0.82,
    },
    {
        'operator_id': 'ESO_006',
        'operator_name': 'physical_confinement',
        'entropy_axis': 'spatial_rearrangement',
        'mechanism_definition': 'Physically confine cells, vesicles, and biomolecules in a recoverable matrix.',
        'state_drift_target': 'spatial diffusion, aggregation, mechanical disruption',
        'representative_implementations': 'alginate_hydrogel|GelMA|collagen_matrix|hyaluronic_acid_gel',
        'reversibility_prior': 0.78,
        'assay_readability_prior': 0.62,
        'temporal_fidelity_prior': 0.75,
    },
    {
        'operator_id': 'ESO_007',
        'operator_name': 'mineralization_state_locking',
        'entropy_axis': 'structural_and_spatial_locking',
        'mechanism_definition': 'Create inorganic or hybrid shells/networks that lock biological structures against thermal, chemical, and spatial drift.',
        'state_drift_target': 'morphology collapse, molecular diffusion, ambient degradation, spatial information loss',
        'representative_implementations': 'silicic_acid|orthosilicic_acid|TMOS|sodium_silicate|silica_shell|calcium_phosphate|ZIF8',
        'reversibility_prior': 0.45,
        'assay_readability_prior': 0.48,
        'temporal_fidelity_prior': 0.88,
    },
    {
        'operator_id': 'ESO_008',
        'operator_name': 'interface_stabilization',
        'entropy_axis': 'interfacial_energy',
        'mechanism_definition': 'Reduce interfacial stress, adsorption, air-water damage, and membrane/interface destabilization.',
        'state_drift_target': 'protein adsorption, vesicle rupture, membrane fusion, aggregation',
        'representative_implementations': 'poloxamer|PEG|albumin|surfactant_low_dose',
        'reversibility_prior': 0.80,
        'assay_readability_prior': 0.58,
        'temporal_fidelity_prior': 0.70,
    },
    {
        'operator_id': 'ESO_009',
        'operator_name': 'microbial_and_bioburden_control',
        'entropy_axis': 'external_biological_growth',
        'mechanism_definition': 'Suppress microbial growth and exogenous biological activity during storage.',
        'state_drift_target': 'contamination, metabolite drift, microbial enzyme release',
        'representative_implementations': 'antimicrobial_hold|sterility|azide_low_dose|filtration',
        'reversibility_prior': 0.70,
        'assay_readability_prior': 0.55,
        'temporal_fidelity_prior': 0.60,
    },
    {
        'operator_id': 'ESO_010',
        'operator_name': 'recoverability_control',
        'entropy_axis': 'information_retrieval',
        'mechanism_definition': 'Enable reversal, cleanup, release, or assay-readable recovery after preservation.',
        'state_drift_target': 'irreversible locking, assay masking, extraction failure, residual interference',
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
