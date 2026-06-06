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

Catatan Akademis:
  Fitur yang tidak tersedia dari input user diisi menggunakan teknik
  median imputation dari dataset training (Prosper Marketplace).
  Hal ini memastikan model ML menerima distribusi yang konsisten
  dengan data pelatihan, dan variasi prediksi ditentukan oleh
  variabel yang memang dikontrol pemohon.
"""
import os
import sys
import numpy as np
import pandas as pd
import joblib
from schemas import PredictInput, PredictOutput

# Fix encoding untuk Windows
if sys.stdout.encoding != 'utf-8':
    sys.stdout.reconfigure(encoding='utf-8')


# ══════════════════════════════════════════════════════════════════════════
# PATH KE FILE MODEL (.pkl)
# ══════════════════════════════════════════════════════════════════════════

BASE_DIR   = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
MODEL_KLAS = os.path.join(BASE_DIR, "model_klasifikasi_loan.pkl")
MODEL_THR  = os.path.join(BASE_DIR, "threshold_tuned.pkl")
MODEL_REG  = os.path.join(BASE_DIR, "model_regresi_tuned_loan.pkl")
DATASET_CSV = os.path.join(BASE_DIR, "Dataset", "CLEANN_prosperloandata (1).csv")
if not os.path.exists(DATASET_CSV):
    DATASET_CSV = os.path.join(BASE_DIR, "Dataset", "prosperLoanData.csv")


# ══════════════════════════════════════════════════════════════════════════
# MEDIAN DATASET PROSPER MARKETPLACE
#
# Nilai-nilai di bawah ini adalah median dari dataset prosperLoanData.csv
# yang digunakan untuk training model. Jika file CSV tersedia saat
# startup, nilai ini akan di-overwrite dengan median yang dihitung
# langsung dari data aktual.
#
# Sumber fallback: Prosper Marketplace Loan Data (public dataset)
# ══════════════════════════════════════════════════════════════════════════

DEFAULT_MEDIANS = {
    # ── Skor kredit & rating ──
    "CreditScoreRangeLower"            : 680.0,
    "CreditScoreRangeUpper"            : 699.0,
    "ProsperScore"                     : 6.0,
    "ProsperRating (numeric)"          : 4.0,
    "ProsperRating (Alpha)"            : "C",      # kategorikal

    # ── Kartu kredit & revolving ──
    "BankcardUtilization"              : 0.54,
    "AvailableBankcardCredit"          : 8413.0,
    "OpenRevolvingMonthlyPayment"      : 298.0,
    "RevolvingCreditBalance"           : 7592.0,
    "OpenRevolvingAccounts"            : 7.0,

    # ── Riwayat kredit ──
    "CurrentCreditLines"               : 10.0,
    "OpenCreditLines"                  : 9.0,
    "TotalCreditLinespast7years"       : 26.0,
    "TotalTrades"                      : 26.0,
    "TradesNeverDelinquent (percentage)": 0.87,

    # ── Tunggakan & catatan publik ──
    "CurrentDelinquencies"             : 0.0,
    "DelinquenciesLast7Years"          : 0.0,
    "AmountDelinquent"                 : 0.0,
    "PublicRecordsLast10Years"         : 0.0,
    "PublicRecordsLast12Months"        : 0.0,

    # ── Inquiry ──
    "TotalInquiries"                   : 5.0,
    "InquiriesLast6Months"             : 1.0,

    # ── Lainnya ──
    "TradesOpenedLast6Months"          : 0.0,
    "IncomeVerifiable"                 : 1,

    # ── Pendapatan & DTI (fallback saja, biasanya di-override user) ──
    "StatedMonthlyIncome"              : 4667.0,
    "DebtToIncomeRatio"                : 0.22,
    "EmploymentStatusDuration"         : 96.0,   # bulan (~8 tahun)

    # ── Kategorikal (mode dataset) ──
    "EmploymentStatus"                 : "Employed",
    "IncomeRange"                      : "$25,000-49,999",
    "Occupation"                       : "Professional",
    "BorrowerState"                    : "CA",
    "IsBorrowerHomeowner"              : True,

    # ── Pinjaman ──
    "Term"                             : 36,
    "ListingCategory (numeric)"        : 1,       # Debt Consolidation
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
    "Modal Usaha"    : 3,   # Business
    "Pendidikan"     : 5,   # Student Use
    "Renovasi Rumah" : 2,   # Home Improvement
    "Kendaraan"      : 6,   # Auto
    "Kesehatan"      : 15,  # Medical/Dental
    "Lainnya"        : 7,   # Other
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
        # Suku bunga fallback default (median BorrowerRate dari dataset Prosper)
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

    # ------------------------------------------------------------------
    # LOAD MODELS
    # ------------------------------------------------------------------
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
            print(f"        Pastikan file .pkl ada di: {BASE_DIR}")
            self.models_loaded = False

    # ------------------------------------------------------------------
    # HITUNG MEDIAN DARI CSV (OPSIONAL)
    # ------------------------------------------------------------------
    def _try_compute_medians_from_csv(self):
        """
        Jika prosperLoanData.csv tersedia, hitung median aktual dari dataset.
        Ini lebih akurat daripada nilai default hardcoded.
        """
        if not os.path.exists(DATASET_CSV):
            print("[INFO] Dataset CSV tidak ditemukan, menggunakan median default")
            return

        try:
            print(f"[INFO] Menghitung median dari {DATASET_CSV} ...")
            df = pd.read_csv(DATASET_CSV, low_memory=False)

            # Kolom numerik yang perlu dihitung mediannya
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

            # Kolom kategorikal → mode (nilai yang paling sering muncul)
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

            # IsBorrowerHomeowner → boolean mode
            if "IsBorrowerHomeowner" in df.columns:
                mode_val = df["IsBorrowerHomeowner"].dropna().mode()
                if len(mode_val) > 0:
                    self.medians["IsBorrowerHomeowner"] = bool(mode_val.iloc[0])

            # Hitung median BorrowerRate dinamis berdasarkan ProsperRating (numeric) dari dataset
            if "ProsperRating (numeric)" in df.columns and "BorrowerRate" in df.columns:
                print("[INFO] Menghitung median suku bunga berdasarkan rating risk dari dataset...")
                rate_medians = df.groupby("ProsperRating (numeric)")["BorrowerRate"].median().to_dict()
                for rating, rate in rate_medians.items():
                    r_key = float(round(rating))
                    if r_key in [1.0, 2.0, 3.0, 4.0, 5.0, 6.0, 7.0]:
                        self.rating_rates[r_key] = float(rate)

            print(f"[OK] Median dihitung dari {len(df):,} baris dataset")

        except Exception as e:
            print(f"[WARN] Gagal menghitung median dari CSV: {e}")
            print("       Menggunakan median default sebagai fallback")

    # ------------------------------------------------------------------
    # PUBLIC: PREDICT
    # ------------------------------------------------------------------
    def predict(self, data: PredictInput) -> PredictOutput:
        """
        Prediksi kelayakan kredit nasabah.

        Alur:
        1. Ekstrak 8 field dari input user (Kredivo-style)
        2. Bangun 26 fitur klasifikasi (user input + median)
        3. Klasifikasi → LAYAK / TIDAK LAYAK
        4. Jika LAYAK → Bangun 41 fitur regresi → Plafon
        5. Hitung cicilan anuitas
        """
        if not self.models_loaded:
            raise RuntimeError(
                "Model belum di-load. Pastikan file .pkl ada di root project."
            )

        # ── A. Ekstrak input user ─────────────────────────────────────
        user = self._extract_user_input(data)

        # ── B. KLASIFIKASI (28 fitur) ─────────────────────────────────
        features = self._build_features(user)
        df_klas = pd.DataFrame([features])[self.pipe_klasifikasi.feature_names_in_]

        proba     = float(self.pipe_klasifikasi.predict_proba(df_klas)[0, 1])
        is_accept = proba >= self.threshold

        # ── C. REJECT ─────────────────────────────────────────────────
        if not is_accept:
            alasan = self._build_rejection_reasons(user)
            confidence = round((1 - proba) * 100, 1)

            return PredictOutput(
                result="TIDAK LAYAK",
                confidence=confidence,
                alasan_penolakan=alasan,
            )

        # ── D. REGRESI (28 fitur) → Plafon ───────────────────────────
        df_reg = pd.DataFrame([features])[self.model_regresi.feature_names_in_]

        plafon = int(np.round(self.model_regresi.predict(df_reg)[0]))
        plafon = max(1000, min(35000, plafon))  # clip ke batas sistem

        nominal = user["nominal"]

        # Jika nominal pengajuan melebihi plafon → REJECT
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

        # ── E. HITUNG CICILAN ANUITAS ─────────────────────────────────
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

        total_bayar = cicilan * tenor
        total_bunga = total_bayar - nominal_final
        sisa_plafon = plafon - nominal_final

        # ── F. CATATAN RISIKO ─────────────────────────────────────────
        catatan_risiko = self._build_risk_note(user, proba)

        confidence = round(proba * 100, 1)

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

    # ------------------------------------------------------------------
    # PRIVATE: Ekstrak Input User (8 Field Kredivo-style)
    # ------------------------------------------------------------------
    def _extract_user_input(self, data: PredictInput) -> dict:
        """
        Ekstrak data dari form frontend.
        Hanya 8 field yang diambil — sisanya akan diisi median.
        """
        # 1. Pendapatan bulanan
        gaji = max(0.0, float(data.monthlyIncome or "0"))
        tambahan = max(0.0, float(data.additionalIncome or "0"))

        # 2. Cicilan aktif → untuk menghitung DTI
        cicilan_aktif = max(0.0, float(data.existingInstallments or "0"))

        # 3. DTI = cicilan / pendapatan (murni, tanpa heuristik)
        total_income = gaji + tambahan
        dti = (cicilan_aktif / total_income) if total_income > 0 else 0.0
        dti = min(dti, 10.0)  # cap rasional, bukan heuristik

        # 4. Status pekerjaan → mapping ke format model
        employment = EMPLOYMENT_MAP.get(data.employment, "Other")
        occupation = OCCUPATION_MAP.get(data.employment, "Other")

        # 5. Lama bekerja (estimasi dari usia jika tersedia)
        age = max(18, int(data.age or "25"))
        lama_kerja = max(0.0, float((age - 20) * 12))  # estimasi kasar: mulai kerja ~20 tahun

        # 6. Jumlah pinjaman (nominal pengajuan)
        nominal = max(0.0, float(data.loanAmount or "0"))

        # 7. Tenor
        tenor = int(data.loanTerm or "36")

        # 8. Tujuan pinjaman → mapping ke kode numerik
        tujuan = LOAN_PURPOSE_MAP.get(data.loanPurpose, 7)

        # 9. Status tempat tinggal → mapping ke borrower state & homeowner
        punya_rumah = (data.propertyArea == "Urban")
        borrower_state = AREA_STATE_MAP.get(data.propertyArea, "CA")

        # 10. Income range (diturunkan dari gaji, ini format model)
        if gaji < 1667:
            income_range = "$1-24,999"
        elif gaji < 4167:
            income_range = "$25,000-49,999"
        elif gaji < 8333:
            income_range = "$50,000-74,999"
        else:
            income_range = "$75,000-99,999"

        return {
            "gaji"            : gaji,
            "total_income"    : total_income,
            "cicilan_aktif"   : cicilan_aktif,
            "dti"             : dti,
            "employment"      : employment,
            "occupation"      : occupation,
            "lama_kerja"      : lama_kerja,
            "nominal"         : nominal,
            "tenor"           : tenor,
            "tujuan"          : tujuan,
            "punya_rumah"     : punya_rumah,
            "borrower_state"  : borrower_state,
            "income_range"    : income_range,
        }

    # ------------------------------------------------------------------
    # PRIVATE: Bangun 28 Fitur yang Disepakati (Klasifikasi & Regresi)
    # ------------------------------------------------------------------
    def _build_features(self, user: dict) -> dict:
        """
        Bangun 28 fitur murni (tanpa rekayasa) untuk model klasifikasi dan regresi.
        """
        m = self.medians
        gaji = user["gaji"]

        return {
            # ── Kolom Kategorikal (5) ──
            "EmploymentStatus"                   : user["employment"],
            "Occupation"                         : user["occupation"],
            "BorrowerState"                      : user["borrower_state"],
            "ProsperRating (Alpha)"              : m.get("ProsperRating (Alpha)", "C"),
            "IncomeRange"                        : user["income_range"],

            # ── Kolom Numerikal (23) ──
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
            "AvailableBankcardCredit"             : m.get("AvailableBankcardCredit", 8000.0),
            "RevolvingCreditBalance"             : m.get("RevolvingCreditBalance", 7000.0),
            "TradesNeverDelinquent (percentage)" : m.get("TradesNeverDelinquent (percentage)", 0.87),
            "CurrentDelinquencies"               : m.get("CurrentDelinquencies", 0.0),
            "DelinquenciesLast7Years"            : m.get("DelinquenciesLast7Years", 0.0)
        }


    # ------------------------------------------------------------------
    # PRIVATE: Suku Bunga Berdasarkan Tenor
    # ------------------------------------------------------------------
    @staticmethod
    def _get_interest_rate(tenor: int) -> float:
        """Suku bunga tahunan berdasarkan tenor pinjaman."""
        if tenor <= 12:
            return 0.08   # 8% per tahun
        elif tenor <= 36:
            return 0.15   # 15% per tahun
        else:
            return 0.22   # 22% per tahun

    def _get_interest_rate_by_risk(self, proba: float) -> float:
        """Suku bunga tahunan dinamis berdasarkan probabilitas kelayakan nasabah (Risk-Based Pricing)."""
        # Rentang probabilitas kelayakan dibagi menjadi 7 tier (makin besar proba, rating makin besar, bunga makin murah)
        if proba >= 0.90:
            rating = 7.0  # Sangat aman (AA)
        elif proba >= 0.80:
            rating = 6.0  # Aman (A)
        elif proba >= 0.70:
            rating = 5.0  # Layak Atas (B)
        elif proba >= 0.60:
            rating = 4.0  # Layak Menengah (C)
        elif proba >= 0.50:
            rating = 3.0  # Cukup Berisiko (D)
        elif proba >= 0.40:
            rating = 2.0  # Berisiko (E)
        else:
            rating = 1.0  # Sangat Berisiko (HR)
            
        # Ambil rate dari dictionary rating_rates yang dihitung dari dataset
        return self.rating_rates.get(rating, 0.1914)  # default C (19.14%)

    # ------------------------------------------------------------------
    # PRIVATE: Alasan Penolakan
    # ------------------------------------------------------------------
    @staticmethod
    def _build_rejection_reasons(user: dict) -> list[str]:
        """
        Bangun daftar alasan penolakan berdasarkan input user.
        Hanya menggunakan data yang memang diisi user, TANPA heuristik.
        """
        alasan = []

        # Pendapatan terlalu rendah
        if user["gaji"] < 300:
            alasan.append(
                f"Pendapatan bulanan (${user['gaji']:,.0f}) belum memenuhi "
                f"batas minimum persyaratan ($300)"
            )

        # DTI terlalu tinggi
        if user["dti"] > 0.50:
            alasan.append(
                f"Rasio hutang terhadap pendapatan (DTI) terlalu tinggi "
                f"({user['dti']:.0%}). Batas aman umumnya di bawah 50%."
            )

        # Tidak bekerja
        if user["employment"] == "Not employed":
            alasan.append(
                "Status pekerjaan saat ini belum memenuhi kriteria kelayakan"
            )

        # Jika tidak ada alasan spesifik, tampilkan pesan umum
        if not alasan:
            alasan.append(
                "Berdasarkan analisis model ML, profil Anda belum memenuhi "
                "kriteria kelayakan minimum saat ini"
            )

        return alasan

    # ------------------------------------------------------------------
    # PRIVATE: Catatan Risiko
    # ------------------------------------------------------------------
    @staticmethod
    def _build_risk_note(user: dict, proba: float) -> str:
        """
        Catatan risiko berdasarkan probabilitas model dan DTI user.
        """
        if proba >= 0.85 and user["dti"] < 0.30:
            return "Profil sangat sehat — risiko sangat rendah"
        elif proba >= 0.70:
            return "Profil sehat — risiko rendah"
        elif proba >= 0.50:
            return "Profil cukup — risiko sedang"
        else:
            return "Profil memenuhi batas minimum — monitor risiko disarankan"
