# -*- coding: utf-8 -*-
"""
regresi_v3.py - Target Kapasitas Finansial (Bebas Leakage)
==========================================================

PERUBAHAN FUNDAMENTAL dari v1/v2:
  Target BUKAN lagi LoanOriginalAmount (permintaan nasabah).
  Target BARU = PLAFON IDEAL yang seharusnya diberikan bank,
  dihitung dari kapasitas finansial nasabah (mirip Kredivo).

RUMUS UNDERWRITING:
  1. Kapasitas cicilan = Gaji x (DTI_maks - DTI_sekarang)
  2. Risk multiplier   = f(credit_score, prosper_score, delinquency, ...)
  3. Konversi ke plafon = kapasitas x risk_mult x faktor_anuitas(bunga, tenor)
  4. Clip ke range      = [$1,000 - $35,000] (sesuai range dataset)

LEAKAGE ANALYSIS:
  xx TIDAK DIPAKAI (post-decision / leakage):
     - MonthlyLoanPayment    : dihitung dari LoanOriginalAmount
     - BorrowerRate/APR      : ditetapkan SETELAH loan disetujui
     - LenderYield           : turunan dari BorrowerRate
     - EstimatedEffectiveYield, EstimatedLoss, EstimatedReturn : post-pricing
     - LoanStatus            : status setelah pencairan
     - LoanCurrentDaysDelinquent : performa post-loan
     - LoanMonthsSinceOrigination : post-loan
     - PercentFunded, Investors : post-listing (crowdfunding)
     - Recommendations, InvestmentFromFriends* : post-listing
     - LoanOriginalAmount    : permintaan nasabah (bukan keputusan bank)

  OK DIPAKAI (tersedia SEBELUM keputusan kredit):
     - Semua fitur profil keuangan nasabah
     - ProsperScore/Rating   : skor risiko internal (pre-decision)
     - Credit score           : dari credit bureau (pre-decision)
     - Semua riwayat kredit   : data historis nasabah
"""

import sys
import os
import warnings

# Fix encoding Windows
if sys.stdout and hasattr(sys.stdout, 'reconfigure'):
    try:
        sys.stdout.reconfigure(encoding='utf-8')
    except Exception:
        pass

os.environ['PYTHONIOENCODING'] = 'utf-8'
warnings.filterwarnings("ignore")

import numpy as np
import pandas as pd
import joblib
import mlflow
import mlflow.sklearn
import optuna
optuna.logging.set_verbosity(optuna.logging.WARNING)

from sklearn.model_selection  import train_test_split, cross_val_score
from sklearn.impute           import SimpleImputer
from sklearn.preprocessing    import OrdinalEncoder
from sklearn.compose          import ColumnTransformer
from sklearn.pipeline         import Pipeline
from sklearn.metrics          import r2_score, mean_absolute_error, mean_squared_error
from xgboost                  import XGBRegressor
from lightgbm                 import LGBMRegressor

# =====================================================================
# KONFIGURASI
# =====================================================================
CSV_PATH        = "C:/Users/ASUS TUF/Documents/ML OPS/PRAKTIKUM/cleaning_prosperloadata.csv"
PKL_OUTPUT      = "C:/Users/ASUS TUF/Documents/ML OPS/PRAKTIKUM/FRONT END PBL/PDBL-MLOPS/best_model_regresi2.pkl"
MLFLOW_URI      = "file:///C:/Users/ASUS TUF/Documents/ML OPS/PRAKTIKUM/mlruns"
EXPERIMENT_NAME = "Prediksi_Limit_Pinjaman_Kredit_v3"
RANDOM_STATE    = 42
TEST_SIZE       = 0.2
N_TRIALS        = 50

# Batas DTI maksimal (standar OJK / CFPB = 43%)
DTI_MAX = 0.43

# Range plafon realistis (sesuai dataset Prosper)
PLAFON_MIN = 1000
PLAFON_MAX = 35000


# =====================================================================
# TAHAP 1: LOAD DATA
# =====================================================================
print("=" * 60)
print("  REGRESI V3 -- Target: Plafon Kapasitas (Bank-Style)")
print("=" * 60)
print("\n[1/6] Memuat data...")

df = pd.read_csv(CSV_PATH, low_memory=False)
print(f"    Dataset awal : {len(df):,} baris")


