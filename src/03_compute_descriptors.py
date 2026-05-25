from pathlib import Path
import json
import pandas as pd
import numpy as np

OUTPUT_DIR = Path('outputs')
OUTPUT_DIR.mkdir(exist_ok=True)

CLASS_RULES = {
    'glass_former': ['trehalose', 'sucrose', 'mannitol', 'sorbitol', 'dextran'],
    'cryoprotectant': ['dimethyl sulfoxide', 'dmso', 'glycerol', 'hydroxyethyl starch'],
    'hydrogel': ['alginate', 'gelatin', 'hyaluronic'],
    'polymer': ['polyethylene glycol', 'peg', 'polyvinyl alcohol', 'pva', 'poloxamer'],
    'fixative': ['glyoxal', 'formaldehyde', 'methanol', 'ethanol'],
    'chelator_buffer': ['edta', 'citrate', 'histidine', 'hepes', 'phosphate'],
    'antioxidant': ['glutathione', 'ascorbic'],
    'mineralization': ['silica', 'calcium phosphate', 'zif-8', 'zif8'],
}


def classify(name):
    n = str(name).lower()
    for cls, terms in CLASS_RULES.items():
        if any(t in n for t in terms):
            return cls
    return 'other'


def proxy_descriptors(name):
    cls = classify(name)
    return {
        'material_class_proxy': cls,
        'hydrophilicity_proxy': 0.8 if cls in ['glass_former', 'chelator_buffer', 'hydrogel'] else 0.5,
        'polymer_MW_bin': 'variable' if cls in ['polymer', 'hydrogel', 'glass_former'] else 'small_molecule_or_not_applicable',
        'charge_density_class': 'anionic' if any(k in str(name).lower() for k in ['alginate', 'edta', 'citrate', 'phosphate']) else 'neutral_or_variable',
        'crosslink_density': 'tunable' if cls in ['hydrogel', 'fixative', 'mineralization'] else 'none',
        'gel_reversibility': 0.8 if cls == 'hydrogel' else np.nan,
        'mesh_size_proxy': 'tunable' if cls == 'hydrogel' else 'not_applicable',
        'mineral_shell_type': str(name) if cls == 'mineralization' else 'not_applicable',
        'etching_or_release_method': 'acid_or_chelator' if cls == 'mineralization' else ('chelator_or_enzyme' if cls == 'hydrogel' else 'not_applicable'),
        'fixation_reversibility': 0.3 if cls == 'fixative' else np.nan,
        'expected_assay_interference_class': {
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
        'proxy_fields': list(rows[0].keys()) if rows else [],
    }
    (OUTPUT_DIR / 'descriptor_dictionary.json').write_text(json.dumps(dictionary, indent=2), encoding='utf-8')
    print(f'Generated descriptor_table.csv with {len(df)} materials')


if __name__ == '__main__':
    main()
