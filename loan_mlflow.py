"""
=============================================================
LOAN LIMIT PREDICTION - MULTI-FEATURE MACHINE LEARNING MODEL
=============================================================
Memprediksi LoanOriginalAmount berdasarkan banyak fitur.
Terintegrasi dengan MLflow Tracking untuk pencatatan eksperimen.
=============================================================
"""

import pandas as pd
import numpy as np
import warnings
import time
import os
import matplotlib.pyplot as plt
import seaborn as sns
import joblib

# ── Integrasi MLflow ────────────────────────────────────────
import mlflow
import mlflow.sklearn

warnings.filterwarnings('ignore')

# ── Library utama ──────────────────────────────────────────
from sklearn.model_selection import train_test_split
from sklearn.preprocessing import StandardScaler
from sklearn.metrics import (mean_squared_error, mean_absolute_error, r2_score)
from sklearn.linear_model import LinearRegression, Ridge, Lasso
from sklearn.ensemble import (RandomForestRegressor, GradientBoostingRegressor, ExtraTreesRegressor)
from sklearn.tree import DecisionTreeRegressor
from sklearn.neighbors import KNeighborsRegressor

# ════════════════════════════════════════════════════════════
# SETUP INTI MLFLOW
# ════════════════════════════════════════════════════════════
# Menentukan nama wadah eksperimen di MLflow dashboard
MLFLOW_EXPERIMENT_NAME = "Loan_Limit_Multi_Feature_Exp"
mlflow.set_experiment(MLFLOW_EXPERIMENT_NAME)


# ════════════════════════════════════════════════════════════
# 1. DATA
# ════════════════════════════════════════════════════════════

df = pd.read_csv('cleaning_prosperloandata.csv')

print("=" * 65)
print("  LOAN LIMIT PREDICTION — MULTI-FEATURE ML MODEL (MLflow)")
print("=" * 65)
print(f"\n📊 Dataset: {df.shape[0]} baris, {df.shape[1]} kolom")


# ════════════════════════════════════════════════════════════
# 2. FITUR INPUT & TARGET
# ════════════════════════════════════════════════════════════

FEATURES = [
    'StatedMonthlyIncome',      # Gaji bulanan
    'CreditScoreMid',           # Skor kredit tengah
    'DebtToIncomeRatio',        # Rasio hutang / pendapatan
    'BorrowerAPR',              # Suku bunga tahunan peminjam
    'EmploymentStatusDuration', # Lama bekerja (bulan)
    'BankcardUtilization',      # Utilisasi kartu kredit (0–1)
    'RevolvingCreditBalance',   # Saldo kredit bergulir
    'TotalTrades',              # Total history kredit
    'OpenCreditLines',          # Jalur kredit aktif
    'IsBorrowerHomeowner',      # Pemilik rumah (0/1)
    'Term',                     # Tenor pinjaman (bulan)
    'ProsperScore',             # Skor risiko Prosper
]

TARGET = 'LoanOriginalAmount'   # Limit / jumlah pinjaman

print(f"\n🎯 Target Prediksi     : {TARGET}")
print(f"📥 Fitur Input ({len(FEATURES)}):  {', '.join(FEATURES)}")


# ════════════════════════════════════════════════════════════
# 3. PREPROCESSING
# ════════════════════════════════════════════════════════════

df_model = df[FEATURES + [TARGET]].copy()
df_model.replace([np.inf, -np.inf], np.nan, inplace=True)

# Isi missing value dengan median
for col in df_model.columns:
    if df_model[col].isnull().any():
        df_model[col].fillna(df_model[col].median(), inplace=True)

X = df_model[FEATURES]
y = df_model[TARGET]

print(f"\n✅ Data setelah preprocessing: {X.shape[0]} baris, {X.shape[1]} fitur")


# ════════════════════════════════════════════════════════════
# 4. SPLIT & SCALE
# ════════════════════════════════════════════════════════════

X_train, X_test, y_train, y_test = train_test_split(
    X, y, test_size=0.2, random_state=42
)

scaler = StandardScaler()
X_train_sc = scaler.fit_transform(X_train)
X_test_sc  = scaler.transform(X_test)

print(f"\n🔀 Train: {X_train.shape[0]} | Test: {X_test.shape[0]}")


# ════════════════════════════════════════════════════════════
# 5. TRAIN 7 MODEL & BANDINGKAN DENGAN LOGGING MLFLOW
# ════════════════════════════════════════════════════════════

