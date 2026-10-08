import os
import uuid
from sqlalchemy import create_engine, Column, Integer, String, Float, DateTime, Boolean, JSON, Text
from sqlalchemy.orm import declarative_base, sessionmaker
from datetime import datetime

# Ambil URL Database dari Environment Variable Railway
SQLALCHEMY_DATABASE_URL = os.environ.get("DATABASE_URL", "sqlite:///./local_fallback.db")

# ─── PENGAMAN OTOMATIS RAILWAY/SUPABASE ───
# Jika Supabase memberikan awalan 'postgres://', otomatis ubah ke 'postgresql://'
# agar SQLAlchemy versi terbaru tidak crash.
if SQLALCHEMY_DATABASE_URL.startswith("postgres://"):
    SQLALCHEMY_DATABASE_URL = SQLALCHEMY_DATABASE_URL.replace("postgres://", "postgresql://", 1)

# Inisialisasi koneksi — dengan pool settings yang aman untuk Supabase pooler
_is_sqlite = SQLALCHEMY_DATABASE_URL.startswith("sqlite")

if _is_sqlite:
    engine = create_engine(SQLALCHEMY_DATABASE_URL, connect_args={"check_same_thread": False})
else:
    engine = create_engine(
        SQLALCHEMY_DATABASE_URL,
        pool_pre_ping=True,       # Cek koneksi masih hidup sebelum dipakai
        pool_size=5,              # Max koneksi yang di-pool
        max_overflow=10,          # Koneksi tambahan saat pool penuh
        pool_recycle=300,         # Recycle koneksi setiap 5 menit (aman untuk Supabase)
    )

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()


# ══════════════════════════════════════════════════════════════════════════
# TABEL: Users — Data Pengguna Aplikasi
# ══════════════════════════════════════════════════════════════════════════

class UserDB(Base):
    __tablename__ = "users"

    id = Column(String, primary_key=True, index=True)
    email = Column(String, unique=True, index=True, nullable=False)
    password = Column(String, nullable=False)  # Plain text sesuai permintaan
    full_name = Column(String, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)

    # Profile fields
    phone = Column(String, default="")
    gender = Column(String, default="")
    marital_status = Column(String, default="")
    dependents = Column(String, default="0")   # [FIX] ubah Integer → String agar konsisten dengan form frontend
    education = Column(String, default="")
    profile_completed = Column(Boolean, default=False)

    # [FIX] Kolom yang sebelumnya hilang — dipakai oleh main.py & Dummy.py
    age = Column(String, default="")
    employment = Column(String, default="")
    monthly_income = Column(String, default="0")
    additional_income = Column(String, default="0")
    existing_installments = Column(String, default="0")
    address = Column(String, default="")


# ══════════════════════════════════════════════════════════════════════════
# TABEL: Loan Applications — Log Pengajuan (Termasuk untuk Retraining)
# ══════════════════════════════════════════════════════════════════════════

class LoanApplication(Base):
    __tablename__ = "loan_applications"

    id = Column(String, primary_key=True, index=True)
    user_id = Column(String, index=True, nullable=True)  # FK ke users

    # [FIX] Tambahkan 'timestamp' sebagai alias created_at — dipakai main.py & Dummy.py
    timestamp = Column(DateTime, default=datetime.utcnow)
    created_at = Column(DateTime, default=datetime.utcnow)

    # Data pinjaman
    loan_amount = Column(String, nullable=True)   # [FIX] String agar konsisten dengan form (bukan Float)
    loan_term = Column(String, nullable=True)
    loan_purpose = Column(String, nullable=True)

    # [FIX] Kolom tambahan yang dipakai Dummy.py & mlops_pipeline.py
    employment = Column(String, nullable=True)
    property_area = Column(String, nullable=True)

    # [FIX] input_data JSON — dipakai main.py (auth/predictions) & mlops_pipeline.py
    input_data = Column(JSON, nullable=True)

    # Hasil prediksi
    plafon = Column(Float, nullable=True)
    cicilan_per_bulan = Column(Float, nullable=True)
    result = Column(String)         # LAYAK / TIDAK LAYAK
    confidence = Column(Float)
    alasan_penolakan = Column(JSON, nullable=True)   # List of strings
    catatan_risiko = Column(String, nullable=True)

    # Kolom MLOps (Ground Truth)
    actual_status = Column(String, nullable=True)    # "Completed", "Chargedoff", dst.
    is_verified_for_training = Column(Boolean, default=False)


# ══════════════════════════════════════════════════════════════════════════
# TABEL: User Financial Profiles — Data Keuangan & Pekerjaan User
# ══════════════════════════════════════════════════════════════════════════

class UserFinancialProfile(Base):
    __tablename__ = "user_financial_profiles"

    id = Column(String, primary_key=True, index=True)
    user_id = Column(String, index=True, nullable=False)  # FK ke users

    employment = Column(String, default="")
    monthly_income = Column(String, default="0")
    additional_income = Column(String, default="0")
    existing_installments = Column(String, default="0")
    address = Column(String, default="")
    property_area = Column(String, default="")
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)


# ══════════════════════════════════════════════════════════════════════════
# TABEL: Training Data Log — Log Data Training Model
# ══════════════════════════════════════════════════════════════════════════

class TrainingDataLog(Base):
    __tablename__ = "training_data_log"

    id = Column(String, primary_key=True, index=True)
    loan_application_id = Column(String, index=True, nullable=False)  # FK ke loan_applications
    used_at = Column(DateTime, default=datetime.utcnow)
    model_version = Column(String, nullable=True)
    included_in_training = Column(Boolean, default=False)


# ══════════════════════════════════════════════════════════════════════════
# TABEL: Model Metrics — Log Evaluasi Setiap Retraining  [FIX] BARU
# ══════════════════════════════════════════════════════════════════════════

class ModelMetric(Base):
    __tablename__ = "model_metrics"

    id = Column(String, primary_key=True, index=True, default=lambda: str(uuid.uuid4()))
    training_date = Column(DateTime, default=datetime.utcnow)
    model_type = Column(String, nullable=False)   # "Klasifikasi" / "Regresi"

    # Metrik Klasifikasi
    accuracy = Column(Float, nullable=True)
    f1_score = Column(Float, nullable=True)
    threshold = Column(Float, nullable=True)      # optimal decision threshold

    # Metrik Regresi
    rmse = Column(Float, nullable=True)

    # Info dataset saat training
    dataset_size = Column(Integer, nullable=True)
    db_data_size = Column(Integer, nullable=True)  # jumlah data dari DB (bukan base CSV)


# ══════════════════════════════════════════════════════════════════════════
# FUNGSI UTILITAS
# ══════════════════════════════════════════════════════════════════════════

def init_db():
    """Buat semua tabel jika belum ada."""
    Base.metadata.create_all(bind=engine)
    print("[OK] Database tables initialized (created if not exist)")


def get_db():
    """Dependency untuk FastAPI — menghasilkan database session."""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
