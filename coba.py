import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import seaborn as sns

# Untuk Machine Learning
from sklearn.model_selection import train_test_split
from sklearn.impute import SimpleImputer
from sklearn.preprocessing import StandardScaler, OneHotEncoder
from sklearn.compose import ColumnTransformer
from sklearn.pipeline import Pipeline
from sklearn.metrics import mean_absolute_error, r2_score

# Import 10 Model
from sklearn.linear_model import LinearRegression, Ridge, Lasso, ElasticNet
from sklearn.tree import DecisionTreeRegressor
from sklearn.ensemble import RandomForestRegressor, GradientBoostingRegressor, AdaBoostRegressor
from sklearn.neighbors import KNeighborsRegressor
from xgboost import XGBRegressor # pastikan sudah pip install xgboost

# 1. LOAD DATA
# ---------------------------------------------------------
df = pd.read_csv('prosperLoanData.csv')
print("Dimensi awal data:", df.shape)

# 2. SELEKSI FITUR & DROP DATA (Mencegah Data Leakage)
# ---------------------------------------------------------
# Kita hanya mengambil fitur yang diketahui SAAT pengajuan pinjaman
features_to_keep = [
    'Term', 'ProsperScore', 'EmploymentStatus', 'IsBorrowerHomeowner', 
    'CreditScoreRangeLower', 'DebtToIncomeRatio', 'StatedMonthlyIncome', 
    'IncomeRange', 'TotalCreditLinespast7years', 'LoanOriginalAmount'
]
df = df[features_to_keep].copy()

# Hapus baris jika target variable (LoanOriginalAmount) kosong (meski biasanya tidak kosong)
df.dropna(subset=['LoanOriginalAmount'], inplace=True)

# 3. TRANSFORMASI TARGET VARIABLE
# ---------------------------------------------------------
# Sesuai permintaan, membulatkan nominal uang pinjaman ke integer terdekat
df['LoanOriginalAmount'] = df['LoanOriginalAmount'].round().astype(int)

# 4. EDA (EXPLORATORY DATA ANALYSIS) DASAR
# ---------------------------------------------------------
plt.figure(figsize=(8,5))
sns.histplot(df['LoanOriginalAmount'], bins=30, kde=True, color='blue')
plt.title('Distribusi Limit Pinjaman (Target)')
plt.xlabel('Nominal Pinjaman')
plt.ylabel('Frekuensi')
plt.show()

# 5. PEMBAGIAN DATA (Train & Test Split)
# ---------------------------------------------------------
X = df.drop(columns=['LoanOriginalAmount'])
y = df['LoanOriginalAmount'] # Target

# Kita split terlebih dahulu untuk mencegah kebocoran informasi saat imputasi
X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=0.2, random_state=42)

# 6. PIPELINE CLEANING (Imputasi & Transformasi/Encoding)
# ---------------------------------------------------------
# Pisahkan kolom numerik dan kategorik
numeric_features = X.select_dtypes(include=['int64', 'float64']).columns
categorical_features = X.select_dtypes(include=['object', 'bool']).columns

# Pipeline Numerik: Imputasi dengan Median (lebih tahan outlier) lalu scaling
numeric_transformer = Pipeline(steps=[
    ('imputer', SimpleImputer(strategy='median')),
    ('scaler', StandardScaler())
])

# Pipeline Kategorik: Imputasi dengan Modus (most_frequent) lalu One-Hot Encoding
categorical_transformer = Pipeline(steps=[
    ('imputer', SimpleImputer(strategy='most_frequent')),
    ('onehot', OneHotEncoder(handle_unknown='ignore'))
])

# Gabungkan pipeline dengan ColumnTransformer
preprocessor = ColumnTransformer(
    transformers=[
        ('num', numeric_transformer, numeric_features),
        ('cat', categorical_transformer, categorical_features)
    ])

# 7. MENYIAPKAN 10 MODEL UNTUK DIPREDIKSI
# ---------------------------------------------------------
models = {
    "Linear Regression": LinearRegression(),
    "Ridge": Ridge(alpha=1.0),
    "Lasso": Lasso(alpha=0.1),
    "ElasticNet": ElasticNet(alpha=0.1),
    "Decision Tree": DecisionTreeRegressor(max_depth=10, random_state=42),
    "Random Forest": RandomForestRegressor(n_estimators=50, max_depth=10, random_state=42),
    "Gradient Boosting": GradientBoostingRegressor(n_estimators=100, random_state=42),
    "AdaBoost": AdaBoostRegressor(n_estimators=50, random_state=42),
    "K-Neighbors": KNeighborsRegressor(n_neighbors=5),
    "XGBoost": XGBRegressor(n_estimators=100, learning_rate=0.1, random_state=42)
}

# 8. TRAINING DAN EVALUASI 10 MODEL
# ---------------------------------------------------------
print("\n=== Memulai Evaluasi 10 Model ===")
results = {}

for name, model in models.items():
    # Buat pipeline utuh: Preprocessing -> Model
    clf = Pipeline(steps=[('preprocessor', preprocessor),
                          ('model', model)])
    
    # Training Model
    clf.fit(X_train, y_train)
    
    # Prediksi
    y_pred = clf.predict(X_test)
    
    # Transformasi akhir Prediksi (Pastikan hasil prediksi dibulatkan/tidak koma)
    y_pred = np.round(y_pred).astype(int)
    
    # Evaluasi dengan Mean Absolute Error dan R-Squared
    mae = mean_absolute_error(y_test, y_pred)
    r2 = r2_score(y_test, y_pred)
    
    results[name] = {'MAE': mae, 'R2': r2}
    print(f"[{name}] -> MAE: ${mae:.0f} | R2 Score: {r2:.4f}")

# Menampilkan hasil terbaik berdasarkan MAE terkecil
best_model = min(results, key=lambda k: results[k]['MAE'])
print(f"\nModel Terbaik Berdasarkan MAE Terendah: {best_model}")