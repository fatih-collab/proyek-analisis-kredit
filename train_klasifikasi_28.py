import os
import pandas as pd
import numpy as np
import joblib
from sklearn.model_selection import train_test_split
from sklearn.pipeline import Pipeline
from sklearn.compose import ColumnTransformer
from sklearn.preprocessing import OrdinalEncoder
from sklearn.impute import SimpleImputer
from sklearn.metrics import f1_score, classification_report, accuracy_score
from lightgbm import LGBMClassifier

# ── 1. Define 28 Raw Features ────────────────────────────────────────
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

# ── 2. Load Dataset ──────────────────────────────────────────────────
dataset_path = "cleaning_prosperloandata.csv"
print(f"Loading dataset from: {dataset_path} ...")
df = pd.read_csv(dataset_path, low_memory=False)

# Reconstruct categorical string columns if they are one-hot encoded
if 'EmploymentStatus' not in df.columns:
    print("Reconstructing 'EmploymentStatus'...")
    emp_cols = [c for c in df.columns if c.startswith("EmploymentStatus_") and c != "EmploymentStatusDuration"]
    df['EmploymentStatus'] = "Other"
    for col in emp_cols:
        category = col.replace("EmploymentStatus_", "")
        df.loc[df[col] == 1, 'EmploymentStatus'] = category

if 'IncomeRange' not in df.columns:
    print("Reconstructing 'IncomeRange'...")
    inc_cols = [c for c in df.columns if c.startswith("IncomeRange_")]
    df['IncomeRange'] = "$25,000-49,999"
    for col in inc_cols:
        category = col.replace("IncomeRange_", "")
        df.loc[df[col] == 1, 'IncomeRange'] = category

if 'ProsperRating (Alpha)' not in df.columns:
    print("Reconstructing 'ProsperRating (Alpha)'...")
    rating_map = {
        1: 'HR', 2: 'E', 3: 'D', 4: 'C', 5: 'B', 6: 'A', 7: 'AA'
    }
    df['ProsperRating (Alpha)'] = df['ProsperRating (numeric)'].round().fillna(4).map(rating_map).fillna('C')

# Ensure string types for categorical columns
for col in cat_cols:
    df[col] = df[col].astype(str)

# ── 3. Map Target (LoanApprovalStatus) ───────────────────────────────
# 1 = ACC (Lancar), 0 = REJECT (Macet)
def map_loan_status(status):
    if status in ['Completed', 'Current', 'FinalPaymentInProgress']:
        return 1
    else:
        return 0

df['LoanApprovalStatus'] = df['LoanStatus'].apply(map_loan_status)

# ── 4. Split Train & Validation ──────────────────────────────────────
X = df[features_28].copy()
y = df['LoanApprovalStatus'].values

X_train, X_val, y_train, y_val = train_test_split(X, y, test_size=0.2, random_state=42)
print(f"Train size: {len(X_train):,}, Validation size: {len(X_val):,}")

# ── 5. Build Pipeline ────────────────────────────────────────────────
num_tr = Pipeline([
    ('imputer', SimpleImputer(strategy='median'))
])
cat_tr = Pipeline([
    ('imp', SimpleImputer(strategy='most_frequent')),
    ('enc', OrdinalEncoder(handle_unknown='use_encoded_value', unknown_value=-1))
])
preprocessor = ColumnTransformer([
    ('num', num_tr, num_cols),
    ('cat', cat_tr, cat_cols)
], remainder='drop')

pipe_klasifikasi = Pipeline([
    ('preprocessor', preprocessor),
    ('model',        LGBMClassifier(
        boosting_type='gbdt',
        learning_rate=0.05,
        n_estimators=400,
        random_state=42,
        n_jobs=-1,
        verbose=-1
    ))
])

# ── 6. Train Model ───────────────────────────────────────────────────
print("Training classification model (LGBMClassifier) on 28 raw features...")
pipe_klasifikasi.fit(X_train, y_train)

# ── 7. Tune Threshold on Validation Set ──────────────────────────────
print("Optimizing threshold for best F1-Score on validation set...")
y_proba = pipe_klasifikasi.predict_proba(X_val)[:, 1]
best_thresh = 0.5
best_f1 = 0

for th in np.arange(0.3, 0.8, 0.01):
    f1 = f1_score(y_val, y_proba >= th)
    if f1 > best_f1:
        best_f1 = f1
        best_thresh = th

# ── 8. Print Evaluation Metrics ──────────────────────────────────────
y_pred = (y_proba >= best_thresh).astype(int)
print("\n" + "="*50)
print("             EVALUASI MODEL KLASIFIKASI")
print("="*50)
print(f"Optimal Threshold : {best_thresh:.4f}")
print(f"F1-Score          : {best_f1:.4%}")
print(f"Accuracy Score    : {accuracy_score(y_val, y_pred):.4%}")
print("\nClassification Report:")
print(classification_report(y_val, y_pred, target_names=['REJECT', 'ACC']))
print("="*50)

# ── 9. Save Pickled Files ───────────────────────────────────────────
joblib.dump(pipe_klasifikasi, "model_tuned_final.pkl")
joblib.dump(best_thresh, "threshold_tuned.pkl")
print("\nSUCCESS: model_tuned_final.pkl & threshold_tuned.pkl saved successfully!")
