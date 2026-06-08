# 🛡️ CreditCare - MLOps Loan Predictor & Credit Risk System

Aplikasi web full-stack untuk prediksi kelayakan kredit (*Credit Scoring*) dan penentuan batas aman pinjaman (*Plafon Limit*) berbasis Machine Learning. Proyek ini dibangun menggunakan arsitektur MLOps modern yang dapat dideploy secara kontainerisasi.

---

## 🚀 Fitur Utama
- **Klasifikasi Risiko Kredit**: Memprediksi kelayakan nasabah (*LAYAK / TIDAK LAYAK*) menggunakan LightGBM Classifier dengan threshold optimal **0.5200**.
- **Regresi Plafon Kredit**: Menentukan batas maksimal limit pinjaman (*Plafon*) menggunakan LightGBM Regressor.
- **Explainable AI (XAI)**: Sistem otomatis penolakan jika nominal pengajuan melampaui plafon limit aman.
- **Dashboard Admin & Monitoring**: Panel visualisasi EDA dan log hasil prediksi dari database secara real-time.
- **Personal User Dashboard**: Histori riwayat prediksi dan ringkasan data kelayakan nasabah secara individual.

---

## 🛠️ Tech Stack
- **Frontend**: Next.js (React + TypeScript + TailwindCSS)
- **Backend**: FastAPI (Python 3.12 + Scikit-Learn + LightGBM)
- **Database**: Supabase / PostgreSQL (Cloud Database)
- **Containerization**: Docker & Docker Compose
- **Hosting / Deployment**: Railway

---

## 💻 Panduan Instalasi & Menjalankan Aplikasi

Pastikan Anda telah menginstal **Python 3.10+**, **Node.js 18+**, dan **Docker** (jika menggunakan kontainer).

### 1. Klon Repositori & Pindah ke Branch `beta`
```bash
git clone https://github.com/fatih-collab/proyek-analisis-kredit.git
cd proyek-analisis-kredit
git checkout beta
```

---

### 2. Cara Menjalankan Backend (FastAPI)

1. **Masuk ke folder backend & buat virtual environment:**
   ```bash
   cd backend
   python -m venv venv
   ```
2. **Aktifkan virtual environment:**
   - **Windows (PowerShell):**
     ```powershell
     .\venv\Scripts\Activate.ps1
     ```
   - **macOS/Linux:**
     ```bash
     source venv/bin/activate
     ```
3. **Instal seluruh dependensi Python:**
   ```bash
   pip install -r requirements.txt
   ```
4. **Pembersihan Dataset Lokal (Opsional)**:
   Jika Anda memiliki file dataset `.csv` lokal dan ingin membersihkan baris `"Not displayed"` secara otomatis:
   ```bash
   python clean_dataset.py
   ```
5. **Jalankan Server FastAPI:**
   ```bash
   uvicorn main:app --reload --host 0.0.0.0 --port 8000
   ```
   *API Dokumentasi Swagger dapat diakses di: `http://localhost:8000/docs`*

---

### 3. Cara Menjalankan Frontend (Next.js)

1. **Buka terminal baru di root folder project:**
   ```bash
   npm install
   ```
2. **Jalankan dev server Next.js:**
   ```bash
   npm run dev
   ```
   *Tampilan antarmuka frontend dapat diakses di: `http://localhost:3000`*

---

### 4. Cara Menjalankan dengan Docker (Rekomendasi Demo)

Untuk demo praktis, Anda bisa menjalankan seluruh layanan (Frontend & Backend) secara bersamaan menggunakan Docker Compose:

1. **Pastikan Docker Desktop sudah aktif.**
2. **Jalankan perintah build & run:**
   ```bash
   docker-compose up --build
   ```
3. **Akses Layanan:**
   - Frontend Next.js: `http://localhost:3000`
   - Backend API: `http://localhost:8000`

---

## 📂 Struktur Folder Utama
```
PDBL-MLOPS/
├── app/                  # Frontend Next.js (React/TypeScript)
├── backend/              # Backend FastAPI (Python)
│   ├── clean_dataset.py  # Script helper pembersih dataset
│   ├── main.py           # Entrypoint server API
│   ├── predictor.py      # Logika model prediksi kelayakan & plafon
│   └── requirements.txt  # Dependensi Python
├── Dataset/              # Folder penyimpanan dataset lokal (large.csv)
├── Dockerfile            # Dockerfile untuk Next.js Frontend
├── docker-compose.yml    # Orkestrasi Docker untuk Multi-container
├── model_klasifikasi_loan.pkl  # Model Klasifikasi ML
├── model_regresi_tuned_loan.pkl # Model Regresi ML
└── threshold_tuned.pkl         # Threshold optimal hasil tuning
```
