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


class MultiHeadPreservationNet(nn.Module):
    def __init__(self, input_dim, hidden_dim=128, dropout=0.15):
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
    for path in [
        OUTPUT_DIR / 'preservation_universe_virtual.csv',
        OUTPUT_DIR / 'preservation_universe_virtual.parquet',
        OUTPUT_DIR / 'descriptor_table.csv',
    ]:
        if path.exists() and path.suffix == '.csv':
            return pd.read_csv(path)
        if path.exists() and path.suffix == '.parquet':
            return pd.read_parquet(path)
    raise FileNotFoundError('Run descriptor/universe generation first.')


def add_mock_labels(df, seed=7):
    rng = np.random.default_rng(seed)
    out = df.copy()
    def prior(col, default):
        if col in out.columns:
            return pd.to_numeric(out[col], errors='coerce').fillna(default).clip(0, 1)
        return pd.Series(default, index=out.index)
    p = prior('preservation_likelihood_prior', 0.55)
    c = prior('assay_compatibility_prior', 0.50)
    b = prior('cleanup_burden_prior', 0.45)
    t = prior('regulatory_status_prior', 0.50)
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


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--epochs', type=int, default=50)
    parser.add_argument('--top-k', type=int, default=24)
    args = parser.parse_args()
    df = load_features()
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
    out.sort_values('dl_acquisition_score', ascending=False).head(args.top_k).to_csv(OUTPUT_DIR / 'deep_learning_recommended_formulations.csv', index=False)
    pd.DataFrame(history).to_csv(MODEL_DIR / 'deep_learning_training_history.csv', index=False)
    torch.save(model.state_dict(), MODEL_DIR / 'multi_head_preservation_net.pt')
    (MODEL_DIR / 'feature_columns.json').write_text(json.dumps(feature_cols, indent=2))
    print('Generated deep_learning_recommended_formulations.csv')


if __name__ == '__main__':
    main()