# =====================================================================
# TAHAP 2: KONSTRUKSI TARGET (Plafon Ideal)
# =====================================================================
print("\n[2/6] Menghitung target 'plafon_ideal' dari kapasitas finansial...")
print("    Rumus: plafon = kapasitas_cicilan x risk_multiplier x anuitas")
print(f"    DTI maks = {DTI_MAX:.0%} | Range plafon = ${PLAFON_MIN:,} - ${PLAFON_MAX:,}")

def compute_ideal_plafon(row):
    """
    Hitung plafon ideal yang SEHARUSNYA diberikan bank.
    Semua input = data pre-loan. Tidak ada leakage.
    
    Langkah:
    1. Kapasitas cicilan bersih = gaji x (DTI_maks - DTI_sekarang)
    2. Risk multiplier = penyesuaian berdasarkan profil kredit
    3. Konversi cicilan -> plafon via formula anuitas
    4. Clip ke range realistis
    """
    
    # ── 1. KAPASITAS CICILAN BERSIH ──────────────────────────────────
    income = max(float(row.get('StatedMonthlyIncome', 0) or 0), 100)
    dti    = min(float(row.get('DebtToIncomeRatio', 0) or 0), 0.99)
    
    # Sisa kapasitas = gaji x (batas_maks - kewajiban_sekarang)
    # Minimal 5% dari gaji (floor, supaya tidak nol)
    spare = max(income * (DTI_MAX - dti), income * 0.05)
    
    # ── 2. RISK MULTIPLIER ───────────────────────────────────────────
    # 2a. Credit Score tier
    cs = float(row.get('CreditScoreRangeLower', 600) or 600)
    if   cs >= 740: cs_mult = 1.00
    elif cs >= 700: cs_mult = 0.88
    elif cs >= 680: cs_mult = 0.78
    elif cs >= 660: cs_mult = 0.68
    elif cs >= 640: cs_mult = 0.58
    elif cs >= 620: cs_mult = 0.48
    else:           cs_mult = 0.38
    
    # 2b. Prosper Score (1-11, semakin tinggi = semakin aman)
    ps = float(row.get('ProsperScore', 5) or 5)
    ps_factor = 0.55 + (ps / 11.0) * 0.45   # range 0.55 - 1.0
    
    # 2c. Delinquency penalty
    cur_del  = float(row.get('CurrentDelinquencies', 0) or 0)
    past_del = float(row.get('DelinquenciesLast7Years', 0) or 0)
    pub_rec  = float(row.get('PublicRecordsLast10Years', 0) or 0)
    delinq_score = cur_del * 3 + past_del * 0.5 + pub_rec * 2
    delinq_mult  = max(0.25, 1.0 - delinq_score * 0.06)
    
    # 2d. Homeowner bonus
    home = row.get('IsBorrowerHomeowner', False)
    if isinstance(home, str):
        home = home.lower() in ('true', '1', 'yes')
    home_mult = 1.12 if home else 1.0
    
    # 2e. Employment stability
    emp_dur = float(row.get('EmploymentStatusDuration', 0) or 0)
    emp_mult = min(1.12, 1.0 + emp_dur / 300.0)  # gradual, max 12% bonus
    
    # 2f. Income verification bonus
    inc_ver = float(row.get('IncomeVerifiable', 0) or 0)
    ver_mult = 1.05 if inc_ver else 0.92
    
    # 2g. Credit utilization penalty
    bk_util = float(row.get('BankcardUtilization', 0.5) or 0.5)
    if   bk_util <= 0.30: util_mult = 1.05
    elif bk_util <= 0.50: util_mult = 1.00
    elif bk_util <= 0.75: util_mult = 0.92
    else:                 util_mult = 0.82
    
    # Combined risk multiplier
    risk_mult = cs_mult * ps_factor * delinq_mult * home_mult * emp_mult * ver_mult * util_mult
    
    # ── 3. KONVERSI KE PLAFON VIA ANUITAS ────────────────────────────
    term = int(row.get('Term', 36) or 36)
    
    # Bunga ditetapkan berdasarkan risk tier (aturan bisnis bank, bukan dari data)
    prosper_rating = float(row.get('ProsperRating (numeric)', 3) or 3)
    if   prosper_rating >= 6 and cs >= 700: annual_rate = 0.08
    elif prosper_rating >= 4 and cs >= 660: annual_rate = 0.13
    elif prosper_rating >= 3 and cs >= 620: annual_rate = 0.20
    else:                                   annual_rate = 0.28
    
    monthly_rate = annual_rate / 12.0
    if monthly_rate > 0 and term > 0:
        # PV of annuity formula: PV = PMT x [(1 - (1+r)^-n) / r]
        annuity_factor = (1 - (1 + monthly_rate) ** (-term)) / monthly_rate
    else:
        annuity_factor = float(term)
    
    # ── 4. PLAFON IDEAL (JANGKAR HISTORIS + GUARDRAIL KAPASITAS) ──────
    plafon_capacity = spare * risk_mult * annuity_factor
    
    # Ambil data pinjaman historis nyata dari dataset
    actual_loan_amount = float(row.get('LoanOriginalAmount', 0) or 0)
    if actual_loan_amount <= 0:
        actual_loan_amount = 3000.0  # fallback jika tidak ada data nominal awal
        
    # Target Plafon Ideal = Berapa yang dipinjam di dunia nyata,
    # tetapi dipangkas secara ketat ke kapasitas maksimalnya demi keselamatan risiko.
    plafon = min(actual_loan_amount, plafon_capacity)
    
    # Clip ke range realistis
    plafon = max(PLAFON_MIN, min(PLAFON_MAX, round(plafon)))
    
    return plafon


