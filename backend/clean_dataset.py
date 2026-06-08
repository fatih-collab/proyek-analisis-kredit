import os
import pandas as pd

backend_dir = os.path.dirname(os.path.abspath(__file__))
BASE_DIR = os.path.dirname(backend_dir)

# File yang akan dibersihkan
targets = [
<<<<<<< HEAD
    os.path.join(BASE_DIR, "Dataset", "prosperloandata_28_fitur_large.csv"),
    os.path.join(BASE_DIR, "prosperloandata_28_fitur_small.csv")
=======
    os.path.join(BASE_DIR, "Dataset", r"/home/sony/Downloads/prosperloandata_28_fitur_large.csv"),
>>>>>>> 8247c49 (Menyambungkan ke supabase)
]

print("=== MEMULAI PEMBERSIHAN DATASET LOKAL ===")

for filepath in targets:
    if os.path.exists(filepath):
        print(f"\n[INFO] Membaca file: {filepath}")
        df = pd.read_csv(filepath, low_memory=False)
        
        if "IncomeRange" in df.columns:
<<<<<<< HEAD
            count = (df["IncomeRange"] == "Not displayed").sum()
            if count > 0:
                print(f"[OK] Menemukan {count:,} baris 'Not displayed'. Mengganti ke '$25,000-49,999'...")
                df["IncomeRange"] = df["IncomeRange"].replace("Not displayed", "$25,000-49,999")
=======
            count = (df["IncomeRange"] == "Not employed").sum()
            if count > 0:
                print(f"[OK] Menemukan {count:,} baris 'Not employed'. Mengganti ke '$25,000-49,999'...")
                df["IncomeRange"] = df["IncomeRange"].replace("Not employed", "$25,000-49,999")
>>>>>>> 8247c49 (Menyambungkan ke supabase)
                
                # Simpan kembali
                df.to_csv(filepath, index=False)
                print(f"[OK] File berhasil disimpan kembali.")
            else:
                print("[INFO] Tidak ditemukan baris 'Not displayed' di file ini.")
        else:
            print("[WARN] Kolom 'IncomeRange' tidak ditemukan.")
    else:
        print(f"[WARN] File tidak ditemukan: {filepath}")

<<<<<<< HEAD
print("\n=== PEMBERSIHAN SELESAI ===")
=======
print("\n=== PEMBERSIHAN SELESAI ===")
>>>>>>> 8247c49 (Menyambungkan ke supabase)
