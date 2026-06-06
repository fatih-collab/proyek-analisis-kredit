'use client';

import React, { useState, useEffect } from 'react';
import { Brain, ArrowRight, CheckCircle2, XCircle, TrendingUp, DollarSign, Clock, User, Home as HomeIcon, CreditCard, BarChart3, RefreshCw, ChevronRight, Sparkles, ArrowLeft, FileCheck, AlertCircle, Banknote, Calculator, ShieldCheck, Zap } from 'lucide-react';
import { useRouter } from 'next/navigation';
import Link from 'next/link';
import { useAuth, PredictionResult } from '../context/AuthContext';
import Header from '../components/Header';

/* ─── Confetti effect ─── */
function Confetti() {
  const colors = ['#0ea5e9', '#6366f1', '#8b5cf6', '#10b981', '#f59e0b', '#ec4899'];
  return (
    <div className="fixed inset-0 pointer-events-none z-[999]">
      {Array.from({ length: 45 }).map((_, i) => (
        <div key={i} className="confetti-piece" style={{
          left: `${Math.random() * 100}%`,
          width: `${6 + Math.random() * 8}px`,
          height: `${6 + Math.random() * 8}px`,
          background: colors[Math.floor(Math.random() * colors.length)],
          borderRadius: Math.random() > 0.5 ? '50%' : '2px',
          animationDuration: `${2 + Math.random() * 2}s`,
          animationDelay: `${Math.random() * 0.8}s`,
        }} />
      ))}
    </div>
  );
}

/* ─── Credit Scanner SVG Animation (Replacing NeuralNetworkAnim) ─── */
function FinanceScannerAnim() {
  return (
    <div className="relative w-64 h-36 mx-auto flex flex-col items-center justify-center bg-slate-50/40 dark:bg-slate-900/10 border border-slate-200/50 dark:border-slate-800/40 rounded-2xl p-4 shadow-inner overflow-hidden select-none">
      {/* Laser scan line */}
      <div className="absolute left-0 right-0 h-[2px] bg-gradient-to-r from-sky-400 via-indigo-500 to-sky-400 opacity-80 animate-[pulse_1.5s_ease-in-out_infinite]" />
      
      {/* Scanning financial doc representation */}
      <div className="flex items-center gap-3">
        <div className="p-3.5 rounded-xl bg-indigo-500/10 border border-indigo-500/30 text-indigo-600 dark:text-indigo-400 animate-pulse">
          <CreditCard className="w-8 h-8" />
        </div>
        <div className="space-y-1.5 text-left">
          <div className="w-24 h-2 rounded bg-slate-200 dark:bg-slate-800 animate-pulse" />
          <div className="w-16 h-1.5 rounded bg-slate-200/75 dark:bg-slate-800/75 animate-pulse" />
          <div className="w-20 h-1.5 rounded bg-slate-200/50 dark:bg-slate-800/50 animate-pulse" />
        </div>
      </div>
      <div className="mt-3 flex items-center gap-1.5 bg-emerald-500/10 text-emerald-600 dark:text-emerald-400 px-2.5 py-0.5 rounded-full text-[10px] font-black uppercase tracking-wider">
        <ShieldCheck className="w-3.5 h-3.5" /> Verifikasi Aman
      </div>
    </div>
  );
}

/* ─── Confidence Ring ─── */
function ConfidenceRing({ value, color }: { value: number; color: string }) {
  const r = 45, c = 2 * Math.PI * r;
  const offset = c - (value / 100) * c;
  return (
    <div className="relative w-28 h-28 flex items-center justify-center">
      <svg width="112" height="112" className="rotate-[-90deg] absolute">
        <circle cx="56" cy="56" r={r} fill="none" stroke="rgba(14,165,233,0.06)" strokeWidth="8" />
        <circle cx="56" cy="56" r={r} fill="none" stroke={color} strokeWidth="8" strokeLinecap="round"
          strokeDasharray={c} strokeDashoffset={offset}
          style={{ 
            transition: 'stroke-dashoffset 1.5s cubic-bezier(0.34,1.56,0.64,1)',
            filter: `drop-shadow(0 0 4px ${color}40)` 
          }} />
      </svg>
      <div className="absolute flex flex-col items-center justify-center">
        <span className="text-2xl font-black tracking-tight" style={{ color }}>{value}%</span>
        <span className="text-xs font-extrabold text-slate-400 dark:text-slate-500 uppercase tracking-widest mt-0.5">Trust Index</span>
      </div>
    </div>
  );
}

