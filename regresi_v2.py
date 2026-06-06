# -*- coding: utf-8 -*-
"""
regresi_v2.py — Versi Peningkatan (Bebas Leakage)
===================================================
Perbaikan dari regresi fix.py:
  1. Log-transform target (LoanOriginalAmount sangat skewed)
  2. Feature engineering lebih kaya & informatif
  3. Optuna hyperparameter tuning (lebih efisien dari RandomizedSearch)
  4. 3 model berlomba: XGBoost vs LightGBM vs HistGradientBoosting
  5. Best model otomatis disimpan ke .pkl & MLflow
  6. Semua run tercatat di MLflow untuk perbandingan

❌ TIDAK dipakai (leakage):
   - MonthlyLoanPayment : dihitung dari LoanOriginalAmount (rumus PMT)
   - BorrowerRate       : ditetapkan SETELAH loan disetujui
   - LoanStatus         : status post-disbursement
   - LP_* kolom         : semua post-disbursement

✅ Semua fitur tersedia SEBELUM keputusan kredit dibuat.
"""

import warnings
warnings.filterwarnings("ignore")

import numpy as np
import pandas as pd
import joblib
import mlflow
import mlflow.sklearn
import optuna
optuna.logging.set_verbosity(optuna.logging.WARNING)

from sklearn.model_selection        import train_test_split, cross_val_score
from sklearn.impute                 import SimpleImputer
from sklearn.preprocessing          import OrdinalEncoder, PowerTransformer
from sklearn.compose                import ColumnTransformer
from sklearn.pipeline               import Pipeline
from sklearn.metrics                import r2_score, mean_absolute_error
from sklearn.ensemble               import HistGradientBoostingRegressor
from xgboost                        import XGBRegressor
from lightgbm                       import LGBMRegressor

# =====================================================================
# KONFIGURASI
# =====================================================================
CSV_PATH        = "C:/Users/ASUS TUF/Documents/ML OPS/PRAKTIKUM/cleaning_prosperloadata.csv"
PKL_OUTPUT      = "C:/Users/ASUS TUF/Documents/ML OPS/PRAKTIKUM/FRONT END PBL/PDBL-MLOPS/best_model_regresi2.pkl"
MLFLOW_URI      = "file:///C:/Users/ASUS TUF/Documents/ML OPS/PRAKTIKUM/mlruns"
EXPERIMENT_NAME = "Prediksi_Limit_Pinjaman_Kredit_v2"
RANDOM_STATE    = 42
TEST_SIZE       = 0.2
N_TRIALS        = 40   # jumlah percobaan Optuna per model (naikan ke 80 untuk lebih optimal)

# =====================================================================
# FITUR AMAN (bebas leakage)
# =====================================================================
FEATURES = [
    # Profil pinjaman
    'Term',
    'ListingCategory (numeric)',

    # Skor & Rating kredit internal
    'ProsperScore',
    'ProsperRating (numeric)',

    # Profil peminjam
    'EmploymentStatus',
    'IsBorrowerHomeowner',
    'Occupation',
    'EmploymentStatusDuration',     # lama bekerja (bulan) → stabilitas

    # Kapasitas bayar
    'StatedMonthlyIncome',
    'IncomeVerifiable',
    'DebtToIncomeRatio',

    # Credit score eksternal
    'CreditScoreRangeLower',
    'CreditScoreRangeUpper',

    # Riwayat kredit
    'TotalCreditLinespast7years',
    'OpenCreditLines',
    'CurrentCreditLines',
    'TotalTrades',
    'TradesNeverDelinquent (percentage)',

    # Kartu kredit
    'BankcardUtilization',
    'AvailableBankcardCredit',
    'RevolvingCreditBalance',
    'OpenRevolvingAccounts',
    'OpenRevolvingMonthlyPayment',

    # Risiko & delinquency
    'InquiriesLast6Months',
    'TotalInquiries',
    'CurrentDelinquencies',
    'DelinquenciesLast7Years',
    'PublicRecordsLast10Years',
    'AmountDelinquent',             # total nominal tunggakan (bukan post-loan)

    # Target
    'LoanOriginalAmount'
]

