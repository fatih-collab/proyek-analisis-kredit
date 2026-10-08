'use client';

import React, { useState } from 'react';
import { LogIn, Mail, Lock, ArrowRight, Eye, EyeOff, Sparkles, Home, UserPlus } from 'lucide-react';
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

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault(); setError('');
    if (!form.email || !form.password) { setError('Email dan password wajib diisi'); return; }
    setLoading(true);
    const res = await login(form.email, form.password);
    setLoading(false);
    if (res.success) router.push('/dashboard'); else setError(res.error || 'Login gagal');
  };

  return (
    <div className="min-h-screen relative transition-colors duration-300 noise-overlay">
      <div className="gradient-mesh" /><div className="orb orb-1" /><div className="orb orb-2" />
      <Header />
      <div className="relative z-10 flex items-center justify-center min-h-screen px-4 py-24">
        <div className="w-full max-w-2xl">
          
          <div className="overflow-hidden rounded-[28px] border border-sky-100/50 dark:border-sky-900/30 shadow-2xl shadow-sky-500/10">
            {/* Header Card (ss 1 style) */}
            <div className="bg-gradient-to-r from-sky-500 via-sky-600 to-indigo-600 px-10 py-12 text-center text-white relative">
              <div className="absolute top-0 right-0 w-24 h-24 bg-white/5 rounded-full -translate-y-6 translate-x-6 blur-xl" />
              <div className="absolute bottom-0 left-0 w-32 h-32 bg-white/5 rounded-full translate-y-12 -translate-x-12 blur-2xl" />
              
              <div className="inline-flex items-center justify-center w-20 h-20 rounded-full bg-white/10 backdrop-blur-md border border-white/20 mb-5 shadow-inner">
                <LogIn className="w-10 h-10 text-white" />
              </div>
              <h1 className="text-4xl font-extrabold tracking-tight mb-2.5">Hai, Selamat Datang! 👋</h1>
              <p className="text-sky-100 text-base font-medium max-w-md mx-auto">Silakan login untuk mengakses seluruh fitur simulasi kelayakan kredit Anda</p>
            </div>

            {/* Body Card */}
            <div className="bg-white/95 dark:bg-slate-950/95 backdrop-blur-xl p-10 sm:p-12 space-y-8">
              {error && (
                <div className="px-5 py-4 rounded-2xl bg-rose-50 dark:bg-rose-950/20 border border-rose-200/50 dark:border-rose-800/30 text-rose-600 dark:text-rose-400 text-base font-semibold flex items-center gap-2">
                  <span className="w-2.5 h-2.5 rounded-full bg-rose-500 animate-pulse" />
                  {error}
                </div>
              )}

              <form onSubmit={handleSubmit} className="space-y-6">
                <div className="space-y-2.5">
                  <label className="block text-sm font-bold uppercase tracking-wider text-sky-800 dark:text-sky-300">Alamat Email</label>
                  <div className="relative">
                    <Mail className="absolute left-5 top-1/2 -translate-y-1/2 w-6 h-6 text-sky-400/60" />
                    <input 
                      type="email" 
                      value={form.email} 
                      onChange={(e) => setForm(f => ({ ...f, email: e.target.value }))}
                      className="w-full pl-14 pr-5 py-5 text-lg rounded-[20px] bg-sky-50/40 dark:bg-sky-950/10 border border-sky-100 dark:border-sky-900/30 text-sky-900 dark:text-sky-100 font-medium placeholder:text-sky-400/30 focus:outline-none focus:ring-2 focus:ring-sky-500 transition-all" 
                      placeholder="nama@email.com" 
                    />
                  </div>
                </div>

                <div className="space-y-2.5">
                  <label className="block text-sm font-bold uppercase tracking-wider text-sky-800 dark:text-sky-300">Kata Sandi</label>
                  <div className="relative">
                    <Lock className="absolute left-5 top-1/2 -translate-y-1/2 w-6 h-6 text-sky-400/60" />
                    <input 
                      type={showPw ? 'text' : 'password'} 
                      value={form.password} 
                      onChange={(e) => setForm(f => ({ ...f, password: e.target.value }))}
                      className="w-full pl-14 pr-14 py-5 text-lg rounded-[20px] bg-sky-50/40 dark:bg-sky-950/10 border border-sky-100 dark:border-sky-900/30 text-sky-900 dark:text-sky-100 font-medium placeholder:text-sky-400/30 focus:outline-none focus:ring-2 focus:ring-sky-500 transition-all" 
                      placeholder="Masukkan kata sandi Anda" 
                    />
                    <button 
                      type="button" 
                      onClick={() => setShowPw(!showPw)} 
                      className="absolute right-5 top-1/2 -translate-y-1/2 text-sky-400/50 hover:text-sky-600 transition-colors"
                    >
                      {showPw ? <EyeOff className="w-6 h-6" /> : <Eye className="w-6 h-6" />}
                    </button>
                  </div>
                </div>

                <button 
                  type="submit" 
                  disabled={loading}
                  className="w-full group flex items-center justify-center gap-3 px-6 py-5 rounded-2xl text-white font-black text-lg transition-all duration-300 hover:-translate-y-1 hover:shadow-lg hover:shadow-sky-500/20 active:translate-y-0 disabled:opacity-50 mt-6 cursor-pointer"
                  style={{ background: 'linear-gradient(135deg, #0ea5e9, #6366f1)' }}
                >
                  {loading ? (
                    <div className="w-7 h-7 border-2 border-white/30 border-t-white rounded-full animate-spin" />
                  ) : (
                    <>Masuk ke Akun <ArrowRight className="w-6 h-6 group-hover:translate-x-1.5 transition-transform" /></>
                  )}
                </button>
              </form>

              {/* Informative info box (ss 1 style) */}
              <div className="bg-sky-50/80 dark:bg-sky-950/20 border border-sky-100 dark:border-sky-900/30 text-sky-800 dark:text-sky-300 rounded-2xl p-5 text-base font-medium leading-relaxed flex items-start gap-4">
                <span className="text-xl leading-none mt-0.5">💡</span>
                <div>
                  Belum memiliki akun? Silakan klik tombol pendaftaran di bawah ini untuk membuat akun baru secara gratis.
                </div>
              </div>

              {/* Action Links */}
              <div className="flex flex-col sm:flex-row items-center justify-between gap-4 pt-5 border-t border-sky-100/30 dark:border-sky-900/20">
                <Link 
                  href="/register" 
                  className="flex items-center gap-2 text-base font-bold text-sky-600 hover:text-sky-800 dark:text-sky-400 dark:hover:text-sky-200 transition-colors"
                >
                  <UserPlus className="w-5 h-5" /> Daftar Akun Baru
                </Link>
                <Link 
                  href="/" 
                  className="flex items-center gap-2 text-base font-bold text-slate-500 hover:text-slate-700 dark:text-slate-400 dark:hover:text-slate-200 transition-colors"
                >
                  <Home className="w-5 h-5" /> Lihat-lihat Dulu
                </Link>
              </div>

            </div>
          </div>
          
        </div>
      </div>
    </div>
  );
}
