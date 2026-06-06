'use client';

import React, { useState, useEffect, useMemo } from 'react';
import { useRouter } from 'next/navigation';
import {
  Users, ClipboardList, CheckCircle2, XCircle, Target,
  BarChart3, Menu, TrendingUp, DollarSign, Activity,
  Shield, Sparkles, RefreshCw, Database, PieChart as PieIcon
} from 'lucide-react';
import AdminSidebar from './components/AdminSidebar';
import DataTable from './components/DataTable';
import { PieChart, BarChart, LineChart, HistogramChart } from './components/EDACharts';

const BACKEND_URL = 'http://localhost:8000';

/* ─── Types ─── */
interface EDAData {
  totalRecords: number;
  avgMonthlyIncome: number;
  medianMonthlyIncome: number;
  avgDTI: number;
  medianDTI: number;
  avgCreditScore: number;
  avgLoanAmount: number;
  medianLoanAmount: number;
  minLoanAmount: number;
  maxLoanAmount: number;
  loanStatusDistribution: Record<string, number>;
  termDistribution: Record<string, number>;
  prosperRatingDistribution: Record<string, number>;
  employmentDistribution: Record<string, number>;
  incomeRangeDistribution: Record<string, number>;
  occupationTop10: Record<string, number>;
  borrowerStateTop10: Record<string, number>;
  creditScoreRanges: Record<string, number>;
  listingCategoryDistribution: Record<string, number>;
  homeownerDistribution: Record<string, number>;
  dtiHistogram: { label: string; value: number }[];
  creditScoreHistogram: { label: string; value: number }[];
  loanAmountHistogram: { label: string; value: number }[];
  monthlyIncomeHistogram: { label: string; value: number }[];
  loansByYear: { label: string; value: number }[];
  loansByYearMonth: { label: string; value: number }[];
}

interface PredLog {
  id: string;
  timestamp: string;
  inputData: Record<string, string>;
  result: string;
  confidence: number;
  plafon?: number;
  cicilanPerBulan?: number;
  alasanPenolakan?: string[];
  catatanRisiko?: string;
  loanAmount: string;
  loanTerm: string;
  loanPurpose: string;
  creditHistory: string;
  employment: string;
  propertyArea: string;
}

function dictToChartData(d: Record<string, number>) {
  return Object.entries(d).map(([label, value]) => ({ label, value }));
}

/* ─── Translations for Laypeople ─── */
const translateLoanStatus = (s: string) => {
  const map: Record<string, string> = {
    'Current': 'Aktif Berjalan',
    'Completed': 'Lunas',
    'Chargedoff': 'Gagal Bayar (Macet)',
    'Defaulted': 'Wanprestasi (Gagal)',
    'Past Due (1-15 days)': 'Terlambat (1-15 Hari)',
    'Past Due (16-30 days)': 'Terlambat (16-30 Hari)',
    'Past Due (31-60 days)': 'Terlambat (31-60 Hari)',
    'Past Due (61-90 days)': 'Terlambat (61-90 Hari)',
    'Past Due (91-120 days)': 'Terlambat (91-120 Hari)',
    'Past Due (>120 days)': 'Terlambat (>120 Hari)',
    'FinalPaymentInProgress': 'Proses Pelunasan',
    'Cancelled': 'Dibatalkan',
  };
  return map[s] || s;
};

const translateEmploymentStatus = (s: string) => {
  const map: Record<string, string> = {
    'Employed': 'Bekerja',
    'Full-time': 'Pekerja Penuh Waktu',
    'Self-employed': 'Wiraswasta',
    'Part-time': 'Pekerja Paruh Waktu',
    'Retired': 'Pensiunan',
    'Not employed': 'Tidak Bekerja',
    'Other': 'Lainnya',
    'Not Available': 'Tidak Tersedia',
  };
  return map[s] || s;
};

