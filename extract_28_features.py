import os
import pandas as pd
import numpy as np

# List 28 Fitur Murni (Tanpa Rekayasa) yang disepakati
FEATURES_28 = [
    # ── 1. Rencana Pinjaman (2) ──
    'Term',
    'ListingCategory (numeric)',
    
    # ── 2. Profil & Pekerjaan (4) ──
    'EmploymentStatus',
    'EmploymentStatusDuration',
    'Occupation',
    'BorrowerState',
    
    # ── 3. Pendapatan & Kemampuan (4) ──
    'StatedMonthlyIncome',
    'DebtToIncomeRatio',
    'IsBorrowerHomeowner',
    'IncomeVerifiable',
    
    # ── 4. Riwayat & Skor Risiko (6) ──
    'CreditScoreRangeLower',
    'CreditScoreRangeUpper',
    'ProsperScore',
    'ProsperRating (numeric)',
    'ProsperRating (Alpha)',
    'IncomeRange',
    
    # ── 5. Penggunaan Kredit (6) ──
    'CurrentCreditLines',
    'OpenCreditLines',
    'TotalCreditLinespast7years',
    'TotalTrades',
    'OpenRevolvingAccounts',
    'OpenRevolvingMonthlyPayment',
    
    # ── 6. Kartu Kredit & Saldo (4) ──
    'BankcardUtilization',
    'AvailableBankcardCredit',
    'RevolvingCreditBalance',
    'TradesNeverDelinquent (percentage)',
    
    # ── 7. Tunggakan & Inquiry (2) ──
    'CurrentDelinquencies',
    'DelinquenciesLast7Years'
]

# Kolom target (untuk training klasifikasi & regresi)
TARGET_COLS = [
    'LoanStatus',           # Target klasifikasi original
    'LoanOriginalAmount'    # Target regresi original (plafon)
]

ALL_COLS_TO_KEEP = FEATURES_28 + TARGET_COLS

def process_large_dataset(filepath, output_path):
    print(f"Loading large dataset from: {filepath} ...")
    df = pd.read_csv(filepath, low_memory=False)
    
    # Reorientasikan kolom kategori yang ter-one-hot di cleaning_prosperloandata.csv
    reconstructed = False
    
    if 'EmploymentStatus' not in df.columns:
        print("Reconstructing 'EmploymentStatus' from one-hot columns...")
        emp_cols = [c for c in df.columns if c.startswith("EmploymentStatus_") and c != "EmploymentStatusDuration"]
        df['EmploymentStatus'] = "Other"
        for col in emp_cols:
            category = col.replace("EmploymentStatus_", "")
            df.loc[df[col] == 1, 'EmploymentStatus'] = category
        reconstructed = True
            
    if 'IncomeRange' not in df.columns:
        print("Reconstructing 'IncomeRange' from one-hot columns...")
        inc_cols = [c for c in df.columns if c.startswith("IncomeRange_")]
        df['IncomeRange'] = "$25,000-49,999"
        for col in inc_cols:
            category = col.replace("IncomeRange_", "")
            df.loc[df[col] == 1, 'IncomeRange'] = category
        reconstructed = True
            
    if 'ProsperRating (Alpha)' not in df.columns:
        print("Reconstructing 'ProsperRating (Alpha)' from 'ProsperRating (numeric)'...")
        rating_map = {
            1: 'HR', 2: 'E', 3: 'D', 4: 'C', 5: 'B', 6: 'A', 7: 'AA'
        }
        if 'ProsperRating (numeric)' in df.columns:
            df['ProsperRating (Alpha)'] = df['ProsperRating (numeric)'].round().fillna(4).map(rating_map).fillna('C')
        else:
            df['ProsperRating (Alpha)'] = 'C'
        reconstructed = True

    # Filter kolom yang benar-benar ada di data
    cols_to_extract = [c for c in ALL_COLS_TO_KEEP if c in df.columns]
    missing_cols = [c for c in ALL_COLS_TO_KEEP if c not in df.columns]
    
    if missing_cols:
        print(f"Peringatan! Kolom ini tidak ditemukan di dataset source: {missing_cols}")
        
    df_extracted = df[cols_to_extract].copy()
    
    # Simpan ke CSV baru
    df_extracted.to_csv(output_path, index=False)
    print(f"SUKSES: Mengekstrak {len(cols_to_extract)} kolom murni.")
    print(f"File tersimpan di: {output_path} ({len(df_extracted):,} baris)")
    print("-" * 50)

def main():
    # 1. Cek dataset besar (113k baris) di root folder
    large_csv = "cleaning_prosperloandata.csv"
    if os.path.exists(large_csv):
        output_large = "prosperloandata_28_fitur_large.csv"
        process_large_dataset(large_csv, output_large)
    else:
        print(f"[INFO] File {large_csv} tidak ditemukan di root directory.")
        
    # 2. Cek dataset kecil (6.7k baris) di folder parent
    small_csv = "../cleaning_prosperloadata.csv"
    if os.path.exists(small_csv):
        output_small = "prosperloandata_28_fitur_small.csv"
        process_large_dataset(small_csv, output_small)
    else:
        print(f"[INFO] File {small_csv} tidak ditemukan di parent directory.")

if __name__ == "__main__":
    main()
