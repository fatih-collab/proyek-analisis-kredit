"""
=============================================================
  LOAN LIMIT PREDICTION - MACHINE LEARNING PIPELINE
  Target  : LoanOriginalAmount
  Support : 100.000+ baris data
=============================================================
"""

import pandas as pd
import numpy as np
import warnings
warnings.filterwarnings("ignore")

# ─────────────────────────────────────────────────────────────
# ✏️  KONFIGURASI – SESUAIKAN BAGIAN INI SAJA
# ─────────────────────────────────────────────────────────────
FILE_PATH  = "cleaning_prosperloandata.csv"   # ← ganti path file Anda
FILE_SEP   = ","               # ← "," untuk CSV | "\t" untuk TSV

TARGET     = "LoanOriginalAmount"

# Kolom yang dibuang (leakage / tidak relevan)
DROP_COLS = [
    "MonthlyLoanPayment",
    "PaymentToLoanRatio",
    "IncomePaymentRatio",
    "PercentFunded",
    "InvestmentFromFriendsCount",
    "InvestmentFromFriendsAmount",
    "Investors",
]

# Kolom kategorikal yang perlu di-encode
CAT_COLS = ["LoanStatus"]

TEST_SIZE   = 0.5     # 20% untuk testing
RANDOM_SEED = 42
# ─────────────────────────────────────────────────────────────

# ─────────────────────────────────────────────────────────────
# 1. LIBRARY IMPORTS
# ─────────────────────────────────────────────────────────────
from sklearn.model_selection import train_test_split
from sklearn.preprocessing import StandardScaler, LabelEncoder
from sklearn.metrics import mean_absolute_error, mean_squared_error, r2_score
from sklearn.linear_model import LinearRegression, Ridge, Lasso
from sklearn.ensemble import RandomForestRegressor, GradientBoostingRegressor
from sklearn.tree import DecisionTreeRegressor
from sklearn.neighbors import KNeighborsRegressor
import joblib
import time
import os

try:
    from xgboost import XGBRegressor
    XGBOOST_AVAILABLE = True
except ImportError:
    XGBOOST_AVAILABLE = False
    print("⚠️  XGBoost tidak tersedia, akan dilewati.")

try:
    from lightgbm import LGBMRegressor
    LIGHTGBM_AVAILABLE = True
except ImportError:
    LIGHTGBM_AVAILABLE = False
    print("⚠️  LightGBM tidak tersedia, akan dilewati.")

# ─────────────────────────────────────────────────────────────
# 2. LOAD DATA
# ─────────────────────────────────────────────────────────────
print("=" * 65)
print("  📂  LOADING DATA")
print("=" * 65)

if not os.path.exists(FILE_PATH):
    raise FileNotFoundError(
        f"\n❌ File '{FILE_PATH}' tidak ditemukan!\n"
        f"   Ubah variabel FILE_PATH di bagian KONFIGURASI.\n"
    )

print(f"📄 Membaca: {FILE_PATH}")
t0 = time.time()

# low_memory=False agar dtype kolom konsisten di dataset besar
df = pd.read_csv(FILE_PATH, sep=FILE_SEP, low_memory=False)

print(f"✅ Data dimuat dalam {time.time()-t0:.1f} detik")
print(f"   Baris  : {df.shape[0]:,}")
print(f"   Kolom  : {df.shape[1]:,}")
print(f"\n   Target '{TARGET}':")
print(f"   Min    : ${df[TARGET].min():,.0f}")
print(f"   Max    : ${df[TARGET].max():,.0f}")
print(f"   Mean   : ${df[TARGET].mean():,.0f}")
print(f"   Median : ${df[TARGET].median():,.0f}")

# ─────────────────────────────────────────────────────────────
# 3. PREPROCESSING
# ─────────────────────────────────────────────────────────────
print("\n" + "=" * 65)
print("  🔧  PREPROCESSING DATA")
print("=" * 65)

df_clean = df.drop(columns=DROP_COLS, errors="ignore").copy()

# ── Label encode kolom kategorikal ──────────────────────────
le_dict = {}
for col in CAT_COLS:
    if col in df_clean.columns:
        le = LabelEncoder()
        df_clean[col] = le.fit_transform(df_clean[col].astype(str))
        le_dict[col]  = le
        print(f"   ✔ Encode '{col}': {list(le.classes_[:5])} ...")