models = {
    'Linear Regression':         LinearRegression(),
    'Ridge Regression':          Ridge(alpha=1.0),
    'Lasso Regression':          Lasso(alpha=100),
    'Decision Tree':             DecisionTreeRegressor(random_state=42),
    'Random Forest':             RandomForestRegressor(n_estimators=100, random_state=42),
    'Extra Trees':               ExtraTreesRegressor(n_estimators=100, random_state=42),
    'Gradient Boosting':         GradientBoostingRegressor(n_estimators=100, random_state=42),
}

results = []
trained_models = {}

print("\n" + "─" * 65)
print(f"{'Model':<25} {'R²':>8} {'MAE':>10} {'RMSE':>10}")
print("─" * 65)

for name, model in models.items():
    # Mengaktifkan MLflow run context untuk setiap model (Spasi diganti underscore untuk nama run yang clean)
    with mlflow.start_run(run_name=name.replace(" ", "_")):
        
        # 1. Log Parameter Global Eksperimen
        mlflow.log_param("total_features_used", len(FEATURES))
        mlflow.log_param("test_split_size", 0.2)
        mlflow.log_param("random_seed_value", 42)
        
        # 2. Log Hyperparameter Spesifik dari Objek Model Secara Dinamis
        model_params = model.get_params()
        for key in ['alpha', 'n_estimators', 'max_depth']:
            if key in model_params and model_params[key] is not None:
                mlflow.log_param(f"model_{key}", model_params[key])

        # Training & Hitung Durasi Waktu Kerja CPU
        t_start = time.time()
        model.fit(X_train_sc, y_train)
        duration = time.time() - t_start
        
        # Prediksi Eksperimen
        y_pred = model.predict(X_test_sc)

        # Hitung Metrik Evaluasi Performa
        r2   = r2_score(y_test, y_pred)
        mae  = mean_absolute_error(y_test, y_pred)
        rmse = np.sqrt(mean_squared_error(y_test, y_pred))

        results.append({'Model': name, 'R2': r2, 'MAE': mae, 'RMSE': rmse})
        trained_models[name] = model

        # 3. Log Metrik ke MLflow Server
        mlflow.log_metric("R2_Score", r2)
        mlflow.log_metric("MAE", mae)
        mlflow.log_metric("RMSE", rmse)
        mlflow.log_metric("Training_Duration_Seconds", duration)

        # 4. Log Feature Importance Chart sebagai Artifact Grafis (Bila model mendukung)
        if hasattr(model, 'feature_importances_'):
            plt.figure(figsize=(10, 5))
            fi = pd.Series(model.feature_importances_, index=FEATURES).sort_values(ascending=False)
            sns.barplot(x=fi.values, y=fi.index, palette="mako")
            plt.title(f"Feature Importance - {name}")
            plt.tight_layout()
            
            plot_name = f"feat_importance_{name.replace(' ', '_')}.png"
            plt.savefig(plot_name)
            plt.close()
            
            mlflow.log_artifact(plot_name) # Kirim ke berkas penampung MLflow
            if os.path.exists(plot_name):
                os.remove(plot_name) # Hapus berkas dump lokal pelengkap

        # 5. Log Binary Model Langsung ke MLflow Artifact Registry
        mlflow.sklearn.log_model(model, artifact_path="model_package")

        print(f"{name:<25} {r2:>8.4f} {mae:>10.0f} {rmse:>10.0f}")

print("─" * 65)


# ════════════════════════════════════════════════════════════
# 6. MODEL TERBAIK
# ════════════════════════════════════════════════════════════

results_df = pd.DataFrame(results).sort_values('R2', ascending=False)
best_name  = results_df.iloc[0]['Model']
best_model = trained_models[best_name]
best_r2    = results_df.iloc[0]['R2']
best_mae   = results_df.iloc[0]['MAE']
best_rmse  = results_df.iloc[0]['RMSE']

print(f"\n🏆 Model Terbaik : {best_name}")
print(f"   R²            : {best_r2:.4f}  (semakin dekat 1 = semakin baik)")
print(f"   MAE           : Rp {best_mae:,.0f}")
print(f"   RMSE          : Rp {best_rmse:,.0f}")


# ════════════════════════════════════════════════════════════
# 7. FEATURE IMPORTANCE (Lokal Display)
# ════════════════════════════════════════════════════════════

