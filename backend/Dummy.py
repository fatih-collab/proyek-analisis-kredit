import os
import random
import uuid
from datetime import datetime, timedelta
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

# Import model tabel dari database.py
from database import UserDB, LoanApplication

# ─── KEAMANAN: Jangan hardcode kredensial di sini! ───────────────────────
# [FIX] Ambil URL dari environment variable, bukan di-hardcode di kode.
# Cara set di terminal sebelum menjalankan script ini:
#   Windows : set DATABASE_URL=postgresql://user:password@host:5432/postgres
#   Linux/Mac: export DATABASE_URL=postgresql://user:password@host:5432/postgres
# ─────────────────────────────────────────────────────────────────────────
SUPABASE_URL = os.environ.get("DATABASE_URL")

if not SUPABASE_URL:
    raise EnvironmentError(
        "[ERROR] Environment variable 'DATABASE_URL' belum di-set!\n"
        "Contoh: export DATABASE_URL=postgresql://user:pass@host:5432/postgres"
    )

# Pengaman postgres:// → postgresql://
if SUPABASE_URL.startswith("postgres://"):
    SUPABASE_URL = SUPABASE_URL.replace("postgres://", "postgresql://", 1)

engine = create_engine(SUPABASE_URL, pool_pre_ping=True)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


def generate_dummy_data(num_records=300):
    db = SessionLocal()
    print(f"🚀 Menghubungkan ke Supabase via DATABASE_URL...")
    print(f"Memulai pembuatan {num_records} data dummy seimbang...")

    tujuan_list = ["Modal Usaha", "Pendidikan", "Renovasi Rumah", "Kendaraan", "Kesehatan", "Lainnya"]
    area_list = ["Urban", "Semiurban", "Rural"]

    total_layak = 0
    total_tidak_layak = 0

    for i in range(num_records):
        user_id = f"user_dummy_{uuid.uuid4().hex[:8]}"
        is_layak = random.random() < 0.6

        if is_layak:
            pekerjaan = random.choice(["Karyawan Swasta", "PNS", "Wiraswasta"])
            pendapatan = random.randint(3500, 12000)
            nominal_pinjaman = random.randint(1000, int(pendapatan * 3))
            cicilan_aktif = random.randint(0, int(pendapatan * 0.2))

            alasan = None
            catatan = random.choice([
                "Profil sangat sehat — risiko sangat rendah",
                "Profil sehat — risiko rendah"
            ])
            score = random.uniform(70.0, 95.0)
            actual_status = random.choice(["Completed", "Current", "FinalPaymentInProgress"])
            total_layak += 1

        else:
            pekerjaan = random.choice(["Freelancer", "Tidak Bekerja", "Karyawan Swasta"])
            pendapatan = random.randint(300, 3500)
            nominal_pinjaman = random.randint(int(pendapatan * 5), 25000)
            cicilan_aktif = random.randint(int(pendapatan * 0.3), int(pendapatan * 0.6))

            alasan = []
            if pendapatan < 1000:
                alasan.append(f"Pendapatan bulanan (${pendapatan}) di bawah standar minimum kelayakan.")
            if pendapatan > 0 and (cicilan_aktif / pendapatan) > 0.4:
                alasan.append("Rasio hutang terhadap pendapatan (DTI) terlalu tinggi karena Anda memiliki cicilan lain yang besar.")
            if pekerjaan == "Tidak Bekerja":
                alasan.append("Status pekerjaan saat ini berisiko tinggi.")
            if not alasan:
                alasan.append("Berdasarkan analisis model ML, profil Anda memiliki histori risiko yang belum memenuhi kriteria.")

            catatan = "Profil berisiko tinggi — pengajuan ditolak otomatis"
            score = random.uniform(15.0, 48.0)
            actual_status = random.choice(["Chargedoff", "Default", "Past Due"])
            total_tidak_layak += 1

        # Tanggal dibuat (acak dalam 60 hari terakhir)
        created = datetime.utcnow() - timedelta(days=random.randint(1, 60))

        # 1. Simpan ke Tabel User
        # [FIX] Kolom age, employment, monthly_income kini ada di UserDB
        new_user = UserDB(
            id=user_id,
            email=f"dummy_{i}_{uuid.uuid4().hex[:4]}@kreditinaja.id",  # [FIX] hindari duplikat email
            password="password123",
            full_name=f"User Dummy {i + 1}",
            created_at=created,
            age=str(random.randint(22, 55)),
            employment=pekerjaan,
            monthly_income=str(pendapatan),
            additional_income="0",
            existing_installments=str(cicilan_aktif),
            profile_completed=True,
        )
        db.add(new_user)

        # 2. Buat JSON Input (disimpan di kolom input_data)
        loan_term = random.choice(["12", "24", "36"])
        loan_purpose = random.choice(tujuan_list)
        property_area = random.choice(area_list)

        input_data_json = {
            "age": new_user.age,
            "employment": pekerjaan,
            "monthlyIncome": str(pendapatan),
            "additionalIncome": "0",
            "loanAmount": str(nominal_pinjaman),
            "loanTerm": loan_term,
            "loanPurpose": loan_purpose,
            "propertyArea": property_area,
            "existingInstallments": str(cicilan_aktif),
        }

        # 3. Simpan ke Tabel Loan Application
        # [FIX] Gunakan nama kolom yang benar: timestamp, input_data, employment, property_area
        new_loan = LoanApplication(
            id=f"pred_dummy_{uuid.uuid4().hex[:8]}",
            user_id=user_id,
            timestamp=created + timedelta(hours=random.randint(1, 24)),
            created_at=created + timedelta(hours=random.randint(1, 24)),
            input_data=input_data_json,
            result="LAYAK" if is_layak else "TIDAK LAYAK",
            confidence=round(score, 1),
            plafon=int(nominal_pinjaman * random.uniform(1.1, 1.5)) if is_layak else None,
            cicilan_per_bulan=round((nominal_pinjaman * 1.15) / int(loan_term), 2) if is_layak else None,
            alasan_penolakan=alasan,
            catatan_risiko=catatan,
            loan_amount=str(nominal_pinjaman),
            loan_term=loan_term,
            loan_purpose=loan_purpose,
            employment=pekerjaan,
            property_area=property_area,
            actual_status=actual_status,
        )
        db.add(new_loan)

    # Kirim semua data ke Supabase
    try:
        db.commit()
        print("⚡ Kirim data selesai!")
        print(f"✅ SUKSES! {num_records} data dummy berhasil masuk ke Supabase.")
        print(f"📊 Statistik: {total_layak} LAYAK | {total_tidak_layak} TIDAK LAYAK")
    except Exception as e:
        db.rollback()
        print(f"❌ Gagal menyuntikkan data dummy ke Supabase: {e}")
        raise
    finally:
        db.close()


if __name__ == "__main__":
    generate_dummy_data(300)
