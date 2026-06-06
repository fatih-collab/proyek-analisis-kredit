"""
main.py — FastAPI entry point untuk PDBL-MLOPS Backend
Jalankan: python main.py
Docs    : http://localhost:8000/docs
"""
import sys
if sys.stdout.encoding != 'utf-8':
    sys.stdout.reconfigure(encoding='utf-8')

import os
import json
import time
from datetime import datetime

from fastapi import FastAPI, HTTPException, Depends, Header
from fastapi.middleware.cors import CORSMiddleware
from schemas import PredictInput, PredictOutput
from admin_schemas import (
    AdminLoginRequest, AdminLoginResponse,
    BulkDataRequest, EDAStats,
    DatasetEDAResponse, PredictionLogEntry, PredictionLogsResponse,
)
from predictor import Predictor
import uvicorn
import pandas as pd
import numpy as np

# ── Admin credentials ────────────────────────────────────────────────────
ADMIN_EMAIL = "admin@kreditinaja.id"
ADMIN_PASSWORD = "admin123"

# ── Paths ─────────────────────────────────────────────────────────────────
DATASET_PATH = os.path.join(BASE_DIR, "Dataset", "CLEANN_prosperloandata (1).csv")
if not os.path.exists(DATASET_PATH):
    DATASET_PATH = os.path.join(BASE_DIR, "Dataset", "prosperLoanData.csv")
PREDICTION_LOG_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "prediction_logs.json")

# ── Active admin tokens (in-memory store) ─────────────────────────────────
active_admin_tokens: set = set()

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
)

# ── CORS — izinkan request dari Next.js dev server ────────────────────────
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:3000",
        "http://localhost:3001",
        "http://127.0.0.1:3000",
        "http://127.0.0.1:3001",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ── Load model sekali saat startup ───────────────────────────────────────
predictor = Predictor()


# ══════════════════════════════════════════════════════════════════════════
# DATASET EDA — Load & cache CSV dataset
# ══════════════════════════════════════════════════════════════════════════

