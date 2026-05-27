from pathlib import Path
import argparse
import json

import numpy as np
import pandas as pd
from sklearn.compose import ColumnTransformer
from sklearn.impute import SimpleImputer
from sklearn.model_selection import train_test_split
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import OneHotEncoder, StandardScaler

try:
    import torch
    from torch import nn
    from torch.utils.data import DataLoader, TensorDataset
except Exception:
    torch = None
    nn = None
    DataLoader = None
    TensorDataset = None

OUTPUT_DIR = Path('outputs')
MODEL_DIR = Path('models')
OUTPUT_DIR.mkdir(exist_ok=True)
MODEL_DIR.mkdir(exist_ok=True)

TARGETS = [
    'preservation_score',
    'assay_compatibility',
    'cleanup_burden',
    'translation_priority',
]


class MultiHeadPreservationNet(nn.Module if nn is not None else object):
    def __init__(self, input_dim, hidden_dim=128, dropout=0.15):
        if nn is None:
            raise ImportError('PyTorch is not installed.')
        super().__init__()
        self.encoder = nn.Sequential(
            nn.Linear(input_dim, hidden_dim), nn.ReLU(), nn.Dropout(dropout),
            nn.Linear(hidden_dim, hidden_dim), nn.ReLU(), nn.Dropout(dropout),
        )
        self.heads = nn.ModuleList([nn.Linear(hidden_dim, 1) for _ in range(4)])

    def forward(self, x):
        z = self.encoder(x)
        return torch.cat([torch.sigmoid(h(z)) for h in self.heads], dim=1)


def load_features():
    # Prefer the assay-scored candidate table when available because it already
    # contains recoverability, assay-risk, and feasibility fields.
    for path in [
        OUTPUT_DIR / 'formulation_assay_compatibility.csv',
        OUTPUT_DIR / 'top_ranked_experimental_candidates.csv',
        OUTPUT_DIR / 'preservation_universe_virtual.csv',
        OUTPUT_DIR / 'preservation_universe_virtual.parquet',
        OUTPUT_DIR / 'descriptor_table.csv',
    ]:
        if path.exists() and path.suffix == '.csv':
            return pd.read_csv(path), path.name
        if path.exists() and path.suffix == '.parquet':
            return pd.read_parquet(path), path.name
    raise FileNotFoundError('Run descriptor/universe/assay-risk generation first.')


def numeric_prior(df, col, default):
    if col in df.columns:
        return pd.to_numeric(df[col], errors='coerce').fillna(default).clip(0, 1)
    return pd.Series(default, index=df.index, dtype=float)


def add_mock_labels(df, seed=7):
    rng = np.random.default_rng(seed)
    out = df.copy()
    p = numeric_prior(out, 'preservation_likelihood_prior', 0.55)
    c = numeric_prior(out, 'assay_compatibility_prior', 0.50)
    b = numeric_prior(out, 'cleanup_burden_prior', 0.45)
    t = numeric_prior(out, 'regulatory_status_prior', 0.50)
    out['preservation_score'] = np.clip(p + rng.normal(0, 0.05, len(out)), 0, 1)
    out['assay_compatibility'] = np.clip(c - 0.25 * b + rng.normal(0, 0.05, len(out)), 0, 1)
    out['cleanup_burden'] = np.clip(b + rng.normal(0, 0.05, len(out)), 0, 1)
    out['translation_priority'] = np.clip(0.7 * t + 0.3 * c + rng.normal(0, 0.05, len(out)), 0, 1)
    return out


def build_matrix(df):
    feature_cols = [c for c in df.columns if c not in TARGETS]
    num_cols = [c for c in feature_cols if pd.api.types.is_numeric_dtype(df[c])]
    cat_cols = [c for c in feature_cols if c not in num_cols]
    prep = ColumnTransformer([
        ('num', Pipeline([('imp', SimpleImputer(strategy='median')), ('scale', StandardScaler())]), num_cols),
        ('cat', Pipeline([('imp', SimpleImputer(strategy='most_frequent')), ('oh', OneHotEncoder(handle_unknown='ignore'))]), cat_cols),
    ])
    X = prep.fit_transform(df[feature_cols])
    if hasattr(X, 'toarray'):
        X = X.toarray()
    y = df[TARGETS].astype(float).values
    return X, y, prep, feature_cols


def train(df, epochs=50):
    if torch is None:
        raise ImportError('Install torch to run deep learning model.')
    labeled = add_mock_labels(df)
    X, y, prep, feature_cols = build_matrix(labeled)
    if len(labeled) < 2:
        raise ValueError('At least two rows are required for train/test split.')
    Xtr, Xte, ytr, yte = train_test_split(X, y, test_size=0.2, random_state=7)
    model = MultiHeadPreservationNet(Xtr.shape[1])
    opt = torch.optim.AdamW(model.parameters(), lr=1e-3, weight_decay=1e-4)
    loss_fn = nn.MSELoss()
    loader = DataLoader(TensorDataset(torch.tensor(Xtr, dtype=torch.float32), torch.tensor(ytr, dtype=torch.float32)), batch_size=64, shuffle=True)
    history = []
    for e in range(epochs):
        model.train()
        losses = []
        for xb, yb in loader:
            opt.zero_grad()
            loss = loss_fn(model(xb), yb)
            loss.backward()
            opt.step()
            losses.append(float(loss.detach()))
        model.eval()
        with torch.no_grad():
            val = loss_fn(model(torch.tensor(Xte, dtype=torch.float32)), torch.tensor(yte, dtype=torch.float32))
        history.append({'epoch': e + 1, 'train_loss': float(np.mean(losses)), 'val_loss': float(val)})
    return model, prep, feature_cols, labeled, history


