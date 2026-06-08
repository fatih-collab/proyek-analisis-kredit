"""
predictor.py — Mesin Prediksi Kelayakan Kredit

Arsitektur (Kredivo-style):
  - 8 field diisi user di frontend (pendapatan, cicilan, pekerjaan, dll)
  - Sisanya diisi MEDIAN dari dataset Prosper Marketplace (median imputation)
  - Model ML memprediksi berdasarkan gabungan keduanya
  - TANPA heuristic rules / hierarchical rules sama sekali

Alur:
  1. Ekstrak 8 field dari input user
  2. Bangun feature vector (user input + median imputation)
  3. Klasifikasi (imblearn Pipeline, 26 fitur) → LAYAK / TIDAK LAYAK
  4. Jika LAYAK → Regresi (sklearn Pipeline, 41 fitur) → Plafon maksimal
  5. Hitung cicilan anuitas
"""
import os
import sys
import numpy as np
import pandas as pd
import joblib
from schemas import PredictInput, PredictOutput

# CATATAN: sys.stdout.reconfigure TIDAK dipanggil di sini.
# Set PYTHONIOENCODING=utf-8 di Dockerfile sebagai gantinya.


# ══════════════════════════════════════════════════════════════════════════
# PATH KE FILE MODEL (.pkl)
# ══════════════════════════════════════════════════════════════════════════

<<<<<<< HEAD
BASE_DIR   = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
=======
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

>>>>>>> 8247c49 (Menyambungkan ke supabase)
def _find_model(filename: str) -> str:
    """Cari file model di beberapa lokasi."""
    candidates = [
        os.path.join("/app/models", filename),              # Docker container
        os.path.join(BASE_DIR, filename),                   # Local dev (parent dir)
        os.path.join(os.path.dirname(os.path.abspath(__file__)), filename),  # Same dir
    ]
    for path in candidates:
        if os.path.exists(path):
            print(f"[OK] Model ditemukan: {path}")
            return path
    print(f"[WARN] Model tidak ditemukan di semua lokasi: {filename}")
    return os.path.join("/app/models", filename)  # Fallback ke Docker path

MODEL_KLAS = _find_model("model_klasifikasi_loan.pkl")
MODEL_THR  = _find_model("threshold_tuned.pkl")
MODEL_REG  = _find_model("model_regresi_tuned_loan.pkl")

# Dataset CSV — opsional, untuk median computation
DATASET_CSV = os.path.join(BASE_DIR, "Dataset", "prosperloandata_28_fitur_large.csv")
if not os.path.exists(DATASET_CSV):
    DATASET_CSV = os.path.join(BASE_DIR, "prosperloandata_28_fitur_small.csv")


# ══════════════════════════════════════════════════════════════════════════
# MEDIAN DATASET PROSPER MARKETPLACE
# ══════════════════════════════════════════════════════════════════════════

DEFAULT_MEDIANS = {
    "CreditScoreRangeLower"             : 680.0,
    "CreditScoreRangeUpper"             : 699.0,
    "ProsperScore"                      : 6.0,
    "ProsperRating (numeric)"           : 4.0,
    "ProsperRating (Alpha)"             : "C",
    "BankcardUtilization"               : 0.54,
    "AvailableBankcardCredit"           : 8413.0,
    "OpenRevolvingMonthlyPayment"       : 298.0,
    "RevolvingCreditBalance"            : 7592.0,
    "OpenRevolvingAccounts"             : 7.0,
    "CurrentCreditLines"                : 10.0,
    "OpenCreditLines"                   : 9.0,
    "TotalCreditLinespast7years"        : 26.0,
    "TotalTrades"                       : 26.0,
    "TradesNeverDelinquent (percentage)": 0.87,
    "CurrentDelinquencies"              : 0.0,
    "DelinquenciesLast7Years"           : 0.0,
    "AmountDelinquent"                  : 0.0,
    "PublicRecordsLast10Years"          : 0.0,
    "PublicRecordsLast12Months"         : 0.0,
    "TotalInquiries"                    : 5.0,
    "InquiriesLast6Months"              : 1.0,
    "TradesOpenedLast6Months"           : 0.0,
    "IncomeVerifiable"                  : 1,
    "StatedMonthlyIncome"               : 4667.0,
    "DebtToIncomeRatio"                 : 0.22,
    "EmploymentStatusDuration"          : 96.0,
    "EmploymentStatus"                  : "Employed",
    "IncomeRange"                       : "$25,000-49,999",
    "Occupation"                        : "Professional",
    "BorrowerState"                     : "CA",
    "IsBorrowerHomeowner"               : True,
    "Term"                              : 36,
    "ListingCategory (numeric)"         : 1,
}