# ── Hapus kolom object yang tersisa ──────────────────────────
obj_cols = df_clean.select_dtypes(include="object").columns.tolist()
if obj_cols:
    print(f"   ⚠️  Kolom string dibuang (tambahkan ke CAT_COLS jika perlu): {obj_cols}")
    df_clean.drop(columns=obj_cols, inplace=True)

# ── Isi missing values dengan median ─────────────────────────
missing_before = df_clean.isnull().sum().sum()
for col in df_clean.select_dtypes(include=[np.number]).columns:
    if df_clean[col].isnull().sum() > 0:
        df_clean[col].fillna(df_clean[col].median(), inplace=True)

print(f"   ✔ Missing values diisi : {missing_before:,} → 0")
print(f"   ✔ Jumlah fitur akhir   : {df_clean.shape[1] - 1}")

X = df_clean.drop(columns=[TARGET])
y = df_clean[TARGET]
FEATURE_NAMES = X.columns.tolist()

# Simpan median fitur untuk default prediksi nanti
FEATURE_MEDIANS = X.median().to_dict()

# ─────────────────────────────────────────────────────────────
# 4. TRAIN / TEST SPLIT + SCALING
# ─────────────────────────────────────────────────────────────
X_train, X_test, y_train, y_test = train_test_split(
    X, y, test_size=TEST_SIZE, random_state=RANDOM_SEED
)

scaler = StandardScaler()
X_train_sc = scaler.fit_transform(X_train)
X_test_sc  = scaler.transform(X_test)

print(f"\n   📊 Train : {X_train.shape[0]:,} sampel")
print(f"   📊 Test  : {X_test.shape[0]:,} sampel")

# ─────────────────────────────────────────────────────────────
# 5. DEFINISI MODEL
#    use_scaled = True  → pakai StandardScaler
#    use_scaled = False → data asli (tree-based tidak butuh scaling)
# ─────────────────────────────────────────────────────────────
models = {
    "Linear Regression"   : (LinearRegression(), True),
    "Ridge Regression"    : (Ridge(alpha=1.0), True),
    "Lasso Regression"    : (Lasso(alpha=1.0), True),
    "Decision Tree"       : (DecisionTreeRegressor(max_depth=8, random_state=RANDOM_SEED), False),
    "K-Nearest Neighbors" : (KNeighborsRegressor(n_neighbors=5), True),
    "Random Forest"       : (RandomForestRegressor(
                                n_estimators=200,
                                n_jobs=-1,           # semua CPU core
                                random_state=RANDOM_SEED), False),
    "Gradient Boosting"   : (GradientBoostingRegressor(
                                n_estimators=200,
                                learning_rate=0.05,
                                random_state=RANDOM_SEED), False),
}

if XGBOOST_AVAILABLE:
    models["XGBoost"] = (XGBRegressor(
        n_estimators=300, learning_rate=0.05,
        n_jobs=-1, random_state=RANDOM_SEED, verbosity=0), False)

if LIGHTGBM_AVAILABLE:
    models["LightGBM"] = (LGBMRegressor(
        n_estimators=300, learning_rate=0.05,
        n_jobs=-1, random_state=RANDOM_SEED, verbose=-1), False)

# ─────────────────────────────────────────────────────────────
# 6. TRAINING & EVALUASI
# ─────────────────────────────────────────────────────────────
print("\n" + "=" * 65)
print("  🏋️   MELATIH & MENGEVALUASI MODEL")
print("=" * 65)

results      = []
trained_dict = {}

for name, (model, use_scaled) in models.items():
    Xtr = X_train_sc if use_scaled else X_train.values
    Xte = X_test_sc  if use_scaled else X_test.values

    t_start = time.time()
    model.fit(Xtr, y_train)
    t_train = time.time() - t_start

    preds = model.predict(Xte)
    mae   = mean_absolute_error(y_test, preds)
    rmse  = np.sqrt(mean_squared_error(y_test, preds))
    r2    = r2_score(y_test, preds)
    mape  = np.mean(np.abs((y_test.values - preds) / (y_test.values + 1e-9))) * 100

    results.append({
        "Model"     : name,
        "R²"        : round(r2, 4),
        "MAE"       : round(mae, 0),
        "RMSE"      : round(rmse, 0),
        "MAPE %"    : round(mape, 2),
        "Waktu (s)" : round(t_train, 1),
    })
    trained_dict[name] = (model, use_scaled)

    print(f"\n  📌 {name}  ({t_train:.1f}s)")
    print(f"     R²={r2:.4f}  MAE=${mae:,.0f}  RMSE=${rmse:,.0f}  MAPE={mape:.2f}%")

