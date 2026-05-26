from pathlib import Path
import pandas as pd

OUT = Path('outputs')
OUT.mkdir(exist_ok=True)

# Top-level output categories are operator-level strategies, not favored materials.
# Mineralization/biomineralization is treated as a subtype of structural-spatial
# state locking and is therefore included under state_locking rather than exported
# as a standalone top-level ranking category.
STRATEGIES = {
    'entropy_suppression': ['trehalose','sucrose','glycerol','dextran','dmso','edta','glutathione','ascorbic acid'],
    'state_locking': [
        'formaldehyde','glyoxal','methanol',
        'alginate','gelatin','hyaluronic acid','hydrogel',
        'silica','silicic acid','orthosilicic acid','tmos','sodium silicate','calcium phosphate','zif-8'
    ],
    'spatial_confinement': ['alginate','gelatin','hyaluronic acid','hydrogel'],
    'molecular_mobility_suppression': ['trehalose','sucrose','glycerol','dmso','dextran','mannitol','sorbitol'],
    'temporal_fidelity': ['trehalose','sucrose','edta','glutathione','ascorbic acid','alginate','glyoxal','silica','silicic acid'],
    'recoverable_preservation': ['edta','citrate','alginate','hyaluronic acid','buffer exchange','sec','spr'],
}

SUBTYPES = {
    'covalent_locking': ['formaldehyde','glyoxal','methanol'],
    'hydrogel_confinement': ['alginate','gelatin','hyaluronic acid','hydrogel'],
    'mineral_locking': ['silica','silicic acid','orthosilicic acid','tmos','sodium silicate','calcium phosphate','zif-8'],
}


def hit_count(text, words):
    t = str(text).lower()
    return sum(1 for w in words if w.lower() in t)


def main():
    src = OUT / 'formulation_assay_compatibility.csv'
    if not src.exists():
        src = OUT / 'top_ranked_experimental_candidates.csv'
    if not src.exists():
        raise FileNotFoundError('Run 05_build_assay_risk_engine.py first')

    df = pd.read_csv(src)
    score_col = 'overall_feasibility_score' if 'overall_feasibility_score' in df.columns else 'preservation_likelihood_prior'

    summary = []
    for name, words in STRATEGIES.items():
        d = df.copy()
        d['strategy'] = name
        d['strategy_match_score'] = d['materials'].apply(lambda x: hit_count(x, words))
        for subtype, subtype_words in SUBTYPES.items():
            d[f'subtype_{subtype}_present'] = d['materials'].apply(lambda x: int(hit_count(x, subtype_words) > 0))
        d = d[d['strategy_match_score'] > 0]
        d = d.sort_values(['strategy_match_score', score_col], ascending=False)
        d.head(30).to_csv(OUT / f'top_{name}_candidates.csv', index=False)
        summary.append({'strategy': name, 'n_candidates': len(d), 'output': f'top_{name}_candidates.csv'})

    hybrid = df.copy()
    for name, words in STRATEGIES.items():
        hybrid[f'{name}_present'] = hybrid['materials'].apply(lambda x: int(hit_count(x, words) > 0))
    present_cols = [f'{k}_present' for k in STRATEGIES]
    hybrid['n_entropy_strategies_combined'] = hybrid[present_cols].sum(axis=1)
    for subtype, subtype_words in SUBTYPES.items():
        hybrid[f'subtype_{subtype}_present'] = hybrid['materials'].apply(lambda x: int(hit_count(x, subtype_words) > 0))
    hybrid = hybrid.sort_values(['n_entropy_strategies_combined', score_col], ascending=False)
    hybrid.head(50).to_csv(OUT / 'top_hybrid_entropy_architectures.csv', index=False)
    pd.DataFrame(summary).to_csv(OUT / 'strategy_output_summary.csv', index=False)
    print('Generated unbiased operator-level strategy rankings')


if __name__ == '__main__':
    main()