# ══════════════════════════════════════════════════════════════════════════
# MAPPING FRONTEND → FORMAT MODEL
# ══════════════════════════════════════════════════════════════════════════

EMPLOYMENT_MAP = {
    "PNS"              : "Employed",
    "Karyawan Swasta"  : "Employed",
    "Wiraswasta"       : "Self-employed",
    "Freelancer"       : "Self-employed",
    "Tidak Bekerja"    : "Not employed",
    "Ibu Rumah Tangga" : "Not employed",
    "Mahasiswa"        : "Not employed",
}

OCCUPATION_MAP = {
    "PNS"              : "Government",
    "Karyawan Swasta"  : "Professional",
    "Wiraswasta"       : "Self Employed",
    "Freelancer"       : "Other",
    "Tidak Bekerja"    : "Other",
    "Ibu Rumah Tangga" : "Homemaker",
    "Mahasiswa"        : "Student",
}

LOAN_PURPOSE_MAP = {
    "Modal Usaha"    : 3,
    "Pendidikan"     : 5,
    "Renovasi Rumah" : 2,
    "Kendaraan"      : 6,
    "Kesehatan"      : 15,
    "Lainnya"        : 7,
}

AREA_STATE_MAP = {
    "Urban"     : "CA",
    "Semiurban" : "TX",
    "Rural"     : "GA",
}


# ══════════════════════════════════════════════════════════════════════════
# PREDICTOR CLASS
# ══════════════════════════════════════════════════════════════════════════

