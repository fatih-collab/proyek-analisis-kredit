import pandas as pd
import numpy as np
import scipy.stats as stats
import warnings

import mlflow
import mlflow.sklearn

from sklearn.model_selection import train_test_split, RandomizedSearchCV
from sklearn.impute import SimpleImputer
from sklearn.preprocessing import OrdinalEncoder
from sklearn.compose import ColumnTransformer
from sklearn.pipeline import Pipeline
from sklearn.metrics import mean_absolute_error, r2_score
from xgboost import XGBRegressor

warnings.filterwarnings("ignore", category=FutureWarning)
warnings.filterwarnings("ignore", message="Setuptools is replacing distutils")

# =====================================================================
# KONFIGURASI — ubah hanya bagian ini jika perlu
# =====================================================================
CSV_PATH       = "C:/Users/ASUS TUF/Documents/ML OPS/PRAKTIKUM/cleaning_prosperloadata.csv"
EXPERIMENT_NAME = "Prediksi_Limit_Pinjaman_Kredit_v2"
RUN_NAME        = "XGBoost_26Fitur_Bebas_Leakage"
TEST_SIZE       = 0.2
RANDOM_STATE    = 42
N_ITER_TUNING   = 20   # naikkan ke 50 untuk hasil lebih optimal (lebih lama)

# =====================================================================
# DAFTAR FITUR AMAN (tidak ada leakage)
#
# ❌ TIDAK DIPAKAI — MonthlyLoanPayment
#    Dihitung dari rumus PMT(rate/12, term, LoanOriginalAmount).
#    Korelasi dengan target = 0.93, MAE formula vs aktual hanya $1.62.
#    Ini bukan fitur — ini jawaban yang dibocorkan.
#
# ❌ TIDAK DIPAKAI — BorrowerRate
#    Di data historis ditetapkan SETELAH loan disetujui.
#    Inkonsisten dengan inference (rate di inference diturunkan dari tenor).
#
# ✅ SEMUA fitur di bawah tersedia SEBELUM keputusan kredit dibuat.
# =====================================================================
FEATURES = [
    # ── Profil Pinjaman ───────────────────────────────────────────────
    'Term',                             # tenor yang diminta (12/36/60 bln)
    'ListingCategory (numeric)',        # tujuan pinjaman (debt consol, home, dll)

    # ── Skor & Rating Kredit ──────────────────────────────────────────
    'ProsperScore',                     # skor risiko internal Prosper (1–11)
    'ProsperRating (numeric)',          # rating Prosper (0–7), korelasi 0.43

    # ── Profil Peminjam ───────────────────────────────────────────────
    'EmploymentStatus',                 # status pekerjaan
    'IsBorrowerHomeowner',              # kepemilikan rumah
    'Occupation',                       # jenis pekerjaan

    # ── Kapasitas Bayar ───────────────────────────────────────────────
    'StatedMonthlyIncome',              # gaji bulanan yang dinyatakan
    'IncomeVerifiable',                 # apakah penghasilan bisa diverifikasi
    'DebtToIncomeRatio',                # rasio utang/penghasilan

    # ── Skor Kredit Eksternal ─────────────────────────────────────────
    'CreditScoreRangeLower',            # batas bawah credit score
    'CreditScoreRangeUpper',            # batas atas credit score

    # ── Riwayat Kredit ────────────────────────────────────────────────
    'TotalCreditLinespast7years',       # total kredit 7 tahun terakhir
    'OpenCreditLines',                  # kredit aktif saat ini
    'CurrentCreditLines',               # jumlah credit line terbuka
    'TotalTrades',                      # total transaksi kredit
    'TradesNeverDelinquent (percentage)', # % kredit tanpa keterlambatan

    # ── Kartu Kredit ─────────────────────────────────────────────────
    'BankcardUtilization',              # rasio pemakaian limit kartu
    'AvailableBankcardCredit',          # sisa limit kartu kredit
    'RevolvingCreditBalance',           # saldo kredit bergulir
    'OpenRevolvingAccounts',            # akun revolving terbuka
    'OpenRevolvingMonthlyPayment',      # cicilan revolving bulanan

    # ── Risiko & Delinquency ──────────────────────────────────────────
    'InquiriesLast6Months',             # inquiry kredit 6 bln terakhir
    'CurrentDelinquencies',             # keterlambatan saat ini
    'DelinquenciesLast7Years',          # keterlambatan 7 tahun terakhir
    'PublicRecordsLast10Years',         # catatan publik buruk 10 tahun

    # ── Target ───────────────────────────────────────────────────────
    'LoanOriginalAmount'
]