/* ─── Mock Credit Card Component ─── */
function CreditCardMockup({ userName, limit }: { userName: string; limit: number }) {
  return (
    <div className="relative overflow-hidden w-full h-56 rounded-[24px] p-6 bg-gradient-to-br from-slate-950 via-slate-900 to-indigo-950 border border-slate-800 text-white shadow-[0_20px_50px_rgba(0,0,0,0.3)] flex flex-col justify-between select-none group transition-all duration-500 hover:scale-[1.02] hover:shadow-[0_25px_60px_rgba(99,102,241,0.2)]">
      {/* Decorative Orbs inside card */}
      <div className="absolute top-[-30px] right-[-30px] w-28 h-28 rounded-full bg-gradient-to-br from-indigo-500/20 to-purple-500/20 blur-2xl pointer-events-none" />
      <div className="absolute bottom-[-20px] left-[20%] w-24 h-24 rounded-full bg-gradient-to-br from-emerald-500/10 to-teal-500/10 blur-xl pointer-events-none" />
      
      {/* Upper row: Chip + Brand */}
      <div className="flex justify-between items-start z-10">
        <div>
          {/* EMV Gold Chip Mockup */}
          <div className="w-11 h-8 rounded-md bg-gradient-to-br from-amber-200 via-yellow-400 to-amber-300 border border-amber-600/30 flex flex-col justify-around p-1 shadow-inner relative">
            <div className="w-full h-[1px] bg-amber-700/20" />
            <div className="w-full h-[1px] bg-amber-700/20" />
            <div className="w-full h-[1px] bg-amber-700/20" />
            <div className="absolute left-[35%] top-0 bottom-0 w-[1px] bg-amber-700/20" />
            <div className="absolute right-[35%] top-0 bottom-0 w-[1px] bg-amber-700/20" />
          </div>
          {/* Wireless signal icon */}
          <svg className="w-5 h-5 text-slate-400/80 mt-2 rotate-90 ml-1" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth="2">
            <path strokeLinecap="round" strokeLinejoin="round" d="M12 18h.01M8 21h8M12 3v10m-3-3l3-3 3 3" />
          </svg>
        </div>
        <div className="text-right">
          <div className="flex items-center gap-1.5 justify-end">
            <CreditCard className="w-4 h-4 text-sky-400" />
            <span className="text-xs font-black tracking-[0.1em] text-slate-200 uppercase">KreditCerdas</span>
          </div>
          <span className="text-[9px] font-bold text-sky-400/60 uppercase tracking-widest">Premium Active</span>
        </div>
      </div>

      {/* Middle row: Credit Limit Balance */}
      <div className="z-10">
        <span className="text-xs font-black text-slate-400/80 uppercase tracking-widest">Prosper Recommended Limit</span>
        <div className="text-3xl font-black text-emerald-400 tracking-tight mt-0.5 filter drop-shadow-[0_0_8px_rgba(16,185,129,0.3)]">
          ${limit.toLocaleString('en-US')}
        </div>
      </div>

      {/* Lower row: User name & Verification badge */}
      <div className="flex justify-between items-end z-10">
        <div>
          <span className="text-[9px] font-bold text-slate-500 uppercase tracking-wider block">Cardholder</span>
          <span className="text-xs font-bold uppercase tracking-wider text-slate-200">{userName || 'Kreditor Terdaftar'}</span>
        </div>
        <div className="flex items-center gap-1 bg-emerald-500/10 border border-emerald-500/25 px-2.5 py-1 rounded-full shadow-inner">
          <ShieldCheck className="w-3 h-3 text-emerald-400" />
          <span className="text-[10px] font-extrabold text-emerald-400 uppercase tracking-wider">Verified Score</span>
        </div>
      </div>
    </div>
  );
}

