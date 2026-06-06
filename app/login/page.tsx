'use client';

import React, { useState } from 'react';
import { LogIn, Mail, Lock, ArrowRight, Eye, EyeOff, Sparkles } from 'lucide-react';
import Link from 'next/link';
import { useRouter } from 'next/navigation';
import { useAuth } from '../context/AuthContext';
import Header from '../components/Header';

export default function LoginPage() {
  const { login } = useAuth();
  const router = useRouter();
  const [form, setForm] = useState({ email: '', password: '' });
  const [showPw, setShowPw] = useState(false);
  const [error, setError] = useState('');
  const [loading, setLoading] = useState(false);

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault(); setError('');
    if (!form.email || !form.password) { setError('Email dan password wajib diisi'); return; }
    setLoading(true);
    const res = login(form.email, form.password);
    setLoading(false);
    if (res.success) router.push('/dashboard'); else setError(res.error || 'Login gagal');
  };

  return (
    <div className="min-h-screen relative transition-colors duration-300 noise-overlay">
      <div className="gradient-mesh" /><div className="orb orb-1" /><div className="orb orb-2" />
      <Header />
      <div className="relative z-10 flex items-center justify-center min-h-screen px-4 py-24">
        <div className="w-full max-w-md">
          <div className="text-center mb-6">

            <h1 className="text-2xl font-black text-sky-950 dark:text-sky-100" style={{ letterSpacing: '-0.03em' }}>Selamat Datang! 👋</h1>
            <p className="text-sm text-sky-700/50 dark:text-sky-300/40 mt-1">Login untuk melanjutkan</p>
          </div>

          <div className="gradient-border">
            <div className="glass-card-static rounded-[22px] p-6">
              <form onSubmit={handleSubmit} className="space-y-4">
                {error && <div className="px-4 py-3 rounded-xl bg-red-50/80 dark:bg-red-900/20 border border-red-200/50 dark:border-red-800/30 text-red-500 text-sm font-medium">{error}</div>}
                <div>
                  <label className="block text-xs font-bold text-sky-700 dark:text-sky-300 mb-1.5">Email</label>
                  <div className="relative">
                    <Mail className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-sky-400/60" />
                    <input type="email" value={form.email} onChange={(e) => setForm(f => ({ ...f, email: e.target.value }))}
                      className="w-full pl-10 pr-4 py-3 rounded-xl bg-sky-50/60 dark:bg-sky-900/20 border border-sky-200/40 dark:border-sky-700/30 text-sky-900 dark:text-sky-100 text-sm font-medium placeholder:text-sky-400/40 transition-all" placeholder="contoh@email.com" />
                  </div>
                </div>
                <div>
                  <label className="block text-xs font-bold text-sky-700 dark:text-sky-300 mb-1.5">Password</label>
                  <div className="relative">
                    <Lock className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-sky-400/60" />
                    <input type={showPw ? 'text' : 'password'} value={form.password} onChange={(e) => setForm(f => ({ ...f, password: e.target.value }))}
                      className="w-full pl-10 pr-12 py-3 rounded-xl bg-sky-50/60 dark:bg-sky-900/20 border border-sky-200/40 dark:border-sky-700/30 text-sky-900 dark:text-sky-100 text-sm font-medium placeholder:text-sky-400/40 transition-all" placeholder="Masukkan password" />
                    <button type="button" onClick={() => setShowPw(!showPw)} className="absolute right-3 top-1/2 -translate-y-1/2 text-sky-400/50 hover:text-sky-600 transition-colors">
                      {showPw ? <EyeOff className="w-4 h-4" /> : <Eye className="w-4 h-4" />}
                    </button>
                  </div>
                </div>
                <button type="submit" disabled={loading}
                  className="w-full group flex items-center justify-center gap-2 px-6 py-3.5 rounded-2xl text-white font-bold text-sm transition-all duration-300 hover:-translate-y-0.5 disabled:opacity-50 mt-2"
                  style={{ background: 'linear-gradient(135deg, #0ea5e9, #6366f1)', boxShadow: '0 6px 24px rgba(14,165,233,0.3)' }}>
                  {loading ? <div className="w-5 h-5 border-2 border-white/30 border-t-white rounded-full animate-spin-slow" /> : <>Login <ArrowRight className="w-4 h-4 group-hover:translate-x-1 transition-transform" /></>}
                </button>
              </form>
              <p className="text-sm text-sky-600/50 dark:text-sky-400/40 text-center mt-5">
                Belum punya akun? <Link href="/register" className="font-bold text-sky-500 hover:text-sky-700 dark:hover:text-sky-200 transition-colors">Daftar</Link>
              </p>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}
