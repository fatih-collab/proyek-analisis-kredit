# CreditCare - Sistem Prediksi Kelayakan & Limit Kredit (MLOps)

Proyek ini adalah sistem analisis kelayakan kredit (Credit Scoring) dan penentuan batas plafon kredit maksimal berbasis Machine Learning. Aplikasi dibangun dengan Next.js pada frontend, FastAPI pada backend, dan database Supabase (PostgreSQL).

## Fitur Utama
- **Filter Kelayakan Kredit**: Menentukan status kelayakan nasabah (LAYAK / TIDAK LAYAK) menggunakan model klasifikasi LightGBM (Tuned Threshold: 0.52).
- **Prediksi Plafon Limit**: Menghitung limit kredit maksimal aman untuk nasabah menggunakan model regresi LightGBM.
- **Explainable Rejection**: Penolakan otomatis dengan penjelasan rasional apabila nominal pengajuan melebihi plafon limit.
- **Monitoring Panel (Admin)**: Visualisasi data EDA historis dan monitoring log aktivitas pengajuan secara real-time.
- **Personal Dashboard (User)**: Halaman histori personal untuk memantau ringkasan hasil pengajuan kredit nasabah.

## Tech Stack
- **Frontend**: Next.js (TypeScript, Tailwind CSS)
- **Backend**: FastAPI (Python)
- **Database**: Supabase (PostgreSQL)
- **Kontainer**: Docker & Docker Compose
- **Hosting**: Railway

---

## Cara Menjalankan Aplikasi Secara Lokal

Pastikan perangkat Anda sudah terpasang **Python 3.10+**, **Node.js 18+**, dan **Docker Desktop** (jika ingin menggunakan Docker).

### 1. Clone Repositori
```bash
git clone https://github.com/fatih-collab/proyek-analisis-kredit.git
cd proyek-analisis-kredit
git checkout beta
```

### 2. Jalankan Backend (FastAPI)
1. Pindah ke direktori backend dan buat virtual environment:
   ```bash
   cd backend
   python -m venv venv
   ```
2. Aktifkan virtual environment:
   - **Windows (PowerShell)**:
     ```powershell
     .\venv\Scripts\Activate.ps1
     ```
   - **Mac/Linux**:
     ```bash
     source venv/bin/activate
     ```
3. Install seluruh library Python yang dibutuhkan:
   ```bash
   pip install -r requirements.txt
   ```
4. Bersihkan data non-standar pada dataset lokal (opsional):
   ```bash
   python clean_dataset.py
   ```
5. Jalankan server FastAPI:
   ```bash
   uvicorn main:app --reload --host 0.0.0.0 --port 8000
   ```
   Dokumentasi API otomatis (Swagger) dapat diakses melalui: `http://localhost:8000/docs`

### 3. Jalankan Frontend (Next.js)
1. Buka terminal baru di root folder proyek, lalu install dependencies:
   ```bash
   npm install
   ```
2. Jalankan dev server Next.js:
   ```bash
   npm run dev
   ```
   Halaman web dapat diakses melalui: `http://localhost:3000`

### 4. Jalankan Sekaligus Menggunakan Docker (Rekomendasi Demo)
Jika ingin menjalankan frontend dan backend secara praktis tanpa install manual:
1. Pastikan aplikasi Docker Desktop sudah aktif.
2. Jalankan perintah berikut di root folder:
   ```bash
   docker-compose up --build
   ```
3. Akses aplikasi:
   - Frontend: `http://localhost:3000`
   - Backend API: `http://localhost:8000`

---

## Struktur Proyek
```
PDBL-MLOPS/
├── app/                  # Kode sumber frontend Next.js
├── backend/              # Kode sumber backend FastAPI
│   ├── clean_dataset.py  # Script pembersih dataset
│   ├── main.py           # Entrypoint API
│   ├── predictor.py      # Logika pemanggilan model ML
│   └── requirements.txt  # Daftar dependensi backend
├── Dataset/              # Folder dataset lokal
├── Dockerfile            # Konfigurasi container frontend
├── docker-compose.yml    # Orkestrasi multi-container
├── model_klasifikasi_loan.pkl  # Model Klasifikasi ML
├── model_regresi_tuned_loan.pkl # Model Regresi ML
└── threshold_tuned.pkl         # Nilai threshold klasifikasi
```
