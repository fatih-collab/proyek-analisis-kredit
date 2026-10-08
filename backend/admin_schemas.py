"""
admin_schemas.py — Pydantic models untuk Admin API
"""
from pydantic import BaseModel
from typing import Optional, List, Literal


class AdminLoginRequest(BaseModel):
    email: str
    password: str


class AdminLoginResponse(BaseModel):
    success: bool
    token: Optional[str] = None
    error: Optional[str] = None


class UserInfo(BaseModel):
    id: str
    fullName: str
    email: str
    createdAt: str
    profileCompleted: bool = False
    predictionCount: int = 0


class PredictionInfo(BaseModel):
    id: str
    userId: str
    userName: str
    date: str
    loanAmount: str
    loanTerm: str
    result: Literal["LAYAK", "TIDAK LAYAK"]
    confidence: float
    loanPurpose: str = ""
    creditHistory: str = ""
    plafon: Optional[int] = None
    cicilanPerBulan: Optional[float] = None
    alasanPenolakan: Optional[List[str]] = None


class BulkDataRequest(BaseModel):
    """Data yang dikirim dari frontend (localStorage) ke backend admin"""
    users: List[dict]
    predictions: List[dict]


class EDAStats(BaseModel):
    totalUsers: int = 0
    totalPredictions: int = 0
    layakCount: int = 0
    tidakLayakCount: int = 0
    approvalRate: float = 0.0
    avgConfidence: float = 0.0

    # Distribusi
    loanPurposeDistribution: dict = {}
    creditHistoryDistribution: dict = {}
    propertyAreaDistribution: dict = {}
    employmentDistribution: dict = {}
    resultByPurpose: dict = {}
    loanAmountRanges: dict = {}
    confidenceDistribution: List[dict] = []
    dailyTrend: List[dict] = []


# ══════════════════════════════════════════════════════════════════════════
# NEW: Response models untuk EDA dari dataset CSV & prediction logs
# ══════════════════════════════════════════════════════════════════════════

class DatasetEDAResponse(BaseModel):
    """EDA statistik yang dihitung dari prosperLoanData.csv"""
    totalRecords: int = 0

    # Summary stats
    avgMonthlyIncome: float = 0.0
    medianMonthlyIncome: float = 0.0
    avgDTI: float = 0.0
    medianDTI: float = 0.0
    avgCreditScore: float = 0.0
    avgLoanAmount: float = 0.0
    medianLoanAmount: float = 0.0
    minLoanAmount: float = 0.0
    maxLoanAmount: float = 0.0

    # Distribusi
    loanStatusDistribution: dict = {}
    termDistribution: dict = {}
    prosperRatingDistribution: dict = {}
    employmentDistribution: dict = {}
    incomeRangeDistribution: dict = {}
    occupationTop10: dict = {}
    borrowerStateTop10: dict = {}
    creditScoreRanges: dict = {}
    listingCategoryDistribution: dict = {}
    homeownerDistribution: dict = {}

    # Histogram data
    dtiHistogram: List[dict] = []
    creditScoreHistogram: List[dict] = []
    loanAmountHistogram: List[dict] = []
    monthlyIncomeHistogram: List[dict] = []

    # Time series
    loansByYear: List[dict] = []
    loansByYearMonth: List[dict] = []


class PredictionLogEntry(BaseModel):
    """Single prediction log entry"""
    id: str = ""
    timestamp: str = ""
    result: str = ""
    confidence: float = 0.0
    plafon: Optional[int] = None
    cicilanPerBulan: Optional[float] = None
    alasanPenolakan: Optional[List[str]] = None
    catatanRisiko: Optional[str] = None
    loanAmount: str = "0"
    loanTerm: str = "36"
    loanPurpose: str = ""
    employment: str = ""
    propertyArea: str = ""
    fullName: Optional[str] = ""
    email: Optional[str] = ""
    phone: Optional[str] = ""
    address: Optional[str] = ""


class PredictionLogsResponse(BaseModel):
    """Response for admin prediction logs endpoint"""
    total: int = 0
    predictions: List[PredictionLogEntry] = []