if hasattr(best_model, 'feature_importances_'):
    fi = pd.Series(best_model.feature_importances_, index=FEATURES)
    fi_sorted = fi.sort_values(ascending=False)
    print(f"\n📌 Feature Importance ({best_name}):")
    for feat, imp in fi_sorted.items():
        bar = '█' * int(imp * 50)
        print(f"   {feat:<30} {imp:.4f}  {bar}")


# ════════════════════════════════════════════════════════════
# 8. PREDIKSI BARU — INPUT MANUAL
# ════════════════════════════════════════════════════════════

def predict_loan_limit(
    monthly_income: float, credit_score: float, debt_to_income: float, borrower_apr: float,
    employment_duration: float, bankcard_utilization: float, revolving_balance: float,
    total_trades: float, open_credit_lines: float, is_homeowner: int, term: int, prosper_score: float,
    model=best_model, scaler=scaler
) -> dict:
    inp = np.array([[
        monthly_income, credit_score, debt_to_income, borrower_apr,
        employment_duration, bankcard_utilization, revolving_balance,
        total_trades, open_credit_lines, is_homeowner, term, prosper_score
    ]])
    inp_sc = scaler.transform(inp)
    limit  = float(model.predict(inp_sc)[0])
    limit  = max(1000, round(limit / 500) * 500)   # Bulatkan ke 500 terdekat

    # Kategori risiko sederhana dari debt_to_income & credit_score
    if credit_score >= 750 and debt_to_income < 0.2:
        risk = "🟢 RENDAH"
    elif credit_score >= 680 and debt_to_income < 0.4:
        risk = "🟡 SEDANG"
    else:
        risk = "🔴 TINGGI"

    return {
        'limit_pinjaman':   limit,
        'kategori_risiko':  risk,
        'model_digunakan':  best_name,
        'skor_r2':          best_r2,
    }


# ── Contoh prediksi ────────────────────────────────────────
print("\n" + "=" * 65)
print("  CONTOH PREDIKSI LIMIT PINJAMAN")
print("=" * 65)

examples = [
    {
        "label": "Peminjam A — Gaji Tinggi, Kredit Bagus",
        "monthly_income": 10_000, "credit_score": 780, "debt_to_income": 0.15, "borrower_apr": 0.09,
        "employment_duration": 60, "bankcard_utilization": 0.20, "revolving_balance": 5_000,
        "total_trades": 30, "open_credit_lines": 10, "is_homeowner": 1, "term": 36, "prosper_score": 9,
    },
    {
        "label": "Peminjam B — Gaji Menengah, Kredit Sedang",
        "monthly_income": 4_000, "credit_score": 680, "debt_to_income": 0.30, "borrower_apr": 0.18,
        "employment_duration": 24, "bankcard_utilization": 0.55, "revolving_balance": 8_000,
        "total_trades": 15, "open_credit_lines": 6, "is_homeowner": 0, "term": 36, "prosper_score": 5,
    },
    {
        "label": "Peminjam C — Gaji Rendah, Kredit Buruk",
        "monthly_income": 1_500, "credit_score": 590, "debt_to_income": 0.60, "borrower_apr": 0.32,
        "employment_duration": 6, "bankcard_utilization": 0.90, "revolving_balance": 12_000,
        "total_trades": 8, "open_credit_lines": 3, "is_homeowner": 0, "term": 60, "prosper_score": 2,
    },
]

for ex in examples:
    label = ex.pop('label')
    result = predict_loan_limit(**ex)
    print(f"\n👤 {label}")
    print(f"   Gaji Bulanan        : $ {ex.get('monthly_income', examples[0].get('monthly_income')):,.0f}")
    print(f"   Skor Kredit         : {ex.get('credit_score', examples[0].get('credit_score'))}")
    print(f"   ➤ Limit Pinjaman    : $ {result['limit_pinjaman']:,.0f}")
    print(f"   ➤ Kategori Risiko   : {result['kategori_risiko']}")


# ════════════════════════════════════════════════════════════
# 9. SIMPAN MODEL & SCALER LOKAL
# ════════════════════════════════════════════════════════════

joblib.dump(best_model, 'best_loan_model.pkl')
joblib.dump(scaler,     'loan_scaler.pkl')

print("\n\n💾 Model tersimpan: best_loan_model.pkl | loan_scaler.pkl")
print("💡 Untuk meluncurkan dashboard visualisasi, silakan ketik perintah berikut di terminal:")
print("   mlflow ui")
print("\n" + "=" * 65)