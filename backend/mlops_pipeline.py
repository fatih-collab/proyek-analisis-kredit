import os
import time
import joblib
import numpy as np
import pandas as pd
from datetime import datetime
from sqlalchemy.orm import Session

from sklearn.pipeline import Pipeline
from sklearn.compose import ColumnTransformer
from sklearn.preprocessing import OrdinalEncoder
from sklearn.impute import SimpleImputer
from sklearn.metrics import accuracy_score, f1_score, mean_squared_error
from lightgbm import LGBMClassifier, LGBMRegressor

from database import LoanApplication, ModelMetric
import predictor

# Definisikan kolom-kolom persis seperti di notebook
cat_cols = ['EmploymentStatus', 'Occupation', 'BorrowerState', 'ProsperRating (Alpha)', 'IncomeRange']
num_cols = [
    'Term', 'ListingCategory (numeric)', 'EmploymentStatusDuration', 'StatedMonthlyIncome',
    'DebtToIncomeRatio', 'IsBorrowerHomeowner', 'IncomeVerifiable', 'CreditScoreRangeLower',
    'CreditScoreRangeUpper', 'ProsperScore', 'ProsperRating (numeric)', 'CurrentCreditLines',
    'OpenCreditLines', 'TotalCreditLinespast7years', 'TotalTrades', 'OpenRevolvingAccounts',
    'OpenRevolvingMonthlyPayment', 'BankcardUtilization', 'AvailableBankcardCredit',
    'RevolvingCreditBalance', 'TradesNeverDelinquent (percentage)', 'CurrentDelinquencies',
    'DelinquenciesLast7Years'
]
features_28 = cat_cols + num_cols

def extract_features_from_input(input_data: dict, medians: dict) -> dict:
    """Ekstrak 28 fitur Prosper dari input_data yang disimpan di database."""
    # Mapping mirip di predictor.py
    gaji = max(0.0, float(input_data.get("monthlyIncome") or "0"))
    tambahan = max(0.0, float(input_data.get("additionalIncome") or "0"))
    cicilan_aktif = max(0.0, float(input_data.get("existingInstallments") or "0"))
    total_income = gaji + tambahan
    dti = (cicilan_aktif / total_income) if total_income > 0 else 0.0
    dti = min(dti, 10.0)

    employment = predictor.EMPLOYMENT_MAP.get(input_data.get("employment"), "Other")
    occupation = predictor.OCCUPATION_MAP.get(input_data.get("employment"), "Other")
    age = max(18, int(input_data.get("age") or "25"))
    lama_kerja = max(0.0, float((age - 20) * 12))
    nominal = max(0.0, float(input_data.get("loanAmount") or "0"))
    tenor = int(input_data.get("loanTerm") or "36")
    tujuan = predictor.LOAN_PURPOSE_MAP.get(input_data.get("loanPurpose"), 7)
    punya_rumah = (input_data.get("propertyArea") == "Urban")
    borrower_state = predictor.AREA_STATE_MAP.get(input_data.get("propertyArea"), "CA")

    if gaji < 1667:
        income_range = "$1-24,999"
    elif gaji < 4167:
        income_range = "$25,000-49,999"
    elif gaji < 8333:
        income_range = "$50,000-74,999"
    else:
        income_range = "$75,000-99,999"

    return {
        "EmploymentStatus": employment,
        "Occupation": occupation,
        "BorrowerState": borrower_state,
        "ProsperRating (Alpha)": medians.get("ProsperRating (Alpha)", "C"),
        "IncomeRange": income_range,
        "Term": tenor,
        "ListingCategory (numeric)": tujuan,
        "EmploymentStatusDuration": lama_kerja,
        "StatedMonthlyIncome": gaji,
        "DebtToIncomeRatio": round(dti, 4),
        "IsBorrowerHomeowner": int(punya_rumah),
        "IncomeVerifiable": int(medians.get("IncomeVerifiable", 1.0)),
        "CreditScoreRangeLower": medians.get("CreditScoreRangeLower", 680.0),
        "CreditScoreRangeUpper": medians.get("CreditScoreRangeUpper", 699.0),
        "ProsperScore": medians.get("ProsperScore", 6.0),
        "ProsperRating (numeric)": medians.get("ProsperRating (numeric)", 4.0),
        "CurrentCreditLines": medians.get("CurrentCreditLines", 10.0),
        "OpenCreditLines": medians.get("OpenCreditLines", 9.0),
        "TotalCreditLinespast7years": medians.get("TotalCreditLinespast7years", 26.0),
        "TotalTrades": medians.get("TotalTrades", 26.0),
        "OpenRevolvingAccounts": medians.get("OpenRevolvingAccounts", 7.0),
        "OpenRevolvingMonthlyPayment": medians.get("OpenRevolvingMonthlyPayment", 300.0),
        "BankcardUtilization": medians.get("BankcardUtilization", 0.48),
        "AvailableBankcardCredit": medians.get("AvailableBankcardCredit", 8000.0),
        "RevolvingCreditBalance": medians.get("RevolvingCreditBalance", 7000.0),
        "TradesNeverDelinquent (percentage)": medians.get("TradesNeverDelinquent (percentage)", 0.87),
        "CurrentDelinquencies": medians.get("CurrentDelinquencies", 0.0),
        "DelinquenciesLast7Years": medians.get("DelinquenciesLast7Years", 0.0),
        # Info tambahan untuk target regresi
        "_nominal_pengajuan": nominal
    }

