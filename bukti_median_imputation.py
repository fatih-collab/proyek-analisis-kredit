# %% [markdown]
# # Bukti Perhitungan Nilai Median dari Dataset Prosper Marketplace
# 
# **Tujuan:** Membuktikan bahwa nilai default yang digunakan dalam sistem prediksi
# kredit berasal dari **median** dataset training, bukan dari inisialisasi manual.
# 
# **Metode:** Median imputation — teknik standar di machine learning untuk mengisi
# fitur yang tidak tersedia. Median dipilih karena robust terhadap outlier,
# terutama pada data keuangan yang bersifat skewed (miring kanan).

# %%
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import seaborn as sns
import warnings

warnings.filterwarnings('ignore')
pd.set_option('display.max_columns', None)
pd.set_option('display.float_format', lambda x: f'{x:,.4f}')

# Styling
plt.rcParams['figure.figsize'] = (14, 6)
plt.rcParams['font.size'] = 11
sns.set_style("whitegrid")
sns.set_palette("husl")

print("Library berhasil di-import [OK]")

# %% [markdown]
# ## 1. Load Dataset

# %%
# Load dataset Prosper Marketplace
df = pd.read_csv("Dataset/CLEANN_prosperloandata (1).csv", low_memory=False)
print(f"Dataset: CLEANN_prosperloandata (1).csv")
print(f"Jumlah baris : {len(df):,}")
print(f"Jumlah kolom : {len(df.columns)}")
print(f"Memory usage : {df.memory_usage(deep=True).sum() / 1e6:.1f} MB")

# %% [markdown]
# ## 2. Kolom yang Digunakan untuk Median Imputation
# 
# Dari 28 fitur yang dibutuhkan model klasifikasi dan 41 fitur untuk model regresi,
# hanya **8 fitur yang diisi oleh user** melalui form frontend. Sisanya diisi
# menggunakan **median dari dataset training ini**.

# %%
# Kolom-kolom numerik yang median-nya akan digunakan sebagai default
kolom_numerik = [
    "CreditScoreRangeLower",
    "CreditScoreRangeUpper",
    "ProsperScore",
    "ProsperRating (numeric)",
    "BankcardUtilization",
    "AvailableBankcardCredit",
    "OpenRevolvingMonthlyPayment",
    "RevolvingCreditBalance",
    "OpenRevolvingAccounts",
    "CurrentCreditLines",
    "OpenCreditLines",
    "TotalCreditLinespast7years",
    "TotalTrades",
    "TradesNeverDelinquent (percentage)",
    "CurrentDelinquencies",
    "DelinquenciesLast7Years",
    "AmountDelinquent",
    "PublicRecordsLast10Years",
    "PublicRecordsLast12Months",
    "TotalInquiries",
    "InquiriesLast6Months",
    "TradesOpenedLast6Months",
    "EmploymentStatusDuration",
    "StatedMonthlyIncome",
    "DebtToIncomeRatio",
]

# Kolom kategorikal (menggunakan mode / nilai paling sering muncul)
kolom_kategorikal = [
    "ProsperRating (Alpha)",
    "EmploymentStatus",
    "IncomeRange",
    "Occupation",
    "BorrowerState",
    "IsBorrowerHomeowner",
]

print(f"Kolom numerik  : {len(kolom_numerik)}")
print(f"Kolom kategori : {len(kolom_kategorikal)}")
print(f"Total          : {len(kolom_numerik) + len(kolom_kategorikal)} kolom")

# %% [markdown]
# ## 3. Perhitungan Median (Numerik)

# %%
# Hitung median, mean, dan statistik lainnya
stats_list = []
for col in kolom_numerik:
    if col in df.columns:
        series = pd.to_numeric(df[col], errors='coerce').dropna()
        stats_list.append({
            "Kolom": col,
            "Count (non-null)": int(series.count()),
            "MEDIAN": round(series.median(), 4),
            "Mean": round(series.mean(), 4),
            "Selisih (Mean-Median)": round(series.mean() - series.median(), 4),
            "Std Dev": round(series.std(), 4),
            "Min": round(series.min(), 4),
            "Max": round(series.max(), 4),
            "Skewness": round(series.skew(), 4),
        })
    else:
        print(f"  [WARNING] Kolom '{col}' tidak ditemukan di dataset!")

