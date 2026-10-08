import os
import pandas as pd

backend_dir = os.path.dirname(os.path.abspath(__file__))
BASE_DIR = os.path.dirname(backend_dir)

# File yang akan dibersihkan
targets = [
    os.path.join(BASE_DIR, "Dataset", "prosperloandata_28_fitur_large.csv"),
    os.path.join(BASE_DIR, "prosperloandata_28_fitur_small.csv")
]

print("=== MEMULAI PEMBERSIHAN DATASET LOKAL ===")

for filepath in targets:
    if os.path.exists(filepath):
        print(f"\n[INFO] Membaca file: {filepath}")
        df = pd.read_csv(filepath, low_memory=False)
        
        if "IncomeRange" in df.columns:
            # Ganti "Not displayed" ke "$25,000-49,999"
            count_not_displayed = (df["IncomeRange"] == "Not displayed").sum()
            if count_not_displayed > 0:
                print(f"[OK] Menemukan {count_not_displayed:,} baris 'Not displayed'. Mengganti ke '$25,000-49,999'...")
                df["IncomeRange"] = df["IncomeRange"].replace("Not displayed", "$25,000-49,999")
            
            # Ganti "Not employed" ke "$25,000-49,999"
            count_not_employed = (df["IncomeRange"] == "Not employed").sum()
            if count_not_employed > 0:
                print(f"[OK] Menemukan {count_not_employed:,} baris 'Not employed'. Mengganti ke '$25,000-49,999'...")
                df["IncomeRange"] = df["IncomeRange"].replace("Not employed", "$25,000-49,999")
                
            if count_not_displayed > 0 or count_not_employed > 0:
                # Simpan kembali
                df.to_csv(filepath, index=False)
                print(f"[OK] File berhasil disimpan kembali.")
            else:
                print("[INFO] Tidak ditemukan baris 'Not displayed' atau 'Not employed' di file ini.")
        else:
            print("[WARN] Kolom 'IncomeRange' tidak ditemukan.")
    else:
        print(f"[WARN] File tidak ditemukan: {filepath}")

print("\n=== PEMBERSIHAN SELESAI ===")