_cached_eda: DatasetEDAResponse | None = None


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
    print(f"[OK] Dataset loaded: {len(df)} rows, {len(df.columns)} columns")

    total = len(df)
    eda = DatasetEDAResponse(totalRecords=total)

    # ── Summary stats ──
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

    # Loan amount — Prosper uses "LoanOriginalAmount" or we can derive
    loan_col = None
    for col_name in ["LoanOriginalAmount", "AmountBorrowed", "LoanOriginalAmount"]:
        if col_name in df.columns:
            loan_col = col_name
            break

    if loan_col:
        la = pd.to_numeric(df[loan_col], errors="coerce").dropna()
        eda.avgLoanAmount = round(float(la.mean()), 2)
        eda.medianLoanAmount = round(float(la.median()), 2)
        eda.minLoanAmount = round(float(la.min()), 2)
        eda.maxLoanAmount = round(float(la.max()), 2)

        # Loan Amount Histogram
        bins = [0, 2000, 5000, 10000, 15000, 20000, 25000, 35000, 100000]
        labels = ["$0-2k", "$2k-5k", "$5k-10k", "$10k-15k", "$15k-20k", "$20k-25k", "$25k-35k", "$35k+"]
        cuts = pd.cut(la, bins=bins, labels=labels, right=False)
        dist = cuts.value_counts().sort_index()
        eda.loanAmountHistogram = [{"label": str(k), "value": int(v)} for k, v in dist.items()]

    # ── Distribusi ──
    if "LoanStatus" in df.columns:
        eda.loanStatusDistribution = df["LoanStatus"].value_counts().head(10).to_dict()
        eda.loanStatusDistribution = {str(k): int(v) for k, v in eda.loanStatusDistribution.items()}

    if "Term" in df.columns:
        eda.termDistribution = df["Term"].value_counts().to_dict()
        eda.termDistribution = {str(k): int(v) for k, v in eda.termDistribution.items()}

    if "ProsperRating (Alpha)" in df.columns:
        pr = df["ProsperRating (Alpha)"].dropna().value_counts().sort_index()
        eda.prosperRatingDistribution = {str(k): int(v) for k, v in pr.items()}

    if "EmploymentStatus" in df.columns:
        eda.employmentDistribution = df["EmploymentStatus"].value_counts().head(10).to_dict()
        eda.employmentDistribution = {str(k): int(v) for k, v in eda.employmentDistribution.items()}

    if "IncomeRange" in df.columns:
        eda.incomeRangeDistribution = df["IncomeRange"].value_counts().to_dict()
        eda.incomeRangeDistribution = {str(k): int(v) for k, v in eda.incomeRangeDistribution.items()}

    if "Occupation" in df.columns:
        eda.occupationTop10 = df["Occupation"].value_counts().head(10).to_dict()
        eda.occupationTop10 = {str(k): int(v) for k, v in eda.occupationTop10.items()}

    if "BorrowerState" in df.columns:
        eda.borrowerStateTop10 = df["BorrowerState"].value_counts().head(10).to_dict()
        eda.borrowerStateTop10 = {str(k): int(v) for k, v in eda.borrowerStateTop10.items()}

    if "IsBorrowerHomeowner" in df.columns:
        eda.homeownerDistribution = df["IsBorrowerHomeowner"].value_counts().to_dict()
        eda.homeownerDistribution = {str(k): int(v) for k, v in eda.homeownerDistribution.items()}

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
        eda.listingCategoryDistribution = lc_named.value_counts().head(10).to_dict()
        eda.listingCategoryDistribution = {str(k): int(v) for k, v in eda.listingCategoryDistribution.items()}

    # ── Credit Score Histogram ──
    if "CreditScoreRangeLower" in df.columns:
        cs = pd.to_numeric(df["CreditScoreRangeLower"], errors="coerce").dropna()
        bins_cs = [0, 500, 550, 600, 650, 700, 750, 800, 900]
        labels_cs = ["<500", "500-549", "550-599", "600-649", "650-699", "700-749", "750-799", "800+"]
        cuts_cs = pd.cut(cs, bins=bins_cs, labels=labels_cs, right=False)
        dist_cs = cuts_cs.value_counts().sort_index()
        eda.creditScoreHistogram = [{"label": str(k), "value": int(v)} for k, v in dist_cs.items()]
        eda.creditScoreRanges = {str(k): int(v) for k, v in dist_cs.items()}

    # ── DTI Histogram ──
    if "DebtToIncomeRatio" in df.columns:
        dti = pd.to_numeric(df["DebtToIncomeRatio"], errors="coerce").dropna()
        dti_clipped = dti.clip(upper=2.0)
        bins_dti = [0, 0.1, 0.2, 0.3, 0.4, 0.5, 0.75, 1.0, 2.0]
        labels_dti = ["0-10%", "10-20%", "20-30%", "30-40%", "40-50%", "50-75%", "75-100%", "100%+"]
        cuts_dti = pd.cut(dti_clipped, bins=bins_dti, labels=labels_dti, right=False)
        dist_dti = cuts_dti.value_counts().sort_index()
        eda.dtiHistogram = [{"label": str(k), "value": int(v)} for k, v in dist_dti.items()]

    # ── Monthly Income Histogram ──
    if "StatedMonthlyIncome" in df.columns:
        inc = pd.to_numeric(df["StatedMonthlyIncome"], errors="coerce").dropna()
        inc_clipped = inc.clip(upper=25000)
        bins_inc = [0, 2000, 4000, 6000, 8000, 10000, 15000, 25000]
        labels_inc = ["$0-2k", "$2k-4k", "$4k-6k", "$6k-8k", "$8k-10k", "$10k-15k", "$15k+"]
        cuts_inc = pd.cut(inc_clipped, bins=bins_inc, labels=labels_inc, right=False)
        dist_inc = cuts_inc.value_counts().sort_index()
        eda.monthlyIncomeHistogram = [{"label": str(k), "value": int(v)} for k, v in dist_inc.items()]

    # ── Time series: loans by year ──
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
# PREDICTION LOGGING
# ══════════════════════════════════════════════════════════════════════════

