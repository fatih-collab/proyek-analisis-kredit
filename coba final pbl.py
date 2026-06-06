import joblib
import numpy as np
import pandas as pd

# ── Load model ────────────────────────────────────────────────────────
pipe_tuned  = joblib.load(r'C:\Users\ASUS TUF\Documents\ML OPS\PRAKTIKUM\model_tuned_final.pkl')
best_thresh = joblib.load(r'C:\Users\ASUS TUF\Documents\ML OPS\PRAKTIKUM\threshold_tuned.pkl')
best_model  = joblib.load(r'C:\Users\ASUS TUF\Documents\ML OPS\PRAKTIKUM\best_model_regresi2.pkl')
print('✅ Semua model berhasil di-load\n')


def proses_pengajuan_lengkap(pipe_klasifikasi, threshold, model_regresi, input_user):
    """
    Alur real pinjaman online:
    1. Klasifikasi  -> ACCEPT / REJECT
    2. Regresi      -> Plafon maksimal (kalau ACCEPT)
    3. User pilih   -> Nominal yang mau dicairkan (<=plafon)
    4. Sistem hitung-> Cicilan berdasarkan nominal yang dipilih
    """

    # ─────────────────────────────────────────────────────────────────
    # A. BUSINESS LOGIC — hitung otomatis fitur teknis
    # ─────────────────────────────────────────────────────────────────
    gaji       = input_user['gaji_bulanan']
    hutang     = input_user['hutang_saat_ini']
    sisa_limit = input_user['sisa_limit_kartu_kredit']

    dti = hutang / gaji if gaji > 0 else 0.99

    if input_user['punya_rumah'] and dti < 0.30:
        credit_score = 740
    elif dti < 0.40:
        credit_score = 680
    elif dti < 0.60:
        credit_score = 600
    else:
        credit_score = 520

    if credit_score >= 720 and dti < 0.30:
        prosper_score        = 9
        prosper_rating_num   = 6
        prosper_rating_alpha = 'A'
    elif credit_score >= 660 and dti < 0.40:
        prosper_score        = 7
        prosper_rating_num   = 4
        prosper_rating_alpha = 'B'
    elif credit_score >= 600:
        prosper_score        = 5
        prosper_rating_num   = 3
        prosper_rating_alpha = 'C'
    else:
        prosper_score        = 3
        prosper_rating_num   = 2
        prosper_rating_alpha = 'D'

    total_limit   = sisa_limit + hutang
    bankcard_util = min(hutang / total_limit, 1.0) if total_limit > 0 else 0.0
    revolving_util    = min((input_user['cicilan_bulanan_kartu'] * 12) / (gaji * 12 + 1), 2.0)
    income_per_crline = gaji / (input_user['jumlah_credit_line'] + 1)
    delinq_composite  = (input_user['tunggakan_saat_ini'] * 3 +
                         input_user['tunggakan_7tahun'] +
                         input_user['catatan_buruk'] * 2)

    if gaji < 1667:
        income_range = '$1-24,999'
    elif gaji < 4167:
        income_range = '$25,000-49,999'
    elif gaji < 8333:
        income_range = '$50,000-74,999'
    else:
        income_range = '$75,000+'

    tenor = input_user['tenor_bulan']
    if tenor <= 12:
        bunga = 0.08
    elif tenor <= 36:
        bunga = 0.15
    else:
        bunga = 0.22

    # ─────────────────────────────────────────────────────────────────
    # B. STEP 1 — KLASIFIKASI: ACCEPT atau REJECT?
    # ─────────────────────────────────────────────────────────────────
    data_klasifikasi = {
        'CreditScoreRangeLower'              : credit_score,
        'DebtToIncomeRatio'                  : round(dti, 4),
        'ProsperScore'                       : prosper_score,
        'ProsperRating (numeric)'            : prosper_rating_num,
        'ProsperRating (Alpha)'              : prosper_rating_alpha,
        'BankcardUtilization'                : round(bankcard_util, 4),
        'IncomeRange'                        : income_range,
        'revolving_util'                     : round(revolving_util, 4),
        'income_per_credit_line'             : round(income_per_crline, 4),
        'delinq_composite'                   : delinq_composite,
        'StatedMonthlyIncome'                : gaji,
        'EmploymentStatus'                   : input_user['status_pekerjaan'],
        'IsBorrowerHomeowner'                : input_user['punya_rumah'],
        'AvailableBankcardCredit'            : sisa_limit,
        'OpenRevolvingMonthlyPayment'        : input_user['cicilan_bulanan_kartu'],
        'TotalCreditLinespast7years'         : input_user['riwayat_kredit_tahun'] * 2,
        'CurrentCreditLines'                 : input_user['jumlah_credit_line'],
        'OpenRevolvingAccounts'              : max(1, input_user['jumlah_credit_line'] - 1),
        'CurrentDelinquencies'               : input_user['tunggakan_saat_ini'],
        'DelinquenciesLast7Years'            : input_user['tunggakan_7tahun'],
        'TotalInquiries'                     : input_user['jumlah_pengajuan_kredit'],
        'InquiriesLast6Months'               : min(input_user['jumlah_pengajuan_kredit'], 3),
        'EmploymentStatusDuration'           : input_user['lama_kerja_bulan'],
        'RevolvingCreditBalance'             : hutang,
        'TradesNeverDelinquent (percentage)' : 1.0 if input_user['tunggakan_7tahun'] == 0 else 0.7,
        'ListingCategory (numeric)'          : input_user['tujuan_pinjaman'],
        'BorrowerState'                      : input_user['borrower_state'],
        'Occupation'                         : input_user['occupation'],
    }

    df_klasifikasi = pd.DataFrame([data_klasifikasi])
    proba          = pipe_klasifikasi.predict_proba(df_klasifikasi)[0, 1]
    is_accept      = proba >= threshold

    # REJECT
    if not is_accept:
        alasan = []
        if dti > 0.50:
            alasan.append(f'Rasio hutang terlalu tinggi ({dti:.0%})')
        if credit_score < 600:
            alasan.append(f'Skor kredit rendah ({credit_score})')
        if input_user['tunggakan_saat_ini'] > 0:
            alasan.append(f'Memiliki {input_user["tunggakan_saat_ini"]} tunggakan aktif')
        if not alasan:
            alasan.append('Profil kredit tidak memenuhi kriteria')

        print('=' * 55)
        print('🏦  HASIL PENGAJUAN PINJAMAN')
        print('=' * 55)
        print(f'  Keputusan : Maaf, Pengajuan DITOLAK')
        print(f'  Alasan    :')
        for a in alasan:
            print(f'    - {a}')
        print('=' * 55)
        return False, None, None

    # ─────────────────────────────────────────────────────────────────
    # C. STEP 2 — REGRESI: hitung plafon maksimal
    #    28 fitur sesuai model regresi teman (bebas leakage)
    # ─────────────────────────────────────────────────────────────────
    data_regresi = {
        # Profil pinjaman
        'Term'                               : tenor,
        'ListingCategory (numeric)'          : input_user['tujuan_pinjaman'],

        # Skor kredit
        'ProsperScore'                       : prosper_score,
        'ProsperRating (numeric)'            : prosper_rating_num,

        # Profil peminjam
        'EmploymentStatus'                   : input_user['status_pekerjaan'],
        'IsBorrowerHomeowner'                : int(input_user['punya_rumah']),
        'Occupation'                         : input_user['occupation'],

        # Kapasitas bayar
        'StatedMonthlyIncome'                : gaji,
        'IncomeVerifiable'                   : 1,
        'DebtToIncomeRatio'                  : round(dti, 4),

        # Credit score
        'CreditScoreRangeLower'              : credit_score,
        'CreditScoreRangeUpper'              : credit_score + 19,

        # Riwayat kredit
        'TotalCreditLinespast7years'         : input_user['riwayat_kredit_tahun'] * 2,
        'OpenCreditLines'                    : input_user['jumlah_credit_line'],
        'CurrentCreditLines'                 : input_user['jumlah_credit_line'],
        'TotalTrades'                        : input_user['riwayat_kredit_tahun'] * 2,
        'TradesNeverDelinquent (percentage)' : 1.0 if input_user['tunggakan_7tahun'] == 0 else 0.7,

        # Kartu kredit
        'BankcardUtilization'                : round(bankcard_util, 4),
        'AvailableBankcardCredit'            : sisa_limit,
        'RevolvingCreditBalance'             : hutang,
        'OpenRevolvingAccounts'              : max(1, input_user['jumlah_credit_line'] - 1),
        'OpenRevolvingMonthlyPayment'        : input_user['cicilan_bulanan_kartu'],

        # Risiko
        'InquiriesLast6Months'               : min(input_user['jumlah_pengajuan_kredit'], 3),
        'CurrentDelinquencies'               : input_user['tunggakan_saat_ini'],
        'DelinquenciesLast7Years'            : input_user['tunggakan_7tahun'],
        'PublicRecordsLast10Years'           : input_user['catatan_buruk'],

        # Feature engineering (sama persis training regresi)
        'TotalDebtEstimation'                : gaji * dti,
        'CreditScoreRange'                   : 19,
    }

    df_regresi   = pd.DataFrame([data_regresi])
    limit_mentah = model_regresi.predict(df_regresi)[0]
    plafon       = int(np.round(limit_mentah))

    # ─────────────────────────────────────────────────────────────────
    # D. STEP 3 — INFORMASIKAN PLAFON KE USER
    # ─────────────────────────────────────────────────────────────────
    print('=' * 55)
    print('🏦  HASIL PENGAJUAN PINJAMAN')
    print('=' * 55)
    print(f'  Keputusan      : SELAMAT! Pengajuan DITERIMA')
    print(f'  Plafon Maksimal: ${plafon:,.0f}')
    print(f'  Bunga          : {bunga * 100:.0f}% per tahun')
    print(f'  Tenor          : {tenor} bulan')
    print(f'  Catatan        : Anda bebas mencairkan sebagian')
    print(f'                   atau seluruh plafon di atas.')
    print('=' * 55)

    # Ambil nominal dari input user
    if 'nominal_dicairkan' in input_user:
        nominal = input_user['nominal_dicairkan']
        print(f'\n  Nominal dipilih: ${nominal:,.0f}')
    else:
        print(f'\n  Masukkan nominal yang ingin dicairkan (maks ${plafon:,.0f}):')
        nominal = float(input('  $ '))

    # ─────────────────────────────────────────────────────────────────
    # E. STEP 4 — VALIDASI & HITUNG CICILAN
    # ─────────────────────────────────────────────────────────────────
    print()
    if nominal > plafon:
        print(f'  Nominal ${nominal:,.0f} melebihi plafon ${plafon:,.0f}')
        print(f'  Silakan masukkan nominal yang lebih kecil.')
        print('=' * 55)
        return True, plafon, None

    nominal = int(np.round(nominal))

    # Rumus cicilan anuitas (sama seperti bank/pinjol sungguhan)
    bunga_per_bulan = bunga / 12
    if bunga_per_bulan > 0:
        cicilan = nominal * (bunga_per_bulan * (1 + bunga_per_bulan)**tenor) / \
                  ((1 + bunga_per_bulan)**tenor - 1)
    else:
        cicilan = nominal / tenor

    total_bayar = cicilan * tenor
    total_bunga = total_bayar - nominal

    print('=' * 55)
    print('💰  RINCIAN PINJAMAN YANG DICAIRKAN')
    print('=' * 55)
    print(f'  Nominal Dicairkan : ${nominal:,.0f}')
    print(f'  Plafon Maksimal   : ${plafon:,.0f}')
    print(f'  Sisa Plafon       : ${plafon - nominal:,.0f} (bisa dicairkan lagi)')
    print(f'  Bunga             : {bunga * 100:.0f}% per tahun')
    print(f'  Tenor             : {tenor} bulan')
    print(f'  Cicilan/Bulan     : ${cicilan:,.0f}')
    print(f'  Total Bunga       : ${total_bunga:,.0f}')
    print(f'  Total Bayar       : ${total_bayar:,.0f}')
    print('=' * 55)

    return True, plafon, nominal


