import pandas as pd
import numpy as np
from sklearn.model_selection import KFold, cross_validate
from sklearn.pipeline import Pipeline
from sklearn.compose import ColumnTransformer
from sklearn.preprocessing import OrdinalEncoder
from sklearn.impute import SimpleImputer
from lightgbm import LGBMRegressor

# Load dataset
dataset_path = "cleaning_prosperloandata.csv"
print(f"Loading large dataset from: {dataset_path} ...")
df = pd.read_csv(dataset_path, low_memory=False)

# ── 1. Reconstruct EmploymentStatus from one-hot columns ──
emp_cols = [c for c in df.columns if c.startswith("EmploymentStatus_") and c != "EmploymentStatusDuration"]
df['EmploymentStatus'] = "Other"
for col in emp_cols:
    category = col.replace("EmploymentStatus_", "")
    df.loc[df[col] == 1, 'EmploymentStatus'] = category

# ── 2. Reconstruct IncomeRange from one-hot columns ──
inc_cols = [c for c in df.columns if c.startswith("IncomeRange_")]
df['IncomeRange'] = "$25,000-49,999"
for col in inc_cols:
    category = col.replace("IncomeRange_", "")
    df.loc[df[col] == 1, 'IncomeRange'] = category

# ── 3. Reconstruct ProsperRating (Alpha) from ProsperRating (numeric) ──
rating_map = {
    1: 'HR', 2: 'E', 3: 'D', 4: 'C', 5: 'B', 6: 'A', 7: 'AA'
}
df['ProsperRating (Alpha)'] = df['ProsperRating (numeric)'].round().fillna(4).map(rating_map).fillna('C')

# ── 4. Map LoanStatus to LoanApprovalStatus ──
def map_loan_status(status):
    if status in ['Completed', 'Current', 'FinalPaymentInProgress']:
        return 1   # ACC
    else:
        return 0   # REJECT

df['LoanApprovalStatus'] = df['LoanStatus'].apply(map_loan_status)

# Convert categorical columns to string
cat_cols_all = ['EmploymentStatus', 'Occupation', 'BorrowerState', 'ProsperRating (Alpha)', 'IncomeRange']
for col in cat_cols_all:
    df[col] = df[col].astype(str)

# Filter only accepted loans for regression
df_reg = df[df['LoanApprovalStatus'] == 1].copy()
y_reg = df_reg['LoanOriginalAmount'].round().astype(int)

# ── 5. Define Feature Sets ───────────────────────────────────────────

# A. 28 Features
cat_cols_28 = ['EmploymentStatus', 'Occupation', 'BorrowerState', 'ProsperRating (Alpha)', 'IncomeRange']
num_cols_28 = [
    'Term', 'ListingCategory (numeric)', 'EmploymentStatusDuration', 'StatedMonthlyIncome',
    'DebtToIncomeRatio', 'IsBorrowerHomeowner', 'IncomeVerifiable', 'CreditScoreRangeLower',
    'CreditScoreRangeUpper', 'ProsperScore', 'ProsperRating (numeric)', 'CurrentCreditLines',
    'OpenCreditLines', 'TotalCreditLinespast7years', 'TotalTrades', 'OpenRevolvingAccounts',
    'OpenRevolvingMonthlyPayment', 'BankcardUtilization', 'AvailableBankcardCredit',
    'RevolvingCreditBalance', 'TradesNeverDelinquent (percentage)', 'CurrentDelinquencies',
    'DelinquenciesLast7Years'
]
features_28 = cat_cols_28 + num_cols_28

# B. 34 Features (28 Features + 6 SLIK OJK Columns)
cat_cols_34 = cat_cols_28
num_cols_34 = num_cols_28 + [
    'InquiriesLast6Months', 'TotalInquiries', 'AmountDelinquent',
    'PublicRecordsLast10Years', 'PublicRecordsLast12Months', 'TradesOpenedLast6Months'
]
features_34 = cat_cols_34 + num_cols_34

# ── 6. Helper function to evaluate feature set ───────────────────────
def evaluate_model(num_cols, cat_cols, X_data, y_data):
    # Preprocessor
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

    # Model
    model = LGBMRegressor(
        boosting_type='gbdt',
        learning_rate=0.05,
        n_estimators=500,
        random_state=42,
        n_jobs=-1,
        verbose=-1
    )

    pipe = Pipeline([
        ('preprocessor', preprocessor),
        ('model',        model)
    ])

    cv = KFold(n_splits=5, shuffle=True, random_state=42)
    scores = cross_validate(
        pipe, X_data, y_data, cv=cv,
        scoring=['r2', 'neg_mean_absolute_error', 'neg_root_mean_squared_error'],
        n_jobs=-1
    )

    r2_mean = np.mean(scores['test_r2'])
    mae_mean = -np.mean(scores['test_neg_mean_absolute_error'])
    rmse_mean = -np.mean(scores['test_neg_root_mean_squared_error'])
    return r2_mean, mae_mean, rmse_mean

# ── 7. Run Evaluations ───────────────────────────────────────────────
print(f"\nRunning evaluations on {len(df_reg):,} rows...")

print("\nEvaluating Model A (28 Features)...")
X_28 = df_reg[features_28].copy()
r2_28, mae_28, rmse_28 = evaluate_model(num_cols_28, cat_cols_28, X_28, y_reg)

print("Evaluating Model B (34 Features - SLIK OJK)...")
X_34 = df_reg[features_34].copy()
r2_34, mae_34, rmse_34 = evaluate_model(num_cols_34, cat_cols_34, X_34, y_reg)

# Print Final Comparison Table
print("\n" + "="*50)
print("             HASIL PERBANDINGAN MODEL")
print("="*50)
print(f"Metrik          | 28 Fitur       | 34 Fitur (SLIK OJK)")
print(f"-"*50)
print(f"R² Score (R2)   | {r2_28:.5f}        | {r2_34:.5f}")
print(f"MAE (Rupiah)    | {mae_28:.2f}     | {mae_34:.2f}")
print(f"RMSE (Rupiah)   | {rmse_28:.2f}     | {rmse_34:.2f}")
print("="*50)