def retrain_models(db: Session, predictor_instance=None):
    """
    Menarik data dari Supabase DB, menggabungkan dengan base dataset CSV,
    melatih ulang model Klasifikasi & Regresi, memperbarui file .pkl,
    serta menyimpan metrik evaluasi ke tabel model_metrics.
    """
    print("[MLOps] Memulai proses training ulang model...")
    t_start = time.time()

    # 1. Load Base Dataset
    csv_path = predictor.DATASET_CSV
    if not os.path.exists(csv_path):
        print(f"[MLOps] [ERROR] Base dataset CSV tidak ditemukan di: {csv_path}")
        return False

    print(f"[MLOps] Membaca base dataset: {csv_path}")
    df_base = pd.read_csv(csv_path, low_memory=False)

    # Bersihkan "Not displayed" di IncomeRange jika ada
    if "IncomeRange" in df_base.columns:
        df_base["IncomeRange"] = df_base["IncomeRange"].replace("Not displayed", "$25,000-49,999")

    # Pastikan target klasifikasi di base dataset terdefinisi
    if "LoanApprovalStatus" not in df_base.columns:
        # Jika belum ada, map dari LoanStatus
        df_base['LoanApprovalStatus'] = df_base['LoanStatus'].apply(
            lambda x: 1 if x in ['Completed', 'Current', 'FinalPaymentInProgress'] else 0
        )
    
    # Target regresi di base dataset adalah LoanOriginalAmount
    if "LoanOriginalAmount" not in df_base.columns and "LoanAmount" in df_base.columns:
        df_base["LoanOriginalAmount"] = df_base["LoanAmount"]

    # Ambil median defaults dari predictor instance atau default
    medians = predictor_instance.medians if predictor_instance else predictor.DEFAULT_MEDIANS

    # 2. Ambil data dari database loan_applications
    db_apps = db.query(LoanApplication).all()
    print(f"[MLOps] Menarik {len(db_apps)} data pengajuan dari database.")

    db_rows = []
    for app in db_apps:
        if not app.input_data:
            continue
        try:
            # Ekstrak fitur
            feats = extract_features_from_input(app.input_data, medians)
            
            # Tentukan label target Klasifikasi
            if app.actual_status:
                is_accept = 1 if app.actual_status in ['Completed', 'Current', 'FinalPaymentInProgress'] else 0
            else:
                is_accept = 1 if app.result == "LAYAK" else 0
            
            feats["LoanApprovalStatus"] = is_accept
            
            # Tentukan target Regresi (hanya jika LAYAK / ACC)
            # Gunakan nominal pengajuan dari user sebagai proxy target
            feats["LoanOriginalAmount"] = feats["_nominal_pengajuan"]
            
            db_rows.append(feats)
        except Exception as e:
            print(f"[MLOps] [WARN] Gagal memproses pengajuan {app.id}: {e}")

    # 3. Gabungkan base dataset dengan data database jika ada
    if db_rows:
        df_db = pd.DataFrame(db_rows)
        # Drop helper column
        if "_nominal_pengajuan" in df_db.columns:
            df_db = df_db.drop(columns=["_nominal_pengajuan"])
        
        # Gabungkan
        df_all = pd.concat([df_base, df_db], ignore_index=True)
        print(f"[MLOps] Data digabungkan. Total baris baru: {len(df_all):,} (Base: {len(df_base):,}, DB: {len(df_db):,})")
    else:
        df_all = df_base
        print(f"[MLOps] Tidak ada data DB valid. Menggunakan base dataset saja ({len(df_all):,} baris).")

    # 4. TRAINING ULANG KLASIFIKASI
    print("[MLOps] Melatih kembali model KLASIFIKASI...")
    X_clf = df_all[features_28]
    y_clf = df_all['LoanApprovalStatus'].fillna(0).astype(int).values

    # Preprocessor pipeline
    preprocessor_clf = ColumnTransformer([
        ('num', Pipeline([('imputer', SimpleImputer(strategy='median'))]), num_cols),
        ('cat', Pipeline([('imp', SimpleImputer(strategy='most_frequent')), 
                          ('enc', OrdinalEncoder(handle_unknown='use_encoded_value', unknown_value=-1))]), cat_cols)
    ], remainder='drop')

    pipe_klasifikasi = Pipeline([
        ('preprocessor', preprocessor_clf),
        ('model', LGBMClassifier(random_state=42, n_jobs=-1, verbose=-1))
    ])

    pipe_klasifikasi.fit(X_clf, y_clf)

    # Evaluasi metrik klasifikasi (on training data for logging)
    y_proba = pipe_klasifikasi.predict_proba(X_clf)[:, 1]
    
    # Cari optimal threshold (sederhana)
    best_thresh, best_f1 = 0.5, 0.0
    for th in np.arange(0.3, 0.8, 0.05):
        y_pred_th = (y_proba >= th).astype(int)
        f1 = f1_score(y_clf, y_pred_th)
        if f1 > best_f1:
            best_f1 = f1
            best_thresh = th
            
    best_thresh = float(best_thresh)
    y_pred_final = (y_proba >= best_thresh).astype(int)
    acc_clf = float(accuracy_score(y_clf, y_pred_final))
    f1_clf = float(f1_score(y_clf, y_pred_final))

    # 5. TRAINING ULANG REGRESI
    print("[MLOps] Melatih kembali model REGRESI...")
    # Regresi hanya dilatih menggunakan data yang berstatus LAYAK (LoanApprovalStatus = 1)
    df_reg_all = df_all[df_all['LoanApprovalStatus'] == 1].copy()
    
    if len(df_reg_all) < 10:
        # Fallback jika data ACC terlalu sedikit
        df_reg_all = df_all.copy()

    X_reg = df_reg_all[features_28]
    y_reg = df_reg_all['LoanOriginalAmount'].fillna(df_all['LoanOriginalAmount'].median()).values

    preprocessor_reg = ColumnTransformer([
        ('num', Pipeline([('imputer', SimpleImputer(strategy='median'))]), num_cols),
        ('cat', Pipeline([('imp', SimpleImputer(strategy='most_frequent')), 
                          ('enc', OrdinalEncoder(handle_unknown='use_encoded_value', unknown_value=-1))]), cat_cols)
    ], remainder='drop')

    pipe_regresi = Pipeline([
        ('preprocessor', preprocessor_reg),
        ('model', LGBMRegressor(random_state=42, n_jobs=-1, verbose=-1))
    ])

    pipe_regresi.fit(X_reg, y_reg)

    # Evaluasi metrik regresi
    y_pred_reg = pipe_regresi.predict(X_reg)
    rmse_reg = float(np.sqrt(mean_squared_error(y_reg, y_pred_reg)))

    # 6. SIMPAN ARTIFAK KE FILE DISK
    print("[MLOps] Menyimpan file model .pkl baru ke disk...")
    try:
        # Tentukan output path (menimpa path yang dicari predictor)
        os.makedirs(os.path.dirname(predictor.MODEL_KLAS), exist_ok=True)
        joblib.dump(pipe_klasifikasi, predictor.MODEL_KLAS)
        joblib.dump(best_thresh, predictor.MODEL_THR)
        joblib.dump(pipe_regresi, predictor.MODEL_REG)
        print("[MLOps] File model berhasil disimpan dan di-overwrite!")
    except Exception as e:
        print(f"[MLOps] [ERROR] Gagal menyimpan model ke disk: {e}")
        return False

    # 7. SIMPAN METRIK KE DATABASE
    try:
        # Log metrik klasifikasi
        metric_clf = ModelMetric(
            training_date=datetime.utcnow(),
            model_type="Klasifikasi",
            accuracy=acc_clf,
            f1_score=f1_clf,
            dataset_size=len(df_all)
        )
        db.add(metric_clf)

        # Log metrik regresi
        metric_reg = ModelMetric(
            training_date=datetime.utcnow(),
            model_type="Regresi",
            rmse=rmse_reg,
            dataset_size=len(df_reg_all)
        )
        db.add(metric_reg)
        
        db.commit()
        print("[MLOps] Metrik evaluasi model berhasil dicatat di database.")
    except Exception as e:
        db.rollback()
        print(f"[MLOps] [WARN] Gagal mencatat metrik ke database: {e}")

    # 8. RELOAD MODEL DI MEMORI
    if predictor_instance:
        try:
            predictor_instance.reload_models()
            print("[MLOps] Model baru berhasil di-reload ke memori backend!")
        except Exception as e:
            print(f"[MLOps] [ERROR] Gagal reload model di memori: {e}")

    duration = time.time() - t_start
    print(f"[MLOps] Training ulang selesai sukses dalam {duration:.2f} detik.")
    return True