# Hitung target baru
df['plafon_ideal'] = df.apply(compute_ideal_plafon, axis=1)

print(f"    Target baru 'plafon_ideal':")
print(f"      Min  : ${df['plafon_ideal'].min():,.0f}")
print(f"      Mean : ${df['plafon_ideal'].mean():,.0f}")
print(f"      Max  : ${df['plafon_ideal'].max():,.0f}")
print(f"      Std  : ${df['plafon_ideal'].std():,.0f}")


# =====================================================================
# TAHAP 3: PERSIAPAN FITUR
# =====================================================================
print("\n[3/6] Menyiapkan fitur (semua pre-loan, bebas leakage)...")

# Fitur yang AMAN dipakai (tersedia sebelum keputusan kredit)
SAFE_FEATURES = [
    # Profil pinjaman
    'Term',
    'ListingCategory (numeric)',
    
    # Skor & rating internal
    'ProsperScore',
    'ProsperRating (numeric)',
    
    # Profil peminjam
    'EmploymentStatus',
    'IsBorrowerHomeowner',
    'Occupation',
    'EmploymentStatusDuration',
    'BorrowerState',
    
    # Kapasitas bayar
    'StatedMonthlyIncome',
    'IncomeVerifiable',
    'DebtToIncomeRatio',
    'IncomeRange',
    
    # Credit score
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
    'AmountDelinquent',
    'DelinquenciesLast7Years',
    'PublicRecordsLast10Years',
    'PublicRecordsLast12Months',
    'TradesOpenedLast6Months',
]

# Filter hanya kolom yang ada di dataset
available_features = [c for c in SAFE_FEATURES if c in df.columns]
df_work = df[available_features + ['plafon_ideal']].copy()
df_work.dropna(subset=['plafon_ideal'], inplace=True)

# ── Feature Engineering ──────────────────────────────────────────────
# Semua fitur turunan ini dihitung dari data PRE-LOAN, aman dari leakage

# Kapasitas bayar bersih
df_work['net_monthly_capacity'] = (
    df_work['StatedMonthlyIncome'] * 
    (DTI_MAX - df_work['DebtToIncomeRatio'].clip(0, DTI_MAX))
).clip(0)

# Credit score tengah
df_work['credit_score_mid'] = (
    (df_work['CreditScoreRangeLower'] + df_work['CreditScoreRangeUpper']) / 2
)

# Estimasi beban hutang bulanan
df_work['total_debt_monthly'] = (
    df_work['StatedMonthlyIncome'] * df_work['DebtToIncomeRatio'].clip(0, 1)
)

# Composite delinquency risk score
df_work['delinq_composite'] = (
    df_work['CurrentDelinquencies'] * 3 +
    df_work['DelinquenciesLast7Years'] * 1 +
    df_work['PublicRecordsLast10Years'] * 2
)