# ─────────────────────────────────────────────────────────────
# 7. TABEL PERBANDINGAN
# ─────────────────────────────────────────────────────────────
results_df = (pd.DataFrame(results)
              .sort_values("R²", ascending=False)
              .reset_index(drop=True))
results_df.index += 1

print("\n" + "=" * 65)
print("  🏆  PERINGKAT MODEL (berdasarkan R²)")
print("=" * 65)
print(results_df.to_string(
    formatters={
        "MAE"    : lambda x: f"${x:,.0f}",
        "RMSE"   : lambda x: f"${x:,.0f}",
        "R²"     : lambda x: f"{x:.4f}",
        "MAPE %" : lambda x: f"{x:.2f}%",
    }
))

# ─────────────────────────────────────────────────────────────
# 8. PILIH & SIMPAN MODEL TERBAIK
# ─────────────────────────────────────────────────────────────
best_name = results_df.iloc[0]["Model"]
best_model_obj, best_scaled = trained_dict[best_name]

print(f"\n🥇 Model Terbaik : {best_name}")
print(f"   R²            : {results_df.iloc[0]['R²']}")
print(f"   MAE           : ${results_df.iloc[0]['MAE']:,.0f}")

# Re-train dengan SELURUH data untuk deployment
X_all_sc = scaler.fit_transform(X)
best_model_obj.fit(X_all_sc if best_scaled else X.values, y)

joblib.dump(best_model_obj,    "best_model.pkl")
joblib.dump(scaler,            "scaler.pkl")
joblib.dump(FEATURE_NAMES,     "feature_names.pkl")
joblib.dump(le_dict,           "label_encoders.pkl")
joblib.dump(best_scaled,       "best_scaled_flag.pkl")
joblib.dump(best_name,         "best_model_name.pkl")
joblib.dump(FEATURE_MEDIANS,   "feature_medians.pkl")

print("\n💾 File tersimpan:")
for f in ["best_model.pkl","scaler.pkl","feature_names.pkl",
          "label_encoders.pkl","best_scaled_flag.pkl",
          "best_model_name.pkl","feature_medians.pkl"]:
    print(f"   ✔ {f}")

# ─────────────────────────────────────────────────────────────
# 9. FITUR TERPENTING
# ─────────────────────────────────────────────────────────────
print("\n" + "=" * 65)
print("  📊  TOP 15 FITUR TERPENTING")
print("=" * 65)

if hasattr(best_model_obj, "feature_importances_"):
    fi = (pd.Series(best_model_obj.feature_importances_, index=FEATURE_NAMES)
          .sort_values(ascending=False).head(15))
    for i, (feat, imp) in enumerate(fi.items(), 1):
        bar = "█" * int(imp * 300)
        print(f"  {i:>2}. {feat:<42} {imp:.4f}  {bar}")
elif hasattr(best_model_obj, "coef_"):
    coef = (pd.Series(np.abs(best_model_obj.coef_), index=FEATURE_NAMES)
            .sort_values(ascending=False).head(15))
    for i, (feat, val) in enumerate(coef.items(), 1):
        print(f"  {i:>2}. {feat:<42} {val:,.2f}")

# ─────────────────────────────────────────────────────────────
# 10. FUNGSI PREDIKSI
# ─────────────────────────────────────────────────────────────
def predict_loan_limit(input_dict: dict) -> dict:
    """
    Prediksi limit pinjaman dari input pengguna.

    Parameters
    ----------
    input_dict : dict
        Nilai fitur. Fitur yang tidak diberikan diisi median otomatis.

    Returns
    -------
    dict berisi:
        predicted_loan   – nilai prediksi ($)
        model_used       – nama model terbaik
        confidence_range – tuple (batas_bawah, batas_atas) ±15%

    Contoh Penggunaan
    -----------------
    result = predict_loan_limit({
        "Term"                    : 36,
        "BorrowerAPR"             : 0.15,
        "ProsperRating (numeric)" : 5,
        "CreditScoreMid"          : 709.5,
        "StatedMonthlyIncome"     : 5000,
        "DebtToIncomeRatio"       : 0.25,
        "IsBorrowerHomeowner"     : 1,
    })
    print(f"Limit Pinjaman: ${result['predicted_loan']:,.2f}")
    """
    mdl          = joblib.load("best_model.pkl")
    sc           = joblib.load("scaler.pkl")
    feat_names   = joblib.load("feature_names.pkl")
    le_d         = joblib.load("label_encoders.pkl")
    scaled_flag  = joblib.load("best_scaled_flag.pkl")
    mdl_name     = joblib.load("best_model_name.pkl")
    feat_medians = joblib.load("feature_medians.pkl")

    # Encode kategorikal
    for col, le in le_d.items():
        if col in input_dict:
            try:
                input_dict[col] = le.transform([str(input_dict[col])])[0]
            except ValueError:
                input_dict[col] = 0

    # Buat 1 baris – fitur yang tidak diisi → pakai nilai median training
    row     = {f: input_dict.get(f, feat_medians.get(f, 0)) for f in feat_names}
    X_input = pd.DataFrame([row])

    if scaled_flag:
        X_input = sc.transform(X_input)

    pred = float(mdl.predict(X_input)[0])
    pred = max(1000, pred)

    return {
        "predicted_loan"   : round(pred, 2),
        "model_used"       : mdl_name,
        "confidence_range" : (round(pred * 0.85, 2), round(pred * 1.15, 2)),
    }

