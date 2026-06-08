"""
main.py — FastAPI entry point untuk PDBL-MLOPS Backend
Jalankan: python main.py
Docs    : http://localhost:8000/docs
"""
import sys
import os

# Tambahkan direktori backend ke sys.path agar modul lokal bisa di-import
backend_dir = os.path.dirname(os.path.abspath(__file__))
if backend_dir not in sys.path:
    sys.path.insert(0, backend_dir)

# PENTING: Jangan panggil sys.stdout.reconfigure di module level —
# di Docker/Railway stdout tidak selalu bisa di-reconfigure dan akan crash.
# Cukup set env var PYTHONIOENCODING=utf-8 di Dockerfile (sudah ditambahkan).

import json
import time
from contextlib import asynccontextmanager
from datetime import datetime

from fastapi import FastAPI, HTTPException, Depends, Header
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy.orm import Session
from database import init_db, get_db, UserDB, LoanApplication
from schemas import PredictInput, PredictOutput
from admin_schemas import (
    AdminLoginRequest, AdminLoginResponse,
    BulkDataRequest, EDAStats,
    DatasetEDAResponse, PredictionLogEntry, PredictionLogsResponse,
)
import uvicorn
import pandas as pd
import numpy as np

# ── Admin credentials ────────────────────────────────────────────────────
ADMIN_EMAIL    = os.environ.get("ADMIN_EMAIL", "admin@kreditinaja.id")
ADMIN_PASSWORD = os.environ.get("ADMIN_PASSWORD", "admin123")

# ── Paths ─────────────────────────────────────────────────────────────────
BASE_DIR = os.path.dirname(backend_dir)
DATASET_PATH = os.path.join(BASE_DIR, "Dataset", "prosperloandata_28_fitur_large.csv")
if not os.path.exists(DATASET_PATH):
    DATASET_PATH = os.path.join(BASE_DIR, "prosperloandata_28_fitur_small.csv")
PREDICTION_LOG_PATH = os.path.join(backend_dir, "prediction_logs.json")

# ── Active admin tokens (in-memory store) ─────────────────────────────────
active_admin_tokens: set = set()

# ── Predictor (di-init saat startup, bukan di module level) ──────────────
predictor = None
_cached_eda: DatasetEDAResponse | None = None


# ══════════════════════════════════════════════════════════════════════════
# LIFESPAN — Init model saat startup (Railway-safe)
# ══════════════════════════════════════════════════════════════════════════

@asynccontextmanager
async def lifespan(app: FastAPI):
    """Startup: load models + init database. Shutdown: cleanup."""
    global predictor
    print("=" * 55)
    print("  PDBL-MLOPS Backend API — Starting up")
    print("=" * 55)

    # Init database tables (Supabase)
    try:
        init_db()
        print("[OK] Database tables ready (Supabase)")
    except Exception as e:
        print(f"[ERROR] Gagal init database: {e}")

    # Load model di sini, bukan di module level
    try:
        from predictor import Predictor
        predictor = Predictor()
        print("[OK] Predictor berhasil diinisialisasi")
    except Exception as e:
        print(f"[ERROR] Gagal init Predictor: {e}")
        predictor = None

    # Pre-compute EDA (opsional, tidak fatal kalau gagal)
    try:
        _compute_eda_from_csv()
    except Exception as e:
        print(f"[WARN] Gagal pre-compute EDA: {e}")

    print("[OK] Startup selesai — API siap menerima request")
    yield
    print("[INFO] Shutting down...")


# ── Init FastAPI ──────────────────────────────────────────────────────────
app = FastAPI(
    title="PDBL-MLOPS Loan Prediction API",
    description=(
        "API prediksi kelayakan pinjaman menggunakan dua model ML:\n"
        "1. Klasifikasi (LightGBM/XGBoost) → ACCEPT/REJECT\n"
        "2. Regresi (XGBoost) → Plafon maksimal\n"
        "Terinspirasi dari Prosper Marketplace dataset."
    ),
    version="1.0.0",
    docs_url="/docs",
    redoc_url="/redoc",
    lifespan=lifespan,
)