def _load_prediction_logs() -> list:
    """Load prediction logs from JSON file."""
    if not os.path.exists(PREDICTION_LOG_PATH):
        return []
    try:
        with open(PREDICTION_LOG_PATH, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return []


def _save_prediction_log(entry: dict):
    """Append a prediction log entry to the JSON file."""
    logs = _load_prediction_logs()
    logs.append(entry)
    # Keep last 10000 entries max
    if len(logs) > 10000:
        logs = logs[-10000:]
    try:
        with open(PREDICTION_LOG_PATH, "w", encoding="utf-8") as f:
            json.dump(logs, f, ensure_ascii=False, indent=2)
    except Exception as e:
        print(f"[WARN] Gagal menyimpan prediction log: {e}")


# ══════════════════════════════════════════════════════════════════════════
# ADMIN AUTH HELPER
# ══════════════════════════════════════════════════════════════════════════

def verify_admin_token(authorization: str = Header(default="")):
    """Validate admin token from Authorization header."""
    token = authorization.replace("Bearer ", "").strip()
    if not token or token not in active_admin_tokens:
        raise HTTPException(status_code=401, detail="Unauthorized: Invalid admin token")
    return token


# ══════════════════════════════════════════════════════════════════════════
# ENDPOINTS
# ══════════════════════════════════════════════════════════════════════════

@app.get("/", tags=["Info"])
def root():
    """Root endpoint — daftar semua endpoint yang tersedia."""
    return {
        "app"      : "PDBL-MLOPS Loan Prediction API",
        "status"   : "running",
        "endpoints": {
            "docs"        : "http://localhost:8000/docs",
            "health"      : "http://localhost:8000/health",
            "predict"     : "POST http://localhost:8000/predict",
            "admin_login" : "POST http://localhost:8000/admin/login",
            "admin_eda"   : "GET http://localhost:8000/admin/eda",
            "admin_preds" : "GET http://localhost:8000/admin/predictions",
        }
    }


@app.get("/health", tags=["Monitoring"])
def health_check():
    """Cek apakah backend dan model berjalan normal."""
    return {
        "status"        : "ok",
        "models_loaded" : predictor.models_loaded,
        "message"       : (
            "Semua model ready" if predictor.models_loaded
            else "Model belum di-load. Cek file .pkl di root project."
        ),
    }


@app.post("/predict", response_model=PredictOutput, tags=["Prediction"])
def predict(data: PredictInput):
    """
    Prediksi kelayakan pinjaman nasabah (Kredivo-style).

    **Arsitektur:**
    - 8 field diisi user di frontend (pendapatan, cicilan, pekerjaan, dll)
    - Sisanya diisi median dataset Prosper (median imputation)
    - Model ML memprediksi berdasarkan gabungan keduanya
    - Tanpa heuristic rules / hierarchical rules

    **Alur:**
    1. Ekstrak 8 field dari input user
    2. Klasifikasi (26 fitur) → LAYAK / TIDAK LAYAK
    3. Jika LAYAK → Regresi (41 fitur) → Plafon maksimal
    4. Hitung cicilan anuitas dari nominal yang diajukan

    **Returns:**
    - `result`: "LAYAK" atau "TIDAK LAYAK"
    - `confidence`: tingkat keyakinan model (%)
    - `plafon`: plafon maksimal yang bisa dicairkan (jika LAYAK)
    - `cicilan_per_bulan`: cicilan bulanan (jika LAYAK)
    - `alasan_penolakan`: alasan jika TIDAK LAYAK
    """
    try:
        result = predictor.predict(data)

        # ── Log prediction ──
        log_entry = {
            "id": f"pred_{int(time.time() * 1000)}",
            "timestamp": datetime.now().isoformat(),
            "inputData": data.model_dump(),
            "result": result.result,
            "confidence": result.confidence,
            "plafon": result.plafon,
            "cicilanPerBulan": result.cicilan_per_bulan,
            "alasanPenolakan": result.alasan_penolakan,
            "catatanRisiko": result.catatan_risiko,
            "loanAmount": data.loanAmount,
            "loanTerm": data.loanTerm,
            "loanPurpose": data.loanPurpose,
            "employment": data.employment,
            "propertyArea": data.propertyArea,
            # Data kontak nasabah
            "fullName": data.fullName,
            "email": data.email,
            "phone": data.phone,
            "address": data.address,
        }
        _save_prediction_log(log_entry)

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
    """Login admin — validasi credential."""
    if data.email == ADMIN_EMAIL and data.password == ADMIN_PASSWORD:
        import hashlib
        token = hashlib.sha256(f"admin_{time.time()}".encode()).hexdigest()[:32]
        active_admin_tokens.add(token)
        return AdminLoginResponse(success=True, token=token)
    return AdminLoginResponse(success=False, error="Email atau password admin salah")


@app.get("/admin/eda", response_model=DatasetEDAResponse, tags=["Admin"])
def admin_eda(token: str = Depends(verify_admin_token)):
    """
    Mengembalikan statistik EDA komprehensif dari dataset prosperLoanData.csv.
    Data di-cache setelah pertama kali dihitung.
    """
    try:
        return _compute_eda_from_csv()
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Gagal menghitung EDA: {str(e)}")


@app.get("/admin/predictions", response_model=PredictionLogsResponse, tags=["Admin"])
def admin_predictions(token: str = Depends(verify_admin_token)):
    """
    Mengembalikan semua log prediksi user.
    Data dari prediction_logs.json yang di-append setiap kali /predict dipanggil.
    """
    logs = _load_prediction_logs()
    entries = []
    for log in reversed(logs):  # newest first
        entries.append(PredictionLogEntry(
            id=log.get("id", ""),
            timestamp=log.get("timestamp", ""),
            inputData=log.get("inputData", {}),
            result=log.get("result", ""),
            confidence=log.get("confidence", 0),
            plafon=log.get("plafon"),
            cicilanPerBulan=log.get("cicilanPerBulan"),
            alasanPenolakan=log.get("alasanPenolakan"),
            catatanRisiko=log.get("catatanRisiko"),
            loanAmount=log.get("loanAmount", "0"),
            loanTerm=log.get("loanTerm", "36"),
            loanPurpose=log.get("loanPurpose", ""),
            creditHistory=log.get("creditHistory", ""),
            employment=log.get("employment", ""),
            propertyArea=log.get("propertyArea", ""),
            fullName=log.get("fullName", ""),
            email=log.get("email", ""),
            phone=log.get("phone", ""),
            address=log.get("address", ""),
        ))
    return PredictionLogsResponse(total=len(entries), predictions=entries)


@app.post("/admin/stats", response_model=EDAStats, tags=["Admin"])
def admin_stats(data: BulkDataRequest):
    """
    Hitung statistik EDA dari data yang dikirim frontend.
    Frontend mengirim semua users + predictions dari localStorage.
    """
    users = data.users
    predictions = data.predictions

    total_users = len(users)
    total_preds = len(predictions)
    layak = sum(1 for p in predictions if p.get("result") == "LAYAK")
    tidak_layak = total_preds - layak
    approval_rate = round((layak / total_preds * 100), 1) if total_preds > 0 else 0.0
    avg_conf = round(sum(p.get("confidence", 0) for p in predictions) / total_preds, 1) if total_preds > 0 else 0.0

    # Distribusi tujuan pinjaman
    purpose_dist = {}
    credit_dist = {}
    area_dist = {}
    emp_dist = {}
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

    # Loan amount ranges
    ranges = {"$0-1k": 0, "$1k-5k": 0, "$5k-10k": 0, "$10k-25k": 0, "$25k+": 0}
    for p in predictions:
        amt = int(p.get("loanAmount", "0") or "0")
        if amt < 1000: ranges["$0-1k"] += 1
        elif amt < 5000: ranges["$1k-5k"] += 1
        elif amt < 10000: ranges["$5k-10k"] += 1
        elif amt < 25000: ranges["$10k-25k"] += 1
        else: ranges["$25k+"] += 1

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
# ENTRY POINT
# ══════════════════════════════════════════════════════════════════════════

if __name__ == "__main__":
    # Preload EDA data saat startup
    print("=" * 55)
    print("  PDBL-MLOPS Backend API")
    print("=" * 55)
    print("  URL   : http://localhost:8000")
    print("  Docs  : http://localhost:8000/docs")
    print("=" * 55)

    # Pre-compute EDA
    try:
        _compute_eda_from_csv()
    except Exception as e:
        print(f"[WARN] Gagal pre-compute EDA: {e}")

    uvicorn.run(
        "main:app",
        host="0.0.0.0",
        port=8000,
        reload=True,
    )