/* ═══ MAIN ═══ */
export default function PredictPage() {
  const { user, isLoggedIn, isLoading, addPrediction } = useAuth();
  const router = useRouter();
  const [step, setStep] = useState<'form' | 'loading' | 'result'>('form');
  const [result, setResult] = useState<PredictionResult | null>(null);
  const [showConfetti, setShowConfetti] = useState(false);
  const [loadingProgress, setLoadingProgress] = useState(0);
  const [loadingText, setLoadingText] = useState('');

  const [form, setForm] = useState({
    age: '', gender: '', maritalStatus: '', dependents: '',
    education: '', employment: '', monthlyIncome: '', additionalIncome: '',
    loanAmount: '', loanTerm: '', interestRate: '', loanPurpose: '',
    propertyArea: '', creditHistory: 'Baik', coApplicantIncome: '0',
    existingInstallments: '0',
  });

  useEffect(() => {
    if (!isLoading && !isLoggedIn) { router.push('/login'); return; }
    if (user?.profile && !user.profile.profileCompleted) { router.push('/profile'); return; }
    if (user?.profile) {
      setForm(f => ({ ...f, age: user.profile.age || '', gender: user.profile.gender || '', maritalStatus: user.profile.maritalStatus || '', dependents: user.profile.dependents || '0', education: user.profile.education || '', employment: user.profile.employment || '', monthlyIncome: user.profile.monthlyIncome || '', additionalIncome: user.profile.additionalIncome || '0', existingInstallments: user.profile.existingInstallments || '0' }));
    }
  }, [user, isLoggedIn, isLoading, router]);

  const handlePredict = async (e: React.FormEvent) => {
    e.preventDefault();
    setStep('loading');
    setLoadingProgress(0);

    const msgs = [
      'Menghubungkan ke server skoring...',
      'Preprocessing data nasabah...',
      'Menjalankan model klasifikasi...',
      'Menghitung plafon dengan model regresi...',
      'Menghitung cicilan anuitas...',
      'Menyusun laporan kredit...',
    ];
    let msgIdx = 0;
    setLoadingText(msgs[0]);
    const msgInterval = setInterval(() => {
      msgIdx++;
      if (msgIdx < msgs.length) setLoadingText(msgs[msgIdx]);
    }, 600);
    const progInterval = setInterval(() => {
      setLoadingProgress(p => Math.min(p + Math.random() * 12, 90));
    }, 400);

    try {
      const payload = {
        ...form,
        fullName: user?.profile?.fullName || user?.fullName || '',
        email: user?.profile?.email || user?.email || '',
        phone: user?.profile?.phone || '',
        address: user?.profile?.address || '',
      };

      const response = await fetch('http://localhost:8000/predict', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(payload),
      });

      clearInterval(msgInterval);
      clearInterval(progInterval);
      setLoadingProgress(100);

      if (!response.ok) {
        const err = await response.json();
        throw new Error(err.detail || 'Gagal menghubungi server');
      }

      const data = await response.json();

      const pred: PredictionResult = {
        id: `pred_${Date.now()}`,
        date: new Date().toISOString(),
        loanAmount: form.loanAmount,
        loanTerm: form.loanTerm,
        interestRate: data.bunga_persen || form.interestRate || '0',
        result: data.result,
        confidence: data.confidence,
        inputData: { ...form },
        plafon: data.plafon,
        bungaPersen: data.bunga_persen,
        bungaRate: data.bunga_rate,
        cicilanPerBulan: data.cicilan_per_bulan,
        totalBunga: data.total_bunga,
        totalBayar: data.total_bayar,
        sisaPlafon: data.sisa_plafon,
        nominalDicairkan: data.nominal_dicairkan,
        catatanRisiko: data.catatan_risiko,
        alasanPenolakan: data.alasan_penolakan,
      };

      addPrediction(pred);
      setResult(pred);
      setStep('result');
      if (data.result === 'LAYAK') {
        setShowConfetti(true);
        setTimeout(() => setShowConfetti(false), 4000);
      }
    } catch (err: unknown) {
      clearInterval(msgInterval);
      clearInterval(progInterval);
      const errorMsg = err instanceof Error ? err.message : 'Tidak dapat terhubung ke server backend.';
      alert(`❌ Error: ${errorMsg}\n\nPastikan backend FastAPI berjalan di http://localhost:8000`);
      setStep('form');
      setLoadingProgress(0);
    }
  };

  if (isLoading) return (
    <div className="min-h-screen flex items-center justify-center bg-slate-50 dark:bg-slate-950">
      <div className="w-12 h-12 border-[3px] border-sky-100 border-t-sky-600 rounded-full animate-spin" />
    </div>
  );

  return (
    <div className="min-h-screen relative transition-colors duration-300 bg-slate-50 dark:bg-slate-950 noise-overlay">
      <div className="gradient-mesh" />
      <div className="orb orb-1" />
      <div className="orb orb-2" />
      <Header />
      {showConfetti && <Confetti />}

      <div className="relative z-10 w-full mx-auto px-6 pt-32 pb-20">
        
        {/* ═══ FORM STEP ═══ */}
        {step === 'form' && (
          <div className="reveal-up visible max-w-5xl mx-auto">
            {/* Header */}
            <div className="text-center mb-8">

              <h1 className="text-4xl font-black text-slate-900 dark:text-white tracking-tight mb-2">Simulasi Kelayakan</h1>
              <p className="text-slate-500 dark:text-slate-400 text-base max-w-lg mx-auto">Masukkan rencana pinjaman untuk dianalisis oleh KreditCerdas AI Engine</p>
            </div>

            {/* Info boxes — side by side */}
            <div className="grid grid-cols-1 md:grid-cols-2 gap-4 mb-8">
              {/* Autofill box */}
              <div className="bg-white/70 dark:bg-slate-900/70 border border-slate-200/50 dark:border-slate-800/50 rounded-2xl p-5 flex items-center gap-4 shadow-sm transition-all hover:bg-white dark:hover:bg-slate-900">
                <div className="w-10 h-10 rounded-2xl bg-emerald-500/10 flex items-center justify-center flex-shrink-0">
                  <User className="w-5 h-5 text-emerald-600 dark:text-emerald-400" />
                </div>
                <p className="text-sm md:text-base font-extrabold text-slate-600 dark:text-slate-400">Data profil Anda telah dimuat secara otomatis dari akun ✓</p>
              </div>

              {/* USD Warning box */}
              <div className="bg-amber-500/5 dark:bg-amber-500/10 border border-amber-500/20 rounded-2xl p-5 flex items-center gap-4 transition-all hover:bg-amber-500/[0.08]">
                <div className="w-10 h-10 rounded-2xl bg-amber-500/15 flex items-center justify-center flex-shrink-0 text-amber-600 dark:text-amber-400">
                  <Zap className="w-5 h-5" />
                </div>
                <div>
                  <p className="text-sm md:text-base font-black text-amber-800 dark:text-amber-400">Parameter Risiko Prosper (USD)</p>
                  <p className="text-xs md:text-sm text-amber-700/70 dark:text-amber-500/50 mt-0.5 leading-relaxed">Model penilaian kami diselaraskan dengan pasar Prosper (Amerika Serikat). Masukkan nominal gaji & pinjaman dalam satuan Dolar (USD). Contoh: Gaji $3,000, Pinjaman $2,000.</p>
                </div>
              </div>
            </div>

            {/* Main Form container */}
            <div className="bg-white/80 dark:bg-slate-900/80 border border-slate-200/50 dark:border-slate-800/50 rounded-[32px] overflow-hidden p-8 md:p-10 shadow-2xl relative backdrop-blur-xl">
              <form onSubmit={handlePredict} className="space-y-8">
                <div className="grid grid-cols-1 md:grid-cols-2 gap-6 md:gap-8">
                  {/* Field 1: Jumlah Pinjaman */}
                  <div className="space-y-3">
                    <label className="block text-sm md:text-base font-black text-slate-700 dark:text-slate-300 tracking-wider uppercase">
                      Jumlah Pinjaman ($) <span className="text-red-500 font-black">*</span>
                    </label>
                    <div className="relative">
                      <DollarSign className="absolute left-4.5 top-1/2 -translate-y-1/2 w-5.5 h-5.5 text-slate-400/60" />
                      <input
                        type="number"
                        required
                        value={form.loanAmount}
                        onChange={(e) => setForm(prev => ({ ...prev, loanAmount: e.target.value }))}
                        className="w-full pl-13 pr-5 py-4 rounded-2xl bg-slate-50/50 dark:bg-slate-950/50 border border-slate-200 dark:border-slate-800 text-slate-900 dark:text-slate-100 text-lg font-bold placeholder:text-slate-400/50 transition-all duration-300 focus:bg-white dark:focus:bg-slate-950 focus:ring-2 focus:ring-indigo-500/20 focus:border-indigo-500 outline-none"
                        placeholder="Contoh: 5000"
                      />
                    </div>
                  </div>

                  {/* Field 2: Tenor (Bulan) */}
                  <div className="space-y-3">
                    <label className="block text-sm md:text-base font-black text-slate-700 dark:text-slate-300 tracking-wider uppercase">
                      Tenor (Bulan) <span className="text-red-500 font-black">*</span>
                    </label>
                    <div className="relative">
                      <Clock className="absolute left-4.5 top-1/2 -translate-y-1/2 w-5.5 h-5.5 text-slate-400/60" />
                      <input
                        type="number"
                        required
                        value={form.loanTerm}
                        onChange={(e) => setForm(prev => ({ ...prev, loanTerm: e.target.value }))}
                        className="w-full pl-13 pr-5 py-4 rounded-2xl bg-slate-50/50 dark:bg-slate-950/50 border border-slate-200 dark:border-slate-800 text-slate-900 dark:text-slate-100 text-lg font-bold placeholder:text-slate-400/50 transition-all duration-300 focus:bg-white dark:focus:bg-slate-950 focus:ring-2 focus:ring-indigo-500/20 focus:border-indigo-500 outline-none"
                        placeholder="12 / 36 / 60"
                      />
                    </div>
                  </div>

                  {/* Field 3: Tujuan Pinjaman */}
                  <div className="space-y-3">
                    <label className="block text-sm md:text-base font-black text-slate-700 dark:text-slate-300 tracking-wider uppercase">
                      Tujuan Pinjaman <span className="text-red-500 font-black">*</span>
                    </label>
                    <div className="relative">
                      <FileCheck className="absolute left-4.5 top-1/2 -translate-y-1/2 w-5.5 h-5.5 text-slate-400/60" />
                      <select
                        required
                        value={form.loanPurpose}
                        onChange={(e) => setForm(prev => ({ ...prev, loanPurpose: e.target.value }))}
                        className="w-full pl-13 pr-10 py-4 rounded-2xl bg-slate-50/50 dark:bg-slate-950/50 border border-slate-200 dark:border-slate-800 text-slate-900 dark:text-slate-100 text-lg font-bold transition-all duration-300 focus:bg-white dark:focus:bg-slate-950 focus:ring-2 focus:ring-indigo-500/20 focus:border-indigo-500 outline-none appearance-none"
                      >
                        <option value="">Pilih Tujuan Pinjaman</option>
                        <option value="Modal Usaha">Modal Usaha</option>
                        <option value="Pendidikan">Pendidikan</option>
                        <option value="Renovasi Rumah">Renovasi Rumah</option>
                        <option value="Kendaraan">Kendaraan</option>
                        <option value="Kesehatan">Kesehatan</option>
                        <option value="Lainnya">Lainnya</option>
                      </select>
                      <div className="absolute right-5 top-1/2 -translate-y-1/2 pointer-events-none text-slate-400 dark:text-slate-600 text-xs">
                        ▼
                      </div>
                    </div>
                  </div>

                  {/* Field 4: Area Tempat Tinggal (Lokasi & Area) */}
                  <div className="space-y-3">
                    <label className="block text-sm md:text-base font-black text-slate-700 dark:text-slate-300 tracking-wider uppercase">
                      Area Tempat Tinggal (Lokasi & Area) <span className="text-red-500 font-black">*</span>
                    </label>
                    <div className="relative">
                      <HomeIcon className="absolute left-4.5 top-1/2 -translate-y-1/2 w-5.5 h-5.5 text-slate-400/60" />
                      <select
                        required
                        value={form.propertyArea}
                        onChange={(e) => setForm(prev => ({ ...prev, propertyArea: e.target.value }))}
                        className="w-full pl-13 pr-10 py-4 rounded-2xl bg-slate-50/50 dark:bg-slate-950/50 border border-slate-200 dark:border-slate-800 text-slate-900 dark:text-slate-100 text-lg font-bold transition-all duration-300 focus:bg-white dark:focus:bg-slate-950 focus:ring-2 focus:ring-indigo-500/20 focus:border-indigo-500 outline-none appearance-none"
                      >
                        <option value="">Pilih Area Tempat Tinggal</option>
                        <option value="Urban">Urban</option>
                        <option value="Semiurban">Semiurban</option>
                        <option value="Rural">Rural</option>
                      </select>
                      <div className="absolute right-5 top-1/2 -translate-y-1/2 pointer-events-none text-slate-400 dark:text-slate-600 text-xs">
                        ▼
                      </div>
                    </div>
                  </div>
                </div>

                {/* Submit button */}
                <div className="pt-4">
                  <button type="submit"
                    className="w-full group flex items-center justify-center gap-2.5 px-8 py-[18px] rounded-2xl bg-indigo-600 hover:bg-indigo-700 text-white font-black text-lg tracking-wider uppercase transition-all duration-300 hover:-translate-y-0.5 shadow-lg shadow-indigo-600/25 active:translate-y-0">
                    <FileCheck className="w-5.5 h-5.5" /> Jalankan Skoring Kredit <ShieldCheck className="w-5.5 h-5.5" />
                  </button>
                </div>
              </form>
            </div>
          </div>
        )}

        {/* ═══ LOADING STEP ═══ */}
        {step === 'loading' && (
          <div className="flex flex-col items-center justify-center min-h-[60vh] gap-6 animate-pulse">
            <div className="bg-white/80 dark:bg-slate-900/80 border border-slate-200/50 dark:border-slate-800/50 rounded-[32px] p-8 text-center w-full max-w-md shadow-xl backdrop-blur-xl">
              <div className="mb-6"><FinanceScannerAnim /></div>
              <div className="w-16 h-16 rounded-2xl bg-gradient-to-br from-indigo-500 to-purple-600 flex items-center justify-center mx-auto mb-5 shadow-lg animate-bounce">
                <ShieldCheck className="w-8 h-8 text-white" />
              </div>
              <h2 className="text-2xl font-black text-slate-900 dark:text-white mb-1">Mengevaluasi Risiko</h2>
              <p className="text-sm text-indigo-500/80 font-bold mb-6 h-4">{loadingText}</p>
              {/* Neon Progress Bar */}
              <div className="w-full h-2 rounded-full bg-slate-100 dark:bg-slate-800 overflow-hidden mb-2 relative">
                <div className="h-full rounded-full transition-all duration-500 ease-out bg-gradient-to-r from-sky-400 via-indigo-500 to-purple-600" style={{ width: `${loadingProgress}%` }} />
              </div>
              <p className="text-sm font-black text-slate-400 tabular-nums">{Math.round(loadingProgress)}%</p>
            </div>
          </div>
        )}

        {/* ═══ RESULT STEP (FULLSCREEN WIDESCREEN DASHBOARD LAYOUT) ═══ */}
        {step === 'result' && result && (
          <div className="animate-result-reveal max-w-[1400px] mx-auto">
            
            {/* ── ROW 1: VERDICT HERO — Full Width Horizontal ── */}
            <div className={`rounded-[32px] p-8 md:p-10 relative overflow-hidden border mb-6 shadow-xl backdrop-blur-xl bg-white/80 dark:bg-slate-900/80 ${
              result.result === 'LAYAK' ? 'border-emerald-500/20' : 'border-rose-500/20'
            }`}>
              {/* Blurred background radial glow */}
              <div className={`absolute top-[-50px] left-[30%] w-64 h-64 rounded-full blur-[100px] pointer-events-none opacity-30 ${
                result.result === 'LAYAK' ? 'bg-emerald-400' : 'bg-rose-400'
              }`} />
              
              <div className="relative flex flex-col md:flex-row items-center gap-8">
                {/* Left: Status text */}
                <div className="flex-1 text-center md:text-left">
                  <div className={`inline-flex items-center gap-1.5 px-4 py-1.5 rounded-full text-xs font-black uppercase tracking-widest border mb-4 ${
                    result.result === 'LAYAK' 
                      ? 'bg-emerald-500/10 text-emerald-600 dark:text-emerald-400 border-emerald-500/25 shadow-[0_0_12px_rgba(16,185,129,0.15)]' 
                      : 'bg-rose-500/10 text-rose-600 dark:text-rose-400 border-rose-500/25 shadow-[0_0_12px_rgba(239,68,68,0.15)]'
                  }`}>
                    <span className={`w-1.5 h-1.5 rounded-full ${
                      result.result === 'LAYAK' ? 'bg-emerald-500 animate-ping' : 'bg-rose-500 animate-ping'
                    }`} />
                    {result.result === 'LAYAK' ? 'Kesiapan Pengajuan Tinggi' : 'Kesiapan Pengajuan Rendah'}
                  </div>

                  <h1 className="text-4xl md:text-5xl font-black tracking-tight text-slate-900 dark:text-white mb-3 leading-none">
                    Rekomendasi Prosper: {result.result === 'LAYAK' ? 'Kategori A/Lancar ✓' : 'Kategori Berisiko ✗'}
                  </h1>
                  
                  <p className="text-slate-500 dark:text-slate-400 text-base font-semibold max-w-lg leading-relaxed">
                    {result.result === 'LAYAK'
                      ? 'Selamat! Hasil asesmen KreditCerdas menyatakan profil Anda memiliki kesiapan tinggi dan risiko rendah untuk diajukan ke Prosper.'
                      : 'Berdasarkan analisis KreditCerdas, profil Anda memiliki rasio risiko yang cukup tinggi untuk diajukan ke Prosper saat ini.'}
                  </p>

                  {result.catatanRisiko && (
                    <span className="inline-flex mt-4 px-3 py-1.5 rounded-full bg-slate-100 dark:bg-slate-800 text-slate-600 dark:text-slate-300 text-sm font-bold border border-slate-200/50 dark:border-slate-700/50 shadow-inner">
                      {result.catatanRisiko}
                    </span>
                  )}
                </div>

                {/* Right: Confidence Ring */}
                <div className="flex-shrink-0 bg-slate-50/50 dark:bg-slate-950/30 border border-slate-200/50 dark:border-slate-800/50 rounded-[24px] p-6 md:p-8 flex flex-col items-center justify-center select-none">
                  <ConfidenceRing value={result.confidence} color={result.result === 'LAYAK' ? '#10b981' : '#ef4444'} />
                  <p className="text-xs font-black text-slate-400 dark:text-slate-500 uppercase tracking-widest mt-3">Statistical Accuracy</p>
                </div>
              </div>
            </div>

            {/* ── ROW 2: TWO-COLUMN DASHBOARD GRID ── */}
            <div className="grid grid-cols-1 lg:grid-cols-5 gap-6 mb-6">
              
              {/* LEFT COLUMN (2/5) — Credit Card OR Analysis Summary */}
              <div className="lg:col-span-2 flex flex-col gap-6">
                {result.result === 'LAYAK' && result.plafon ? (
                  <CreditCardMockup userName={user?.fullName || ''} limit={result.plafon} />
                ) : (
                  <div className="bg-white/80 dark:bg-slate-900/80 border border-slate-200/50 dark:border-slate-800/50 rounded-[28px] p-6 space-y-2.5 shadow-md flex-1">
                    <h3 className="text-sm font-black text-slate-800 dark:text-slate-200 flex items-center gap-1.5 mb-3 uppercase tracking-wider">
                      <BarChart3 className="w-4 h-4 text-indigo-500" /> Ringkasan Analisis
                    </h3>
                    {[
                      { l: 'Rencana Pinjaman', v: `$${parseInt(result.loanAmount || '0').toLocaleString('en-US')}` },
                      { l: 'Tenor Rencana', v: `${result.loanTerm} Bulan` },
                      { l: 'Tujuan Pinjaman', v: result.inputData.loanPurpose },
                      { l: 'Riwayat Kredit', v: result.inputData.creditHistory },
                    ].map((r, i) => (
                      <div key={i} className="flex justify-between text-sm py-2 border-b border-slate-100 dark:border-slate-800/50 last:border-0">
                        <span className="text-slate-500 dark:text-slate-500 font-semibold">{r.l}</span>
                        <span className="font-extrabold text-slate-900 dark:text-white">{r.v}</span>
                      </div>
                    ))}
                  </div>
                )}

                {/* Action Buttons — stacked under the card */}
                <div className="flex gap-3">
                  <button onClick={() => { setStep('form'); setResult(null); }}
                    className="flex-1 flex items-center justify-center gap-2 px-5 py-3.5 rounded-xl text-white font-black text-sm tracking-wider uppercase bg-indigo-600 hover:bg-indigo-700 transition-all hover:-translate-y-0.5 shadow-md shadow-indigo-600/10">
                    <RefreshCw className="w-3.5 h-3.5" /> Analisis Ulang
                  </button>
                  <Link href="/dashboard" className="flex-1 flex items-center justify-center gap-2 px-5 py-3.5 rounded-xl font-black text-sm tracking-wider uppercase bg-white dark:bg-slate-900 border border-slate-200 dark:border-slate-800 text-slate-700 dark:text-slate-300 hover:bg-slate-50 dark:hover:bg-slate-950 transition-all hover:-translate-y-0.5 shadow-sm">
                    Dashboard <ChevronRight className="w-4 h-4" />
                  </Link>
                </div>
              </div>

              {/* RIGHT COLUMN (3/5) — Payment Details OR Rejection Reasons */}
              <div className="lg:col-span-3 flex flex-col gap-6">

                {/* IF APPROVED: Detailed payment metrics */}
                {result.result === 'LAYAK' && result.plafon && (
                  <div className="bg-white/80 dark:bg-slate-900/80 border border-slate-200/50 dark:border-slate-800/50 rounded-[28px] p-6 md:p-8 shadow-md flex-1">
                    <h3 className="text-base font-black text-emerald-600 dark:text-emerald-400 flex items-center gap-1.5 mb-5 uppercase tracking-widest">
                      <Banknote className="w-5 h-5" /> Simulasi & Rekomendasi Prosper
                    </h3>
                    
                    {/* Nominal and Term Pill Cards — 3 columns */}
                    <div className="grid grid-cols-2 md:grid-cols-4 gap-3 mb-5">
                      <div className="rounded-2xl p-4 text-center bg-slate-50/50 dark:bg-slate-950/30 border border-slate-200/50 dark:border-slate-800/50">
                        <p className="text-xs font-black text-slate-400 dark:text-slate-500 uppercase tracking-widest mb-1">Nominal Dicairkan</p>
                        <p className="text-2xl font-black text-indigo-600 dark:text-indigo-400">
                          ${(result.nominalDicairkan || 0).toLocaleString('en-US')}
                        </p>
                      </div>
                      <div className="rounded-2xl p-4 text-center bg-slate-50/50 dark:bg-slate-950/30 border border-slate-200/50 dark:border-slate-800/50">
                        <p className="text-xs font-black text-slate-400 dark:text-slate-500 uppercase tracking-widest mb-1">Tenor Kredit</p>
                        <p className="text-2xl font-black text-slate-800 dark:text-slate-100">
                          {result.loanTerm} <span className="text-sm font-semibold text-slate-500">Bulan</span>
                        </p>
                      </div>
                      <div className="rounded-2xl p-4 text-center bg-slate-50/50 dark:bg-slate-950/30 border border-slate-200/50 dark:border-slate-800/50">
                        <p className="text-xs font-black text-slate-400 dark:text-slate-500 uppercase tracking-widest mb-1">Cicilan / Bulan</p>
                        <p className="text-2xl font-black text-sky-600 dark:text-sky-400">
                          ${(result.cicilanPerBulan || 0).toLocaleString('en-US', { minimumFractionDigits: 0, maximumFractionDigits: 0 })}
                        </p>
                      </div>
                      <div className="rounded-2xl p-4 text-center bg-slate-50/50 dark:bg-slate-950/30 border border-slate-200/50 dark:border-slate-800/50">
                        <p className="text-xs font-black text-slate-400 dark:text-slate-500 uppercase tracking-widest mb-1">Suku Bunga (APR)</p>
                        <p className="text-2xl font-black text-amber-600 dark:text-amber-400">
                          {result.bungaPersen || '-'}
                        </p>
                      </div>
                    </div>

                    {/* Visual Limit Allocation Bar */}
                    {(() => {
                      const totalPlafon = result.plafon || 0;
                      const usedAmount = result.nominalDicairkan || 0;
                      const remainingLimit = result.sisaPlafon || 0;
                      const usedPercent = totalPlafon > 0 ? Math.min(100, Math.max(0, (usedAmount / totalPlafon) * 100)) : 0;
                      const remainingPercent = 100 - usedPercent;
                      
                      return (
                        <div className="bg-slate-50/70 dark:bg-slate-950/20 border border-slate-200/50 dark:border-slate-800/50 rounded-2xl p-5 mb-5 space-y-3">
                          <div className="flex justify-between items-center">
                            <span className="font-extrabold text-slate-600 dark:text-slate-400 uppercase tracking-widest text-xs">Alokasi Limit Kredit</span>
                            <span className="font-black text-sm text-indigo-600 dark:text-indigo-400">{Math.round(usedPercent)}% Terpakai</span>
                          </div>
                          
                          <div className="w-full h-3.5 rounded-full bg-slate-200/60 dark:bg-slate-800 overflow-hidden flex">
                            <div className="h-full bg-gradient-to-r from-rose-500 to-indigo-600 transition-all duration-1000 ease-out" style={{ width: `${usedPercent}%` }} />
                            <div className="h-full bg-emerald-500 transition-all duration-1000 ease-out" style={{ width: `${remainingPercent}%` }} />
                          </div>
                          
                          <div className="grid grid-cols-3 gap-2 text-center pt-1">
                            <div className="flex flex-col">
                              <span className="text-slate-400 dark:text-slate-500 font-bold uppercase tracking-wider text-xs">Total Limit (Plafon)</span>
                              <span className="font-black text-sm text-slate-800 dark:text-slate-200">${totalPlafon.toLocaleString('en-US')}</span>
                            </div>
                            <div className="flex flex-col border-x border-slate-200/50 dark:border-slate-800/50">
                              <span className="text-rose-500/80 font-bold uppercase tracking-wider text-xs">Telah Digunakan</span>
                              <span className="font-black text-sm text-rose-600 dark:text-rose-400">${usedAmount.toLocaleString('en-US')}</span>
                            </div>
                            <div className="flex flex-col">
                              <span className="text-emerald-500 font-bold uppercase tracking-wider text-xs">Sisa Limit Tersedia</span>
                              <span className="font-black text-sm text-emerald-500">${remainingLimit.toLocaleString('en-US')}</span>
                            </div>
                          </div>
                        </div>
                      );
                    })()}

                    {/* Tagihan details — 2-column grid */}
                    <div className="grid grid-cols-1 md:grid-cols-2 gap-x-6">
                      {[
                        { icon: DollarSign,  l: 'Total Beban Bunga',         v: `$${(result.totalBunga || 0).toLocaleString('en-US', { minimumFractionDigits: 0, maximumFractionDigits: 0 })}` },
                        { icon: BarChart3,   l: 'Total Pengembalian',        v: `$${(result.totalBayar || 0).toLocaleString('en-US', { minimumFractionDigits: 0, maximumFractionDigits: 0 })}` },
                        { icon: Banknote,    l: 'Sisa Saldo Plafon Kredit',  v: `$${(result.sisaPlafon || 0).toLocaleString('en-US', { minimumFractionDigits: 0, maximumFractionDigits: 0 })}` },
                      ].map((r, i) => (
                        <div key={i} className="flex items-center justify-between text-sm py-3 border-b border-slate-100 dark:border-slate-800/40 last:border-0">
                          <span className="flex items-center gap-2 text-slate-500 dark:text-slate-400 font-semibold">
                            <r.icon className="w-4 h-4 text-slate-400" /> {r.l}
                          </span>
                          <span className="font-extrabold text-slate-900 dark:text-slate-100">{r.v}</span>
                        </div>
                      ))}
                    </div>
                  </div>
                )}

                {/* IF REJECTED: Detailed credit policy warnings */}
                {result.result === 'TIDAK LAYAK' && result.alasanPenolakan && result.alasanPenolakan.length > 0 && (
                  <div className="bg-white/80 dark:bg-slate-900/80 border border-slate-200/50 dark:border-slate-800/50 rounded-[28px] p-6 md:p-8 shadow-md relative overflow-hidden flex-1">
                    <div className="absolute top-0 right-0 w-28 h-28 rounded-full bg-rose-500/5 blur-xl pointer-events-none" />
                    <h3 className="text-base font-black text-rose-600 dark:text-rose-400 flex items-center gap-1.5 mb-5 uppercase tracking-widest">
                      <AlertCircle className="w-5 h-5" /> Faktor Penghambat Kelayakan
                    </h3>
                    <ul className="space-y-4">
                      {result.alasanPenolakan.map((alasan, i) => (
                        <li key={i} className="flex items-start gap-3 text-base text-slate-600 dark:text-slate-300 font-semibold">
                          <span className="mt-0.5 w-6 h-6 rounded-lg bg-rose-500/10 text-rose-600 flex items-center justify-center flex-shrink-0 font-black text-xs">{i + 1}</span>
                          <div className="mt-0.5 leading-relaxed">{alasan}</div>
                        </li>
                      ))}
                    </ul>
                  </div>
                )}
              </div>

            </div>
          </div>
        )}

      </div>
    </div>
  );
}
