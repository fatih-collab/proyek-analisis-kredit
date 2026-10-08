"""
validate_models.py — Validasi dan Komparasi Model Pickle Baru vs Lama
"""
import os
import sys
import joblib
import pandas as pd

# Fix encoding untuk Windows
if sys.stdout.encoding != 'utf-8':
    sys.stdout.reconfigure(encoding='utf-8')

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

OLD_KLAS = os.path.join(BASE_DIR, "model_tuned_final.pkl")
OLD_REG = os.path.join(BASE_DIR, "best_model_regresi2.pkl")

NEW_KLAS = os.path.join(BASE_DIR, "model_klasifikasi_loan.pkl")
NEW_REG = os.path.join(BASE_DIR, "model_regresi_tuned_loan.pkl")

def check_model(path, label):
    print(f"\n==========================================")
    print(f" Memeriksa Model {label}:")
    print(f" Path: {path}")
    print(f"==========================================")
    if not os.path.exists(path):
        print("❌ File tidak ditemukan!")
        return None
    
    try:
        model = joblib.load(path)
        print("✅ Berhasil di-load!")
        print(f"Tipe Model: {type(model)}")
        
        # Cek feature_names_in_ jika ada
        if hasattr(model, "feature_names_in_"):
            features = list(model.feature_names_in_)
            print(f"Jumlah Fitur: {len(features)}")
            print(f"Fitur: {features}")
            return features
        elif hasattr(model, "steps"):
            # Jika pipeline tapi tidak langsung punya feature_names_in_
            print("Model adalah Pipeline. Mencoba memeriksa langkah pertama...")
            step_model = model.steps[0][1]
            if hasattr(step_model, "feature_names_in_"):
                features = list(step_model.feature_names_in_)
                print(f"Jumlah Fitur (Step 1): {len(features)}")
                print(f"Fitur: {features}")
                return features
        print("⚠️ Model tidak memiliki atribut 'feature_names_in_'")
        return []
    except Exception as e:
        print(f"❌ Error saat me-load model: {e}")
        return None

def main():
    print("Memulai validasi model...")
    
    # Check Klasifikasi
    old_klas_features = check_model(OLD_KLAS, "Klasifikasi LAMA (model_tuned_final.pkl)")
    new_klas_features = check_model(NEW_KLAS, "Klasifikasi BARU (model_klasifikasi_loan.pkl)")
    
    # Check Regresi
    old_reg_features = check_model(OLD_REG, "Regresi LAMA (best_model_regresi2.pkl)")
    new_reg_features = check_model(NEW_REG, "Regresi BARU (model_regresi_tuned_loan.pkl)")
    
    # Perbandingan Fitur Klasifikasi
    if old_klas_features is not None and new_klas_features is not None:
        print("\n==========================================")
        print(" Perbandingan Fitur Model Klasifikasi")
        print("==========================================")
        diff_old = set(old_klas_features) - set(new_klas_features)
        diff_new = set(new_klas_features) - set(old_klas_features)
        
        print(f"Jumlah Fitur Lama: {len(old_klas_features)}")
        print(f"Jumlah Fitur Baru: {len(new_klas_features)}")
        
        if diff_old:
            print(f"❌ Fitur ada di LAMA tapi hilang di BARU: {diff_old}")
        if diff_new:
            print(f"⚠️ Fitur ada di BARU tapi tidak ada di LAMA: {diff_new}")
        if not diff_old and not diff_new:
            print("✅ Struktur fitur model Klasifikasi 100% cocok (Identik)!")
            
    # Perbandingan Fitur Regresi
    if old_reg_features is not None and new_reg_features is not None:
        print("\n==========================================")
        print(" Perbandingan Fitur Model Regresi")
        print("==========================================")
        diff_old_r = set(old_reg_features) - set(new_reg_features)
        diff_new_r = set(new_reg_features) - set(old_reg_features)
        
        print(f"Jumlah Fitur Lama: {len(old_reg_features)}")
        print(f"Jumlah Fitur Baru: {len(new_reg_features)}")
        
        if diff_old_r:
            print(f"❌ Fitur ada di LAMA tapi hilang di BARU: {diff_old_r}")
        if diff_new_r:
            print(f"⚠️ Fitur ada di BARU tapi tidak ada di LAMA: {diff_new_r}")
        if not diff_old_r and not diff_new_r:
            print("✅ Struktur fitur model Regresi 100% cocok (Identik)!")

    # Test dummy prediction dengan Predictor baru jika file baru ada
    if os.path.exists(NEW_KLAS) and os.path.exists(NEW_REG):
        print("\n==========================================")
        print(" Menguji Prediksi dengan Model BARU")
        print("==========================================")
        try:
            # Tambahkan path backend ke sys.path
            backend_dir = os.path.dirname(os.path.abspath(__file__))
            if backend_dir not in sys.path:
                sys.path.append(backend_dir)
            from predictor import Predictor
            from schemas import PredictInput
            
            predictor = Predictor()
            
            # Buat sample input layak
            sample_layak = PredictInput(
                age="30",
                employment="Karyawan Swasta",
                monthlyIncome="5000",
                additionalIncome="1000",
                loanAmount="500",
                loanTerm="12",
                propertyArea="Urban",
                existingInstallments="200"
            )
            res_layak = predictor.predict(sample_layak)
            print("✅ Test Input Layak Berhasil:")
            print(f"   Hasil: {res_layak.result}")
            print(f"   Keyakinan: {res_layak.confidence}%")
            if res_layak.result == "LAYAK":
                print(f"   Plafon: ${res_layak.plafon:,}")
                print(f"   Bunga: {res_layak.bunga_persen}")
                print(f"   Cicilan: ${res_layak.cicilan_per_bulan}/bulan")
            else:
                print(f"   Alasan Penolakan: {res_layak.alasan_penolakan}")
                
            # Buat sample input berisiko (DTI sangat tinggi / tidak bekerja)
            sample_tidak_layak = PredictInput(
                age="25",
                employment="Tidak Bekerja",
                monthlyIncome="200",
                additionalIncome="0",
                loanAmount="5000",
                loanTerm="36",
                propertyArea="Rural",
                existingInstallments="300"
            )
            res_tl = predictor.predict(sample_tidak_layak)
            print("\n✅ Test Input Tidak Layak Berhasil:")
            print(f"   Hasil: {res_tl.result}")
            print(f"   Keyakinan: {res_tl.confidence}%")
            print(f"   Alasan Penolakan: {res_tl.alasan_penolakan}")
            
        except Exception as e:
            print(f"❌ Error saat menguji prediksi: {e}")

if __name__ == "__main__":
    main()
