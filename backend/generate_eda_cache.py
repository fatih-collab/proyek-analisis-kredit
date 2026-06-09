import os
import json
import pandas as pd
import numpy as np

# Set paths
BACKEND_DIR = os.path.dirname(os.path.abspath(__file__))
BASE_DIR = os.path.dirname(BACKEND_DIR)
DATASET_PATH = os.path.join(BASE_DIR, "Dataset", "prosperloandata_28_fitur_large.csv")
if not os.path.exists(DATASET_PATH):
    DATASET_PATH = os.path.join(BASE_DIR, "prosperloandata_28_fitur_small.csv")

CACHE_PATH = os.path.join(BACKEND_DIR, "eda_cache.json")

def generate_cache():
    if not os.path.exists(DATASET_PATH):
        print(f"[ERROR] Dataset tidak ditemukan di: {DATASET_PATH}")
        return

    print(f"[INFO] Membaca dataset dari: {DATASET_PATH} ...")
    df = pd.read_csv(DATASET_PATH, low_memory=False)
    if "IncomeRange" in df.columns:
        df["IncomeRange"] = df["IncomeRange"].replace("Not displayed", "$25,000-49,999")
    print(f"[OK] Dataset loaded: {len(df)} baris")

    total = len(df)
    eda = {"totalRecords": total}

    if "StatedMonthlyIncome" in df.columns:
        income = pd.to_numeric(df["StatedMonthlyIncome"], errors="coerce").dropna()
        eda["avgMonthlyIncome"] = round(float(income.mean()), 2)
        eda["medianMonthlyIncome"] = round(float(income.median()), 2)

    if "DebtToIncomeRatio" in df.columns:
        dti = pd.to_numeric(df["DebtToIncomeRatio"], errors="coerce").dropna()
        eda["avgDTI"] = round(float(dti.mean()), 4)
        eda["medianDTI"] = round(float(dti.median()), 4)

    if "CreditScoreRangeLower" in df.columns:
        cs = pd.to_numeric(df["CreditScoreRangeLower"], errors="coerce").dropna()
        eda["avgCreditScore"] = round(float(cs.mean()), 1)

    loan_col = None
    for col_name in ["LoanOriginalAmount", "AmountBorrowed"]:
        if col_name in df.columns:
            loan_col = col_name
            break

    if loan_col:
        la = pd.to_numeric(df[loan_col], errors="coerce").dropna()
        eda["avgLoanAmount"] = round(float(la.mean()), 2)
        eda["medianLoanAmount"] = round(float(la.median()), 2)
        eda["minLoanAmount"] = round(float(la.min()), 2)
        eda["maxLoanAmount"] = round(float(la.max()), 2)
        bins = [0, 2000, 5000, 10000, 15000, 20000, 25000, 35000, 100000]
        labels = ["$0-2k", "$2k-5k", "$5k-10k", "$10k-15k", "$15k-20k", "$20k-25k", "$25k-35k", "$35k+"]
        cuts = pd.cut(la, bins=bins, labels=labels, right=False)
        dist = cuts.value_counts().sort_index()
        eda["loanAmountHistogram"] = [{"label": str(k), "value": int(v)} for k, v in dist.items()]

    if "LoanStatus" in df.columns:
        eda["loanStatusDistribution"] = {str(k): int(v) for k, v in df["LoanStatus"].value_counts().head(10).items()}

    if "Term" in df.columns:
        eda["termDistribution"] = {str(k): int(v) for k, v in df["Term"].value_counts().items()}

    if "ProsperRating (Alpha)" in df.columns:
        pr = df["ProsperRating (Alpha)"].dropna().value_counts().sort_index()
        eda["prosperRatingDistribution"] = {str(k): int(v) for k, v in pr.items()}

    if "EmploymentStatus" in df.columns:
        eda["employmentDistribution"] = {str(k): int(v) for k, v in df["EmploymentStatus"].value_counts().head(10).items()}

    if "IncomeRange" in df.columns:
        eda["incomeRangeDistribution"] = {str(k): int(v) for k, v in df["IncomeRange"].value_counts().items()}

    if "Occupation" in df.columns:
        eda["occupationTop10"] = {str(k): int(v) for k, v in df["Occupation"].value_counts().head(10).items()}

    if "BorrowerState" in df.columns:
        eda["borrowerStateTop10"] = {str(k): int(v) for k, v in df["BorrowerState"].value_counts().head(10).items()}

    if "IsBorrowerHomeowner" in df.columns:
        eda["homeownerDistribution"] = {str(k): int(v) for k, v in df["IsBorrowerHomeowner"].value_counts().items()}

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
        eda["listingCategoryDistribution"] = {str(k): int(v) for k, v in lc_named.value_counts().head(10).items()}

    if "CreditScoreRangeLower" in df.columns:
        cs = pd.to_numeric(df["CreditScoreRangeLower"], errors="coerce").dropna()
        bins_cs = [0, 500, 550, 600, 650, 700, 750, 800, 900]
        labels_cs = ["<500", "500-549", "550-599", "600-649", "650-699", "700-749", "750-799", "800+"]
        cuts_cs = pd.cut(cs, bins=bins_cs, labels=labels_cs, right=False)
        dist_cs = cuts_cs.value_counts().sort_index()
        eda["creditScoreHistogram"] = [{"label": str(k), "value": int(v)} for k, v in dist_cs.items()]
        eda["creditScoreRanges"] = {str(k): int(v) for k, v in dist_cs.items()}

    if "DebtToIncomeRatio" in df.columns:
        dti = pd.to_numeric(df["DebtToIncomeRatio"], errors="coerce").dropna()
        dti_clipped = dti.clip(upper=2.0)
        bins_dti = [0, 0.1, 0.2, 0.3, 0.4, 0.5, 0.75, 1.0, 2.0]
        labels_dti = ["0-10%", "10-20%", "20-30%", "30-40%", "40-50%", "50-75%", "75-100%", "100%+"]
        cuts_dti = pd.cut(dti_clipped, bins=bins_dti, labels=labels_dti, right=False)
        dist_dti = cuts_dti.value_counts().sort_index()
        eda["dtiHistogram"] = [{"label": str(k), "value": int(v)} for k, v in dist_dti.items()]

    if "StatedMonthlyIncome" in df.columns:
        inc = pd.to_numeric(df["StatedMonthlyIncome"], errors="coerce").dropna()
        inc_clipped = inc.clip(upper=25000)
        bins_inc = [0, 2000, 4000, 6000, 8000, 10000, 15000, 25000]
        labels_inc = ["$0-2k", "$2k-4k", "$4k-6k", "$6k-8k", "$8k-10k", "$10k-15k", "$15k+"]
        cuts_inc = pd.cut(inc_clipped, bins=bins_inc, labels=labels_inc, right=False)
        dist_inc = cuts_inc.value_counts().sort_index()
        eda["monthlyIncomeHistogram"] = [{"label": str(k), "value": int(v)} for k, v in dist_inc.items()]

    date_col = None
    for col_name in ["ListingCreationDate", "LoanOriginationDate", "DateCreditPulled"]:
        if col_name in df.columns:
            date_col = col_name
            break

    if date_col:
        dates = pd.to_datetime(df[date_col], errors="coerce").dropna()
        by_year = dates.dt.year.value_counts().sort_index()
        eda["loansByYear"] = [{"label": str(int(k)), "value": int(v)} for k, v in by_year.items()]
        by_ym = dates.dt.to_period("M").value_counts().sort_index().tail(36)
        eda["loansByYearMonth"] = [{"label": str(k), "value": int(v)} for k, v in by_ym.items()]

    # Save to file
    with open(CACHE_PATH, "w") as f:
        json.dump(eda, f, indent=2)
    print(f"[OK] Cache EDA berhasil disimpan ke: {CACHE_PATH}")

if __name__ == "__main__":
    generate_cache()