# ─────────────────────────────────────────────────────────────
# 11. DEMO PREDIKSI
# ─────────────────────────────────────────────────────────────
print("\n" + "=" * 65)
print("  🧪  CONTOH PREDIKSI INTERAKTIF")
print("=" * 65)

profil_list = [
    {
        "label": "Risiko Rendah – Gaji tinggi, credit score bagus",
        "input": {
            "Term": 36, "BorrowerAPR": 0.10, "BorrowerRate": 0.085,
            "ProsperRating (numeric)": 6, "ProsperScore": 9,
            "CreditScoreRangeLower": 780, "CreditScoreRangeUpper": 799,
            "CreditScoreMid": 789.5, "IsBorrowerHomeowner": 1,
            "StatedMonthlyIncome": 10000, "DebtToIncomeRatio": 0.15,
            "BankcardUtilization": 0.20, "AvailableBankcardCredit": 40000,
            "CurrentDelinquencies": 0, "InquiriesLast6Months": 0,
            "EmploymentStatus_Employed": 1, "IncomeRange_$100,000+": 1,
        }
    },
    {
        "label": "Risiko Menengah – Gaji rata-rata, credit score biasa",
        "input": {
            "Term": 36, "BorrowerAPR": 0.18, "BorrowerRate": 0.15,
            "ProsperRating (numeric)": 4, "ProsperScore": 6,
            "CreditScoreRangeLower": 680, "CreditScoreRangeUpper": 699,
            "CreditScoreMid": 689.5, "IsBorrowerHomeowner": 0,
            "StatedMonthlyIncome": 4500, "DebtToIncomeRatio": 0.30,
            "BankcardUtilization": 0.55, "AvailableBankcardCredit": 5000,
            "CurrentDelinquencies": 1, "InquiriesLast6Months": 2,
            "EmploymentStatus_Full-time": 1, "IncomeRange_$50,000-74,999": 1,
        }
    },
    {
        "label": "Risiko Tinggi – Gaji rendah, credit score buruk",
        "input": {
            "Term": 36, "BorrowerAPR": 0.33, "BorrowerRate": 0.30,
            "ProsperRating (numeric)": 1, "ProsperScore": 2,
            "CreditScoreRangeLower": 580, "CreditScoreRangeUpper": 599,
            "CreditScoreMid": 589.5, "IsBorrowerHomeowner": 0,
            "StatedMonthlyIncome": 2000, "DebtToIncomeRatio": 0.60,
            "BankcardUtilization": 0.92, "AvailableBankcardCredit": 200,
            "CurrentDelinquencies": 3, "InquiriesLast6Months": 6,
            "EmploymentStatus_Part-time": 1, "IncomeRange_$1-24,999": 1,
        }
    },
]

for p in profil_list:
    hasil = predict_loan_limit(p["input"])
    lo, hi = hasil["confidence_range"]
    print(f"\n  📋 {p['label']}")
    print(f"     ➡️  Prediksi   : ${hasil['predicted_loan']:>12,.2f}")
    print(f"     🔀 Range ±15% : ${lo:>12,.2f}  –  ${hi:>12,.2f}")
    print(f"     🤖 Model      : {hasil['model_used']}")

print("\n" + "=" * 65)
print("  ✅  SELESAI – Pipeline berhasil dijalankan!")
print("=" * 65)