const translateLoanPurpose = (s: string) => {
  const map: Record<string, string> = {
    'Debt Consolidation': 'Konsolidasi Hutang',
    'Home Improvement': 'Renovasi Rumah',
    'Business': 'Modal Usaha',
    'Personal Loan': 'Kebutuhan Pribadi',
    'Education': 'Pendidikan',
    'Medical': 'Kesehatan',
    'Auto': 'Kendaraan',
    'Wedding': 'Pernikahan',
    'Other': 'Lainnya',
  };
  return map[s] || s;
};

export default function AdminDashboard() {
  const router = useRouter();
  const [sidebarOpen, setSidebarOpen] = useState(false);
  const [eda, setEda] = useState<EDAData | null>(null);
  const [predictions, setPredictions] = useState<PredLog[]>([]);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState('');
  const [activeTab, setActiveTab] = useState<'overview' | 'eda' | 'predictions'>('overview');
  
  // Resizable sidebar states
  const [sidebarWidth, setSidebarWidth] = useState(260);
  const [isDragging, setIsDragging] = useState(false);
  const [isLargeScreen, setIsLargeScreen] = useState(false);
  const [mounted, setMounted] = useState(false);
  
  // Sub-tab state inside EDA Analytics
  const [edaSubTab, setEdaSubTab] = useState<'demographics' | 'risk' | 'loans'>('demographics');

  const getToken = () => {
    try {
      const s = JSON.parse(localStorage.getItem('mlops_admin_session') || '{}');
      return s.token || '';
    } catch { return ''; }
  };

  // Sync state & screen resize detection
  useEffect(() => {
    setMounted(true);
    const savedWidth = localStorage.getItem('admin_sidebar_width');
    if (savedWidth) {
      setSidebarWidth(parseInt(savedWidth));
    }
    
    const handleResize = () => {
      setIsLargeScreen(window.innerWidth >= 1024);
    };
    handleResize();
    window.addEventListener('resize', handleResize);
    return () => window.removeEventListener('resize', handleResize);
  }, []);

  const updateSidebarWidth = (w: number) => {
    setSidebarWidth(w);
    localStorage.setItem('admin_sidebar_width', String(w));
  };

  // ── Sync activeTab with URL hash on mount and hashchange ──
  useEffect(() => {
    const syncTabWithHash = () => {
      const hash = window.location.hash;
      if (hash === '#predictions') {
        setActiveTab('predictions');
      } else if (hash === '#eda' || hash === '#users') {
        setActiveTab('eda');
      } else {
        setActiveTab('overview');
      }
    };

    syncTabWithHash();
    window.addEventListener('hashchange', syncTabWithHash);
    return () => window.removeEventListener('hashchange', syncTabWithHash);
  }, []);

  useEffect(() => {
    const session = localStorage.getItem('mlops_admin_session');
    if (!session) { router.push('/admin/login'); return; }
    loadData();
  }, [router]);

  const loadData = async () => {
    setIsLoading(true);
    setError('');
    const token = getToken();
    const headers = { 'Authorization': `Bearer ${token}` };

    try {
      const [edaRes, predRes] = await Promise.all([
        fetch(`${BACKEND_URL}/admin/eda`, { headers }),
        fetch(`${BACKEND_URL}/admin/predictions`, { headers }),
      ]);

      if (edaRes.status === 401 || predRes.status === 401) {
        localStorage.removeItem('mlops_admin_session');
        router.push('/admin/login');
        return;
      }

      if (edaRes.ok) {
        const edaData = await edaRes.json();
        setEda(edaData);
      }
      if (predRes.ok) {
        const predData = await predRes.json();
        setPredictions(predData.predictions || []);
      }
    } catch {
      setError('Gagal terhubung ke backend. Pastikan server berjalan di localhost:8000');
    }
    setIsLoading(false);
  };

  const handleLogout = () => {
    localStorage.removeItem('mlops_admin_session');
    router.push('/admin/login');
  };

  // ── Prediction stats ──
  const predStats = useMemo(() => {
    const total = predictions.length;
    const layak = predictions.filter(p => p.result === 'LAYAK').length;
    const tidakLayak = total - layak;
    const avgConf = total > 0 ? Math.round(predictions.reduce((s, p) => s + p.confidence, 0) / total * 10) / 10 : 0;
    const approvalRate = total > 0 ? Math.round((layak / total) * 1000) / 10 : 0;
    return { total, layak, tidakLayak, avgConf, approvalRate };
  }, [predictions]);

  // ── Table columns ──
  const predColumns = [
    { key: 'timestamp', label: 'Waktu', sortable: true, render: (v: unknown) => {
      const d = new Date(String(v));
      return d.toLocaleDateString('id-ID', { day: '2-digit', month: 'short', year: 'numeric', hour: '2-digit', minute: '2-digit' });
    }},
    { key: 'fullName', label: 'Nama Nasabah', sortable: true },
    { key: 'email', label: 'Email', sortable: true },
    { key: 'phone', label: 'No. Telepon', sortable: true },
    { key: 'address', label: 'Alamat', sortable: true },
    { key: 'result', label: 'Hasil', sortable: true, render: (v: unknown) => (
      <span className={`inline-flex items-center gap-1 px-2.5 py-1 rounded-xl text-[10px] font-extrabold ${v === 'LAYAK' ? 'bg-emerald-100/60 dark:bg-emerald-900/20 text-emerald-600' : 'bg-red-100/60 dark:bg-red-900/20 text-red-500'}`}>
        {v === 'LAYAK' ? <CheckCircle2 className="w-3.5 h-3.5" /> : <XCircle className="w-3.5 h-3.5" />}
        {String(v)}
      </span>
    )},
    { key: 'loanAmount', label: 'Pinjaman', sortable: true, render: (v: unknown) => `$${parseInt(String(v) || '0').toLocaleString('en-US')}` },
    { key: 'loanTerm', label: 'Tenor', render: (v: unknown) => `${v} bln` },
    { key: 'loanPurpose', label: 'Tujuan', sortable: true, render: (v: unknown) => translateLoanPurpose(String(v)) },
    { key: 'employment', label: 'Pekerjaan', sortable: true, render: (v: unknown) => translateEmploymentStatus(String(v)) },
  ];

  const predTableData = predictions.map(p => ({ ...p }));

  // ── Summary cards ──
  const overviewCards = [
    { label: 'Data Sampel Kredit (CSV)', value: eda?.totalRecords?.toLocaleString() || '0', icon: Database },
    { label: 'Total Pengajuan Skoring', value: predStats.total.toLocaleString(), icon: ClipboardList },
    { label: 'Pengajuan Layak', value: predStats.layak.toLocaleString(), icon: CheckCircle2 },
    { label: 'Pengajuan Tidak Layak', value: predStats.tidakLayak.toLocaleString(), icon: XCircle },
    { label: 'Rasio Kelayakan Pinjaman', value: `${predStats.approvalRate}%`, icon: TrendingUp },
    { label: 'Tingkat Keyakinan Model', value: `${predStats.avgConf}%`, icon: Target },
  ];

  /* ── Mapped Data translations for charts ── */
  const mappedLoanStatusDataOverview = useMemo(() => {
    if (!eda) return [];
    return dictToChartData(eda.loanStatusDistribution).slice(0, 6).map((d, i) => ({
      ...d,
      label: translateLoanStatus(d.label),
      color: ['#10b981','#ef4444','#f59e0b','#6366f1','#0ea5e9','#ec4899'][i]
    }));
  }, [eda]);

  const mappedLoanStatusDataEDA = useMemo(() => {
    if (!eda) return [];
    return dictToChartData(eda.loanStatusDistribution).slice(0, 8).map((d, i) => ({
      ...d,
      label: translateLoanStatus(d.label),
      color: ['#10b981','#ef4444','#f59e0b','#6366f1','#0ea5e9','#ec4899','#14b8a6','#8b5cf6'][i]
    }));
  }, [eda]);

  const mappedHomeownerData = useMemo(() => {
    if (!eda) return [];
    return dictToChartData(eda.homeownerDistribution).map((d, i) => ({
      ...d,
      label: d.label === 'True' || d.label === 'true' ? 'Memiliki Rumah' : 'Tidak Memiliki Rumah',
      color: ['#0ea5e9','#f59e0b'][i]
    }));
  }, [eda]);

  const mappedEmploymentData = useMemo(() => {
    if (!eda) return [];
    return dictToChartData(eda.employmentDistribution).map(d => ({
      ...d,
      label: translateEmploymentStatus(d.label)
    }));
  }, [eda]);

  const mappedUserPurposeData = useMemo(() => {
    return dictToChartData(
      predictions.reduce((acc, p) => {
        const k = translateLoanPurpose(p.loanPurpose || 'Lainnya');
        acc[k] = (acc[k] || 0) + 1;
        return acc;
      }, {} as Record<string, number>)
    );
  }, [predictions]);

  const mappedUserEmploymentData = useMemo(() => {
    return dictToChartData(
      predictions.reduce((acc, p) => {
        const k = translateEmploymentStatus(p.employment || 'Unknown');
        acc[k] = (acc[k] || 0) + 1;
        return acc;
      }, {} as Record<string, number>)
    );
  }, [predictions]);

  if (isLoading) {
    return (
      <div className="min-h-screen flex items-center justify-center">
        <div className="text-center">
          <div className="w-10 h-10 border-3 border-sky-100 border-t-sky-600 rounded-full animate-spin mx-auto mb-4" />
          <p className="text-xs font-bold text-sky-500/60">Loading data analitis & pengajuan...</p>
        </div>
      </div>
    );
  }

  return (
    <div className="min-h-screen relative transition-colors duration-300 noise-overlay">
      <div className="gradient-mesh" /><div className="orb orb-1" /><div className="orb orb-2" />

      <AdminSidebar
        mobileOpen={sidebarOpen}
        onClose={() => setSidebarOpen(false)}
        onLogout={handleLogout}
        sidebarWidth={sidebarWidth}
        setSidebarWidth={updateSidebarWidth}
        isDragging={isDragging}
        setIsDragging={setIsDragging}
        activeTab={activeTab}
        setActiveTab={setActiveTab}
      />

      <main
        className="relative z-10 min-h-screen"
        style={{
          marginLeft: mounted && isLargeScreen ? `${sidebarWidth}px` : undefined,
          transition: isDragging ? 'none' : 'margin-left 0.2s cubic-bezier(0.4, 0, 0.2, 1)'
        }}
      >
        {/* Top bar */}
        <div className="sticky top-0 z-30 glass-card-static border-b border-sky-100/30 dark:border-sky-800/20 px-4 lg:px-8 py-4 flex items-center justify-between">
          <div className="flex items-center gap-3">
            <button onClick={() => setSidebarOpen(true)} className="lg:hidden p-2 rounded-xl hover:bg-sky-100/40 dark:hover:bg-sky-800/20 transition-colors">
              <Menu className="w-5 h-5 text-sky-700 dark:text-sky-300" />
            </button>
            <div>
              <h1 className="text-lg font-black text-sky-950 dark:text-sky-100" style={{ letterSpacing: '-0.03em' }}>
                Monitoring Panel
              </h1>
            </div>
          </div>
          <button onClick={loadData} className="flex items-center gap-2 px-4 py-2.5 rounded-xl glass-card-static text-xs font-bold text-sky-700 dark:text-sky-300 hover:shadow-md hover:scale-[1.02] active:scale-98 transition-all">
            <RefreshCw className="w-3.5 h-3.5" /> Segarkan Data
          </button>
        </div>

        <div className="px-4 lg:px-8 py-8 space-y-10">
          {error && (
            <div className="px-5 py-4 rounded-2xl bg-red-50/80 dark:bg-red-900/20 border border-red-200/50 dark:border-red-800/30 text-red-500 text-sm font-semibold shadow-sm">
              ⚠️ {error}
            </div>
          )}

          {/* ═══ OVERVIEW TAB ═══ */}
          {activeTab === 'overview' && (
            <>
              {/* Metrics Grid */}
              <section className="space-y-4">
                <div className="flex items-center gap-2">
                  <Activity className="w-4 h-4 text-sky-500" />
                  <h2 className="text-sm font-black text-sky-950 dark:text-sky-100">Metrik Utama Sistem & Model</h2>
                </div>
                <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
                  {overviewCards.map((c, i) => {
                    let borderColor = 'border-sky-100/30 dark:border-sky-800/10';
                    let iconBg = 'bg-sky-50 dark:bg-sky-900/30 text-sky-600 dark:text-sky-400';
                    let accentBar = 'bg-sky-500/80';
                    
                    if (c.label === 'Data Sampel Kredit (CSV)') {
                      borderColor = 'border-slate-200 dark:border-slate-800/60';
                      iconBg = 'bg-slate-50 dark:bg-slate-800/50 text-slate-600 dark:text-slate-400';
                      accentBar = 'bg-slate-400 dark:bg-slate-600';
                    } else if (c.label === 'Total Pengajuan Skoring') {
                      borderColor = 'border-indigo-100/60 dark:border-indigo-900/20';
                      iconBg = 'bg-indigo-50 dark:bg-indigo-900/30 text-indigo-600 dark:text-indigo-400';
                      accentBar = 'bg-indigo-500';
                    } else if (c.label === 'Pengajuan Layak') {
                      borderColor = 'border-emerald-200/50 dark:border-emerald-900/20';
                      iconBg = 'bg-emerald-50 dark:bg-emerald-900/30 text-emerald-600 dark:text-emerald-400';
                      accentBar = 'bg-emerald-500';
                    } else if (c.label === 'Pengajuan Tidak Layak') {
                      borderColor = 'border-rose-200/50 dark:border-rose-900/20';
                      iconBg = 'bg-rose-50 dark:bg-rose-900/30 text-rose-600 dark:text-rose-400';
                      accentBar = 'bg-rose-500';
                    } else if (c.label === 'Rasio Kelayakan Pinjaman') {
                      borderColor = 'border-teal-100/60 dark:border-teal-900/20';
                      iconBg = 'bg-teal-50 dark:bg-teal-900/30 text-teal-600 dark:text-teal-400';
                      accentBar = 'bg-teal-500';
                    } else if (c.label === 'Tingkat Keyakinan Model') {
                      borderColor = 'border-purple-100/60 dark:border-purple-900/20';
                      iconBg = 'bg-purple-50 dark:bg-purple-900/30 text-purple-600 dark:text-purple-400';
                      accentBar = 'bg-purple-500';
                    }

                    return (
                      <div key={i} className={`glass-card-static rounded-3xl p-6 relative overflow-hidden group hover:scale-[1.01] transition-all duration-300 border ${borderColor}`} style={{ boxShadow: '0 8px 30px rgba(14,165,233,0.02)' }}>
                        <div className={`absolute top-0 left-0 right-0 h-[4px] ${accentBar} opacity-80 group-hover:opacity-100 transition-opacity`} />
                        <div className="flex items-center justify-between">
                          <div className="space-y-1">
                            <p className="text-xs font-bold text-sky-500/70 uppercase tracking-wider">{c.label}</p>
                            <p className="text-4xl font-black text-sky-955 dark:text-sky-50 tabular-nums" style={{ letterSpacing: '-0.03em' }}>{c.value}</p>
                          </div>
                          <div className={`w-12 h-12 rounded-2xl ${iconBg} flex items-center justify-center flex-shrink-0 shadow-sm`}>
                            <c.icon className="w-6 h-6" />
                          </div>
                        </div>
                      </div>
                    );
                  })}
                </div>
              </section>

              {/* Dataset summary cards */}
              {eda && (
                <section className="space-y-4">
                  <div className="flex items-center gap-2.5">
                    <div className="p-1.5 rounded-lg bg-sky-100/50 dark:bg-sky-900/30">
                      <Database className="w-4 h-4 text-sky-600 dark:text-sky-400" />
                    </div>
                    <div>
                      <h2 className="text-sm font-black text-sky-950 dark:text-sky-100">Statistik Sampel Kredit (prosperLoanData.csv)</h2>
                      <p className="text-[10px] font-bold text-sky-500/50">Profil keuangan rata-rata debitur dalam database historis</p>
                    </div>
                  </div>
                  <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-6">
                    {[
                      { l: 'Rata-rata Pendapatan Bulanan', v: `$${eda.avgMonthlyIncome.toLocaleString('en-US', {maximumFractionDigits:0})}`, desc: 'Total pendapatan per bulan' },
                      { l: 'Rata-rata Skor Kredit', v: eda.avgCreditScore.toFixed(0), desc: 'Skor kelayakan kredit historis' },
                      { l: 'Rata-rata Rasio DTI', v: `${(eda.avgDTI * 100).toFixed(1)}%`, desc: 'Rasio hutang dibanding pendapatan' },
                      { l: 'Rata-rata Nominal Pinjaman', v: `$${eda.avgLoanAmount.toLocaleString('en-US', {maximumFractionDigits:0})}`, desc: 'Jumlah dana yang diajukan' },
                    ].map((s, i) => (
                      <div key={i} className="glass-card-static rounded-3xl p-6 text-center border border-sky-100/20 dark:border-sky-800/10 relative overflow-hidden group" style={{ boxShadow: '0 4px 20px rgba(14,165,233,0.02)' }}>
                        <div className="absolute top-0 left-0 right-0 h-[3px] bg-sky-500/30 dark:bg-sky-500/10" />
                        <p className="text-[10px] font-bold text-sky-500/70 uppercase tracking-wider mb-2">{s.l}</p>
                        <p className="text-3xl font-black text-sky-955 dark:text-sky-50">{s.v}</p>
                        <p className="text-[10px] text-sky-400/50 mt-1 font-semibold">{s.desc}</p>
                      </div>
                    ))}
                  </div>
                </section>
              )}

              {/* Quick charts */}
              {eda && (
                <section className="space-y-4">
                  <div className="flex items-center gap-2">
                    <BarChart3 className="w-4 h-4 text-sky-500" />
                    <h2 className="text-sm font-black text-sky-950 dark:text-sky-100">Ikhtisar Cepat Visualisasi Dataset</h2>
                  </div>
                  <div className="grid grid-cols-1 lg:grid-cols-2 gap-8">
                    <PieChart title="Status Kelayakan Pinjaman Historis" data={mappedLoanStatusDataOverview} />
                    <BarChart title="Peringkat Kredit Prosper Rating" data={dictToChartData(eda.prosperRatingDistribution)} />
                  </div>
                </section>
              )}

              {/* Prediction results quick */}
              {predStats.total > 0 && (
                <section className="space-y-4">
                  <div className="flex items-center gap-2">
                    <ClipboardList className="w-4 h-4 text-sky-500" />
                    <h2 className="text-sm font-black text-sky-950 dark:text-sky-100">Visualisasi Log Pengajuan Saat Ini</h2>
                  </div>
                  <div className="grid grid-cols-1 lg:grid-cols-2 gap-8">
                    <PieChart
                      title="Distribusi Hasil Evaluasi Pengguna"
                      data={[
                        { label: 'LAYAK (Disetujui)', value: predStats.layak, color: '#10b981' },
                        { label: 'TIDAK LAYAK (Ditolak)', value: predStats.tidakLayak, color: '#ef4444' },
                      ]}
                    />
                    <BarChart title="Tujuan Pengajuan Pinjaman" data={mappedUserPurposeData} />
                  </div>
                </section>
              )}
            </>
          )}

          {/* ═══ EDA TAB ═══ */}
          {activeTab === 'eda' && eda && (
            <>
              <section id="eda" className="space-y-6">
                <div className="flex items-center gap-2">
                  <BarChart3 className="w-4 h-4 text-sky-500" />
                  <h2 className="text-sm font-black text-sky-950 dark:text-sky-100">Analisis Eksplorasi Dataset Lengkap</h2>
                  <div className="inline-flex items-center gap-1.5 px-3 py-1 rounded-full bg-indigo-100/50 dark:bg-indigo-900/20 border border-indigo-200/30 dark:border-indigo-700/20">
                    <Sparkles className="w-3 h-3 text-indigo-500 animate-pulse" />
                    <span className="text-[10px] font-extrabold text-indigo-600 dark:text-indigo-400 uppercase tracking-wider">{eda.totalRecords.toLocaleString()} Baris Data</span>
                  </div>
                </div>

                {/* Sub-tab menu for EDA charts organization to prevent clutter */}
                <div className="flex flex-wrap gap-2.5 border-b border-sky-100/30 dark:border-sky-800/20 pb-4">
                  {([
                    { key: 'demographics', label: 'Profil Demografi Debitur', desc: 'Analisis pekerjaan, negara bagian, & status kepemilikan aset.' },
                    { key: 'risk', label: 'Analisis Risiko & Kredit', desc: 'Pemetaan skor kredit, rasio DTI, & rating kelayakan.' },
                    { key: 'loans', label: 'Karakteristik & Tren Pinjaman', desc: 'Nominal pengajuan, jangka waktu tenor, & tren tahunan.' },
                  ] as const).map(sub => (
                    <button
                      key={sub.key}
                      onClick={() => setEdaSubTab(sub.key)}
                      className={`flex flex-col items-start text-left px-5 py-3 rounded-2xl transition-all border ${
                        edaSubTab === sub.key
                          ? 'bg-gradient-to-r from-sky-500/10 to-indigo-500/10 border-sky-300 dark:border-sky-700 text-sky-700 dark:text-sky-400 shadow-sm'
                          : 'bg-white/40 dark:bg-slate-900/20 border-transparent hover:bg-sky-50/50 dark:hover:bg-sky-900/10 text-sky-700/60 dark:text-sky-300/50'
                      }`}
                    >
                      <span className="text-xs font-black">{sub.label}</span>
                      <span className="text-[9px] opacity-70 font-bold mt-0.5">{sub.desc}</span>
                    </button>
                  ))}
                </div>

                {/* SUB TAB 1: Demographics */}
                {edaSubTab === 'demographics' && (
                  <div className="grid grid-cols-1 lg:grid-cols-2 gap-8 animate-fade-in">
                    <PieChart title="Status Kepemilikan Rumah (Homeowner)" data={mappedHomeownerData} />
                    <BarChart title="Status Pekerjaan Debitur" data={mappedEmploymentData} />
                    <BarChart title="Top 10 Sektor Pekerjaan Debitur" data={dictToChartData(eda.occupationTop10)} />
                    <BarChart title="Top 10 Domisili Negara Bagian Debitur" data={dictToChartData(eda.borrowerStateTop10)} />
                    <BarChart title="Pembagian Rentang Pendapatan Tahunan" data={dictToChartData(eda.incomeRangeDistribution)} />
                  </div>
                )}

                {/* SUB TAB 2: Risk Analysis */}
                {edaSubTab === 'risk' && (
                  <div className="grid grid-cols-1 lg:grid-cols-2 gap-8 animate-fade-in">
                    <HistogramChart title="Distribusi Skor Kredit (Credit Score)" data={eda.creditScoreHistogram} color="#0ea5e9" />
                    <HistogramChart title="Distribusi Rasio Hutang ke Pendapatan (DTI Ratio)" data={eda.dtiHistogram} color="#6366f1" />
                    <HistogramChart title="Distribusi Pendapatan Bulanan (Monthly Income)" data={eda.monthlyIncomeHistogram} color="#f59e0b" />
                    <BarChart title="Peringkat Kredit Prosper Rating" data={dictToChartData(eda.prosperRatingDistribution)} />
                  </div>
                )}

                {/* SUB TAB 3: Loan Characteristics */}
                {edaSubTab === 'loans' && (
                  <div className="grid grid-cols-1 lg:grid-cols-2 gap-8 animate-fade-in">
                    <PieChart title="Distribusi Status Keberjalanan Pinjaman" data={mappedLoanStatusDataEDA} />
                    <HistogramChart title="Nominal Pengajuan Pinjaman (Loan Amount)" data={eda.loanAmountHistogram} color="#10b981" />
                    <BarChart title="Pilihan Tenor Pinjaman (Bulan)" data={dictToChartData(eda.termDistribution)} />
                    <BarChart title="Top 10 Kategori Penggunaan Pinjaman" data={dictToChartData(eda.listingCategoryDistribution)} />
                    <LineChart title="Perkembangan Jumlah Pinjaman per Tahun" data={eda.loansByYear} color="#0ea5e9" />
                  </div>
                )}
              </section>
            </>
          )}

          {/* ═══ PREDICTIONS TAB ═══ */}
          {activeTab === 'predictions' && (
            <section id="predictions" className="space-y-8">
              <div className="flex items-center gap-2">
                <ClipboardList className="w-4 h-4 text-sky-500" />
                <h2 className="text-sm font-black text-sky-950 dark:text-sky-100">Riwayat Pengajuan Skoring Otomatis</h2>
                <span className="text-[10px] font-extrabold text-sky-600 dark:text-sky-400 px-2.5 py-1 rounded-full bg-sky-100/40 dark:bg-sky-800/20">{predictions.length} Data</span>
              </div>

              {predictions.length === 0 ? (
                <div className="glass-card-static rounded-3xl p-12 text-center">
                  <ClipboardList className="w-12 h-12 text-sky-300/40 mx-auto mb-4" />
                  <p className="text-sm font-black text-sky-700/60 dark:text-sky-300/40">Belum ada pengajuan masuk</p>
                  <p className="text-xs text-sky-500/40 mt-1 font-semibold">Data log akan muncul setelah pengguna mengisi formulir di menu Predict</p>
                </div>
              ) : (
                <div className="space-y-8">
                  {/* Grid stats */}
                  <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-6">
                    {[
                      { l: 'Total Pengajuan', v: predStats.total.toLocaleString(), isNeutral: true },
                      { l: 'Kategori LAYAK', v: predStats.layak.toLocaleString(), isEmerald: true },
                      { l: 'Kategori TIDAK LAYAK', v: predStats.tidakLayak.toLocaleString(), isRose: true },
                      { l: 'Tingkat Kelayakan Pinjaman', v: `${predStats.approvalRate}%`, isNeutral: true },
                    ].map((c, i) => {
                      let borderColor = 'border-sky-100/30 dark:border-sky-800/10';
                      let accentBar = 'bg-sky-500/80';
                      if (c.isEmerald) {
                        borderColor = 'border-emerald-200/50 dark:border-emerald-900/20';
                        accentBar = 'bg-emerald-500';
                      } else if (c.isRose) {
                        borderColor = 'border-rose-200/50 dark:border-rose-900/20';
                        accentBar = 'bg-rose-500';
                      }
                      return (
                        <div key={i} className={`glass-card-static rounded-3xl p-6 text-center relative overflow-hidden shadow-sm border ${borderColor}`} style={{ boxShadow: '0 4px 20px rgba(14,165,233,0.02)' }}>
                          <div className={`absolute top-0 left-0 right-0 h-[3px] ${accentBar}`} />
                          <p className="text-[10px] font-bold text-sky-500/70 uppercase tracking-wider mb-1">{c.l}</p>
                          <p className="text-3xl font-black text-sky-955 dark:text-sky-50">{c.v}</p>
                        </div>
                      );
                    })}
                  </div>

                  {/* Charts */}
                  <div className="grid grid-cols-1 lg:grid-cols-2 gap-8">
                    <PieChart
                      title="Hasil Evaluasi Skoring Berjalan"
                      data={[
                        { label: 'LAYAK (Disetujui)', value: predStats.layak, color: '#10b981' },
                        { label: 'TIDAK LAYAK (Ditolak)', value: predStats.tidakLayak, color: '#ef4444' },
                      ]}
                    />
                    <BarChart title="Status Pekerjaan Pemohon" data={mappedUserEmploymentData} />
                  </div>

                  {/* Table with spacious layout */}
                  <div className="pt-4">
                    <DataTable
                      columns={predColumns}
                      data={predTableData}
                      searchKeys={['result', 'loanPurpose', 'employment', 'fullName', 'email', 'phone', 'address']}
                      pageSize={10}
                      emptyMessage="Belum ada data pengajuan"
                    />
                  </div>
                </div>
              )}
            </section>
          )}

          <div className="h-8" />
        </div>
      </main>
    </div>
  );
}