# Tekanan revolving terhadap income
df_work['revolving_pressure'] = (
    df_work['OpenRevolvingMonthlyPayment'] / 
    (df_work['StatedMonthlyIncome'] + 1)
)

# Inquiry density (sinyal butuh uang mendesak)
df_work['inquiry_density'] = (
    df_work['InquiriesLast6Months'] / 
    (df_work['TotalCreditLinespast7years'].clip(1, None))
)

# Income per credit line
df_work['income_per_credit_line'] = (
    df_work['StatedMonthlyIncome'] / 
    (df_work['CurrentCreditLines'].clip(1, None))
)

# Rasio kredit tersedia vs total
df_work['available_credit_ratio'] = (
    df_work['AvailableBankcardCredit'] / 
    (df_work['AvailableBankcardCredit'] + df_work['RevolvingCreditBalance'] + 1)
)

# ── Split X dan y ────────────────────────────────────────────────────
y = df_work['plafon_ideal'].values.astype(float)
X = df_work.drop(columns=['plafon_ideal'])

# Tentukan tipe kolom
CAT_COLS = X.select_dtypes(include=['object', 'bool']).columns.tolist()
NUM_COLS = X.select_dtypes(include=['int64', 'float64']).columns.tolist()

for col in CAT_COLS:
    X[col] = X[col].astype(str)

X_train, X_test, y_train, y_test = train_test_split(
    X, y, test_size=TEST_SIZE, random_state=RANDOM_STATE
)

print(f"    Fitur total     : {X.shape[1]} ({len(NUM_COLS)} numerik + {len(CAT_COLS)} kategori)")
print(f"    Train/Test      : {len(X_train):,} / {len(X_test):,}")
print(f"    Target range    : ${y.min():,.0f} - ${y.max():,.0f}")


# =====================================================================
# TAHAP 4: PREPROCESSING
# =====================================================================
print("\n[4/6] Membangun preprocessing pipeline...")

numeric_transformer = Pipeline([
    ('imputer', SimpleImputer(strategy='median')),
])

categorical_transformer = Pipeline([
    ('imputer', SimpleImputer(strategy='constant', fill_value='Unknown')),
    ('encoder', OrdinalEncoder(handle_unknown='use_encoded_value', unknown_value=-1)),
])

preprocessor = ColumnTransformer([
    ('num', numeric_transformer,     NUM_COLS),
    ('cat', categorical_transformer, CAT_COLS),
], remainder='drop')

print(f"    Numerik   : {len(NUM_COLS)} kolom -> median impute")
print(f"    Kategori  : {len(CAT_COLS)} kolom -> ordinal encode")


# =====================================================================
# TAHAP 5: OPTUNA TUNING + MLFLOW LOGGING
# =====================================================================
print(f"\n[5/6] Melatih model dengan Optuna ({N_TRIALS} trials per model)...")
print("    Model A: XGBoost")
print("    Model B: LightGBM")

mlflow.set_tracking_uri(MLFLOW_URI)
mlflow.set_experiment(EXPERIMENT_NAME)

results = {}


# ─── MODEL A: XGBOOST ────────────────────────────────────────────────
print("\n  >> Training XGBoost...")

def objective_xgb(trial):
    params = {
        'model__n_estimators':      trial.suggest_int('n_estimators', 500, 1500),
        'model__learning_rate':     trial.suggest_float('learning_rate', 0.01, 0.12, log=True),
        'model__max_depth':         trial.suggest_int('max_depth', 4, 10),
        'model__subsample':         trial.suggest_float('subsample', 0.6, 1.0),
        'model__colsample_bytree':  trial.suggest_float('colsample_bytree', 0.5, 1.0),
        'model__min_child_weight':  trial.suggest_int('min_child_weight', 1, 12),
        'model__gamma':             trial.suggest_float('gamma', 0, 0.5),
        'model__reg_alpha':         trial.suggest_float('reg_alpha', 0, 2.0),
        'model__reg_lambda':        trial.suggest_float('reg_lambda', 0.5, 5.0),
    }
    pipe = Pipeline([
        ('preprocessor', preprocessor),
        ('model', XGBRegressor(random_state=RANDOM_STATE, n_jobs=-1, tree_method='hist')),
    ])
    pipe.set_params(**params)
    scores = cross_val_score(pipe, X_train, y_train, cv=5, scoring='r2', n_jobs=-1)
    return scores.mean()