stats_df = pd.DataFrame(stats_list)
print("\n" + "="*100)
print("  TABEL MEDIAN UNTUK SETIAP KOLOM NUMERIK")
print("="*100)
print(stats_df.to_string(index=False))

# %% [markdown]
# ## 4. Perhitungan Mode (Kategorikal)

# %%
# Hitung mode untuk kolom kategorikal
mode_list = []
for col in kolom_kategorikal:
    if col in df.columns:
        series = df[col].dropna()
        mode_val = series.mode().iloc[0] if len(series.mode()) > 0 else "N/A"
        mode_count = (series == mode_val).sum()
        mode_pct = mode_count / len(series) * 100
        mode_list.append({
            "Kolom": col,
            "Count (non-null)": int(series.count()),
            "MODE (Nilai Default)": mode_val,
            "Frekuensi Mode": int(mode_count),
            "Persentase": f"{mode_pct:.1f}%",
        })

mode_df = pd.DataFrame(mode_list)
print("\n" + "="*80)
print("  TABEL MODE UNTUK SETIAP KOLOM KATEGORIKAL")
print("="*80)
print(mode_df.to_string(index=False))

# %% [markdown]
# ## 5. Mengapa Median, Bukan Mean?
# 
# Distribusi data keuangan bersifat **skewed (miring kanan)** — artinya ada
# segelintir nilai ekstrem (outlier) yang menarik mean ke atas. Median lebih
# **robust** terhadap outlier dan lebih merepresentasikan **nasabah tipikal**.
# 
# Visualisasi di bawah membuktikan bahwa sebagian besar kolom bersifat skewed:

# %%
# Visualisasi distribusi: kolom-kolom dengan skewness tertinggi
skewed_cols = stats_df.nlargest(6, "Skewness")["Kolom"].tolist()

fig, axes = plt.subplots(2, 3, figsize=(18, 10))
fig.suptitle("Distribusi Kolom dengan Skewness Tertinggi\n(Garis Merah = MEDIAN, Garis Biru Putus = MEAN)", 
             fontsize=14, fontweight='bold', y=1.02)