# =====================================================================
# DEMO — 3 SKENARIO NASABAH
# =====================================================================

# Nasabah 1 — Profil Sehat, cairkan SEBAGIAN dari plafon
input_nasabah_1 = {
    'borrower_state'          : 'CA',
    'occupation'              : 'Professional',
    'gaji_bulanan'            : 5500.0,
    'status_pekerjaan'        : 'Employed',
    'punya_rumah'             : True,
    'tenor_bulan'             : 36,
    'sanggup_cicil_bulan'     : 250.0,
    'hutang_saat_ini'         : 800.0,
    'sisa_limit_kartu_kredit' : 2000.0,
    'cicilan_bulanan_kartu'   : 100.0,
    'jumlah_credit_line'      : 8,
    'riwayat_kredit_tahun'    : 5,
    'tunggakan_saat_ini'      : 0,
    'tunggakan_7tahun'        : 0,
    'catatan_buruk'           : 0,
    'jumlah_pengajuan_kredit' : 2,
    'lama_kerja_bulan'        : 48,
    'tujuan_pinjaman'         : 1,
    'nominal_dicairkan'       : 3000.0,   # cairkan $3,000 dari plafon
}

# Nasabah 2 — Profil Berisiko (kemungkinan REJECT)
input_nasabah_2 = {
    'borrower_state'          : 'TX',
    'occupation'              : 'Other',
    'gaji_bulanan'            : 2000.0,
    'status_pekerjaan'        : 'Self-employed',
    'punya_rumah'             : False,
    'tenor_bulan'             : 60,
    'sanggup_cicil_bulan'     : 100.0,
    'hutang_saat_ini'         : 1800.0,
    'sisa_limit_kartu_kredit' : 0.0,
    'cicilan_bulanan_kartu'   : 200.0,
    'jumlah_credit_line'      : 3,
    'riwayat_kredit_tahun'    : 1,
    'tunggakan_saat_ini'      : 2,
    'tunggakan_7tahun'        : 5,
    'catatan_buruk'           : 1,
    'jumlah_pengajuan_kredit' : 8,
    'lama_kerja_bulan'        : 6,
    'tujuan_pinjaman'         : 1,
    'nominal_dicairkan'       : 5000.0,
}