# =====================================================================
# TAHAP 1: LOAD & FEATURE ENGINEERING
# =====================================================================
print("=" * 60)
print("  REGRESI V2 — Bebas Leakage, Target: LoanOriginalAmount")
print("=" * 60)
print("\n[1/5] Memuat dan memproses data...")

df = pd.read_csv(CSV_PATH, low_memory=False)
df.dropna(subset=['LoanOriginalAmount'], inplace=True)

# Hanya ambil kolom yang tersedia di dataset
available = [c for c in FEATURES if c in df.columns]
df_sub = df[available].copy()

# ── Feature Engineering (semua aman, pre-loan) ──────────────────────

# 1. Kapasitas bayar bersih per bulan setelah kewajiban
df_sub['net_monthly_capacity'] = (
    df_sub['StatedMonthlyIncome'] * (1 - df_sub['DebtToIncomeRatio'].clip(0, 1))
)

# 2. Credit score tengah (lebih stabil dari upper/lower sendiri)
df_sub['credit_score_mid'] = (
    (df_sub['CreditScoreRangeLower'] + df_sub['CreditScoreRangeUpper']) / 2
)

# 3. Rentang credit score (indikator ketidakpastian)
df_sub['credit_score_range'] = (
    df_sub['CreditScoreRangeUpper'] - df_sub['CreditScoreRangeLower']
)

# 4. Estimasi total beban hutang bulanan
df_sub['total_debt_monthly'] = (
    df_sub['StatedMonthlyIncome'] * df_sub['DebtToIncomeRatio'].clip(0, 2)
)

# 5. Composite risk score (semakin tinggi = semakin berisiko)
df_sub['delinq_composite'] = (
    df_sub['CurrentDelinquencies'] * 3 +
    df_sub['DelinquenciesLast7Years'] +
    df_sub['PublicRecordsLast10Years'] * 2
)

# 6. Credit utilization health (semakin kecil = lebih sehat)
df_sub['revolving_pressure'] = (
    df_sub['OpenRevolvingMonthlyPayment'] /
    (df_sub['StatedMonthlyIncome'] + 1)
)

# 7. Kepadatan inquiry (inquiry banyak = sinyal negatif)
df_sub['inquiry_density'] = (
    df_sub['InquiriesLast6Months'] /
    (df_sub['TotalCreditLinespast7years'].clip(1, None))
)

# 8. Income per credit line (kemampuan kelola banyak kredit)
df_sub['income_per_credit_line'] = (
    df_sub['StatedMonthlyIncome'] /
    (df_sub['CurrentCreditLines'].clip(1, None))
)

# 9. Available credit ratio
df_sub['available_credit_ratio'] = (
    df_sub['AvailableBankcardCredit'] /
    (df_sub['AvailableBankcardCredit'] + df_sub['RevolvingCreditBalance'] + 1)
)

# 10. Stability score (lama kerja × income verifiable)
df_sub['stability_score'] = (
    df_sub.get('EmploymentStatusDuration', pd.Series(0, index=df_sub.index)) *
    df_sub['IncomeVerifiable'].fillna(0)
)

# ── Log-transform target (distribusi sangat skewed ke kanan) ─────────
# PENTING: inverse saat prediksi → np.expm1(pred)
y_raw = df_sub['LoanOriginalAmount'].values
y     = np.log1p(y_raw)   # log(1 + x) → aman untuk x >= 0

X = df_sub.drop(columns=['LoanOriginalAmount'])

print(f"    Dataset  : {len(df_sub):,} baris | {X.shape[1]} fitur input")
print(f"    Target   : ${y_raw.min():,.0f} – ${y_raw.max():,.0f} "
      f"(mean ${y_raw.mean():,.0f}) | log-transformed")

# ── Tipe data ────────────────────────────────────────────────────────
CAT_COLS = X.select_dtypes(include=['object', 'bool']).columns.tolist()
NUM_COLS = X.select_dtypes(include=['int64', 'float64']).columns.tolist()

for col in CAT_COLS:
    X[col] = X[col].astype(str)

X_train, X_test, y_train, y_test = train_test_split(
    X, y, test_size=TEST_SIZE, random_state=RANDOM_STATE
)
print(f"    Train    : {len(X_train):,} | Test: {len(X_test):,}")