class Predictor:
    def __init__(self):
        self.models_loaded = False
        self.medians = dict(DEFAULT_MEDIANS)
        self.rating_rates = {
            7.0: 0.0779,
            6.0: 0.1119,
            5.0: 0.1509,
            4.0: 0.1914,
            3.0: 0.2492,
            2.0: 0.2925,
            1.0: 0.3177
        }
        self._load_models()
        self._try_compute_medians_from_csv()

    def _load_models(self):
        """Load semua model .pkl saat startup."""
        try:
            self.pipe_klasifikasi = joblib.load(MODEL_KLAS)
            self.threshold        = joblib.load(MODEL_THR)
            self.model_regresi    = joblib.load(MODEL_REG)
            self.models_loaded    = True
            print("[OK] Semua model berhasil di-load")
            print(f"     Threshold klasifikasi : {self.threshold:.4f}")
            print(f"     Fitur klasifikasi     : {len(self.pipe_klasifikasi.feature_names_in_)}")
            print(f"     Fitur regresi         : {len(self.model_regresi.feature_names_in_)}")
        except FileNotFoundError as e:
            print(f"[ERROR] Model tidak ditemukan: {e}")
            print(f"        Pastikan .pkl ada di /app/models/ (Docker) atau {BASE_DIR} (lokal)")
            self.models_loaded = False
        except Exception as e:
            print(f"[ERROR] Gagal load model: {e}")
            self.models_loaded = False

    def _try_compute_medians_from_csv(self):
        if not os.path.exists(DATASET_CSV):
            print("[INFO] Dataset CSV tidak ditemukan, menggunakan median default")
            return

        try:
            print(f"[INFO] Menghitung median dari {DATASET_CSV} ...")
            df = pd.read_csv(DATASET_CSV, low_memory=False)
            if "IncomeRange" in df.columns:
                df["IncomeRange"] = df["IncomeRange"].replace("Not displayed", "$25,000-49,999")

            numeric_cols = [
                "CreditScoreRangeLower", "CreditScoreRangeUpper",
                "ProsperScore", "ProsperRating (numeric)",
                "BankcardUtilization", "AvailableBankcardCredit",
                "OpenRevolvingMonthlyPayment", "RevolvingCreditBalance",
                "OpenRevolvingAccounts", "CurrentCreditLines", "OpenCreditLines",
                "TotalCreditLinespast7years", "TotalTrades",
                "TradesNeverDelinquent (percentage)",
                "CurrentDelinquencies", "DelinquenciesLast7Years",
                "AmountDelinquent", "PublicRecordsLast10Years",
                "PublicRecordsLast12Months",
                "TotalInquiries", "InquiriesLast6Months",
                "TradesOpenedLast6Months", "EmploymentStatusDuration",
                "StatedMonthlyIncome", "DebtToIncomeRatio",
            ]
            for col in numeric_cols:
                if col in df.columns:
                    val = pd.to_numeric(df[col], errors="coerce").dropna().median()
                    if not np.isnan(val):
                        self.medians[col] = float(val)

            cat_cols = {
                "ProsperRating (Alpha)": "C",
                "EmploymentStatus": "Employed",
                "IncomeRange": "$25,000-49,999",
                "Occupation": "Professional",
                "BorrowerState": "CA",
            }
            for col, fallback in cat_cols.items():
                if col in df.columns:
                    mode_series = df[col].dropna().mode()
                    if len(mode_series) > 0:
                        self.medians[col] = str(mode_series.iloc[0])

            if "IsBorrowerHomeowner" in df.columns:
                mode_val = df["IsBorrowerHomeowner"].dropna().mode()
                if len(mode_val) > 0:
                    self.medians["IsBorrowerHomeowner"] = bool(mode_val.iloc[0])

            if "ProsperRating (numeric)" in df.columns and "BorrowerRate" in df.columns:
                rate_medians = df.groupby("ProsperRating (numeric)")["BorrowerRate"].median().to_dict()
                for rating, rate in rate_medians.items():
                    r_key = float(round(rating))
                    if r_key in [1.0, 2.0, 3.0, 4.0, 5.0, 6.0, 7.0]:
                        self.rating_rates[r_key] = float(rate)

            print(f"[OK] Median dihitung dari {len(df):,} baris dataset")

        except Exception as e:
            print(f"[WARN] Gagal menghitung median dari CSV: {e}")
            print("       Menggunakan median default sebagai fallback")

    def predict(self, data: PredictInput) -> PredictOutput:
        if not self.models_loaded:
            raise RuntimeError(
                "Model belum di-load. Pastikan file .pkl ada di /app/models/"
            )

        user = self._extract_user_input(data)

        # ── KLASIFIKASI ───────────────────────────────────────────────
        features = self._build_features(user)
        df_klas = pd.DataFrame([features])[self.pipe_klasifikasi.feature_names_in_]

        proba     = float(self.pipe_klasifikasi.predict_proba(df_klas)[0, 1])
        is_accept = proba >= self.threshold

        if not is_accept:
            alasan = self._build_rejection_reasons(user)
            confidence = round((1 - proba) * 100, 1)
            return PredictOutput(
                result="TIDAK LAYAK",
                confidence=confidence,
                alasan_penolakan=alasan,
            )

        # ── REGRESI → Plafon ──────────────────────────────────────────
        df_reg = pd.DataFrame([features])[self.model_regresi.feature_names_in_]
        plafon = int(np.round(self.model_regresi.predict(df_reg)[0]))
        plafon = max(1000, min(35000, plafon))

        nominal = user["nominal"]
        if nominal > plafon:
            return PredictOutput(
                result="TIDAK LAYAK",
                confidence=95.0,
                alasan_penolakan=[
                    f"Nominal pengajuan (${nominal:,.0f}) melebihi limit kredit "
                    f"maksimal Anda (${plafon:,.0f}). "
                    f"Silakan ajukan nominal di bawah limit Anda."
                ],
            )

        # ── HITUNG CICILAN ANUITAS ─────────────────────────────────────
        tenor = user["tenor"]
        bunga = self._get_interest_rate_by_risk(proba)
        nominal_final = nominal

        bunga_per_bulan = bunga / 12
        if bunga_per_bulan > 0 and tenor > 0:
            cicilan = nominal_final * (
                bunga_per_bulan * (1 + bunga_per_bulan) ** tenor
            ) / ((1 + bunga_per_bulan) ** tenor - 1)
        else:
            cicilan = nominal_final / tenor if tenor > 0 else nominal_final

        total_bayar   = cicilan * tenor
        total_bunga   = total_bayar - nominal_final
        sisa_plafon   = plafon - nominal_final
        catatan_risiko = self._build_risk_note(user, proba)
        confidence    = round(proba * 100, 1)

        return PredictOutput(
            result="LAYAK",
            confidence=confidence,
            plafon=plafon,
            bunga_persen=f"{bunga * 100:.0f}%",
            bunga_rate=bunga,
            cicilan_per_bulan=round(cicilan, 2),
            total_bunga=round(total_bunga, 2),
            total_bayar=round(total_bayar, 2),
            sisa_plafon=round(sisa_plafon, 2),
            catatan_risiko=catatan_risiko,
            nominal_dicairkan=int(nominal_final),
        )

    def _extract_user_input(self, data: PredictInput) -> dict:
        gaji        = max(0.0, float(data.monthlyIncome or "0"))
        tambahan    = max(0.0, float(data.additionalIncome or "0"))
        cicilan_aktif = max(0.0, float(data.existingInstallments or "0"))
        total_income = gaji + tambahan
        dti = (cicilan_aktif / total_income) if total_income > 0 else 0.0
        dti = min(dti, 10.0)

        employment    = EMPLOYMENT_MAP.get(data.employment, "Other")
        occupation    = OCCUPATION_MAP.get(data.employment, "Other")
        age           = max(18, int(data.age or "25"))
        lama_kerja    = max(0.0, float((age - 20) * 12))
        nominal       = max(0.0, float(data.loanAmount or "0"))
        tenor         = int(data.loanTerm or "36")
        tujuan        = LOAN_PURPOSE_MAP.get(data.loanPurpose, 7)
        punya_rumah   = (data.propertyArea == "Urban")
        borrower_state = AREA_STATE_MAP.get(data.propertyArea, "CA")

        if gaji < 1667:
            income_range = "$1-24,999"
        elif gaji < 4167:
            income_range = "$25,000-49,999"
        elif gaji < 8333:
            income_range = "$50,000-74,999"
        else:
            income_range = "$75,000-99,999"

        return {
            "gaji"          : gaji,
            "total_income"  : total_income,
            "cicilan_aktif" : cicilan_aktif,
            "dti"           : dti,
            "employment"    : employment,
            "occupation"    : occupation,
            "lama_kerja"    : lama_kerja,
            "nominal"       : nominal,
            "tenor"         : tenor,
            "tujuan"        : tujuan,
            "punya_rumah"   : punya_rumah,
            "borrower_state": borrower_state,
            "income_range"  : income_range,
        }

    def _build_features(self, user: dict) -> dict:
        m    = self.medians
        gaji = user["gaji"]
        return {
            "EmploymentStatus"                   : user["employment"],
            "Occupation"                         : user["occupation"],
            "BorrowerState"                      : user["borrower_state"],
            "ProsperRating (Alpha)"              : m.get("ProsperRating (Alpha)", "C"),
            "IncomeRange"                        : user["income_range"],
            "Term"                               : user["tenor"],
            "ListingCategory (numeric)"          : user["tujuan"],
            "EmploymentStatusDuration"           : user["lama_kerja"],
            "StatedMonthlyIncome"                : gaji,
            "DebtToIncomeRatio"                  : round(user["dti"], 4),
            "IsBorrowerHomeowner"                : int(user["punya_rumah"]),
            "IncomeVerifiable"                   : int(m.get("IncomeVerifiable", 1.0)),
            "CreditScoreRangeLower"              : m.get("CreditScoreRangeLower", 680.0),
            "CreditScoreRangeUpper"              : m.get("CreditScoreRangeUpper", 699.0),
            "ProsperScore"                       : m.get("ProsperScore", 6.0),
            "ProsperRating (numeric)"            : m.get("ProsperRating (numeric)", 4.0),
            "CurrentCreditLines"                 : m.get("CurrentCreditLines", 10.0),
            "OpenCreditLines"                    : m.get("OpenCreditLines", 9.0),
            "TotalCreditLinespast7years"         : m.get("TotalCreditLinespast7years", 26.0),
            "TotalTrades"                        : m.get("TotalTrades", 26.0),
            "OpenRevolvingAccounts"              : m.get("OpenRevolvingAccounts", 7.0),
            "OpenRevolvingMonthlyPayment"        : m.get("OpenRevolvingMonthlyPayment", 300.0),
            "BankcardUtilization"                : m.get("BankcardUtilization", 0.48),
            "AvailableBankcardCredit"            : m.get("AvailableBankcardCredit", 8000.0),
            "RevolvingCreditBalance"             : m.get("RevolvingCreditBalance", 7000.0),
            "TradesNeverDelinquent (percentage)" : m.get("TradesNeverDelinquent (percentage)", 0.87),
            "CurrentDelinquencies"               : m.get("CurrentDelinquencies", 0.0),
            "DelinquenciesLast7Years"            : m.get("DelinquenciesLast7Years", 0.0),
        }

    @staticmethod
    def _get_interest_rate(tenor: int) -> float:
        if tenor <= 12:
            return 0.08
        elif tenor <= 36:
            return 0.15
        else:
            return 0.22

    def _get_interest_rate_by_risk(self, proba: float) -> float:
        if proba >= 0.90:   rating = 7.0
        elif proba >= 0.80: rating = 6.0
        elif proba >= 0.70: rating = 5.0
        elif proba >= 0.60: rating = 4.0
        elif proba >= 0.50: rating = 3.0
        elif proba >= 0.40: rating = 2.0
        else:               rating = 1.0
        return self.rating_rates.get(rating, 0.1914)

    @staticmethod
    def _build_rejection_reasons(user: dict) -> list:
        alasan = []
        if user["gaji"] < 300:
            alasan.append(
                f"Pendapatan bulanan (${user['gaji']:,.0f}) belum memenuhi "
                f"batas minimum persyaratan ($300)"
            )
        if user["dti"] > 0.50:
            alasan.append(
                f"Rasio hutang terhadap pendapatan (DTI) terlalu tinggi "
                f"({user['dti']:.0%}). Batas aman umumnya di bawah 50%."
            )
        if user["employment"] == "Not employed":
            alasan.append(
                "Status pekerjaan saat ini belum memenuhi kriteria kelayakan"
            )
        if not alasan:
            alasan.append(
                "Berdasarkan analisis model ML, profil Anda belum memenuhi "
                "kriteria kelayakan minimum saat ini"
            )
        return alasan

    @staticmethod
    def _build_risk_note(user: dict, proba: float) -> str:
        if proba >= 0.85 and user["dti"] < 0.30:
            return "Profil sangat sehat — risiko sangat rendah"
        elif proba >= 0.70:
            return "Profil sehat — risiko rendah"
        elif proba >= 0.50:
            return "Profil cukup — risiko sedang"
        else:
            return "Profil memenuhi batas minimum — monitor risiko disarankan"
