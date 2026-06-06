import os
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
from sklearn.model_selection import train_test_split, learning_curve
from sklearn.pipeline import Pipeline
from sklearn.compose import ColumnTransformer
from sklearn.preprocessing import OrdinalEncoder
from sklearn.impute import SimpleImputer
from sklearn.metrics import f1_score, classification_report, accuracy_score, precision_score, recall_score
from lightgbm import LGBMClassifier
import joblib

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
for col in cat_cols:
    if col not in df.columns:
        if col == 'EmploymentStatus':
            print("Reconstructing 'EmploymentStatus'...")
            emp_cols = [c for c in df.columns if c.startswith("EmploymentStatus_") and c != "EmploymentStatusDuration"]
            df['EmploymentStatus'] = "Other"
            for c in emp_cols:
                category = c.replace("EmploymentStatus_", "")
                df.loc[df[c] == 1, 'EmploymentStatus'] = category
        elif col == 'IncomeRange':
            print("Reconstructing 'IncomeRange'...")
            inc_cols = [c for c in df.columns if c.startswith("IncomeRange_")]
            df['IncomeRange'] = "$25,000-49,999"
            for c in inc_cols:
                category = c.replace("IncomeRange_", "")
                df.loc[df[c] == 1, 'IncomeRange'] = category
        elif col == 'ProsperRating (Alpha)':
            print("Reconstructing 'ProsperRating (Alpha)'...")
            rating_map = {1: 'HR', 2: 'E', 3: 'D', 4: 'C', 5: 'B', 6: 'A', 7: 'AA'}
            df['ProsperRating (Alpha)'] = df['ProsperRating (numeric)'].round().fillna(4).map(rating_map).fillna('C')

# Ensure string types for categorical columns
for col in cat_cols:
    df[col] = df[col].astype(str)

# Target Mapping
def map_loan_status(status):
    if status in ['Completed', 'Current', 'FinalPaymentInProgress']:
        return 1
    else:
        return 0

df['LoanApprovalStatus'] = df['LoanStatus'].apply(map_loan_status)

X = df[features_28].copy()
y = df['LoanApprovalStatus'].values

# Split Train & Validation
X_train, X_val, y_train, y_val = train_test_split(X, y, test_size=0.2, random_state=42)
print(f"Train size: {len(X_train):,}, Validation size: {len(X_val):,}")

# Build Pipeline
num_tr = Pipeline([('imputer', SimpleImputer(strategy='median'))])
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

# Train Model
print("Training classification model...")
pipe_klasifikasi.fit(X_train, y_train)

# Load threshold
best_thresh = 0.48
if os.path.exists("threshold_tuned.pkl"):
    best_thresh = joblib.load("threshold_tuned.pkl")
    print(f"Loaded threshold from file: {best_thresh}")
else:
    print(f"Using default threshold: {best_thresh}")

# Evaluate Train vs Val
y_train_proba = pipe_klasifikasi.predict_proba(X_train)[:, 1]
y_train_pred = (y_train_proba >= best_thresh).astype(int)

y_val_proba = pipe_klasifikasi.predict_proba(X_val)[:, 1]
y_val_pred = (y_val_proba >= best_thresh).astype(int)

train_acc = accuracy_score(y_train, y_train_pred)
val_acc = accuracy_score(y_val, y_val_pred)

train_prec = precision_score(y_train, y_train_pred)
val_prec = precision_score(y_val, y_val_pred)

train_rec = recall_score(y_train, y_train_pred)
val_rec = recall_score(y_val, y_val_pred)

train_f1 = f1_score(y_train, y_train_pred)
val_f1 = f1_score(y_val, y_val_pred)

print("\n" + "="*60)
print("             OVERFITTING COMPARISON REPORT")
print("="*60)
print(f"Metric      | Train       | Validation  | Gap (Train - Val)")
print("-"*60)
print(f"Accuracy    | {train_acc:11.4%} | {val_acc:11.4%} | {train_acc - val_acc:+11.4%}")
print(f"Precision   | {train_prec:11.4%} | {val_prec:11.4%} | {train_prec - val_prec:+11.4%}")
print(f"Recall      | {train_rec:11.4%} | {val_rec:11.4%} | {train_rec - val_rec:+11.4%}")
print(f"F1-Score    | {train_f1:11.4%} | {val_f1:11.4%} | {train_f1 - val_f1:+11.4%}")
print("="*60)

# Check feature leakage
print("\nChecking for potential data leakage features:")
print("- Are there target-like features in the input features?")
print(f"- Selected features: {len(features_28)} columns")
for col in features_28:
    # check correlation with target if numeric
    if col in num_cols:
        corr = df[col].corr(df['LoanApprovalStatus'])
        print(f"  * {col:35s}: correlation with target = {corr:+.4f}")
    else:
        print(f"  * {col:35s}: categorical feature")

# Generate Learning Curve
print("\nGenerating Learning Curve (this might take a minute)...")
train_sizes = np.linspace(0.1, 1.0, 5)
train_sizes_abs, train_scores, val_scores = learning_curve(
    pipe_klasifikasi, X_train, y_train,
    train_sizes=train_sizes,
    cv=3,
    scoring='f1',
    n_jobs=-1,
    verbose=0
)

train_mean = np.mean(train_scores, axis=1)
train_std = np.std(train_scores, axis=1)
val_mean = np.mean(val_scores, axis=1)
val_std = np.std(val_scores, axis=1)

plt.figure(figsize=(10, 6))
plt.plot(train_sizes_abs, train_mean, 'o-', color='blue', label='Training F1-score')
plt.fill_between(train_sizes_abs, train_mean - train_std, train_mean + train_std, alpha=0.15, color='blue')
plt.plot(train_sizes_abs, val_mean, 's-', color='green', label='Cross-validation F1-score')
plt.fill_between(train_sizes_abs, val_mean - val_std, val_mean + val_std, alpha=0.15, color='green')

plt.title('Learning Curve (LGBMClassifier - 28 features)')
plt.xlabel('Training Set Size (Number of Samples)')
plt.ylabel('F1-score')
plt.grid(True)
plt.legend(loc='lower right')
plt.tight_layout()

# Save image in workspace
plt.savefig('learning_curve.png', dpi=300)
print("Saved learning_curve.png in workspace.")

# Copy to brain folder for artifact visualization if needed
brain_dir = r"C:\Users\ASUS TUF\.gemini\antigravity\brain\a7cb6bbb-15d8-4d78-ac8b-877d7d3301ed"
if os.path.exists(brain_dir):
    dest_path = os.path.join(brain_dir, 'learning_curve.png')
    plt.savefig(dest_path, dpi=300)
    print(f"Saved copy to artifact directory: {dest_path}")