# =====================================================================
# TAHAP 2: PIPELINE PREPROCESSING
# =====================================================================
print("\n[2/5] Membangun pipeline preprocessing...")

numeric_transformer = Pipeline([
    ('imputer',   SimpleImputer(strategy='median')),
    ('power',     PowerTransformer(method='yeo-johnson')),  # normalize skewed
])

categorical_transformer = Pipeline([
    ('imputer', SimpleImputer(strategy='constant', fill_value='Unknown')),
    ('encoder', OrdinalEncoder(handle_unknown='use_encoded_value', unknown_value=-1)),
])

preprocessor = ColumnTransformer([
    ('num', numeric_transformer,     NUM_COLS),
    ('cat', categorical_transformer, CAT_COLS),
], remainder='drop')

print(f"    Numerik      : {len(NUM_COLS)} kolom -> median + Yeo-Johnson normalize")
print(f"    Kategorikal  : {len(CAT_COLS)} kolom -> ordinal encode")

# =====================================================================
# TAHAP 3: OPTUNA TUNING - 3 MODEL BERLOMBA
# =====================================================================
print(f"\n[3/5] Optuna tuning ({N_TRIALS} trials x model)...")

mlflow.set_tracking_uri(MLFLOW_URI)
mlflow.set_experiment(EXPERIMENT_NAME)

results = {}

# ─────────────────────────────────────────────────────────────────────
# Model A: XGBoost
# ─────────────────────────────────────────────────────────────────────
print("\n  ▶ [A] XGBoost...")

def objective_xgb(trial):
    params = {
        'model__n_estimators':      trial.suggest_int('n_estimators', 400, 1200),
        'model__learning_rate':     trial.suggest_float('learning_rate', 0.01, 0.1, log=True),
        'model__max_depth':         trial.suggest_int('max_depth', 4, 10),
        'model__subsample':         trial.suggest_float('subsample', 0.6, 1.0),
        'model__colsample_bytree':  trial.suggest_float('colsample_bytree', 0.5, 1.0),
        'model__min_child_weight':  trial.suggest_int('min_child_weight', 1, 10),
        'model__gamma':             trial.suggest_float('gamma', 0, 0.5),
        'model__reg_alpha':         trial.suggest_float('reg_alpha', 0, 1.0),
        'model__reg_lambda':        trial.suggest_float('reg_lambda', 0.5, 5.0),
    }
    pipe = Pipeline([
        ('preprocessor', preprocessor),
        ('model', XGBRegressor(random_state=RANDOM_STATE, n_jobs=-1, tree_method='hist')),
    ])
    pipe.set_params(**params)
    scores = cross_val_score(pipe, X_train, y_train, cv=3, scoring='r2', n_jobs=-1)
    return scores.mean()

study_xgb = optuna.create_study(direction='maximize', sampler=optuna.samplers.TPESampler(seed=RANDOM_STATE))
study_xgb.optimize(objective_xgb, n_trials=N_TRIALS, show_progress_bar=False)

best_xgb_pipe = Pipeline([
    ('preprocessor', preprocessor),
    ('model', XGBRegressor(random_state=RANDOM_STATE, n_jobs=-1, tree_method='hist')),
])
xgb_params = {f"model__{k}": v for k, v in study_xgb.best_params.items()}
best_xgb_pipe.set_params(**xgb_params)
best_xgb_pipe.fit(X_train, y_train)

y_pred_xgb_log  = best_xgb_pipe.predict(X_test)
y_pred_xgb      = np.expm1(y_pred_xgb_log)       # inverse log-transform
y_test_original = np.expm1(y_test)

r2_xgb  = r2_score(y_test_original, y_pred_xgb)
mae_xgb = mean_absolute_error(y_test_original, y_pred_xgb)
results['XGBoost'] = {'r2': r2_xgb, 'mae': mae_xgb, 'pipe': best_xgb_pipe, 'params': study_xgb.best_params}
print(f"    XGBoost   → R²: {r2_xgb:.4f} | MAE: ${mae_xgb:,.0f}")

# ─────────────────────────────────────────────────────────────────────
# Model B: LightGBM
# ─────────────────────────────────────────────────────────────────────
print("\n  ▶ [B] LightGBM...")

