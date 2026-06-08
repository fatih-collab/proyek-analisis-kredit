import os
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
    age = Column(String, default="")
    gender = Column(String, default="")
    marital_status = Column(String, default="")
    dependents = Column(String, default="0")
    education = Column(String, default="")
    employment = Column(String, default="")
    monthly_income = Column(String, default="0")
    additional_income = Column(String, default="0")
    address = Column(Text, default="")
    profile_completed = Column(Boolean, default=False)
    existing_installments = Column(String, default="0")


# ══════════════════════════════════════════════════════════════════════════
# TABEL: Loan Applications — Log Pengajuan (Termasuk untuk Retraining)
# ══════════════════════════════════════════════════════════════════════════

class LoanApplication(Base):
    __tablename__ = "loan_applications"

    id = Column(String, primary_key=True, index=True)
    user_id = Column(String, index=True, nullable=True)  # Link ke user yang mengajukan
    timestamp = Column(DateTime, default=datetime.utcnow)
    input_data = Column(JSON)   # Menyimpan data input JSON dari frontend
    result = Column(String)     # LAYAK / TIDAK LAYAK
    confidence = Column(Float)
    plafon = Column(Float, nullable=True)
    cicilan_per_bulan = Column(Float, nullable=True)
    alasan_penolakan = Column(JSON, nullable=True)  # List of strings
    catatan_risiko = Column(String, nullable=True)

    # Info tambahan dari form
    loan_amount = Column(String, nullable=True)
    loan_term = Column(String, nullable=True)
    loan_purpose = Column(String, nullable=True)
    employment = Column(String, nullable=True)
    property_area = Column(String, nullable=True)
    full_name = Column(String, nullable=True)
    email = Column(String, nullable=True)
    phone = Column(String, nullable=True)
    address = Column(Text, nullable=True)

    # Kolom MLOps (Ground Truth)
    actual_status = Column(String, nullable=True)   # Contoh: "Completed", "Chargedoff"
    is_verified_for_training = Column(Boolean, default=False)


# ══════════════════════════════════════════════════════════════════════════
# TABEL: Model Metrics — Metrik Evaluasi Model
# ══════════════════════════════════════════════════════════════════════════

class ModelMetric(Base):
    __tablename__ = "model_metrics"

    id = Column(Integer, primary_key=True, index=True)
    training_date = Column(DateTime, default=datetime.utcnow)
    model_type = Column(String)     # "Klasifikasi" atau "Regresi"
    accuracy = Column(Float, nullable=True)
    f1_score = Column(Float, nullable=True)
    rmse = Column(Float, nullable=True)
    dataset_size = Column(Integer)


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