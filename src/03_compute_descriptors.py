from pathlib import Path
import json
import pandas as pd
import numpy as np

OUTPUT_DIR = Path('outputs')
OUTPUT_DIR.mkdir(exist_ok=True)

SILICA_FORMING_PRECURSOR_TERMS = [
    'silica-forming precursor',
    'silicic acid',
    'orthosilicic acid',
    'silicate',
    'sodium silicate',
    'tetramethyl orthosilicate',
    'tmos',
    'teos',
]

CLASS_RULES = {
    'glass_former': ['trehalose', 'sucrose', 'mannitol', 'sorbitol', 'dextran'],
    'cryoprotectant': ['dimethyl sulfoxide', 'dmso', 'glycerol', 'hydroxyethyl starch'],
    'hydrogel': ['alginate', 'gelatin', 'hyaluronic'],
    'polymer': ['polyethylene glycol', 'peg', 'polyvinyl alcohol', 'pva', 'poloxamer'],
    'fixative': ['glyoxal', 'formaldehyde', 'methanol', 'ethanol'],
    'chelator_buffer': ['edta', 'citrate', 'histidine', 'hepes', 'phosphate'],
    'antioxidant': ['glutathione', 'ascorbic'],
    # Mineralization is now a mechanistic class, not a final-product label.
    # Silica-forming precursors are handled explicitly below so TMOS/silicate/silicic acid
    # are not collapsed with the final condensed silica phase.
    'mineralization': ['calcium phosphate', 'zif-8', 'zif8'],
}


def is_silica_forming_precursor(name):
    n = str(name).lower()
    return any(t in n for t in SILICA_FORMING_PRECURSOR_TERMS)


def classify(name):
    n = str(name).lower()
    if is_silica_forming_precursor(n):
        return 'silica_forming_precursor'
    if n.strip() == 'silica':
        return 'silica_final_product_reference'
    for cls, terms in CLASS_RULES.items():
        if any(t in n for t in terms):
            return cls
    return 'other'


def silica_role(name):
    n = str(name).lower()
    if 'tetramethyl orthosilicate' in n or 'tmos' in n or 'teos' in n:
        return 'hydrolyzable_alkoxysilane_precursor'
    if 'sodium silicate' in n or 'silicate' in n:
        return 'aqueous_silicate_precursor'
    if 'silicic acid' in n or 'orthosilicic acid' in n:
        return 'hydrolysis_product_or_monomeric_silica_precursor'
    if n.strip() == 'silica':
        return 'condensed_silica_final_product_reference'
    return 'not_applicable'


def proxy_descriptors(name):
    cls = classify(name)
    silica_related = cls in ['silica_forming_precursor', 'silica_final_product_reference']
    return {
        'material_class_proxy': cls,
        'functional_category': 'silica-forming precursor' if cls == 'silica_forming_precursor' else cls,
        'hydrophilicity_proxy': 0.8 if cls in ['glass_former', 'chelator_buffer', 'hydrogel', 'silica_forming_precursor'] else 0.5,
        'polymer_MW_bin': 'variable' if cls in ['polymer', 'hydrogel', 'glass_former'] else 'small_molecule_or_not_applicable',
        'charge_density_class': 'anionic' if any(k in str(name).lower() for k in ['alginate', 'edta', 'citrate', 'phosphate', 'silicate']) else 'neutral_or_variable',
        'crosslink_density': 'tunable' if cls in ['hydrogel', 'fixative', 'mineralization', 'silica_forming_precursor'] else 'none',
        'gel_reversibility': 0.8 if cls == 'hydrogel' else np.nan,
        'mesh_size_proxy': 'tunable' if cls == 'hydrogel' else 'not_applicable',
        'mineral_shell_type': 'amorphous_silica_or_silica_like_network' if cls == 'silica_forming_precursor' else (str(name) if cls == 'mineralization' else 'not_applicable'),
        'silica_chemistry_role': silica_role(name),
        'hydrolysis_product': 'silicic_acid_or_silanol_species' if cls == 'silica_forming_precursor' else 'not_applicable',
        'final_condensation_product': 'amorphous_silica_or_silica_like_network' if silica_related else 'not_applicable',
        'etching_or_release_method': 'acid_or_fluoride_or_silica_dissolution_workflow' if silica_related else ('acid_or_chelator' if cls == 'mineralization' else ('chelator_or_enzyme' if cls == 'hydrogel' else 'not_applicable')),
        'fixation_reversibility': 0.3 if cls == 'fixative' else np.nan,
        'expected_assay_interference_class': {
            'silica_forming_precursor': 'silica_condensation_or_mineral_carryover',
            'silica_final_product_reference': 'silica_particle_or_shell_carryover',
            'mineralization': 'mineral_particle',
            'hydrogel': 'hydrogel_fragment',
            'polymer': 'polymer_carryover',
            'fixative': 'crosslink_or_solvent_burden',
            'chelator_buffer': 'ionic_or_chelation_effect',
        }.get(cls, 'low_or_unknown'),
    }


def main():
    evidence_path = OUTPUT_DIR / 'evidence_table.csv'
    if not evidence_path.exists():
        raise FileNotFoundError('Run src/01_build_evidence_table.py first')
    evidence = pd.read_csv(evidence_path)
    materials = sorted(evidence['material_name'].dropna().unique())
    rows = []
    for material in materials:
        row = {'material_name': material}
        row.update(proxy_descriptors(material))
        row['descriptor_source'] = 'rule_based_proxy_descriptors; upgradeable_to_pubchem_rdkit'
        rows.append(row)
    df = pd.DataFrame(rows)
    df.to_csv(OUTPUT_DIR / 'descriptor_table.csv', index=False)
    dictionary = {
        'descriptor_source': 'Proxy descriptors for first-pass AI-guided formulation ranking.',
        'small_molecule_upgrade': 'Add PubChem/RDKit descriptors when exact structures are available.',
        'silica_ontology_note': 'TMOS, soluble silicates, and silicic/orthosilicic acid are treated as silica-forming precursor chemistry; silica is treated as the condensed final-product reference, not the precursor material.',
        'proxy_fields': list(rows[0].keys()) if rows else [],
    }
    (OUTPUT_DIR / 'descriptor_dictionary.json').write_text(json.dumps(dictionary, indent=2), encoding='utf-8')
    print(f'Generated descriptor_table.csv with {len(df)} materials')


if __name__ == '__main__':
    main()