def objective_lgbm(trial):
    params = {
        'model__n_estimators':      trial.suggest_int('n_estimators', 400, 1500),
        'model__learning_rate':     trial.suggest_float('learning_rate', 0.01, 0.1, log=True),
        'model__max_depth':         trial.suggest_int('max_depth', 4, 12),
        'model__num_leaves':        trial.suggest_int('num_leaves', 31, 255),
        'model__subsample':         trial.suggest_float('subsample', 0.6, 1.0),
        'model__colsample_bytree':  trial.suggest_float('colsample_bytree', 0.5, 1.0),
        'model__min_child_samples': trial.suggest_int('min_child_samples', 10, 100),
        'model__reg_alpha':         trial.suggest_float('reg_alpha', 0, 1.0),
        'model__reg_lambda':        trial.suggest_float('reg_lambda', 0, 5.0),
    }
    pipe = Pipeline([
        ('preprocessor', preprocessor),
        ('model', LGBMRegressor(random_state=RANDOM_STATE, n_jobs=-1, verbose=-1)),
    ])
    pipe.set_params(**params)
    scores = cross_val_score(pipe, X_train, y_train, cv=3, scoring='r2', n_jobs=-1)
    return scores.mean()

study_lgbm = optuna.create_study(direction='maximize', sampler=optuna.samplers.TPESampler(seed=RANDOM_STATE))
study_lgbm.optimize(objective_lgbm, n_trials=N_TRIALS, show_progress_bar=False)

best_lgbm_pipe = Pipeline([
    ('preprocessor', preprocessor),
    ('model', LGBMRegressor(random_state=RANDOM_STATE, n_jobs=-1, verbose=-1)),
])
lgbm_params = {f"model__{k}": v for k, v in study_lgbm.best_params.items()}
best_lgbm_pipe.set_params(**lgbm_params)
best_lgbm_pipe.fit(X_train, y_train)

y_pred_lgbm_log = best_lgbm_pipe.predict(X_test)
y_pred_lgbm     = np.expm1(y_pred_lgbm_log)

r2_lgbm  = r2_score(y_test_original, y_pred_lgbm)
mae_lgbm = mean_absolute_error(y_test_original, y_pred_lgbm)
results['LightGBM'] = {'r2': r2_lgbm, 'mae': mae_lgbm, 'pipe': best_lgbm_pipe, 'params': study_lgbm.best_params}
print(f"    LightGBM  → R²: {r2_lgbm:.4f} | MAE: ${mae_lgbm:,.0f}")

# ─────────────────────────────────────────────────────────────────────
# Model C: HistGradientBoosting (sklearn, native NaN support)
# ─────────────────────────────────────────────────────────────────────
print("\n  ▶ [C] HistGradientBoosting...")

def objective_hgb(trial):
    params = {
        'model__max_iter':             trial.suggest_int('max_iter', 300, 1000),
        'model__learning_rate':        trial.suggest_float('learning_rate', 0.01, 0.15, log=True),
        'model__max_depth':            trial.suggest_int('max_depth', 4, 12),
        'model__max_leaf_nodes':       trial.suggest_int('max_leaf_nodes', 20, 150),
        'model__min_samples_leaf':     trial.suggest_int('min_samples_leaf', 10, 100),
        'model__l2_regularization':    trial.suggest_float('l2_regularization', 0, 1.0),
    }
    pipe = Pipeline([
        ('preprocessor', preprocessor),
        ('model', HistGradientBoostingRegressor(random_state=RANDOM_STATE)),
    ])
    pipe.set_params(**params)
    scores = cross_val_score(pipe, X_train, y_train, cv=3, scoring='r2', n_jobs=-1)
    return scores.mean()

study_hgb = optuna.create_study(direction='maximize', sampler=optuna.samplers.TPESampler(seed=RANDOM_STATE))
study_hgb.optimize(objective_hgb, n_trials=N_TRIALS, show_progress_bar=False)

best_hgb_pipe = Pipeline([
    ('preprocessor', preprocessor),
    ('model', HistGradientBoostingRegressor(random_state=RANDOM_STATE)),
])
hgb_params = {f"model__{k}": v for k, v in study_hgb.best_params.items()}
best_hgb_pipe.set_params(**hgb_params)
best_hgb_pipe.fit(X_train, y_train)