# ── CORS ───────────────────────────────────────────────────────────────────
_default_origins = [
    "http://localhost:3000",
    "http://localhost:3001",
    "http://127.0.0.1:3000",
    "http://127.0.0.1:3001",
]
_env_origins = os.environ.get("CORS_ORIGINS", "")
if _env_origins:
    _default_origins.extend([o.strip() for o in _env_origins.split(",") if o.strip()])

app.add_middleware(
    CORSMiddleware,
    allow_origins=_default_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# ══════════════════════════════════════════════════════════════════════════
# DATASET EDA
# ══════════════════════════════════════════════════════════════════════════

def _compute_eda_from_csv() -> DatasetEDAResponse:
    """Load prosperLoanData.csv dan hitung semua statistik EDA."""
    global _cached_eda
    if _cached_eda is not None:
        return _cached_eda

    if not os.path.exists(DATASET_PATH):
        print(f"[WARN] Dataset tidak ditemukan: {DATASET_PATH}")
        return DatasetEDAResponse()

    print(f"[INFO] Loading dataset dari {DATASET_PATH} ...")
    df = pd.read_csv(DATASET_PATH, low_memory=False)
    if "IncomeRange" in df.columns:
        df["IncomeRange"] = df["IncomeRange"].replace("Not displayed", "$25,000-49,999")
    print(f"[OK] Dataset loaded: {len(df)} rows, {len(df.columns)} columns")

    total = len(df)
    eda = DatasetEDAResponse(totalRecords=total)

    if "StatedMonthlyIncome" in df.columns:
        income = pd.to_numeric(df["StatedMonthlyIncome"], errors="coerce").dropna()
        eda.avgMonthlyIncome = round(float(income.mean()), 2)
        eda.medianMonthlyIncome = round(float(income.median()), 2)

    if "DebtToIncomeRatio" in df.columns:
        dti = pd.to_numeric(df["DebtToIncomeRatio"], errors="coerce").dropna()
        eda.avgDTI = round(float(dti.mean()), 4)
        eda.medianDTI = round(float(dti.median()), 4)

    if "CreditScoreRangeLower" in df.columns:
        cs = pd.to_numeric(df["CreditScoreRangeLower"], errors="coerce").dropna()
        eda.avgCreditScore = round(float(cs.mean()), 1)

    loan_col = None
    for col_name in ["LoanOriginalAmount", "AmountBorrowed"]:
        if col_name in df.columns:
            loan_col = col_name
            break

    if loan_col:
        la = pd.to_numeric(df[loan_col], errors="coerce").dropna()
        eda.avgLoanAmount = round(float(la.mean()), 2)
        eda.medianLoanAmount = round(float(la.median()), 2)
        eda.minLoanAmount = round(float(la.min()), 2)
        eda.maxLoanAmount = round(float(la.max()), 2)
        bins = [0, 2000, 5000, 10000, 15000, 20000, 25000, 35000, 100000]
        labels = ["$0-2k", "$2k-5k", "$5k-10k", "$10k-15k", "$15k-20k", "$20k-25k", "$25k-35k", "$35k+"]
        cuts = pd.cut(la, bins=bins, labels=labels, right=False)
        dist = cuts.value_counts().sort_index()
        eda.loanAmountHistogram = [{"label": str(k), "value": int(v)} for k, v in dist.items()]

    if "LoanStatus" in df.columns:
        eda.loanStatusDistribution = {str(k): int(v) for k, v in df["LoanStatus"].value_counts().head(10).items()}

    if "Term" in df.columns:
        eda.termDistribution = {str(k): int(v) for k, v in df["Term"].value_counts().items()}

    if "ProsperRating (Alpha)" in df.columns:
        pr = df["ProsperRating (Alpha)"].dropna().value_counts().sort_index()
        eda.prosperRatingDistribution = {str(k): int(v) for k, v in pr.items()}

    if "EmploymentStatus" in df.columns:
        eda.employmentDistribution = {str(k): int(v) for k, v in df["EmploymentStatus"].value_counts().head(10).items()}

    if "IncomeRange" in df.columns:
        eda.incomeRangeDistribution = {str(k): int(v) for k, v in df["IncomeRange"].value_counts().items()}

    if "Occupation" in df.columns:
        eda.occupationTop10 = {str(k): int(v) for k, v in df["Occupation"].value_counts().head(10).items()}

    if "BorrowerState" in df.columns:
        eda.borrowerStateTop10 = {str(k): int(v) for k, v in df["BorrowerState"].value_counts().head(10).items()}

    if "IsBorrowerHomeowner" in df.columns:
        eda.homeownerDistribution = {str(k): int(v) for k, v in df["IsBorrowerHomeowner"].value_counts().items()}

    if "ListingCategory (numeric)" in df.columns:
        cat_map = {
            0: "Not Available", 1: "Debt Consolidation", 2: "Home Improvement",
            3: "Business", 4: "Personal Loan", 5: "Student Use", 6: "Auto",
            7: "Other", 8: "Baby & Adoption", 9: "Boat", 10: "Cosmetic Procedure",
            11: "Engagement Ring", 12: "Green Loans", 13: "Household Expenses",
            14: "Large Purchases", 15: "Medical/Dental", 16: "Motorcycle",
            17: "RV", 18: "Taxes", 19: "Vacation", 20: "Wedding Loans",
        }
        lc = pd.to_numeric(df["ListingCategory (numeric)"], errors="coerce").dropna().astype(int)
        lc_named = lc.map(lambda x: cat_map.get(x, f"Cat-{x}"))
        eda.listingCategoryDistribution = {str(k): int(v) for k, v in lc_named.value_counts().head(10).items()}

    if "CreditScoreRangeLower" in df.columns:
        cs = pd.to_numeric(df["CreditScoreRangeLower"], errors="coerce").dropna()
        bins_cs = [0, 500, 550, 600, 650, 700, 750, 800, 900]
        labels_cs = ["<500", "500-549", "550-599", "600-649", "650-699", "700-749", "750-799", "800+"]
        cuts_cs = pd.cut(cs, bins=bins_cs, labels=labels_cs, right=False)
        dist_cs = cuts_cs.value_counts().sort_index()
        eda.creditScoreHistogram = [{"label": str(k), "value": int(v)} for k, v in dist_cs.items()]
        eda.creditScoreRanges = {str(k): int(v) for k, v in dist_cs.items()}

    if "DebtToIncomeRatio" in df.columns:
        dti = pd.to_numeric(df["DebtToIncomeRatio"], errors="coerce").dropna()
        dti_clipped = dti.clip(upper=2.0)
        bins_dti = [0, 0.1, 0.2, 0.3, 0.4, 0.5, 0.75, 1.0, 2.0]
        labels_dti = ["0-10%", "10-20%", "20-30%", "30-40%", "40-50%", "50-75%", "75-100%", "100%+"]
        cuts_dti = pd.cut(dti_clipped, bins=bins_dti, labels=labels_dti, right=False)
        dist_dti = cuts_dti.value_counts().sort_index()
        eda.dtiHistogram = [{"label": str(k), "value": int(v)} for k, v in dist_dti.items()]

    if "StatedMonthlyIncome" in df.columns:
        inc = pd.to_numeric(df["StatedMonthlyIncome"], errors="coerce").dropna()
        inc_clipped = inc.clip(upper=25000)
        bins_inc = [0, 2000, 4000, 6000, 8000, 10000, 15000, 25000]
        labels_inc = ["$0-2k", "$2k-4k", "$4k-6k", "$6k-8k", "$8k-10k", "$10k-15k", "$15k+"]
        cuts_inc = pd.cut(inc_clipped, bins=bins_inc, labels=labels_inc, right=False)
        dist_inc = cuts_inc.value_counts().sort_index()
        eda.monthlyIncomeHistogram = [{"label": str(k), "value": int(v)} for k, v in dist_inc.items()]

    date_col = None
    for col_name in ["ListingCreationDate", "LoanOriginationDate", "DateCreditPulled"]:
        if col_name in df.columns:
            date_col = col_name
            break

    if date_col:
        dates = pd.to_datetime(df[date_col], errors="coerce").dropna()
        by_year = dates.dt.year.value_counts().sort_index()
        eda.loansByYear = [{"label": str(int(k)), "value": int(v)} for k, v in by_year.items()]
        by_ym = dates.dt.to_period("M").value_counts().sort_index().tail(36)
        eda.loansByYearMonth = [{"label": str(k), "value": int(v)} for k, v in by_ym.items()]

    _cached_eda = eda
    print(f"[OK] EDA computed: {total} records")
    return eda


# ══════════════════════════════════════════════════════════════════════════
# PREDICTION LOGGING (DATABASE)
# ══════════════════════════════════════════════════════════════════════════

def _save_prediction_to_db(entry: dict):
    """Simpan prediction log ke database Supabase."""
    try:
        db = next(get_db())
        record = LoanApplication(
            id=entry.get("id", f"pred_{int(time.time() * 1000)}"),
            user_id=entry.get("userId"),
            timestamp=datetime.fromisoformat(entry["timestamp"]) if entry.get("timestamp") else datetime.utcnow(),
            input_data=entry.get("inputData", {}),
            result=entry.get("result", ""),
            confidence=entry.get("confidence", 0),
            plafon=entry.get("plafon"),
            cicilan_per_bulan=entry.get("cicilanPerBulan"),
            alasan_penolakan=entry.get("alasanPenolakan"),
            catatan_risiko=entry.get("catatanRisiko"),
            loan_amount=entry.get("loanAmount"),
            loan_term=entry.get("loanTerm"),
            loan_purpose=entry.get("loanPurpose"),
            employment=entry.get("employment"),
            property_area=entry.get("propertyArea"),
            full_name=entry.get("fullName"),
            email=entry.get("email"),
            phone=entry.get("phone"),
            address=entry.get("address"),
        )
        db.add(record)
        db.commit()
        db.close()
    except Exception as e:
        print(f"[WARN] Gagal menyimpan prediction log ke DB: {e}")


# ══════════════════════════════════════════════════════════════════════════
# ADMIN AUTH
# ══════════════════════════════════════════════════════════════════════════

def verify_admin_token(authorization: str = Header(default="")):
    token = authorization.replace("Bearer ", "").strip()
    if not token or token not in active_admin_tokens:
        raise HTTPException(status_code=401, detail="Unauthorized: Invalid admin token")
    return token


# ══════════════════════════════════════════════════════════════════════════
# ENDPOINTS
# ══════════════════════════════════════════════════════════════════════════

@app.get("/", tags=["Info"])
def root():
    return {
        "app"      : "PDBL-MLOPS Loan Prediction API",
        "status"   : "running",
        "endpoints": {
            "docs"        : "/docs",
            "health"      : "/health",
            "predict"     : "POST /predict",
            "admin_login" : "POST /admin/login",
            "admin_eda"   : "GET /admin/eda",
            "admin_preds" : "GET /admin/predictions",
        }
    }


@app.get("/health", tags=["Monitoring"])
def health_check():
    models_ok = predictor is not None and predictor.models_loaded
    return {
        "status"        : "ok",
        "models_loaded" : models_ok,
        "message"       : (
            "Semua model ready" if models_ok
            else "Model belum di-load. Cek file .pkl di /app/models/"
        ),
    }


@app.post("/predict", response_model=PredictOutput, tags=["Prediction"])
def predict(data: PredictInput):
    if predictor is None or not predictor.models_loaded:
        raise HTTPException(
            status_code=503,
            detail="Model belum siap. Cek /health untuk detail."
        )
    try:
        result = predictor.predict(data)

        log_entry = {
            "id"             : f"pred_{int(time.time() * 1000)}",
            "timestamp"      : datetime.now().isoformat(),
            "userId"         : data.userId,
            "inputData"      : data.model_dump(),
            "result"         : result.result,
            "confidence"     : result.confidence,
            "plafon"         : result.plafon,
            "cicilanPerBulan": result.cicilan_per_bulan,
            "alasanPenolakan": result.alasan_penolakan,
            "catatanRisiko"  : result.catatan_risiko,
            "loanAmount"     : data.loanAmount,
            "loanTerm"       : data.loanTerm,
            "loanPurpose"    : data.loanPurpose,
            "employment"     : data.employment,
            "propertyArea"   : data.propertyArea,
            "fullName"       : data.fullName,
            "email"          : data.email,
            "phone"          : data.phone,
            "address"        : data.address,
        }
        _save_prediction_to_db(log_entry)
        return result

    except RuntimeError as e:
        raise HTTPException(status_code=503, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Terjadi kesalahan: {str(e)}")


# ══════════════════════════════════════════════════════════════════════════
# ADMIN ENDPOINTS
# ══════════════════════════════════════════════════════════════════════════

@app.post("/admin/login", response_model=AdminLoginResponse, tags=["Admin"])
def admin_login(data: AdminLoginRequest):
    if data.email == ADMIN_EMAIL and data.password == ADMIN_PASSWORD:
        import hashlib
        token = hashlib.sha256(f"admin_{time.time()}".encode()).hexdigest()[:32]
        active_admin_tokens.add(token)
        return AdminLoginResponse(success=True, token=token)
    return AdminLoginResponse(success=False, error="Email atau password admin salah")


@app.get("/admin/eda", response_model=DatasetEDAResponse, tags=["Admin"])
def admin_eda(token: str = Depends(verify_admin_token)):
    try:
        return _compute_eda_from_csv()
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Gagal menghitung EDA: {str(e)}")


@app.get("/admin/predictions", response_model=PredictionLogsResponse, tags=["Admin"])
def admin_predictions(token: str = Depends(verify_admin_token), db: Session = Depends(get_db)):
    logs = db.query(LoanApplication).order_by(LoanApplication.timestamp.desc()).limit(500).all()
    entries = []
    for log in logs:
        entries.append(PredictionLogEntry(
            id=log.id or "",
            timestamp=log.timestamp.isoformat() if log.timestamp else "",
            inputData=log.input_data or {},
            result=log.result or "",
            confidence=log.confidence or 0,
            plafon=int(log.plafon) if log.plafon else None,
            cicilanPerBulan=log.cicilan_per_bulan,
            alasanPenolakan=log.alasan_penolakan,
            catatanRisiko=log.catatan_risiko,
            loanAmount=log.loan_amount or "0",
            loanTerm=log.loan_term or "36",
            loanPurpose=log.loan_purpose or "",
            creditHistory="",
            employment=log.employment or "",
            propertyArea=log.property_area or "",
            fullName=log.full_name or "",
            email=log.email or "",
            phone=log.phone or "",
            address=log.address or "",
        ))
    return PredictionLogsResponse(total=len(entries), predictions=entries)


@app.post("/admin/stats", response_model=EDAStats, tags=["Admin"])
def admin_stats(data: BulkDataRequest):
    users = data.users
    predictions = data.predictions

    total_users = len(users)
    total_preds = len(predictions)
    layak = sum(1 for p in predictions if p.get("result") == "LAYAK")
    tidak_layak = total_preds - layak
    approval_rate = round((layak / total_preds * 100), 1) if total_preds > 0 else 0.0
    avg_conf = round(sum(p.get("confidence", 0) for p in predictions) / total_preds, 1) if total_preds > 0 else 0.0

    purpose_dist: dict = {}
    credit_dist: dict  = {}
    area_dist: dict    = {}
    emp_dist: dict     = {}
    for p in predictions:
        inp = p.get("inputData", {})
        purpose = inp.get("loanPurpose", "Lainnya")
        purpose_dist[purpose] = purpose_dist.get(purpose, 0) + 1
        credit = inp.get("creditHistory", "Unknown")
        credit_dist[credit] = credit_dist.get(credit, 0) + 1
        area = inp.get("propertyArea", "Unknown")
        area_dist[area] = area_dist.get(area, 0) + 1
        emp = inp.get("employment", "Unknown")
        emp_dist[emp] = emp_dist.get(emp, 0) + 1

    ranges = {"$0-1k": 0, "$1k-5k": 0, "$5k-10k": 0, "$10k-25k": 0, "$25k+": 0}
    for p in predictions:
        try:
            amt = int(p.get("loanAmount", "0") or "0")
        except (ValueError, TypeError):
            amt = 0
        if amt < 1000:   ranges["$0-1k"] += 1
        elif amt < 5000:  ranges["$1k-5k"] += 1
        elif amt < 10000: ranges["$5k-10k"] += 1
        elif amt < 25000: ranges["$10k-25k"] += 1
        else:             ranges["$25k+"] += 1

    return EDAStats(
        totalUsers=total_users,
        totalPredictions=total_preds,
        layakCount=layak,
        tidakLayakCount=tidak_layak,
        approvalRate=approval_rate,
        avgConfidence=avg_conf,
        loanPurposeDistribution=purpose_dist,
        creditHistoryDistribution=credit_dist,
        propertyAreaDistribution=area_dist,
        employmentDistribution=emp_dist,
        loanAmountRanges=ranges,
    )


# ══════════════════════════════════════════════════════════════════════════
# USER AUTH ENDPOINTS (Supabase-backed)
# ══════════════════════════════════════════════════════════════════════════

from pydantic import BaseModel
from typing import Optional

class RegisterRequest(BaseModel):
    email: str
    password: str
    fullName: str

class LoginRequest(BaseModel):
    email: str
    password: str

class ProfileUpdateRequest(BaseModel):
    phone: Optional[str] = None
    age: Optional[str] = None
    gender: Optional[str] = None
    maritalStatus: Optional[str] = None
    dependents: Optional[str] = None
    education: Optional[str] = None
    employment: Optional[str] = None
    monthlyIncome: Optional[str] = None
    additionalIncome: Optional[str] = None
    address: Optional[str] = None
    profileCompleted: Optional[bool] = None
    existingInstallments: Optional[str] = None
    fullName: Optional[str] = None


@app.post("/auth/register", tags=["Auth"])
def auth_register(data: RegisterRequest, db: Session = Depends(get_db)):
    existing = db.query(UserDB).filter(UserDB.email == data.email.lower()).first()
    if existing:
        raise HTTPException(status_code=400, detail="Email sudah terdaftar")

    import hashlib
    user_id = f"user_{int(time.time() * 1000)}_{hashlib.md5(data.email.encode()).hexdigest()[:8]}"
    new_user = UserDB(
        id=user_id,
        email=data.email.lower(),
        password=data.password,
        full_name=data.fullName,
    )
    db.add(new_user)
    db.commit()
    db.refresh(new_user)

    token = hashlib.sha256(f"user_{time.time()}_{user_id}".encode()).hexdigest()[:32]
    return {
        "success": True,
        "token": token,
        "user": {
            "id": new_user.id,
            "email": new_user.email,
            "fullName": new_user.full_name,
            "createdAt": new_user.created_at.isoformat() if new_user.created_at else "",
            "profile": _user_to_profile(new_user),
        }
    }


@app.post("/auth/login", tags=["Auth"])
def auth_login(data: LoginRequest, db: Session = Depends(get_db)):
    user = db.query(UserDB).filter(
        UserDB.email == data.email.lower(),
        UserDB.password == data.password
    ).first()
    if not user:
        raise HTTPException(status_code=401, detail="Email atau password salah")

    import hashlib
    token = hashlib.sha256(f"user_{time.time()}_{user.id}".encode()).hexdigest()[:32]
    return {
        "success": True,
        "token": token,
        "user": {
            "id": user.id,
            "email": user.email,
            "fullName": user.full_name,
            "createdAt": user.created_at.isoformat() if user.created_at else "",
            "profile": _user_to_profile(user),
        }
    }


@app.get("/auth/profile/{user_id}", tags=["Auth"])
def auth_get_profile(user_id: str, db: Session = Depends(get_db)):
    user = db.query(UserDB).filter(UserDB.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="User tidak ditemukan")
    return {
        "id": user.id,
        "email": user.email,
        "fullName": user.full_name,
        "createdAt": user.created_at.isoformat() if user.created_at else "",
        "profile": _user_to_profile(user),
    }


@app.put("/auth/profile/{user_id}", tags=["Auth"])
def auth_update_profile(user_id: str, data: ProfileUpdateRequest, db: Session = Depends(get_db)):
    user = db.query(UserDB).filter(UserDB.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="User tidak ditemukan")

    if data.phone is not None: user.phone = data.phone
    if data.age is not None: user.age = data.age
    if data.gender is not None: user.gender = data.gender
    if data.maritalStatus is not None: user.marital_status = data.maritalStatus
    if data.dependents is not None: user.dependents = data.dependents
    if data.education is not None: user.education = data.education
    if data.employment is not None: user.employment = data.employment
    if data.monthlyIncome is not None: user.monthly_income = data.monthlyIncome
    if data.additionalIncome is not None: user.additional_income = data.additionalIncome
    if data.address is not None: user.address = data.address
    if data.profileCompleted is not None: user.profile_completed = data.profileCompleted
    if data.existingInstallments is not None: user.existing_installments = data.existingInstallments
    if data.fullName is not None:
        user.full_name = data.fullName

    db.commit()
    db.refresh(user)
    return {"success": True, "profile": _user_to_profile(user)}


@app.get("/auth/predictions/{user_id}", tags=["Auth"])
def auth_get_predictions(user_id: str, db: Session = Depends(get_db)):
    logs = db.query(LoanApplication).filter(
        LoanApplication.user_id == user_id
    ).order_by(LoanApplication.timestamp.desc()).limit(100).all()

    predictions = []
    for log in logs:
        predictions.append({
            "id": log.id,
            "date": log.timestamp.isoformat() if log.timestamp else "",
            "loanAmount": log.loan_amount or "0",
            "loanTerm": log.loan_term or "36",
            "result": log.result or "",
            "confidence": log.confidence or 0,
            "inputData": log.input_data or {},
            "plafon": int(log.plafon) if log.plafon else None,
            "cicilanPerBulan": log.cicilan_per_bulan,
            "alasanPenolakan": log.alasan_penolakan,
            "catatanRisiko": log.catatan_risiko,
        })
    return {"predictions": predictions}


def _user_to_profile(user: UserDB) -> dict:
    return {
        "fullName": user.full_name or "",
        "email": user.email or "",
        "phone": user.phone or "",
        "age": user.age or "",
        "gender": user.gender or "",
        "maritalStatus": user.marital_status or "",
        "dependents": user.dependents or "0",
        "education": user.education or "",
        "employment": user.employment or "",
        "monthlyIncome": user.monthly_income or "0",
        "additionalIncome": user.additional_income or "0",
        "address": user.address or "",
        "profileCompleted": user.profile_completed or False,
        "existingInstallments": user.existing_installments or "0",
    }


# ══════════════════════════════════════════════════════════════════════════
# ENTRY POINT (lokal saja — Railway pakai CMD di Dockerfile)
# ══════════════════════════════════════════════════════════════════════════

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 8000))
    uvicorn.run(
        "main:app",
        host="0.0.0.0",
        port=port,
        reload=False,  # Jangan pakai reload di production
    )