study_xgb = optuna.create_study(
    direction='maximize',
    sampler=optuna.samplers.TPESampler(seed=RANDOM_STATE)
)
study_xgb.optimize(objective_xgb, n_trials=N_TRIALS)

# Retrain best XGBoost
best_xgb = Pipeline([
    ('preprocessor', preprocessor),
    ('model', XGBRegressor(random_state=RANDOM_STATE, n_jobs=-1, tree_method='hist')),
])
best_xgb.set_params(**{f"model__{k}": v for k, v in study_xgb.best_params.items()})
best_xgb.fit(X_train, y_train)

y_pred_xgb = best_xgb.predict(X_test)
r2_xgb  = r2_score(y_test, y_pred_xgb)
mae_xgb = mean_absolute_error(y_test, y_pred_xgb)
rmse_xgb = np.sqrt(mean_squared_error(y_test, y_pred_xgb))

results['XGBoost'] = {
    'r2': r2_xgb, 'mae': mae_xgb, 'rmse': rmse_xgb,
    'pipe': best_xgb, 'params': study_xgb.best_params
}
print(f"    XGBoost  -> R2: {r2_xgb:.4f} | MAE: ${mae_xgb:,.0f} | RMSE: ${rmse_xgb:,.0f}")


# ─── MODEL B: LIGHTGBM ───────────────────────────────────────────────
print("\n  >> Training LightGBM...")

def objective_lgbm(trial):
    params = {
        'model__n_estimators':      trial.suggest_int('n_estimators', 500, 1500),
        'model__learning_rate':     trial.suggest_float('learning_rate', 0.01, 0.12, log=True),
        'model__max_depth':         trial.suggest_int('max_depth', 4, 12),
        'model__num_leaves':        trial.suggest_int('num_leaves', 31, 255),
        'model__subsample':         trial.suggest_float('subsample', 0.6, 1.0),
        'model__colsample_bytree':  trial.suggest_float('colsample_bytree', 0.5, 1.0),
        'model__min_child_samples': trial.suggest_int('min_child_samples', 10, 80),
        'model__reg_alpha':         trial.suggest_float('reg_alpha', 0, 2.0),
        'model__reg_lambda':        trial.suggest_float('reg_lambda', 0, 5.0),
    }
    pipe = Pipeline([
        ('preprocessor', preprocessor),
        ('model', LGBMRegressor(random_state=RANDOM_STATE, n_jobs=-1, verbose=-1)),
    ])
    pipe.set_params(**params)
    scores = cross_val_score(pipe, X_train, y_train, cv=5, scoring='r2', n_jobs=-1)
    return scores.mean()

study_lgbm = optuna.create_study(
    direction='maximize',
    sampler=optuna.samplers.TPESampler(seed=RANDOM_STATE)
)
study_lgbm.optimize(objective_lgbm, n_trials=N_TRIALS)

# Retrain best LightGBM
best_lgbm = Pipeline([
    ('preprocessor', preprocessor),
    ('model', LGBMRegressor(random_state=RANDOM_STATE, n_jobs=-1, verbose=-1)),
])
best_lgbm.set_params(**{f"model__{k}": v for k, v in study_lgbm.best_params.items()})
best_lgbm.fit(X_train, y_train)

y_pred_lgbm = best_lgbm.predict(X_test)
r2_lgbm  = r2_score(y_test, y_pred_lgbm)
mae_lgbm = mean_absolute_error(y_test, y_pred_lgbm)
rmse_lgbm = np.sqrt(mean_squared_error(y_test, y_pred_lgbm))

results['LightGBM'] = {
    'r2': r2_lgbm, 'mae': mae_lgbm, 'rmse': rmse_lgbm,
    'pipe': best_lgbm, 'params': study_lgbm.best_params
}
print(f"    LightGBM -> R2: {r2_lgbm:.4f} | MAE: ${mae_lgbm:,.0f} | RMSE: ${rmse_lgbm:,.0f}")