y_pred_hgb_log = best_hgb_pipe.predict(X_test)
y_pred_hgb     = np.expm1(y_pred_hgb_log)

r2_hgb  = r2_score(y_test_original, y_pred_hgb)
mae_hgb = mean_absolute_error(y_test_original, y_pred_hgb)
results['HistGBT'] = {'r2': r2_hgb, 'mae': mae_hgb, 'pipe': best_hgb_pipe, 'params': study_hgb.best_params}
print(f"    HistGBT   → R²: {r2_hgb:.4f} | MAE: ${mae_hgb:,.0f}")

# =====================================================================
# TAHAP 4: LOG SEMUA KE MLFLOW & PILIH PEMENANG
# =====================================================================
print("\n[4/5] Logging semua model ke MLflow...")

best_name = max(results, key=lambda k: results[k]['r2'])
best_r2   = results[best_name]['r2']
best_mae  = results[best_name]['mae']
best_pipe = results[best_name]['pipe']

for model_name, res in results.items():
    run_name = f"v2_{model_name}_log_target"
    with mlflow.start_run(run_name=run_name):
        mlflow.log_param("model_type",       model_name)
        mlflow.log_param("n_features",       X.shape[1])
        mlflow.log_param("log_transform",    "log1p(LoanOriginalAmount)")
        mlflow.log_param("n_trials_optuna",  N_TRIALS)
        mlflow.log_param("leakage_removed",  "MonthlyLoanPayment, BorrowerRate, LoanStatus")
        mlflow.log_param("train_size",       len(X_train))
        mlflow.log_param("test_size",        len(X_test))

        for k, v in res['params'].items():
            mlflow.log_param(k, round(v, 6) if isinstance(v, float) else v)

        mlflow.log_metric("R2_Score", res['r2'])
        mlflow.log_metric("MAE",      res['mae'])
        mlflow.log_metric("is_best",  1 if model_name == best_name else 0)

        mlflow.sklearn.log_model(
            sk_model=res['pipe'],
            artifact_path=f"model_{model_name.lower()}",
            input_example=X_test.iloc[:3]
        )

    status = " <- BEST" if model_name == best_name else ""
    print(f"    [{model_name}] R2={res['r2']:.4f} | MAE=${res['mae']:,.0f}{status}")

# =====================================================================
# TAHAP 5: SIMPAN MODEL TERBAIK KE .pkl
# =====================================================================
print(f"\n[5/5] Menyimpan model terbaik ({best_name}) ke .pkl...")
joblib.dump(best_pipe, PKL_OUTPUT)
print(f"    ✅ Tersimpan: {PKL_OUTPUT}")

# =====================================================================
# LAPORAN AKHIR
# =====================================================================
print()
print("=" * 60)
print("  LAPORAN AKHIR — Regresi V2 (Bebas Leakage)")
print("=" * 60)
print(f"  {'Model':<15} {'R2 Score':>10} {'MAE ($)':>12}")
print(f"  {'-'*40}")
for name, res in sorted(results.items(), key=lambda x: -x[1]['r2']):
    flag = " [BEST]" if name == best_name else ""
    print(f"  {name:<15} {res['r2']:>10.4f} {res['mae']:>12,.0f}{flag}")
print(f"  {'-'*40}")
print(f"  Fitur input   : {X.shape[1]} kolom")
print(f"  Log-transform : log1p(target) -> expm1(pred)")
print(f"  Leakage       : TIDAK ADA")
print(f"  MLflow UI     : http://localhost:5000")
print("=" * 60)
print()
print("[INFO] Cara lihat di MLflow:")
print("   1. Buka terminal baru")
print("   2. Jalankan: mlflow ui --backend-store-uri 'file:///C:/Users/ASUS TUF/Documents/ML OPS/PRAKTIKUM/mlruns' --port 5000")
print("   3. Buka http://localhost:5000")
print("   4. Pilih experiment 'Prediksi_Limit_Pinjaman_Kredit_v2'")
print("   5. Bandingkan run v2_XGBoost, v2_LightGBM, v2_HistGBT")