def deterministic_recommendation(df, top_k=24, source_table='unknown'):
    """Fallback recommendation scaffold for CI/artifact generation.

    This keeps the GitHub Actions artifact pipeline reproducible without requiring
    a heavyweight PyTorch install. The output is intentionally labeled as a
    scaffold, not as a trained neural-network result.
    """
    out = df.copy()

    preservation = numeric_prior(out, 'preservation_likelihood_prior', 0.55)
    assay = numeric_prior(out, 'assay_compatibility_prior', 0.50)
    cleanup = numeric_prior(out, 'cleanup_burden_prior', 0.45)
    regulatory = numeric_prior(out, 'regulatory_status_prior', 0.50)
    recoverability = numeric_prior(out, 'recoverability_score', 1 - cleanup)

    pcr_risk = numeric_prior(out, 'PCR_risk_score', 0.10)
    lcms_risk = numeric_prior(out, 'LCMS_risk_score', 0.10)
    scrna_risk = numeric_prior(out, 'scRNAseq_risk_score', 0.10)
    mean_assay_risk = (pcr_risk + lcms_risk + scrna_risk) / 3

    if 'overall_feasibility_score' in out.columns:
        base_score = pd.to_numeric(out['overall_feasibility_score'], errors='coerce').fillna(0)
    else:
        base_score = preservation + assay + recoverability - cleanup - mean_assay_risk

    out['dl_predicted_preservation_score'] = preservation
    out['dl_predicted_assay_compatibility'] = assay
    out['dl_predicted_cleanup_burden'] = cleanup
    out['dl_predicted_translation_priority'] = 0.6 * regulatory + 0.4 * assay
    out['dl_acquisition_score'] = base_score + 0.25 * out['dl_predicted_translation_priority']
    out['model_status'] = 'deterministic_scaffold_no_torch'
    out['model_input_table'] = source_table
    out['model_note'] = 'PyTorch was not available in this run; recommendations use deterministic prior-based scoring for artifact generation.'

    out = out.sort_values('dl_acquisition_score', ascending=False).head(top_k)
    out.to_csv(OUTPUT_DIR / 'deep_learning_recommended_formulations.csv', index=False)

    metadata = {
        'model_status': 'deterministic_scaffold_no_torch',
        'source_table': source_table,
        'top_k': top_k,
        'note': 'Install torch or enable the PyTorch workflow path to train MultiHeadPreservationNet. Current artifact is a reproducible prior-based recommendation scaffold.',
    }
    (MODEL_DIR / 'deep_learning_model_metadata.json').write_text(json.dumps(metadata, indent=2), encoding='utf-8')
    pd.DataFrame([metadata]).to_csv(MODEL_DIR / 'deep_learning_training_history.csv', index=False)
    return out


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--epochs', type=int, default=50)
    parser.add_argument('--top-k', type=int, default=24)
    parser.add_argument('--require-torch', action='store_true', help='Fail if PyTorch is unavailable instead of using deterministic fallback.')
    args = parser.parse_args()

    df, source_table = load_features()

    if torch is None and not args.require_torch:
        deterministic_recommendation(df, top_k=args.top_k, source_table=source_table)
        print('Generated deep_learning_recommended_formulations.csv using deterministic scaffold fallback')
        return

    model, prep, feature_cols, labeled, history = train(df, epochs=args.epochs)
    X = prep.transform(labeled[feature_cols])
    if hasattr(X, 'toarray'):
        X = X.toarray()
    model.eval()
    with torch.no_grad():
        pred = model(torch.tensor(X, dtype=torch.float32)).numpy()
    out = labeled.copy()
    out['dl_predicted_preservation_score'] = pred[:, 0]
    out['dl_predicted_assay_compatibility'] = pred[:, 1]
    out['dl_predicted_cleanup_burden'] = pred[:, 2]
    out['dl_predicted_translation_priority'] = pred[:, 3]
    out['dl_acquisition_score'] = out['dl_predicted_preservation_score'] + out['dl_predicted_assay_compatibility'] + out['dl_predicted_translation_priority'] - out['dl_predicted_cleanup_burden']
    out['model_status'] = 'trained_pytorch_mock_label_scaffold'
    out['model_input_table'] = source_table
    out.sort_values('dl_acquisition_score', ascending=False).head(args.top_k).to_csv(OUTPUT_DIR / 'deep_learning_recommended_formulations.csv', index=False)
    pd.DataFrame(history).to_csv(MODEL_DIR / 'deep_learning_training_history.csv', index=False)
    torch.save(model.state_dict(), MODEL_DIR / 'multi_head_preservation_net.pt')
    (MODEL_DIR / 'feature_columns.json').write_text(json.dumps(feature_cols, indent=2))
    print('Generated deep_learning_recommended_formulations.csv')


if __name__ == '__main__':
    main()
