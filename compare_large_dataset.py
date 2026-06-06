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
print("Reconstructing EmploymentStatus...")
df['EmploymentStatus'] = "Other"
for col in emp_cols:
    category = col.replace("EmploymentStatus_", "")
    df.loc[df[col] == 1, 'EmploymentStatus'] = category

# ── 2. Reconstruct IncomeRange from one-hot columns ──
inc_cols = [c for c in df.columns if c.startswith("IncomeRange_")]
print("Reconstructing IncomeRange...")
df['IncomeRange'] = "$25,000-49,999"
for col in inc_cols:
    category = col.replace("IncomeRange_", "")
    df.loc[df[col] == 1, 'IncomeRange'] = category

# ── 3. Reconstruct ProsperRating (Alpha) from ProsperRating (numeric) ──
print("Reconstructing ProsperRating (Alpha)...")
rating_map = {
    1: 'HR', 2: 'E', 3: 'D', 4: 'C', 5: 'B', 6: 'A', 7: 'AA'
}
# Round numeric rating to nearest integer to map to alpha
df['ProsperRating (Alpha)'] = df['ProsperRating (numeric)'].round().fillna(4).map(rating_map).fillna('C')

# ── 4. Map LoanStatus to LoanApprovalStatus ──
def map_loan_status(status):
    if status in ['Completed', 'Current', 'FinalPaymentInProgress']:
        return 1   # ACC
    else:
        return 0   # REJECT

df['LoanApprovalStatus'] = df['LoanStatus'].apply(map_loan_status)

# ── 5. Calculate Derived Features ──
df['revolving_util'] = (
    df['OpenRevolvingMonthlyPayment'] * 12 /
    (df['StatedMonthlyIncome'] * 12 + 1)
).clip(0, 2)

df['income_per_credit_line'] = (
    df['StatedMonthlyIncome'] /
    (df['CurrentCreditLines'] + 1)
)

df['delinq_composite'] = (
    df['CurrentDelinquencies'] * 3 +
    df['DelinquenciesLast7Years'] +
    df['PublicRecordsLast10Years'] * 2
)

# ── 6. Define the agreed 28 features ──
cat_cols = ['EmploymentStatus', 'Occupation', 'BorrowerState', 'ProsperRating (Alpha)']
num_cols = [
    'StatedMonthlyIncome', 'DebtToIncomeRatio', 'EmploymentStatusDuration', 'Term', 
    'ListingCategory (numeric)', 'IsBorrowerHomeowner', 'CreditScoreRangeLower', 
    'ProsperScore', 'ProsperRating (numeric)', 'BankcardUtilization', 
    'AvailableBankcardCredit', 'OpenRevolvingMonthlyPayment', 'RevolvingCreditBalance', 
    'CurrentCreditLines', 'OpenRevolvingAccounts', 'TotalCreditLinespast7years', 
    'CurrentDelinquencies', 'DelinquenciesLast7Years', 'TotalInquiries', 
    'InquiriesLast6Months', 'TradesNeverDelinquent (percentage)',
    'revolving_util', 'income_per_credit_line', 'delinq_composite'
]
features_28 = cat_cols + num_cols

# Convert categorical columns to string
for col in cat_cols:
    df[col] = df[col].astype(str)

# Prepare regression data (only accepted loans)
df_reg = df[df['LoanApprovalStatus'] == 1].copy()
X_reg = df_reg[features_28].copy()
y_reg = df_reg['LoanOriginalAmount'].round().astype(int)

# Preprocessor for regression
num_tr_reg = Pipeline([
    ('imputer', SimpleImputer(strategy='median'))
])
cat_tr = Pipeline([
    ('imp', SimpleImputer(strategy='most_frequent')),
    ('enc', OrdinalEncoder(handle_unknown='use_encoded_value', unknown_value=-1))
])
prep_reg = ColumnTransformer([
    ('num', num_tr_reg, num_cols),
    ('cat', cat_tr, cat_cols)
], remainder='drop')

# Tuned parameters of LGBMRegressor
reg_params = {
    'boosting_type': 'gbdt',
    'colsample_bytree': 0.56867249659062,
    'learning_rate': 0.012269590712657756,
    'max_depth': 12,
    'min_child_samples': 31,
    'n_estimators': 766,
    'n_jobs': -1,
    'num_leaves': 172,
    'random_state': 42,
    'reg_alpha': 1.0271116194457306,
    'reg_lambda': 2.8529985325150196,
    'subsample': 0.7931863100780914,
    'verbose': -1
}

pipe_reg = Pipeline([
    ('preprocessor', prep_reg),
    ('model',        LGBMRegressor(**reg_params))
])

# ── 7. Run Cross-Validation ──
print(f"\nRunning 5-Fold Cross-Validation on {len(X_reg):,} accepted rows...")
cv = KFold(n_splits=5, shuffle=True, random_state=42)
scores = cross_validate(
    pipe_reg, X_reg, y_reg, cv=cv,
    scoring=['r2', 'neg_mean_absolute_error', 'neg_root_mean_squared_error'],
    n_jobs=-1
)

r2_mean = np.mean(scores['test_r2'])
mae_mean = -np.mean(scores['test_neg_mean_absolute_error'])
rmse_mean = -np.mean(scores['test_neg_root_mean_squared_error'])

print("\n=== RESULTS FOR 28 FEATURES ON LARGE DATASET ===")
print(f"Mean R2   : {r2_mean:.4f}")
print(f"Mean MAE  : {mae_mean:.4f}")
print(f"Mean RMSE : {rmse_mean:.4f}")