for idx, col in enumerate(skewed_cols):
    ax = axes[idx // 3][idx % 3]
    series = pd.to_numeric(df[col], errors='coerce').dropna()
    
    # Hapus outlier ekstrem untuk visualisasi (>99.5 percentile)
    upper = series.quantile(0.995)
    series_clipped = series[series <= upper]
    
    ax.hist(series_clipped, bins=50, color='#5B9BD5', alpha=0.7, edgecolor='white')
    
    median_val = series.median()
    mean_val = series.mean()
    
    ax.axvline(median_val, color='red', linewidth=2, label=f'Median: {median_val:,.2f}')
    ax.axvline(mean_val, color='blue', linewidth=2, linestyle='--', label=f'Mean: {mean_val:,.2f}')
    
    skew_val = series.skew()
    ax.set_title(f"{col}\n(skewness: {skew_val:.2f})", fontsize=10, fontweight='bold')
    ax.legend(fontsize=8)
    ax.set_ylabel("Frekuensi")

plt.tight_layout()
plt.savefig("bukti_median_vs_mean_distribusi.png", dpi=150, bbox_inches='tight')
plt.show()
print("\n[OK] Grafik disimpan: bukti_median_vs_mean_distribusi.png")

# %% [markdown]
# ## 6. Bukti Konkret: Mean vs Median pada Kolom Kritis

# %%
# Tabel perbandingan Mean vs Median untuk kolom yang paling skewed
print("\n" + "="*90)
print("  PERBANDINGAN MEAN vs MEDIAN — KOLOM DENGAN SKEWNESS TINGGI")
print("="*90)
print(f"\n  {'Kolom':<40} {'Median':>12} {'Mean':>12} {'Skewness':>10} {'Pilihan':>10}")
print("  " + "-"*86)

for _, row in stats_df.iterrows():
    skew = abs(row['Skewness'])
    pilihan = "MEDIAN [OK]" if skew > 0.5 else "~sama"
    marker = " [!]" if skew > 2.0 else ""
    print(f"  {row['Kolom']:<40} {row['MEDIAN']:>12.4f} {row['Mean']:>12.4f} {row['Skewness']:>10.2f} {pilihan:>10}{marker}")

print(f"\n  Catatan: [!] = skewness > 2.0 (sangat miring, mean sangat tidak representatif)")
print(f"  Kesimpulan: Median adalah pilihan yang tepat untuk data keuangan yang skewed.")

# %% [markdown]
# ## 7. Tabel Final: Nilai Default yang Digunakan di Sistem

# %%
# Rangkuman final — ini adalah nilai yang digunakan di backend/predictor.py
print("\n" + "="*90)
print("  NILAI DEFAULT FINAL (DIGUNAKAN DI PREDICTOR.PY)")
print("="*90)

print(f"\n  === NUMERIK (MEDIAN) ===")
print(f"  {'Kolom':<45} {'Nilai Default':>15}")
print("  " + "-"*62)
for _, row in stats_df.iterrows():
    val = row['MEDIAN']
    if val == int(val):
        print(f"  {row['Kolom']:<45} {int(val):>15,}")
    else:
        print(f"  {row['Kolom']:<45} {val:>15,.4f}")

print(f"\n  === KATEGORIKAL (MODE) ===")
print(f"  {'Kolom':<45} {'Nilai Default':>15}")
print("  " + "-"*62)
for _, row in mode_df.iterrows():
    print(f"  {row['Kolom']:<45} {str(row['MODE (Nilai Default)']):>15}")

# %% [markdown]
# ## 8. Validasi: Kolom Delinquency (Median = 0 adalah Benar)
# 
# Salah satu pertanyaan penting: mengapa median `CurrentDelinquencies` = 0?
# Karena **mayoritas nasabah tidak memiliki tunggakan.**

# %%
# Distribusi CurrentDelinquencies
fig, axes = plt.subplots(1, 2, figsize=(14, 5))

# CurrentDelinquencies
col = "CurrentDelinquencies"
series = pd.to_numeric(df[col], errors='coerce').dropna()
val_counts = series.value_counts().sort_index().head(10)

axes[0].bar(val_counts.index.astype(str), val_counts.values, color='#ED7D31', alpha=0.8)
axes[0].set_title(f"Distribusi {col}\n(Median={series.median():.0f}, Mean={series.mean():.2f})", fontweight='bold')
axes[0].set_xlabel("Jumlah Tunggakan")
axes[0].set_ylabel("Jumlah Nasabah")
pct_zero = (series == 0).sum() / len(series) * 100
axes[0].annotate(f'{pct_zero:.1f}% nasabah\npunya 0 tunggakan', 
                xy=(0, val_counts.iloc[0]), fontsize=10, fontweight='bold',
                ha='center', va='bottom', color='red')

# DelinquenciesLast7Years
col2 = "DelinquenciesLast7Years"
series2 = pd.to_numeric(df[col2], errors='coerce').dropna()
val_counts2 = series2.value_counts().sort_index().head(10)

axes[1].bar(val_counts2.index.astype(str), val_counts2.values, color='#70AD47', alpha=0.8)
axes[1].set_title(f"Distribusi {col2}\n(Median={series2.median():.0f}, Mean={series2.mean():.2f})", fontweight='bold')
axes[1].set_xlabel("Jumlah Tunggakan (7 Tahun)")
axes[1].set_ylabel("Jumlah Nasabah")
pct_zero2 = (series2 == 0).sum() / len(series2) * 100
axes[1].annotate(f'{pct_zero2:.1f}% nasabah\npunya 0 tunggakan', 
                xy=(0, val_counts2.iloc[0]), fontsize=10, fontweight='bold',
                ha='center', va='bottom', color='red')

plt.tight_layout()
plt.savefig("bukti_median_delinquency.png", dpi=150, bbox_inches='tight')
plt.show()
print("\n[OK] Grafik disimpan: bukti_median_delinquency.png")

# %% [markdown]
# ## Kesimpulan
# 
# 1. **Semua nilai default** yang digunakan di `predictor.py` berasal dari **median**
#    dataset training `prosperLoanData.csv` — **bukan inisialisasi manual**.
# 
# 2. **Median dipilih** karena data keuangan bersifat **skewed** (miring kanan).
#    Mean ditarik oleh outlier sehingga tidak merepresentasikan nasabah tipikal.
# 
# 3. Untuk kolom kategorikal, digunakan **mode** (nilai yang paling sering muncul).
# 
# 4. **Teknik ini disebut Median Imputation** — standar di dunia machine learning
#    untuk mengisi fitur yang tidak tersedia dari input user.