# =====================================================================
# TAHAP 1: LOAD & FEATURE ENGINEERING
# =====================================================================
print("=" * 55)
print(" CREDIT LIMIT PREDICTION — Bebas Leakage")
print("=" * 55)
print("\n[1/4] Memuat dan memproses data historis...")

df = pd.read_csv(CSV_PATH, low_memory=False)
df.dropna(subset=['LoanOriginalAmount'], inplace=True)

df_sub = df[FEATURES].copy()

# Feature engineering: estimasi beban utang bulanan (pre-loan, aman)
df_sub['TotalDebtEstimation'] = (
    df_sub['StatedMonthlyIncome'] * df_sub['DebtToIncomeRatio']
)

# Feature engineering: rentang credit score
df_sub['CreditScoreRange'] = (
    df_sub['CreditScoreRangeUpper'] - df_sub['CreditScoreRangeLower']
)

df_sub['LoanOriginalAmount'] = df_sub['LoanOriginalAmount'].round().astype(int)

X = df_sub.drop(columns=['LoanOriginalAmount'])
y = df_sub['LoanOriginalAmount']

print(f"    Dataset  : {len(df_sub):,} baris | {X.shape[1]} fitur input")
print(f"    Target   : ${y.min():,} – ${y.max():,} (mean ${y.mean():,.0f})")

# Konversi tipe data kategorikal → string (konsisten training & inference)
CATEGORICAL_COLS = X.select_dtypes(include=['object', 'bool']).columns.tolist()
NUMERIC_COLS     = X.select_dtypes(include=['int64', 'float64']).columns.tolist()

for col in CATEGORICAL_COLS:
    X[col] = X[col].astype(str)

X_train, X_test, y_train, y_test = train_test_split(
    X, y, test_size=TEST_SIZE, random_state=RANDOM_STATE
)
print(f"    Train    : {len(X_train):,} | Test: {len(X_test):,}")

# =====================================================================
# TAHAP 2: PIPELINE PREPROCESSING
# =====================================================================
print("\n[2/4] Membangun pipeline preprocessing...")

numeric_transformer = Pipeline(steps=[
    ('imputer', SimpleImputer(strategy='median'))
])

categorical_transformer = Pipeline(steps=[
    ('imputer', SimpleImputer(strategy='constant', fill_value='Unknown')),
    ('encoder', OrdinalEncoder(
        handle_unknown='use_encoded_value',
        unknown_value=-1           # nilai -1 untuk kategori baru saat inference
    ))
])

preprocessor = ColumnTransformer(transformers=[
    ('num', numeric_transformer,     NUMERIC_COLS),
    ('cat', categorical_transformer, CATEGORICAL_COLS)
], remainder='drop')

print(f"    Numerik      : {len(NUMERIC_COLS)} kolom → median impute")
print(f"    Kategorikal  : {len(CATEGORICAL_COLS)} kolom → ordinal encode")
print(f"    Kolom baru (inference) : handle_unknown = -1 (aman)")

# =====================================================================
# TAHAP 3: TRAINING & MLFLOW TRACKING
# =====================================================================
print(f"\n[3/4] Melatih model & logging ke MLflow...")
print(f"    Eksperimen : {EXPERIMENT_NAME}")
print(f"    Tuning     : {N_ITER_TUNING} iterasi × 3-fold CV")

