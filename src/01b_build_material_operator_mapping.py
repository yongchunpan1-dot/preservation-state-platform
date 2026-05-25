from pathlib import Path
import pandas as pd

OUTPUT_DIR = Path('outputs')
OUTPUT_DIR.mkdir(exist_ok=True)

MAPPINGS = [
    ('trehalose', 'ESO_001', 'primary'),
    ('trehalose', 'ESO_002', 'secondary'),
    ('sucrose', 'ESO_001', 'primary'),
    ('dextran', 'ESO_001', 'primary'),
    ('glycerol', 'ESO_001', 'primary'),
    ('DMSO', 'ESO_001', 'primary'),
    ('EDTA', 'ESO_004', 'primary'),
    ('EDTA', 'ESO_010', 'secondary'),
    ('glutathione', 'ESO_003', 'primary'),
    ('ascorbic acid', 'ESO_003', 'primary'),
    ('alginate', 'ESO_006', 'primary'),
    ('gelatin', 'ESO_006', 'primary'),
    ('hyaluronic acid', 'ESO_006', 'primary'),
    ('formaldehyde', 'ESO_005', 'primary'),
    ('glyoxal', 'ESO_005', 'primary'),
    ('methanol', 'ESO_005', 'secondary'),
    ('silica', 'ESO_007', 'primary'),
    ('silicic acid', 'ESO_007', 'primary'),
    ('orthosilicic acid', 'ESO_007', 'primary'),
    ('TMOS', 'ESO_007', 'primary'),
    ('tetramethyl orthosilicate', 'ESO_007', 'primary'),
    ('sodium silicate', 'ESO_007', 'primary'),
    ('calcium phosphate', 'ESO_007', 'primary'),
    ('ZIF-8', 'ESO_007', 'primary'),
    ('poloxamer 188', 'ESO_008', 'primary'),
    ('polyethylene glycol', 'ESO_008', 'primary'),
]


def main():
    rows = []
    for material, operator, role in MAPPINGS:
        rows.append({
            'material_name': material,
            'operator_id': operator,
            'mapping_role': role,
        })

    df = pd.DataFrame(rows)
    df.to_csv(OUTPUT_DIR / 'material_operator_mapping.csv', index=False)
    print(f'Generated material_operator_mapping.csv with {len(df)} mappings')


if __name__ == '__main__':
    main()