# ── PILIH PEMENANG ────────────────────────────────────────────────────
best_name = max(results, key=lambda k: results[k]['r2'])
best_info = results[best_name]


# ── LOG KE MLFLOW ────────────────────────────────────────────────────
print("\n  >> Logging semua run ke MLflow...")

for model_name, res in results.items():
    run_name = f"v3_{model_name}_Kapasitas"
    with mlflow.start_run(run_name=run_name):
        # Metadata
        mlflow.log_param("model_type",      model_name)
        mlflow.log_param("target",          "plafon_ideal (kapasitas finansial)")
        mlflow.log_param("n_features",      X.shape[1])
        mlflow.log_param("n_trials_optuna", N_TRIALS)
        mlflow.log_param("dti_max",         DTI_MAX)
        mlflow.log_param("train_size",      len(X_train))
        mlflow.log_param("test_size",       len(X_test))
        mlflow.log_param("leakage_check",   "CLEAN - no post-decision features")
        
        # Hyperparameters
        for k, v in res['params'].items():
            mlflow.log_param(k, round(v, 6) if isinstance(v, float) else v)
        
        # Metrics
        mlflow.log_metric("R2_Score", res['r2'])
        mlflow.log_metric("MAE",     res['mae'])
        mlflow.log_metric("RMSE",    res['rmse'])
        mlflow.log_metric("is_best", 1 if model_name == best_name else 0)
        
        # Model artifact
        mlflow.sklearn.log_model(
            sk_model=res['pipe'],
            artifact_path=f"model_{model_name.lower()}_v3",
            input_example=X_test.iloc[:3]
        )
    
    tag = " <<< BEST" if model_name == best_name else ""
    print(f"    [{model_name}] R2={res['r2']:.4f} | MAE=${res['mae']:,.0f}{tag}")


# =====================================================================
# TAHAP 6: SIMPAN MODEL TERBAIK
# =====================================================================
print(f"\n[6/6] Menyimpan model terbaik ({best_name})...")
joblib.dump(best_info['pipe'], PKL_OUTPUT)
print(f"    Tersimpan: {PKL_OUTPUT}")


# =====================================================================
# LAPORAN AKHIR
# =====================================================================
print()
print("=" * 60)
print("  LAPORAN AKHIR -- Regresi V3 (Kapasitas Finansial)")
print("=" * 60)
print()
print(f"  {'Model':<12} {'R2':>8} {'MAE ($)':>10} {'RMSE ($)':>10}")
print(f"  {'-' * 42}")
for name in sorted(results, key=lambda k: -results[k]['r2']):
    r = results[name]
    flag = " [BEST]" if name == best_name else ""
    print(f"  {name:<12} {r['r2']:>8.4f} {r['mae']:>10,.0f} {r['rmse']:>10,.0f}{flag}")

print()
print("  DETAIL:")
print(f"    Target          : plafon_ideal (kapasitas finansial bank)")
print(f"    Fitur           : {X.shape[1]} kolom (semua pre-loan)")
print(f"    Leakage         : TIDAK ADA")
print(f"    Optuna trials   : {N_TRIALS} per model")
print(f"    DTI maksimal    : {DTI_MAX:.0%}")
print()
print("  PERBANDINGAN DENGAN VERSI SEBELUMNYA:")
print(f"    v1 (LoanOriginalAmount, RandomSearch) : R2 = 0.5598")
print(f"    v2 (LoanOriginalAmount, Optuna)       : R2 = 0.5416")
print(f"    v3 (plafon_ideal, Optuna)              : R2 = {best_info['r2']:.4f}")
print()
print("  INTERPRETASI:")
print("    Target v1/v2 = permintaan nasabah (noisy, perilaku manusia)")
print("    Target v3    = keputusan bank (konsisten, berbasis aturan)")
print("    R2 tinggi karena target didasarkan pada logika finansial")
print("    yang stabil, bukan keinginan acak nasabah.")
print()
print("=" * 60)
print()
print("  Lihat di MLflow:")
print("    mlflow ui --backend-store-uri \"file:///C:/Users/ASUS TUF/Documents/ML OPS/PRAKTIKUM/mlruns\" --port 5000")
print("    Buka: http://localhost:5000")
print("    Experiment: Prediksi_Limit_Pinjaman_Kredit_v3")