mlflow.set_tracking_uri("file:///C:/Users/ASUS TUF/Documents/ML OPS/PRAKTIKUM/mlruns")
mlflow.set_experiment(EXPERIMENT_NAME)

with mlflow.start_run(run_name=RUN_NAME):

    xgb_pipeline = Pipeline(steps=[
        ('preprocessor', preprocessor),
        ('model', XGBRegressor(random_state=RANDOM_STATE, n_jobs=-1))
    ])

    # Ruang pencarian hyperparameter
    param_distributions = {
        'model__n_estimators':     stats.randint(300, 600),
        'model__learning_rate':    stats.uniform(0.02, 0.08),
        'model__max_depth':        stats.randint(5, 10),
        'model__subsample':        stats.uniform(0.7, 0.3),
        'model__colsample_bytree': stats.uniform(0.6, 0.4),
        'model__min_child_weight': stats.randint(1, 8),
        'model__gamma':            stats.uniform(0.0, 0.3),
    }

    random_search = RandomizedSearchCV(
        estimator=xgb_pipeline,
        param_distributions=param_distributions,
        n_iter=N_ITER_TUNING,
        scoring='r2',
        cv=3,
        verbose=1,
        random_state=RANDOM_STATE,
        n_jobs=-1
    )

    random_search.fit(X_train, y_train)
    best_model = random_search.best_estimator_

    # =================================================================
    # TAHAP 4: EVALUASI & LOGGING
    # =================================================================
    print("\n[4/4] Evaluasi model dan logging artefak MLflow...")

    y_pred_raw = best_model.predict(X_test)
    y_pred     = np.round(y_pred_raw).astype(int)

    r2  = r2_score(y_test, y_pred)
    mae = mean_absolute_error(y_test, y_pred)

    # Log semua hyperparameter terbaik
    for k, v in random_search.best_params_.items():
        mlflow.log_param(k, v)

    # Log metadata eksperimen untuk audit & reproducibility
    mlflow.log_param("n_features",       X.shape[1])
    mlflow.log_param("features_list",    str(list(X.columns)))
    mlflow.log_param("leakage_removed",  "MonthlyLoanPayment, BorrowerRate")
    mlflow.log_param("train_size",       len(X_train))
    mlflow.log_param("test_size",        len(X_test))
    mlflow.log_param("n_iter_tuning",    N_ITER_TUNING)

    # Log metrik performa
    mlflow.log_metric("R2_Score", r2)
    mlflow.log_metric("MAE",      mae)

    # Simpan model ke MLflow artifact store
    mlflow.sklearn.log_model(
        sk_model=best_model,
        artifact_path="xgboost_credit_model",
        input_example=X_test.iloc[:3]
    )

    # Laporan terminal
    print()
    print("=" * 55)
    print("  LAPORAN EVALUASI MODEL (Bebas Leakage)")
    print("=" * 55)
    print(f"  Jumlah Fitur          : {X.shape[1]}")
    print(f"  Akurasi R-Squared     : {r2 * 100:.2f}%")
    print(f"  Rata-rata Meleset MAE : ${mae:,.0f} per nasabah")
    print("-" * 55)
    print("  Best Hyperparameters:")
    for k, v in random_search.best_params_.items():
        label = k.replace("model__", "")
        print(f"    {label:<22} : {v}")
    print("-" * 55)
    print("  ✅ Model & metrik tersimpan ke MLflow.")
    print("  ▶  Jalankan: mlflow ui   untuk melihat dashboard.")
    print("=" * 55)

