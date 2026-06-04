import pandas as pd
import os
import mlflow
import mlflow.xgboost
import mlflow.lightgbm
import mlflow.catboost
from sklearn.model_selection import train_test_split
from sklearn.metrics import accuracy_score, f1_score

# Import Tiga Raja Gradient Boosting
import xgboost as xgb
import lightgbm as lgb
from catboost import CatBoostClassifier

# ==========================================
# 1. LOAD DATA & PREPROCESSING
# ==========================================
# Memuat dataset Prosper Loan dari path Anda
df = pd.read_csv(r"D:\Koding Liburan\Full Dataset\dataset_anjay_mabar\dataset\prosperLoanData.csv")

# Bikin Target (0 = Lancar, 1 = Bermasalah)
df['Target'] = df['LoanStatus'].apply(lambda x: 0 if x in ['Completed', 'Current'] else 1)

# Buang Data Leakage (Bocor Masa Depan) & Kolom Status Asli
kolom_bocor = [
    'LoanCurrentDaysDelinquent', 
    'LoanMonthsSinceOrigination', 
    'AmountDelinquent',
    'CurrentDelinquencies',
    'LoanStatus'
]
df_bersih = df.drop(columns=kolom_bocor, errors='ignore')

# Pisahkan Fitur (X) dan Target (y)
X = df_bersih.drop('Target', axis=1)
y = df_bersih['Target']

# ==========================================
# 🔥 FIX ABSOLUT: DETEKSI SEMUA KOLOM NON-NUMERIK & BERSIHKAN TOTAL
# ==========================================
# Dapatkan semua nama kolom yang bukan merupakan angka murni murni murni
kolom_teks = X.select_dtypes(exclude=['int64', 'float64']).columns.tolist()

# Tambahan: cari kolom object yang tersisa atau bertipe campuran
for col in X.columns:
    if X[col].dtype == 'object' or col in kolom_teks:
        if col not in kolom_teks:
            kolom_teks.append(col)

# Bersihkan nilai kosong di kolom-kolom teks tersebut
for col in kolom_teks:
    # Paksa isi data kosong menggunakan metode fillna bawaan pandas tipe object/string
    X[col] = X[col].astype(str).fillna('Unknown')
    X[col] = X[col].replace(['nan', 'NaN', 'None', 'nan ', ' nan'], 'Unknown')
    # Ubah ke category untuk kebahagiaan XGBoost dan LightGBM
    X[col] = X[col].astype('category')

# Setelah data benar-benar bersih dari NaN, lakukan Split Data
X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=0.2, random_state=42, stratify=y)


# ==========================================
# 2. SETUP MLFLOW TRACKING
# ==========================================
jalur_mlruns = os.path.abspath("mlruns")
mlflow.set_tracking_uri(f"file:///{jalur_mlruns.replace(chr(92), '/')}")

# Set Nama Eksperimen di MLflow
mlflow.set_experiment("PBL_Credit_Scoring_Prosper")


# ==========================================
# 3. TRAINING & LOGGING KE MLFLOW EXPERIMENT & REGISTRY
# ==========================================

# --- MODEL 1: XGBoost ---
print("Training XGBoost...")
with mlflow.start_run(run_name="XGBoost_Model"):
    model_xgb = xgb.XGBClassifier(
        enable_categorical=True, 
        random_state=42, 
        eval_metric='logloss'
    )
    model_xgb.fit(X_train, y_train)
    y_pred_xgb = model_xgb.predict(X_test)
    
    acc = accuracy_score(y_test, y_pred_xgb)
    f1 = f1_score(y_test, y_pred_xgb)
    
    mlflow.log_metric("Accuracy", acc)
    mlflow.log_metric("F1_Score", f1)
    
    mlflow.xgboost.log_model(
        xgb_model=model_xgb, 
        artifact_path="model_xgboost",
        registered_model_name="Model_XGBoost_Prosper"
    )
    print(f"XGBoost Selesai! Accuracy: {acc:.4f}")

# --- MODEL 2: LightGBM ---
print("\nTraining LightGBM...")
with mlflow.start_run(run_name="LightGBM_Model"):
    model_lgb = lgb.LGBMClassifier(random_state=42, categorical_feature='auto')
    model_lgb.fit(X_train, y_train)
    y_pred_lgb = model_lgb.predict(X_test)
    
    acc = accuracy_score(y_test, y_pred_lgb)
    f1 = f1_score(y_test, y_pred_lgb)
    
    mlflow.log_metric("Accuracy", acc)
    mlflow.log_metric("F1_Score", f1)
    
    mlflow.lightgbm.log_model(
        lgb_model=model_lgb, 
        artifact_path="model_lightgbm",
        registered_model_name="Model_LightGBM_Prosper"
    )
    print(f"LightGBM Selesai! Accuracy: {acc:.4f}")

# --- MODEL 3: CatBoost ---
print("\nTraining CatBoost...")
with mlflow.start_run(run_name="CatBoost_Model"):
    # 🔥 AMAN: Duplikasi data khusus CatBoost dan paksa bertipe string primitif (str)
    X_train_cat = X_train.copy()
    X_test_cat = X_test.copy()
    
    for col in kolom_teks:
        X_train_cat[col] = X_train_cat[col].astype(str)
        X_test_cat[col] = X_test_cat[col].astype(str)

    model_cat = CatBoostClassifier(cat_features=kolom_teks, random_state=42, verbose=0)
    
    # 🔥 UTAMA: Memanggil X_train_cat (bukan X_train) agar CatBoost tidak crash
    model_cat.fit(X_train_cat, y_train)
    y_pred_cat = model_cat.predict(X_test_cat)
    
    acc = accuracy_score(y_test, y_pred_cat)
    f1 = f1_score(y_test, y_pred_cat)
    
    mlflow.log_metric("Accuracy", acc)
    mlflow.log_metric("F1_Score", f1)
    
    mlflow.catboost.log_model(
        cb_model=model_cat, 
        artifact_path="model_catboost",
        registered_model_name="Model_CatBoost_Prosper"
    )
    print(f"CatBoost Selesai! Accuracy: {acc:.4f}")

print("\n🎉 SEMUA MODEL BERHASIL DITRAINING & MASUK KE MLFLOW (EXPERIMENT & REGISTRY)!")