# Nasabah 3 — ACCEPT tapi minta nominal melebihi plafon
input_nasabah_3 = {
    'borrower_state'          : 'NY',
    'occupation'              : 'Teacher',
    'gaji_bulanan'            : 4500.0,
    'status_pekerjaan'        : 'Employed',
    'punya_rumah'             : False,
    'tenor_bulan'             : 36,
    'sanggup_cicil_bulan'     : 200.0,
    'hutang_saat_ini'         : 500.0,
    'sisa_limit_kartu_kredit' : 1500.0,
    'cicilan_bulanan_kartu'   : 80.0,
    'jumlah_credit_line'      : 5,
    'riwayat_kredit_tahun'    : 3,
    'tunggakan_saat_ini'      : 0,
    'tunggakan_7tahun'        : 0,
    'catatan_buruk'           : 0,
    'jumlah_pengajuan_kredit' : 1,
    'lama_kerja_bulan'        : 24,
    'tujuan_pinjaman'         : 1,
    'nominal_dicairkan'       : 99999.0,  # sengaja minta terlalu besar
}

print('\n--- NASABAH 1 (Profil Sehat, cairkan sebagian) ---')
proses_pengajuan_lengkap(pipe_tuned, best_thresh, best_model, input_nasabah_1)

print('\n--- NASABAH 2 (Profil Berisiko) ---')
proses_pengajuan_lengkap(pipe_tuned, best_thresh, best_model, input_nasabah_2)

print('\n--- NASABAH 3 (Minta melebihi plafon) ---')
proses_pengajuan_lengkap(pipe_tuned, best_thresh, best_model, input_nasabah_3)