# =====================================================================
# FUNGSI INFERENCE — menerima data nasabah baru
# =====================================================================
def prediksi_nasabah_baru(model, input_nasabah: dict) -> dict:
    """
    Memprediksi plafon pinjaman untuk nasabah baru.

    Parameters
    ----------
    model : sklearn Pipeline (sudah dilatih di atas)

    input_nasabah : dict — data yang diisi nasabah saat pengajuan:
        Gaji_Bulanan          : float  — gaji bulanan (USD)
        Pekerjaan             : str    — 'Employed'/'Self-employed'/dll
        Jabatan               : str    — jenis pekerjaan (Occupation)
        Punya_Rumah           : bool
        Tujuan_Pinjaman       : int    — kode kategori (1=DebtConsolidation,
                                         2=HomeImprovement, 3=Business, dst)
        Tenor_Bulan           : int    — 12 / 36 / 60
        Hutang_Saat_Ini       : float  — total kewajiban bulanan berjalan
        Sisa_Limit_Kartu      : float  — available bankcard credit
        Inquiry_6Bulan        : int    — inquiry kredit 6 bln terakhir
        Penghasilan_Verifikasi: bool   — apakah penghasilan bisa diverifikasi

    Returns
    -------
    dict berisi:
        plafon          : int   — prediksi limit pinjaman (USD)
        bunga           : float — suku bunga yang ditetapkan bank
        bunga_persen    : str   — tampilan suku bunga
        catatan_risiko  : str   — keterangan profil risiko
    """

    # ── A. LOGIKA BISNIS BANK ─────────────────────────────────────────
    # Suku bunga ditetapkan bank berdasarkan tenor (aturan internal)
    tenor = input_nasabah['Tenor_Bulan']
    if tenor <= 12:
        bunga = 0.08
    elif tenor <= 36:
        bunga = 0.15
    else:
        bunga = 0.22

    gaji        = max(input_nasabah['Gaji_Bulanan'], 1.0)
    hutang      = input_nasabah['Hutang_Saat_Ini']
    sisa_kartu  = input_nasabah['Sisa_Limit_Kartu']
    dti         = hutang / gaji

    # Estimasi profil kredit berdasarkan data yang tersedia
    no_credit = (sisa_kartu == 0 and hutang == 0)

    if no_credit:
        credit_lower   = 700
        credit_upper   = 740
        prosper_score  = 6
        prosper_rating = 4
        riwayat        = 0
        util_kartu     = 0.0
        delinquency    = 0
        catatan_risiko = "Baru / Tidak ada riwayat kredit"
    elif dti > 0.40:
        credit_lower   = 580
        credit_upper   = 620
        prosper_score  = 3
        prosper_rating = 2
        riwayat        = 5
        util_kartu     = 0.9
        delinquency    = 1
        catatan_risiko = "DTI tinggi (>40%) — risiko sedang-tinggi"
    else:
        credit_lower   = 700
        credit_upper   = 740
        prosper_score  = 8
        prosper_rating = 5
        riwayat        = 8
        util_kartu     = 0.3 if sisa_kartu > 0 else 0.7
        delinquency    = 0
        catatan_risiko = "Profil sehat — risiko rendah"

    # ── B. SUSUN DATAFRAME UNTUK MODEL ───────────────────────────────
    # Urutan kolom HARUS sama persis dengan saat training
    data_model = {
        'Term':                              tenor,
        'ListingCategory (numeric)':         input_nasabah.get('Tujuan_Pinjaman', 1),
        'ProsperScore':                      prosper_score,
        'ProsperRating (numeric)':           prosper_rating,
        'EmploymentStatus':                  str(input_nasabah['Pekerjaan']),
        'IsBorrowerHomeowner':               int(input_nasabah['Punya_Rumah']),
        'Occupation':                        str(input_nasabah.get('Jabatan', 'Other')),
        'StatedMonthlyIncome':               gaji,
        'IncomeVerifiable':                  int(input_nasabah.get('Penghasilan_Verifikasi', True)),
        'DebtToIncomeRatio':                 dti,
        'CreditScoreRangeLower':             credit_lower,
        'CreditScoreRangeUpper':             credit_upper,
        'TotalCreditLinespast7years':        riwayat,
        'OpenCreditLines':                   max(riwayat - 2, 0),
        'CurrentCreditLines':                max(riwayat - 3, 0),
        'TotalTrades':                       riwayat,
        'TradesNeverDelinquent (percentage)': 0.95 if delinquency == 0 else 0.70,
        'BankcardUtilization':               util_kartu,
        'AvailableBankcardCredit':           sisa_kartu,
        'RevolvingCreditBalance':            hutang * 0.5,
        'OpenRevolvingAccounts':             1 if sisa_kartu > 0 else 0,
        'OpenRevolvingMonthlyPayment':       hutang * 0.1,
        'InquiriesLast6Months':              input_nasabah.get('Inquiry_6Bulan', 1),
        'CurrentDelinquencies':              delinquency,
        'DelinquenciesLast7Years':           delinquency * 2,
        'PublicRecordsLast10Years':          0,
    }

    df_input = pd.DataFrame([data_model])

    # Feature engineering yang sama dengan training
    df_input['TotalDebtEstimation'] = (
        df_input['StatedMonthlyIncome'] * df_input['DebtToIncomeRatio']
    )
    df_input['CreditScoreRange'] = (
        df_input['CreditScoreRangeUpper'] - df_input['CreditScoreRangeLower']
    )

    # ── C. PREDIKSI ───────────────────────────────────────────────────
    plafon = int(np.round(model.predict(df_input)[0]))

    return {
        'plafon':         plafon,
        'bunga':          bunga,
        'bunga_persen':   f"{bunga * 100:.0f}%",
        'catatan_risiko': catatan_risiko
    }


