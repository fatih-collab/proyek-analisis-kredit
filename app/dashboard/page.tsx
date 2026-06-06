'use client';

import React, { useEffect } from 'react';
import { BarChart3, CreditCard, CheckCircle2, XCircle, Clock, TrendingUp, ArrowRight, Plus, Activity, Sparkles, Target } from 'lucide-react';
import Link from 'next/link';
import { useRouter } from 'next/navigation';
import { useAuth } from '../context/AuthContext';
import Header from '../components/Header';
import Footer from '../components/Footer';

export default function DashboardPage() {
  const { user, isLoggedIn, isLoading, predictions } = useAuth();
  const router = useRouter();

  useEffect(() => { if (!isLoading && !isLoggedIn) router.push('/login'); }, [isLoggedIn, isLoading, router]);

  if (isLoading) return <div className="min-h-screen flex items-center justify-center"><div className="w-10 h-10 border-3 border-sky-200 border-t-sky-500 rounded-full animate-spin-slow" /></div>;

  const total = predictions.length;
  const layak = predictions.filter(p => p.result === 'LAYAK').length;
  const tidakLayak = predictions.filter(p => p.result === 'TIDAK LAYAK').length;
  const avgConf = total > 0 ? Math.round(predictions.reduce((s, p) => s + p.confidence, 0) / total * 10) / 10 : 0;

  const cards = [
    { label: 'Total Prediksi', value: total, icon: BarChart3, gradient: 'from-cyan-400 to-blue-500', shadow: 'rgba(14,165,233,0.25)' },
    { label: 'Layak', value: layak, icon: CheckCircle2, gradient: 'from-emerald-400 to-green-500', shadow: 'rgba(16,185,129,0.25)' },
    { label: 'Tidak Layak', value: tidakLayak, icon: XCircle, gradient: 'from-red-400 to-rose-500', shadow: 'rgba(239,68,68,0.25)' },
    { label: 'Avg Confidence', value: `${avgConf}%`, icon: Target, gradient: 'from-indigo-400 to-purple-500', shadow: 'rgba(99,102,241,0.25)' },
  ];

  return (
    <div className="min-h-screen relative transition-colors duration-300 noise-overlay">
      <div className="gradient-mesh" /><div className="orb orb-1" /><div className="orb orb-2" />
      <Header />

      <div className="relative z-10 max-w-5xl mx-auto px-4 pt-28 pb-16">
        {/* Header row */}
        <div className="flex flex-col sm:flex-row items-start sm:items-center justify-between mb-8 gap-4">
          <div>

            <h1 className="text-2xl md:text-3xl font-black text-sky-950 dark:text-sky-100" style={{ letterSpacing: '-0.03em' }}>Halo, {user?.fullName}! 👋</h1>
            <p className="text-sm text-sky-700/50 dark:text-sky-300/40 mt-1">Lihat ringkasan dan riwayat prediksi Anda</p>
          </div>
          <Link href="/predict" className="group inline-flex items-center gap-2 px-6 py-3 rounded-2xl text-white font-bold text-sm transition-all duration-300 hover:-translate-y-0.5"
            style={{ background: 'linear-gradient(135deg, #0ea5e9, #6366f1)', boxShadow: '0 6px 24px rgba(14,165,233,0.3)' }}>
            <Plus className="w-4 h-4" /> Prediksi Baru
          </Link>
        </div>

        {/* Summary Cards */}
        <div className="grid grid-cols-2 lg:grid-cols-4 gap-3 lg:gap-4 mb-8">
          {cards.map((c, i) => (
            <div key={i} className="glass-card-static rounded-2xl p-5 relative overflow-hidden group" style={{ boxShadow: `0 4px 24px ${c.shadow.replace('0.25', '0.06')}` }}>
              <div className={`absolute top-0 left-0 right-0 h-[3px] bg-gradient-to-r ${c.gradient} opacity-60 group-hover:opacity-100 transition-opacity`} />
              <div className="flex items-start justify-between">
                <div>
                  <p className="text-2xl md:text-3xl font-black text-sky-900 dark:text-sky-100 tabular-nums" style={{ letterSpacing: '-0.03em' }}>{c.value}</p>
                  <p className="text-[10px] font-bold text-sky-500/60 dark:text-sky-400/50 uppercase tracking-wider mt-1">{c.label}</p>
                </div>
                <div className={`w-10 h-10 rounded-xl bg-gradient-to-br ${c.gradient} flex items-center justify-center flex-shrink-0 opacity-80`} style={{ boxShadow: `0 4px 12px ${c.shadow}` }}>
                  <c.icon className="w-5 h-5 text-white" />
                </div>
              </div>
            </div>
          ))}
        </div>

        {/* Profile check */}
        {user && !user.profile.profileCompleted && (
          <div className="glass-card-static rounded-2xl px-5 py-4 mb-6 flex items-center gap-3" style={{ boxShadow: '0 4px 20px rgba(14,165,233,0.06)' }}>
            <div className="w-10 h-10 rounded-xl bg-gradient-to-br from-amber-400 to-orange-500 flex items-center justify-center flex-shrink-0"><Activity className="w-5 h-5 text-white" /></div>
            <div className="flex-1"><p className="text-sm font-bold text-sky-900 dark:text-sky-100">Profil Belum Lengkap</p><p className="text-xs text-sky-600/50 dark:text-sky-400/40">Lengkapi untuk gunakan fitur prediksi</p></div>
            <Link href="/profile" className="text-xs font-bold text-sky-500 hover:text-sky-700 flex items-center gap-1 transition-colors">Lengkapi <ArrowRight className="w-3 h-3" /></Link>
          </div>
        )}

        {/* Prediction History */}
        <div className="glass-card-static rounded-3xl overflow-hidden" style={{ boxShadow: '0 8px 40px rgba(14,165,233,0.06)' }}>
          <div className="px-6 py-4 border-b border-sky-100/30 dark:border-sky-800/20 flex items-center justify-between">
            <h2 className="text-sm font-black text-sky-900 dark:text-sky-100 flex items-center gap-2"><Clock className="w-4 h-4 text-sky-500" /> Riwayat Prediksi</h2>
            <span className="text-[10px] font-bold text-sky-400/50 px-2.5 py-1 rounded-full bg-sky-100/40 dark:bg-sky-800/20">{total} data</span>
          </div>

          {predictions.length === 0 ? (
            <div className="px-6 py-20 text-center">
              <div className="w-20 h-20 rounded-3xl bg-gradient-to-br from-sky-100 to-indigo-100 dark:from-sky-900/30 dark:to-indigo-900/30 flex items-center justify-center mx-auto mb-5"><CreditCard className="w-10 h-10 text-sky-400/60" /></div>
              <h3 className="text-lg font-bold text-sky-900 dark:text-sky-100 mb-1">Belum Ada Prediksi</h3>
              <p className="text-sm text-sky-700/40 dark:text-sky-300/40 mb-6">Mulai prediksi kelayakan pinjaman pertama Anda</p>
              <Link href="/predict" className="inline-flex items-center gap-2 px-6 py-3 rounded-2xl text-white font-bold text-sm hover:-translate-y-0.5 transition-all"
                style={{ background: 'linear-gradient(135deg, #0ea5e9, #6366f1)', boxShadow: '0 6px 24px rgba(14,165,233,0.3)' }}>
                <CreditCard className="w-4 h-4" /> Mulai Prediksi
              </Link>
            </div>
          ) : (
            <div className="divide-y divide-sky-100/30 dark:divide-sky-800/20">
              {predictions.map((p, i) => (
                <div key={p.id} className="px-6 py-4 flex items-center gap-4 hover:bg-sky-50/30 dark:hover:bg-sky-900/10 transition-colors group">
                  <div className={`w-11 h-11 rounded-xl flex items-center justify-center flex-shrink-0 ${p.result === 'LAYAK' ? 'bg-gradient-to-br from-emerald-400 to-green-500' : 'bg-gradient-to-br from-red-400 to-rose-500'}`}
                    style={{ boxShadow: p.result === 'LAYAK' ? '0 4px 12px rgba(16,185,129,0.25)' : '0 4px 12px rgba(239,68,68,0.2)' }}>
                    {p.result === 'LAYAK' ? <CheckCircle2 className="w-5 h-5 text-white" /> : <XCircle className="w-5 h-5 text-white" />}
                  </div>
                  <div className="flex-1 min-w-0">
                    <div className="flex items-center gap-2 mb-0.5">
                      <span className={`text-[11px] font-extrabold px-2.5 py-0.5 rounded-lg ${p.result === 'LAYAK' ? 'bg-emerald-100/60 dark:bg-emerald-900/20 text-emerald-600 dark:text-emerald-400' : 'bg-red-100/60 dark:bg-red-900/20 text-red-500 dark:text-red-400'}`}>{p.result}</span>
                      <span className="text-[10px] font-bold text-sky-400/50 tabular-nums">{p.confidence}%</span>
                    </div>
                    <p className="text-xs text-sky-700/50 dark:text-sky-300/40 truncate">${parseInt(p.loanAmount).toLocaleString('en-US')} · {p.loanTerm} bulan · {p.inputData.loanPurpose}</p>
                  </div>
                  <div className="text-right flex-shrink-0">
                    <p className="text-[10px] text-sky-400/50 font-medium">{new Date(p.date).toLocaleDateString('id-ID', { day: '2-digit', month: 'short', year: 'numeric' })}</p>
                    <p className="text-[9px] text-sky-400/40">{new Date(p.date).toLocaleTimeString('id-ID', { hour: '2-digit', minute: '2-digit' })}</p>
                  </div>
                </div>
              ))}
            </div>
          )}
        </div>
      </div>

      <Footer />
    </div>
  );
}