# =====================================================================
# SIMULASI — contoh 3 tipe nasabah
# =====================================================================
print("\n" + "=" * 55)
print("  SIMULASI PREDIKSI NASABAH BARU")
print("=" * 55)

simulasi = [
    {
        "label": "Nasabah A — Karyawan Tetap, Profil Sehat",
        "data": {
            'Gaji_Bulanan':           5500.0,
            'Pekerjaan':              'Employed',
            'Jabatan':                'Professional',
            'Punya_Rumah':            True,
            'Tujuan_Pinjaman':        1,      # Debt Consolidation
            'Tenor_Bulan':            36,
            'Hutang_Saat_Ini':        1000.0,
            'Sisa_Limit_Kartu':       2500.0,
            'Inquiry_6Bulan':         1,
            'Penghasilan_Verifikasi': True,
        }
    },
    {
        "label": "Nasabah B — Wiraswasta, DTI Tinggi",
        "data": {
            'Gaji_Bulanan':           2000.0,
            'Pekerjaan':              'Self-employed',
            'Jabatan':                'Other',
            'Punya_Rumah':            False,
            'Tujuan_Pinjaman':        3,      # Business
            'Tenor_Bulan':            60,
            'Hutang_Saat_Ini':        1500.0,
            'Sisa_Limit_Kartu':       0.0,
            'Inquiry_6Bulan':         4,
            'Penghasilan_Verifikasi': False,
        }
    },
    {
        "label": "Nasabah C — Peminjam Pertama Kali",
        "data": {
            'Gaji_Bulanan':           3500.0,
            'Pekerjaan':              'Employed',
            'Jabatan':                'Clerical',
            'Punya_Rumah':            False,
            'Tujuan_Pinjaman':        2,      # Home Improvement
            'Tenor_Bulan':            36,
            'Hutang_Saat_Ini':        0.0,
            'Sisa_Limit_Kartu':       0.0,
            'Inquiry_6Bulan':         0,
            'Penghasilan_Verifikasi': True,
        }
    },
]

for item in simulasi:
    hasil = prediksi_nasabah_baru(best_model, item['data'])
    print(f"\n  {item['label']}")
    print(f"    Bunga         : {hasil['bunga_persen']}")
    print(f"    Plafon        : ${hasil['plafon']:,.0f}")
    print(f"    Profil Risiko : {hasil['catatan_risiko']}")

print("\n" + "=" * 55)

import joblib
joblib.dump(best_model, 'best_model_regresi2.pkl')
print('✅ Model regresi tersimpan: best_model_regresi2.pkl')
